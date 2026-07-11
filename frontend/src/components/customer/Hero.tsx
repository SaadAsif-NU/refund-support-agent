/** Marketing hero above the chat card. */
export function Hero() {
  return (
    <header className="mb-[26px] text-center">
      <div className="mb-[15px] inline-flex items-center gap-[7px] rounded-full border border-accent/30 bg-accent/10 px-[14px] py-1.5 text-[11px] font-bold uppercase tracking-[1.2px] text-accent">
        ✦ AI-powered support
      </div>
      <h1 className="m-0 mb-2 bg-linear-to-b from-white to-[#b9c4e6] bg-clip-text text-[clamp(26px,4vw,40px)] font-extrabold tracking-[-0.5px] text-transparent">
        How can we help with your refund?
      </h1>
      <p className="mx-auto max-w-[620px] text-[15px] leading-[1.55] text-muted">
        Chat with Nimbus, our AI support agent. Every request is checked against NimbusMart's
        refund policy in real time - fairly, and instantly.
      </p>
    </header>
  );
}
