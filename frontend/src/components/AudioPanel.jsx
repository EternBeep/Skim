import { motion } from "framer-motion";
import { Activity, Flame, Zap } from "lucide-react";
import { formatTime } from "../utils/format";

export default function AudioPanel({ data }) {
  if (!data) return null;

  const beats = data.beat_times || [];
  const peaks = data.energy_peaks || [];
  const duration = data.duration || (beats.length ? beats[beats.length - 1] : 1);

  return (
    <motion.section
      className="card"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.05, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="audio-panel__header">
        <div className="card__label" style={{ marginBottom: 0 }}>
          <Activity size={14} aria-hidden="true" />
          Audio analysis
        </div>
        {data.tempo ? (
          <div className="audio-panel__bpm">
            {Math.round(data.tempo)} <span>BPM</span>
          </div>
        ) : null}
      </div>

      {beats.length > 0 && (
        <div className="beat-timeline" aria-label="Beat timeline">
          {beats.map((t, i) => (
            <div
              key={i}
              className="beat-timeline__tick"
              style={{ left: `${(t / duration) * 100}%` }}
            />
          ))}
          {peaks.map((p, i) => (
            <div
              key={`p${i}`}
              className={`beat-timeline__peak${i === 0 ? " beat-timeline__peak--top" : ""}`}
              style={{ left: `${(p.timestamp / duration) * 100}%` }}
              title={formatTime(p.timestamp)}
            />
          ))}
        </div>
      )}

      <div className="section-label">Highest-energy moments</div>
      <div className="energy-chips">
        {peaks.length === 0 ? (
          <span className="status-meta">No clear energy peaks detected.</span>
        ) : (
          peaks.map((p, i) => (
            <a
              key={i}
              href={p.youtube_url}
              target="_blank"
              rel="noreferrer"
              className={`energy-chip${i === 0 ? " energy-chip--top" : ""}`}
            >
              {i === 0 ? (
                <Flame size={16} aria-hidden="true" color="var(--text-primary)" />
              ) : (
                <Zap size={16} aria-hidden="true" color="var(--text-muted)" />
              )}
              <div>
                <div className="energy-chip__time">{formatTime(p.timestamp)}</div>
                <div className="energy-chip__label">
                  {i === 0 ? "Peak energy" : `Energy ${p.energy.toFixed(2)}`}
                </div>
              </div>
            </a>
          ))
        )}
      </div>
    </motion.section>
  );
}
