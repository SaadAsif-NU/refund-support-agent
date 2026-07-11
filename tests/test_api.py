"""FastAPI HTTP endpoint tests, driven through Starlette's TestClient.

Covers every JSON route (shape + status codes), the health check, the served
pages, the static mount, and the auto-generated OpenAPI surface.
"""
from backend.tools import execute_tool


# ── Health ───────────────────────────────────────────────────────
def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert set(body["llm"]) >= {"provider", "model"}


# ── /api/providers ───────────────────────────────────────────────
def test_providers_shape(client):
    resp = client.get("/api/providers")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {"llm", "providers", "default_provider"}
    assert set(body["llm"]) >= {"provider", "model"}

    ids = {p["id"] for p in body["providers"]}
    assert {"mock", "groq", "gemini", "openai", "anthropic"} <= ids
    for p in body["providers"]:
        assert set(p) >= {"id", "label", "model", "available"}

    # The offline agent is always available; the default is a real provider id.
    mock = next(p for p in body["providers"] if p["id"] == "mock")
    assert mock["available"] is True
    assert body["default_provider"] in ids


def test_providers_has_no_scenarios(client):
    """Scenarios were split out to /api/scenarios; they must not leak back here."""
    assert "scenarios" not in client.get("/api/providers").json()


# ── /api/scenarios ───────────────────────────────────────────────
def test_scenarios(client):
    resp = client.get("/api/scenarios")
    assert resp.status_code == 200
    scenarios = resp.json()["scenarios"]
    assert isinstance(scenarios, list) and len(scenarios) == 8
    for s in scenarios:
        assert set(s) >= {"label", "expected", "message"}


# ── /api/customers ───────────────────────────────────────────────
def test_customers(client):
    resp = client.get("/api/customers")
    assert resp.status_code == 200
    customers = resp.json()["customers"]
    assert len(customers) == 15
    first = customers[0]
    assert set(first) >= {"id", "name", "email", "orders"}


# ── /api/policy ──────────────────────────────────────────────────
def test_policy_text(client):
    resp = client.get("/api/policy")
    assert resp.status_code == 200
    text = resp.json()["policy"]
    assert isinstance(text, str) and len(text) > 100


# ── /api/ledger ──────────────────────────────────────────────────
def test_ledger_starts_empty(client):
    assert client.get("/api/ledger").json()["ledger"] == []


def test_ledger_reflects_a_processed_refund(client):
    ctx = {"session_id": "led", "verified_customer_id": "CUST-001"}
    execute_tool("process_refund", {"order_id": "ORD-1001", "amount": 149.99, "reason": "ok"}, ctx)
    ledger = client.get("/api/ledger").json()["ledger"]
    assert len(ledger) == 1
    assert ledger[0]["outcome"] == "APPROVE"
    assert ledger[0]["amount"] == 149.99


# ── health/providers consistency ─────────────────────────────────
def test_health_and_providers_report_same_llm(client):
    assert client.get("/health").json()["llm"] == client.get("/api/providers").json()["llm"]


# ── Pages (served from the built frontend, or 503 if not built) ───
def test_customer_page(client):
    resp = client.get("/")
    assert resp.status_code in (200, 503)
    if resp.status_code == 503:
        assert "not built" in resp.text.lower()
    else:
        assert 'id="root"' in resp.text


def test_admin_page(client):
    resp = client.get("/admin")
    assert resp.status_code in (200, 503)


# ── Static assets mount ──────────────────────────────────────────
def test_missing_asset_is_404(client):
    # The /assets mount exists (check_dir=False); a missing file is a clean 404.
    assert client.get("/assets/does-not-exist.js").status_code == 404


# ── Unknown routes ───────────────────────────────────────────────
def test_unknown_route_404(client):
    assert client.get("/api/nope").status_code == 404


# ── FastAPI-generated surface ────────────────────────────────────
def test_openapi_and_docs_available(client):
    schema = client.get("/openapi.json")
    assert schema.status_code == 200
    paths = schema.json()["paths"]
    assert "/api/providers" in paths and "/api/scenarios" in paths
    assert client.get("/docs").status_code == 200
