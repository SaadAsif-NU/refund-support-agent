import type { Outcome } from "../../types/api";
import { renderMarkdown } from "../../lib/markdown";
import { OUTCOME_BADGE, OUTCOME_TONE_CLASS } from "../../lib/constants";

export type Sender = "user" | "bot";

interface MessageBubbleProps {
  who: Sender;
  text: string;
  outcome?: Outcome | null;
}

/** A single chat row: avatar + bubble. Human on the right, Nimbus on the left. */
export function MessageBubble({ who, text, outcome }: MessageBubbleProps) {
  const isUser = who === "user";
  const badge = !isUser && outcome ? OUTCOME_BADGE[outcome] : undefined;

  return (
    <div
      className={`flex max-w-full animate-msg-in items-end gap-3 ${isUser ? "flex-row-reverse" : ""}`}
    >
      <div
        className={`grid h-9 w-9 flex-none place-items-center rounded-[11px] text-[18px] mb-0.5 ${
          isUser
            ? "border border-line-strong bg-panel-3"
            : "bg-linear-to-br from-accent to-accent-2 shadow-[0_6px_18px_-6px_rgba(109,155,255,0.6)]"
        }`}
      >
        {isUser ? "🧑" : "☁️"}
      </div>

      <div
        className={`relative max-w-[min(640px,78%)] rounded-[18px] px-[17px] py-[13px] text-[14.5px] leading-[1.55] shadow-soft max-[920px]:max-w-[82%] ${
          isUser
            ? "rounded-br-[5px] border border-white/15 bg-linear-to-br from-accent to-accent-2 text-white shadow-[0_14px_34px_-16px_rgba(109,155,255,0.6)]"
            : "rounded-bl-[5px] border border-accent/20 bg-panel-2 shadow-[0_12px_30px_-18px_rgba(0,0,0,0.6)]"
        }`}
      >
        {badge && (
          <span
            className={`mb-2 inline-flex items-center gap-1.5 rounded-full px-[11px] py-1 text-[11px] font-extrabold tracking-[.3px] ${OUTCOME_TONE_CLASS[badge.tone]}`}
          >
            {badge.label}
          </span>
        )}
        <div
          className={`mb-[5px] text-[10.5px] font-bold uppercase tracking-[.7px] ${
            isUser ? "opacity-60" : "text-accent opacity-85"
          }`}
        >
          {isUser ? "You" : "Nimbus"}
        </div>
        <div>{renderMarkdown(text)}</div>
      </div>
    </div>
  );
}
