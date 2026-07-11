"""WebSocket endpoint tests: the customer chat channel and the admin stream.

Driven through TestClient.websocket_connect, which runs the real async handlers
on the app's event loop (so the full agent loop executes end-to-end).
"""
import asyncio

from backend.agent import agent


# ── /ws/chat ─────────────────────────────────────────────────────
def _drive_chat(client, message, session_id="ws"):
    """Send one chat message and return the final 'reply' frame."""
    with client.websocket_connect("/ws/chat") as chat:
        chat.send_json({"session_id": session_id, "message": message})
        for _ in range(6):
            frame = chat.receive_json()
            if frame["type"] == "reply":
                return frame
    raise AssertionError("no reply frame received")


def test_chat_emits_thinking_status_then_reply(client):
    with client.websocket_connect("/ws/chat") as chat:
        chat.send_json({"session_id": "ws-1",
                        "message": "Hi, Emily Carter CUST-001, refund order ORD-1001."})
        first = chat.receive_json()
        assert first["type"] == "status" and first["state"] == "thinking"
        reply = None
        for _ in range(5):
            frame = chat.receive_json()
            if frame["type"] == "reply":
                reply = frame
                break
        assert reply is not None
        assert reply["text"].strip()
        assert reply["outcome"] == "APPROVE"


def test_chat_denial_carries_deny_outcome(client):
    reply = _drive_chat(client, "Marcus Bell CUST-002, refund order ORD-2001.", "ws-2")
    assert reply["outcome"] == "DENY"


def test_chat_updates_the_ledger(client):
    _drive_chat(client, "Emily Carter CUST-001, refund order ORD-1001.", "ws-3")
    ledger = client.get("/api/ledger").json()["ledger"]
    assert len(ledger) == 1 and ledger[0]["outcome"] == "APPROVE"


# ── /ws/admin ────────────────────────────────────────────────────
def test_admin_replays_reasoning_history(client):
    # Generate activity first; a freshly-connected admin must replay it.
    asyncio.run(agent.handle_message("hist-1", "Emily Carter CUST-001, refund order ORD-1001."))

    from backend.events import bus
    history_len = len(bus.history())
    assert history_len > 0

    # Read exactly the replayed count so we never block waiting on live events.
    with client.websocket_connect("/ws/admin") as admin:
        events = [admin.receive_json() for _ in range(history_len)]

    # Every event has the documented envelope.
    for e in events:
        assert set(e) >= {"seq", "session_id", "kind", "data", "timestamp"}
    kinds = {e["kind"] for e in events}
    assert events[0]["kind"] == "session_start"
    assert {"tool_call", "decision", "session_end"} <= kinds
