import type { ReactNode } from "react";

interface TopBarProps {
  logo: string;
  title: string;
  subtitle: string;
  children: ReactNode; // right-hand controls
}

/** Sticky, blurred top bar with a gradient brand logo and a right-side slot. */
export function TopBar({ logo, title, subtitle, children }: TopBarProps) {
  return (
    <div className="sticky top-0 z-20 flex items-center justify-between gap-[14px] border-b border-line 
    bg-[rgba(12,17,32,0.6)] px-[clamp(16px,4vw,34px)] py-[14px] backdrop-blur-[14px] backdrop-saturate-[1.4]">
      <div className="flex items-center gap-[13px] text-[15.5px] font-bold tracking-[.1px]">
        <div className="relative grid h-10 w-10 place-items-center rounded-xl bg-linear-to-br from-accent 
        to-accent-2 text-[20px] shadow-[0_6px_20px_-4px_rgba(109,155,255,0.55)] after:absolute after:-inset-[3px] 
        after:-z-10 after:rounded-[14px] after:bg-linear-to-br after:from-accent after:to-accent-2 after:opacity-55 
        after:blur-[12px] after:content-[''] after:animate-glow">
          {logo}
        </div>
        <div>
          {title}
          <small className="mt-px block text-[12px] font-medium text-muted">{subtitle}</small>
        </div>
      </div>
      <div className="flex items-center gap-3 text-[13px]">{children}</div>
    </div>
  );
}
