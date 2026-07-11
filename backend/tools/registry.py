"""Tool dispatch.

Maps tool names to their implementations and executes them. Tools that need
per-session context (the finalize tools) receive it via `ctx`; the rest are
called with the LLM-supplied arguments alone.
"""
from __future__ import annotations

from typing import Any

from .checks import (
    calculate_refund_amount,
    check_customer_standing,
    check_high_value,
    check_item_eligibility,
    check_return_window,
)
from .decisions import deny_refund, escalate_to_human, process_refund
from .lookup import get_order, lookup_customer

# Tools that also need session context receive it via `ctx`.
_CTX_TOOLS = {"process_refund", "deny_refund", "escalate_to_human"}
_REGISTRY = {
    "lookup_customer": lookup_customer,
    "get_order": get_order,
    "check_return_window": check_return_window,
    "check_item_eligibility": check_item_eligibility,
    "check_customer_standing": check_customer_standing,
    "check_high_value": check_high_value,
    "calculate_refund_amount": calculate_refund_amount,
    "process_refund": process_refund,
    "deny_refund": deny_refund,
    "escalate_to_human": escalate_to_human,
}


def execute_tool(name: str, args: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    fn = _REGISTRY.get(name)
    if fn is None:
        return {"error": f"Unknown tool '{name}'."}
    try:
        if name in _CTX_TOOLS:
            return fn(ctx=ctx, **args)
        return fn(**args)
    except TypeError as exc:
        return {"error": f"Invalid arguments for '{name}': {exc}"}
