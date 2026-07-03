---
title: Skim
emoji: 🎬
colorFrom: purple
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# VibeSeek — Week 1
> Semantic video search: paste a YouTube URL, describe a vibe, jump to that timestamp.

## Architecture (Week 1)

```
YouTube URL
    │
    ▼
yt-dlp  ──────► MP4 file
    │
    ▼
OpenCV ────────► Frames (every 2s as JPEG)
    │
    ▼
CLIP ViT-B/32 ► 512-dim embeddings (per frame)
    │
    ▼
Cosine search ◄── Text query (also CLIP-encoded)
    │
    ▼
Top-K timestamps → YouTube deep links
```

---

## Setup

### Prerequisites
- Python 3.10+
- Node 18+
- ~4GB disk (CLIP model + video downloads)
- GPU optional but recommended for embedding speed

### Backend

```bash
cd vibeseek/backend

# 1. Create venv
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 2. Install PyTorch first (GPU: https://pytorch.org/get-started/locally/)
pip install torch torchvision

# 3. Install CLIP (from OpenAI GitHub)
pip install git+https://github.com/openai/CLIP.git

# 4. Install remaining deps
pip install opencv-python yt-dlp fastapi "uvicorn[standard]" numpy Pillow

# 5. Run server
uvicorn main:app --reload --port 8000
```

Open http://localhost:8000/docs to verify the API is running.

### Frontend

```bash
cd vibeseek/frontend

# Bootstrap with Vite
npm create vite@latest . -- --template react
# (say yes to overwrite, select React)

# Copy our App.jsx into src/ (already done)

npm install
npm run dev
```

Open http://localhost:5173

---

## Quick test (CLI, no frontend needed)

```bash
cd backend
source venv/bin/activate

# Test with any YouTube video
python test_pipeline.py \
  --url "https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  --query "dance moves" \
  --interval 3.0
```

---

## API Reference

| Endpoint | Method | Purpose |
|---|---|---|
| `POST /index` | POST | Start indexing a YouTube URL |
| `GET /status/{job_id}` | GET | Poll indexing progress |
| `POST /search` | POST | Semantic search over indexed video |
| `GET /indexes` | GET | List all indexed videos |
| `GET /health` | GET | Health check |

### POST /index
```json
{ "youtube_url": "https://...", "interval_sec": 2.0 }
```

### POST /search
```json
{ "video_id": "dQw4w9WgXcQ", "query": "the beat drop", "top_k": 5 }
```

---

## Project structure

```
vibeseek/
├── backend/
│   ├── frame_extractor.py   # yt-dlp download + OpenCV frame sampling
│   ├── clip_embedder.py     # CLIP image/text encoding + cosine search
│   ├── main.py              # FastAPI server
│   ├── test_pipeline.py     # CLI test script
│   └── requirements.txt
├── frontend/
│   └── src/
│       └── App.jsx          # React UI
└── README.md
```

---

## Week 2 Roadmap

- [ ] **Whisper** — transcribe audio, index subtitle chunks
- [ ] **librosa** — beat/onset detection → beat timestamps as search results
- [ ] **ChromaDB** — replace in-memory dict with persistent vector DB
- [ ] **Multi-modal fusion** — combine visual + audio + text similarity scores

## Week 3+ Ideas

- Scene change detection (PySceneDetect)
- Emotion detection via face embeddings
- Speaker diarisation
- Export clip as short video
