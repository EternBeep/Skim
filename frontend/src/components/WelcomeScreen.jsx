import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowRight } from "lucide-react";
import { EncryptedText } from "./ui/EncryptedText";
import { AuroraBackground } from "./ui/AuroraBackground";
import { FloatingParticles } from "./ui/FloatingParticles";

/**
 * WelcomeScreen — single splash page
 *
 * Flow:
 *  1. "Welcome to" fades in
 *  2. "Skim." does the encrypted character-by-character reveal
 *  3. Blinking cursor + tagline appear
 *  4. "Enter Skim →" button fades in
 *  5. User clicks → main app
 */
export default function WelcomeScreen({ onContinue }) {
  const [encDone, setEncDone] = useState(false);

  return (
    <motion.div
      className="welcome"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, scale: 0.97, filter: "blur(12px)" }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
    >
      <AuroraBackground />
      <FloatingParticles />

      <div className="splash">
        {/* small label */}
        <motion.div
          className="splash__label"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3, duration: 0.6 }}
        >
          <span className="splash__dot" aria-hidden="true" />
          Semantic video search
        </motion.div>

        {/* headline: two lines */}
        <div className="splash__headline">
          {/* "Welcome to" — fades in first */}
          <motion.div
            className="splash__pre"
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          >
            Welcome to
          </motion.div>

          {/* "Skim." — encrypted reveal, starts after 1.2s so it's fully visible */}
          <motion.h1
            className="splash__title"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.9, duration: 0.3 }}
          >
            <EncryptedText
              text="Skim."
              encryptedClassName="enc-hidden"
              revealedClassName="enc-visible"
              revealDelayMs={180}
              startDelayMs={1200}
              onComplete={() => setEncDone(true)}
            />
            {/* blinking cursor after reveal */}
            <AnimatePresence>
              {encDone && (
                <motion.span
                  className="splash__cursor"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  aria-hidden="true"
                >
                  |
                </motion.span>
              )}
            </AnimatePresence>
          </motion.h1>
        </div>

        {/* CTA button — appears after reveal */}
        <AnimatePresence>
          {encDone && (
            <motion.div
              className="splash__cta"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.4 }}
            >
              <button
                id="welcome-enter-btn"
                className="btn btn--enter"
                onClick={onContinue}
              >
                Enter Skim
                <ArrowRight size={18} aria-hidden="true" />
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
