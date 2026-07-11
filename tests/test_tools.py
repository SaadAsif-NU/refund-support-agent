"""Unit tests for the agent tools (backend/tools/).

Read-only tools return structured facts; the finalize tools are *guarded* — they
re-check the deterministic policy engine and refuse to record an outcome the
policy disagrees with. That guard is the core safety property, so it's tested
hard here.
"""
from backend.store import store
from backend.tools import (
    TOOL_SCHEMAS,
    calculate_refund_amount,
    check_customer_standing,
    check_item_eligibility,
    check_return_window,
    execute_tool,
    get_order,
    lookup_customer,
)


# ── lookup / get_order ───────────────────────────────────────────
def test_lookup_customer_found():
    res = lookup_customer("CUST-001")
    assert res["found"] is True and res["customer_id"] == "CUST-001"
    assert res["orders"] and res["orders"][0]["order_id"] == "ORD-1001"


def test_lookup_customer_not_found():
    assert lookup_customer("CUST-999")["found"] is False


def test_get_order_confirms_ownership():
    assert get_order("ORD-1001", "CUST-001")["belongs_to_customer"] is True
    # messy ids still resolve correctly
    assert get_order("ord1001", "cust001")["belongs_to_customer"] is True


def test_get_order_detects_wrong_owner():
    res = get_order("ORD-2001", "CUST-001")   # ORD-2001 belongs to CUST-002
    assert res["belongs_to_customer"] is False and res["policy_ref"] == "Section 4"


def test_get_order_not_found():
    assert get_order("ORD-0000")["found"] is False


# ── read-only check tools ────────────────────────────────────────
def test_check_return_window_reports_pass():
    assert check_return_window("ORD-1001")["passed"] is True


def test_check_tools_report_missing_order():
    assert "error" in check_return_window("ORD-0000")
    assert "error" in calculate_refund_amount("ORD-0000")


def test_item_eligibility_lists_blocking_reasons():
    res = check_item_eligibility("ORD-9001")   # used blender
    assert res["eligible"] is False and res["blocking_reasons"]


def test_customer_standing_missing_customer():
    assert "error" in check_customer_standing("CUST-999")


def test_calculate_refund_amount_partial():
    calc = calculate_refund_amount("ORD-10001")
    assert calc["outcome"] == "APPROVE_PARTIAL"


# ── dispatch (execute_tool) ──────────────────────────────────────
def test_execute_unknown_tool():
    assert "error" in execute_tool("nope", {}, {})


def test_execute_tool_invalid_arguments():
    # missing required 'identifier' -> TypeError caught and reported
    res = execute_tool("lookup_customer", {"wrong": "x"}, {})
    assert "error" in res


def test_execute_tool_routes_context_tools():
    ctx = {"session_id": "d", "verified_customer_id": "CUST-001"}
    res = execute_tool("process_refund", {"order_id": "ORD-1001", "amount": 149.99, "reason": "ok"}, ctx)
    assert res["success"] is True


# ── guarded finalize tools ───────────────────────────────────────
def ctx_for(cust):
    return {"session_id": "t", "verified_customer_id": cust}


def test_process_refund_blocked_when_policy_denies():
    res = execute_tool("process_refund", {"order_id": "ORD-2001", "amount": 89.0, "reason": "x"},
                       ctx_for("CUST-002"))
    assert res["success"] is False and res.get("blocked") is True


def test_process_refund_is_amount_authoritative():
    # Model asks for an inflated amount; policy fixes it to the true price.
    res = execute_tool("process_refund", {"order_id": "ORD-1001", "amount": 999.0, "reason": "x"},
                       ctx_for("CUST-001"))
    assert res["success"] is True and res["amount_refunded"] == 149.99


def test_process_refund_forces_partial_amount():
    res = execute_tool("process_refund", {"order_id": "ORD-10001", "amount": 129.0, "reason": "x"},
                       ctx_for("CUST-010"))
    assert res["outcome"] == "APPROVE_PARTIAL" and res["amount_refunded"] == round(129.0 * 0.85, 2)


def test_process_refund_blocked_on_ownership_mismatch():
    res = execute_tool("process_refund", {"order_id": "ORD-9001", "amount": 62.0, "reason": "x"},
                       ctx_for("CUST-001"))   # ORD-9001 is CUST-009's
    assert res["success"] is False and res["policy_ref"] == "Section 4"


def test_deny_refund_blocked_when_policy_approves():
    res = execute_tool("deny_refund", {"order_id": "ORD-1001", "reason": "x", "policy_ref": "Section 1"},
                       ctx_for("CUST-001"))
    assert res["success"] is False and res.get("blocked") is True


def test_deny_refund_allowed_and_cites_authoritative_section():
    res = execute_tool("deny_refund", {"order_id": "ORD-2001", "reason": "past window", "policy_ref": "Section 99"},
                       ctx_for("CUST-002"))
    assert res["success"] is True and res["policy_ref"] == "Section 1"   # tool overrides the citation


def test_escalate_blocked_when_policy_denies():
    res = execute_tool("escalate_to_human", {"order_id": "ORD-2001", "reason": "x", "policy_ref": "Section 1"},
                       ctx_for("CUST-002"))
    assert res.get("blocked") is True


def test_escalate_allowed_for_high_value():
    res = execute_tool("escalate_to_human", {"order_id": "ORD-5001", "reason": "high value", "policy_ref": "Section 10"},
                       ctx_for("CUST-005"))
    assert res["success"] is True and res["outcome"] == "ESCALATE" and "ticket_id" in res


def test_processed_refund_then_blocked_as_duplicate():
    ok = execute_tool("process_refund", {"order_id": "ORD-1001", "amount": 149.99, "reason": "x"},
                      ctx_for("CUST-001"))
    assert ok["success"] is True
    again = execute_tool("process_refund", {"order_id": "ORD-1001", "amount": 149.99, "reason": "x"},
                         ctx_for("CUST-001"))
    assert again["success"] is False and again["policy_ref"] == "Section 8"


def test_finalize_writes_to_ledger():
    before = len(store.refund_ledger)
    execute_tool("deny_refund", {"order_id": "ORD-2001", "reason": "past window", "policy_ref": "Section 1"},
                 ctx_for("CUST-002"))
    assert len(store.refund_ledger) == before + 1


# ── tool schemas ─────────────────────────────────────────────────
def test_tool_schemas_cover_every_registered_tool():
    names = {t["function"]["name"] for t in TOOL_SCHEMAS}
    assert names == {
        "lookup_customer", "get_order", "check_return_window", "check_item_eligibility",
        "check_customer_standing", "check_high_value", "calculate_refund_amount",
        "process_refund", "deny_refund", "escalate_to_human",
    }


def test_tool_schemas_are_well_formed():
    for t in TOOL_SCHEMAS:
        assert t["type"] == "function"
        fn = t["function"]
        assert fn["name"] and fn["description"]
        assert fn["parameters"]["type"] == "object"
        assert "properties" in fn["parameters"]
