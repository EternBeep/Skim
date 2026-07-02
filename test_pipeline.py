"""
VibeSeek - Week 1
Quick offline test: extracts frames from a local video file and runs CLIP search.
Use this to verify your pipeline works BEFORE wiring up the FastAPI server.

Usage:
    python test_pipeline.py --url "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --query "the chorus"
    python test_pipeline.py --file my_video.mp4 --query "a fight scene"
"""

#this is used to run the test pipeline with out the API
import argparse
import sys
from frame_extractor import extract_frames, extract_frames_from_url
from clip_embedder import CLIPEmbedder


def run_test(video_path: str | None, youtube_url: str | None, query: str,
             interval: float = 3.0, transcribe: bool = False):
    print("\n" + "="*60)
    print("  VibeSeek — Week 1 Pipeline Test")
    print("="*60)

    # Step 1: Get frames (keep the media path so we can also transcribe it)
    media_path = video_path
    if youtube_url:
        print(f"\n[1/3] Downloading & extracting frames from YouTube...")
        media_path, frames, _meta = extract_frames_from_url(youtube_url, interval_sec=interval)
    else:
        print(f"\n[1/3] Extracting frames from local file: {video_path}")
        frames = extract_frames(video_path, interval_sec=interval)

    print(f"      → {len(frames)} frames extracted")

    # Optional: Whisper transcription (Week 2) — exercises the new module offline.
    if transcribe and media_path:
        from audio_transcriber import WhisperTranscriber
        print(f"\n[+]   Transcribing audio with Whisper...")
        chunks = WhisperTranscriber().transcribe(media_path)
        print(f"      → {len(chunks)} transcript chunks")
        for c in chunks[:8]:
            print(f"        [{c.start:6.1f}-{c.end:6.1f}s] {c.text}")
        if len(chunks) > 8:
            print(f"        ... (+{len(chunks) - 8} more)")

    # Step 2: Embed frames with CLIP
    print(f"\n[2/3] Generating CLIP embeddings...")
    embedder = CLIPEmbedder()
    frame_embeddings = embedder.embed_frames(frames)

    # Step 3: Search
    print(f"\n[3/3] Searching for: '{query}'")
    query_vec = embedder.embed_text(query)
    results = embedder.search(query_vec, frame_embeddings, top_k=5)

    print(f"\n{'─'*60}")
    print(f"  Top results for: \"{query}\"")
    print(f"{'─'*60}")
    for i, r in enumerate(results, 1):
        mins = int(r['timestamp']) // 60
        secs = int(r['timestamp']) % 60
        print(f"  #{i}  {mins:02d}:{secs:02d}  (score: {r['score']:.4f})  → {r['image_path']}")

    print(f"{'─'*60}\n")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test VibeSeek pipeline")
    parser.add_argument("--url", type=str, help="YouTube URL")
    parser.add_argument("--file", type=str, help="Local video file path")
    parser.add_argument("--query", type=str, required=True, help="Search query/vibe")
    parser.add_argument("--interval", type=float, default=3.0, help="Frame sampling interval (seconds)")
    parser.add_argument("--transcribe", action="store_true", help="Also run Whisper transcription")
    args = parser.parse_args()

    if not args.url and not args.file:
        print("Error: provide --url or --file")
        sys.exit(1)

    run_test(
        video_path=args.file,
        youtube_url=args.url,
        query=args.query,
        interval=args.interval,
        transcribe=args.transcribe,
    )
