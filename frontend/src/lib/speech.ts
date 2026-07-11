/* Text-to-speech for spoken replies (Web Speech API). */

export function speak(text: string): void {
  if (!("speechSynthesis" in window)) return;
  const clean = text.replace(/\*\*/g, "").replace(/[#_`]/g, "");
  const utterance = new SpeechSynthesisUtterance(clean);
  utterance.rate = 1.03;
  utterance.pitch = 1.0;
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

export function cancelSpeech(): void {
  if ("speechSynthesis" in window) window.speechSynthesis.cancel();
}
