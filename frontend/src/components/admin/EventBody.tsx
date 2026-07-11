import type { AgentEvent } from "../../types/api";
import { Badge } from "../common/Badge";

const CODE = "rounded-md bg-white/[0.06] px-1.5 py-px font-mono text-[12px]";
const PRE =
  "mt-[7px] overflow-x-auto whitespace-pre-wrap break-words rounded-[9px] border border-line bg-[#0a0e1a] px-3 py-2.5 font-mono text-[12px] text-[#bcd0ff]";

/** Renders the body of a reasoning event, formatted per kind (mirrors `bodyFor`). */
export function EventBody({ event }: { event: AgentEvent }) {
  // Event payloads are loosely-typed maps keyed by kind; read them dynamically.
  const d = event.data as Record<string, unknown>;

  switch (event.kind) {
    case "session_start":
      return (
        <>
          ▶ Customer: “{String(d.user_message ?? "")}”
          {d.provider ? (
            <span className="font-mono text-[11.5px] text-faint">
              {" "}
              via {String(d.provider)} · {String(d.model ?? "")}
            </span>
          ) : null}
        </>
      );
    case "thought":
      return <>{String(d.text ?? "")}</>;
    case "tool_call":
      return (
        <>
          <code className={CODE}>{String(d.tool)}(</code>
          <pre className={PRE}>{JSON.stringify(d.arguments ?? {}, null, 2)}</pre>
        </>
      );
    case "tool_result":
      return (
        <>
          {String(d.tool)} →<pre className={PRE}>{JSON.stringify(d.result ?? {}, null, 2)}</pre>
        </>
      );
    case "decision":
      return (
        <>
          <Badge outcome={String(d.outcome ?? "")} /> via{" "}
          <code className={CODE}>{String(d.tool)}</code>
        </>
      );
    case "retry":
      return (
        <>
          ⟳ Attempt {String(d.attempt)}/{String(d.max)} after error: {String(d.error ?? "")}
        </>
      );
    case "error":
      return <>⚠ {String(d.text ?? "")}</>;
    case "assistant_message":
      return <>💬 {String(d.text ?? "")}</>;
    case "session_end":
      return <>■ Completed in {String(d.steps)} step(s).</>;
    default:
      return <>{JSON.stringify(d)}</>;
  }
}
