"""
VibeSeek - Week 3
Central config: loads every cloud credential / setting from environment variables
(.env locally, repository Secrets on Hugging Face Spaces). Keeping it all in one
place means no secret is ever hard-coded inside a module, and switching between
local dev and the deployed Space is just a matter of which env vars are present.
"""

import os                              # os.getenv() reads environment variables
from dotenv import load_dotenv         # load_dotenv() pulls key=value pairs from a .env file

load_dotenv()                          # read the local .env into the environment (does nothing in prod, where real env vars already exist)

# --- Pinecone (cloud vector DB, replaces ChromaDB) -------------------------- #
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")        # secret key that authenticates us to Pinecone ("" if unset)
PINECONE_INDEX = os.getenv("PINECONE_INDEX", "vibeseek")    # name of the single shared index we store all vectors in
PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")         # which cloud the serverless index lives on (free Starter = AWS)
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1") # which region within that cloud (free Starter = us-east-1)
VECTOR_DIM = 512   # the index width: CLIP is 512-dim; MiniLM (384) gets zero-padded up to this so both fit one index

# --- Cloudinary (frame thumbnail hosting, replaces local /frames) ----------- #
CLOUDINARY_CLOUD_NAME = os.getenv("CLOUDINARY_CLOUD_NAME", "")   # your Cloudinary account's unique name (part of every image URL)
CLOUDINARY_API_KEY = os.getenv("CLOUDINARY_API_KEY", "")        # public-ish key identifying API calls
CLOUDINARY_API_SECRET = os.getenv("CLOUDINARY_API_SECRET", "")  # secret used to sign uploads (keep private)
CLOUDINARY_FOLDER = os.getenv("CLOUDINARY_FOLDER", "vibeseek/frames")  # folder prefix every uploaded frame is stored under

# --- Upstash Redis (job queue state + global index registry) ---------------- #
REDIS_URL = os.getenv("REDIS_URL", "")   # full rediss:// TLS connection string (host + port + password in one URL)

# --- Groq (optional, free tier — AI-written video summaries) ----------------- #
# Get a free key at https://console.groq.com/keys (no credit card).
# Leave blank to fall back to the free offline extractive summary.
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")                          # "" = disabled, use the offline summary instead
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")       # free, capable model on the Groq free tier

# --- Local working directory (temp frames before they're uploaded) ---------- #
DATA_DIR = os.getenv("VIBESEEK_DATA_DIR", "vibeseek_data")   # where downloads/frames are written before going to the cloud
