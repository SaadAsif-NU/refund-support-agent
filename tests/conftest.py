"""Shared test fixtures.

The CRM store, durable refund ledger, agent session memory, and reasoning event
bus are all process-wide singletons that the agent mutates. Reset them before
every test so cases are independent and order-insensitive.

Crucially, the refund ledger is disk-backed (persisted to
`backend/data/refund_ledger.json` and replayed on load), so each test is pointed
at its own temp ledger file — tests never read or write the real one.
"""
import pytest
from fastapi.testclient import TestClient

from backend.agent import agent
from backend.events import bus
from backend.main import app
from backend.store import store


@pytest.fixture(autouse=True)
def reset_state(tmp_path):
    # Isolate the durable ledger at a per-test temp path, then reload: this
    # re-materializes orders (clearing already_refunded flips) and reads the
    # empty temp ledger, so every test starts from clean seed data.
    store._ledger_file = tmp_path / "refund_ledger.json"
    store._load()
    agent._sessions.clear()       # drop per-session conversation history
    bus._history.clear()          # drop replayable reasoning history
    bus._subscribers.clear()
    bus._seq = 0
    yield


@pytest.fixture
def client():
    """A FastAPI TestClient with app startup/shutdown handled."""
    with TestClient(app) as c:
        yield c
