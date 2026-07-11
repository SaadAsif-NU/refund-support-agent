/* Shared API contract types — mirror the FastAPI backend's JSON/WS payloads. */

export type Outcome = "APPROVE" | "APPROVE_PARTIAL" | "DENY" | "ESCALATE";

export interface Provider {
  id: string;
  label: string;
  available: boolean;
}

export interface Scenario {
  label: string;
  expected: string;
  message: string;
}

export interface LlmInfo {
  provider: string;
  model: string;
  [key: string]: unknown;
}

/** GET /api/providers — the active LLM plus the selectable provider catalogue. */
export interface ProvidersInfo {
  llm: LlmInfo;
  providers: Provider[];
  default_provider: string;
}

export interface LedgerEntry {
  outcome: Outcome | string;
  amount?: number;
  order_id?: string;
  customer_id?: string;
  item?: string;
  policy_ref?: string;
  [key: string]: unknown;
}

/* Customer chat WebSocket: server -> client frames. */
export type ChatServerMessage =
  | { type: "status"; state?: string; provider?: string }
  | { type: "reply"; text: string; provider?: string; outcome?: Outcome | null }
  | { type: "error"; text: string };

/* Admin reasoning stream event kinds. */
export type EventKind =
  | "session_start"
  | "thought"
  | "tool_call"
  | "tool_result"
  | "decision"
  | "retry"
  | "error"
  | "assistant_message"
  | "session_end";

export interface AgentEvent {
  seq: number;
  session_id: string;
  kind: EventKind | string;
  data: Record<string, unknown>;
  timestamp: string;
}
