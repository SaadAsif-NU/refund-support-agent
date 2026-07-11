import type { Scenario } from "../../types/api";

interface ScenarioChipsProps {
  scenarios: Scenario[];
  onPick: (message: string) => void;
}

/** One-click demo scenario chips that pre-fill the composer. */
export function ScenarioChips({ scenarios, onPick }: ScenarioChipsProps) {
  return (
    <div className="mb-[18px]">
      <span className="mb-[11px] block text-center text-[11px] font-bold uppercase tracking-[1.4px] text-faint" />
      <div className="flex flex-wrap justify-center gap-[9px]">
        {scenarios.map((scenario) => (
          <button
            key={scenario.label}
            type="button"
            onClick={() => onPick(scenario.message)}
            className="cursor-pointer rounded-full border border-line bg-white/[0.04] px-[15px] py-[9px] text-[13px] font-semibold text-ink transition duration-200 hover:-translate-y-0.5 hover:border-accent/55 hover:bg-accent/10 hover:shadow-[0_10px_24px_-12px_rgba(109,155,255,0.7)]"
          >
            {scenario.label}
          </button>
        ))}
      </div>
    </div>
  );
}
