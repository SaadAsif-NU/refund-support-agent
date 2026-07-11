"""Multi-provider dispatch.

`ProviderManager.complete` is the one normalized entry point the whole app is
written against. It resolves which providers are available from environment
keys and routes each completion to the right adapter:

  * **mock**      - deterministic offline agent (`MockLLM`); no key required.
  * **groq/gemini/openai** - any OpenAI-compatible endpoint via the `openai` SDK.
  * **anthropic** - Claude via the official `anthropic` SDK (native Messages API;
                    the canonical history is translated at call time).

Keys live server-side only and are never sent to the browser.
"""
from __future__ import annotations

import json
import os
from typing import Any

from .mock import MockLLM
from .translate import _split_system, _to_anthropic_messages, _to_anthropic_tools
from .types import AssistantTurn, ToolCall

# Provider catalog. `kind` selects the adapter; `key_env`/`model_env` are the
# env vars a user sets. `deterministic` sends temperature=0 where the model
# accepts it (some newer models reject non-default sampling params).
PROVIDERS: dict[str, dict[str, Any]] = {
    "mock": {
        "label": "Offline agent (no key)", "kind": "mock",
        "key_env": None, "model_env": None, "default_model": "offline-mock-agent",
    },
    "groq": {
        "label": "Groq · Llama 3.3 70B", "kind": "openai", "deterministic": True,
        "key_env": "GROQ_API_KEY", "model_env": "GROQ_MODEL",
        "base_url": "https://api.groq.com/openai/v1", "default_model": "llama-3.3-70b-versatile",
    },
    "gemini": {
        "label": "Google · Gemini 2.5 Flash", "kind": "openai", "deterministic": True,
        "key_env": "GEMINI_API_KEY", "model_env": "GEMINI_MODEL",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "default_model": "gemini-2.5-flash",
    },
    "openai": {
        "label": "OpenAI · GPT-5", "kind": "openai", "deterministic": False,
        "key_env": "OPENAI_API_KEY", "model_env": "OPENAI_MODEL",
        "base_url": "https://api.openai.com/v1", "default_model": "gpt-5",
    },
    "anthropic": {
        "label": "Anthropic · Claude Opus 4.8", "kind": "anthropic", "deterministic": False,
        "key_env": "ANTHROPIC_API_KEY", "model_env": "ANTHROPIC_MODEL",
        "default_model": "claude-opus-4-8",
    },
}


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass


class ProviderManager:
    """Resolves provider availability from env and dispatches completions."""

    def __init__(self) -> None:
        _load_dotenv()
        self._mock = MockLLM()
        self._openai_clients: dict[str, Any] = {}
        self._anthropic_client: Any = None

        default = os.getenv("DEFAULT_PROVIDER", "mock").strip().lower()
        self.default_provider = default if self.is_available(default) else "mock"

    # ── availability / metadata ──────────────────────────────────
    def _key(self, provider: str) -> str:
        env = PROVIDERS.get(provider, {}).get("key_env")
        return os.getenv(env, "").strip() if env else ""

    def _model(self, provider: str) -> str:
        cfg = PROVIDERS[provider]
        env = cfg.get("model_env")
        return (os.getenv(env, "").strip() if env else "") or cfg["default_model"]

    def is_available(self, provider: str) -> bool:
        if provider == "mock":
            return True
        cfg = PROVIDERS.get(provider)
        return bool(cfg) and bool(self._key(provider))

    def resolve(self, provider: str | None) -> str:
        """Pick a usable provider: the requested one if available, else default."""
        if provider and self.is_available(provider):
            return provider
        return self.default_provider

    def catalog(self) -> list[dict[str, Any]]:
        return [{
            "id": pid, "label": cfg["label"],
            "model": self._model(pid), "available": self.is_available(pid),
        } for pid, cfg in PROVIDERS.items()]

    def describe(self, provider: str | None = None) -> dict[str, str]:
        pid = self.resolve(provider)
        return {"provider": pid, "label": PROVIDERS[pid]["label"], "model": self._model(pid)}

    def complete_offline(self, messages: list[dict[str, Any]]) -> AssistantTurn:
        """Deterministic offline completion - used as a resilience fallback when a
        cloud provider is rate-limited or unreachable mid-conversation."""
        return self._mock.complete(messages)

    # ── completion dispatch ──────────────────────────────────────
    async def complete(self, provider: str, messages: list[dict[str, Any]],
                       tools: list[dict[str, Any]]) -> AssistantTurn:
        provider = self.resolve(provider)
        kind = PROVIDERS[provider]["kind"]
        if kind == "mock":
            return self._mock.complete(messages)
        if kind == "anthropic":
            return await self._complete_anthropic(provider, messages, tools)
        return await self._complete_openai(provider, messages, tools)

    async def _complete_openai(self, provider, messages, tools) -> AssistantTurn:
        cfg = PROVIDERS[provider]
        client = self._openai_clients.get(provider)
        if client is None:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self._key(provider), base_url=cfg["base_url"])
            self._openai_clients[provider] = client

        kwargs: dict[str, Any] = {"model": self._model(provider), "messages": messages,
                                  "tools": tools, "tool_choice": "auto"}
        if cfg.get("deterministic"):
            kwargs["temperature"] = 0
        resp = await client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message
        calls: list[ToolCall] = []
        for tc in (msg.tool_calls or []):
            try:
                args = json.loads(tc.function.arguments or "{}")
            except (json.JSONDecodeError, TypeError):
                args = {}
            calls.append(ToolCall(id=tc.id, name=tc.function.name, arguments=args))
        return AssistantTurn(content=msg.content, tool_calls=calls)

    async def _complete_anthropic(self, provider, messages, tools) -> AssistantTurn:
        if self._anthropic_client is None:
            from anthropic import AsyncAnthropic
            self._anthropic_client = AsyncAnthropic(api_key=self._key(provider))

        system, convo = _split_system(messages)
        resp = await self._anthropic_client.messages.create(
            model=self._model(provider), max_tokens=2048,
            system=system, messages=_to_anthropic_messages(convo),
            tools=_to_anthropic_tools(tools), tool_choice={"type": "auto"},
        )
        content_parts: list[str] = []
        calls: list[ToolCall] = []
        for block in resp.content:
            if block.type == "text":
                content_parts.append(block.text)
            elif block.type == "tool_use":
                calls.append(ToolCall(id=block.id, name=block.name, arguments=dict(block.input)))
        content = "\n".join(content_parts) if content_parts else None
        if getattr(resp, "stop_reason", None) == "refusal":
            content = content or "I'm sorry, I'm not able to help with that request."
        return AssistantTurn(content=content, tool_calls=calls)
