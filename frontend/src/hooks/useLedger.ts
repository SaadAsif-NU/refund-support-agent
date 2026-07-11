import { useCallback, useState } from "react";
import type { LedgerEntry } from "../types/api";
import { fetchLedger } from "../lib/api";

/** Holds the decision/refund ledger with an on-demand refresh. */
export function useLedger() {
  const [ledger, setLedger] = useState<LedgerEntry[]>([]);

  const refresh = useCallback(() => {
    fetchLedger()
      .then(setLedger)
      .catch(() => {
      });
  }, []);

  return { ledger, refresh };
}
