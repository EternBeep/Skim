"""
VibeSeek - Week 1
Frame Extractor: Downloads YouTube video and extracts frames at regular intervals.
"""

import os
import re
import ssl
import cv2
import yt_dlp
from pathlib import Path
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Module-level SSL patch — must run before any network call.
# HuggingFace Spaces uses a hardened OpenSSL build that rejects YouTube's TLS
# handshake at the Python socket layer, before yt-dlp options even apply.
# Disabling cert verification here fixes both get_video_id and download_video.
# ---------------------------------------------------------------------------
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except AttributeError:
    pass  # not available on all builds; safe to skip

# Regex patterns covering every common YouTube URL format.
# Used by get_video_id() to extract the 11-char video ID without any network call.
_YT_ID_RE = re.compile(
    r"(?:youtube\.com/(?:watch\?(?:.*&)?v=|embed/|v/|shorts/)"
    r"|youtu\.be/)"
    r"([a-zA-Z0-9_-]{11})"
)

#datclass is use to creat a cleaner function style instead of the original one
# dataclasses.dataclass() is a decorator that automatically generates the __init__ and __repr__ methods
@dataclass
class Frame:
    timestamp: float       # seconds
    frame_index: int
    image_path: str        # path to saved .jpg

# A trimmed-down view of yt-dlp's info dict — just the fields the summarizer
# needs to describe ANY video (music, anime, movies) when there's no speech.
def _meta_from_info(info: dict) -> dict:
    return {
        "title": info.get("title") or "",
        "description": info.get("description") or "",
        "uploader": info.get("uploader") or info.get("channel") or "",
        "duration": info.get("duration") or 0,          # seconds
        "tags": info.get("tags") or [],
        "categories": info.get("categories") or [],
    }


# This function downloads the video from the given YouTube URL using yt-dlp
def download_video(youtube_url: str, output_dir: str = "downloads") -> tuple[str, dict]:
    """
    Downloads a YouTube video using yt-dlp.
    Returns (local file path, metadata dict) — the metadata lets us summarise even
    videos with no speech (music/anime/movies), straight from yt-dlp's info.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)#this is used to create my downloaded file folder

    ydl_opts = {
        "format": "bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4]/best",#this is used to select the best quality of the video and audio
        "outtmpl": f"{output_dir}/%(id)s.%(ext)s",#this is used to save the video in the downloaded file folder
        "quiet": True,#keeps output clean
        "no_warnings": True,#keeps output clean
        # SSL / network fixes for HuggingFace Spaces and restricted environments.
        # HF containers run on OpenSSL builds that reject certain TLS handshakes
        # from YouTube; these three options work around that reliably.
        "nocheckcertificate": True,        # skip TLS cert verification (safe in a closed server env)
        "legacy_server_connect": True,     # allow OpenSSL legacy renegotiation (fixes EOF error)
        "source_address": "0.0.0.0",      # force IPv4 binding — HF Spaces IPv6 routing is unreliable
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=True)#This extracts the information of the video and downloads it
        video_id = info["id"]#get id of the video
        ext = info.get("ext", "mp4")#get to know its extension
        video_path = f"{output_dir}/{video_id}.{ext}"#use to build file apth like downloads /abc.mp4 and combining the downloaded files
        meta = _meta_from_info(info)#keep title/description/tags/etc for the summary

    print(f"[FrameExtractor] Downloaded: {video_path}")
    return video_path, meta


def extract_frames(
    video_path: str,
    output_dir: str = "frames",
    interval_sec: float = 2.0,
    max_frames: int = 500,
) -> list[Frame]:
    """
    Extracts one frame every `interval_sec` seconds from the video.
    Saves frames as JPEGs. Returns a list of Frame objects with timestamps.

    Args:
        video_path:    Path to the local video file.
        output_dir:    Directory to save extracted frames.
        interval_sec:  How often to sample (default: every 2 seconds).
        max_frames:    Safety cap to avoid processing huge videos.

    Returns:
        List[Frame] sorted by timestamp.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)#this is used to create my frames file folder 

    cap = cv2.VideoCapture(video_path)#this is used to open the video
    if not cap.isOpened():#used to check if the video is opened
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)#this is used to get the frames per second of the video
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))#this is used to get the total number of frames in the video
    duration_sec = total_frames / fps if fps > 0 else 0#this is used to get the duration of the video in seconds

    print(f"[FrameExtractor] FPS={fps:.1f}, Duration={duration_sec:.1f}s, Total frames={total_frames}")#this is used to print the frames per second, duration and total number of frames of the video

    frame_step = max(1, int(fps * interval_sec))#this is used to get the number of frames to skip between each frame extraction i.e every 2 sec capture one frame
    frames: list[Frame] = []#used to store the extracted frames
    frame_index = 0#used to store the frame index
    saved_count = 0#used to store the number of frames saved

    while saved_count < max_frames:#used to extract frames until the number of saved frames is equal to the maximum number of frames
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)#used to set the current frame index
        ret, frame = cap.read()#this is used to read the frame

        if not ret:#used to check if the frame is read successfully
            break

        timestamp = frame_index / fps#this is used to calculate the timestamp of the frame
        img_filename = f"frame_{saved_count:05d}_{timestamp:.2f}s.jpg"#used to create the filename of the frame like frame_00000_0.00s.jpg etc
        img_path = os.path.join(output_dir, img_filename)#used to create the path of the frame like frame/frame_00000_0.00s.jpg etc

        cv2.imwrite(img_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 85])#this is used to save the frame as a jpg file 

        frames.append(Frame( #used to store the extracted frames 
            timestamp=timestamp,#used to store the timestamp of the frame
            frame_index=frame_index,#used to store the frame index
            image_path=img_path,#used to store the path of the frame
        ))

        frame_index += frame_step#this is used to get the number of frames to skip between each frame extraction i.e every 2 sec capture one frame
        saved_count += 1#this is used to increment the number of frames saved

    cap.release()#this is used to release the video capture object
    print(f"[FrameExtractor] Extracted {len(frames)} frames → {output_dir}/")#this is used to print the number of frames extracted and the path of the folder where the frames are saved
    return frames#this is used to return the list of frames


def get_video_id(youtube_url: str) -> str:
    """
    Extracts the YouTube video ID from a URL.

    Fast path: regex parse — covers every standard YouTube URL format with
    zero network calls and zero SSL exposure. This is what runs for the cache
    check (goal #3) on every /index request.

    Slow path: yt-dlp metadata fetch — only triggered for unusual/shortened
    URLs that don't match the regex (e.g. custom vanity URLs, playlists).
    """
    # Fast path — no network, no SSL.
    match = _YT_ID_RE.search(youtube_url)
    if match:
        return match.group(1)

    # Slow path — yt-dlp lightweight fetch (download=False).
    print(f"[FrameExtractor] URL did not match regex, falling back to yt-dlp: {youtube_url}")
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,        # metadata only — no bytes pulled
        "nocheckcertificate": True,   # SSL handled at Python level above, belt+suspenders
        "legacy_server_connect": True,
        "source_address": "0.0.0.0", # force IPv4 — HF Spaces IPv6 is unreliable
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=False)
    return info["id"]


def extract_frames_from_url(
    youtube_url: str,
    interval_sec: float = 2.0,
    base_dir: str = "vibeseek_data",
) -> tuple[str, list[Frame], dict]:
    """
    Convenience wrapper: download + extract in one call.
    Returns (video_path, frames_list, metadata) — metadata feeds the summary.
    """
    video_path, meta = download_video(youtube_url, output_dir=f"{base_dir}/downloads")#download + grab metadata
    video_id = Path(video_path).stem#this is used to get the id of the video
    frames_dir = f"{base_dir}/frames/{video_id}"#this is used to create the path of the folder where the frames are saved

    frames = extract_frames(
        video_path=video_path,#this is used to pass the path of the video to the extract_frames function
        output_dir=frames_dir,#this is used to pass the path of the folder where the frames are saved to the extract_frames function
        interval_sec=interval_sec,#this is used to pass the interval of the frames to the extract_frames function
    )#this is used to extract the frames from the video
    return video_path, frames, meta#video path + frames + metadata for the summary
