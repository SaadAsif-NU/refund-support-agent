"""Read-only CRM lookup tools.

Identity verification and order retrieval (policy Section 4). These tools only
read from the store; they never record an outcome.
"""
from __future__ import annotations

from typing import Any

from ..store import store


def lookup_customer(identifier: str) -> dict[str, Any]:
    """Section 4 - verify the customer exists (by id or email)."""
    customer = store.find_customer(identifier)
    if not customer:
        return {"found": False,
                "detail": f"No customer found for '{identifier}'. Ask them to verify their email or customer ID."}
    return {
        "found": True,
        "customer_id": customer["id"],
        "name": customer["name"],
        "email": customer["email"],
        "tier": customer["tier"],
        "refunds_last_12_months": customer["refunds_last_12_months"],
        "flagged_for_review": customer["flagged_for_review"],
        "orders": [{"order_id": o["id"], "item": o["item"], "amount": o["amount"], "status": o["status"]}
                   for o in customer["orders"]],
    }


def get_order(order_id: str, customer_id: str | None = None) -> dict[str, Any]:
    """Section 4 - fetch an order and confirm it belongs to the customer."""
    order = store.get_order(order_id)
    if not order:
        return {"found": False,
                "detail": f"No order found with ID '{order_id}'. Ask the customer to re-check the order number."}
    if customer_id:
        # Resolve the supplied id/email to a canonical customer so 'cust001',
        # 'CUST-001', or the email all compare correctly.
        requester = store.find_customer(customer_id)
        if not requester or requester["id"] != order["_customer_id"]:
            return {"found": True, "belongs_to_customer": False, "policy_ref": "Section 4",
                    "detail": f"Order {order['id']} does not belong to customer {customer_id}. Deny per Section 4."}
    return {
        "found": True,
        "belongs_to_customer": True,
        "order_id": order["id"],
        "item": order["item"],
        "category": order["category"],
        "amount": order["amount"],
        "shipping_fee": order["shipping_fee"],
        "status": order["status"],
        "condition": order["condition"],
        "final_sale": order["final_sale"],
        "digital": order["digital"],
        "already_refunded": order["already_refunded"],
        "delivered_date": order["delivered_date"],
        "days_since_delivery": store.days_since_delivery(order),
    }
