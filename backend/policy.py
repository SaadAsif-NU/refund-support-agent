"""Deterministic refund-policy engine.

The LLM orchestrates and communicates, but every *decision-relevant fact* is
computed here in plain Python. This keeps outcomes trustworthy and auditable:
the agent cannot hallucinate a customer into (or out of) a refund.
"""
from __future__ import annotations

from typing import Any

# ── Policy constants (mirror backend/data/refund_policy.md) ──────
STANDARD_WINDOW_DAYS = 30
DEFECTIVE_WINDOW_DAYS = 90
RESTOCKING_FEE_RATE = 0.15
HIGH_VALUE_THRESHOLD = 500.0
FRAUD_REFUND_LIMIT = 3  # more than this in 12 months -> escalate

NON_REFUNDABLE_CATEGORIES = {"gift_card", "perishable", "intimate_apparel"}
DEFECT_CONDITIONS = {"defective", "damaged"}


def check_window(order: dict[str, Any], days_since_delivery: int | None) -> dict[str, Any]:
    """Section 1 / Section 7 - return-window eligibility (defective items get 90 days)."""
    defective = order.get("condition") in DEFECT_CONDITIONS
    limit = DEFECTIVE_WINDOW_DAYS if defective else STANDARD_WINDOW_DAYS
    ref = "Section 7" if defective else "Section 1"
    if days_since_delivery is None:
        return {
            "passed": False,
            "policy_ref": "Section 6",
            "detail": "Order has not been delivered yet; no return window has started.",
        }
    passed = days_since_delivery <= limit
    return {
        "passed": passed,
        "policy_ref": ref,
        "limit_days": limit,
        "days_since_delivery": days_since_delivery,
        "detail": (
            f"Delivered {days_since_delivery} days ago; within the {limit}-day "
            f"{'defective-item ' if defective else ''}window."
            if passed
            else f"Delivered {days_since_delivery} days ago, which is past the {limit}-day window."
        ),
    }


def check_category(order: dict[str, Any]) -> dict[str, Any]:
    """Section 3 - non-refundable categories / final sale / downloaded digital goods."""
    category = order.get("category")
    if order.get("final_sale"):
        return {"passed": False, "policy_ref": "Section 3",
                "detail": f"Item was a Final Sale purchase ({category}); not refundable."}
    if category in NON_REFUNDABLE_CATEGORIES:
        return {"passed": False, "policy_ref": "Section 3",
                "detail": f"Category '{category}' is non-refundable (final sale)."}
    if order.get("digital") and order.get("condition") == "used":
        return {"passed": False, "policy_ref": "Section 3",
                "detail": "Digital goods are non-refundable once downloaded/activated."}
    return {"passed": True, "policy_ref": "Section 3",
            "detail": f"Category '{category}' is eligible for refund."}


def check_condition(order: dict[str, Any]) -> dict[str, Any]:
    """Section 2 - item condition (used non-defective items are not eligible)."""
    condition = order.get("condition")
    if condition in DEFECT_CONDITIONS:
        return {"passed": True, "policy_ref": "Section 7",
                "detail": f"Item reported as {condition}; qualifies under the defective/damaged policy."}
    if condition == "used":
        return {"passed": False, "policy_ref": "Section 2",
                "detail": "Item is used and not defective; not in resalable condition."}
    return {"passed": True, "policy_ref": "Section 2",
            "detail": f"Item condition '{condition}' is resalable."}


def check_status(order: dict[str, Any]) -> dict[str, Any]:
    """Section 6 - only delivered orders can be refunded."""
    status = order.get("status")
    if status != "delivered":
        return {"passed": False, "policy_ref": "Section 6",
                "detail": f"Order status is '{status}', not 'delivered'. Cancellation must be handled by a human."}
    return {"passed": True, "policy_ref": "Section 6", "detail": "Order is delivered."}


def check_duplicate(order: dict[str, Any]) -> dict[str, Any]:
    """Section 8 - already-refunded orders cannot be refunded again."""
    if order.get("already_refunded"):
        return {"passed": False, "policy_ref": "Section 8",
                "detail": "This order has already been refunded."}
    return {"passed": True, "policy_ref": "Section 8", "detail": "No prior refund on this order."}


def check_fraud(customer: dict[str, Any]) -> dict[str, Any]:
    """Section 9 - fraud/abuse guard -> escalate (never auto-approve)."""
    count = customer.get("refunds_last_12_months", 0)
    flagged = customer.get("flagged_for_review", False)
    if flagged or count > FRAUD_REFUND_LIMIT:
        reason = "account flagged for review" if flagged else f"{count} refunds in the last 12 months (limit {FRAUD_REFUND_LIMIT})"
        return {"passed": False, "escalate": True, "policy_ref": "Section 9",
                "detail": f"Fraud guard triggered: {reason}. Requires human manager."}
    return {"passed": True, "escalate": False, "policy_ref": "Section 9",
            "detail": f"{count} refunds in the last 12 months; within abuse limits."}


def check_high_value(order: dict[str, Any]) -> dict[str, Any]:
    """Section 10 - orders over the threshold need manager approval -> escalate."""
    amount = float(order.get("amount", 0))
    if amount > HIGH_VALUE_THRESHOLD:
        return {"passed": False, "escalate": True, "policy_ref": "Section 10",
                "detail": f"Item price ${amount:.2f} exceeds ${HIGH_VALUE_THRESHOLD:.0f}; needs manager approval."}
    return {"passed": True, "escalate": False, "policy_ref": "Section 10",
            "detail": f"Item price ${amount:.2f} is within the auto-approval limit."}


def evaluate(order: dict[str, Any], customer: dict[str, Any],
             days_since_delivery: int | None, verified_customer_id: str | None = None) -> dict[str, Any]:
    """Authoritative end-to-end decision for one order, in policy precedence.

    This is the single source of truth used both by the offline agent's decision
    logic and by the live-agent safety net (when a real model narrates a decision
    without calling a finalize tool). Ownership (Section 4) is enforced here too.
    """
    if verified_customer_id and order.get("_customer_id", "").upper() != verified_customer_id.upper():
        return {"kind": "DENY", "policy_ref": "Section 4",
                "reason": "Order does not belong to the verified customer."}
    if order.get("status") != "delivered":
        return {"kind": "ESCALATE", "policy_ref": "Section 6",
                "reason": f"Order status is '{order.get('status')}'; cancellation needs a human."}
    if order.get("already_refunded"):
        return {"kind": "DENY", "policy_ref": "Section 8", "reason": "This order has already been refunded."}
    cat = check_category(order)
    if not cat["passed"]:
        return {"kind": "DENY", "policy_ref": cat["policy_ref"], "reason": cat["detail"]}
    cond = check_condition(order)
    if not cond["passed"]:
        return {"kind": "DENY", "policy_ref": cond["policy_ref"], "reason": cond["detail"]}
    win = check_window(order, days_since_delivery)
    if not win["passed"]:
        return {"kind": "DENY", "policy_ref": win["policy_ref"], "reason": win["detail"]}
    if customer and check_fraud(customer)["escalate"]:
        return {"kind": "ESCALATE", "policy_ref": "Section 9", "reason": check_fraud(customer)["detail"]}
    hv = check_high_value(order)
    if hv["escalate"]:
        return {"kind": "ESCALATE", "policy_ref": "Section 10", "reason": hv["detail"]}
    calc = compute_refund_amount(order)
    return {"kind": "APPROVE", "policy_ref": calc["policy_ref"],
            "reason": "All eligibility checks passed.",
            "refund_amount": calc["refund_amount"], "restocking_fee": calc["restocking_fee"]}


def compute_refund_amount(order: dict[str, Any]) -> dict[str, Any]:
    """Section 5 / Section 7 / Section 11 - final refundable amount, applying any restocking fee."""
    amount = float(order.get("amount", 0))
    defective = order.get("condition") in DEFECT_CONDITIONS
    opened_electronics = order.get("category") == "electronics" and order.get("condition") == "opened"
    if opened_electronics and not defective:
        fee = round(amount * RESTOCKING_FEE_RATE, 2)
        return {"refund_amount": round(amount - fee, 2), "restocking_fee": fee,
                "policy_ref": "Section 5", "outcome": "APPROVE_PARTIAL",
                "detail": f"Opened electronics: 15% restocking fee (${fee:.2f}) applied."}
    return {"refund_amount": round(amount, 2), "restocking_fee": 0.0,
            "policy_ref": "Section 7" if defective else "Section 5", "outcome": "APPROVE",
            "detail": "Full item price refundable; no restocking fee."}
