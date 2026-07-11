"""Unit tests for the multi-provider LLM layer (backend/llm/).

Covers provider availability/resolution, the deterministic offline MockLLM, and
the OpenAI-canonical -> Anthropic Messages API translation.
"""
import json

from backend.llm import (
    MockLLM,
    ProviderManager,
    _split_system,
    _to_anthropic_messages,
    _to_anthropic_tools,
)
from backend.tools import TOOL_SCHEMAS

_KEY_ENVS = ["GROQ_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
             "GROQ_MODEL", "DEFAULT_PROVIDER"]


def _clean_env(monkeypatch):
    """Neutralise ambient keys so availability is deterministic.

    load_dotenv() uses override=False, so these empty values win over any .env.
    """
    for k in _KEY_ENVS:
        monkeypatch.setenv(k, "")


# ── availability / resolution ────────────────────────────────────
def test_only_mock_available_without_keys(monkeypatch):
    _clean_env(monkeypatch)
    pm = ProviderManager()
    assert pm.is_available("mock") is True
    assert pm.is_available("groq") is False
    assert pm.default_provider == "mock"


def test_catalog_reports_all_five_providers(monkeypatch):
    _clean_env(monkeypatch)
    pm = ProviderManager()
    catalog = pm.catalog()
    assert {c["id"] for c in catalog} == {"mock", "groq", "gemini", "openai", "anthropic"}
    assert next(c for c in catalog if c["id"] == "mock")["available"] is True


def test_key_makes_provider_available(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test-key")
    pm = ProviderManager()
    assert pm.is_available("groq") is True
    assert pm.resolve("groq") == "groq"


def test_resolve_falls_back_to_default(monkeypatch):
    _clean_env(monkeypatch)
    pm = ProviderManager()
    assert pm.resolve("groq") == "mock"   # requested but unavailable
    assert pm.resolve(None) == "mock"


def test_default_provider_env_respected(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test-key")
    monkeypatch.setenv("DEFAULT_PROVIDER", "groq")
    assert ProviderManager().default_provider == "groq"


def test_default_provider_falls_back_when_unavailable(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("DEFAULT_PROVIDER", "openai")   # no key -> unusable
    assert ProviderManager().default_provider == "mock"


def test_model_override_via_env(monkeypatch):
    _clean_env(monkeypatch)
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test-key")
    monkeypatch.setenv("GROQ_MODEL", "custom-model-x")
    pm = ProviderManager()
    model = next(c for c in pm.catalog() if c["id"] == "groq")["model"]
    assert model == "custom-model-x"


def test_describe_returns_label_and_model(monkeypatch):
    _clean_env(monkeypatch)
    info = ProviderManager().describe()
    assert set(info) == {"provider", "label", "model"} and info["provider"] == "mock"


# ── MockLLM (offline deterministic agent) ────────────────────────
def test_mock_asks_for_verification_without_identity():
    turn = MockLLM().complete([{"role": "user", "content": "I want a refund please"}])
    assert turn.tool_calls == []
    assert "verify" in (turn.content or "").lower()


def test_mock_first_step_looks_up_customer():
    turn = MockLLM().complete([{"role": "user",
                                "content": "Emily Carter CUST-001, refund order ORD-1001"}])
    assert turn.tool_calls and turn.tool_calls[0].name == "lookup_customer"
    assert turn.tool_calls[0].arguments["identifier"] == "CUST-001"


def test_mock_infers_customer_from_order_alone():
    turn = MockLLM().complete([{"role": "user", "content": "refund order ORD-1001 please"}])
    # ORD-1001 -> resolves to its owner CUST-001, so it can still start verifying.
    assert turn.tool_calls and turn.tool_calls[0].name == "lookup_customer"


# ── OpenAI -> Anthropic translation ──────────────────────────────
def test_split_system_pulls_out_system_prompt():
    system, convo = _split_system([
        {"role": "system", "content": "You are Nimbus."},
        {"role": "user", "content": "hi"},
    ])
    assert system == "You are Nimbus."
    assert len(convo) == 1 and convo[0]["role"] == "user"


def test_to_anthropic_messages_shapes_tool_calls_and_results():
    convo = [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "checking",
         "tool_calls": [{"id": "t1", "type": "function",
                         "function": {"name": "get_order", "arguments": json.dumps({"order_id": "ORD-1"})}}]},
        {"role": "tool", "tool_call_id": "t1", "content": json.dumps({"found": True})},
        {"role": "tool", "tool_call_id": "t2", "content": json.dumps({"x": 1})},
    ]
    out = _to_anthropic_messages(convo)

    assert out[0] == {"role": "user", "content": "hi"}

    assistant = out[1]
    assert assistant["role"] == "assistant"
    blocks = assistant["content"]
    assert blocks[0] == {"type": "text", "text": "checking"}
    assert blocks[1]["type"] == "tool_use" and blocks[1]["input"] == {"order_id": "ORD-1"}

    # Consecutive tool results collapse into a single user turn.
    tool_turn = out[2]
    assert tool_turn["role"] == "user"
    assert [b["type"] for b in tool_turn["content"]] == ["tool_result", "tool_result"]
    assert tool_turn["content"][0]["tool_use_id"] == "t1"


def test_to_anthropic_tools_maps_schema_shape():
    tools = _to_anthropic_tools(TOOL_SCHEMAS)
    assert len(tools) == len(TOOL_SCHEMAS)
    first = tools[0]
    assert set(first) == {"name", "description", "input_schema"}
    assert first["name"] == "lookup_customer"
