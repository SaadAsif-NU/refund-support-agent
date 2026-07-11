import { OUTCOME_BADGE_CLASS } from "../../lib/constants";

interface BadgeProps {
  outcome: string;
}

/** Small pill showing a decision outcome, coloured by its code. */
export function Badge({ outcome }: BadgeProps) {
  const tone = OUTCOME_BADGE_CLASS[outcome] ?? "";
  return (
    <span
      className={`inline-block rounded-full px-2.5 py-[3px] text-[10.5px] font-extrabold tracking-[.3px] ${tone}`}
    >
      {outcome}
    </span>
  );
}
