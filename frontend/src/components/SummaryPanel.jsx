import { motion } from "framer-motion";
import { FileText, Music2, Sparkles, Film } from "lucide-react";

const SOURCE_ICONS = {
  ai: Sparkles,
  metadata: Film,
  transcript: FileText,
};

const SOURCE_LABELS = {
  ai: "Summary · AI-written",
  metadata: "Summary · from video details",
  transcript: "Summary · from transcript",
};

export default function SummaryPanel({ data, hasTranscript }) {
  if (!data?.summary) {
    return (
      <motion.section
        className="card summary-panel summary-panel--empty"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      >
        <Music2 size={18} aria-hidden="true" color="var(--text-muted)" />
        <p>
          {hasTranscript
            ? "No summary available for this video."
            : "No speech detected — this looks like a music or instrumental video. The beat analysis below still works."}
        </p>
      </motion.section>
    );
  }

  const keywords = data.keywords || [];
  const Icon = SOURCE_ICONS[data.source] || FileText;

  return (
    <motion.section
      className="card summary-panel"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="summary-panel__rail" aria-hidden="true" />
      <div className="summary-panel__header">
        <Icon size={16} aria-hidden="true" color="var(--text-secondary)" />
        <span className="summary-panel__tag">
          {SOURCE_LABELS[data.source] || SOURCE_LABELS.transcript}
        </span>
      </div>
      <p className="summary-panel__text">{data.summary}</p>
      {keywords.length > 0 && (
        <div className="summary-panel__keywords">
          {keywords.map((k) => (
            <span key={k} className="keyword">
              #{k}
            </span>
          ))}
        </div>
      )}
    </motion.section>
  );
}
