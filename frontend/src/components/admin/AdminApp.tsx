import { useCallback, useEffect, useRef, useState } from "react";
import type { AgentEvent } from "../../types/api";
import { useProviders } from "../../hooks/useProviders";
import { useLedger } from "../../hooks/useLedger";
import { useReconnectingWebSocket } from "../../hooks/useReconnectingWebSocket";
import { TopBar } from "../common/TopBar";
import { ConnectionStatus } from "../common/ConnectionStatus";
import { Pill } from "../common/Pill";
import { ReasoningFeed } from "./ReasoningFeed";
import { Ledger } from "./Ledger";
import { Legend } from "./Legend";

/** Admin dashboard: live reasoning stream + decision/refund ledger + legend. */
export default function AdminApp() {
  const providerInfo = useProviders();
  const { ledger, refresh } = useLedger();
  const [events, setEvents] = useState<AgentEvent[]>([]);
  // Dedupe by sequence number across reconnects/history replays.
  const seen = useRef<Set<number>>(new Set());

  const handleMessage = useCallback(
    (raw: unknown) => {
      const event = raw as AgentEvent;
      if (seen.current.has(event.seq)) return;
      seen.current.add(event.seq);
      setEvents((prev) => [...prev, event]);
      if (event.kind === "decision") refresh();
    },
    [refresh],
  );

  const { status } = useReconnectingWebSocket("/ws/admin", { onMessage: handleMessage });

  useEffect(() => {
    refresh();
  }, [refresh]);

  const llmLabel = providerInfo ? `🧠 ${providerInfo.llm.provider} · ${providerInfo.llm.model}` : "·";

  return (
    <>
      <TopBar logo="🛰️" title="Agent Admin Console" subtitle="Live reasoning & decision logs">
        <Pill>{llmLabel}</Pill>
        <ConnectionStatus status={status} openLabel="streaming" />
        <a
          href="/"
          target="_blank"
          className="rounded-full px-[13px] py-[7px] font-semibold text-muted no-underline transition duration-200 hover:bg-white/[0.06] hover:text-white"
        >
          Customer{" "}→
        </a>
      </TopBar>

      <div className="mx-auto grid max-w-[1400px] grid-cols-[1fr_380px] items-start gap-[18px] px-[clamp(16px,3vw,26px)] py-[22px] max-[920px]:grid-cols-1">
        <ReasoningFeed events={events} onClear={() => setEvents([])} />
        <div>
          <Ledger ledger={ledger} />
          <Legend />
        </div>
      </div>
    </>
  );
}
