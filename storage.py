"""
VibeSeek - Week 3
Storage: uploads extracted frame JPEGs to Cloudinary and returns public CDN URLs,
replacing the Week 2 local "/frames" static mount. Thumbnails are then served from
Cloudinary's global CDN for every user, instead of from this one server's disk —
which also means the backend can run on an ephemeral host (HF Spaces) without
losing images on restart.
"""

import cloudinary                  # the Cloudinary SDK (configuration object)
import cloudinary.uploader         # submodule that exposes upload()
import config                      # our central env-backed settings

# Configure the SDK once at import time using the credentials from config.
cloudinary.config(
    cloud_name=config.CLOUDINARY_CLOUD_NAME,   # which account to upload into
    api_key=config.CLOUDINARY_API_KEY,         # public key for the request
    api_secret=config.CLOUDINARY_API_SECRET,   # secret used to sign the request
    secure=True,                               # always return https:// URLs (not http)
)


def upload_frame(local_path: str, video_id: str, frame_index: int) -> str:
    """
    Uploads one frame JPEG to Cloudinary and returns its public CDN URL.

    The public_id is deterministic ("{folder}/{video_id}/frame_00012"), so
    re-indexing the same video overwrites the old image instead of piling up
    duplicates — and a cached video never needs re-uploading.
    """
    public_id = f"{config.CLOUDINARY_FOLDER}/{video_id}/frame_{frame_index:05d}"  # stable name for this exact frame (zero-padded index)
    result = cloudinary.uploader.upload(   # do the actual HTTP upload to Cloudinary
        local_path,                        # path to the JPEG on local disk
        public_id=public_id,               # store it under our deterministic id
        overwrite=True,                    # replace any existing image with the same id
        resource_type="image",             # tell Cloudinary this is an image (not video/raw)
    )
    return result["secure_url"]            # the https CDN URL the frontend will load


def is_remote_url(path: str) -> bool:
    """True for a Cloudinary (http/https) URL, False for a legacy local path."""
    return bool(path) and path.startswith(("http://", "https://"))   # non-empty AND starts with a web scheme
