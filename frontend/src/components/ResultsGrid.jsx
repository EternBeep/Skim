import { motion } from "framer-motion";
import { Eye, Mic, Sparkles, Film, ExternalLink } from "lucide-react";
import { formatTime } from "../utils/format";

const SOURCE_CONFIG = {
  visual: { label: "Visual", Icon: Eye },
  spoken: { label: "Spoken", Icon: Mic },
  both: { label: "Seen + Said", Icon: Sparkles },
};

const container = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.06 },
  },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.35, ease: [0.16, 1, 0.3, 1] },
  },
};

export default function ResultsGrid({ results, query }) {
  if (!results.length) return null;

  return (
    <div>
      <div className="results-header">
        Top {results.length} matches for &ldquo;{query}&rdquo;
      </div>
      <motion.div
        className="results-grid"
        variants={container}
        initial="hidden"
        animate="visible"
      >
        {results.map((r, i) => {
          const source = SOURCE_CONFIG[r.match_source] || SOURCE_CONFIG.visual;
          const SourceIcon = source.Icon;

          return (
            <motion.a
              key={`${r.timestamp}-${i}`}
              href={r.youtube_url}
              target="_blank"
              rel="noreferrer"
              className="result-card"
              variants={item}
              whileHover={{ y: -3 }}
              whileTap={{ scale: 0.98 }}
            >
              <div className="result-card__thumb">
                {r.thumbnail_url ? (
                  <img src={r.thumbnail_url} alt={`Frame at ${formatTime(r.timestamp)}`} loading="lazy" />
                ) : (
                  <Film size={28} className="result-card__thumb-placeholder" aria-hidden="true" />
                )}
                {r.match_source && (
                  <span className="result-card__source">
                    <SourceIcon size={11} aria-hidden="true" />
                    {source.label}
                  </span>
                )}
                <span className="result-card__score">
                  {(r.score * 100).toFixed(1)}
                </span>
              </div>
              <div className="result-card__body">
                <div className="result-card__time">{formatTime(r.timestamp)}</div>
                {r.transcript ? (
                  <div className="result-card__transcript">&ldquo;{r.transcript}&rdquo;</div>
                ) : (
                  <div className="result-card__hint">
                    Open at this moment <ExternalLink size={10} style={{ display: "inline", verticalAlign: "middle" }} aria-hidden="true" />
                  </div>
                )}
              </div>
            </motion.a>
          );
        })}
      </motion.div>
    </div>
  );
}
