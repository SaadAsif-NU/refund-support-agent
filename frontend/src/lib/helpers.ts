/* Reusable, pure helper functions — safe to use anywhere in the app.
 * Keep these dependency-free and side-effect-free so they stay portable. */

/** "2026-07-09T12:34:56.789" -> "12:34:56.789". Empty string for missing input. */
export function formatTime(timestamp: string): string {
  if (!timestamp) return "";
  return timestamp.split("T")[1]?.slice(0, 12) ?? "";
}
