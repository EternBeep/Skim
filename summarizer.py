"""
Skim - Transcript Summarizer
Builds a short "what's this video about" summary plus a few topic keywords
straight from the Whisper transcript — so a freshly indexed video can be skimmed
at a glance before you ever search it.

Why no LLM call: the rest of the stack is deliberately free-tier / no-API-key
(Pinecone + Cloudinary + Redis). So instead of paying an external model, we do
centroid-based EXTRACTIVE summarization, reusing the MiniLM chunk embeddings that
indexing already computed:

  1. The centroid (mean) of every chunk embedding is the video's semantic "centre
     of mass" — the gist of everything said.
  2. The chunks whose embeddings sit closest to that centroid are the most
     representative lines, so we pick those as the summary.
  3. A small redundancy penalty (MMR-lite) stops us picking three sentences that
     all say the same thing.

This means the summary costs essentially nothing extra at index time — the
embeddings are already in hand.
"""

import re                       # tokenising transcript text for keyword counts
from collections import Counter  # tallying word frequencies for keywords
import numpy as np              # vector maths over the chunk embeddings

# Very common English words carry little topical signal, so we drop them before
# picking a video's keywords — the chips should show what it's ABOUT, not filler.
_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "of", "to", "in", "on", "for",
    "with", "as", "at", "by", "from", "this", "that", "these", "those", "it",
    "its", "is", "are", "was", "were", "be", "been", "being", "am", "do", "does",
    "did", "have", "has", "had", "will", "would", "can", "could", "should",
    "shall", "may", "might", "must", "i", "you", "he", "she", "we", "they", "me",
    "him", "her", "us", "them", "my", "your", "his", "our", "their", "what",
    "which", "who", "whom", "when", "where", "why", "how", "all", "any", "both",
    "each", "few", "more", "most", "some", "such", "no", "nor", "not", "only",
    "own", "same", "so", "than", "too", "very", "just", "now", "then", "there",
    "here", "up", "down", "out", "off", "over", "under", "again", "about",
    "into", "yeah", "okay", "ok", "like", "got", "get", "gonna", "wanna", "really",
    "right", "well", "know", "going", "one", "two", "thing", "things", "lot",
    "kind", "sort", "way", "every", "much", "many", "also", "even", "back",
    "good", "great", "want", "make", "made", "see", "say", "said", "go", "come",
}

# Whisper sometimes emits non-speech markers like "[Music]" or "(applause)".
_NONSPEECH = re.compile(r"^[\[\(].*[\]\)]$")
_WORD = re.compile(r"[a-z][a-z'\-]+")   # keyword tokens: letters (apostrophes/hyphens ok)

# Patterns used to scrub a YouTube description down to its actual prose, dropping
# the boilerplate that clutters music/anime/movie descriptions (links, credits,
# "subscribe", chapter timestamps, social handles, label notices, etc.).
_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_DROP_LINE_RE = re.compile(
    r"(provided to youtube|auto-generated|released on|©|℗|all rights reserved|"
    r"subscribe|follow (us|me)|stream|spotify|apple music|itunes|soundcloud|"
    r"download|listen|out now|available now|directed by|prod(\.|uced)? by|"
    r"instagram|twitter|tiktok|facebook|merch|patreon|discord|bandcamp|"
    r"music video by|vevo)",
    re.IGNORECASE,
)
_TIMESTAMP_LINE_RE = re.compile(r"^\s*\(?\d{1,2}:\d{2}")   # chapter lines like "0:00 Intro"


def _clean(text: str) -> str:
    """Collapse whitespace and strip Whisper's leading/trailing junk."""
    return re.sub(r"\s+", " ", text or "").strip()


def _fmt_duration(seconds) -> str:
    """Human-readable length, e.g. 311 -> '5:11', 72 -> '1:12'."""
    try:
        s = int(seconds)
    except (TypeError, ValueError):
        return ""
    if s <= 0:
        return ""
    m, sec = divmod(s, 60)
    return f"{m}:{sec:02d}"


def _clean_description(text: str) -> str:
    """
    Reduce a raw YouTube description to its first couple of real sentences,
    throwing away links, credits, calls-to-action and chapter timestamps so the
    summary reads like prose, not a press release.
    """
    if not text:
        return ""
    text = _URL_RE.sub("", text)
    keep = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#") or line.startswith("@"):
            continue                                  # hashtag / handle line
        if _TIMESTAMP_LINE_RE.match(line):
            continue                                  # chapter timestamp line
        if _DROP_LINE_RE.search(line):
            continue                                  # boilerplate / promo line
        if len(line.split()) < 4:
            continue                                  # too short to be a real sentence
        if not re.search(r"\b[a-z]{2,}\b", line):
            continue                                  # no lowercase word -> a title/credit fragment, not prose
        keep.append(line)
    prose = _clean(" ".join(keep))
    if not prose:
        return ""
    # Take the first ~2 sentences, capped so the card stays compact.
    sentences = re.split(r"(?<=[.!?])\s+", prose)
    summary = " ".join(sentences[:2]).strip()
    if len(summary) > 300:
        summary = summary[:300].rstrip() + "…"
    if summary[-1] not in ".!?…":                     # guarantee a clean sentence end
        summary += "."
    return summary


def _keywords(texts: list[str], max_keywords: int) -> list[str]:
    """Top content words across the whole transcript, for the topic chips."""
    counts: Counter[str] = Counter()
    for t in texts:
        for w in _WORD.findall(t.lower()):
            if len(w) >= 3 and w not in _STOPWORDS:   # skip short words + filler
                counts[w] += 1
    return [w for w, _ in counts.most_common(max_keywords)]


def summarize(chunks, embeddings, max_sentences: int = 3,
              max_keywords: int = 6) -> dict | None:
    """
    Build an extractive summary + keywords from transcript chunks.

    Args:
        chunks:     list of TranscriptChunk (each has .text and .start).
        embeddings: (N, D) L2-normalised MiniLM vectors aligned 1:1 with `chunks`
                    (exactly what indexing already produced for these chunks).
        max_sentences: how many representative lines to stitch into the summary.
        max_keywords:  how many topic words to surface.

    Returns:
        {"summary": str, "keywords": [str, ...], "sentence_count": int}
        or None when there's no usable speech to summarise (e.g. a music video).
    """
    if chunks is None or len(chunks) == 0:
        return None
    if embeddings is None or len(embeddings) != len(chunks):
        return None   # misaligned/empty embeddings — can't score safely

    emb = np.asarray(embeddings, dtype=np.float32)

    # Candidate sentences: real speech of a few words or more. Very short or
    # non-speech fragments ("Yeah.", "[Music]") make a poor summary, so we keep
    # their indices out of selection while preserving alignment with `emb`.
    candidates = []   # (original_index, cleaned_text)
    for i, c in enumerate(chunks):
        text = _clean(getattr(c, "text", ""))
        if len(text.split()) >= 4 and not _NONSPEECH.match(text):
            candidates.append((i, text))

    keywords = _keywords([t for _, t in candidates] or
                         [_clean(getattr(c, "text", "")) for c in chunks],
                         max_keywords)

    if not candidates:
        return None   # nothing worth summarising (e.g. instrumental / chants)

    idxs = np.array([i for i, _ in candidates])
    cand_emb = emb[idxs]                          # (M, D) embeddings of candidates

    # Centroid = the gist; renormalise so dot product is cosine similarity.
    centroid = cand_emb.mean(axis=0)
    norm = np.linalg.norm(centroid)
    if norm > 0:
        centroid = centroid / norm
    central = cand_emb @ centroid                 # similarity of each candidate to the gist

    # Greedy MMR-lite: keep picking the most central line that isn't a near-
    # duplicate of one we've already chosen, so the summary stays on-topic but
    # non-repetitive. The 0.85 threshold only drops genuine paraphrases — lines
    # from one video are naturally somewhat similar, so a lower bar would wrongly
    # collapse distinct points into a single sentence.
    target = min(max_sentences, len(candidates))
    chosen: list[int] = []                        # positions into `candidates`
    order = list(np.argsort(-central))            # most central first
    for pos in order:
        if len(chosen) >= target:
            break
        if any(float(cand_emb[pos] @ cand_emb[c]) > 0.85 for c in chosen):
            continue                              # near-duplicate of a picked line
        chosen.append(pos)

    # If redundancy filtering left us short of the target, top up with the next
    # most-central lines so we still use the content we have.
    if len(chosen) < target:
        for pos in order:
            if len(chosen) >= target:
                break
            if pos not in chosen:
                chosen.append(pos)

    # Read the chosen lines back in chronological order so the summary flows.
    chosen.sort(key=lambda pos: getattr(chunks[candidates[pos][0]], "start", 0.0))
    summary = " ".join(candidates[pos][1] for pos in chosen)

    return {
        "summary": summary,
        "keywords": keywords,
        "sentence_count": len(chosen),
    }


def _meta_keywords(meta: dict, max_keywords: int) -> list[str]:
    """Topic chips for a no-speech video: prefer the uploader's own tags."""
    out, seen = [], set()
    for t in (meta.get("tags") or []):
        tl = _clean(str(t)).lower()
        if tl and tl not in seen and 2 <= len(tl) <= 30:   # skip junk/very long tags
            seen.add(tl)
            out.append(tl)
        if len(out) >= max_keywords:
            return out
    if out:
        return out
    # No tags — fall back to content words from the title + category.
    text = meta.get("title", "") + " " + " ".join(meta.get("categories") or [])
    return _keywords([text], max_keywords)


# Mood read from tempo + key — "what the music conveys" without needing lyrics.
# (tempo_adjective, is_fast, is_slow) and the major/minor emotional gloss are
# combined into one human sentence describing the track's feel.
def _music_mood(audio: dict | None) -> str:
    if not audio or not audio.get("tempo"):
        return ""
    t = float(audio["tempo"])
    if t < 70:        tempo_adj, band = "calm", "slow"
    elif t < 95:      tempo_adj, band = "mellow", "slow"
    elif t < 115:     tempo_adj, band = "steady", "mid"
    elif t < 135:     tempo_adj, band = "energetic", "fast"
    else:             tempo_adj, band = "driving", "fast"

    mode = audio.get("mode")
    mode_adj = {"major": "bright", "minor": "moody"}.get(mode, "")

    # Overall mood from the (mode, tempo-band) pairing — this is the "conveys" bit.
    overall = {
        ("major", "fast"): "an upbeat, celebratory mood",
        ("major", "mid"):  "a warm, positive mood",
        ("major", "slow"): "a gentle, hopeful mood",
        ("minor", "fast"): "an intense, dramatic mood",
        ("minor", "mid"):  "a reflective, emotional mood",
        ("minor", "slow"): "a wistful, melancholic mood",
    }.get((mode, band), {"fast": "an energetic mood", "mid": "a steady mood",
                         "slow": "a calm mood"}[band])

    feel = f"{tempo_adj} and {mode_adj}" if mode_adj else tempo_adj
    return f"It feels {feel}, conveying {overall}."


def summarize_from_metadata(meta: dict | None, audio: dict | None = None,
                            max_keywords: int = 6) -> dict | None:
    """
    Describe ANY video from its YouTube metadata + audio analysis — the fallback
    for music, anime, movie clips and anything else Whisper found no speech in.

    Leads with the title (and channel), adds a cleaned line of the description if
    there is one, and finishes with length/tempo facts. Always returns something
    as long as we at least know the title.
    """
    if not meta:
        return None
    title = _clean(meta.get("title", ""))
    if not title:
        return None   # without a title there's nothing trustworthy to say

    uploader = _clean(meta.get("uploader", ""))
    desc = _clean_description(meta.get("description", ""))
    tempo = audio.get("tempo") if audio else None
    duration = (audio.get("duration") if audio else None) or meta.get("duration")
    is_music = any("music" in c.lower() for c in (meta.get("categories") or []))
    mood = _music_mood(audio)

    parts = [f"“{title}”"]                       # “Title”
    if uploader and uploader.lower() not in title.lower():
        parts[0] += f" by {uploader}"
    parts[0] += "."

    # Body: for a music video describe what the track CONVEYS (mood/feel) rather
    # than credits; otherwise use the real description prose if there is one.
    if is_music and mood:
        parts.append(mood)
        if desc:                                 # keep a real description too, if present
            parts.append(desc)
    elif desc:
        parts.append(desc)
    elif mood:                                   # non-music with no prose: still give the feel
        parts.append(mood)

    # Closing facts — runtime, plus BPM when the mood sentence didn't already imply it.
    dur_txt = _fmt_duration(duration)
    if dur_txt and tempo and not mood:
        parts.append(f"It runs {dur_txt} at around {round(float(tempo))} BPM.")
    elif dur_txt and tempo:
        parts.append(f"Runs {dur_txt} at ~{round(float(tempo))} BPM.")
    elif dur_txt:
        parts.append(f"It runs about {dur_txt}.")
    elif tempo:
        parts.append(f"It sits at around {round(float(tempo))} BPM.")

    return {
        "summary": " ".join(parts),
        "keywords": _meta_keywords(meta, max_keywords),
        "sentence_count": len(parts),
    }


def groq_summarize(text: str, api_key: str, model: str = "llama-3.3-70b-versatile",
                   max_chars: int = 12000) -> str | None:
    """
    Ask Groq's free API to WRITE a 2-3 sentence summary of a transcript — a real,
    human-readable gist rather than extracted quotes. Groq exposes an OpenAI-style
    chat endpoint. Best-effort: returns None on any failure (no key, network error,
    rate limit) so the caller can fall back to the offline extractive summary.
    """
    import requests   # only needed when Groq is configured; keeps base import light

    prompt = (
        "Summarize what this video is about based on its transcript. Write 2-3 "
        "clear sentences describing the content and what it conveys — the main "
        "topic, the key points, and the overall message or mood. Be specific and "
        "neutral. Do not mention that this is a transcript, and do not add a "
        "preamble like 'Here is the summary'.\n\nTranscript:\n"
        + text[:max_chars]
    )
    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 256,
            },
            timeout=30,
        )
        if resp.status_code != 200:                      # bad key, quota, bad model, etc.
            print(f"[Summarizer] Groq HTTP {resp.status_code}: {resp.text[:200]}")
            return None
        out = _clean(resp.json()["choices"][0]["message"]["content"])
        return out or None
    except Exception as e:                                # network/JSON/etc — never fatal
        print(f"[Summarizer] Groq summary failed (non-fatal): {e}")
        return None


def build_summary(chunks, embeddings, meta: dict | None = None,
                  audio: dict | None = None, max_sentences: int = 3,
                  max_keywords: int = 6, groq_api_key: str = "",
                  groq_model: str = "llama-3.3-70b-versatile") -> dict | None:
    """
    One entry point that yields a summary for EVERY video.

    For videos with speech, prefers an AI-written summary via the free Groq tier
    (when a key is configured), and falls back to the offline extractive summary if
    Groq is unavailable. For no-speech videos (music/anime/movies), builds a
    description from the video's metadata + audio analysis. The result is tagged
    with `source` so the UI can say where the gist came from.
    """
    if chunks:
        full_text = " ".join(_clean(getattr(c, "text", "")) for c in chunks).strip()

        # 1. Best: a real, AI-written summary (free Groq tier), if a key is set.
        if not groq_api_key:
            print("[Summarizer] No GROQ_API_KEY loaded -> using offline summary. "
                  "(If you set a key, RESTART the backend so .env is reloaded.)")
        if groq_api_key and full_text:
            print(f"[Summarizer] Calling Groq ({groq_model}) for an AI summary...")
            written = groq_summarize(full_text, groq_api_key, groq_model)
            if written:
                print("[Summarizer] Groq summary OK (source=ai).")
                return {
                    "summary": written,
                    "keywords": _keywords([full_text], max_keywords),
                    "sentence_count": len([s for s in re.split(r"[.!?]", written) if s.strip()]),
                    "source": "ai",
                }

        # 2. Free offline fallback: extractive summary from the chunk embeddings.
        if embeddings is not None and len(embeddings) == len(chunks):
            spoken = summarize(chunks, embeddings, max_sentences, max_keywords)
            if spoken:
                spoken["source"] = "spoken"
                return spoken

    meta_summary = summarize_from_metadata(meta, audio, max_keywords)
    if meta_summary:
        meta_summary["source"] = "metadata"
        return meta_summary

    return None
