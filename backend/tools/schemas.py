"""OpenAI-compatible tool schemas.

The JSON function-calling schemas advertised to every provider. The Anthropic
adapter translates these into its `input_schema` shape at call time.
"""
from __future__ import annotations

from typing import Any


def _tool(name: str, description: str, props: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {"type": "function", "function": {
        "name": name, "description": description,
        "parameters": {"type": "object", "properties": props, "required": required},
    }}


_STR = {"type": "string"}
TOOL_SCHEMAS = [
    _tool("lookup_customer", "Look up a customer by their email or customer ID to verify identity (policy Section 4).",
          {"identifier": {**_STR, "description": "Customer email or ID, e.g. 'CUST-001' or 'emily.carter@example.com'."}},
          ["identifier"]),
    _tool("get_order", "Fetch an order's full details and confirm it belongs to the customer (policy Section 4).",
          {"order_id": {**_STR, "description": "Order ID, e.g. 'ORD-1001'."},
           "customer_id": {**_STR, "description": "The customer's ID to verify ownership (optional but recommended)."}},
          ["order_id"]),
    _tool("check_return_window", "Check whether the request is within the applicable return window (Section 1 standard / Section 7 defective).",
          {"order_id": _STR}, ["order_id"]),
    _tool("check_item_eligibility", "Check category, item condition, order status, and duplicate-refund rules (Section 2/Section 3/Section 6/Section 8).",
          {"order_id": _STR}, ["order_id"]),
    _tool("check_customer_standing", "Run the fraud/abuse guard for a customer (Section 9). May force escalation.",
          {"identifier": {**_STR, "description": "Customer email or ID."}}, ["identifier"]),
    _tool("check_high_value", "Check whether the order exceeds the manager-approval threshold (Section 10).",
          {"order_id": _STR}, ["order_id"]),
    _tool("calculate_refund_amount", "Compute the final refundable amount including any restocking fee (Section 5/Section 7).",
          {"order_id": _STR}, ["order_id"]),
    _tool("process_refund", "Issue an APPROVED refund. Only call after all checks pass.",
          {"order_id": _STR, "amount": {"type": "number", "description": "Final amount to refund."},
           "reason": {**_STR, "description": "Short justification citing policy."}},
          ["order_id", "amount", "reason"]),
    _tool("deny_refund", "Deny a refund. Always cite the specific policy section.",
          {"order_id": _STR, "reason": _STR, "policy_ref": {**_STR, "description": "e.g. 'Section 1'"}},
          ["order_id", "reason", "policy_ref"]),
    _tool("escalate_to_human", "Escalate to a human manager (fraud guard Section 9, high value Section 10, or undelivered Section 6).",
          {"order_id": _STR, "reason": _STR, "policy_ref": _STR},
          ["order_id", "reason", "policy_ref"]),
]
