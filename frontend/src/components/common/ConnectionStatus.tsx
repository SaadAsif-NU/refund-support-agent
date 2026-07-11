import type { ConnectionStatus as Status } from "../../hooks/useReconnectingWebSocket";
import { Pill } from "./Pill";

interface ConnectionStatusProps {
  status: Status;
  /** Label shown while connected (e.g. "online" or "streaming"). */
  openLabel: string;
}

const DOT_CLASS: Record<Status, string> = {
  connecting: "bg-faint",
  open: "bg-green shadow-[0_0_0_4px_rgba(52,211,153,.16)]",
  closed: "bg-red shadow-[0_0_0_4px_rgba(251,113,133,.16)]",
};

/** Live connection indicator: a coloured dot + status text, in a pill. */
export function ConnectionStatus({ status, openLabel }: ConnectionStatusProps) {
  const text =
    status === "open" ? openLabel : status === "closed" ? "reconnecting…" : "connecting…";
  return (
    <Pill>
      <span className={`h-2 w-2 rounded-full transition-[background] duration-300 ${DOT_CLASS[status]}`} />
      <span>{text}</span>
    </Pill>
  );
}
