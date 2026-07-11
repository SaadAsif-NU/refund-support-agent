/** Three-dot "Nimbus is typing" row, shown while awaiting a reply. */
export function TypingIndicator() {
  return (
    <div className="flex max-w-full items-end gap-3">
      <div className="grid h-9 w-9 flex-none place-items-center rounded-[11px] bg-linear-to-br from-accent to-accent-2 text-[18px] shadow-[0_6px_18px_-6px_rgba(109,155,255,0.6)] mb-0.5">
        ☁️
      </div>
      <div className="flex items-center gap-[5px] rounded-[18px] rounded-bl-[5px] border border-accent/20 bg-panel-2 px-[18px] py-[15px]">
        <span className="h-[7px] w-[7px] rounded-full bg-muted animate-blink" />
        <span className="h-[7px] w-[7px] rounded-full bg-muted animate-blink [animation-delay:.2s]" />
        <span className="h-[7px] w-[7px] rounded-full bg-muted animate-blink [animation-delay:.4s]" />
      </div>
    </div>
  );
}
