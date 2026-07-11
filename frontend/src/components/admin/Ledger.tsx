import type { LedgerEntry } from "../../types/api";
import { Badge } from "../common/Badge";

/** Decision / refund ledger panel (newest first). */
export function Ledger({ ledger }: { ledger: LedgerEntry[] }) {
  return (
    <div className="mb-4 overflow-hidden rounded-card border border-line bg-panel shadow-panel backdrop-blur-[18px]">
      <h2 className="m-0 flex items-center justify-between border-b border-line px-5 py-[15px] text-[12px] font-bold uppercase tracking-[1px] text-muted">
        <span>⚖️ Decisions &amp; Refund Ledger</span>
      </h2>
      {ledger.length === 0 ? (
        <div className="px-[18px] py-4 text-[12.5px] leading-[1.7] text-muted">
          No decisions recorded yet.
        </div>
      ) : (
        <div className="scroll-y flex max-h-[42vh] flex-col gap-[10px] overflow-y-auto p-[14px]">
          {ledger
            .slice()
            .reverse()
            .map((entry, index) => {
              const approved =
                entry.outcome === "APPROVE" || entry.outcome === "APPROVE_PARTIAL";
              const amount = approved
                ? `$${Number(entry.amount).toFixed(2)}`
                : entry.policy_ref ?? "";
              return (
                <div
                  key={index}
                  className="flex items-center gap-[11px] rounded-[11px] border border-line bg-white/[0.02] px-[13px] py-[11px] text-[13px] transition duration-200 hover:border-line-strong"
                >
                  <Badge outcome={String(entry.outcome)} />
                  <span>
                    <div>{entry.item || entry.order_id || ""}</div>
                    <span className="font-mono text-[11.5px] text-faint">
                      {entry.order_id ?? ""} · {entry.customer_id ?? ""}
                    </span>
                  </span>
                  <span className="ml-auto font-extrabold">{amount}</span>
                </div>
              );
            })}
        </div>
      )}
    </div>
  );
}
