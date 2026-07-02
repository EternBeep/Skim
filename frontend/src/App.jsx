import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Link2, Search, Loader2, RotateCcw, AlertCircle } from "lucide-react";
import { API, VIBE_SUGGESTIONS } from "./constants/api";
import Header from "./components/Header";
import StatusBadge, { StatusMessage, IndexProgress } from "./components/StatusBadge";
import SummaryPanel from "./components/SummaryPanel";
import AudioPanel from "./components/AudioPanel";
import ResultsGrid from "./components/ResultsGrid";
import HowItWorks from "./components/HowItWorks";
import "./App.css";

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
      } catch {
        /* backend may be offline during local dev */
      }
    }, 1500);

    return () => clearInterval(pollRef.current);
  }, [jobId]);

  useEffect(() => {
    if (!videoId) return;
    fetch(`${API}/audio-analysis/${videoId}`)
      .then((r) => (r.ok ? r.json() : null))
      .then(setAudio)
      .catch(() => {});
  }, [videoId]);

  async function handleIndex(force = false) {
    if (!url.trim()) return;
    setError("");
    setResults([]);
    setJobStatus(null);
    setVideoId(null);
    setAudio(null);
    setIndexing(true);

    try {
      const res = await fetch(`${API}/index`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ youtube_url: url, interval_sec: 2.0, force }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Indexing request failed");
      setJobId(data.job_id);
    } catch (err) {
      setError(err.message || "Cannot reach backend. Start the FastAPI server first.");
      setIndexing(false);
    }
  }

  async function handleSearch() {
    if (!videoId || !query.trim()) return;
    setSearching(true);
    setError("");

    try {
      const res = await fetch(`${API}/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_id: videoId, query, top_k: 6 }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Search failed");
      setResults(data.results || []);
    } catch (err) {
      setError(err.message || "Search failed. Is the server running?");
    }
    setSearching(false);
  }

  return (
    <div className="app">
      <div className="app__noise" aria-hidden="true" />
      <div className="app__glow app__glow--1" aria-hidden="true" />
      <div className="app__glow app__glow--2" aria-hidden="true" />

      <Header />

      <main className="app__content">
        {/* Step 1 — Index */}
        <motion.section
          className="card"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="card__label">
            <span className="card__step">1</span>
            Index video
          </div>
          <div className="input-row">
            <input
              className="input"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleIndex()}
              placeholder="https://www.youtube.com/watch?v=..."
              aria-label="YouTube URL"
            />
            <button
              className="btn btn--primary"
              onClick={() => handleIndex()}
              disabled={indexing || !url.trim()}
            >
              {indexing ? (
                <>
                  <Loader2 size={16} className="spin" aria-hidden="true" />
                  Indexing…
                </>
              ) : (
                <>
                  <Link2 size={16} aria-hidden="true" />
                  Index
                </>
              )}
            </button>
          </div>

          {jobStatus && (
            <>
              <div className="status-row">
                <StatusBadge status={jobStatus.status} />
                {jobStatus.status === "embedding" && jobStatus.total_frames && (
                  <span className="status-meta">{jobStatus.total_frames} frames to embed</span>
                )}
                {jobStatus.status === "done" && (
                  <>
                    <span className="status-meta status-meta--success">
                      {jobStatus.frame_count} frames
                      {jobStatus.has_transcript
                        ? ` · ${jobStatus.transcript_chunks} transcript chunks`
                        : " · no speech detected"}
                      {jobStatus.cached ? " · cached" : ""}
                    </span>
                    <button
                      className="btn btn--ghost"
                      onClick={() => handleIndex(true)}
                      disabled={indexing || !url.trim()}
                      title="Re-process this video from scratch"
                    >
                      <RotateCcw size={12} aria-hidden="true" />
                      Re-index
                    </button>
                  </>
                )}
                <StatusMessage status={jobStatus.status} />
              </div>
              <IndexProgress status={jobStatus.status} />
            </>
          )}
        </motion.section>

        <AnimatePresence>
          {jobStatus?.status === "done" && (
            <SummaryPanel
              data={jobStatus.summary}
              hasTranscript={jobStatus.has_transcript}
            />
          )}
        </AnimatePresence>

        <AnimatePresence>{videoId && <AudioPanel data={audio} />}</AnimatePresence>

        {/* Step 2 — Search */}
        <motion.section
          className={`card${!videoId ? " card--disabled" : ""}`}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.22, ease: [0.16, 1, 0.3, 1] }}
        >
          <div className="card__label">
            <span className="card__step">2</span>
            Search by vibe
          </div>

          <div className="chips">
            {VIBE_SUGGESTIONS.map((v) => (
              <button
                key={v}
                type="button"
                className={`btn btn--chip${query === v ? " is-active" : ""}`}
                onClick={() => setQuery(v)}
                disabled={!videoId}
              >
                {v}
              </button>
            ))}
          </div>

          <div className="input-row">
            <input
              className="input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="Describe a vibe, a moment, or something that was said…"
              disabled={!videoId}
              aria-label="Search query"
            />
            <button
              className="btn btn--primary"
              onClick={handleSearch}
              disabled={searching || !videoId || !query.trim()}
            >
              {searching ? (
                <>
                  <Loader2 size={16} className="spin" aria-hidden="true" />
                  Searching…
                </>
              ) : (
                <>
                  <Search size={16} aria-hidden="true" />
                  Search
                </>
              )}
            </button>
          </div>
        </motion.section>

        <AnimatePresence>
          {error && (
            <motion.div
              className="error-banner"
              role="alert"
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25 }}
            >
              <AlertCircle size={16} aria-hidden="true" />
              {error}
            </motion.div>
          )}
        </AnimatePresence>

        <ResultsGrid results={results} query={query} />
        <HowItWorks />
      </main>

      <footer className="app-footer">
        Built with CLIP · Whisper · librosa · Pinecone · Cloudinary · Redis
      </footer>

    </div>
  );
}
