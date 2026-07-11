"""OpenAI-canonical -> Anthropic Messages API translation.

The app keeps one canonical (OpenAI-shaped) message history. Anthropic's
Messages API differs - the system prompt is a top-level arg, tool calls/results
are content blocks, and consecutive tool results collapse into one user turn -
so we translate at call time rather than storing a second history.
"""
from __future__ import annotations

import json
from typing import Any


def _split_system(messages: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    """Anthropic takes the system prompt as a top-level arg, not a message."""
    system_parts, convo = [], []
    for m in messages:
        if m.get("role") == "system":
            system_parts.append(m.get("content") or "")
        else:
            convo.append(m)
    return "\n\n".join(p for p in system_parts if p), convo


def _to_anthropic_messages(convo: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in convo:
        role = m.get("role")
        if role == "user":
            out.append({"role": "user", "content": m.get("content") or ""})
        elif role == "assistant":
            blocks: list[dict[str, Any]] = []
            if m.get("content"):
                blocks.append({"type": "text", "text": m["content"]})
            for tc in (m.get("tool_calls") or []):
                try:
                    args = json.loads(tc["function"]["arguments"] or "{}")
                except (json.JSONDecodeError, TypeError):
                    args = {}
                blocks.append({"type": "tool_use", "id": tc["id"],
                               "name": tc["function"]["name"], "input": args})
            out.append({"role": "assistant", "content": blocks or [{"type": "text", "text": "..."}]})
        elif role == "tool":
            block = {"type": "tool_result", "tool_use_id": m.get("tool_call_id"),
                     "content": m.get("content") or ""}
            # Merge consecutive tool results into a single user turn (Anthropic
            # expects all tool_results for a turn in one user message).
            if out and out[-1]["role"] == "user" and isinstance(out[-1]["content"], list):
                out[-1]["content"].append(block)
            else:
                out.append({"role": "user", "content": [block]})
    return out


def _to_anthropic_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{"name": t["function"]["name"], "description": t["function"]["description"],
             "input_schema": t["function"]["parameters"]} for t in tools]
