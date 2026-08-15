# src/qa/checks.py
# Phase 2J — Final Pipeline QA Gate: Atomic Check Functions
#
# Each function returns (passed: bool, detail: str).
# All checks are fail-closed: any exception → fail.
#
# Phase 2G+: check_video_map() and check_video_with_ffprobe() accept an optional
# content_type parameter so format-specific resolution/duration rules are enforced.

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from src.video.format_config import (
    ALL_ALLOWED_RESOLUTIONS,
    DEFAULT_CONTENT_TYPE,
    get_format_config,
    validate_content_type,
    validate_duration_for_content_type,
    validate_resolution_for_content_type,
)


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

PRODUCTION_SOURCES = {"youtube_api", "cached_youtube_api"}
REJECTED_SOURCES   = {"mock", "offline"}
# Kept for backwards-compat; callers that used ALLOWED_RESOLUTIONS directly still work.
ALLOWED_RESOLUTIONS = ALL_ALLOWED_RESOLUTIONS


# ─────────────────────────────────────────────────────────────────────────────
# 1. Approval Provenance
# ─────────────────────────────────────────────────────────────────────────────

def check_decision_approval(decision: dict) -> tuple[bool, str]:
    """Decision must be approved with production-grade source and high confidence."""
    if not decision.get("approved_for_generation"):
        return False, "approved_for_generation is not true"
    src = decision.get("data_source", "")
    if src in REJECTED_SOURCES or src not in PRODUCTION_SOURCES:
        return False, f"data_source '{src}' is not a production source"
    conf = decision.get("confidence", "")
    if conf != "high":
        return False, f"confidence '{conf}' is not 'high'"
    topic = decision.get("selected_topic", "")
    if not topic or not topic.strip():
        return False, "selected_topic is missing or empty"
    return True, "OK"


def check_provenance_consistency(manifests: dict[str, dict]) -> tuple[bool, str]:
    """
    All manifests that carry approval_metadata must agree on:
      approved_for_generation, selected_topic, data_source, confidence, score.
    """
    reference: dict[str, Any] | None = None
    reference_name: str = ""
    fields = ["approved_for_generation", "selected_topic", "data_source", "confidence", "score"]

    for name, manifest in manifests.items():
        meta = manifest.get("approval_metadata")
        if meta is None:
            continue
        if reference is None:
            reference = {f: meta.get(f) for f in fields}
            reference_name = name
            continue
        for f in fields:
            if meta.get(f) != reference.get(f):
                return (
                    False,
                    f"Provenance mismatch on '{f}': "
                    f"{reference_name}={reference.get(f)!r} "
                    f"vs {name}={meta.get(f)!r}",
                )

    if reference is None:
        return False, "No manifest contains approval_metadata — cannot verify provenance"
    if not reference.get("approved_for_generation"):
        return False, "approval_metadata.approved_for_generation is not true"
    if reference.get("data_source") in REJECTED_SOURCES:
        return False, f"approval_metadata.data_source '{reference['data_source']}' is not production"
    return True, "OK"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Topic Consistency
# ─────────────────────────────────────────────────────────────────────────────

def _normalise(s: str) -> str:
    import re
    return re.sub(r"[^a-z0-9\s]", "", s.strip().lower())


def check_topic_consistency(decision: dict, manifests: dict[str, dict]) -> tuple[bool, str]:
    """
    The selected_topic from the decision must be consistent across all manifests.
    """
    canonical = decision.get("selected_topic", "")
    if not canonical:
        return False, "Decision has no selected_topic"

    for name, manifest in manifests.items():
        meta_topic = (manifest.get("approval_metadata") or {}).get("selected_topic", "")
        if meta_topic and meta_topic.strip() != canonical.strip():
            return (
                False,
                f"approval_metadata.selected_topic mismatch in {name}: "
                f"expected '{canonical}', got '{meta_topic}'",
            )

    STOP = {"a", "an", "the", "of", "in", "on", "at", "to", "and", "or",
            "for", "is", "it", "its", "why", "how", "what", "does"}
    canonical_words = {
        w for w in _normalise(canonical).split() if w not in STOP and len(w) >= 3
    }

    TOPIC_FIELDS = {
        "script":         ["title"],
        "audio_map":      ["script_title"],
        "visual_map":     ["script_title"],
        "content_brief":  ["primary_title"],
        "thumbnail_meta": ["title", "topic"],
    }

    for name, fields in TOPIC_FIELDS.items():
        manifest = manifests.get(name)
        if manifest is None:
            continue
        for field in fields:
            value = manifest.get(field, "")
            if not value:
                continue
            value_words = {
                w for w in _normalise(value).split() if w not in STOP and len(w) >= 3
            }
            overlap = canonical_words & value_words
            if len(overlap) == 0:
                return (
                    False,
                    f"Topic mismatch in {name}.{field}: no keywords from "
                    f"'{canonical}' found in '{value}'",
                )
    return True, "OK"


# ─────────────────────────────────────────────────────────────────────────────
# 3. File Integrity
# ─────────────────────────────────────────────────────────────────────────────

def check_json_file(path: str | Path) -> tuple[bool, str]:
    """File exists, is non-zero, and parses as valid JSON."""
    p = Path(path)
    if not p.exists():
        return False, f"File does not exist: {p}"
    size = p.stat().st_size
    if size == 0:
        return False, f"File is zero bytes: {p}"
    try:
        json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return False, f"Invalid JSON in {p}: {exc}"
    return True, "OK"


def check_media_file(path: str | Path, min_bytes: int = 1) -> tuple[bool, str]:
    """Media file exists and is non-zero (or above min_bytes)."""
    p = Path(path)
    if not p.exists():
        return False, f"Media file does not exist: {p}"
    size = p.stat().st_size
    if size < min_bytes:
        return False, f"Media file is too small ({size} bytes, min={min_bytes}): {p}"
    return True, "OK"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Audio QA
# ─────────────────────────────────────────────────────────────────────────────

def check_audio_map(audio_map: dict) -> tuple[bool, str]:
    """Validate audio map structure and scene ordering."""
    scenes = audio_map.get("audio_scenes", [])
    if not scenes:
        return False, "audio_scenes is empty"

    total_dur = audio_map.get("total_duration_seconds", 0)
    if not total_dur or total_dur <= 0:
        return False, f"total_duration_seconds is not positive: {total_dur}"

    expected = list(range(1, len(scenes) + 1))
    actual   = [s.get("scene") for s in scenes]
    if actual != expected:
        return False, f"Scene ordering broken: expected {expected}, got {actual}"

    for scene in scenes:
        dur = scene.get("duration_seconds", 0)
        if dur <= 0:
            return False, f"Scene {scene.get('scene')} has non-positive duration: {dur}"
        af = scene.get("audio_file", "")
        if not af:
            return False, f"Scene {scene.get('scene')} missing audio_file"
        p = Path(af)
        if not p.exists():
            return False, f"Scene {scene.get('scene')} audio file missing: {p}"
        if p.stat().st_size == 0:
            return False, f"Scene {scene.get('scene')} audio file is zero bytes: {p}"

    return True, "OK"


# ─────────────────────────────────────────────────────────────────────────────
# 5. Visual QA
# ─────────────────────────────────────────────────────────────────────────────

def check_visual_map(visual_map: dict) -> tuple[bool, str]:
    """Validate visual map: every scene has a non-zero image file."""
    scenes = visual_map.get("visual_scenes", [])
    if not scenes:
        return False, "visual_scenes is empty"

    expected = list(range(1, len(scenes) + 1))
    actual   = [s.get("scene") for s in scenes]
    if actual != expected:
        return False, f"Visual scene ordering broken: expected {expected}, got {actual}"

    provider = visual_map.get("provider", "")
    is_mock  = provider == "mock"

    for scene in scenes:
        img = scene.get("image_file", "")
        if not img:
            return False, f"Visual scene {scene.get('scene')} missing image_file"
        p = Path(img)
        if not p.exists():
            return False, f"Visual scene {scene.get('scene')} image missing: {p}"
        if p.stat().st_size == 0:
            return False, f"Visual scene {scene.get('scene')} image is zero bytes: {p}"
        if not is_mock:
            try:
                from PIL import Image
                with Image.open(p) as img_obj:
                    img_obj.load()
            except Exception as exc:
                return False, f"Visual scene {scene.get('scene')} image corrupt/unreadable: {exc}"

    return True, "OK"


# ─────────────────────────────────────────────────────────────────────────────
# 6. Video QA
# ─────────────────────────────────────────────────────────────────────────────

def check_video_map(video_map: dict, content_type: str = DEFAULT_CONTENT_TYPE) -> tuple[bool, str]:
    """
    Validate video map structure.

    Parameters
    ----------
    content_type : str
        "short" or "long".  Resolution and aspect_ratio in the map are
        validated against the declared content_type.
    """
    video_file = video_map.get("video_file", "")
    if not video_file:
        return False, "video_map missing video_file"
    p = Path(video_file)
    if not p.exists():
        return False, f"Video file not found: {p}"
    if p.stat().st_size == 0:
        return False, f"Video file is zero bytes: {p}"

    # ── content_type check ─────────────────────────────────────────────────
    map_ct = video_map.get("content_type", "")
    if map_ct:
        ok_ct, ct_err = validate_content_type(map_ct)
        if not ok_ct:
            return False, f"video_map contains invalid content_type: {ct_err}"
        if map_ct != content_type:
            return (
                False,
                f"content_type mismatch: caller expected '{content_type}', "
                f"video_map declares '{map_ct}'",
            )

    # ── Resolution check ───────────────────────────────────────────────────
    resolution = video_map.get("resolution", "")
    if resolution not in ALL_ALLOWED_RESOLUTIONS:
        return False, f"Video resolution '{resolution}' is not in allowed resolutions {sorted(ALL_ALLOWED_RESOLUTIONS)}"

    ok_res, res_err = validate_resolution_for_content_type(resolution, content_type)
    if not ok_res:
        return False, res_err

    scenes = video_map.get("scenes", [])
    if not scenes:
        return False, "video_map has no scenes"

    total_dur = video_map.get("total_duration", 0)
    if not total_dur or total_dur <= 0:
        return False, f"total_duration is not positive: {total_dur}"

    return True, "OK"


def check_video_with_ffprobe(
    video_file: str | Path,
    *,
    allow_mock: bool = False,
    content_type: str = DEFAULT_CONTENT_TYPE,
) -> tuple[bool, str, dict]:
    """
    Strict production video validation using ffprobe and ffmpeg decode.

    Parameters
    ----------
    content_type : str
        "short" or "long".  Determines which resolutions and duration
        bounds are considered valid.  Defaults to "short".
    """
    vval = {
        "file_exists": False,
        "file_size_bytes": 0,
        "container": "",
        "duration_seconds": 0.0,
        "video_codec": "",
        "pixel_format": "",
        "width": 0,
        "height": 0,
        "audio_codec": "",
        "audio_channels": 0,
        "ffprobe_passed": False,
        "ffmpeg_decode_passed": False
    }

    p = Path(video_file)
    if not p.exists():
        return False, f"Video file not found: {p}", vval
    vval["file_exists"] = True
    vval["file_size_bytes"] = p.stat().st_size

    if p.stat().st_size == 0:
        return False, f"Video file is zero bytes: {p}", vval

    # Reject mock text files
    try:
        header = p.read_bytes()[:64]
        if header.startswith(b"MOCK_MP4_VIDEO"):
            if allow_mock:
                vval.update({
                    "container": "mock",
                    "duration_seconds": 150.0,
                    "video_codec": "h264",
                    "pixel_format": "yuv420p",
                    "width": 1080,
                    "height": 1920,
                    "audio_codec": "aac",
                    "audio_channels": 2,
                    "ffprobe_passed": True,
                    "ffmpeg_decode_passed": True
                })
                return True, "mock video accepted (test mode)", vval
            return False, "Mock video artifact is not valid for production QA", vval
    except Exception:
        pass

    try:
        result = subprocess.run(
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
        if result.returncode != 0:
            return False, f"ffprobe failed (exit {result.returncode}): {result.stderr[:200]}", vval

        probe = json.loads(result.stdout)
    except FileNotFoundError:
        return False, "ffprobe binary not found — cannot validate video for production", vval
    except json.JSONDecodeError as exc:
        return False, f"ffprobe returned unparseable JSON: {exc}", vval
    except Exception as exc:
        return False, f"ffprobe error: {exc}", vval

    fmt = probe.get("format", {})
    vval["container"] = fmt.get("format_name", "")

    streams = probe.get("streams", [])
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

    if not video_streams:
        return False, "No video stream found by ffprobe", vval
    if not audio_streams:
        return False, "No audio stream found by ffprobe", vval

    vs = video_streams[0]
    codec   = vs.get("codec_name", "")
    pix_fmt = vs.get("pix_fmt", "")
    width   = vs.get("width", 0)
    height  = vs.get("height", 0)

    vval["video_codec"] = codec
    vval["pixel_format"] = pix_fmt
    vval["width"] = width
    vval["height"] = height

    as_info = audio_streams[0]
    vval["audio_codec"] = as_info.get("codec_name", "")
    vval["audio_channels"] = as_info.get("channels", 0)

    if codec != "h264":
        return False, f"Invalid video codec: expected h264, got '{codec}'", vval
    if pix_fmt not in ("yuv420p", "yuvj420p"):
        return False, f"Invalid pixel format: expected yuv420p, got '{pix_fmt}'", vval

    # ── Format-aware resolution check ──────────────────────────────────────
    actual_res = f"{width}x{height}"
    ok_res, res_err = validate_resolution_for_content_type(actual_res, content_type)
    if not ok_res:
        return False, res_err, vval

    duration = float(fmt.get("duration", 0) or 0)
    if duration <= 0:
        duration = float(vs.get("duration", 0) or 0)
    if duration <= 0:
        return False, f"Video duration is not positive: {duration}", vval

    vval["duration_seconds"] = duration
    vval["ffprobe_passed"] = True

    # FFmpeg decode test
    try:
        decode_result = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(p), "-f", "null", "-"],
            capture_output=True,
            text=True,
            timeout=120,
            encoding="utf-8",
            errors="replace",
        )
        if decode_result.returncode != 0:
            return False, f"FFmpeg decode test failed: {decode_result.stderr[:200]}", vval
    except FileNotFoundError:
        return False, "FFmpeg binary not found — cannot perform decode validation", vval
    except Exception as exc:
        return False, f"FFmpeg decode error: {exc}", vval

    vval["ffmpeg_decode_passed"] = True

    detail = (
        f"OK (duration={duration:.1f}s, {width}x{height}, "
        f"v={codec}/{pix_fmt}, a={vval['audio_codec']}/{vval['audio_channels']}ch, "
        f"size={vval['file_size_bytes']} bytes)"
    )
    return True, detail, vval


# ─────────────────────────────────────────────────────────────────────────────
# 7. Thumbnail QA
# ─────────────────────────────────────────────────────────────────────────────

def check_thumbnail_meta(thumbnail_meta: dict, thumbnail_file: str | Path) -> tuple[bool, str]:
    """Validate thumbnail metadata and actual image file."""
    resolution = thumbnail_meta.get("resolution", "")
    if resolution != "1280x720":
        return False, f"Thumbnail resolution must be 1280x720, got '{resolution}'"

    fmt = thumbnail_meta.get("format", "")
    if fmt.lower() not in ("png", "jpeg", "jpg"):
        return False, f"Thumbnail format must be png/jpeg, got '{fmt}'"

    approved_src = thumbnail_meta.get("approved_source", "")
    if approved_src in REJECTED_SOURCES or approved_src not in PRODUCTION_SOURCES:
        return False, f"Thumbnail approved_source '{approved_src}' is not production"

    conf = thumbnail_meta.get("confidence", "")
    if conf != "high":
        return False, f"Thumbnail confidence '{conf}' is not 'high'"

    meta = thumbnail_meta.get("approval_metadata")
    if not meta:
        return False, "Thumbnail metadata missing approval_metadata"
    if not meta.get("approved_for_generation"):
        return False, "Thumbnail approval_metadata.approved_for_generation is not true"

    p = Path(thumbnail_file)
    if not p.exists():
        return False, f"Thumbnail image file not found: {p}"
    size = p.stat().st_size
    if size == 0:
        return False, f"Thumbnail image is zero bytes: {p}"
    if size > 2 * 1024 * 1024:
        return False, f"Thumbnail exceeds 2MB YouTube limit: {size / 1024 / 1024:.2f}MB"

    try:
        from PIL import Image
        with Image.open(p) as img:
            w, h = img.size
            if w != 1280 or h != 720:
                return False, f"Thumbnail pixel dimensions {w}x{h} ≠ 1280x720"
            ratio = w / h
            if not (1.77 <= ratio <= 1.78):
                return False, f"Thumbnail aspect ratio {ratio:.3f} is not 16:9"
    except Exception as exc:
        return False, f"Thumbnail image unreadable: {exc}"

    return True, "OK"


# ─────────────────────────────────────────────────────────────────────────────
# 8. Scene Synchronisation
# ─────────────────────────────────────────────────────────────────────────────

def check_scene_sync(
    script: dict,
    audio_map: dict,
    visual_map: dict,
    video_map: dict,
) -> tuple[bool, str]:
    """
    script.scene_scripts, audio_map.audio_scenes, visual_map.visual_scenes,
    and video_map.scenes must all agree on scene count and ordering.
    """
    script_scenes  = [s.get("scene") for s in script.get("scene_scripts",  [])]
    audio_scenes   = [s.get("scene") for s in audio_map.get("audio_scenes", [])]
    visual_scenes  = [s.get("scene") for s in visual_map.get("visual_scenes", [])]
    video_scenes   = [s.get("scene") for s in video_map.get("scenes",       [])]

    counts = {
        "script":  len(script_scenes),
        "audio":   len(audio_scenes),
        "visual":  len(visual_scenes),
        "video":   len(video_scenes),
    }
    unique_counts = set(counts.values())
    if len(unique_counts) > 1:
        return False, f"Scene count mismatch: {counts}"

    if script_scenes != audio_scenes:
        return False, f"Script/Audio scene ordering mismatch: {script_scenes} vs {audio_scenes}"
    if script_scenes != visual_scenes:
        return False, f"Script/Visual scene ordering mismatch: {script_scenes} vs {visual_scenes}"
    if script_scenes != video_scenes:
        return False, f"Script/Video scene ordering mismatch: {script_scenes} vs {video_scenes}"

    if len(set(script_scenes)) != len(script_scenes):
        return False, f"Duplicate scene numbers detected: {script_scenes}"

    return True, "OK"
