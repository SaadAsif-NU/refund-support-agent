"""Read-only JSON APIs: LLM providers, demo scenarios, CRM, policy, ledger, health."""
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..agent import agent
from ..scenarios import SCENARIOS
from ..store import store

router = APIRouter()


@router.get("/api/providers")
async def providers() -> JSONResponse:
    """The LLM the agent is using plus the selectable provider catalogue."""
    return JSONResponse({
        "llm": agent.describe(),
        "providers": agent.provider_catalog(),
        "default_provider": agent.providers.default_provider,
    })


@router.get("/api/scenarios")
async def scenarios() -> JSONResponse:
    """Curated one-click demo prompts for the customer chat."""
    return JSONResponse({"scenarios": SCENARIOS})


@router.get("/api/customers")
async def customers() -> JSONResponse:
    return JSONResponse({"customers": store.all_customers()})


@router.get("/api/policy")
async def policy() -> JSONResponse:
    return JSONResponse({"policy": store.policy_text})


@router.get("/api/ledger")
async def ledger() -> JSONResponse:
    return JSONResponse({"ledger": store.refund_ledger})


@router.get("/health")
async def health() -> JSONResponse:
    return JSONResponse({"status": "ok", "llm": agent.describe()})
