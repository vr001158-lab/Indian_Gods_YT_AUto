# src/assets/validator.py
# Central Asset Validation Layer for Images and Videos

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

SUPPORTED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
SUPPORTED_VIDEO_EXTS = {".mp4", ".mov", ".webm"}


class AssetValidationError(ValueError):
    """Raised when an asset fails validation (corrupted, unreadable, zero-byte)."""


def validate_image_asset(path: str | Path) -> dict[str, Any]:
    """
    Validate an image asset.
    Checks:
    - File exists
    - File size > 0
    - Supported extension (.png, .jpg, .jpeg, .webp)
    - Readable by Pillow (Image.open)
    - Valid dimensions (width > 0, height > 0)

    Returns asset metadata dict:
      {
        "asset_id": ...,
        "type": "image",
        "path": ...,
        "width": int,
        "height": int,
        "format": str,
        "aspect_ratio": float,
        "file_size_bytes": int,
        "valid": True
      }
    """
    p = Path(path)
    if not p.exists():
        raise AssetValidationError(f"Image asset does not exist: {p}")
    
    size = p.stat().st_size
    if size == 0:
        raise AssetValidationError(f"Image asset is zero bytes: {p}")

    ext = p.suffix.lower()
    if ext not in SUPPORTED_IMAGE_EXTS:
        raise AssetValidationError(f"Unsupported image extension '{ext}' for file {p.name}")

    try:
        from PIL import Image
        with Image.open(p) as img:
            w, h = img.size
            fmt = (img.format or ext.lstrip(".")).lower()
            img.verify()
    except Exception as exc:
        raise AssetValidationError(f"Corrupted image asset {p.name}: {exc}") from exc

    if w <= 0 or h <= 0:
        raise AssetValidationError(f"Invalid image dimensions {w}x{h} for {p.name}")

    aspect_ratio = round(w / h, 4)

    return {
        "asset_id": p.stem,
        "type": "image",
        "path": str(p).replace("\\", "/"),
        "width": w,
        "height": h,
        "format": fmt,
        "aspect_ratio": aspect_ratio,
        "file_size_bytes": size,
        "valid": True,
    }


def validate_video_asset(path: str | Path) -> dict[str, Any]:
    """
    Validate a video asset using ffprobe.
    Checks:
    - File exists
    - File size > 0
    - Supported extension (.mp4, .mov, .webm)
    - Not a mock text stub
    - ffprobe succeeds (exit code 0)
    - Valid video stream, codec, width, height, duration > 0, FPS

    Returns asset metadata dict:
      {
        "asset_id": ...,
        "type": "video",
        "path": ...,
        "width": int,
        "height": int,
        "duration": float,
        "fps": float,
        "video_codec": str,
        "container": str,
        "file_size_bytes": int,
        "valid": True
      }
    """
    p = Path(path)
    if not p.exists():
        raise AssetValidationError(f"Video asset does not exist: {p}")

    size = p.stat().st_size
    if size == 0:
        raise AssetValidationError(f"Video asset is zero bytes: {p}")

    ext = p.suffix.lower()
    if ext not in SUPPORTED_VIDEO_EXTS:
        raise AssetValidationError(f"Unsupported video extension '{ext}' for file {p.name}")

    # Check for mock text stubs
    try:
        header = p.read_bytes()[:64]
        if header.startswith(b"MOCK_MP4_VIDEO") or header.startswith(b"MOCK_DRY_RUN_IMAGE"):
            raise AssetValidationError(f"Mock video text stub is not a valid video asset: {p.name}")
    except AssetValidationError:
        raise
    except Exception:
        pass

    try:
        res = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_streams",
                "-show_format",
                "-of", "json",
                str(p),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            encoding="utf-8",
            errors="replace",
        )
        if res.returncode != 0:
            raise AssetValidationError(
                f"ffprobe validation failed for {p.name} (exit {res.returncode}): {res.stderr[:200].strip()}"
            )
        probe = json.loads(res.stdout)
    except AssetValidationError:
        raise
    except FileNotFoundError:
        raise AssetValidationError("ffprobe binary not found — cannot validate video asset")
    except Exception as exc:
        raise AssetValidationError(f"ffprobe decode error for {p.name}: {exc}") from exc

    fmt = probe.get("format", {})
    container = fmt.get("format_name", "")

    streams = probe.get("streams", [])
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    if not video_streams:
        raise AssetValidationError(f"No video stream detected in {p.name}")

    vs = video_streams[0]
    codec = vs.get("codec_name", "")
    w = vs.get("width", 0)
    h = vs.get("height", 0)

    if w <= 0 or h <= 0:
        raise AssetValidationError(f"Invalid video resolution {w}x{h} in {p.name}")

    # Resolve duration
    dur_str = fmt.get("duration") or vs.get("duration") or "0"
    try:
        dur = float(dur_str)
    except ValueError:
        dur = 0.0

    if dur <= 0:
        raise AssetValidationError(f"Invalid video duration {dur}s in {p.name}")

    # Resolve FPS
    r_fps = vs.get("r_frame_rate", "30/1")
    try:
        num, den = map(float, r_fps.split("/"))
        fps = round(num / den, 2) if den else 30.0
    except Exception:
        fps = 30.0

    return {
        "asset_id": p.stem,
        "type": "video",
        "path": str(p).replace("\\", "/"),
        "width": w,
        "height": h,
        "duration": round(dur, 2),
        "fps": fps,
        "video_codec": codec,
        "container": container,
        "file_size_bytes": size,
        "valid": True,
    }
