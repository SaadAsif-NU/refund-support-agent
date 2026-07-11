"""Reasoning event bus.

A tiny async pub/sub used to stream the agent's live reasoning (thoughts,
tool calls, tool results, retries, decisions) to any connected admin
dashboards. New subscribers receive a replay of recent events so a dashboard
opened mid-conversation isn't blank.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

MAX_HISTORY = 300


class EventBus:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue] = set()
        self._history: list[dict[str, Any]] = []
        self._seq = 0

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subscribers.discard(q)

    def history(self) -> list[dict[str, Any]]:
        return list(self._history)

    async def emit(self, session_id: str, kind: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Publish one reasoning event. `kind` is one of:
        session_start | thought | tool_call | tool_result | retry | error |
        decision | assistant_message | session_end.
        """
        self._seq += 1
        event = {
            "seq": self._seq,
            "session_id": session_id,
            "kind": kind,
            "data": data or {},
            "timestamp": datetime.now().isoformat(timespec="milliseconds"),
        }
        self._history.append(event)
        if len(self._history) > MAX_HISTORY:
            self._history = self._history[-MAX_HISTORY:]
        for q in list(self._subscribers):
            q.put_nowait(event)
        return event


bus = EventBus()
