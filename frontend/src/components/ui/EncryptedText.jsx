import { useState, useEffect } from "react";

const POOL =
  "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%&*<>?/{}[]";
const rnd = () => POOL[Math.floor(Math.random() * POOL.length)];

/**
 * EncryptedText — scrambles characters then reveals them left-to-right.
 *
 * Props:
 *  text              — the string to reveal
 *  encryptedClassName — className while character is still scrambling
 *  revealedClassName  — className once character is locked in
 *  revealDelayMs      — ms between each character reveal (default 100)
 *  startDelayMs       — ms to wait before starting the effect (default 0)
 *  onComplete         — callback fired when all characters are revealed
 */
export function EncryptedText({
  text,
  encryptedClassName = "enc-hidden",
  revealedClassName = "enc-visible",
  revealDelayMs = 100,
  startDelayMs = 0,
  onComplete,
}) {
  const [state, setState] = useState(() => ({
    chars: text.split("").map((c) => (c === " " ? " " : rnd())),
    revealed: new Array(text.length).fill(false),
  }));

  const [started, setStarted] = useState(startDelayMs === 0);

  // Handle the start delay
  useEffect(() => {
    if (startDelayMs <= 0) return;
    const t = setTimeout(() => setStarted(true), startDelayMs);
    return () => clearTimeout(t);
  }, [startDelayMs]);

  // Run the actual scramble + reveal only after started is true
  useEffect(() => {
    if (!started) return;

    const mask = new Array(text.length).fill(false);
    let idx = 0;

    // Continuously randomise unrevealed positions
    const scrambleId = setInterval(() => {
      setState((prev) => ({
        ...prev,
        chars: text
          .split("")
          .map((c, i) => (mask[i] ? c : c === " " ? " " : rnd())),
      }));
    }, 60);

    // Reveal one character at a time
    const revealId = setInterval(() => {
      if (idx >= text.length) {
        clearInterval(revealId);
        clearInterval(scrambleId);
        setState({
          chars: text.split(""),
          revealed: new Array(text.length).fill(true),
        });
        onComplete?.();
        return;
      }
      mask[idx] = true;
      const i = idx;
      setState((prev) => {
        const chars = [...prev.chars];
        const revealed = [...prev.revealed];
        chars[i] = text[i];
        revealed[i] = true;
        return { chars, revealed };
      });
      idx++;
    }, revealDelayMs);

    return () => {
      clearInterval(scrambleId);
      clearInterval(revealId);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [started]);

  return (
    <span aria-label={text} role="text">
      {state.chars.map((ch, i) => (
        <span key={i} className={state.revealed[i] ? revealedClassName : encryptedClassName}>
          {ch}
        </span>
      ))}
    </span>
  );
}
