/*
 * Static legend explaining the event kinds. Note: in the original CSS the bold/
 * uppercase `.kind` styling is scoped to `.event`, so here the kind words are
 * only colour-tinted (normal weight/case) — matched intentionally.
 */
export function Legend() {
  return (
    <div className="overflow-hidden rounded-card border border-line bg-panel shadow-panel backdrop-blur-[18px]">
      <h2 className="m-0 flex items-center justify-between border-b border-line px-5 py-[15px] text-[12px] font-bold uppercase tracking-[1px] text-muted">
        <span>📋 Legend</span>
      </h2>
      <div className="px-[18px] py-4 text-[12.5px] leading-[1.7] text-muted">
        <p className="m-0">
          <span className="text-violet">thought</span> - the agent's internal plan.
          <br />
          <span className="text-accent">tool_call</span> - a policy/CRM tool invocation.
          <br />
          tool_result - the JSON returned to the agent.
          <br />
          <span className="text-green">decision</span> - final outcome (approve / deny / escalate).
          <br />
          <span className="text-amber">retry</span> &amp;{" "}
          <span className="text-red">error</span> - failure handling.
        </p>
        <p className="mb-0 mt-3">
          Every decision is computed by the deterministic policy engine, so the agent can't
          hallucinate a refund. Sessions are tagged like{" "}
          <code className="rounded-md bg-white/[0.06] px-1.5 py-px text-[11.5px] text-ink">
            web-ab12cd
          </code>
          .
        </p>
      </div>
    </div>
  );
}
