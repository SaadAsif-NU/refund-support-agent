import axios from "axios";
import type { LedgerEntry, ProvidersInfo, Scenario } from "../types/api";

/**
 * Shared axios instance for the backend REST API.
 *
 * Same-origin: `/api/*` is proxied to FastAPI by Vite in dev and served by the
 * backend in prod. Centralising baseURL/timeout/headers here gives us one place
 * to add interceptors (auth, error normalisation, retries) as the app grows.
 * Unlike `fetch`, axios rejects on non-2xx responses, so callers can rely on a
 * thrown error rather than checking `res.ok`.
 */
export const http = axios.create({
  baseURL: "/",
  timeout: 10_000,
  headers: { Accept: "application/json" },
});

/** GET /api/providers — active llm, provider catalogue, and default provider. */
export async function fetchProviders(): Promise<ProvidersInfo> {
  const { data } = await http.get<ProvidersInfo>("/api/providers");
  return data;
}

/** GET /api/scenarios — curated one-click demo prompts. */
export async function fetchScenarios(): Promise<Scenario[]> {
  const { data } = await http.get<{ scenarios?: Scenario[] }>("/api/scenarios");
  return data.scenarios ?? [];
}

/** GET /api/ledger — decision / refund ledger. */
export async function fetchLedger(): Promise<LedgerEntry[]> {
  const { data } = await http.get<{ ledger?: LedgerEntry[] }>("/api/ledger");
  return data.ledger ?? [];
}
