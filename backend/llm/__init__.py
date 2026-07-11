"""Multi-provider LLM layer.

One normalized interface (`ProviderManager.complete`) backs every provider and
the whole app is written against it. The layer is split into:

  * types     - the provider-independent `AssistantTurn` / `ToolCall` shapes
  * providers - the `PROVIDERS` catalog and `ProviderManager` dispatch
  * translate - OpenAI-canonical -> Anthropic Messages API conversion
  * mock      - the deterministic offline agent (`MockLLM`)

The frontend lets the user pick a provider per message; only providers whose API
key is present in the environment are selectable (mock is always available).
Keys live server-side only and are never sent to the browser.

Everything previously importable from the flat `llm` module is re-exported here.
"""
from __future__ import annotations

from .mock import MockLLM
from .providers import PROVIDERS, ProviderManager
from .translate import _split_system, _to_anthropic_messages, _to_anthropic_tools
from .types import AssistantTurn, ToolCall

__all__ = [
    "ProviderManager",
    "PROVIDERS",
    "AssistantTurn",
    "ToolCall",
    "MockLLM",
    "_split_system",
    "_to_anthropic_messages",
    "_to_anthropic_tools",
]
