import type { Outcome } from "../../types/api";
import type { Sender } from "./MessageBubble";

export interface ChatMessage {
  id: number;
  who: Sender;
  text: string;
  outcome?: Outcome | null;
}
