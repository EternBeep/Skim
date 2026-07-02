export const API = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const VIBE_SUGGESTIONS = [
  "the beat drop",
  "intense fight scene",
  "someone says thank you",
  "crowd going wild",
  "slow dramatic reveal",
];

export const SOURCE_META = {
  visual: { label: "Visual", Icon: "Eye" },
  spoken: { label: "Spoken", Icon: "Mic" },
  both: { label: "Seen + Said", Icon: "Sparkles" },
};

export const STATUS_LABELS = {
  queued: "Queued",
  downloading: "Downloading",
  embedding: "Embedding frames",
  transcribing: "Transcribing audio",
  uploading: "Uploading thumbnails",
  analyzing: "Analyzing beats",
  storing: "Saving vectors",
  done: "Ready",
  error: "Error",
};
