# AI Customer Support Agent (Refunds)

A fully functional web app in which an **AI agent processes or denies e-commerce refunds**
by dynamically calling tools to enforce a strict refund policy. It ships with a customer
**chat interface + voice**, and an **admin dashboard that streams the agent's live reasoning**
(thoughts, tool calls, tool results, retries, and final decisions).

> Runs out of the box with **no API key** (deterministic offline agent). Paste a key into
> `.env` and that provider lights up in the in-app **model picker** - Groq or Gemini (free),
> or GPT / Claude (paid). Voice uses the browser's built-in speech engine, so the whole thing
> is **100% free** to run and demo.

---

## ✨ What's inside

| Requirement | Implementation |
|---|---|
| **Mock data** | `backend/data/customers.json` - **15 CRM profiles** with orders; `backend/data/refund_policy.md` - a strict, 12-section policy. |
| **Agent backend** | A transparent **raw function-calling loop** (`backend/agent.py`) that calls tools to validate every rule. Provider-agnostic LLM layer (`backend/llm/`). |
| **Deterministic policy** | `backend/policy.py` computes every decision fact in plain Python, so the agent **can't hallucinate a refund**. |
| **Frontend** | **React + TypeScript + Tailwind**, bundled by **Vite**. Customer **chat UI** with a **microphone** and an **admin dashboard** with real-time reasoning logs - two entry points (`frontend/src/main-customer.tsx`, `frontend/src/main-admin.tsx`). |
| **Voice pipeline (bonus)** | Browser **Web Speech API** - speech-to-text (mic) and text-to-speech (spoken replies). Free, no external service. |
| **Reasoning logs / failure handling** | Live WebSocket event stream; the agent loop retries LLM failures with backoff and surfaces `retry`/`error` events in the admin panel. |

---

## 🚀 Run it (from scratch)

The app is a **FastAPI backend** (agent, policy, JSON APIs, WebSockets) plus a **React/Vite
frontend** (customer chat + admin dashboard). There are two ways to run it: a **single server**
(build the frontend once; the backend then serves everything on `:8000`) or a **dev setup** with
hot reload (Vite on `:5173` proxying `/api` and `/ws` to the backend on `:8000`).

### Prerequisites

- **Python 3.10+**
- **Node.js 18+** and **npm** (to build/run the frontend)

### 1. Get the code & set up the backend

```bash
git clone https://github.com/SaadAsif-NU/refund-support-agent.git
cd refund-support-agent

python3 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# (optional) paste an API key to unlock a real model - see "Model providers" below.
# Skip this to run in the free offline "mock" mode.
cp .env.example .env
```

### 2a. Single server (simplest)

Build the frontend once; the FastAPI backend serves the whole app on **:8000**.

```bash
cd frontend && npm install && npm run build && cd ..   # type-checks + bundles to frontend/dist/
python run.py                                          # serves API, WebSockets, and the built UI
```

- **Customer chat** → http://127.0.0.1:8000/
- **Admin console** → http://127.0.0.1:8000/admin

Re-run `npm run build` after any frontend change. (This is also the deployment shape: one
FastAPI process serving both the API and the static bundle from `frontend/dist/`.)

### 2b. Development (hot reload)

Two terminals — open the **Vite** URL (`:5173`), **not** `:8000`. Vite serves the UI and
transparently proxies `/api` and `/ws/*` to the backend.

```bash
# terminal 1 — backend (REST + WebSockets) on :8000
python run.py                       # or: uvicorn backend.main:app --reload --port 8000

# terminal 2 — Vite dev server on :5173, with hot reload
cd frontend && npm install && npm run dev
```

- **Customer chat** → http://localhost:5173/
- **Admin console** → http://localhost:5173/admin  *(open side-by-side)*

### Tests

```bash
pytest -q               # 165 backend tests: policy units + end-to-end agent/API
```

---

## 🧠 Model providers (switchable in the UI)

The chat has a **model picker** in the top bar. It lists five providers; each one
becomes selectable the moment its API key is present in `.env` (the offline agent is
always available). Keys live only on the server and are never sent to the browser.

| Provider (picker label) | Get a key | `.env` variable |
|---|---|---|
| **Offline agent** | - (built in) | - |
| **Groq · Llama 3.3 70B** | <https://console.groq.com/keys> | `GROQ_API_KEY` |
| **Google · Gemini 2.5 Flash** | <https://aistudio.google.com/apikey> | `GEMINI_API_KEY` |
| **OpenAI · GPT-5** | <https://platform.openai.com/api-keys> | `OPENAI_API_KEY` |
| **Anthropic · Claude Opus 4.8** | <https://console.anthropic.com/settings/keys> | `ANTHROPIC_API_KEY` |

**How to add a key:** open `.env`, paste the key next to the matching variable, and
restart the backend. To make a provider the default selection, set `DEFAULT_PROVIDER=groq`
(or `gemini` / `openai` / `anthropic`). Model per provider is overridable, e.g.
`OPENAI_MODEL=gpt-4o-mini` or `ANTHROPIC_MODEL=claude-haiku-4-5` for cheaper runs.

Groq/Gemini/OpenAI go through the OpenAI-compatible API; **Claude uses the official
`anthropic` SDK** (the canonical message history is translated to the Messages API at
call time). If a provider is picked without a key, the request is **served by the
offline agent** so a demo never breaks.

> **Rate limits & resilience.** Each refund makes ~8 sequential model calls (one per tool
> step), which can trip a free tier's per-minute quota. If the chosen provider returns a
> 429/quota error mid-conversation, the app **falls back to the offline engine for the rest
> of that turn** and still returns the correct decision - the admin panel shows the
> `... unavailable (429); continuing on the offline engine` event. For heavy back-to-back
> demoing, **Groq** (higher free limits, fast) or the **Offline agent** (instant, no quota)
> are the smoothest; Gemini's free tier is fine for occasional requests.

---

## 💬 How to talk to the agent

The agent needs to **identify the customer and the order**, so include a customer
reference (name, `CUST-00X`, or the email) and an order number (`ORD-XXXX`) in your
message. It handles free-form phrasing - "hi, I'm Emily, order ORD-1001 didn't fit,
can I get a refund?" works. If you leave out the order, it asks for it and remembers
your identity across the follow-up. All 15 customers and their orders are in
`backend/data/customers.json`; the app's one-click **scenario chips** at the top of the
chat are the quickest way to try it.

---

## 🎙️ Voice pipeline

Voice is **100% free and built into the browser** - no ElevenLabs / OpenAI Realtime /
LiveKit account required:

- **Speech-to-text (mic):** the Web Speech API's `SpeechRecognition`
  (`frontend/src/hooks/useSpeechRecognition.ts`) - click 🎙️, speak, and the transcript is
  sent as a normal chat message.
- **Text-to-speech (spoken replies):** `speechSynthesis` (`frontend/src/lib/speech.ts`) reads
  the agent's reply aloud; toggle it with the 🔊 button.

Both run entirely client-side (best in Chrome/Edge). The architecture is provider-
agnostic, so a paid real-time voice service could be dropped in later without touching
the agent or policy layers - but nothing paid is needed for the demo.

---

## 🏗️ Architecture

```
Customer (chat / 🎙️ voice)                     Admin dashboard (real-time)
        │  WebSocket /ws/chat                         ▲  WebSocket /ws/admin
        ▼                                             │  (thoughts, tool calls,
┌── FastAPI (backend/main.py + routes/) ──────────────┴── results, retries, decisions)
│                                                     │
│   Agent loop (agent.py) ──emits──► Event bus (events.py)
│        │ function calling
│        ▼
│   Tools (tools/) ──► Policy engine (policy.py)   ◄── deterministic rules
│        │                    │
│        ▼                    ▼
│   CRM store (store.py) ◄── data/customers.json + data/refund_policy.md
└──────────────────────────────────────────────────────────────────────────

LLM layer (llm/): offline mock · Groq/Gemini/GPT via OpenAI SDK · Claude via anthropic SDK
```

**The loop** (`backend/agent.py`): the LLM proposes tool calls → we execute them against the
deterministic policy engine → feed JSON results back → repeat until the model returns a final
answer. It must finish by calling exactly one of `process_refund`, `deny_refund`, or
`escalate_to_human`. Every step is emitted to the event bus for the admin panel. The system
prompt (with the policy spliced in) lives in `backend/prompts.py`.

**The tools** (`backend/tools/`), grouped by responsibility:
- `lookup.py` — `lookup_customer` · `get_order` (read-only identity/order retrieval)
- `checks.py` — `check_return_window` · `check_item_eligibility` · `check_customer_standing` ·
  `check_high_value` · `calculate_refund_amount` (read-only policy checks)
- `decisions.py` — `process_refund` · `deny_refund` · `escalate_to_human` (the **guarded**
  finalize tools — the only ones that write the ledger)
- `registry.py` — name → implementation dispatch (`execute_tool`); `schemas.py` — the
  OpenAI-compatible `TOOL_SCHEMAS` advertised to every provider.

**Why decisions are trustworthy:** the LLM *orchestrates and communicates*, but every
decision-relevant fact (windows, categories, restocking math, fraud limits) is computed in
`policy.py`. The finalize tools re-check the policy verdict before writing, so the model
cannot approve something the policy forbids.

**Deterministic safety net:** real models occasionally *narrate* a decision without calling
the finalize tool. If a turn ends that way, `policy.evaluate()` computes the authoritative
outcome (ownership included) and records it - so the admin log and refund ledger are always
complete, regardless of the model. These backstop decisions are tagged `auto` in the event
stream.

---

## 📁 Project structure

```
refund-support-agent/
├── backend/                     # FastAPI service (agent, policy, APIs, WebSockets)
│   ├── main.py                  # app composition root: include routers, mount static
│   ├── paths.py                 # shared filesystem paths (FRONTEND_DIR)
│   ├── scenarios.py             # curated one-click demo scenarios (served at /api/scenarios)
│   ├── prompts.py               # the agent system prompt (policy spliced in)
│   ├── agent.py                 # function-calling agent loop + retry/failure handling
│   ├── policy.py                # deterministic policy engine (single source of truth)
│   ├── store.py                 # CRM store + durable refund ledger (persisted to data/)
│   ├── events.py                # async pub/sub reasoning event bus
│   ├── routes/                  # HTTP + WebSocket handlers, grouped by concern
│   │   ├── pages.py             #   GET / (customer) and /admin
│   │   ├── api.py               #   /api/providers · /api/scenarios · /api/customers · /api/policy · /api/ledger · /health
│   │   └── websockets.py        #   /ws/chat (customer) · /ws/admin (reasoning stream)
│   ├── tools/                   # agent tools, grouped by responsibility
│   │   ├── lookup.py            #   read-only identity/order retrieval
│   │   ├── checks.py            #   read-only policy checks
│   │   ├── decisions.py         #   guarded finalize tools (record the outcome)
│   │   ├── registry.py          #   name → impl dispatch (execute_tool)
│   │   └── schemas.py           #   OpenAI-compatible tool schemas (TOOL_SCHEMAS)
│   ├── llm/                     # multi-provider LLM layer
│   │   ├── types.py             #   AssistantTurn / ToolCall (provider-independent shapes)
│   │   ├── providers.py         #   PROVIDERS catalog + ProviderManager dispatch
│   │   ├── translate.py         #   OpenAI-canonical → Anthropic Messages API translation
│   │   └── mock.py              #   deterministic offline agent (MockLLM)
│   └── data/
│       ├── customers.json       # 15 CRM profiles + orders
│       └── refund_policy.md     # strict refund policy
├── frontend/                    # React + TypeScript + Tailwind, bundled by Vite
│   ├── index.html               # customer page  → loads src/main-customer.tsx
│   ├── admin.html               # admin page     → loads src/main-admin.tsx
│   ├── vite.config.ts           # React + Tailwind plugins; dev proxy /api,/ws → :8000
│   ├── package.json             # scripts: dev · build · preview
│   └── src/
│       ├── main-customer.tsx    # customer app entry
│       ├── main-admin.tsx       # admin app entry
│       ├── index.css            # Tailwind v4 theme tokens (@theme) + base layer
│       ├── components/
│       │   ├── common/          # TopBar · Pill · Badge · ConnectionStatus
│       │   ├── customer/        # CustomerApp · Hero · ScenarioChips · ProviderSelect ·
│       │   │                    #   MessageList · MessageBubble · TypingIndicator · Composer
│       │   └── admin/           # AdminApp · ReasoningFeed · EventCard · EventBody · Ledger · Legend
│       ├── hooks/               # useConfig · useLedger · useReconnectingWebSocket · useSpeechRecognition
│       ├── lib/                 # api · eventStyles · markdown · outcomes · speech
│       └── types/               # shared API types + Web Speech typings
├── tests/                       # policy unit tests + end-to-end agent/API tests
├── run.py                       # backend launcher (uvicorn backend.main:app)
├── requirements.txt
└── .env.example
```

---

## 📜 Refund policy (summary)

30-day standard window · 90 days for defective/damaged · gift cards / perishables / intimate
apparel / downloaded digital goods are final sale · used non-defective items ineligible · 15%
restocking fee on opened electronics · fraud guard (>3 refunds/yr → escalate) · orders >$500 →
manager approval · refunds to original payment method only. Full text: `backend/data/refund_policy.md`.
