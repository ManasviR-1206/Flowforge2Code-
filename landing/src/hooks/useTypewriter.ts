import { useState, useEffect } from 'react';

export function useTypewriter(
  fullText: string = "Draw it. Understand it. Generate it. Run it.",
  speedMs: number = 38,
  startDelayMs: number = 600
) {
  const [displayedText, setDisplayedText] = useState("");
  const [isTypingComplete, setIsTypingComplete] = useState(false);

  useEffect(() => {
    let timeoutId: ReturnType<typeof setTimeout>;
    let charIndex = 0;

    const startTimeout = setTimeout(() => {
      const typeNextChar = () => {
        if (charIndex <= fullText.length) {
          setDisplayedText(fullText.slice(0, charIndex));
          charIndex++;
          if (charIndex <= fullText.length) {
            timeoutId = setTimeout(typeNextChar, speedMs);
          } else {
            setIsTypingComplete(true);
          }
        }
      };
      typeNextChar();
    }, startDelayMs);

    return () => {
      clearTimeout(startTimeout);
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [fullText, speedMs, startDelayMs]);

  return { displayedText, isTypingComplete };
}
