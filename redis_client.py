"""
VibeSeek - Week 3
Redis client + global index registry, backed by Upstash Redis (free tier, no card).

Redis has two jobs in Week 3, both sharing the single connection created here:
  1. A GLOBAL "is this video already indexed?" cache + catalogue (this file). A URL
     indexed by ANY user becomes instantly searchable for EVERYONE, because the
     registry lives in the cloud instead of on one server's disk.
  2. Storing job state (see job_queue.py) so /status works across threads.

The registry is stored as a Redis hash: field = video_id, value = JSON catalogue entry.
"""

import json                # turn dict entries into strings to store, and back again
import redis               # redis-py: talks to Upstash over the Redis protocol (TLS)
import config              # central env-backed settings (gives us REDIS_URL)

REGISTRY_KEY = "vibeseek:registry"   # the Redis hash name that holds video_id -> JSON entry

# One shared, thread-safe connection pool. decode_responses=True returns str (not
# bytes). Upstash provides a rediss:// (TLS) URL. Stays None if unconfigured so
# importing this module never crashes during local experiments.
# socket_keepalive + health_check_interval keep idle connections alive and let
# redis-py detect/replace one Upstash has dropped.
_redis = redis.from_url(                 # build a client (connection pool) from the URL
    config.REDIS_URL,                    # the rediss:// connection string
    decode_responses=True,               # give us Python str back instead of raw bytes
    socket_keepalive=True,               # send TCP keepalives so idle sockets aren't dropped
    health_check_interval=30,            # ping every 30s on reuse; recycle dead connections
    retry_on_timeout=True,               # transparently retry a read that timed out once
) if config.REDIS_URL else None          # ...but only if a URL was actually configured


def get_client() -> redis.Redis:
    """Returns the shared Redis connection, or raises if REDIS_URL is unset."""
    if _redis is None:                   # guard: we never built a client
        raise RuntimeError("REDIS_URL is not set — configure Upstash Redis in your env.")
    return _redis                        # hand back the shared client


# ------------------------------------------------------------------ #
#  Global index registry (the video cache for goal #3)               #
# ------------------------------------------------------------------ #

def is_indexed(video_id: str) -> bool:
    """Global cache check: True if this video_id was already indexed by anyone."""
    return bool(get_client().hexists(REGISTRY_KEY, video_id))   # HEXISTS = does this field exist in the hash?


def set_indexed(video_id: str, youtube_url: str, frame_count: int,
                has_transcript: bool, summary: dict | None = None):
    """Record a finished index in the global catalogue so it can be reused later."""
    entry = {                            # build the catalogue record for this video
        "video_id": video_id,            # the YouTube id (also the Pinecone namespace)
        "youtube_url": youtube_url,       # the original URL the user submitted
        "frame_count": frame_count,       # how many frames we embedded
        "has_transcript": has_transcript, # whether Whisper found any speech
        "summary": summary,               # extractive gist + keywords (None for no-speech videos)
    }
    get_client().hset(REGISTRY_KEY, video_id, json.dumps(entry))   # HSET field=video_id value=JSON string


def get_entry(video_id: str) -> dict | None:
    """Fetch one catalogue entry, or None if the video isn't indexed."""
    raw = get_client().hget(REGISTRY_KEY, video_id)   # HGET returns the JSON string (or None)
    return json.loads(raw) if raw else None           # parse it back to a dict, or None if missing


def list_registry() -> list[dict]:
    """All catalogue entries, for the /indexes endpoint."""
    return [json.loads(v) for v in get_client().hgetall(REGISTRY_KEY).values()]   # HGETALL -> parse every JSON value


# ------------------------------------------------------------------ #
#  Audio analysis cache (librosa results, kept global)               #
# ------------------------------------------------------------------ #

AUDIO_KEY = "vibeseek:audio"   # the Redis hash name that holds video_id -> JSON analysis result


def set_audio(video_id: str, data: dict):
    """Cache a video's beat/energy analysis so it survives source-file cleanup."""
    get_client().hset(AUDIO_KEY, video_id, json.dumps(data))   # store the analysis dict as JSON under this video_id


def get_audio(video_id: str) -> dict | None:
    """Fetch cached audio analysis, or None if it hasn't been computed yet."""
    raw = get_client().hget(AUDIO_KEY, video_id)   # HGET the JSON string (or None)
    return json.loads(raw) if raw else None        # parse to dict, or None if absent
