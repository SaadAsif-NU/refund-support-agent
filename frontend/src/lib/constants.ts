/* Presentation constants (labels + Tailwind class maps) used across the UI.
 * Pure data — no logic. Reusable helper functions live in ./helpers. */
import type { Outcome } from "../types/api";

/* ── Admin reasoning-event presentation ──────────────────────────── */

/** Human label per event kind (falls back to the raw kind). */
export const KIND_LABELS: Record<string, string> = {
  session_start: "session",
  thought: "thought",
  tool_call: "tool_call",
  tool_result: "tool_result",
  decision: "decision",
  retry: "retry",
  error: "error",
  assistant_message: "reply",
  session_end: "session_end",
};

/** Left-border colour (and subtle background tint for some) per kind. */
export const KIND_CARD_CLASS: Record<string, string> = {
  thought: "border-l-violet",
  tool_call: "border-l-accent",
  tool_result: "border-l-tool-result",
  decision: "border-l-green bg-green/[0.07]",
  retry: "border-l-amber bg-amber/[0.08]",
  error: "border-l-red bg-red/[0.08]",
  session_start: "border-l-session",
  session_end: "border-l-session",
  assistant_message: "border-l-assistant",
};

/** Coloured kind label — only some kinds are tinted; others inherit ink. */
export const KIND_TEXT_CLASS: Record<string, string> = {
  thought: "text-violet",
  tool_call: "text-accent",
  decision: "text-green",
  retry: "text-amber",
  error: "text-red",
};

/* ── Customer-facing outcome badge (inside a Nimbus bot bubble) ───── */

export type Tone = "approve" | "deny" | "escalate";

export const OUTCOME_BADGE: Record<Outcome, { tone: Tone; label: string }> = {
  APPROVE: { tone: "approve", label: "✓ Approved" },
  APPROVE_PARTIAL: { tone: "approve", label: "✓ Partial refund" },
  DENY: { tone: "deny", label: "✕ Declined" },
  ESCALATE: { tone: "escalate", label: "⤴ Escalated to a human" },
};

export const OUTCOME_TONE_CLASS: Record<Tone, string> = {
  approve: "bg-green/15 text-green shadow-[inset_0_0_0_1px_rgba(52,211,153,.3)]",
  deny: "bg-red/15 text-red shadow-[inset_0_0_0_1px_rgba(251,113,133,.3)]",
  escalate: "bg-amber/15 text-amber shadow-[inset_0_0_0_1px_rgba(251,191,36,.3)]",
};

/* ── Admin decision / ledger badge colour by outcome code ────────── */

export const OUTCOME_BADGE_CLASS: Record<string, string> = {
  APPROVE: "bg-green/15 text-green",
  APPROVE_PARTIAL: "bg-green/15 text-green",
  DENY: "bg-red/15 text-red",
  ESCALATE: "bg-amber/15 text-amber",
};
