import type { RefObject } from "react";

interface ComposerProps {
  value: string;
  onChange: (value: string) => void;
  onSend: () => void;
  onMicToggle: () => void;
  micActive: boolean;
  micSupported: boolean;
  ttsEnabled: boolean;
  onToggleTts: () => void;
  sendDisabled: boolean;
  inputRef?: RefObject<HTMLInputElement | null>;
}

const ICON_BTN =
  "grid w-[50px] place-items-center rounded-[13px] border border-line bg-white/[0.04] text-[19px] text-ink transition duration-200 cursor-pointer enabled:hover:border-line-strong enabled:hover:bg-white/[0.08] disabled:cursor-not-allowed disabled:opacity-40";

/** Input row: mic, TTS toggle, text field, and send button. */
export function Composer({
  value,
  onChange,
  onSend,
  onMicToggle,
  micActive,
  micSupported,
  ttsEnabled,
  onToggleTts,
  sendDisabled,
  inputRef,
}: ComposerProps) {
  return (
    <div className="flex gap-[10px] border-t border-line bg-[rgba(9,12,21,0.35)] px-[clamp(14px,3vw,20px)] py-4">
      <button
        type="button"
        onClick={onMicToggle}
        disabled={!micSupported}
        title={micSupported ? "Speak your request" : "Voice input needs Chrome or Edge"}
        className={`${ICON_BTN} ${micActive ? "border-red bg-red text-white animate-mic" : ""}`}
      >
        🎙️
      </button>
      <button
        type="button"
        onClick={onToggleTts}
        title="Toggle spoken replies"
        className={`${ICON_BTN} ${ttsEnabled ? "border-green/50 text-green" : ""}`}
      >
        {ttsEnabled ? "🔊" : "🔈"}
      </button>
      <input
        ref={inputRef}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter") onSend();
        }}
        placeholder="Type your message, or tap the mic to speak…"
        autoComplete="off"
        className="flex-1 rounded-[13px] border border-line bg-white/[0.04] px-4 py-[14px] text-[15px] text-ink outline-none transition duration-200 placeholder:text-faint focus:border-accent/60 focus:bg-accent/[0.06] focus:shadow-[0_0_0_4px_rgba(109,155,255,0.12)]"
      />
      <button
        type="button"
        onClick={onSend}
        disabled={sendDisabled}
        className="cursor-pointer rounded-[13px] bg-linear-to-br from-accent to-accent-2 px-[22px] text-[14.5px] font-bold text-white shadow-[0_10px_24px_-10px_rgba(109,155,255,0.8)] transition enabled:hover:-translate-y-px enabled:hover:brightness-110 enabled:active:translate-y-0 enabled:active:scale-[.98] disabled:cursor-not-allowed disabled:opacity-45"
      >
        Send
      </button>
    </div>
  );
}
