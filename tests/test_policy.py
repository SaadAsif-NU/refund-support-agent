"""Unit tests for the deterministic policy engine (backend/policy.py).

Real orders from the CRM cover the common cases; synthetic order dicts pin down
the exact boundaries (window edges, high-value threshold, fraud limit).
"""
import pytest

from backend import policy
from backend.store import store


def order(oid):
    return store.get_order(oid)


def days(oid):
    return store.days_since_delivery(order(oid))


# ── check_window (Section 1 standard / Section 7 defective / Section 6 undelivered) ──
def test_window_within_standard():
    assert policy.check_window(order("ORD-1001"), days("ORD-1001"))["passed"] is True   # 8 days


def test_window_outside_standard():
    res = policy.check_window(order("ORD-2001"), days("ORD-2001"))                       # 47 days
    assert res["passed"] is False and res["policy_ref"] == "Section 1"


def test_window_defective_gets_90_days():
    res = policy.check_window(order("ORD-4001"), days("ORD-4001"))                       # 60 days, defective
    assert res["passed"] is True and res["policy_ref"] == "Section 7"


def test_window_undelivered_fails_section_6():
    res = policy.check_window(order("ORD-11001"), None)
    assert res["passed"] is False and res["policy_ref"] == "Section 6"


@pytest.mark.parametrize("condition,d,expected", [
    ("unused", 30, True),    # exactly at the 30-day edge
    ("unused", 31, False),   # one day past
    ("defective", 90, True), # exactly at the 90-day defective edge
    ("defective", 91, False),
])
def test_window_boundaries(condition, d, expected):
    synthetic = {"condition": condition}
    assert policy.check_window(synthetic, d)["passed"] is expected


# ── check_category (Section 3) ───────────────────────────────────
@pytest.mark.parametrize("oid", ["ORD-3001", "ORD-13001", "ORD-7001", "ORD-8001"])
def test_non_refundable_categories(oid):
    # gift card, perishable, intimate/final-sale, downloaded-digital-used
    res = policy.check_category(order(oid))
    assert res["passed"] is False and res["policy_ref"] == "Section 3"


def test_category_normal_item_passes():
    assert policy.check_category(order("ORD-1001"))["passed"] is True


def test_category_final_sale_blocks():
    assert policy.check_category({"category": "home", "final_sale": True})["passed"] is False


# ── check_condition (Section 2 used / Section 7 defective) ────────
def test_condition_used_not_eligible():
    res = policy.check_condition(order("ORD-9001"))
    assert res["passed"] is False and res["policy_ref"] == "Section 2"


def test_condition_damaged_is_eligible():
    res = policy.check_condition(order("ORD-14001"))
    assert res["passed"] is True and res["policy_ref"] == "Section 7"


def test_condition_opened_is_resalable():
    assert policy.check_condition(order("ORD-10001"))["passed"] is True


# ── check_status (Section 6) ─────────────────────────────────────
def test_status_delivered_passes():
    assert policy.check_status(order("ORD-1001"))["passed"] is True


def test_status_not_delivered_fails():
    res = policy.check_status(order("ORD-11001"))                                        # shipped
    assert res["passed"] is False and res["policy_ref"] == "Section 6"


# ── check_duplicate (Section 8) ──────────────────────────────────
def test_duplicate_blocks_already_refunded():
    res = policy.check_duplicate(order("ORD-12001"))
    assert res["passed"] is False and res["policy_ref"] == "Section 8"


def test_duplicate_ok_for_fresh_order():
    assert policy.check_duplicate(order("ORD-1001"))["passed"] is True


# ── check_fraud (Section 9) ──────────────────────────────────────
def test_fraud_flagged_customer_escalates():
    assert policy.check_fraud(store.find_customer("CUST-006"))["escalate"] is True


def test_fraud_clean_customer_ok():
    assert policy.check_fraud(store.find_customer("CUST-001"))["escalate"] is False


@pytest.mark.parametrize("count,flagged,expected", [
    (3, False, False),   # exactly the limit is fine
    (4, False, True),    # over the limit escalates
    (0, True, True),     # flagged escalates regardless of count
])
def test_fraud_boundaries(count, flagged, expected):
    cust = {"refunds_last_12_months": count, "flagged_for_review": flagged}
    assert policy.check_fraud(cust)["escalate"] is expected


# ── check_high_value (Section 10) ────────────────────────────────
def test_high_value_over_threshold_escalates():
    assert policy.check_high_value(order("ORD-5001"))["escalate"] is True                # $899


def test_high_value_under_threshold_ok():
    assert policy.check_high_value(order("ORD-1001"))["escalate"] is False               # $149.99


@pytest.mark.parametrize("amount,expected", [(500.0, False), (500.01, True)])
def test_high_value_boundary(amount, expected):
    assert policy.check_high_value({"amount": amount})["escalate"] is expected


# ── evaluate (authoritative end-to-end verdict, in precedence) ───
@pytest.mark.parametrize("oid,kind,ref", [
    ("ORD-1001", "APPROVE", None),         # within window, resalable
    ("ORD-2001", "DENY", "Section 1"),     # outside window
    ("ORD-3001", "DENY", "Section 3"),     # gift card
    ("ORD-4001", "APPROVE", None),         # defective, 90-day
    ("ORD-5001", "ESCALATE", "Section 10"),# high value
    ("ORD-6001", "ESCALATE", "Section 9"), # fraud guard
    ("ORD-9001", "DENY", "Section 2"),     # used
    ("ORD-11001", "ESCALATE", "Section 6"),# undelivered
    ("ORD-12001", "DENY", "Section 8"),    # already refunded
    ("ORD-13001", "DENY", "Section 3"),    # perishable
])
def test_evaluate_outcomes(oid, kind, ref):
    o = order(oid)
    c = store.find_customer(o["_customer_id"])
    verdict = policy.evaluate(o, c, store.days_since_delivery(o))
    assert verdict["kind"] == kind
    if ref:
        assert verdict["policy_ref"] == ref


def test_evaluate_enforces_ownership_section_4():
    o = order("ORD-9001")                                                                # belongs to CUST-009
    c = store.find_customer(o["_customer_id"])
    verdict = policy.evaluate(o, c, store.days_since_delivery(o), verified_customer_id="CUST-001")
    assert verdict["kind"] == "DENY" and verdict["policy_ref"] == "Section 4"


# ── compute_refund_amount (Section 5 / Section 7) ────────────────
def test_partial_refund_on_opened_electronics():
    calc = policy.compute_refund_amount(order("ORD-10001"))                              # opened earbuds $129
    assert calc["outcome"] == "APPROVE_PARTIAL"
    assert calc["restocking_fee"] == round(129.0 * 0.15, 2)
    assert calc["refund_amount"] == round(129.0 * 0.85, 2)


def test_full_refund_no_fee_on_opened_non_electronics():
    calc = policy.compute_refund_amount(order("ORD-15001"))                              # opened towels (home)
    assert calc["outcome"] == "APPROVE" and calc["restocking_fee"] == 0.0
    assert calc["refund_amount"] == 48.0


def test_full_refund_on_defective_cites_section_7():
    calc = policy.compute_refund_amount(order("ORD-4001"))
    assert calc["restocking_fee"] == 0.0 and calc["policy_ref"] == "Section 7"
