import type { AgentEvent } from "../../types/api";
import { KIND_CARD_CLASS, KIND_LABELS, KIND_TEXT_CLASS } from "../../lib/constants";
import { formatTime } from "../../lib/helpers";
import { EventBody } from "./EventBody";

/** One reasoning event: coloured left border, kind label, session/time, body. */
export function EventCard({ event }: { event: AgentEvent }) {
  const cardTint = KIND_CARD_CLASS[event.kind] ?? "";
  const kindColor = KIND_TEXT_CLASS[event.kind] ?? "";
  const label = KIND_LABELS[event.kind] ?? event.kind;

  return (
    <div
      className={`animate-ev-in rounded-xl border border-l-[3px] border-line bg-white/[0.02] px-[14px] py-[11px] ${cardTint}`}
    >
      <div className="flex items-center gap-[9px] text-[12.5px]">
        <span className={`text-[10.5px] font-extrabold uppercase tracking-[.5px] ${kindColor}`}>
          {label}
        </span>
        <span className="ml-auto font-mono text-[11px] text-faint">
          {event.session_id} · {formatTime(event.timestamp)}
        </span>
      </div>
      <div className="mt-2 text-[13px] leading-[1.5] text-ink">
        <EventBody event={event} />
      </div>
    </div>
  );
}
