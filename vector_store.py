"""
VibeSeek - Week 3
Vector Store: cloud vector storage on Pinecone (replaces the Week 2 ChromaDB).

Design
  - ONE serverless index at dimension 512 (CLIP's width) — well within the free
    Starter plan, which allows a single index.
  - Each video gets its own Pinecone *namespace* (= video_id), so per-video search
    is a namespace-scoped query and "does this video exist?" is a namespace check.
  - Every vector carries metadata: video_id, timestamp, image_path (a Cloudinary
    URL), transcript_chunk, source ("visual" | "audio").
  - MiniLM transcript vectors are 384-dim, so they are zero-padded up to 512 before
    upsert. Search always filters by `source`, so a padded transcript vector is only
    ever compared against other padded transcript vectors — the trailing zeros
    cancel in both the dot product and the norms, so cosine scores are identical to
    the native 384-dim space. (A CLIP query, likewise, only ever hits 512-dim
    visual vectors.) This is what lets two embedding spaces share one index.

The lightweight catalogue (which videos are indexed) now lives in Redis — see
redis_client.py — so it's global across users, not tied to one disk.
"""

import numpy as np                                 # for the zero-padding math
from pinecone import Pinecone, ServerlessSpec      # Pinecone v5 SDK: client + index-spec helper
import config                                       # central env-backed settings (API key, index name, dims)

# Single client, reused across requests.
_pc = Pinecone(api_key=config.PINECONE_API_KEY)    # authenticate to Pinecone once at import time


def _ensure_index():
    """Create the serverless index on first run; reattach to it on later runs."""
    existing = [i["name"] for i in _pc.list_indexes()]   # names of indexes already in this project
    if config.PINECONE_INDEX not in existing:            # if ours doesn't exist yet...
        print(f"[VectorStore] Creating Pinecone index '{config.PINECONE_INDEX}'...")   # ...log that we're creating it
        _pc.create_index(                                # ...and create it
            name=config.PINECONE_INDEX,                  # the index name from config
            dimension=config.VECTOR_DIM,                 # 512 dims (CLIP width)
            metric="cosine",                             # use cosine similarity for scoring
            spec=ServerlessSpec(cloud=config.PINECONE_CLOUD, region=config.PINECONE_REGION),  # where to host it (free tier = aws/us-east-1)
        )
    return _pc.Index(config.PINECONE_INDEX)              # return a handle to the (now existing) index


# get_or_create equivalent: a restart reattaches to the existing cloud index.
_index = _ensure_index()                                # build the index handle once, reused everywhere below

# Pinecone caps vectors per upsert call; chunk large videos into batches.
_UPSERT_BATCH = 100                                     # how many vectors to send per upsert request


def _pad(vec) -> list:
    """
    Zero-pad a vector up to VECTOR_DIM and return a plain list for Pinecone.
    No-op for 512-dim CLIP vectors; widens 384-dim MiniLM vectors to 512.
    """
    v = np.asarray(vec, dtype=np.float32).ravel()        # make sure it's a flat float32 numpy array
    if v.shape[0] < config.VECTOR_DIM:                   # if it's shorter than the index width (e.g. 384)...
        v = np.pad(v, (0, config.VECTOR_DIM - v.shape[0]))   # ...append zeros until it reaches 512
    return v.tolist()                                    # Pinecone wants a plain Python list of floats


def _upsert_batched(namespace: str, vectors: list):
    """Upsert vectors into a namespace in batches to respect Pinecone limits."""
    for start in range(0, len(vectors), _UPSERT_BATCH):  # walk the list in steps of 100
        _index.upsert(vectors=vectors[start:start + _UPSERT_BATCH], namespace=namespace)   # send one batch into the video's namespace


# ------------------------------------------------------------------ #
#  Writes                                                            #
# ------------------------------------------------------------------ #

def add_frames(video_id: str, frame_embeddings: list, frame_transcripts: list[str],
               image_urls: list[str]):
    """
    Stores CLIP frame embeddings (source="visual").

    Args:
        frame_embeddings:  list of FrameEmbedding (has .frame and .embedding)
        frame_transcripts: parallel list of the nearest transcript text per frame
                           ("" when there's no speech) — kept as metadata so each
                           visual hit can also show what was being said.
        image_urls:        parallel list of Cloudinary URLs for each frame.
    """
    if not frame_embeddings:                             # nothing to store?
        return                                           # bail out early

    vectors = []                                         # accumulator for the Pinecone records
    for fe, transcript, url in zip(frame_embeddings, frame_transcripts, image_urls):   # walk all three parallel lists together
        frame = fe.frame                                 # the Frame object (timestamp, index, path)
        vectors.append({                                 # build one Pinecone vector record
            "id": f"{video_id}:f:{frame.frame_index}",   # unique id: "<video>:f:<frameindex>" ('f' = frame)
            "values": _pad(fe.embedding),                # the 512-dim CLIP embedding as a list
            "metadata": {                                # searchable/returnable metadata for this vector
                "video_id": video_id,                    # which video it belongs to
                "timestamp": float(frame.timestamp),     # seconds into the video
                "image_path": url or "",                 # the Cloudinary CDN URL for this frame
                "transcript_chunk": transcript or "",    # nearest spoken line (caption aid)
                "source": "visual",                      # tags this as a CLIP/visual vector
            },
        })

    _upsert_batched(video_id, vectors)                   # push them all to Pinecone, batched
    print(f"[VectorStore] Upserted {len(vectors)} frame vectors for {video_id}.")   # log how many we stored


def add_transcripts(video_id: str, chunks: list, embeddings, nearest_image_urls: list[str]):
    """
    Stores transcript-chunk embeddings (source="audio").

    Args:
        chunks:             list of TranscriptChunk (has .start, .end, .text)
        embeddings:         (N, 384) array of MiniLM vectors, aligned to chunks
        nearest_image_urls: parallel list of the closest frame's Cloudinary URL per
                            chunk so a spoken-word hit still has something to show.
    """
    if not chunks:                                       # no speech was found?
        return                                           # nothing to store

    vectors = []                                         # accumulator for the Pinecone records
    for i, (chunk, url) in enumerate(zip(chunks, nearest_image_urls)):   # walk chunks + their nearest-frame URLs
        vectors.append({                                 # build one Pinecone vector record
            "id": f"{video_id}:t:{i}",                   # unique id: "<video>:t:<index>" ('t' = transcript)
            "values": _pad(embeddings[i]),               # the MiniLM vector, padded 384 -> 512
            "metadata": {                                # metadata for this spoken chunk
                "video_id": video_id,                    # which video it belongs to
                "timestamp": float((chunk.start + chunk.end) / 2),   # midpoint of the spoken window (seconds)
                "image_path": url or "",                 # nearest frame's Cloudinary URL (so it has a thumbnail)
                "transcript_chunk": chunk.text,          # the actual words spoken
                "source": "audio",                       # tags this as a spoken/MiniLM vector
            },
        })

    _upsert_batched(video_id, vectors)                   # push them all to Pinecone, batched
    print(f"[VectorStore] Upserted {len(vectors)} transcript vectors for {video_id}.")   # log how many we stored


# ------------------------------------------------------------------ #
#  Queries                                                           #
# ------------------------------------------------------------------ #

def _hits(resp, text_key: str) -> list[dict]:
    """
    Flattens a Pinecone query response into the dict shape main.py's RRF fusion
    expects. The cosine metric already returns a 0..1-ish similarity as `score`
    (higher = better), so no distance conversion is needed.

    text_key is "transcript" for visual hits and "text" for spoken hits, matching
    the keys the fusion step reads.
    """
    out = []                                             # accumulator for cleaned-up hits
    for m in resp.get("matches", []) or []:              # iterate the raw matches (empty list if none)
        md = m.get("metadata", {}) or {}                 # the metadata dict we stored on upsert
        out.append({                                     # reshape into what main.py wants
            "timestamp": float(md.get("timestamp", 0.0)),    # seconds into the video
            "score": float(m.get("score", 0.0)),             # cosine similarity (higher = better)
            "image_path": md.get("image_path", ""),          # Cloudinary thumbnail URL
            text_key: md.get("transcript_chunk", ""),        # caption text, under "transcript" or "text"
        })
    return out                                           # the list of hit dicts


def query_frames(video_id: str, clip_vec, k: int) -> list[dict]:
    """Cosine search over a video's visual (CLIP) vectors. Returns up to k hits."""
    resp = _index.query(                                 # ask Pinecone for nearest neighbours
        namespace=video_id,                              # only search this video's namespace
        vector=_pad(clip_vec),                           # the query embedding (padded to 512)
        top_k=k,                                          # how many results to return
        filter={"source": "visual"},                     # only consider visual vectors
        include_metadata=True,                           # return the stored metadata too
    )
    return _hits(resp, "transcript")                     # reshape; caption goes under "transcript"


def query_transcripts(video_id: str, text_vec, k: int) -> list[dict]:
    """Cosine search over a video's spoken (MiniLM) vectors. Returns up to k hits."""
    resp = _index.query(                                 # ask Pinecone for nearest neighbours
        namespace=video_id,                              # only search this video's namespace
        vector=_pad(text_vec),                           # the query embedding (MiniLM, padded to 512)
        top_k=k,                                          # how many results to return
        filter={"source": "audio"},                      # only consider spoken vectors
        include_metadata=True,                           # return the stored metadata too
    )
    return _hits(resp, "text")                           # reshape; caption goes under "text"


def has_video(video_id: str) -> bool:
    """True if any vectors are stored under this video_id's namespace."""
    stats = _index.describe_index_stats()                # ask Pinecone for per-namespace counts
    # The SDK response exposes namespaces as an attribute; fall back to dict access.
    namespaces = getattr(stats, "namespaces", None)      # try attribute access first
    if namespaces is None and isinstance(stats, dict):   # if that failed and it's a dict...
        namespaces = stats.get("namespaces", {})         # ...read it as a dict key
    return bool(namespaces) and video_id in namespaces   # True only if our video has a namespace
