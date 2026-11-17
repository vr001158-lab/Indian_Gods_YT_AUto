# src/assets/fallback_downloader.py
# Automated Missing-Asset Fallback Downloader & Quarantine Service
#
# Non-interactive fallback downloader for missing devotional visual assets.
# Tools used: gallery-dl, yt-dlp, ffprobe, ffmpeg, Pillow.
#
# Quarantine & Approval Rule:
#   All downloaded assets are stored in quarantine directories:
#     - assets/incoming/<canonical_deity>/videos/
#     - assets/incoming/<canonical_deity>/images/
#   Assets remain strictly UNAPPROVED until an explicit entry is registered
#   in the repository asset catalog (DeityAssetIndex / KNOWN_NARRATIVE_METADATA).
#   If unapproved, downstream production pipelines and QA gates fail closed.

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Optional
from PIL import Image

from src.assets.selector import resolve_deity


DEFAULT_INCOMING_DIR = Path("assets/incoming")


def sanitize_filename(name: str) -> str:
    """Sanitizes strings for safe filename usage."""
    clean = re.sub(r"[^\w\-_.]", "_", name.strip())
    return re.sub(r"__+", "_", clean)


def validate_image_file(file_path: Path | str) -> tuple[bool, str, dict[str, Any]]:
    """
    Validates image file using Pillow.
    Ensures the image is not corrupt and can be decoded properly.
    """
    p = Path(file_path)
    if not p.is_file() or p.stat().st_size == 0:
        return False, "File does not exist or is empty", {}

    try:
        with Image.open(p) as img:
            img.verify()
        with Image.open(p) as img:
            w, h = img.size
            fmt = (img.format or "").upper()
            if w <= 0 or h <= 0:
                return False, f"Invalid image dimensions: {w}x{h}", {}
            return True, "Valid image", {
                "width": w,
                "height": h,
                "format": fmt,
                "size_bytes": p.stat().st_size,
            }
    except Exception as e:
        return False, f"Pillow image validation failed: {e}", {}


def validate_video_file(file_path: Path | str) -> tuple[bool, str, dict[str, Any]]:
    """
    Validates video file integrity using ffprobe.
    Ensures container and video stream are valid.
    """
    p = Path(file_path)
    if not p.is_file() or p.stat().st_size == 0:
        return False, "File does not exist or is empty", {}

    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,duration,codec_name",
        "-of", "json",
        str(p),
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if res.returncode != 0:
            return False, f"ffprobe error: {res.stderr.strip()}", {}

        data = json.loads(res.stdout)
        streams = data.get("streams", [])
        if not streams:
            return False, "No video stream detected by ffprobe", {}

        v_stream = streams[0]
        w = int(v_stream.get("width", 0))
        h = int(v_stream.get("height", 0))
        dur = float(v_stream.get("duration", 0.0) or 0.0)
        codec = v_stream.get("codec_name", "unknown")

        if w <= 0 or h <= 0:
            return False, f"Invalid video stream dimensions: {w}x{h}", {}

        return True, "Valid video", {
            "width": w,
            "height": h,
            "duration": dur,
            "codec": codec,
            "size_bytes": p.stat().st_size,
        }
    except Exception as e:
        return False, f"ffprobe execution failed: {e}", {}


class MissingAssetFallbackDownloader:
    """
    Non-interactive fallback downloader for missing devotional visual assets.
    """

    def __init__(self, incoming_root: Path | str = DEFAULT_INCOMING_DIR):
        self.incoming_root = Path(incoming_root)

    def get_quarantine_directory(self, canonical_deity: str, media_type: str = "videos") -> Path:
        """
        Returns the quarantine directory for a given deity and media type:
        assets/incoming/<canonical_deity>/<media_type>/
        """
        m_type = "videos" if media_type.lower().startswith("vid") else "images"
        q_dir = self.incoming_root / canonical_deity.lower() / m_type
        q_dir.mkdir(parents=True, exist_ok=True)
        return q_dir

    def download_asset(
        self,
        deity: str,
        topic_keywords: str,
        media_type: str = "videos",
        url: Optional[str] = None,
        max_duration_seconds: int = 60,
    ) -> dict[str, Any]:
        """
        Non-interactively downloads a missing asset into quarantine.
        Never calls input() or prompts user.

        Query format: "<canonical_deity> <topic_keywords>"
        """
        canonical_deity = resolve_deity(topic_keywords, deity_hint=deity, default=deity.lower())
        m_type = "videos" if media_type.lower().startswith("vid") else "images"
        target_dir = self.get_quarantine_directory(canonical_deity, m_type)

        search_query = f"{canonical_deity} {topic_keywords}".strip()
        safe_tag = sanitize_filename(f"{canonical_deity}_{topic_keywords}")[:40]

        result_record: dict[str, Any] = {
            "deity": canonical_deity,
            "query": search_query,
            "media_type": m_type,
            "status": "NOT_DOWNLOADED",
            "file_path": None,
            "quarantined": True,
            "approval_status": "UNAPPROVED",
            "integrity_status": "UNKNOWN",
            "validation_details": {},
        }

        # If an explicit direct URL is provided, download with yt-dlp or gallery-dl
        if url:
            if m_type == "videos":
                out_tmpl = str(target_dir / f"{safe_tag}_%(id)s.%(ext)s")
                cmd = [
                    "yt-dlp",
                    "--no-input",
                    "--no-interactive",
                    "--max-filesize", "50M",
                    "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                    "-o", out_tmpl,
                    url,
                ]
            else:
                cmd = [
                    "gallery-dl",
                    "--no-input",
                    "--destination", str(target_dir),
                    url,
                ]

            try:
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
                if res.returncode == 0:
                    # Find newly created file in target_dir
                    candidates = sorted(target_dir.glob(f"{safe_tag}*"), key=lambda p: p.stat().st_mtime, reverse=True)
                    if candidates:
                        f_path = candidates[0]
                        result_record["file_path"] = str(f_path).replace("\\", "/")
                        result_record["status"] = "QUARANTINED"
            except Exception as e:
                result_record["error"] = str(e)
                return result_record

        # Validate file if downloaded
        if result_record.get("file_path"):
            p = Path(result_record["file_path"])
            if m_type == "videos":
                valid, msg, details = validate_video_file(p)
            else:
                valid, msg, details = validate_image_file(p)

            result_record["integrity_status"] = "VALID" if valid else "CORRUPT"
            result_record["validation_details"] = details
            result_record["validation_message"] = msg
            if not valid:
                result_record["approval_status"] = "REJECTED_CORRUPT"

        return result_record
