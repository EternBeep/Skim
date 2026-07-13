import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Link2,
  Search,
  Zap,
  Layers,
  ScanLine,
  ArrowRight,
  Video,
  Mic,
  Eye,
  Shuffle,
} from "lucide-react";
import { EncryptedText } from "./ui/EncryptedText";
import { CanvasText } from "./ui/CanvasText";

/* ─── data ──────────────────────────────────────────────────────────── */

const TIPS = [
  {
    icon: Video,
    title: "Paste any YouTube URL",
    desc: "Copy the full URL from your browser bar or share menu. Hit Index and Skim will start processing the video in the background.",
    color: "#ff4444",
  },
  {
    icon: Eye,
    title: "Search by what you see",
    desc: 'Describe a visual scene: "close-up of hands on keyboard", "sunset over the ocean", "whiteboard with diagram". CLIP understands frames visually.',
    color: "#a78bfa",
  },
  {
    icon: Mic,
    title: "Search by what was said",
    desc: 'Describe spoken content: "they talked about React hooks", "someone mentioned the price". Whisper transcribes audio and MiniLM embeds it semantically.',
    color: "#34d399",
  },
  {
    icon: Shuffle,
    title: "Mix vibes & language",
    desc: "The best searches blend both — try something like \"energetic intro with upbeat music\" or \"calm moment someone explains recursion\".",
    color: "#fbbf24",
  },
  {
    icon: Zap,
    title: "Re-indexing is instant",
    desc: "Once indexed, results are cached in Redis and Pinecone. Searching again is near-instant. Use Re-index only if the video content has changed.",
    color: "#60a5fa",
  },
];

const stagger = {
  hidden: {},
  visible: { transition: { staggerChildren: 0.07, delayChildren: 0.25 } },
};
const fadeUp = {
  hidden: { opacity: 0, y: 18 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } },
};

/* ─── Phase 1: full-screen splash ───────────────────────────────────── */

function SplashPhase({ onDone }) {
  const [encDone, setEncDone] = useState(false);

  // After the encrypt animation finishes, wait 1.4 s then advance
  useEffect(() => {
    if (!encDone) return;
    const t = setTimeout(onDone, 1400);
    return () => clearTimeout(t);
  }, [encDone, onDone]);

  return (
    <motion.div
      className="splash"
      key="splash"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, y: -24, filter: "blur(6px)" }}
      transition={{ duration: 0.55, ease: [0.16, 1, 0.3, 1] }}
    >
      {/* tiny label */}
      <motion.div
        className="splash__label"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3, duration: 0.5 }}
      >
        <span className="splash__dot" aria-hidden="true" />
        Semantic video search
      </motion.div>

      {/* main encrypted headline */}
      <motion.h1
        className="splash__title"
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5, duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      >
        <EncryptedText
          text="Welcome to Skim."
          encryptedClassName="enc-hidden"
          revealedClassName="enc-visible"
          revealDelayMs={55}
          onComplete={() => setEncDone(true)}
        />
      </motion.h1>

      {/* subtle sub-line that fades in once text is done */}
      <AnimatePresence>
        {encDone && (
          <motion.p
            className="splash__sub"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45 }}
          >
            Loading your workspace…
          </motion.p>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

/* ─── Phase 2: tips guide ────────────────────────────────────────────── */

function TipsPhase({ onContinue }) {
  return (
    <motion.div
      className="welcome__inner"
      key="tips"
      initial={{ opacity: 0, y: 32 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.97, filter: "blur(6px)" }}
      transition={{ duration: 0.55, ease: [0.16, 1, 0.3, 1] }}
    >
      {/* Badge */}
      <motion.div
        className="welcome__badge"
        initial={{ opacity: 0, scale: 0.85 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      >
        <span className="welcome__badge-dot" aria-hidden="true" />
        <ScanLine size={12} aria-hidden="true" />
        Quick start guide
      </motion.div>

      {/* Title — uses CanvasText for the "Skim" highlight */}
      <motion.div
        className="welcome__hero"
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.08, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      >
        <h2 className="welcome__title">
          How to use{" "}
          <CanvasText
            text="Skim"
            backgroundColor="#0369a1"
            colors={[
              "rgba(0, 153, 255, 0)",
              "rgba(0, 153, 255, 0.7)",
              "rgba(255,255,255,0.85)",
              "rgba(0, 153, 255, 0.7)",
              "rgba(0, 153, 255, 0)",
            ]}
            animationDuration={4}
          />
        </h2>
        <p className="welcome__subtitle">
          Semantic search inside any YouTube video — by{" "}
          <em>what was seen</em> and <em>what was said</em>. Here's everything
          you need to know.
        </p>
      </motion.div>

      {/* Step flow */}
      <motion.div
        className="welcome__flow"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.16, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      >
        {[
          { icon: Link2, label: "Paste URL" },
          { icon: Layers, label: "Index video" },
          { icon: Search, label: "Search vibes" },
          { icon: Zap, label: "Jump to moment" },
        ].map((step, i) => (
          <div key={i} className="welcome__flow-step">
            <div className="welcome__flow-icon">
              <step.icon size={16} aria-hidden="true" />
            </div>
            <span className="welcome__flow-label">{step.label}</span>
            {i < 3 && (
              <ArrowRight size={14} className="welcome__flow-arrow" aria-hidden="true" />
            )}
          </div>
        ))}
      </motion.div>

      {/* Tips grid */}
      <motion.div className="welcome__tips" variants={stagger} initial="hidden" animate="visible">
        {TIPS.map((tip) => {
          const Icon = tip.icon;
          return (
            <motion.div key={tip.title} className="tip-card" variants={fadeUp}>
              <div className="tip-card__icon" style={{ "--tip-color": tip.color }}>
                <Icon size={18} aria-hidden="true" />
              </div>
              <div className="tip-card__body">
                <div className="tip-card__title">{tip.title}</div>
                <div className="tip-card__desc">{tip.desc}</div>
              </div>
            </motion.div>
          );
        })}
      </motion.div>

      {/* CTA */}
      <motion.div
        className="welcome__cta"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.65, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
      >
        <button id="welcome-continue-btn" className="btn btn--continue" onClick={onContinue}>
          Let's go
          <ArrowRight size={16} aria-hidden="true" />
        </button>
        <p className="welcome__skip">This guide won't show again after you continue.</p>
      </motion.div>
    </motion.div>
  );
}

/* ─── Root export ────────────────────────────────────────────────────── */

export default function WelcomeScreen({ onContinue }) {
  const [phase, setPhase] = useState("splash"); // "splash" | "tips"

  return (
    <motion.div
      className="welcome"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, scale: 0.98, filter: "blur(8px)" }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="welcome__glow welcome__glow--1" aria-hidden="true" />
      <div className="welcome__glow welcome__glow--2" aria-hidden="true" />
      <div className="welcome__noise" aria-hidden="true" />

      <AnimatePresence mode="wait">
        {phase === "splash" ? (
          <SplashPhase key="splash" onDone={() => setPhase("tips")} />
        ) : (
          <TipsPhase key="tips" onContinue={onContinue} />
        )}
      </AnimatePresence>
    </motion.div>
  );
}
