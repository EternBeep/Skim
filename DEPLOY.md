# VibeSeek — Week 3 Deployment Guide

Everything below is **free tier, no credit card** (Cloudinary replaces R2, Hugging
Face Spaces replaces Render).

## 0. Provision the cloud services (all free, no card)

| Service | Sign up | What you need |
|---|---|---|
| **Pinecone** | https://app.pinecone.io | API key (Starter project, AWS `us-east-1`) |
| **Cloudinary** | https://cloudinary.com | Cloud name + API key + API secret |
| **Upstash Redis** | https://console.upstash.com | The `rediss://` (TLS) connection URL |

You do **not** pre-create the Pinecone index — `vector_store.py` creates it on first
boot (dimension 512, cosine).

## 1. Local run

```bash
cd D:\Project2\VibeSeek
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          # then fill in the keys
uvicorn main:app --reload --port 8000

cd frontend
npm install
npm run dev                     # defaults to http://localhost:8000 backend
```

## 2. Backend → Hugging Face Spaces (Docker)

1. Create a new Space: **SDK = Docker**, hardware = **CPU basic (free)**.
2. Push this repo to the Space (the `Dockerfile` is at the root). The Space's
   `README.md` must start with this metadata block:

   ```yaml
   ---
   title: VibeSeek
   emoji: 🎬
   colorFrom: purple
   colorTo: pink
   sdk: docker
   app_port: 7860
   pinned: false
   ---
   ```

3. In **Space → Settings → Variables and secrets**, add as **Secrets**:
   `PINECONE_API_KEY`, `PINECONE_INDEX`, `PINECONE_CLOUD`, `PINECONE_REGION`,
   `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`,
   `CLOUDINARY_FOLDER`, `REDIS_URL`.
4. The Space builds and serves at `https://<user>-vibeseek.hf.space`. Verify
   `…/health` returns `{"status":"ok"}`.

> First request after idle is slow — the Space wakes up and lazy-loads the models.

## 3. Frontend → Vercel

1. Import the repo in Vercel, set **Root Directory = `frontend`** (Vite is
   auto-detected; `frontend/vercel.json` pins the build).
2. Add env var **`VITE_API_BASE_URL`** = your Space URL
   (`https://<user>-vibeseek.hf.space`).
3. Deploy. The frontend now talks to the HF backend; thumbnails load straight from
   Cloudinary's CDN.

## 4. How the Week 3 goals map to the code

| Goal | Where |
|---|---|
| 1 · Pinecone vector DB | `vector_store.py`, `config.py` |
| 2 · Cloudinary frame hosting | `storage.py`, upload step in `main.py` |
| 3 · Global video cache | `redis_client.py` registry + cache check in `/index` |
| 4 · Redis job queue | `job_queue.py` (single serialized worker) |
| 5 · CPU optimisation | CLIP `batch_size=16`, Whisper `base` |
| 6 · Frontend API base URL | `frontend/src/App.jsx` via `VITE_API_BASE_URL` |
| 7 · Free tier, no card | Cloudinary + HF Spaces + Pinecone + Upstash |
