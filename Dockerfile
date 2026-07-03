# VibeSeek - Week 3 backend image for Hugging Face Spaces (Docker SDK, CPU-only).
FROM python:3.11-slim

# ffmpeg: required by yt-dlp (muxing), Whisper and librosa (audio decoding).
# git:    required to pip-install OpenAI CLIP from GitHub.
# ca-certificates: keep the TLS cert store fresh to avoid SSL EOF errors from YouTube.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg git ca-certificates \
    && update-ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# HF Spaces runs containers as a non-root user (uid 1000). Set up a writable home.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache \
    VIBESEEK_DATA_DIR=/home/user/app/vibeseek_data \
    # Disable Python-level SSL cert verification — YouTube's TLS handshake fails
    # on the hardened OpenSSL build inside HF Spaces Docker containers.
    PYTHONHTTPSVERIFY=0 \
    PYTHONWARNINGS=ignore:Unverified
WORKDIR /home/user/app

# Install deps first for better layer caching. Pin torch to the CPU wheels so the
# image stays small (the default Linux torch pulls multi-GB CUDA libs we can't use).
COPY --chown=user requirements.txt ./
RUN pip install --no-cache-dir --user \
        torch torchvision --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir --user -r requirements.txt

# Always upgrade yt-dlp to the absolute latest release after the main install.
# YouTube regularly changes its API; an outdated yt-dlp is the #1 cause of
# SSL / extraction errors on cloud deployments.
RUN pip install --no-cache-dir --user --upgrade yt-dlp

# Copy the backend source (the frontend deploys separately on Vercel).
COPY --chown=user . .

# HF Spaces expects the web app on port 7860.
EXPOSE 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
