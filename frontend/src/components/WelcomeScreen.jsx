import { motion, AnimatePresence } from "framer-motion";
import {
  Link2,
  Search,
  Zap,
  Layers,
  ScanLine,
  ArrowRight,
  Youtube,
  Mic,
  Eye,
  Shuffle,
} from "lucide-react";

const TIPS = [
  {
    icon: Youtube,
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

const container = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.07, delayChildren: 0.3 },
  },
};

const item = {
  hidden: { opacity: 0, y: 18 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] },
  },
};

export default function WelcomeScreen({ onContinue }) {
  return (
    <motion.div
      className="welcome"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0, scale: 0.98, filter: "blur(8px)" }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
    >
      {/* Background glows */}
      <div className="welcome__glow welcome__glow--1" aria-hidden="true" />
      <div className="welcome__glow welcome__glow--2" aria-hidden="true" />
      <div className="welcome__noise" aria-hidden="true" />

      <div className="welcome__inner">
        {/* Badge */}
        <motion.div
          className="welcome__badge"
          initial={{ opacity: 0, scale: 0.85 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
        >
          <span className="welcome__badge-dot" aria-hidden="true" />
          <ScanLine size={12} aria-hidden="true" />
          Quick start guide
        </motion.div>

        {/* Title */}
        <motion.div
          className="welcome__hero"
          initial={{ opacity: 0, y: 28 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
        >
          <h1 className="welcome__title">
            How to use
            <span className="welcome__title-accent"> Skim</span>
          </h1>
          <p className="welcome__subtitle">
            Semantic search inside any YouTube video — by{" "}
            <em>what was seen</em> and <em>what was said</em>. Here's everything
            you need to know.
          </p>
        </motion.div>

        {/* Steps flow */}
        <motion.div
          className="welcome__flow"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
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
                <ArrowRight
                  size={14}
                  className="welcome__flow-arrow"
                  aria-hidden="true"
                />
              )}
            </div>
          ))}
        </motion.div>

        {/* Tips grid */}
        <motion.div
          className="welcome__tips"
          variants={container}
          initial="hidden"
          animate="visible"
        >
          {TIPS.map((tip) => {
            const Icon = tip.icon;
            return (
              <motion.div key={tip.title} className="tip-card" variants={item}>
                <div
                  className="tip-card__icon"
                  style={{ "--tip-color": tip.color }}
                >
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
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.75, ease: [0.16, 1, 0.3, 1] }}
        >
          <button
            id="welcome-continue-btn"
            className="btn btn--continue"
            onClick={onContinue}
          >
            Let's go
            <ArrowRight size={16} aria-hidden="true" />
          </button>
          <p className="welcome__skip">
            This guide won't show again after you continue.
          </p>
        </motion.div>
      </div>
    </motion.div>
  );
}
