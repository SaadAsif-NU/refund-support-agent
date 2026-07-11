"""WebSocket channels: customer chat and the admin reasoning stream."""
from __future__ import annotations

import asyncio
import contextlib

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..agent import agent
from ..events import bus
from ..store import store

router = APIRouter()


@router.websocket("/ws/chat")
async def ws_chat(ws: WebSocket) -> None:
    """Customer chat channel: {session_id, message} -> {type: 'reply', text}."""
    await ws.accept()
    try:
        while True:
            payload = await ws.receive_json()
            session_id = payload.get("session_id", "anon")
            message = (payload.get("message") or "").strip()
            provider = payload.get("provider")
            if not message:
                continue
            resolved = agent.providers.resolve(provider)
            await ws.send_json({"type": "status", "state": "thinking", "provider": resolved})
            before = len(store.refund_ledger)
            reply = await agent.handle_message(session_id, message, provider)
            # Attach this turn's decision outcome (if any) so the UI can badge it.
            new_entries = store.refund_ledger[before:]
            outcome = new_entries[-1]["outcome"] if new_entries else None
            await ws.send_json({"type": "reply", "text": reply, "provider": resolved, "outcome": outcome})
    except WebSocketDisconnect:
        return
    except Exception as exc:  # noqa: BLE001
        try:
            await ws.send_json({"type": "error", "text": f"Server error: {exc}"})
        except Exception:
            pass


@router.websocket("/ws/admin")
async def ws_admin(ws: WebSocket) -> None:
    """Admin dashboard channel: replays recent reasoning events, then streams live."""
    await ws.accept()
    for event in bus.history():
        await ws.send_json(event)
    queue = bus.subscribe()
    # This is a push-only loop, so also watch the socket for a disconnect —
    # whether the admin closed the tab or uvicorn closed the connection during
    # graceful shutdown. Without this the loop blocks on queue.get() forever,
    # leaking the connection and stalling shutdown ("Waiting for background
    # tasks to complete").
    disconnect = asyncio.ensure_future(ws.receive())
    try:
        while not disconnect.done():
            nxt = asyncio.ensure_future(queue.get())
            done, _ = await asyncio.wait(
                {nxt, disconnect}, return_when=asyncio.FIRST_COMPLETED
            )
            if nxt in done:
                await ws.send_json(nxt.result())
            else:
                nxt.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await nxt
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        disconnect.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await disconnect
        bus.unsubscribe(queue)
