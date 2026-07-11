import type { ReactNode } from "react";

interface PillProps {
  children: ReactNode;
  className?: string;
  title?: string;
}

/** Rounded translucent pill used across both top bars. */
export function Pill({ children, className = "", title }: PillProps) {
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-2 rounded-full border border-line 
        bg-white/[0.03] px-[13px] py-[7px] text-[13px] font-medium text-muted ${className}`}
    >
      {children}
    </span>
  );
}
