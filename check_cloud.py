"""
VibeSeek - Week 3
Cloud smoke test: verifies that the Pinecone, Cloudinary and Upstash Redis
credentials in .env actually connect. Run this before booting the full server so
config problems surface fast (no torch/whisper load required).

    python check_cloud.py
"""

import config   # importing this loads .env via python-dotenv, so creds are available

ok = True       # overall pass/fail flag, flipped to False by any failed check


def check(name: str, fn):
    """Run one connectivity check and print a pass/fail line."""
    global ok                                  # we may flip the module-level flag
    try:
        detail = fn()                          # run the check; returns a short detail string
        print(f"[PASS] {name}: {detail}")      # report success
    except Exception as e:                      # any error means this service didn't connect
        ok = False                             # mark the overall run as failed
        print(f"[FAIL] {name}: {e}")           # report the error message


# --- Pinecone --------------------------------------------------------------- #
def _pinecone():
    from pinecone import Pinecone             # import here so a missing dep only fails this check
    pc = Pinecone(api_key=config.PINECONE_API_KEY)   # authenticate with our key
    names = [i["name"] for i in pc.list_indexes()]   # list existing indexes (also proves the key works)
    return f"connected, existing indexes = {names or 'none yet'}"   # detail line for the PASS message


# --- Cloudinary ------------------------------------------------------------- #
def _cloudinary():
    import cloudinary                         # SDK config object
    import cloudinary.api                     # submodule with ping()
    cloudinary.config(                        # configure with our credentials
        cloud_name=config.CLOUDINARY_CLOUD_NAME,
        api_key=config.CLOUDINARY_API_KEY,
        api_secret=config.CLOUDINARY_API_SECRET,
        secure=True,
    )
    res = cloudinary.api.ping()               # ping() hits Cloudinary and validates the creds
    return f"ping = {res.get('status')}"      # should be "ok"


# --- Upstash Redis ---------------------------------------------------------- #
def _redis():
    import redis                              # redis-py client
    r = redis.from_url(config.REDIS_URL, decode_responses=True)   # connect using the rediss:// URL
    r.set("vibeseek:healthcheck", "ok")       # write a test key
    return f"ping ok, roundtrip value = {r.get('vibeseek:healthcheck')}"   # read it back to prove read+write work


check("Pinecone", _pinecone)        # run the Pinecone check
check("Cloudinary", _cloudinary)    # run the Cloudinary check
check("Upstash Redis", _redis)      # run the Redis check

print("\nAll cloud services OK." if ok else "\nSome checks FAILED -- fix .env above.")   # final summary line
