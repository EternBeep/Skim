"""
VibeSeek - Week 3
Job Queue: a single background worker that serialises heavy indexing jobs.

Why: indexing is heavy (yt-dlp + CLIP + Whisper + librosa). If several users hit
/index at once, running them all concurrently would exhaust memory and crash the
box. So every request runs through ONE worker, a single job at a time — concurrent
users queue up safely instead of taking the server down (goal #4).

Transport vs. state:
  - The queue itself is an in-process queue.Queue. The backend runs as a SINGLE
    instance on Hugging Face Spaces, so there's nothing to coordinate across
    processes, and an in-process queue is reliable + costs zero Redis commands
    while idle.
  - Job STATE lives in Upstash Redis (a hash) so /status works, and — together
    with the global registry in redis_client.py — repeated URLs stay cached for
    everyone.
  - We deliberately do NOT use a Redis BLPOP consumer: Upstash's free tier drops
    long-idle blocking connections, which makes a persistent blocking worker
    unreliable.
"""

import json                      # serialise/deserialise job status dicts
import queue                     # thread-safe in-process FIFO queue
import threading                 # to run the worker on a background thread + guard startup
import redis_client              # shared Redis connection (we store job state here)

JOBS_KEY = "vibeseek:jobs"       # the Redis hash name: field = job_id, value = JSON status dict

_queue: "queue.Queue" = queue.Queue()   # the in-process pending-jobs queue (jobs waiting to run)
_worker_started = False          # flag so we only ever launch one worker thread
_lock = threading.Lock()         # protects the flag from two threads starting the worker at once


# ------------------------------------------------------------------ #
#  Job status (stored in Redis so /status survives the thread)       #
# ------------------------------------------------------------------ #

def set_status(job_id: str, status: dict):
    redis_client.get_client().hset(JOBS_KEY, job_id, json.dumps(status))   # overwrite this job's status with a fresh JSON dict


def get_status(job_id: str) -> dict | None:
    raw = redis_client.get_client().hget(JOBS_KEY, job_id)   # read the JSON string for this job (or None)
    return json.loads(raw) if raw else None                 # parse to dict, or None if the job is unknown


def update_status(job_id: str, **fields) -> dict:
    """Merge fields into the existing status dict and persist it."""
    cur = get_status(job_id) or {}   # start from the current status (or empty if none yet)
    cur.update(fields)               # merge in the new key/values (e.g. status="embedding")
    set_status(job_id, cur)          # write the merged dict back to Redis
    return cur                       # return it for convenience


# ------------------------------------------------------------------ #
#  Enqueue + worker                                                  #
# ------------------------------------------------------------------ #

def enqueue(job_id: str, payload: dict):
    """Mark the job queued (in Redis) and hand it to the in-process worker."""
    set_status(job_id, {"status": "queued", **payload})   # record initial state so /status shows "queued" immediately
    _queue.put({"job_id": job_id, **payload})             # drop the work item onto the queue for the worker to pick up


def start_worker(handler):
    """
    Launch the single background worker (idempotent). `handler(job_id, payload)`
    does the real indexing work. Running exactly one worker is the whole point —
    it serialises heavy jobs so concurrent users can't OOM the host.
    """
    global _worker_started           # we're going to flip the module-level flag
    with _lock:                      # only one thread may run this block at a time
        if _worker_started:          # if a worker already exists...
            return                   # ...do nothing (idempotent)
        _worker_started = True       # otherwise claim the slot

    def _loop():                     # the worker's main loop (runs forever on its thread)
        print("[JobQueue] Worker started, waiting for jobs...")   # one-time startup log
        while True:                  # keep processing jobs until the process exits
            msg = _queue.get()       # BLOCK here (in-process) until a job is available
            job_id = msg.pop("job_id")   # pull the job_id out, leaving just the payload
            try:
                handler(job_id, msg)     # run the actual indexing pipeline to completion
            except Exception as e:       # never let one failed job kill the worker thread
                update_status(job_id, status="error", error=str(e))   # record the failure for /status
                print(f"[JobQueue] Job {job_id} failed: {e}")          # log it for debugging
            finally:
                _queue.task_done()       # tell the queue this item is fully handled

    threading.Thread(target=_loop, daemon=True, name="vibeseek-worker").start()   # spawn the loop as a daemon thread (dies with the app)
