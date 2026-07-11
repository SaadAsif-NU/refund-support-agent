import { useEffect, useRef } from "react";
import type { ChatMessage } from "./message";
import { MessageBubble } from "./MessageBubble";
import { TypingIndicator } from "./TypingIndicator";

interface MessageListProps {
  messages: ChatMessage[];
  typing: boolean;
}

/** Scrolling list of chat bubbles; auto-scrolls to the newest content. */
export function MessageList({ messages, typing }: MessageListProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, typing]);

  return (
    <div
      ref={scrollRef}
      className="scroll-y flex flex-1 flex-col gap-[18px] overflow-y-auto scroll-smooth px-[clamp(16px,3vw,30px)] py-[26px]"
    >
      {messages.map((message) => (
        <MessageBubble
          key={message.id}
          who={message.who}
          text={message.text}
          outcome={message.outcome}
        />
      ))}
      {typing && <TypingIndicator />}
    </div>
  );
}
