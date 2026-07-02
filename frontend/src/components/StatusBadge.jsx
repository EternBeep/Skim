import { STATUS_LABELS } from "../constants/api";

const ACTIVE_STATUSES = new Set([
  "downloading",
  "embedding",
  "transcribing",
  "uploading",
  "analyzing",
  "storing",
  "queued",
]);

const STATUS_MESSAGES = {
  downloading: "Fetching video from YouTube…",
  transcribing: "Whisper is listening…",
  analyzing: "Finding the beat…",
};

export default function StatusBadge({ status }) {
  const label = STATUS_LABELS[status] || STATUS_LABELS.queued;
  const isActive = ACTIVE_STATUSES.has(status) && status !== "done";
  const isDone = status === "done";

  return (
    <span
      className={`status-badge${isActive ? " is-active" : ""}${isDone ? " is-done" : ""}`}
    >
      <span className="status-badge__dot" aria-hidden="true" />
      {label}
      {status === "embedding" ? "…" : ""}
    </span>
  );
}

export function StatusMessage({ status }) {
  const message = STATUS_MESSAGES[status];
  if (!message) return null;
  return <span className="status-meta">{message}</span>;
}

export function IndexProgress({ status }) {
  const progressMap = {
    queued: 5,
    downloading: 20,
    embedding: 40,
    transcribing: 55,
    uploading: 70,
    analyzing: 85,
    storing: 95,
    done: 100,
  };
  const value = progressMap[status] ?? 0;
  if (status === "done" || status === "error") return null;

  return (
    <div className="progress-bar" role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={100}>
      <div className="progress-bar__fill" style={{ width: `${value}%` }} />
    </div>
  );
}
