import { useEffect, useState } from "react";
import type { Scenario } from "../types/api";
import { fetchScenarios } from "../lib/api";

/** Loads /api/scenarios once. Returns [] until it resolves (or on failure). */
export function useScenarios(): Scenario[] {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);

  useEffect(() => {
    let active = true;
    fetchScenarios()
      .then((list) => {
        if (active) setScenarios(list);
      })
      .catch(() => {
        /* leave [] on failure */
      });
    return () => {
      active = false;
    };
  }, []);

  return scenarios;
}
