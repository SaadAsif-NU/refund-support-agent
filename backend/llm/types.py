"""Normalized message shapes (provider-independent).

Every provider adapter returns an `AssistantTurn`, so the agent loop reasons
over one shape regardless of which backend produced it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class AssistantTurn:
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
