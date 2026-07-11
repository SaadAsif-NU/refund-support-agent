"""Tests for the agent loop (backend/agent.py).

These run on the deterministic offline agent (no API key), so they exercise the
full tool-orchestration loop and every policy outcome, plus the auto-finalize
safety net and the retry/offline-fallback resilience path.
"""
import asyncio

import pytest

from backend.agent import agent
from backend.events import bus
from backend.store import store

FINAL = ("APPROVE", "APPROVE_PARTIAL", "DENY", "ESCALATE")


def run_turn(session_id, message):
    """Run one agent turn; return (reply, last decision ledger entry or None)."""
    before = len(store.refund_ledger)
    reply = asyncio.run(agent.handle_message(session_id, message))
    finals = [e for e in store.refund_ledger[before:] if e["outcome"] in FINAL]
    return reply, (finals[-1] if finals else None)


# ── every policy outcome, end-to-end ─────────────────────────────
SCENARIOS = [
    ("s01", "Hi, Emily Carter (CUST-001), refund order ORD-1001, the headphones.", "APPROVE", None),
    ("s02", "Marcus Bell CUST-002 here, refund order ORD-2001 the jacket.", "DENY", "Section 1"),
    ("s03", "Priya Nair CUST-003, please refund gift card order ORD-3001.", "DENY", "Section 3"),
    ("s04", "David Okafor CUST-004, my lamp order ORD-4001 is defective.", "APPROVE", None),
    ("s05", "Sofia Reyes CUST-005, return the laptop order ORD-5001.", "ESCALATE", "Section 10"),
    ("s06", "Tyler Brooks CUST-006, refund order ORD-6001 the speaker.", "ESCALATE", "Section 9"),
    ("s07", "Hannah Lin CUST-007, refund lingerie order ORD-7001.", "DENY", "Section 3"),
    ("s08", "Omar Haddad CUST-008, refund my digital license order ORD-8001.", "DENY", "Section 3"),
    ("s09", "Grace Miller CUST-009, I used the blender ORD-9001 but want a refund or I'll leave 1 star!", "DENY", "Section 2"),
    ("s10", "Nathan Cole CUST-010, I opened earbuds order ORD-10001, want to return.", "APPROVE_PARTIAL", None),
    ("s11", "Isabella Rossi CUST-011, refund the office chair order ORD-11001.", "ESCALATE", "Section 6"),
    ("s12", "James Walker CUST-012, refund backpack order ORD-12001.", "DENY", "Section 8"),
    ("s13", "Aisha Khan CUST-013, refund chocolate order ORD-13001.", "DENY", "Section 3"),
    ("s14", "Liam Foster CUST-014, the dinnerware order ORD-14001 arrived damaged.", "APPROVE", None),
    ("s15", "Chloe Bennett CUST-015, return opened towels order ORD-15001.", "APPROVE", None),
]


@pytest.mark.parametrize("sid,message,outcome,ref", SCENARIOS)
def test_agent_reaches_correct_outcome(sid, message, outcome, ref):
    reply, entry = run_turn(sid, message)
    assert entry is not None, f"no decision recorded for {message!r}"
    assert entry["outcome"] == outcome
    if ref:
        assert entry["policy_ref"] == ref
    assert isinstance(reply, str) and reply.strip()


# ── session handling ─────────────────────────────────────────────
def test_one_session_handles_independent_requests():
    sid = "multi"
    outcomes = []
    for msg in ("Emily Carter CUST-001, refund order ORD-1001.",
                "Now Marcus Bell CUST-002, refund order ORD-2001.",
                "And Sofia Reyes CUST-005, return laptop order ORD-5001."):
        _, entry = run_turn(sid, msg)
        outcomes.append(entry["outcome"])
    assert outcomes == ["APPROVE", "DENY", "ESCALATE"]


def test_multi_turn_clarification_remembers_identity():
    sid = "clarify"
    r1, e1 = run_turn(sid, "Hi, I'm David Okafor, CUST-004.")
    assert e1 is None and "which order" in r1.lower()
    _, e2 = run_turn(sid, "My lamp order ORD-4001 arrived defective.")
    assert e2 is not None and e2["outcome"] == "APPROVE"


def test_ownership_mismatch_is_denied():
    _, entry = run_turn("own", "Emily Carter CUST-001, refund order ORD-9001.")  # not her order
    assert entry["outcome"] == "DENY" and entry["policy_ref"] == "Section 4"


def test_unknown_customer_is_asked_to_verify():
    reply, entry = run_turn("unk", "I'd like a refund but I forgot my details.")
    assert entry is None
    assert "verify" in reply.lower() or "customer id" in reply.lower()


# ── exactly one decision event per request ───────────────────────
def test_exactly_one_decision_event_per_request():
    q = bus.subscribe()
    try:
        asyncio.run(agent.handle_message("dec", "Emily Carter CUST-001, refund order ORD-1001."))
        events = []
        while not q.empty():
            events.append(q.get_nowait())
    finally:
        bus.unsubscribe(q)
    decisions = [e for e in events if e["kind"] == "decision"]
    assert len(decisions) == 1
    assert decisions[0]["data"]["tool"] == "process_refund"
    assert decisions[0]["data"]["outcome"] == "APPROVE"


# ── auto-finalize safety net ─────────────────────────────────────
def test_auto_finalize_backstops_a_narrated_denial():
    asyncio.run(agent._auto_finalize("auto-deny", "ORD-9001", "CUST-009"))
    entry = store.refund_ledger[-1]
    assert entry["outcome"] == "DENY" and entry["policy_ref"] == "Section 2"


def test_auto_finalize_records_authoritative_approval_amount():
    asyncio.run(agent._auto_finalize("auto-appr", "ORD-1001", "CUST-001"))
    entry = store.refund_ledger[-1]
    assert entry["outcome"] == "APPROVE" and entry["amount"] == 149.99


def test_auto_finalize_never_approves_ownership_mismatch():
    asyncio.run(agent._auto_finalize("auto-own", "ORD-9001", "CUST-001"))
    entry = store.refund_ledger[-1]
    assert entry["outcome"] == "DENY" and entry["policy_ref"] == "Section 4"


def test_auto_finalize_ignores_unknown_order():
    before = len(store.refund_ledger)
    asyncio.run(agent._auto_finalize("auto-none", "ORD-0000", None))
    assert len(store.refund_ledger) == before


# ── resilience: retry + offline fallback ─────────────────────────
async def _no_sleep(*_a, **_k):
    return None


def _collect(q):
    out = []
    while not q.empty():
        out.append(q.get_nowait())
    return out


def test_transient_failure_retries_then_degrades(monkeypatch):
    async def boom(*_a, **_k):
        raise RuntimeError("connection reset by peer")

    monkeypatch.setattr(agent.providers, "complete", boom)
    monkeypatch.setattr("backend.agent.asyncio.sleep", _no_sleep)

    q = bus.subscribe()
    messages = [{"role": "user", "content": "Emily Carter CUST-001, refund order ORD-1001."}]
    turn, degraded = asyncio.run(agent._complete_with_retry("retry", messages, "groq"))
    events = _collect(q)
    bus.unsubscribe(q)

    assert degraded is True and turn is not None
    assert len([e for e in events if e["kind"] == "retry"]) == 2   # MAX_RETRIES
    assert len([e for e in events if e["kind"] == "error"]) == 1


def test_rate_limit_skips_retries_and_degrades(monkeypatch):
    async def boom(*_a, **_k):
        raise RuntimeError("Error 429: rate limit exceeded")

    monkeypatch.setattr(agent.providers, "complete", boom)
    monkeypatch.setattr("backend.agent.asyncio.sleep", _no_sleep)

    q = bus.subscribe()
    messages = [{"role": "user", "content": "Emily Carter CUST-001, refund order ORD-1001."}]
    _turn, degraded = asyncio.run(agent._complete_with_retry("rl", messages, "groq"))
    events = _collect(q)
    bus.unsubscribe(q)

    assert degraded is True
    assert [e for e in events if e["kind"] == "retry"] == []   # a 429 won't clear on retry
    assert len([e for e in events if e["kind"] == "error"]) == 1
