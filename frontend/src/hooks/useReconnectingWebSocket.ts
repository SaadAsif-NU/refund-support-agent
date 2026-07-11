import { useEffect, useRef, useState } from "react";

export type ConnectionStatus = "connecting" | "open" | "closed";

interface Options {
  /** Called with each parsed JSON frame. */
  onMessage: (data: unknown) => void;
}

/**
 * A WebSocket that transparently reconnects (1.5s backoff), exposing a simple
 * status and a `send` helper. This encapsulates the connect/reconnect/status
 * plumbing that both pages previously duplicated by hand.
 */
export function useReconnectingWebSocket(path: string, { onMessage }: Options) {
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const wsRef = useRef<WebSocket | null>(null);
  // Keep the latest callback without re-opening the socket on every render.
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  useEffect(() => {
    let disposed = false;
    let retryTimer: ReturnType<typeof setTimeout> | undefined;

    const connect = () => {
      setStatus("connecting");
      const ws = new WebSocket(`ws://${location.host}${path}`);
      wsRef.current = ws;
      ws.onopen = () => setStatus("open");
      ws.onclose = () => {
        setStatus("closed");
        if (!disposed) retryTimer = setTimeout(connect, 1500);
      };
      ws.onmessage = (event) => {
        try {
          onMessageRef.current(JSON.parse(event.data));
        } catch {
          /* ignore malformed frames */
        }
      };
    };
    connect();

    return () => {
      disposed = true;
      if (retryTimer) clearTimeout(retryTimer);
      wsRef.current?.close();
    };
  }, [path]);

  /** Send a JSON payload. Returns false if the socket is not open. */
  const send = (data: unknown): boolean => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data));
      return true;
    }
    return false;
  };

  return { status, send };
}
