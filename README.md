---
title: Skim
emoji: 🎬
colorFrom: purple
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

<div align="center">

# 🎬 Skim

**Semantic Video Search — find any moment by vibe, not by timestamp.**

Paste a YouTube URL. Describe a vibe. Jump to that exact moment — by what was _seen_ **and** what was _said_.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-8-646CFF?style=flat-square&logo=vite&logoColor=white)](https://vitejs.dev/)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![Deployed on HF Spaces](https://img.shields.io/badge/🤗-Hugging%20Face%20Spaces-blue?style=flat-square)](https://huggingface.co/spaces/Herta09/Skim)

</div>

---

## ✨ What is Skim?

Skim is a **multi-modal semantic video search engine**. Instead of scrubbing through hours of footage, you describe the _vibe_ of the moment you're looking for — a mood, an action, a line of dialogue — and Skim jumps you straight there.

It works by combining **two AI search spaces**:

| Space | Model | What it matches |
|-------|-------|-----------------|
| 🎞️ **Visual** | OpenAI **CLIP** (ViT-B/32) | What was _seen_ in each frame |
| 🗣️ **Spoken** | **MiniLM** (all-MiniLM-L6-v2) | What was _said_ (via Whisper transcription) |

Results from both spaces are blended into one ranking using **Reciprocal Rank Fusion (RRF)**, and each result is tagged with its match source — `visual`, `spoken`, or `both`.

---

## 🚀 Key Features

- **🔍 Hybrid Semantic Search** — Search across what was seen _and_ what was said simultaneously
- **🎙️ Whisper Transcription** — Automatic speech-to-text with timestamped chunks
- **🥁 Beat & Energy Analysis** — librosa-powered BPM detection, beat grid, and top energy moments
- **📝 AI Summaries** — Groq-powered (Llama 3.3) video gist with free offline fallback
- **🌍 Global Video Cache** — Index a video once; everyone can search it instantly via Redis
- **🧵 Single-Worker Queue** — Serialized job processing prevents OOM on concurrent requests
- **☁️ Fully Cloud-Backed** — Pinecone vectors, Cloudinary thumbnails, Upstash Redis state
- **💸 100% Free Tier** — No credit card required for any service
- **⏯️ YouTube Deep Links** — Click any result to jump directly to that timestamp

---

## 🏗️ Architecture

```
YouTube URL
    │
    ▼
yt-dlp ──────────► MP4 file ─────────────────────┐
    │                                              │
    ▼                                              ▼
OpenCV ──────────► Frames (every 2s)          Whisper (base)
    │                   │                         │
    ▼                   ▼                         ▼
CLIP ViT-B/32      Cloudinary CDN         Timestamped transcript
    │               (thumbnails)                  │
    ▼                                             ▼
512-dim visual                              MiniLM (384-dim)
 embeddings                                text embeddings
    │                                             │
    └──────────► Pinecone (cloud) ◄───────────────┘
                     │
                     ▼
               Search query
         (CLIP + MiniLM encoded)
                     │
                     ▼
            Reciprocal Rank Fusion
                     │
                     ▼
         Top-K moments + deep links
         (tagged: visual / spoken / both)
```

---

## 🛠️ Tech Stack

### Backend
| Technology | Purpose |
|-----------|---------|
| **FastAPI** | REST API server |
| **OpenAI CLIP** (ViT-B/32) | Visual frame embeddings (512-dim) |
| **OpenAI Whisper** (base) | Speech-to-text transcription |
| **Sentence Transformers** (MiniLM) | Transcript text embeddings (384-dim) |
| **librosa** | Beat detection, BPM, and energy analysis |
| **yt-dlp** | YouTube video downloading |
| **OpenCV** | Frame extraction at configurable intervals |
| **Pinecone** | Cloud vector database (cosine similarity) |
| **Cloudinary** | Frame thumbnail CDN hosting |
| **Upstash Redis** | Job queue, global index registry, audio cache |
| **Groq** (optional) | AI-written video summaries (Llama 3.3, free tier) |

### Frontend
| Technology | Purpose |
|-----------|---------|
| **React 19** | UI framework |
| **Vite 8** | Dev server and bundler |
| **Framer Motion** | Smooth animations and transitions |
| **Lucide React** | Iconography |

---

## 📦 Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **ffmpeg** on PATH (required by yt-dlp, Whisper, and librosa)
- ~4 GB disk (for CLIP model weights + video downloads)
- GPU optional but recommended for faster embedding

---

## ⚡ Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/EternBeep/Skim.git
cd Skim
```

### 2. Set up the backend

```bash
# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate         # Windows
# source venv/bin/activate   # macOS / Linux

# Install PyTorch (GPU: see https://pytorch.org/get-started/locally/)
pip install torch torchvision

# Install OpenAI CLIP
pip install git+https://github.com/openai/CLIP.git

# Install all remaining dependencies
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
copy .env.example .env       # Windows
# cp .env.example .env       # macOS / Linux
```

Open `.env` and fill in your credentials (all services have a free tier, no credit card):

| Service | Sign-Up | Required Keys |
|---------|---------|---------------|
| [Pinecone](https://app.pinecone.io) | Free Starter | `PINECONE_API_KEY` |
| [Cloudinary](https://cloudinary.com) | Free | `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` |
| [Upstash Redis](https://console.upstash.com) | Free | `REDIS_URL` (the `rediss://` TLS string) |
| [Groq](https://console.groq.com/keys) | Free (optional) | `GROQ_API_KEY` — leave blank for offline summaries |

### 4. Start the backend

```bash
uvicorn main:app --reload --port 8000
```

Verify at [http://localhost:8000/health](http://localhost:8000/health) → `{"status": "ok"}`

### 5. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) and start searching! 🎉

> **Windows shortcut:** Run `start.bat` from the project root to launch both servers and open the browser automatically.

---

## 🧪 CLI Test (No Frontend Needed)

```bash
python test_pipeline.py \
  --url "https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  --query "dance moves" \
  --interval 3.0 \
  --transcribe
```

---

## 📡 API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | `GET` | Health check |
| `/index` | `POST` | Start indexing a YouTube video |
| `/status/{job_id}` | `GET` | Poll indexing progress |
| `/search` | `POST` | Semantic search over an indexed video |
| `/audio-analysis/{video_id}` | `GET` | Beat grid + energy peaks for a video |
| `/indexes` | `GET` | List all globally indexed videos |

### `POST /index`

```json
{
  "youtube_url": "https://www.youtube.com/watch?v=...",
  "interval_sec": 2.0,
  "force": false
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `youtube_url` | string | — | The YouTube video URL to index |
| `interval_sec` | float | `2.0` | Frame sampling interval in seconds |
| `force` | bool | `false` | Set `true` to bypass cache and re-index |

### `POST /search`

```json
{
  "video_id": "dQw4w9WgXcQ",
  "query": "the beat drop",
  "top_k": 5
}
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `video_id` | string | — | The YouTube video ID to search |
| `query` | string | — | Natural language vibe description |
| `top_k` | int | `5` | Number of results to return |

### Response Example

```json
{
  "query": "the beat drop",
  "video_id": "dQw4w9WgXcQ",
  "results": [
    {
      "timestamp": 42.0,
      "score": 0.01639,
      "transcript": "Never gonna give you up",
      "match_source": "both",
      "thumbnail_url": "https://res.cloudinary.com/...",
      "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s"
    }
  ]
}
```

---

## 📁 Project Structure

```
Skim/
├── main.py                 # FastAPI server — endpoints, RRF fusion, job orchestration
├── frame_extractor.py      # yt-dlp download + OpenCV frame sampling
├── clip_embedder.py        # CLIP image/text encoding (512-dim)
├── text_embedder.py        # MiniLM transcript embeddings (384-dim)
├── audio_transcriber.py    # Whisper speech-to-text
├── audio_analyzer.py       # librosa beat detection + energy peaks
├── summarizer.py           # AI (Groq) + extractive + metadata summaries
├── vector_store.py         # Pinecone cloud vector DB
├── storage.py              # Cloudinary frame thumbnail hosting
├── redis_client.py         # Upstash Redis: global registry + audio cache
├── job_queue.py            # Single-worker serialized job queue
├── config.py               # Central env-backed configuration
├── test_pipeline.py        # CLI test script (no server needed)
├── requirements.txt        # Python dependencies
├── Dockerfile              # Production image (HF Spaces, CPU-only)
├── start.bat               # Windows: launch backend + frontend together
├── .env.example            # Template for environment variables
├── DEPLOY.md               # Deployment guide (HF Spaces + Vercel)
│
└── frontend/               # React + Vite frontend
    ├── index.html
    ├── package.json
    ├── vite.config.js
    ├── vercel.json          # Vercel deployment config
    └── src/
        ├── App.jsx          # Main application component
        ├── App.css          # Styling (dark theme, glassmorphism)
        ├── main.jsx         # Entry point
        ├── constants/       # API base URL, vibe suggestions
        ├── components/      # UI components
        │   ├── Header.jsx
        │   ├── WelcomeScreen.jsx
        │   ├── StatusBadge.jsx
        │   ├── SummaryPanel.jsx
        │   ├── AudioPanel.jsx
        │   ├── ResultsGrid.jsx
        │   └── HowItWorks.jsx
        └── utils/           # Helpers (time formatting, etc.)
```

---

## ☁️ Deployment

### Backend → Hugging Face Spaces (Docker)

1. Create a new Space → **SDK = Docker**, hardware = **CPU basic (free)**
2. Push this repo to the Space (the `Dockerfile` at the root handles everything)
3. Add your credentials as **Secrets** in Space Settings:
   `PINECONE_API_KEY`, `PINECONE_INDEX`, `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`, `REDIS_URL`
4. Verify at `https://<user>-skim.hf.space/health`

### Frontend → Vercel

1. Import the repo in Vercel, set **Root Directory = `frontend`**
2. Add env var `VITE_API_BASE_URL` = your HF Space URL
3. Deploy — the frontend talks to the HF backend; thumbnails load from Cloudinary CDN

> See [DEPLOY.md](DEPLOY.md) for the full step-by-step guide.

---

## 🧠 How It Works

<table>
<tr><td>

### 1️⃣ See + Hear
OpenCV samples frames every 2 seconds. Whisper transcribes the audio into timestamped spoken segments.

</td><td>

### 2️⃣ Dual Embeddings
CLIP encodes each frame into a 512-dim visual vector. MiniLM encodes each spoken line into a 384-dim text vector. Both share one Pinecone index via zero-padding.

</td><td>

### 3️⃣ Hybrid Search
Your query is encoded in both spaces. Reciprocal Rank Fusion blends visual + spoken hits into one ranking, tagged by match source.

</td></tr>
</table>

---

## 🗺️ Roadmap

- [ ] Scene change detection (PySceneDetect)
- [ ] Emotion detection via face embeddings
- [ ] Speaker diarisation
- [ ] Export clip as short video
- [ ] Playlist / multi-video search
- [ ] User accounts + search history

---

## 🤝 Contributing

Contributions are welcome! Feel free to open an issue or submit a pull request.

1. Fork the repository
2. Create a feature branch (`git checkout -b feat/amazing-feature`)
3. Commit your changes (`git commit -m "feat: add amazing feature"`)
4. Push to the branch (`git push origin feat/amazing-feature`)
5. Open a Pull Request

---


<div align="center">

**Built with** ❤️ **using CLIP · Whisper · librosa · Pinecone · Cloudinary · Redis**

[⬆ Back to top](#-skim)

</div>
