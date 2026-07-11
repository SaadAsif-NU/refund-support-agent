"""Unit tests for the reasoning event bus (backend/events.py)."""
import asyncio

from backend.events import MAX_HISTORY, bus


def test_emit_builds_the_documented_envelope():
    ev = asyncio.run(bus.emit("s1", "thought", {"text": "hi"}))
    assert ev["session_id"] == "s1"
    assert ev["kind"] == "thought"
    assert ev["data"] == {"text": "hi"}
    assert set(ev) >= {"seq", "session_id", "kind", "data", "timestamp"}


def test_emit_defaults_empty_data():
    ev = asyncio.run(bus.emit("s1", "session_end"))
    assert ev["data"] == {}


def test_emit_appends_to_history():
    asyncio.run(bus.emit("s1", "thought", {"text": "a"}))
    asyncio.run(bus.emit("s1", "decision", {"outcome": "APPROVE"}))
    kinds = [e["kind"] for e in bus.history()]
    assert kinds == ["thought", "decision"]


def test_seq_is_monotonic():
    a = asyncio.run(bus.emit("s", "thought"))
    b = asyncio.run(bus.emit("s", "thought"))
    assert b["seq"] == a["seq"] + 1


def test_subscriber_receives_events():
    q = bus.subscribe()
    ev = asyncio.run(bus.emit("s", "tool_call", {"tool": "get_order"}))
    assert q.get_nowait()["seq"] == ev["seq"]
    bus.unsubscribe(q)


def test_multiple_subscribers_all_receive():
    q1, q2 = bus.subscribe(), bus.subscribe()
    asyncio.run(bus.emit("s", "thought"))
    assert q1.get_nowait()["kind"] == "thought"
    assert q2.get_nowait()["kind"] == "thought"
    bus.unsubscribe(q1)
    bus.unsubscribe(q2)


def test_unsubscribe_stops_delivery():
    q = bus.subscribe()
    bus.unsubscribe(q)
    asyncio.run(bus.emit("s", "thought"))
    assert q.empty()


def test_history_returned_copy_is_independent():
    asyncio.run(bus.emit("s", "thought"))
    snapshot = bus.history()
    snapshot.clear()
    assert len(bus.history()) == 1   # internal history unaffected


def test_history_is_capped():
    async def emit_many(n):
        for i in range(n):
            await bus.emit("s", "thought", {"i": i})

    asyncio.run(emit_many(MAX_HISTORY + 5))
    hist = bus.history()
    assert len(hist) == MAX_HISTORY
    # Oldest 5 were dropped; seq numbering is preserved.
    assert hist[0]["seq"] == 6
    assert hist[-1]["seq"] == MAX_HISTORY + 5
