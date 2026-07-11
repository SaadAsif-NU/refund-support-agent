"""The refund agent loop.

A transparent, framework-free function-calling loop: the LLM proposes tool
calls, we execute them against the deterministic policy engine, feed results
back, and repeat until the model produces a final customer-facing answer.
Every step is emitted to the reasoning event bus for the admin dashboard, and
LLM calls are wrapped with retry/backoff so transient failures are visible and
recoverable.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from . import policy
from .events import bus
from .llm import AssistantTurn, ProviderManager
from .prompts import SYSTEM_PROMPT
from .store import store
from .tools import TOOL_SCHEMAS, execute_tool

MAX_STEPS = 10
MAX_RETRIES = 2
FINAL_OUTCOMES = {"APPROVE", "APPROVE_PARTIAL", "DENY", "ESCALATE"}
# Only these tools produce a real decision; other tools (e.g. calculate_refund_amount)
# may carry a proposed `outcome` but must not fire a decision event.
FINALIZE_TOOLS = {"process_refund", "deny_refund", "escalate_to_human"}


class Agent:
    """Holds per-session conversation state and runs the tool-calling loop."""

    def __init__(self) -> None:
        self.providers = ProviderManager()
        self._sessions: dict[str, list[dict[str, Any]]] = {}

    def describe(self, provider: str | None = None) -> dict[str, str]:
        return self.providers.describe(provider)

    def provider_catalog(self) -> list[dict[str, Any]]:
        return self.providers.catalog()

    def _history(self, session_id: str) -> list[dict[str, Any]]:
        if session_id not in self._sessions:
            self._sessions[session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
        return self._sessions[session_id]

    async def handle_message(self, session_id: str, user_text: str, provider: str | None = None) -> str:
        provider = self.providers.resolve(provider)
        info = self.providers.describe(provider)
        messages = self._history(session_id)
        messages.append({"role": "user", "content": user_text})
        await bus.emit(session_id, "session_start",
                       {"user_message": user_text, "provider": provider, "model": info["model"]})

        # Track this request so we can backstop a decision the model narrates
        # but forgets to record via a finalize tool (real models sometimes do).
        finalized = False
        turn_order_id: str | None = None
        turn_customer_id: str | None = None
        degraded = False  # once the cloud provider fails, finish the turn offline

        for step in range(MAX_STEPS):
            if degraded:
                turn = self.providers.complete_offline(messages)
            else:
                turn, degraded = await self._complete_with_retry(session_id, messages, provider)

            if turn.content and turn.tool_calls:
                await bus.emit(session_id, "thought", {"text": turn.content})

            if turn.tool_calls:
                messages.append(self._assistant_dict(turn))
                for call in turn.tool_calls:
                    await bus.emit(session_id, "tool_call",
                                   {"tool": call.name, "arguments": call.arguments})
                    result = execute_tool(call.name, call.arguments,
                                          {"session_id": session_id, "verified_customer_id": turn_customer_id})
                    outcome = result.get("outcome") if isinstance(result, dict) else None
                    await bus.emit(session_id, "tool_result",
                                   {"tool": call.name, "result": result})
                    if call.arguments.get("order_id"):
                        turn_order_id = call.arguments["order_id"]
                    if call.name == "lookup_customer" and result.get("found"):
                        turn_customer_id = result.get("customer_id")
                    elif call.arguments.get("customer_id"):
                        turn_customer_id = call.arguments["customer_id"]
                    if call.name in FINALIZE_TOOLS and outcome in FINAL_OUTCOMES:
                        await bus.emit(session_id, "decision",
                                       {"tool": call.name, "outcome": outcome, "result": result})
                        finalized = True
                    messages.append({
                        "role": "tool", "tool_call_id": call.id,
                        "content": json.dumps(result, default=str),
                    })
                continue

            # No tool calls -> final answer to the customer.
            reply = turn.content or "I'm sorry, I wasn't able to complete that. Could you rephrase?"
            if not finalized and turn_order_id:
                await self._auto_finalize(session_id, turn_order_id, turn_customer_id)
            messages.append({"role": "assistant", "content": reply})
            await bus.emit(session_id, "assistant_message", {"text": reply})
            await bus.emit(session_id, "session_end", {"steps": step + 1})
            return reply

        # Safety valve: the loop ran too long.
        fallback = ("I'm having trouble completing this request right now. I've flagged it for a "
                    "human agent who will follow up with you shortly.")
        await bus.emit(session_id, "error", {"text": "Max reasoning steps exceeded; handing off."})
        await bus.emit(session_id, "assistant_message", {"text": fallback})
        messages.append({"role": "assistant", "content": fallback})
        return fallback

    async def _auto_finalize(self, session_id: str, order_id: str, customer_id: str | None) -> None:
        """Deterministic backstop: the model gave a final answer without calling a
        finalize tool, so the policy engine computes the authoritative decision and
        records it (keeps the admin log and refund ledger complete and trustworthy)."""
        order = store.get_order(order_id)
        if not order:
            return
        customer = store.find_customer(order["_customer_id"])
        decision = policy.evaluate(order, customer, store.days_since_delivery(order), customer_id)
        kind = decision["kind"]
        if kind == "APPROVE":
            tool = "process_refund"
            args = {"order_id": order_id, "amount": decision.get("refund_amount", order["amount"]),
                    "reason": decision["reason"]}
        elif kind == "ESCALATE":
            tool = "escalate_to_human"
            args = {"order_id": order_id, "reason": decision["reason"], "policy_ref": decision["policy_ref"]}
        else:
            tool = "deny_refund"
            args = {"order_id": order_id, "reason": decision["reason"], "policy_ref": decision["policy_ref"]}

        result = execute_tool(tool, args, {"session_id": session_id, "verified_customer_id": customer_id})
        await bus.emit(session_id, "tool_call", {"tool": tool, "arguments": args, "auto": True})
        await bus.emit(session_id, "tool_result", {"tool": tool, "result": result})
        outcome = result.get("outcome") if isinstance(result, dict) else None
        if outcome in FINAL_OUTCOMES:
            await bus.emit(session_id, "decision",
                           {"tool": tool, "outcome": outcome, "result": result, "auto": True})

    async def _complete_with_retry(self, session_id: str, messages: list[dict[str, Any]],
                                   provider: str) -> tuple[AssistantTurn, bool]:
        """Returns (turn, degraded). `degraded` is True when the cloud provider
        failed and we fell back to the offline engine - the caller then finishes
        the rest of the turn offline instead of re-retrying a rate-limited API."""
        last_exc: Exception | None = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                turn = await self.providers.complete(provider, messages, TOOL_SCHEMAS)
                if not turn.content and not turn.tool_calls:
                    raise ValueError("Empty completion (no content and no tool calls).")
                return turn, False
            except Exception as exc:  # noqa: BLE001 - surface any provider/parse error
                last_exc = exc
                msg = str(exc).lower()
                # A rate limit / quota error won't clear in a couple of seconds, so
                # don't burn retries on it - degrade to the offline engine now.
                rate_limited = ("429" in msg or "quota" in msg or "rate limit" in msg
                                or type(exc).__name__ == "RateLimitError")
                if attempt < MAX_RETRIES and not rate_limited:
                    await bus.emit(session_id, "retry", {
                        "attempt": attempt + 1, "max": MAX_RETRIES, "error": str(exc),
                    })
                    await asyncio.sleep(0.8 * (attempt + 1))
                else:
                    break

        # Provider unreachable (rate limit / auth / network). Rather than dead-end
        # the customer, fall back to the deterministic offline engine so the
        # conversation still completes correctly. The admin panel shows the reason.
        await bus.emit(session_id, "error",
                       {"text": f"{provider} unavailable ({last_exc}); continuing on the offline engine."})
        if provider != "mock":
            try:
                return self.providers.complete_offline(messages), True
            except Exception:  # noqa: BLE001
                pass
        return AssistantTurn(content=(
            "I'm sorry - I'm having a technical issue right now. Please try again in a moment.")), False

    @staticmethod
    def _assistant_dict(turn: AssistantTurn) -> dict[str, Any]:
        return {
            "role": "assistant",
            "content": turn.content or "",
            "tool_calls": [{
                "id": c.id, "type": "function",
                "function": {"name": c.name, "arguments": json.dumps(c.arguments)},
            } for c in turn.tool_calls],
        }


agent = Agent()
