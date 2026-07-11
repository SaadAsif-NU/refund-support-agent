"""Finalize (decision-recording) tools.

These are the only tools that mutate the refund ledger. Each is guarded: the
deterministic policy engine must independently agree with the outcome the model
is trying to record, so the agent cannot approve, deny, or escalate against
policy. They receive session context via `ctx`.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from .. import policy
from ..store import store


def _authoritative(order: dict[str, Any], verified_customer_id: str | None) -> dict[str, Any]:
    """The deterministic verdict the finalize tools are allowed to record."""
    customer = store.find_customer(order["_customer_id"])
    return policy.evaluate(order, customer, store.days_since_delivery(order), verified_customer_id)


def process_refund(order_id: str, amount: float, reason: str, ctx: dict[str, Any]) -> dict[str, Any]:
    """Finalize an APPROVED refund (writes the refund ledger). Guarded: the policy
    engine must agree the outcome is APPROVE, and it fixes the amount."""
    order = store.get_order(order_id)
    if not order:
        return {"success": False, "detail": f"Order '{order_id}' not found."}
    verdict = _authoritative(order, ctx.get("verified_customer_id"))
    if verdict["kind"] != "APPROVE":
        return {"success": False, "blocked": True, "policy_ref": verdict["policy_ref"],
                "detail": (f"Refund not permitted - the correct outcome for this order is "
                           f"{verdict['kind']} ({verdict['policy_ref']}): {verdict['reason']} "
                           f"Record that outcome instead.")}
    amount = verdict.get("refund_amount", amount)   # policy fixes the amount
    outcome = "APPROVE_PARTIAL" if float(amount) < float(order["amount"]) else "APPROVE"
    entry = {
        "order_id": order["id"],
        "customer_id": order["_customer_id"],
        "item": order["item"],
        "amount": round(float(amount), 2),
        "outcome": outcome,
        "reason": reason,
        "method": "original payment method (Section 12)",
        "session_id": ctx.get("session_id"),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    store.record_refund(entry)
    return {"success": True, "outcome": outcome, "refund_id": f"RF-{len(store.refund_ledger):04d}",
            "amount_refunded": entry["amount"], "method": entry["method"], "detail": "Refund issued."}


def deny_refund(order_id: str, reason: str, policy_ref: str, ctx: dict[str, Any]) -> dict[str, Any]:
    """Record a denied refund. Guarded: the policy engine must agree it's a DENY
    (prevents wrongly denying an eligible refund)."""
    order = store.get_order(order_id)
    if order:
        verdict = _authoritative(order, ctx.get("verified_customer_id"))
        if verdict["kind"] != "DENY":
            return {"success": False, "blocked": True, "policy_ref": verdict["policy_ref"],
                    "detail": (f"This order should not be denied - policy says {verdict['kind']} "
                               f"({verdict['policy_ref']}): {verdict['reason']} Record that outcome instead.")}
        policy_ref = verdict["policy_ref"]   # cite the authoritative section
    entry = {
        "order_id": order_id, "customer_id": (order or {}).get("_customer_id"),
        "item": (order or {}).get("item"), "amount": 0.0, "outcome": "DENY",
        "reason": reason, "policy_ref": policy_ref,
        "session_id": ctx.get("session_id"), "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    store.record_refund(entry)
    return {"success": True, "outcome": "DENY", "policy_ref": policy_ref, "detail": "Refund denied and logged."}


def escalate_to_human(order_id: str, reason: str, policy_ref: str, ctx: dict[str, Any]) -> dict[str, Any]:
    """Route the case to a human manager. Guarded: escalation is only valid when the
    policy engine says ESCALATE (fraud Section 9 / high value Section 10 / undelivered Section 6) - a plain
    policy denial (e.g. Section 1 window, Section 3 category) must be denied, not escalated."""
    order = store.get_order(order_id)
    if order:
        verdict = _authoritative(order, ctx.get("verified_customer_id"))
        if verdict["kind"] != "ESCALATE":
            return {"success": False, "blocked": True, "policy_ref": verdict["policy_ref"],
                    "detail": (f"Escalation is not warranted - policy says {verdict['kind']} "
                               f"({verdict['policy_ref']}): {verdict['reason']} Record that outcome instead.")}
        policy_ref = verdict["policy_ref"]
    entry = {
        "order_id": order_id, "customer_id": (order or {}).get("_customer_id"),
        "item": (order or {}).get("item"), "amount": 0.0, "outcome": "ESCALATE",
        "reason": reason, "policy_ref": policy_ref,
        "session_id": ctx.get("session_id"), "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    store.record_refund(entry)
    return {"success": True, "outcome": "ESCALATE", "policy_ref": policy_ref,
            "ticket_id": f"ESC-{len(store.refund_ledger):04d}", "detail": "Escalated to a human manager."}
