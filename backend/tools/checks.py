"""Policy-check tools.

Each tool runs one deterministic policy check from the engine (policy.py) over a
given order or customer and returns the structured result the LLM reasons over.
These are read-only: they inform the decision but never record it.
"""
from __future__ import annotations

from typing import Any

from .. import policy
from ..store import store


def check_return_window(order_id: str) -> dict[str, Any]:
    """Section 1 / Section 7 - is the request inside the applicable return window?"""
    order = store.get_order(order_id)
    if not order:
        return {"error": f"Order '{order_id}' not found."}
    return policy.check_window(order, store.days_since_delivery(order))


def check_item_eligibility(order_id: str) -> dict[str, Any]:
    """Section 2/Section 3/Section 6/Section 8 - category, condition, order status, and duplicate checks."""
    order = store.get_order(order_id)
    if not order:
        return {"error": f"Order '{order_id}' not found."}
    checks = {
        "category": policy.check_category(order),
        "condition": policy.check_condition(order),
        "status": policy.check_status(order),
        "duplicate": policy.check_duplicate(order),
    }
    failures = [f"{name} ({c['policy_ref']}): {c['detail']}"
                for name, c in checks.items() if not c["passed"]]
    return {"eligible": len(failures) == 0, "checks": checks, "blocking_reasons": failures}


def check_customer_standing(identifier: str) -> dict[str, Any]:
    """Section 9 - fraud/abuse guard; may force escalation."""
    customer = store.find_customer(identifier)
    if not customer:
        return {"error": f"Customer '{identifier}' not found."}
    return policy.check_fraud(customer)


def check_high_value(order_id: str) -> dict[str, Any]:
    """Section 10 - does this order need manager approval?"""
    order = store.get_order(order_id)
    if not order:
        return {"error": f"Order '{order_id}' not found."}
    return policy.check_high_value(order)


def calculate_refund_amount(order_id: str) -> dict[str, Any]:
    """Section 5 / Section 7 - final refundable amount incl. any restocking fee."""
    order = store.get_order(order_id)
    if not order:
        return {"error": f"Order '{order_id}' not found."}
    return policy.compute_refund_amount(order)
