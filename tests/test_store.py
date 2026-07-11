"""Unit tests for the CRM store and its durable refund ledger (backend/store.py)."""
import pytest

from backend.store import Store, store


def test_loads_15_customers():
    assert len(store.all_customers()) == 15


# ── find_customer ────────────────────────────────────────────────
def test_find_by_id_and_email():
    assert store.find_customer("CUST-001")["id"] == "CUST-001"
    assert store.find_customer("emily.carter@example.com")["id"] == "CUST-001"


@pytest.mark.parametrize("form", ["CUST-001", "cust-001", "cust001", "CUST 001", " Cust-001 "])
def test_find_customer_tolerant_of_format(form):
    assert store.find_customer(form)["id"] == "CUST-001"


@pytest.mark.parametrize("bad", ["", "cust999", "nobody@nowhere.com", None])
def test_find_customer_unknown_is_none(bad):
    assert store.find_customer(bad) is None


# ── get_order ────────────────────────────────────────────────────
@pytest.mark.parametrize("form", ["ORD-1001", "ord-1001", "ord1001", "ORD 1001"])
def test_get_order_tolerant_of_format(form):
    assert store.get_order(form)["id"] == "ORD-1001"


@pytest.mark.parametrize("bad", ["", "ORD-0000", None])
def test_get_order_unknown_is_none(bad):
    assert store.get_order(bad) is None


def test_order_carries_customer_backreference():
    assert store.get_order("ORD-1001")["_customer_id"] == "CUST-001"
    assert store.get_order("ORD-2001")["_customer_id"] == "CUST-002"


# ── days_since_delivery ──────────────────────────────────────────
def test_days_since_delivery_materialized():
    assert store.days_since_delivery(store.get_order("ORD-1001")) == 8


def test_days_since_delivery_none_when_undelivered():
    assert store.days_since_delivery(store.get_order("ORD-11001")) is None


# ── record_refund ────────────────────────────────────────────────
def test_record_refund_appends_to_ledger():
    entry = {"order_id": "ORD-1001", "outcome": "APPROVE", "amount": 149.99}
    store.record_refund(entry)
    assert store.refund_ledger[-1] is entry


def test_approved_refund_flips_already_refunded():
    assert store.get_order("ORD-1001")["already_refunded"] is False
    store.record_refund({"order_id": "ORD-1001", "outcome": "APPROVE", "amount": 149.99})
    assert store.get_order("ORD-1001")["already_refunded"] is True


def test_denial_does_not_flip_already_refunded():
    store.record_refund({"order_id": "ORD-1001", "outcome": "DENY", "amount": 0.0})
    assert store.get_order("ORD-1001")["already_refunded"] is False


# ── all_customers ────────────────────────────────────────────────
def test_all_customers_have_materialized_orders():
    for cust in store.all_customers():
        for o in cust["orders"]:
            assert "_customer_id" in o
            assert "delivered_date" in o


# ── durable ledger persistence (survives restarts) ───────────────
def test_ledger_persists_to_disk(tmp_path):
    ledger_file = tmp_path / "ledger.json"
    s = Store(ledger_file=ledger_file)
    s.record_refund({"order_id": "ORD-1001", "outcome": "APPROVE", "amount": 149.99})
    assert ledger_file.exists()


def test_ledger_replayed_on_reload(tmp_path):
    ledger_file = tmp_path / "ledger.json"
    Store(ledger_file=ledger_file).record_refund(
        {"order_id": "ORD-1001", "outcome": "APPROVE", "amount": 149.99})

    # A brand-new store reading the same file rehydrates ledger + order state.
    fresh = Store(ledger_file=ledger_file)
    assert len(fresh.refund_ledger) == 1
    assert fresh.get_order("ORD-1001")["already_refunded"] is True


def test_missing_ledger_file_starts_empty(tmp_path):
    assert Store(ledger_file=tmp_path / "does-not-exist.json").refund_ledger == []


def test_corrupt_ledger_file_is_ignored(tmp_path):
    bad = tmp_path / "corrupt.json"
    bad.write_text("{ this is not valid json")
    assert Store(ledger_file=bad).refund_ledger == []
