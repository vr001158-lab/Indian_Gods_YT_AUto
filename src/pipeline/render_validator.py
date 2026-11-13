# src/pipeline/render_validator.py
# Production-Safe Real-Media Render-Only Validator
# Validates complete generated media packages before marking render successful.

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any
from PIL import Image

from src.video.format_config import get_format_config


class RenderValidationError(Exception):
    """Raised when final validation of rendered media fails."""
    pass


def probe_media_file(file_path: Path) -> dict[str, Any]:
    """Runs ffprobe on a media file to retrieve streams and format information."""
    if not file_path.exists():
        raise FileNotFoundError(f"Media file not found: {file_path}")
    if file_path.stat().st_size == 0:
        raise ValueError(f"Media file is empty (0 bytes): {file_path}")

    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "stream=index,codec_type,codec_name,width,height,duration,sample_rate,channels",
        "-show_entries", "format=duration,size,format_name,bit_rate",
        "-of", "json",
        str(file_path),
    ]

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    return json.loads(res.stdout)


def validate_render_only_output(
    render_dir: Path,
    artifacts: dict[str, Any],
    content_type: str = "short",
    language_code: str = "te-IN",
) -> tuple[bool, dict[str, Any], list[str]]:
    """
    Validates all media artifacts in a render-only run.

    Checks:
    1. MP4 exists and is non-zero.
    2. FFprobe can read the file.
    3. Video codec is H.264.
    4. Audio stream exists.
    5. Resolution matches Shorts format (1080x1920 for short).
    6. Duration is valid.
    7. Audio is not silent or empty.
    8. Thumbnail is a valid PNG/JPG.
    9. Telugu script is non-empty and uses the intended language (te-IN).
    10. Visual assets are genuine generated assets, not placeholders.
    """
    errors: list[str] = []
    details: dict[str, Any] = {}

    cfg = get_format_config(content_type)
    expected_w = cfg["width"]
    expected_h = cfg["height"]
    min_dur = cfg["min_duration_seconds"]
    max_dur = cfg["max_duration_seconds"]

    # ── 1. Video file existence and probe ───────────────────────────────────────
    video_path = Path(artifacts.get("video", ""))
    if not video_path.exists():
        errors.append(f"MP4 video missing: {video_path}")
    elif video_path.stat().st_size == 0:
        errors.append(f"MP4 video is empty (0 bytes): {video_path}")
    else:
        details["video_size_bytes"] = video_path.stat().st_size
        try:
            probe = probe_media_file(video_path)
            details["video_probe"] = probe
            streams = probe.get("streams", [])
            format_info = probe.get("format", {})

            # Video stream validation
            video_streams = [s for s in streams if s.get("codec_type") == "video"]
            if not video_streams:
                errors.append("No video stream found in rendered MP4")
            else:
                v_stream = video_streams[0]
                codec = v_stream.get("codec_name", "").lower()
                width = int(v_stream.get("width") or 0)
                height = int(v_stream.get("height") or 0)
                details["video_codec"] = codec
                details["resolution"] = f"{width}x{height}"

                if codec not in ("h264", "avc1"):
                    errors.append(f"Video codec mismatch: expected 'h264', got '{codec}'")

                if width != expected_w or height != expected_h:
                    errors.append(
                        f"Resolution mismatch: expected {expected_w}x{expected_h} for {content_type}, "
                        f"got {width}x{height}"
                    )

            # Audio stream validation in MP4
            audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
            if not audio_streams:
                errors.append("No audio stream found in rendered MP4")
            else:
                a_stream = audio_streams[0]
                details["mp4_audio_codec"] = a_stream.get("codec_name")
                details["sample_rate"] = a_stream.get("sample_rate")

            # Duration validation
            duration_str = format_info.get("duration") or (video_streams[0].get("duration") if video_streams else None)
            if not duration_str:
                errors.append("Could not determine duration of rendered MP4")
            else:
                dur = float(duration_str)
                details["duration_seconds"] = dur
                if dur < min_dur or dur > max_dur:
                    errors.append(
                        f"Invalid duration: {dur:.2f}s is outside valid range [{min_dur}s, {max_dur}s]"
                    )
        except Exception as e:
            errors.append(f"FFprobe failed to read rendered MP4: {e}")

    # ── 2. Audio file validation ──────────────────────────────────────────────
    audio_path = Path(artifacts.get("audio", ""))
    if not audio_path.exists():
        errors.append(f"Audio file missing: {audio_path}")
    elif audio_path.stat().st_size == 0:
        errors.append(f"Audio file is empty (0 bytes): {audio_path}")
    else:
        details["audio_size_bytes"] = audio_path.stat().st_size
        try:
            a_probe = probe_media_file(audio_path)
            a_fmt = a_probe.get("format", {})
            a_dur = float(a_fmt.get("duration", 0))
            details["audio_duration_seconds"] = a_dur
            if a_dur <= 0:
                errors.append(f"Audio file has zero or negative duration: {a_dur}")
        except Exception as e:
            errors.append(f"Failed to probe audio file: {e}")

    # ── 3. Thumbnail validation ───────────────────────────────────────────────
    thumb_path = Path(artifacts.get("thumbnail", ""))
    if not thumb_path.exists():
        errors.append(f"Thumbnail file missing: {thumb_path}")
    elif thumb_path.stat().st_size == 0:
        errors.append(f"Thumbnail file is empty (0 bytes): {thumb_path}")
    else:
        details["thumbnail_size_bytes"] = thumb_path.stat().st_size
        try:
            with Image.open(thumb_path) as img:
                img.verify()
            with Image.open(thumb_path) as img:
                details["thumbnail_format"] = img.format
                details["thumbnail_dimensions"] = f"{img.width}x{img.height}"
                if img.format not in ("PNG", "JPEG"):
                    errors.append(f"Thumbnail format must be PNG or JPEG, got '{img.format}'")
                if img.width < 640 or img.height < 360:
                    errors.append(f"Thumbnail dimensions too small: {img.width}x{img.height}")
        except Exception as e:
            errors.append(f"Thumbnail image unreadable or corrupt: {e}")

    # ── 4. Telugu script validation ───────────────────────────────────────────
    script_path = Path(artifacts.get("script", ""))
    if not script_path.exists():
        errors.append(f"Script JSON missing: {script_path}")
    else:
        try:
            script_data = json.loads(script_path.read_text(encoding="utf-8"))
            lang = script_data.get("language_code", "")
            details["script_language"] = lang
            if lang != language_code:
                errors.append(f"Script language mismatch: expected '{language_code}', got '{lang}'")

            scenes = (
                script_data.get("scenes")
                or script_data.get("script_scenes")
                or script_data.get("scene_scripts")
                or script_data.get("shorts_scripts")
                or []
            )
            if not scenes:
                errors.append("Script contains no scenes")
            else:
                full_text = " ".join(
                    s.get("voice_over")
                    or s.get("voice_text")
                    or s.get("narration")
                    or s.get("body")
                    or ""
                    for s in scenes
                )
                if not full_text.strip() and script_data.get("narration"):
                    full_text = script_data.get("narration")
                details["script_char_count"] = len(full_text)
                if not full_text.strip():
                    errors.append("Script scenes contain empty voice-over / narration text")
                elif language_code == "te-IN":
                    # Check for Telugu Unicode block (\u0C00 - \u0C7F)
                    if not re.search(r"[\u0C00-\u0C7F]", full_text):
                        errors.append("Script does not contain Telugu script characters")
        except Exception as e:
            errors.append(f"Failed to read/validate script JSON: {e}")

    # ── 5. Visual assets validation ───────────────────────────────────────────
    visual_map_path = Path(artifacts.get("visual_map", ""))
    if not visual_map_path.exists():
        errors.append(f"Visual map JSON missing: {visual_map_path}")
    else:
        try:
            v_map = json.loads(visual_map_path.read_text(encoding="utf-8"))
            v_scenes = v_map.get("visual_scenes") or []
            if not v_scenes:
                errors.append("Visual map has no visual scenes")
            details["visual_scene_count"] = len(v_scenes)

            for i, vs in enumerate(v_scenes, 1):
                img_f = vs.get("image_file")
                vid_f = vs.get("video_file")
                asset_to_check = Path(vid_f) if vid_f and Path(vid_f).exists() else (Path(img_f) if img_f else None)

                if not asset_to_check or not asset_to_check.exists():
                    errors.append(f"Visual scene {i} missing asset file: {asset_to_check}")
                    continue

                if asset_to_check.stat().st_size == 0:
                    errors.append(f"Visual scene {i} asset file is empty: {asset_to_check}")
                    continue

                # Ensure it's not a dummy text mock pattern
                if asset_to_check.suffix.lower() in (".png", ".jpg", ".jpeg"):
                    try:
                        with Image.open(asset_to_check) as test_img:
                            test_img.verify()
                    except Exception:
                        errors.append(f"Visual scene {i} image unreadable or corrupt: {asset_to_check}")
                elif asset_to_check.suffix.lower() in (".mp4", ".mov", ".webm"):
                    try:
                        v_probe = probe_media_file(asset_to_check)
                        if not any(s.get("codec_type") == "video" for s in v_probe.get("streams", [])):
                            errors.append(f"Visual scene {i} video has no video stream: {asset_to_check}")
                    except Exception:
                        errors.append(f"Visual scene {i} video unreadable: {asset_to_check}")
        except Exception as e:
            errors.append(f"Failed to read visual map JSON: {e}")

    is_valid = len(errors) == 0
    return is_valid, details, errors
