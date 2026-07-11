import { useEffect, useState } from "react";
import type { ProvidersInfo } from "../types/api";
import { fetchProviders } from "../lib/api";

/** Loads /api/providers once. Returns null until it resolves (or on failure). */
export function useProviders(): ProvidersInfo | null {
  const [providers, setProviders] = useState<ProvidersInfo | null>(null);

  useEffect(() => {
    let active = true;
    fetchProviders()
      .then((info) => {
        if (active) setProviders(info);
      })
      .catch(() => {
        /* leave null on failure */
      });
    return () => {
      active = false;
    };
  }, []);

  return providers;
}
