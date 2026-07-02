import { useState, useRef, useEffect } from "react";

// Week 3: API base comes from the build-time env var so the same bundle can point
// at localhost in dev and the Hugging Face Space in production (set in Vercel).
const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

function formatTime(sec) {
  const m = Math.floor(sec / 60).toString().padStart(2, "0");
  const s = Math.floor(sec % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

// How each hybrid-search match source is labelled on a result card.
const SOURCE_META = {
  visual: { icon: "👁", label: "Visual", color: "#a78bfa", bg: "rgba(124,58,237,0.15)" },
  spoken: { icon: "🗣", label: "Spoken", color: "#5DCAA5", bg: "rgba(15,110,86,0.18)" },
  both:   { icon: "✦", label: "Seen + Said", color: "#f0997b", bg: "rgba(236,72,153,0.15)" },
};

function StatusBadge({ status }) {
  const map = {
    queued: { label: "Queued", color: "#888780", bg: "#F1EFE8" },
    downloading: { label: "Downloading…", color: "#185FA5", bg: "#E6F1FB" },
    embedding: { label: "Embedding frames…", color: "#3B6D11", bg: "#EAF3DE" },
    transcribing: { label: "Transcribing audio…", color: "#0F6E56", bg: "#E1F5EE" },
    uploading: { label: "Uploading thumbnails…", color: "#185FA5", bg: "#E6F1FB" },
    analyzing: { label: "Analyzing beats…", color: "#6B3FA0", bg: "#EEE6FA" },
    storing: { label: "Saving vectors…", color: "#185FA5", bg: "#E6F1FB" },
    done: { label: "Ready", color: "#0F6E56", bg: "#E1F5EE" },
    error: { label: "Error", color: "#993C1D", bg: "#FAECE7" },
  };
  const { label, color, bg } = map[status] || map.queued;
  return (
    <span style={{
      fontSize: 12, fontWeight: 500, padding: "3px 10px",
      borderRadius: 20, background: bg, color, letterSpacing: "0.02em"
    }}>{label}</span>
  );
}

function SourceBadge({ source }) {
  const meta = SOURCE_META[source] || SOURCE_META.visual;
  return (
    <div style={{
      position: "absolute", top: 8, left: 8,
      background: meta.bg, borderRadius: 20,
      padding: "2px 9px", fontSize: 10.5, color: meta.color, fontWeight: 600,
      display: "flex", alignItems: "center", gap: 4, backdropFilter: "blur(4px)",
    }}>
      <span style={{ fontSize: 11 }}>{meta.icon}</span>{meta.label}
    </div>
  );
}

// "What's this about" panel — the extractive transcript summary + topic
// keywords, shown the moment a video finishes indexing.
function SummaryPanel({ data, hasTranscript }) {
  const keywords = (data && data.keywords) || [];

  // No transcript means there was no speech to summarise (e.g. a music video).
  // Say so explicitly instead of silently rendering nothing.
  if (!data || !data.summary) {
    return (
      <section style={{
        background: "#16161d", border: "1px solid #2a2a38",
        borderRadius: 16, padding: "18px 28px", marginBottom: 16,
        display: "flex", alignItems: "center", gap: 10,
        animation: "fadeUp 0.4s ease both",
      }}>
        <span style={{ fontSize: 14, opacity: 0.7 }}>🎵</span>
        <div style={{ fontSize: 13, color: "#888896", lineHeight: 1.5 }}>
          {hasTranscript
            ? "No summary available for this video."
            : "No speech detected — this looks like a music or instrumental video, so there's nothing to summarise. The beat analysis below still works."}
        </div>
      </section>
    );
  }

  return (
    <section style={{
      position: "relative", overflow: "hidden",
      background: "#16161d", border: "1px solid #2a2a38",
      borderRadius: 16, padding: "24px 28px", marginBottom: 16,
      animation: "fadeUp 0.4s ease both",
    }}>
      {/* Gradient accent rail down the left edge */}
      <div style={{
        position: "absolute", left: 0, top: 0, bottom: 0, width: 3,
        background: "linear-gradient(180deg, #a78bfa 0%, #ec4899 55%, #f97316 100%)",
      }} />
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
        <span style={{ fontSize: 14 }}>
          {data.source === "ai" ? "✨" : data.source === "metadata" ? "🎬" : "📝"}
        </span>
        <div style={{ fontSize: 11, color: "#7c5cbf", fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase" }}>
          {data.source === "ai" ? "Summary · AI-written"
            : data.source === "metadata" ? "Summary · from video details"
            : "Summary · from transcript"}
        </div>
      </div>

      <p style={{ fontSize: 14.5, color: "#cdc9e0", lineHeight: 1.65, marginBottom: keywords.length ? 16 : 0 }}>
        {data.summary}
      </p>

      {keywords.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {keywords.map(k => (
            <span key={k} style={{
              background: "#1e1e28", border: "1px solid #2a2a38",
              color: "#9a8fc0", borderRadius: 20, padding: "4px 12px",
              fontSize: 12, fontWeight: 500,
            }}>#{k}</span>
          ))}
        </div>
      )}
    </section>
  );
}

// Beats + top energy moments panel, shown once a video is indexed.
function AudioPanel({ data }) {
  if (!data) return null;
  const beats = data.beat_times || [];
  const peaks = data.energy_peaks || [];
  const duration = data.duration || (beats.length ? beats[beats.length - 1] : 1);

  return (
    <section style={{
      background: "#16161d", border: "1px solid #2a2a38",
      borderRadius: 16, padding: "24px 28px", marginBottom: 24,
      animation: "fadeUp 0.4s ease both",
    }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 16 }}>
        <div style={{ fontSize: 11, color: "#7c5cbf", fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase" }}>
          Audio analysis · librosa
        </div>
        {data.tempo ? (
          <div style={{ fontFamily: "'Space Mono', monospace", fontSize: 13, color: "#c4b5fd" }}>
            {Math.round(data.tempo)} <span style={{ color: "#666672", fontSize: 11 }}>BPM</span>
          </div>
        ) : null}
      </div>

      {/* Beat timeline — a tick per detected beat across the duration */}
      {beats.length > 0 && (
        <div style={{
          position: "relative", height: 34, background: "#0e0e14",
          border: "1px solid #2a2a38", borderRadius: 8, overflow: "hidden", marginBottom: 16,
        }}>
          {beats.map((t, i) => (
            <div key={i} style={{
              position: "absolute", top: 6, bottom: 6, width: 1,
              left: `${(t / duration) * 100}%`, background: "#3a2f5e",
            }} />
          ))}
          {peaks.map((p, i) => (
            <div key={`p${i}`} title={`${formatTime(p.timestamp)}`} style={{
              position: "absolute", top: 0, bottom: 0, width: 2,
              left: `${(p.timestamp / duration) * 100}%`,
              background: i === 0 ? "#f97316" : "#ec4899",
              boxShadow: i === 0 ? "0 0 8px #f97316" : "none",
            }} />
          ))}
        </div>
      )}

      {/* Top energy moments as jump-to chips */}
      <div style={{ fontSize: 11, color: "#555560", marginBottom: 10, letterSpacing: "0.05em" }}>
        Highest-energy moments
      </div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
        {peaks.map((p, i) => (
          <a key={i} href={p.youtube_url} target="_blank" rel="noreferrer"
            style={{
              display: "flex", alignItems: "center", gap: 8, textDecoration: "none",
              background: i === 0 ? "#2a1810" : "#1e1e28",
              border: `1px solid ${i === 0 ? "#7a3a18" : "#2a2a38"}`,
              borderRadius: 10, padding: "8px 14px",
            }}>
            <span style={{ fontSize: 15 }}>{i === 0 ? "🔥" : "⚡"}</span>
            <div>
              <div style={{
                fontFamily: "'Space Mono', monospace", fontSize: 14, fontWeight: 700,
                color: i === 0 ? "#fbbf24" : "#f0eeff",
              }}>{formatTime(p.timestamp)}</div>
              <div style={{ fontSize: 10, color: "#666672" }}>
                {i === 0 ? "Peak energy" : `Energy ${p.energy.toFixed(2)}`}
              </div>
            </div>
          </a>
        ))}
        {peaks.length === 0 && (
          <span style={{ fontSize: 12, color: "#555560" }}>No clear energy peaks detected.</span>
        )}
      </div>
    </section>
  );
}

export default function App() {
  const [url, setUrl] = useState("");
  const [jobId, setJobId] = useState(null);
  const [jobStatus, setJobStatus] = useState(null);
  const [videoId, setVideoId] = useState(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [searching, setSearching] = useState(false);
  const [indexing, setIndexing] = useState(false);
  const [error, setError] = useState("");
  const [audio, setAudio] = useState(null);
  const pollRef = useRef(null);

  useEffect(() => {
    if (!jobId) return;
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API}/status/${jobId}`);
        const data = await res.json();
        setJobStatus(data);
        if (data.status === "done") {
          setVideoId(data.video_id);
          setIndexing(false);
          clearInterval(pollRef.current);
        } else if (data.status === "error") {
          setError(data.error || "Indexing failed");
          setIndexing(false);
          clearInterval(pollRef.current);
        }
      } catch { /* server might not be running in demo */ }
    }, 1500);
    return () => clearInterval(pollRef.current);
  }, [jobId]);

  // Once a video is indexed, pull its beat/energy analysis. (Audio is already
  // reset to null in handleIndex before any new videoId arrives.)
  useEffect(() => {
    if (!videoId) return;
    fetch(`${API}/audio-analysis/${videoId}`)
      .then(r => (r.ok ? r.json() : null))
      .then(setAudio)
      .catch(() => {});
  }, [videoId]);

  async function handleIndex(force = false) {
    if (!url.trim()) return;
    setError(""); setResults([]); setJobStatus(null); setVideoId(null); setAudio(null);
    setIndexing(true);
    try {
      const res = await fetch(`${API}/index`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        // force=true re-processes from scratch, bypassing the cached entry.
        body: JSON.stringify({ youtube_url: url, interval_sec: 2.0, force }),
      });
      const data = await res.json();
      setJobId(data.job_id);
    } catch {
      setError("Cannot reach backend. Start the FastAPI server first.");
      setIndexing(false);
    }
  }

  async function handleSearch() {
    if (!videoId || !query.trim()) return;
    setSearching(true); setError("");
    try {
      const res = await fetch(`${API}/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_id: videoId, query, top_k: 6 }),
      });
      const data = await res.json();
      setResults(data.results || []);
    } catch {
      setError("Search failed. Is the server running?");
    }
    setSearching(false);
  }

  return (
    <div style={{
      minHeight: "100vh", background: "#0e0e11",
      fontFamily: "'DM Sans', system-ui, sans-serif",
      color: "#e8e6f0", padding: "0 0 80px",
    }}>
      {/* Google Font */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=Space+Mono:wght@700&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::placeholder { color: #555560; }
        input:focus { outline: none; }
        button:hover { opacity: 0.85; }
        button:active { transform: scale(0.97); }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.45} }
        @keyframes fadeUp { from{opacity:0;transform:translateY(12px)} to{opacity:1;transform:translateY(0)} }
        .result-card { animation: fadeUp 0.35s ease both; }
        .result-card:hover { background: #1e1e26 !important; }
      `}</style>

      {/* Header */}
      <div style={{ textAlign: "center", padding: "64px 24px 40px" }}>
        <div style={{
          display: "inline-block", fontFamily: "'Space Mono', monospace",
          fontSize: 11, letterSpacing: "0.2em", color: "#7c5cbf",
          background: "#1a1330", padding: "4px 14px", borderRadius: 4,
          border: "1px solid #2e2250", marginBottom: 20, textTransform: "uppercase"
        }}>Week 3 build · CLIP + Whisper + librosa · Pinecone + Cloudinary + Redis</div>
        <h1 style={{
          fontFamily: "'Space Mono', monospace", fontSize: "clamp(36px,6vw,64px)",
          fontWeight: 700, letterSpacing: "-0.02em",
          background: "linear-gradient(135deg, #a78bfa 0%, #ec4899 55%, #f97316 100%)",
          WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
          lineHeight: 1.1, marginBottom: 12,
        }}>Skim</h1>
        <p style={{ color: "#888896", fontSize: 16, maxWidth: 440, margin: "0 auto" }}>
          Paste a YouTube URL. Describe a vibe. Jump to that moment — by what was seen <i>and</i> what was said.
        </p>
      </div>

      <div style={{ maxWidth: 720, margin: "0 auto", padding: "0 20px" }}>

        {/* Step 1 — Index */}
        <section style={{
          background: "#16161d", border: "1px solid #2a2a38",
          borderRadius: 16, padding: "28px 28px 24px", marginBottom: 16,
        }}>
          <div style={{ fontSize: 11, color: "#7c5cbf", fontWeight: 600, letterSpacing: "0.12em", marginBottom: 16, textTransform: "uppercase" }}>
            Step 1 · Index video
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <input
              value={url}
              onChange={e => setUrl(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleIndex()}
              placeholder="https://www.youtube.com/watch?v=..."
              style={{
                flex: 1, background: "#0e0e14", border: "1px solid #2a2a38",
                borderRadius: 10, padding: "11px 16px", fontSize: 14, color: "#e8e6f0",
              }}
            />
            <button onClick={() => handleIndex()} disabled={indexing || !url}
              style={{
                background: indexing ? "#2a1f4a" : "#7c3aed",
                color: "#fff", border: "none", borderRadius: 10,
                padding: "11px 22px", fontSize: 14, fontWeight: 600, cursor: "pointer",
                whiteSpace: "nowrap", transition: "all 0.15s",
                opacity: !url ? 0.4 : 1,
              }}>
              {indexing ? "Indexing…" : "Index"}
            </button>
          </div>

          {jobStatus && (
            <div style={{ marginTop: 16, display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
              <StatusBadge status={jobStatus.status} />
              {jobStatus.status === "embedding" && jobStatus.total_frames && (
                <span style={{ fontSize: 12, color: "#666672" }}>
                  {jobStatus.total_frames} frames to embed
                </span>
              )}
              {jobStatus.status === "done" && (
                <>
                  <span style={{ fontSize: 12, color: "#5DCAA5" }}>
                    ✓ {jobStatus.frame_count} frames
                    {jobStatus.has_transcript
                      ? ` · ${jobStatus.transcript_chunks} transcript chunks`
                      : " · no speech detected"}
                    {" "}· video_id: {jobStatus.video_id}
                  </span>
                  {/* Re-process from scratch, ignoring the cached entry. */}
                  <button onClick={() => handleIndex(true)} disabled={indexing || !url}
                    title="Re-process this video from scratch, ignoring the cache"
                    style={{
                      background: "transparent", color: "#888896",
                      border: "1px solid #2a2a38", borderRadius: 20,
                      padding: "3px 12px", fontSize: 12, cursor: "pointer",
                      fontFamily: "inherit", display: "flex", alignItems: "center", gap: 5,
                    }}>
                    ↻ Re-index
                  </button>
                </>
              )}
              {(jobStatus.status === "downloading" || jobStatus.status === "transcribing" || jobStatus.status === "analyzing") && (
                <span style={{ fontSize: 12, color: "#888896", animation: "pulse 1.4s infinite" }}>
                  {jobStatus.status === "downloading" && "Fetching video from YouTube…"}
                  {jobStatus.status === "transcribing" && "Whisper is listening…"}
                  {jobStatus.status === "analyzing" && "Finding the beat…"}
                </span>
              )}
            </div>
          )}
        </section>

        {/* Summary panel — the gist of what was said */}
        {jobStatus?.status === "done" &&
          <SummaryPanel data={jobStatus.summary} hasTranscript={jobStatus.has_transcript} />}

        {/* Audio analysis panel */}
        {videoId && <AudioPanel data={audio} />}

        {/* Step 2 — Search */}
        <section style={{
          background: "#16161d", border: "1px solid #2a2a38",
          borderRadius: 16, padding: "28px 28px 24px", marginBottom: 24,
          opacity: videoId ? 1 : 0.5, transition: "opacity 0.3s",
        }}>
          <div style={{ fontSize: 11, color: "#7c5cbf", fontWeight: 600, letterSpacing: "0.12em", marginBottom: 16, textTransform: "uppercase" }}>
            Step 2 · Search by vibe
          </div>

          {/* Vibe chips */}
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 14 }}>
            {["the beat drop", "intense fight scene", "someone says thank you", "crowd going wild", "slow dramatic reveal"].map(v => (
              <button key={v} onClick={() => setQuery(v)}
                style={{
                  background: query === v ? "#2e1f5e" : "#1e1e28",
                  border: `1px solid ${query === v ? "#7c3aed" : "#2a2a38"}`,
                  color: query === v ? "#c4b5fd" : "#888896",
                  borderRadius: 20, padding: "5px 13px", fontSize: 12,
                  cursor: "pointer", transition: "all 0.15s", fontFamily: "inherit",
                }}>
                {v}
              </button>
            ))}
          </div>

          <div style={{ display: "flex", gap: 10 }}>
            <input
              value={query}
              onChange={e => setQuery(e.target.value)}
              onKeyDown={e => e.key === "Enter" && handleSearch()}
              placeholder="Describe a vibe, a moment, or something that was said…"
              disabled={!videoId}
              style={{
                flex: 1, background: "#0e0e14", border: "1px solid #2a2a38",
                borderRadius: 10, padding: "11px 16px", fontSize: 14, color: "#e8e6f0",
              }}
            />
            <button onClick={handleSearch} disabled={searching || !videoId || !query}
              style={{
                background: "#ec4899", color: "#fff", border: "none",
                borderRadius: 10, padding: "11px 22px", fontSize: 14, fontWeight: 600,
                cursor: "pointer", transition: "all 0.15s",
                opacity: (!videoId || !query) ? 0.35 : 1,
              }}>
              {searching ? "…" : "Search"}
            </button>
          </div>
        </section>

        {error && (
          <div style={{
            background: "#1f1016", border: "1px solid #4a1b0c",
            borderRadius: 10, padding: "12px 16px", marginBottom: 20,
            fontSize: 13, color: "#F0997B",
          }}>{error}</div>
        )}

        {/* Results */}
        {results.length > 0 && (
          <div>
            <div style={{ fontSize: 12, color: "#555560", marginBottom: 14, letterSpacing: "0.05em" }}>
              Top {results.length} matches for "{query}"
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
              {results.map((r, i) => (
                <a key={i} href={r.youtube_url} target="_blank" rel="noreferrer"
                  className="result-card"
                  style={{
                    background: "#13131a", border: "1px solid #2a2a38",
                    borderRadius: 12, overflow: "hidden", textDecoration: "none",
                    display: "block", transition: "background 0.15s",
                    animationDelay: `${i * 0.06}s`,
                  }}>
                  {/* Thumbnail */}
                  <div style={{
                    background: "#1e1e2a", height: 100,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    position: "relative", overflow: "hidden",
                  }}>
                    {r.thumbnail_url
                      ? <img src={r.thumbnail_url} alt=""
                          style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                      : <span style={{ fontSize: 28, color: "#333" }}>🎬</span>
                    }
                    {/* Match-source badge */}
                    {r.match_source && <SourceBadge source={r.match_source} />}
                    {/* Score pill */}
                    <div style={{
                      position: "absolute", top: 8, right: 8,
                      background: "rgba(14,14,20,0.85)", borderRadius: 20,
                      padding: "2px 9px", fontSize: 11, color: "#a78bfa", fontWeight: 600,
                    }}>
                      {(r.score * 100).toFixed(1)}
                    </div>
                  </div>
                  <div style={{ padding: "10px 14px 12px" }}>
                    <div style={{
                      fontFamily: "'Space Mono', monospace", fontSize: 18,
                      fontWeight: 700, color: "#f0eeff", letterSpacing: "-0.01em",
                    }}>{formatTime(r.timestamp)}</div>
                    {r.transcript ? (
                      <div style={{
                        fontSize: 11.5, color: "#8a8a99", marginTop: 5, lineHeight: 1.45,
                        display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical",
                        overflow: "hidden",
                      }}>“{r.transcript}”</div>
                    ) : (
                      <div style={{ fontSize: 11, color: "#555560", marginTop: 2 }}>
                        Click to open at this moment →
                      </div>
                    )}
                  </div>
                </a>
              ))}
            </div>
          </div>
        )}

        {/* How it works */}
        <div style={{
          marginTop: 48, padding: "24px 28px",
          background: "#16161d", border: "1px solid #2a2a38", borderRadius: 16,
        }}>
          <div style={{ fontSize: 11, color: "#555560", fontWeight: 600, letterSpacing: "0.12em", marginBottom: 16, textTransform: "uppercase" }}>
            How Skim works
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
            {[
              { n: "01", title: "See + hear", desc: "OpenCV samples frames; Whisper transcribes the audio into timestamped lines" },
              { n: "02", title: "Dual embeddings", desc: "CLIP encodes each frame; MiniLM encodes each spoken line — two semantic spaces" },
              { n: "03", title: "Hybrid search", desc: "Your query hits both spaces; Reciprocal Rank Fusion blends seen + said into one ranking" },
            ].map(s => (
              <div key={s.n}>
                <div style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, color: "#7c3aed", marginBottom: 6 }}>{s.n}</div>
                <div style={{ fontSize: 13, fontWeight: 600, color: "#c4b5fd", marginBottom: 4 }}>{s.title}</div>
                <div style={{ fontSize: 12, color: "#666672", lineHeight: 1.6 }}>{s.desc}</div>
              </div>
            ))}
          </div>
          <div style={{ marginTop: 20, padding: "12px 0 0", borderTop: "1px solid #2a2a38", fontSize: 11, color: "#444450" }}>
            Vectors persist in Pinecone · thumbnails on Cloudinary · cached globally in Redis for instant repeat searches
          </div>
        </div>

      </div>
    </div>
  );
}
