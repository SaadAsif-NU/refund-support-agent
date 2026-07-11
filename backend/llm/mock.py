"""Offline deterministic agent.

A tool-calling agent used when no API key is configured (and as a resilience
fallback when a cloud provider is rate-limited mid-conversation). It reads the
conversation, replays which tools have already run, and returns the next tool
call (or the final answer) - mirroring the policy exactly so demos work fully
offline.
"""
from __future__ import annotations

import json
import re
from typing import Any

from ..store import store
from .types import AssistantTurn, ToolCall

_CUST_RE = re.compile(r"CUST[-\s]?(\d{3,})", re.IGNORECASE)
_ORD_RE = re.compile(r"ORD[-\s]?(\d{3,})", re.IGNORECASE)
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


class MockLLM:
    """Deterministic tool-calling agent used when no API key is configured.

    It reads the conversation, replays which tools have already run, and
    returns the next tool call (or the final answer) - mirroring the real
    policy exactly so demos work fully offline.
    """

    _counter = 0

    def _call(self, name: str, args: dict[str, Any], thought: str) -> AssistantTurn:
        MockLLM._counter += 1
        return AssistantTurn(
            content=thought,
            tool_calls=[ToolCall(id=f"mock-{MockLLM._counter}", name=name, arguments=args)],
        )

    def complete(self, messages: list[dict[str, Any]]) -> AssistantTurn:
        # Scope to the CURRENT request: everything after the last finalized decision.
        # This lets one browser session handle many independent refund requests
        # (and multi-turn clarifications) without leaking stale tool results.
        id_to_name = self._id_to_name(messages)
        window = self._current_window(messages, id_to_name)
        results = self._collect_results(window, id_to_name)
        user_text = " ".join(m.get("content") or "" for m in window if m.get("role") == "user")

        order_id = self._extract(user_text, _ORD_RE, "ORD-")
        cust_id = self._extract(user_text, _CUST_RE, "CUST-")
        email_m = _EMAIL_RE.search(user_text)
        cust_ident = cust_id or (email_m.group(0) if email_m else None)
        if not cust_ident and order_id:
            o = store.get_order(order_id)
            if o:
                cust_ident = o["_customer_id"]

        # 1) Identify the customer.
        if "lookup_customer" not in results:
            if not cust_ident:
                return AssistantTurn(content=(
                    "I can help with that refund. To verify your account, could you share the "
                    "email on the order or your customer ID (e.g. CUST-001), plus the order number?"))
            return self._call("lookup_customer", {"identifier": cust_ident},
                              "First I need to verify the customer's identity (Section 4).")
        cust = results["lookup_customer"]
        if not cust.get("found"):
            return AssistantTurn(content=(
                "I wasn't able to find an account with those details. Could you double-check the "
                "email or customer ID on the order?"))

        # 2) Pull the order and confirm ownership.
        if not order_id:
            return AssistantTurn(content=(
                f"Thanks {cust['name'].split()[0]} - which order would you like refunded? "
                "Please share the order number (e.g. ORD-1001)."))
        if "get_order" not in results:
            return self._call("get_order", {"order_id": order_id, "customer_id": cust["customer_id"]},
                              "Now I'll pull the order and confirm it belongs to this customer (Section 4).")
        order = results["get_order"]
        if not order.get("found"):
            return AssistantTurn(content=(
                f"I couldn't find order {order_id} on your account. Could you re-check the order number?"))
        if not order.get("belongs_to_customer", True):
            return self._finalize_or_reply(
                results, "deny_refund",
                {"order_id": order_id, "reason": "Order does not belong to this customer.", "policy_ref": "Section 4"},
                "This order isn't linked to the verified account, so I have to decline (Section 4).",
                lambda: (f"I'm sorry, but order {order_id} isn't associated with your account, so I'm unable "
                         "to process a refund on it (policy Section 4). Please double-check the order number."))

        # 3) Gather all decision facts.
        if "check_customer_standing" not in results:
            return self._call("check_customer_standing", {"identifier": cust["customer_id"]},
                              "Running the fraud/abuse guard for this account (Section 9).")
        if "check_item_eligibility" not in results:
            return self._call("check_item_eligibility", {"order_id": order_id},
                              "Checking category, condition, order status and duplicate rules (Section 2/Section 3/Section 6/Section 8).")
        if "check_return_window" not in results:
            return self._call("check_return_window", {"order_id": order_id},
                              "Checking whether we're inside the return window (Section 1/Section 7).")
        if "check_high_value" not in results:
            return self._call("check_high_value", {"order_id": order_id},
                              "Checking whether this order needs manager approval (Section 10).")

        # 4) Decide.
        decision = self._decide(order, results)
        if decision["kind"] == "APPROVE":
            if "calculate_refund_amount" not in results:
                return self._call("calculate_refund_amount", {"order_id": order_id},
                                  "All checks passed - calculating the exact refund amount (Section 5/Section 7).")
            calc = results["calculate_refund_amount"]
            return self._finalize_or_reply(
                results, "process_refund",
                {"order_id": order_id, "amount": calc["refund_amount"], "reason": decision["reason"]},
                "Issuing the approved refund to the original payment method (Section 12).",
                lambda: self._approve_message(cust, order, calc, results.get("process_refund", {})))
        if decision["kind"] == "ESCALATE":
            return self._finalize_or_reply(
                results, "escalate_to_human",
                {"order_id": order_id, "reason": decision["reason"], "policy_ref": decision["policy_ref"]},
                f"This case must go to a human manager ({decision['policy_ref']}).",
                lambda: self._escalate_message(cust, order, decision, results.get("escalate_to_human", {})))
        # DENY
        return self._finalize_or_reply(
            results, "deny_refund",
            {"order_id": order_id, "reason": decision["reason"], "policy_ref": decision["policy_ref"]},
            f"Policy blocks this refund ({decision['policy_ref']}); holding the line.",
            lambda: self._deny_message(cust, order, decision))

    # ── decision logic (mirrors policy.py precedence) ────────────
    def _decide(self, order: dict[str, Any], results: dict[str, Any]) -> dict[str, Any]:
        standing = results.get("check_customer_standing", {})
        elig = results.get("check_item_eligibility", {})
        window = results.get("check_return_window", {})
        hv = results.get("check_high_value", {})

        if order.get("status") != "delivered":
            return {"kind": "ESCALATE", "policy_ref": "Section 6",
                    "reason": f"Order status is '{order.get('status')}'; cancellation needs a human."}
        if order.get("already_refunded"):
            return {"kind": "DENY", "policy_ref": "Section 8",
                    "reason": "This order has already been refunded."}
        checks = elig.get("checks", {})
        for key in ("category", "condition"):
            c = checks.get(key, {})
            if c and not c.get("passed", True):
                return {"kind": "DENY", "policy_ref": c["policy_ref"], "reason": c["detail"]}
        if not window.get("passed", True):
            return {"kind": "DENY", "policy_ref": window.get("policy_ref", "Section 1"),
                    "reason": window.get("detail", "Outside the return window.")}
        if standing.get("escalate"):
            return {"kind": "ESCALATE", "policy_ref": "Section 9", "reason": standing.get("detail")}
        if hv.get("escalate"):
            return {"kind": "ESCALATE", "policy_ref": "Section 10", "reason": hv.get("detail")}
        return {"kind": "APPROVE", "policy_ref": "Section 1", "reason": "All eligibility checks passed."}

    # ── helpers ──────────────────────────────────────────────────
    def _finalize_or_reply(self, results, tool_name, args, thought, message_fn) -> AssistantTurn:
        if tool_name not in results:
            return self._call(tool_name, args, thought)
        return AssistantTurn(content=message_fn())

    @staticmethod
    def _extract(text: str, pattern: re.Pattern, prefix: str) -> str | None:
        m = pattern.search(text or "")
        return f"{prefix}{m.group(1)}" if m else None

    # Calling one of these means a request reached a final outcome; the next
    # user message begins a fresh request.
    _FINALIZE = {"process_refund", "deny_refund", "escalate_to_human"}

    @staticmethod
    def _id_to_name(messages: list[dict[str, Any]]) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for m in messages:
            if m.get("role") == "assistant":
                for tc in (m.get("tool_calls") or []):
                    mapping[tc["id"]] = tc["function"]["name"]
        return mapping

    def _current_window(self, messages: list[dict[str, Any]], id_to_name: dict[str, str]) -> list[dict[str, Any]]:
        """Return the messages belonging to the current request.

        A new request begins at the first user message that arrives *after* a
        finalized decision. The finalize result itself stays in the window so
        the closing message can be rendered before the next request resets it.
        """
        boundary = 0
        saw_final = False
        for i, m in enumerate(messages):
            role = m.get("role")
            if role == "tool" and id_to_name.get(m.get("tool_call_id")) in self._FINALIZE:
                saw_final = True
            elif role == "user" and saw_final:
                boundary = i
                saw_final = False
        return messages[boundary:]

    @staticmethod
    def _collect_results(messages: list[dict[str, Any]], id_to_name: dict[str, str]) -> dict[str, Any]:
        """name -> parsed latest tool result, within the given message slice."""
        results: dict[str, Any] = {}
        for m in messages:
            if m.get("role") == "tool":
                name = id_to_name.get(m.get("tool_call_id"))
                if name:
                    try:
                        results[name] = json.loads(m.get("content") or "{}")
                    except json.JSONDecodeError:
                        results[name] = {}
        return results

    # ── natural-language outcome messages ────────────────────────
    def _approve_message(self, cust, order, calc, refund) -> str:
        rid = refund.get("refund_id", "RF-XXXX")
        if calc.get("outcome") == "APPROVE_PARTIAL":
            fee = calc.get("restocking_fee", 0.0)
            return (f"Good news, {cust['name'].split()[0]} - your refund for the {order['item']} is approved. "
                    f"Because it's an opened electronics item, a 15% restocking fee (${fee:.2f}) applies per "
                    f"policy Section 5, so **${calc['refund_amount']:.2f}** will be returned to your original payment "
                    f"method (Section 12). Confirmation: {rid}. Anything else I can help with?")
        return (f"Good news, {cust['name'].split()[0]} - your refund for the {order['item']} is approved. "
                f"**${calc['refund_amount']:.2f}** will be returned to your original payment method (Section 12) within "
                f"a few business days. Confirmation: {rid}. Is there anything else I can help with?")

    def _deny_message(self, cust, order, decision) -> str:
        return (f"I'm sorry, {cust['name'].split()[0]}, but I'm unable to approve a refund for the "
                f"{order['item']}. {decision['reason']} This falls under our refund policy {decision['policy_ref']}. "
                f"I know that's not the answer you were hoping for. If you believe there's been a mistake, I can "
                f"note your account for a manager to review.")

    def _escalate_message(self, cust, order, decision, esc) -> str:
        ticket = esc.get("ticket_id", "ESC-XXXX")
        return (f"Thanks for your patience, {cust['name'].split()[0]}. Your request for the {order['item']} "
                f"needs a quick review by one of our managers ({decision['policy_ref']}), so I've escalated it "
                f"(ticket {ticket}). A team member will follow up shortly. Is there anything else I can help with?")
