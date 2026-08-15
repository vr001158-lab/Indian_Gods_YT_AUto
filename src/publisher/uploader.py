# src/publisher/uploader.py
# Phase 2K — YouTube Publisher: Upload Orchestrator
#
# Wraps the existing youtube_uploader.upload_to_youtube() and adds:
#   - Thumbnail upload (videos.setThumbnail)
#   - Publishing manifest written to data/publishing/
#   - PRIVATE-only enforcement
#   - No credential logging at any point
#
# IMPORTANT: This module NEVER stores, prints, or logs OAuth credentials,
# access tokens, refresh tokens, or client secrets.

from __future__ import annotations

import json
import sys

# Windows-safe: reconfigure stdout/stderr to UTF-8 so that youtube_uploader's
# emoji print() calls don't crash on CP1252 consoles.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# PRIVATE is the ONLY permitted initial privacy status.
# This value is hard-coded and cannot be overridden by callers.
REQUIRED_PRIVACY = "private"


class PublishError(RuntimeError):
    """Raised when a YouTube upload or thumbnail set operation fails."""


# ─────────────────────────────────────────────────────────────────────────────
# Thumbnail upload
# ─────────────────────────────────────────────────────────────────────────────

def upload_thumbnail(creds: Any, video_id: str, thumbnail_file: str | Path) -> bool:
    """
    Set the custom thumbnail for an already-uploaded video.

    Returns True on success, False if thumbnail is unavailable (non-fatal).
    Raises PublishError on API failure.

    Never logs credential values.
    """
    tf = Path(thumbnail_file)
    if not tf.exists() or tf.stat().st_size == 0:
        print(
            f"  [WARNING] Thumbnail file missing or empty: {tf} — skipping.",
            file=sys.stderr,
        )
        return False

    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        youtube  = build("youtube", "v3", credentials=creds)
        mimetype = "image/png" if tf.suffix.lower() == ".png" else "image/jpeg"
        media    = MediaFileUpload(str(tf), mimetype=mimetype)

        youtube.thumbnails().set(
            videoId=video_id,
            media_body=media,
        ).execute()

        print(f"  Thumbnail uploaded: {tf.name}")
        return True

    except Exception as exc:
        raise PublishError(f"Thumbnail upload failed: {exc}") from exc


# ─────────────────────────────────────────────────────────────────────────────
# Main publisher
# ─────────────────────────────────────────────────────────────────────────────

def publish_video(
    creds: Any,
    video_file: str | Path,
    title: str,
    description: str,
    tags: list[str],
    category_id: str,
    thumbnail_file: str | Path | None,
    qa: dict,
    output_dir: str | Path = "data/publishing",
) -> dict:
    """
    Upload the video to YouTube (always PRIVATE), optionally set the thumbnail,
    and write a publishing manifest.

    Parameters
    ----------
    creds:
        Google OAuth credentials object (never logged).
    video_file:
        Path to the validated MP4 file.
    title, description, tags, category_id:
        YouTube metadata.
    thumbnail_file:
        Path to the thumbnail image (PNG/JPEG).  May be None or missing.
    qa:
        The complete Final QA result dict (for provenance in manifest).
    output_dir:
        Where to write publish_YYYYMMDD_HHMMSS.json.

    Returns
    -------
    dict — the publishing manifest (without credential values).
    """
    import youtube_uploader as _yt_uploader

    from .safety import verify_video_with_ffprobe, PublisherSafetyError

    vp = Path(video_file)
    ct = qa.get("content_type", "short")
    try:
        verify_video_with_ffprobe(vp, content_type=ct)
    except PublisherSafetyError as exc:
        raise PublishError(f"Pre-upload ffprobe validation failed for {vp.name}: {exc}") from exc

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # ── Step 1: Upload video ────────────────────────────────────────────────
    # Privacy is ALWAYS "private" — non-negotiable.
    print(f"  Uploading to YouTube [PRIVATE]...")
    print(f"  File:  {vp.name} ({vp.stat().st_size / 1024 / 1024:.2f} MB)")
    print(f"  Title: {title[:80]}")

    try:
        video_id = _yt_uploader.upload_to_youtube(
            creds          = creds,
            video_path     = vp,
            title          = title,
            description    = description,
            tags           = tags,
            privacy_status = REQUIRED_PRIVACY,
            category_id    = category_id,
        )
    except Exception as exc:
        raise PublishError(f"YouTube video upload failed: {exc}") from exc

    if not video_id:
        raise PublishError("YouTube API returned empty video ID")

    youtube_url = f"https://www.youtube.com/watch?v={video_id}"
    print(f"  Video ID : {video_id}")
    print(f"  URL      : {youtube_url}")

    # ── Step 2: Upload thumbnail ────────────────────────────────────────────
    thumbnail_uploaded = False
    thumbnail_error    = ""
    if thumbnail_file:
        try:
            thumbnail_uploaded = upload_thumbnail(creds, video_id, thumbnail_file)
        except PublishError as exc:
            # Thumbnail failure is non-fatal — video is already uploaded
            thumbnail_error = str(exc)
            print(f"  [WARNING] {thumbnail_error}", file=sys.stderr)

    # ── Step 3: Build manifest ──────────────────────────────────────────────
    # IMPORTANT: NO credential values are included in the manifest.
    arts = qa.get("artifacts", {})
    ct = qa.get("content_type", "short")
    manifest = {
        "video_id":           video_id,
        "youtube_url":        youtube_url,
        "selected_topic":     qa.get("selected_topic", ""),
        "privacy_status":     REQUIRED_PRIVACY,
        "upload_timestamp":   ts,
        "thumbnail_uploaded": thumbnail_uploaded,
        "thumbnail_error":    thumbnail_error,
        "success":            True,
        "approval_metadata":  qa.get("approval_metadata", {}),
        # ── Content format metadata ────────────────────────────────────────────
        "content_type":       ct,
        "aspect_ratio":       qa.get("aspect_ratio", ""),
        "resolution":         qa.get("resolution", ""),
        "duration_seconds":   qa.get("video_validation", {}).get("duration_seconds"),
        "source_artifacts": {
            "decision":       arts.get("decision",       ""),
            "content_brief":  arts.get("content_brief",  ""),
            "script":         arts.get("script",         ""),
            "audio":          arts.get("audio",          ""),
            "visual":         arts.get("visual",         ""),
            "video":          arts.get("video",          ""),
            "thumbnail":      arts.get("thumbnail",      ""),
        },
        "video_file":         str(vp),
        "thumbnail_file":     str(thumbnail_file) if thumbnail_file else "",
        "title":              title,
        "tags":               tags,
        "category_id":        category_id,
        # Deliberately excluded: credentials, tokens, client secrets
    }

    # ── Step 4: Save manifest ───────────────────────────────────────────────
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / f"publish_{ts}.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"  Manifest : {manifest_path}")

    # ── Step 5: Append to persistent history file (production runs only) ───
    is_temp_run = "tmp" in str(out_dir).lower() or "temp" in str(out_dir).lower() or "tmp" in str(vp).lower() or "temp" in str(vp).lower()
    if not is_temp_run:
        history_file = Path("data/publishing_history.json")
        history_file.parent.mkdir(parents=True, exist_ok=True)
        history_records = []
        if history_file.exists():
            try:
                history_records = json.loads(history_file.read_text(encoding="utf-8"))
                if not isinstance(history_records, list):
                    history_records = []
            except Exception:
                history_records = []

        history_entry = {
            "youtube_video_id": video_id,
            "topic":            qa.get("selected_topic", ""),
            "title":            title,
            "content_type":     ct,
            "aspect_ratio":     qa.get("aspect_ratio", ""),
            "resolution":       qa.get("resolution", ""),
            "duration_seconds": qa.get("video_validation", {}).get("duration_seconds"),
            "published_at":     ts,
            "video_file_name":  vp.name,
        }
        history_records.append(history_entry)
        history_file.write_text(json.dumps(history_records, indent=2, ensure_ascii=False), encoding="utf-8")

    manifest["_manifest_path"] = str(manifest_path)
    return manifest
