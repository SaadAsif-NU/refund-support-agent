import { useEffect, useRef } from "react";
import type { AgentEvent } from "../../types/api";
import { EventCard } from "./EventCard";

interface ReasoningFeedProps {
  events: AgentEvent[];
  onClear: () => void;
}

/** Live, auto-scrolling stream of agent reasoning events. */
export function ReasoningFeed({ events, onClear }: ReasoningFeedProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [events]);

  return (
    <div className="overflow-hidden rounded-card border border-line bg-panel shadow-panel backdrop-blur-[18px]">
      <h2 className="m-0 flex items-center justify-between border-b border-line px-5 py-[15px] text-[12px] font-bold uppercase tracking-[1px] text-muted">
        <span>🧠 Live Agent Reasoning</span>
        <button
          type="button"
          onClick={onClear}
          className="cursor-pointer rounded-lg border border-line bg-transparent px-[11px] py-[5px] text-[11px] font-semibold text-muted transition duration-200 hover:border-line-strong hover:bg-white/[0.05] hover:text-white"
        >
          clear
        </button>
      </h2>
      <div
        ref={scrollRef}
        className="scroll-y flex max-h-[78vh] flex-col gap-[11px] overflow-y-auto p-4"
      >
        {events.length === 0 ? (
          <div className="px-[14px] py-[48px] text-center text-[14px] leading-[1.6] text-muted">
            Waiting for activity… open the{" "}
            <a href="/" target="_blank" className="text-accent no-underline hover:underline">
              customer chat
            </a>{" "}
            and send a refund request to watch the agent reason, call tools, and decide in real
            time.
          </div>
        ) : (
          events.map((event) => <EventCard key={event.seq} event={event} />)
        )}
      </div>
    </div>
  );
}
