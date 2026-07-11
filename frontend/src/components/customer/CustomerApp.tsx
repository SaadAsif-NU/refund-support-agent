import { useCallback, useEffect, useRef, useState } from "react";
import type { ChatServerMessage, Outcome } from "../../types/api";
import { useProviders } from "../../hooks/useProviders";
import { useScenarios } from "../../hooks/useScenarios";
import { useReconnectingWebSocket } from "../../hooks/useReconnectingWebSocket";
import { useSpeechRecognition } from "../../hooks/useSpeechRecognition";
import { cancelSpeech, speak } from "../../lib/speech";
import { TopBar } from "../common/TopBar";
import { ConnectionStatus } from "../common/ConnectionStatus";
import { Hero } from "./Hero";
import { ScenarioChips } from "./ScenarioChips";
import { ProviderSelect } from "./ProviderSelect";
import { MessageList } from "./MessageList";
import { Composer } from "./Composer";
import type { ChatMessage } from "./message";
import type { Sender } from "./MessageBubble";

const PROVIDER_STORAGE_KEY = "nimbus-provider";
const GREETING =
  "Hi! I'm Nimbus, NimbusMart's refund assistant. I can help you request a refund on a " +
  "recent order. To get started, tell me your name or email and the order number you'd " +
  "like to refund.";

/** Customer chat page: WebSocket chat, provider picker, scenarios, and voice. */
export default function CustomerApp() {
  const sessionId = useRef("web-" + Math.random().toString(36).slice(2, 9)).current;
  const providerInfo = useProviders();
  const scenarios = useScenarios();

  const [provider, setProvider] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([
    { id: 0, who: "bot", text: GREETING },
  ]);
  const [typing, setTyping] = useState(false);
  const [busy, setBusy] = useState(false);
  const [input, setInput] = useState("");
  const [ttsEnabled, setTtsEnabled] = useState(true);
  const nextId = useRef(1);
  const inputRef = useRef<HTMLInputElement>(null);

  const addMessage = useCallback((text: string, who: Sender, outcome?: Outcome | null) => {
    setMessages((prev) => [...prev, { id: nextId.current++, who, text, outcome }]);
  }, []);

  const handleMessage = useCallback(
    (raw: unknown) => {
      const data = raw as ChatServerMessage;
      if (data.type === "status") {
        setTyping(true);
      } else if (data.type === "reply") {
        setTyping(false);
        addMessage(data.text, "bot", data.outcome ?? null);
        if (ttsEnabled) speak(data.text);
        setBusy(false);
      } else if (data.type === "error") {
        setTyping(false);
        addMessage(data.text, "bot");
        setBusy(false);
      }
    },
    [addMessage, ttsEnabled],
  );

  const { status, send } = useReconnectingWebSocket("/ws/chat", { onMessage: handleMessage });

  const doSend = (raw: string) => {
    const text = raw.trim();
    if (!text) return;
    const sent = send({ session_id: sessionId, message: text, provider });
    if (!sent) return;
    addMessage(text, "user");
    setInput("");
    setBusy(true);
  };

  const mic = useSpeechRecognition({
    onTranscript: setInput,
    onFinal: (text) => doSend(text),
  });

  // Pick the initial provider once the catalogue arrives (saved pref if still valid).
  useEffect(() => {
    if (!providerInfo) return;
    const saved = localStorage.getItem(PROVIDER_STORAGE_KEY);
    const valid = saved && providerInfo.providers.some((p) => p.id === saved && p.available);
    setProvider(valid && saved ? saved : providerInfo.default_provider);
  }, [providerInfo]);

  const changeProvider = (id: string) => {
    setProvider(id);
    localStorage.setItem(PROVIDER_STORAGE_KEY, id);
  };

  const toggleTts = () => {
    setTtsEnabled((prev) => {
      const next = !prev;
      if (!next) cancelSpeech();
      return next;
    });
  };

  const pickScenario = (message: string) => {
    setInput(message);
    inputRef.current?.focus();
  };

  return (
    <>
      <TopBar logo="☁️" title="NimbusMart Support" subtitle="AI Refund Assistant">
        <ProviderSelect
          providers={providerInfo?.providers ?? []}
          value={provider}
          onChange={changeProvider}
        />
        <ConnectionStatus status={status} openLabel="online" />
        <a
          href="/admin"
          target="_blank"
          className="rounded-full px-[13px] py-[7px] font-semibold text-muted no-underline transition duration-200 hover:bg-white/[0.06] hover:text-white"
        >
          Admin{" "}→
        </a>
      </TopBar>

      <div className="mx-auto mb-10 mt-[30px] max-w-[1120px] px-[clamp(16px,4vw,28px)]">
        <Hero />
        <ScenarioChips scenarios={scenarios} onPick={pickScenario} />
        <div className="flex h-[66vh] min-h-[460px] flex-col overflow-hidden rounded-card border border-line bg-panel shadow-[0_20px_60px_-20px_rgba(0,0,0,0.6),0_0_90px_-50px_rgba(109,155,255,0.55),inset_0_1px_0_rgba(255,255,255,0.06)] backdrop-blur-[20px]">
          <MessageList messages={messages} typing={typing} />
          <Composer
            value={input}
            onChange={setInput}
            onSend={() => doSend(input)}
            onMicToggle={mic.toggle}
            micActive={mic.listening}
            micSupported={mic.supported}
            ttsEnabled={ttsEnabled}
            onToggleTts={toggleTts}
            sendDisabled={busy}
            inputRef={inputRef}
          />
        </div>
        <div className="mt-[14px] text-center text-[12.5px] leading-[1.6] text-faint">
          Tip: click a scenario above to auto-fill a request. Voice uses your browser's built-in
          speech (Chrome recommended). Open the{" "}
          <a
            href="/admin"
            target="_blank"
            className="text-accent no-underline hover:underline"
          >
            Admin dashboard
          </a>{" "}
          to watch the agent reason in real time.
        </div>
      </div>
    </>
  );
}
