"""
VibeSeek - Week 3
FastAPI Backend: Index a YouTube video (frames + transcript + audio analysis)
and search it by vibe across BOTH what was seen (CLIP) and what was said (Whisper
+ MiniLM), fused with Reciprocal Rank Fusion.

Week 3 changes:
  - Vectors persist in Pinecone (cloud) instead of ChromaDB (local).
  - Frame thumbnails are hosted on Cloudinary (cloud CDN) instead of local /frames.
  - A global Redis registry caches indexed videos, so a URL indexed by anyone is
    instantly searchable for everyone — repeated URLs skip download + processing.
  - Indexing runs through a single Redis-backed worker so concurrent users queue
    up instead of crashing the box.
"""
#Backend Part of VibeSeek
import os#used for local file cleanup after upload
import sys#used to force UTF-8 stdout below
import uuid#use to generate unique ids of jobs or videos
import shutil#used to remove the local frames directory after Cloudinary upload

# Windows consoles default to cp1252, which can't encode the arrows/em-dashes in
# our log lines and would crash a worker job mid-print. Force UTF-8 everywhere
# (no-op on Linux/HF Spaces, which is already UTF-8).
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass
from glob import glob#used to locate the downloaded video file by id
from pathlib import Path #Pathlib is a module used to handle file paths in a platform-independent way
from typing import Optional#use to type hints like optional values eg if _embedder is not initialised then it is None

from fastapi import FastAPI, HTTPException #FastAPI framework + error handling (BackgroundTasks replaced by the Redis queue)
from fastapi.middleware.cors import CORSMiddleware#used to handle CORS (Cross-Origin Resource Sharing) ,Allows frontend and backend to communicate.
from pydantic import BaseModel#use to validate the data sent to the API

from frame_extractor import extract_frames_from_url, get_video_id, Frame#frame extractor + cache-check id resolver
from clip_embedder import CLIPEmbedder#imports the clip_embedder module (visual embeddings)
from text_embedder import TextEmbedder#MiniLM embeddings for spoken-word search
from audio_transcriber import WhisperTranscriber, nearest_transcript#Whisper transcription
import audio_analyzer#librosa beat/energy analysis
import config#central env-backed settings (Groq key etc.)
import summarizer#transcript summary + keywords (free Groq tier, offline fallback)
import vector_store#Pinecone-backed persistence
import storage#Cloudinary frame hosting
import redis_client#Upstash Redis: global registry + audio cache
import job_queue#Upstash Redis: indexing job queue + worker

# ------------------------------------------------------------------ #
#  App setup                                                           #
# ------------------------------------------------------------------ #

app = FastAPI(title="VibeSeek API", version="0.3.0")#this is used to create the FastAPI app,creates API server

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)#Allow any frontend to call this API   #tighten in production means to restrict the frontend to a specific domain

DATA_DIR = "vibeseek_data"#creats the main directory to store the data (now just a temp workspace)
FRAMES_DIR = f"{DATA_DIR}/frames"#temp frames before they're uploaded to Cloudinary
DOWNLOADS_DIR = f"{DATA_DIR}/downloads"#where yt-dlp saves the source video
Path(FRAMES_DIR).mkdir(parents=True, exist_ok=True)
Path(DOWNLOADS_DIR).mkdir(parents=True, exist_ok=True)

# Note: frames are served from Cloudinary in Week 3, so the local /frames static
# mount from Week 2 has been removed.

# Lazy-loaded models (load on first use, then reused)
_embedder: Optional[CLIPEmbedder] = None
_text_embedder: Optional[TextEmbedder] = None
_transcriber: Optional[WhisperTranscriber] = None

def get_embedder() -> CLIPEmbedder:
    global _embedder
    if _embedder is None:
        _embedder = CLIPEmbedder()#this is used to create the CLIP embedder object
    return _embedder

def get_text_embedder() -> TextEmbedder:
    global _text_embedder
    if _text_embedder is None:
        _text_embedder = TextEmbedder()
    return _text_embedder

def get_transcriber() -> WhisperTranscriber:
    global _transcriber
    if _transcriber is None:
        _transcriber = WhisperTranscriber()
    return _transcriber


# ------------------------------------------------------------------ #
#  Pydantic models                                                     #
# ------------------------------------------------------------------ #

class IndexRequest(BaseModel):
    youtube_url: str
    interval_sec: float = 2.0      # sample every N seconds
    force: bool = False            # True = bypass the cache and re-process from scratch

class SearchRequest(BaseModel):
    video_id: str
    query: str
    top_k: int = 5


# ------------------------------------------------------------------ #
#  Helpers                                                             #
# ------------------------------------------------------------------ #

def _nearest_frame_image(timestamp: float, frames: list[Frame]) -> str:
    """Closest extracted frame's thumbnail to a transcript chunk's midpoint."""
    if not frames:
        return ""
    closest = min(frames, key=lambda f: abs(f.timestamp - timestamp))
    return closest.image_path


def _thumbnail_url(image_path: str) -> Optional[str]:
    """
    Return a thumbnail URL for the UI. In Week 3 image_path is already a Cloudinary
    https URL, so it's passed straight through. (Empty -> None.)
    """
    if not image_path:                            # no image stored for this hit?
        return None                               # nothing to show
    if storage.is_remote_url(image_path):         # is it an http(s) URL (i.e. Cloudinary)?
        return image_path                         # already a Cloudinary CDN URL
    return None                                   # legacy local paths no longer served


def _youtube_link(video_id: str, timestamp: float) -> str:
    return f"https://www.youtube.com/watch?v={video_id}&t={int(timestamp)}s"


def _rrf_fuse(visual_hits: list[dict], spoken_hits: list[dict],
              top_k: int, k0: int = 60, bucket: float = 2.0) -> list[dict]:
    """
    Reciprocal Rank Fusion of the visual (CLIP) and spoken (MiniLM) result lists.

    RRF is rank-based, so the two very different cosine-score scales never need to
    be compared directly. Hits that fall in the same ~`bucket`-second window are
    merged into one "moment" and tagged with which source(s) matched.
    """
    moments: dict[int, dict] = {}

    def slot(ts: float) -> int:
        return round(ts / bucket)

    for rank, h in enumerate(visual_hits):
        m = moments.setdefault(slot(h["timestamp"]), {"score": 0.0, "sources": set(),
                                                       "visual": None, "spoken": None})
        m["score"] += 1.0 / (k0 + rank)
        m["sources"].add("visual")
        m["visual"] = h

    for rank, h in enumerate(spoken_hits):
        m = moments.setdefault(slot(h["timestamp"]), {"score": 0.0, "sources": set(),
                                                       "visual": None, "spoken": None})
        m["score"] += 1.0 / (k0 + rank)
        m["sources"].add("spoken")
        m["spoken"] = h

    ranked = sorted(moments.values(), key=lambda m: m["score"], reverse=True)[:top_k]

    results = []
    for m in ranked:
        v, s = m["visual"], m["spoken"]
        # Prefer the visual frame for timestamp/thumbnail; fall back to the chunk.
        timestamp = (v or s)["timestamp"]
        image_path = (v["image_path"] if v and v.get("image_path") else
                      (s["image_path"] if s else ""))
        # Prefer the actual spoken text; otherwise the caption attached to the frame.
        transcript = (s["text"] if s else v.get("transcript", "")) or ""
        match_source = "both" if len(m["sources"]) == 2 else m["sources"].pop()

        results.append({
            "timestamp": round(float(timestamp), 2),
            "score": round(float(m["score"]), 5),
            "transcript": transcript,
            "match_source": match_source,
            "image_path": image_path,
        })
    return results


def _cleanup_local(video_path: str, video_id: str):
    """
    Free local disk on the ephemeral host once everything is in the cloud:
    Cloudinary holds the frames, Pinecone holds the vectors, Redis holds the audio
    analysis. Best-effort — failures here are non-fatal.
    """
    try:
        if video_path and os.path.exists(video_path):     # if the downloaded source file is still on disk...
            os.remove(video_path)                         # ...delete it (it's no longer needed; audio analysis is in Redis)
        frames_dir = f"{FRAMES_DIR}/{video_id}"           # the local folder of extracted JPEGs for this video
        if os.path.isdir(frames_dir):                     # if that folder exists...
            shutil.rmtree(frames_dir, ignore_errors=True) # ...remove it entirely (frames now live on Cloudinary)
    except Exception as e:                                 # cleanup must never crash a finished job
        print(f"[Index] Local cleanup failed (non-fatal): {e}")   # just log and move on


# ------------------------------------------------------------------ #
#  Indexing job (runs on the single Redis worker)                     #
# ------------------------------------------------------------------ #

def _run_index_job(job_id: str, payload: dict):
    """Handler invoked by the job_queue worker — one video at a time."""
    youtube_url = payload["youtube_url"]                       # the URL to index (from the queued payload)
    interval_sec = float(payload.get("interval_sec", 2.0))    # how often to sample a frame (default every 2s)
    force = bool(payload.get("force", False))                 # re-index: ignore cached audio analysis

    # --- 1. Download + extract frames ---------------------------------- #
    job_queue.update_status(job_id, status="downloading")     # tell /status we're downloading
    video_path, frames, meta = extract_frames_from_url(       # yt-dlp download + OpenCV frame sampling (+ metadata)
        youtube_url,                                          # the video to fetch
        interval_sec=interval_sec,                            # sampling interval
        base_dir=DATA_DIR,                                    # where to write the temp video + frames
    )
    video_id = Path(video_path).stem                          # the YouTube id = the downloaded file's name without extension

    # --- 2. CLIP-embed the frames -------------------------------------- #
    job_queue.update_status(job_id, status="embedding", total_frames=len(frames))   # report progress + frame count
    frame_embeddings = get_embedder().embed_frames(frames)    # run CLIP over every frame (batch 16)
    emb_frames = [fe.frame for fe in frame_embeddings]   # frames that embedded OK (some may be skipped if unreadable)

    # --- 3. Transcribe speech ------------------------------------------ #
    job_queue.update_status(job_id, status="transcribing")    # tell /status we're transcribing
    chunks = get_transcriber().transcribe(video_path)         # run Whisper (base) -> timestamped text chunks
    has_transcript = len(chunks) > 0                          # False for music/no-speech videos

    # Attach the nearest spoken line to every frame (caption + keyword aid).
    frame_transcripts = [nearest_transcript(f.timestamp, chunks) for f in emb_frames]   # one caption per embedded frame

    # --- 4. Upload frames to Cloudinary -------------------------------- #
    job_queue.update_status(job_id, status="uploading")       # tell /status we're uploading thumbnails
    image_urls = [storage.upload_frame(f.image_path, video_id, f.frame_index)   # upload each frame -> CDN URL
                  for f in emb_frames]                                          # ...for every embedded frame
    url_by_path = {f.image_path: u for f, u in zip(emb_frames, image_urls)}  # local -> CDN  (lookup for the step below)

    # MiniLM-embed the spoken chunks for semantic transcript search.
    chunk_embeddings = None                                   # stays None if there's no speech
    nearest_images = []                                       # parallel list of nearest-frame URLs per chunk
    if has_transcript:                                        # only if Whisper found speech
        chunk_embeddings = get_text_embedder().embed_chunks([c.text for c in chunks])   # MiniLM-encode each spoken chunk
        # Map each chunk to the Cloudinary URL of its nearest embedded frame.
        nearest_images = [url_by_path.get(_nearest_frame_image((c.start + c.end) / 2, emb_frames), "")   # nearest frame -> its CDN URL
                          for c in chunks]                    # ...for every chunk

    # --- 5. Audio analysis (beats + energy) ---------------------------- #
    job_queue.update_status(job_id, status="analyzing")       # tell /status we're analysing audio
    analysis = None                                           # stays None if librosa fails; feeds the summary's tempo/length facts
    try:
        analysis = audio_analyzer.get_or_analyze(video_id, video_path, force=force)   # librosa beat grid + energy peaks (recompute on re-index)
        redis_client.set_audio(video_id, analysis)   # cache globally (survives cleanup)   # so /audio-analysis works after cleanup
    except Exception as e:                       # analysis is best-effort
        print(f"[Index] Audio analysis failed (non-fatal): {e}")   # log but don't fail the whole job

    # --- 5b. Summary (works for EVERY video) --------------------------- #
    # Spoken transcript when there's speech; otherwise a description built from
    # the YouTube metadata + audio facts — so music/anime/movies get one too.
    summary = summarizer.build_summary(chunks, chunk_embeddings, meta, analysis,
                                       groq_api_key=config.GROQ_API_KEY,
                                       groq_model=config.GROQ_MODEL)

    # --- 6. Persist to Pinecone ---------------------------------------- #
    job_queue.update_status(job_id, status="storing")         # tell /status we're saving vectors
    vector_store.add_frames(video_id, frame_embeddings, frame_transcripts, image_urls)   # store visual vectors
    if has_transcript:                                        # only if there was speech
        vector_store.add_transcripts(video_id, chunks, chunk_embeddings, nearest_images)   # store spoken vectors

    # --- 7. Record in the global registry (the cache for goal #3) ------ #
    redis_client.set_indexed(video_id, youtube_url, len(frame_embeddings), has_transcript, summary)   # mark indexed for everyone (+ cache the summary)

    # --- 8. Free local disk on the ephemeral host ---------------------- #
    _cleanup_local(video_path, video_id)                      # delete the temp video + frames now they're in the cloud

    job_queue.update_status(                                  # final status: done + summary numbers
        job_id,
        status="done",                                        # the frontend stops polling on "done"
        video_id=video_id,                                    # so the UI knows what to search
        frame_count=len(frame_embeddings),                   # how many frames were stored
        has_transcript=has_transcript,                        # whether speech was found
        transcript_chunks=len(chunks),                        # how many spoken chunks were stored
        summary=summary,                                      # the extractive gist + keywords (or None)
    )


# Start the single background worker as soon as the app process boots.
@app.on_event("startup")                          # FastAPI runs this once, right after the server starts
def _startup():
    job_queue.start_worker(_run_index_job)        # launch the one worker thread, telling it to use _run_index_job


# ------------------------------------------------------------------ #
#  Endpoints                                                           #
# ------------------------------------------------------------------ #

@app.get("/health")
def health(): #use to check if server is alive
    return {"status": "ok", "service": "VibeSeek Week 3"}


@app.post("/index")
def start_indexing(req: IndexRequest):
    """
    Resolve the video id, check the global cache, and either return instantly
    (already indexed by anyone) or enqueue a background indexing job to poll.
    """
    job_id = str(uuid.uuid4())[:8]                # short random id the frontend will poll on

    # --- Cache check (goal #3): skip download + processing if already indexed --- #
    try:
        video_id = get_video_id(req.youtube_url)  # resolve the YouTube id WITHOUT downloading (cheap metadata call)
    except Exception as e:                         # bad/unreachable URL
        raise HTTPException(400, f"Could not resolve YouTube URL: {e}")   # 400 = client error

    if not req.force and redis_client.is_indexed(video_id):   # already indexed? (skip when re-indexing)
        # Mark the job done immediately so the frontend's poll flow stays identical.
        # Populate counts from the registry so the UI shows real numbers, not blanks.
        entry = redis_client.get_entry(video_id) or {}   # pull the saved catalogue entry (counts etc.)
        job_queue.set_status(job_id, {            # write a "done" status straightaway (no work needed)
            "status": "done",                     # frontend sees done on its first poll
            "url": req.youtube_url,               # echo the URL
            "video_id": video_id,                 # so the UI can search it
            "cached": True,                       # flag that this was a cache hit
            "frame_count": entry.get("frame_count", 0),          # real number from the registry
            "has_transcript": entry.get("has_transcript", False),# real flag from the registry
            "transcript_chunks": 0,               # unknown from the registry; not needed for a cache hit
            "summary": entry.get("summary"),      # the cached gist (None for older/instrumental entries)
        })
        return {"job_id": job_id, "video_id": video_id, "cached": True,   # respond instantly
                "message": "Already indexed — ready to search."}

    # --- Not cached: queue it for the single worker ---------------------------- #
    job_queue.enqueue(job_id, {                   # hand the work to the background worker
        "youtube_url": req.youtube_url,           # the URL to index
        "interval_sec": req.interval_sec,         # frame sampling interval
        "force": req.force,                       # re-index? bypass cached audio analysis
        "url": req.youtube_url,                   # kept for display in /status
    })
    return {"job_id": job_id, "cached": False, "message": "Indexing started"}   # tell the client to start polling


@app.get("/status/{job_id}")
def get_status(job_id: str):
    """Poll indexing progress."""
    status = job_queue.get_status(job_id)         # read this job's status dict from Redis
    if status is None:                            # unknown job id?
        raise HTTPException(404, "Job not found") # 404 so the frontend can stop polling
    return status                                 # hand back the current status (status, progress, results)


@app.post("/search")
def search(req: SearchRequest):
    """
    Hybrid semantic search over an indexed video. Combines CLIP visual matches
    and MiniLM transcript matches via RRF, returning top-k moments tagged by
    match source (visual / spoken / both).
    """
    if not vector_store.has_video(req.video_id):  # are there any vectors for this video in Pinecone?
        raise HTTPException(404, f"No index found for video_id '{req.video_id}'. Index it first.")   # 404 if not indexed

    # Embed the query in BOTH spaces.
    clip_vec = get_embedder().embed_text(req.query)        # CLIP-encode the query (for visual matching)
    text_vec = get_text_embedder().embed_query(req.query)  # MiniLM-encode the query (for spoken matching)

    # Pull a wider candidate set from each, then fuse down to top_k.
    pool = max(req.top_k * 2, req.top_k + 4)               # ask for extra candidates so fusion has room to work
    visual_hits = vector_store.query_frames(req.video_id, clip_vec, pool)        # nearest visual vectors
    spoken_hits = vector_store.query_transcripts(req.video_id, text_vec, pool)   # nearest spoken vectors

    fused = _rrf_fuse(visual_hits, spoken_hits, top_k=req.top_k)   # blend the two lists into one ranking (RRF)

    # Decorate with thumbnail + YouTube deep links for the UI.
    for r in fused:                                        # for each final result...
        r["thumbnail_url"] = _thumbnail_url(r["image_path"])           # the Cloudinary image to show
        r["youtube_url"] = _youtube_link(req.video_id, r["timestamp"]) # deep link that jumps to this timestamp

    return {                                               # the JSON the frontend renders
        "query": req.query,                               # echo the query
        "video_id": req.video_id,                         # echo which video
        "results": fused,                                 # the ranked moments
    }


@app.get("/audio-analysis/{video_id}")
def audio_analysis(video_id: str):
    """
    Beat grid + top energy moments for a video. Served from the Redis cache (filled
    during indexing); falls back to computing from the source file if it's still on
    local disk.
    """
    if not redis_client.is_indexed(video_id):     # is this video in the global registry at all?
        raise HTTPException(404, f"No index found for video_id '{video_id}'.")   # 404 if never indexed

    # Prefer the global Redis cache so this works even after local cleanup.
    analysis = redis_client.get_audio(video_id)   # try the cached librosa result first

    if analysis is None:                          # not cached (e.g. analysis failed during indexing)?
        # Fall back to the downloaded source file (extension varies: mp4/mkv/webm).
        matches = glob(f"{DOWNLOADS_DIR}/{video_id}.*")   # look for the source file still on disk
        if not matches:                           # nothing to analyse and no cache?
            raise HTTPException(404, f"Audio analysis for '{video_id}' is unavailable.")   # give up
        try:
            analysis = audio_analyzer.get_or_analyze(video_id, matches[0])   # compute it now from the file
            redis_client.set_audio(video_id, analysis)   # and cache it for next time
        except Exception as e:                    # librosa blew up?
            raise HTTPException(500, f"Audio analysis failed: {e}")   # 500 = server error

    # Add deep links so the UI can jump straight to each energy moment.
    for peak in analysis.get("energy_peaks", []):  # for each high-energy moment...
        peak["youtube_url"] = _youtube_link(video_id, peak["timestamp"])   # attach a jump-to link
    if analysis.get("top_moment"):                 # and the single hottest moment, if any...
        analysis["top_moment"]["youtube_url"] = _youtube_link(video_id, analysis["top_moment"]["timestamp"])   # link it too

    return {"video_id": video_id, **analysis}     # return the id plus all analysis fields


@app.get("/indexes")
def list_indexes():
    """List all indexed videos from the global registry."""
    return {"indexes": redis_client.list_registry()}   # read every catalogue entry from Redis
