import { useEffect, useRef, useState } from "react";

interface Options {
  /** Live transcript (interim + final so far) as the user speaks. */
  onTranscript: (text: string) => void;
  /** Final transcript, emitted once recognition ends with non-empty speech. */
  onFinal: (text: string) => void;
}

/**
 * Wraps the browser SpeechRecognition API (Chrome/Edge). Exposes whether it is
 * supported, whether it is currently listening, and a toggle to start/stop.
 */
export function useSpeechRecognition({ onTranscript, onFinal }: Options) {
  const Ctor =
    typeof window !== "undefined"
      ? window.SpeechRecognition ?? window.webkitSpeechRecognition
      : undefined;
  const supported = Boolean(Ctor);

  const [listening, setListening] = useState(false);
  const recogRef = useRef<SpeechRecognition | null>(null);
  const finalRef = useRef("");
  const callbacksRef = useRef({ onTranscript, onFinal });
  callbacksRef.current = { onTranscript, onFinal };

  useEffect(() => {
    if (!Ctor) return;
    const recog = new Ctor();
    recog.lang = "en-US";
    recog.interimResults = true;
    recog.continuous = false;

    recog.onstart = () => setListening(true);
    recog.onend = () => {
      setListening(false);
      const finalText = finalRef.current.trim();
      if (finalText) callbacksRef.current.onFinal(finalText);
    };
    recog.onerror = () => setListening(false);
    recog.onresult = (event) => {
      let interim = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) finalRef.current += transcript;
        else interim += transcript;
      }
      callbacksRef.current.onTranscript((finalRef.current + interim).trim());
    };

    recogRef.current = recog;
    return () => {
      recog.onstart = recog.onend = recog.onerror = recog.onresult = null;
      try {
        recog.stop();
      } catch {
        /* not started */
      }
      recogRef.current = null;
    };
  }, [Ctor]);

  const toggle = () => {
    const recog = recogRef.current;
    if (!recog) return;
    if (listening) {
      recog.stop();
      return;
    }
    finalRef.current = "";
    try {
      recog.start();
    } catch {
      /* already started */
    }
  };

  return { supported, listening, toggle };
}
