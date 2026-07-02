"""
VibeSeek - Week 2
Audio Analyzer: Uses librosa to detect the beat grid and the highest-energy
moments of a video's audio track — useful for music videos where the "vibe"
is driven by drops and beat changes.

Results are cached to JSON per video_id so we only run the (somewhat expensive)
analysis once.
"""

import os
import json
import numpy as np
import librosa
from pathlib import Path

CACHE_DIR = "vibeseek_data/audio"      # where per-video analysis JSON lives


def _pick_energy_peaks(times, energy, top_n: int = 3, min_sep_sec: float = 5.0):
    """
    Picks the top_n highest-energy moments, greedily enforcing a minimum time
    separation so we don't return three adjacent frames of the same drop.

    Returns a list of {"timestamp": float, "energy": float}, highest first.
    """
    order = np.argsort(energy)[::-1]              # indices, strongest energy first
    chosen: list[int] = []

    for idx in order:
        t = times[idx]
        # keep this peak only if it's far enough from every peak already chosen
        if all(abs(t - times[c]) >= min_sep_sec for c in chosen):
            chosen.append(int(idx))
        if len(chosen) >= top_n:
            break

    return [
        {"timestamp": round(float(times[i]), 2), "energy": round(float(energy[i]), 4)}
        for i in chosen
    ]


# Krumhansl-Kessler key profiles — the classic templates for guessing whether a
# piece sits in a major (bright/positive) or minor (darker/emotional) key. We
# correlate the song's average chroma against both, across all 12 roots, and keep
# whichever fits best. It's a heuristic, but a widely-used and decent one.
_KK_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
_KK_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


def _estimate_mode(y, sr) -> str | None:
    """
    Guess 'major' vs 'minor' from the audio's average chroma — a proxy for the
    track's emotional colour (bright vs moody). Returns None if it can't tell.
    """
    try:
        chroma_mean = librosa.feature.chroma_stft(y=y, sr=sr).mean(axis=1)
        n = np.linalg.norm(chroma_mean)
        if n == 0:
            return None
        cm = chroma_mean / n
        maj = _KK_MAJOR / np.linalg.norm(_KK_MAJOR)
        minr = _KK_MINOR / np.linalg.norm(_KK_MINOR)
        best_major = max(float(np.dot(np.roll(maj, i), cm)) for i in range(12))   # best major key fit
        best_minor = max(float(np.dot(np.roll(minr, i), cm)) for i in range(12))  # best minor key fit
        return "major" if best_major >= best_minor else "minor"
    except Exception:
        return None   # mode is a nice-to-have; never fail analysis over it


def analyze(media_path: str) -> dict:
    """
    Runs beat + energy analysis on a media file's audio.

    Returns:
        {
          "tempo": float,                       # estimated BPM
          "duration": float,                    # seconds
          "mode": "major" | "minor" | None,     # rough emotional colour of the key
          "beat_times": [float, ...],           # beat timestamps
          "energy_peaks": [{timestamp, energy}],# top-3 highest-energy moments
          "top_moment": {timestamp, energy},    # the single peak (or None)
        }
    """
    print(f"[AudioAnalyzer] Analyzing {media_path}...")

    # librosa reads the audio track via ffmpeg/audioread; mono keeps it simple.
    y, sr = librosa.load(media_path, mono=True)
    duration = float(librosa.get_duration(y=y, sr=sr))

    # --- Beat tracking ------------------------------------------------------ #
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    # tempo can come back as a 0-d / 1-element array depending on librosa version
    tempo = float(np.atleast_1d(tempo)[0])

    # --- Energy (RMS) ------------------------------------------------------- #
    rms = librosa.feature.rms(y=y)[0]            # per-frame root-mean-square energy
    rms_times = librosa.times_like(rms, sr=sr)
    energy_peaks = _pick_energy_peaks(rms_times, rms, top_n=3)

    # --- Emotional colour (major/minor) ------------------------------------- #
    mode = _estimate_mode(y, sr)                 # 'major' (bright) / 'minor' (moody) / None

    result = {
        "tempo": round(tempo, 1),
        "duration": round(duration, 2),
        "mode": mode,
        "beat_times": [round(float(t), 2) for t in beat_times],
        "energy_peaks": energy_peaks,
        "top_moment": energy_peaks[0] if energy_peaks else None,
    }
    print(f"[AudioAnalyzer] tempo={result['tempo']} BPM, "
          f"{len(result['beat_times'])} beats, {len(energy_peaks)} energy peaks.")
    return result


def _cache_path(video_id: str) -> str:
    return os.path.join(CACHE_DIR, f"{video_id}.json")


def get_or_analyze(video_id: str, media_path: str, force: bool = False) -> dict:
    """
    Returns cached analysis for video_id if present, otherwise analyzes
    media_path and caches the result to JSON. Pass force=True (a re-index) to
    ignore the cache and recompute from scratch.
    """
    Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
    cache = _cache_path(video_id)

    if not force and os.path.exists(cache):
        with open(cache, "r", encoding="utf-8") as f:
            return json.load(f)

    result = analyze(media_path)
    with open(cache, "w", encoding="utf-8") as f:
        json.dump(result, f)
    return result
