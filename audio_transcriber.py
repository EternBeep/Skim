"""
VibeSeek - Week 2
Audio Transcriber: Runs OpenAI Whisper on a downloaded video to produce
timestamped transcript chunks, so search can also match *what was said*.
"""

import whisper                       # openai-whisper: speech-to-text
from dataclasses import dataclass


@dataclass
class TranscriptChunk:
    start: float       # seconds — when this spoken segment begins
    end: float         # seconds — when it ends
    text: str          # the words spoken in this window


class WhisperTranscriber:
    """
    Wraps Whisper for transcription. The model is lazy-loaded on first use so
    importing this module stays cheap.

    Usage:
        transcriber = WhisperTranscriber()
        chunks = transcriber.transcribe("vibeseek_data/downloads/abc.mp4")
    """

    def __init__(self, model_name: str = "base"):
        self.model_name = model_name      # "base" trades some speed for noticeably better accuracy than "tiny"
        self.model = None                 # loaded on first transcribe() call

    def _ensure_model(self):
        if self.model is None:
            print(f"[Transcriber] Loading Whisper '{self.model_name}'...")
            self.model = whisper.load_model(self.model_name)
            print("[Transcriber] Ready.")

    def transcribe(self, media_path: str) -> list[TranscriptChunk]:
        """
        Transcribes a media file. Whisper extracts the audio track itself
        (via ffmpeg), so the raw .mp4 can be passed directly.

        Returns a list of TranscriptChunk, or [] for music / no-speech clips.
        """
        self._ensure_model()
        print(f"[Transcriber] Transcribing {media_path}...")

        # fp16=False — we run on CPU, where half precision is unsupported.
        result = self.model.transcribe(media_path, fp16=False)

        chunks: list[TranscriptChunk] = []
        for seg in result.get("segments", []):
            text = seg.get("text", "").strip()
            if not text:                          # skip silent / empty segments
                continue
            chunks.append(TranscriptChunk(
                start=float(seg["start"]),
                end=float(seg["end"]),
                text=text,
            ))

        print(f"[Transcriber] Got {len(chunks)} transcript chunks.")
        return chunks


def nearest_transcript(timestamp: float, chunks: list[TranscriptChunk]) -> str:
    """
    Finds the transcript text most relevant to a given frame timestamp.

    Prefers a chunk whose [start, end] window contains the timestamp; otherwise
    falls back to the chunk whose midpoint is closest. Returns "" when there are
    no chunks (e.g. an instrumental video) so the value is Chroma-metadata safe.
    """
    if not chunks:
        return ""

    for c in chunks:                              # exact containment wins
        if c.start <= timestamp <= c.end:
            return c.text

    # No window contains it — pick the closest chunk by midpoint distance.
    closest = min(chunks, key=lambda c: abs(((c.start + c.end) / 2) - timestamp))
    return closest.text
