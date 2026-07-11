"""Agent tools.

Each tool is a small, pure-ish function over the CRM store and the policy
engine. The agent loop dispatches through `execute_tool`; the LLM only ever
sees the JSON these functions return. Deterministic policy math lives in
policy.py, so the agent's decisions are auditable rather than hallucinated.

The tools are grouped by responsibility:
  * lookup    - read-only identity/order retrieval (Section 4)
  * checks    - individual policy checks (read-only)
  * decisions - the guarded finalize tools that record an outcome
  * registry  - name -> implementation dispatch (`execute_tool`)
  * schemas   - the OpenAI-compatible tool schemas (`TOOL_SCHEMAS`)

Everything the rest of the app imported from the old `tools` module is
re-exported here, so `from .tools import execute_tool, TOOL_SCHEMAS` still works.
"""
from __future__ import annotations

from .checks import (
    calculate_refund_amount,
    check_customer_standing,
    check_high_value,
    check_item_eligibility,
    check_return_window,
)
from .decisions import deny_refund, escalate_to_human, process_refund
from .lookup import get_order, lookup_customer
from .registry import execute_tool
from .schemas import TOOL_SCHEMAS

__all__ = [
    "execute_tool",
    "TOOL_SCHEMAS",
    "lookup_customer",
    "get_order",
    "check_return_window",
    "check_item_eligibility",
    "check_customer_standing",
    "check_high_value",
    "calculate_refund_amount",
    "process_refund",
    "deny_refund",
    "escalate_to_human",
]
