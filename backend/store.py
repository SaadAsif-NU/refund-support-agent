"""CRM data store.

Loads the mock customer/order database from JSON and materializes concrete
dates from stored day-offsets, so every demo scenario stays valid no matter
when the app is run.

The refund ledger is the durable source of truth for refund decisions: it is
persisted to `data/refund_ledger.json` and replayed on startup, so approved
refunds (and the duplicate guard that depends on them) survive restarts rather
than living only in process memory. The seed catalog stays immutable; order
refund-state is derived from the ledger.
"""
from __future__ import annotations

import json
import os
import re
import threading
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Optional


def _squash(value: str) -> str:
    """Normalize an id for tolerant matching: lowercase, alphanumerics only.
    So 'CUST-001', 'cust001', 'cust 001', 'Cust-001' all map to 'cust001'."""
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())

DATA_DIR = Path(__file__).parent / "data"
CUSTOMERS_FILE = DATA_DIR / "customers.json"
POLICY_FILE = DATA_DIR / "refund_policy.md"
# Durable, append-only refund ledger — the source of truth for refund decisions,
# so they survive restarts instead of living only in process memory. `customers.json`
# stays immutable seed data; order refund-state is derived by replaying this file.
# Overridable (e.g. tests point it at a temp path) via env var.
REFUND_LEDGER_FILE = Path(os.getenv("REFUND_LEDGER_FILE", str(DATA_DIR / "refund_ledger.json")))


def _iso(days_ago: Optional[int]) -> Optional[str]:
    if days_ago is None:
        return None
    return (date.today() - timedelta(days=int(days_ago))).isoformat()


class Store:
    """Thread-safe view of the CRM plus a disk-backed, append-only refund ledger."""

    def __init__(self, ledger_file: Path | None = None) -> None:
        self._lock = threading.Lock()
        self._customers: dict[str, dict[str, Any]] = {}
        self._email_index: dict[str, str] = {}
        self._customer_squash: dict[str, str] = {}   # 'cust001' -> 'CUST-001'
        self._orders: dict[str, dict[str, Any]] = {}  # order_id -> order (with _customer_id)
        self._order_squash: dict[str, str] = {}       # 'ord1001' -> 'ORD-1001'
        self.refund_ledger: list[dict[str, Any]] = []
        self.policy_text: str = ""
        self._ledger_file = ledger_file or REFUND_LEDGER_FILE
        self._load()

    def _load(self) -> None:
        raw = json.loads(CUSTOMERS_FILE.read_text())
        for cust in raw["customers"]:
            materialized_orders = []
            for order in cust["orders"]:
                o = dict(order)
                o["order_date"] = _iso(order.get("order_date_days_ago"))
                o["delivered_date"] = _iso(order.get("delivered_days_ago"))
                o["_customer_id"] = cust["id"]
                materialized_orders.append(o)
                self._orders[o["id"]] = o
                self._order_squash[_squash(o["id"])] = o["id"]
            record = dict(cust)
            record["orders"] = materialized_orders
            self._customers[cust["id"]] = record
            self._email_index[cust["email"].lower()] = cust["id"]
            self._customer_squash[_squash(cust["id"])] = cust["id"]

        self.policy_text = POLICY_FILE.read_text()

        # Rehydrate refund state from the durable ledger (source of truth).
        self.refund_ledger = []
        self._load_ledger()

    def _load_ledger(self) -> None:
        """Load the persisted refund ledger and replay it onto order state, so
        approved refunds survive restarts. Missing/corrupt file -> empty ledger."""
        if not self._ledger_file.exists():
            return
        try:
            entries = json.loads(self._ledger_file.read_text())
        except (json.JSONDecodeError, OSError):
            return
        for entry in entries:
            self.refund_ledger.append(entry)
            self._apply_outcome(entry)

    # ── Lookups (tolerant of case, hyphens, and spacing) ───────
    def find_customer(self, identifier: str) -> Optional[dict[str, Any]]:
        """Look up a customer by id or email. Accepts 'CUST-001', 'cust001',
        'cust 001', or the email in any case."""
        if not identifier:
            return None
        key = identifier.strip()
        if key.upper() in self._customers:
            return self._customers[key.upper()]
        if key.lower() in self._email_index:
            return self._customers[self._email_index[key.lower()]]
        canonical = self._customer_squash.get(_squash(key))
        return self._customers.get(canonical) if canonical else None

    def get_order(self, order_id: str) -> Optional[dict[str, Any]]:
        """Look up an order by id, tolerant of case/hyphen/spacing."""
        if not order_id:
            return None
        key = order_id.strip()
        if key.upper() in self._orders:
            return self._orders[key.upper()]
        canonical = self._order_squash.get(_squash(key))
        return self._orders.get(canonical) if canonical else None

    def days_since_delivery(self, order: dict[str, Any]) -> Optional[int]:
        if not order.get("delivered_date"):
            return None
        delivered = datetime.fromisoformat(order["delivered_date"]).date()
        return (date.today() - delivered).days

    # ── Ledger (mutations) ─────────────────────────────────────
    def record_refund(self, entry: dict[str, Any]) -> None:
        """Append a decision to the ledger, reflect it onto order state, and
        persist to disk — all under the lock so concurrent writes are serialized."""
        with self._lock:
            self.refund_ledger.append(entry)
            self._apply_outcome(entry)
            self._persist_ledger()

    def _apply_outcome(self, entry: dict[str, Any]) -> None:
        """Reflect a ledger entry onto derived order state (the duplicate guard)."""
        if entry.get("outcome") in ("APPROVE", "APPROVE_PARTIAL"):
            order = self.get_order(entry.get("order_id", ""))
            if order:
                order["already_refunded"] = True

    def _persist_ledger(self) -> None:
        """Write the ledger to disk atomically (temp file + os.replace) so a crash
        mid-write can never corrupt or truncate the durable record."""
        self._ledger_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._ledger_file.parent / (self._ledger_file.name + ".tmp")
        tmp.write_text(json.dumps(self.refund_ledger, indent=2))
        os.replace(tmp, self._ledger_file)

    def all_customers(self) -> list[dict[str, Any]]:
        return list(self._customers.values())


# Single shared instance used across the app.
store = Store()
