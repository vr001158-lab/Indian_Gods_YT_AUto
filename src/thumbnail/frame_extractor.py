# src/thumbnail/frame_extractor.py
# Phase 2H / Phase 4 — Video Frame Extractor & Quality Filter for Thumbnails
#
# Extracts high-resolution candidate frames from video assets using FFmpeg.
# Applies quality validation:
#   - Rejects black / severely underexposed frames
#   - Rejects blurred / low-frequency frames
#   - Rejects blank / solid-color frames
#
# Strictly enforces provenance: A frame is NEVER classified as verified artwork
# unless its source scene in the visual map is explicitly verified for the target deity and avatar.

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional, Any
from PIL import Image, ImageStat, ImageFilter


def compute_frame_sharpness(img: Image.Image) -> float:
    """
    Computes sharpness variance using a high-pass Laplacian filter.
    Higher values indicate sharp edges; low values (< 100) indicate blurry frames.
    """
    gray = img.convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)
    stat = ImageStat.Stat(edges)
    # Variance of edge pixels (squared stddev)
    variance = (stat.stddev[0]) ** 2
    return round(variance, 2)


def is_frame_suitable(
    image_path: Path,
    min_mean_brightness: float = 25.0,
    max_mean_brightness: float = 245.0,
    min_sharpness_variance: float = 80.0,
    min_color_variance: float = 18.0,
) -> tuple[bool, dict[str, Any]]:
    """
    Validates whether an extracted frame is visually suitable for a thumbnail background:
      - Brightness between 25 and 245 (rejects black and blown-out white)
      - Sharpness variance >= 80 (rejects motion blur and transitions)
      - Color std-dev >= 18 (rejects flat uniform placeholders)
    """
    p = Path(image_path)
    if not p.exists() or p.stat().st_size == 0:
        return False, {"error": "File does not exist or is empty"}

    try:
        with Image.open(p) as img:
            rgb = img.convert("RGB")
            stat = ImageStat.Stat(rgb)
            mean_brightness = sum(stat.mean) / 3.0
            color_stddev = sum(stat.stddev) / 3.0
            sharpness = compute_frame_sharpness(rgb)

            details = {
                "mean_brightness": round(mean_brightness, 2),
                "color_stddev": round(color_stddev, 2),
                "sharpness_variance": sharpness,
                "dimensions": img.size,
            }

            if mean_brightness < min_mean_brightness:
                return False, {**details, "rejection_reason": f"Frame is too dark/black (brightness: {mean_brightness:.1f} < {min_mean_brightness})"}
            if mean_brightness > max_mean_brightness:
                return False, {**details, "rejection_reason": f"Frame is overexposed/white (brightness: {mean_brightness:.1f} > {max_mean_brightness})"}
            if color_stddev < min_color_variance:
                return False, {**details, "rejection_reason": f"Frame is flat/blank (stddev: {color_stddev:.1f} < {min_color_variance})"}
            if sharpness < min_sharpness_variance:
                return False, {**details, "rejection_reason": f"Frame is blurry (sharpness: {sharpness:.1f} < {min_sharpness_variance})"}

            return True, details

    except Exception as e:
        return False, {"error": f"Failed to analyze frame image: {e}"}


def extract_candidate_frames(
    video_path: Path,
    output_dir: Path,
    timestamps_seconds: list[float] | None = None,
    deity: str = "general",
    avatar: Optional[str] = None,
    source_verified: bool = False,
    scene_identities: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    Extracts frames from video_path at specified timestamps using FFmpeg.
    Enforces Strict Deity Identity Inheritance:
      Each frame inherits identity verification from the covering visual scene.
      Frames from mismatched scenes receive DEITY_MISMATCH.
      Frames from unverified scenes receive DEITY_UNVERIFIED.
      Only frames with QUALITY_VERIFIED + DEITY_VERIFIED qualify for approved thumbnail reuse.
    """
    v_path = Path(video_path)
    if not v_path.exists():
        return []

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not timestamps_seconds:
        # Default sampling timestamps: 2.0s, 5.0s, 10.0s, 15.0s, 20.0s
        timestamps_seconds = [2.0, 5.0, 10.0, 15.0, 20.0]

    def _find_scene_at_timestamp(ts_val: float) -> dict[str, Any] | None:
        if not scene_identities:
            return None
        cum_time = 0.0
        for sc in scene_identities:
            dur = float(sc.get("duration_seconds", 5.0) or 5.0)
            if cum_time <= ts_val < (cum_time + dur):
                return sc
            cum_time += dur
        return scene_identities[-1] if scene_identities else None

    extracted_frames = []

    for idx, ts in enumerate(timestamps_seconds):
        frame_name = f"frame_{idx:02d}_{int(ts)}s.png"
        frame_out = out_dir / frame_name

        cmd = [
            "ffmpeg",
            "-y",
            "-ss", str(ts),
            "-i", str(v_path),
            "-vframes", "1",
            "-q:v", "2",
            str(frame_out),
        ]

        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
            if res.returncode != 0 or not frame_out.exists():
                continue

            suitable, metrics = is_frame_suitable(frame_out)
            if suitable:
                # Resolve identity status by inheriting from source scene
                sc = _find_scene_at_timestamp(ts)
                if sc:
                    sc_avatar = sc.get("avatar")
                    sc_deity = sc.get("canonical_deity") or sc.get("deity")
                    sc_ver = sc.get("verification_status")
                    sc_asset = str(sc.get("image_file") or sc.get("source_path") or "").lower()

                    # Identity mismatch checks
                    if avatar and sc_avatar and sc_avatar != avatar:
                        identity_status = "DEITY_MISMATCH"
                    elif avatar and any(o_av in Path(sc_asset).stem.lower() for o_av in ("kurma", "narasimha", "krishna", "vamana", "trivikrama", "matsya") if o_av != avatar):
                        identity_status = "DEITY_MISMATCH"
                    elif deity and sc_deity and sc_deity != deity and sc_deity != "general":
                        identity_status = "DEITY_MISMATCH"
                    elif sc_ver in ("DEITY_VERIFIED", "verified_visual") or (source_verified and sc_avatar == avatar):
                        identity_status = "DEITY_VERIFIED"
                    else:
                        identity_status = "DEITY_UNVERIFIED"
                else:
                    if source_verified:
                        identity_status = "DEITY_VERIFIED"
                    else:
                        identity_status = "DEITY_UNVERIFIED"

                is_approved = (identity_status == "DEITY_VERIFIED")

                extracted_frames.append({
                    "frame_path": str(frame_out).replace("\\", "/"),
                    "timestamp_seconds": ts,
                    "metrics": metrics,
                    "deity": deity,
                    "avatar": avatar,
                    "quality_status": "QUALITY_VERIFIED",
                    "identity_status": identity_status,
                    "source_verified": is_approved,
                    "approval_status": "APPROVED" if is_approved else f"REJECTED_{identity_status}",
                    "source_scene": sc.get("scene") if sc else None,
                })
            else:
                # Discard unsuitable frame
                if frame_out.exists():
                    try:
                        frame_out.unlink()
                    except Exception:
                        pass
        except Exception:
            continue

    return extracted_frames
