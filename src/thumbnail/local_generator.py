# src/thumbnail/local_generator.py
# Phase 2H / Phase 4 — Simple, Robust Local Thumbnail Generator
#
# Generates production 1280x720 devotional YouTube thumbnails exclusively from
# local repository assets:
#   1. Resolves deity from decision / script (or weekday automation default).
#   2. Searches matching deity folder in assets/gods/, assets/gods_landscape_long_video/, assets/gods_processed/.
#   3. Prioritizes approved local images (.png, .jpg, .jpeg, .webp).
#   4. If only videos are available or video is passed, extracts a representative frame using FFmpeg.
#      CRITICAL SAFEGUARD: Never passes .mp4, .mov, .mkv, .webm directly to Pillow Image.open.
#   5. Applies Telugu typography (Noto Sans Telugu), sacred gold title, subtitle,
#      channel branding badge ('దైవ దర్శనం'), devotional gold border, and YouTube safe margins.
#   6. Zero external AI dependencies (no Pollinations/Flux).
#   7. Emits 1280x720 PNG and schema-compliant thumbnail metadata JSON.

from __future__ import annotations

import json
import os
import time
import subprocess
from pathlib import Path
from typing import Any, Optional
from PIL import Image

from src.thumbnail.generator import ThumbnailGenerator
from src.thumbnail.asset_index import DeityAssetIndex, resolve_deity_and_avatar
from src.thumbnail.asset_selector import (
    ThumbnailAssetSelector,
    SelectedThumbnailAsset,
    NoSuitableThumbnailAssetError,
)
from src.thumbnail.composer import compose_reused_thumbnail
from src.thumbnail.analyzer import analyze_thumbnail_file
from src.thumbnail.schemas import validate_metadata_output
from src.decision.weekday_deity import select_weekday_deity


VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def extract_video_frame_safely(
    video_path: Path | str,
    output_path: Path | str,
    timestamp_str: str = "00:00:02",
) -> Path:
    """
    Extracts a single representative frame from video_path using FFmpeg.
    Verifies that the extracted image is valid via Pillow before returning.
    """
    v_path = Path(video_path)
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    if not v_path.exists():
        raise FileNotFoundError(f"Video file not found: {v_path}")

    cmd = [
        "ffmpeg",
        "-y",
        "-ss", timestamp_str,
        "-i", str(v_path),
        "-vframes", "1",
        "-q:v", "2",
        str(out_p),
    ]

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
    if res.returncode != 0 or not out_p.exists() or out_p.stat().st_size == 0:
        # Fallback to start timestamp 00:00:00
        cmd[2] = "00:00:00"
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)

    if not out_p.exists() or out_p.stat().st_size == 0:
        raise RuntimeError(f"FFmpeg failed to extract frame from video: {v_path}")

    # Verify frame is readable by Pillow
    with Image.open(out_p) as test_img:
        test_img.verify()

    return out_p


class LocalThumbnailGenerator(ThumbnailGenerator):
    """
    Production local thumbnail generator using Pillow and local repository assets.
    """

    def __init__(self, asset_index: Optional[DeityAssetIndex] = None):
        self.asset_index = asset_index or DeityAssetIndex()
        self.selector = ThumbnailAssetSelector(self.asset_index)

    def select_best_local_asset(
        self,
        deity: str,
        avatar: Optional[str] = None,
        topic: str = "",
    ) -> Path:
        """
        Finds the best local visual asset for the deity:
        - First checks for approved local images in repository.
        - If only videos exist, extracts a representative frame via FFmpeg.
        - Fails closed safely if no matching approved asset exists.
        """
        c_deity, c_avatar = resolve_deity_and_avatar(f"{deity} {avatar or ''} {topic}")
        target_deity = c_deity or deity.lower()
        target_avatar = avatar or c_avatar

        # 1. Query DeityAssetIndex
        approved_records = self.asset_index.find_approved_assets(deity=target_deity, avatar=target_avatar)
        approved_images = [r for r in approved_records if r.file_format.lower() in ("png", "jpg", "jpeg", "webp")]
        approved_videos = [r for r in approved_records if r.file_format.lower() in ("mp4", "mov", "webm", "avi", "mkv")]

        if approved_images:
            return Path(approved_images[0].file_path)

        if approved_videos:
            temp_dir = Path("data/thumbnails/frames")
            temp_dir.mkdir(parents=True, exist_ok=True)
            v_asset = approved_videos[0]
            out_frame = temp_dir / f"extracted_{v_asset.asset_id}.png"
            return extract_video_frame_safely(Path(v_asset.file_path), out_frame)

        # 2. Check physical directory assets/gods/<target_deity>/
        # Requires asset-level approval verification before selecting any file.
        from src.qa.checks import _is_trusted_approved_asset
        for base_dir in (Path("assets/gods"), Path("assets/gods_landscape_long_video")):
            deity_folder = base_dir / target_deity
            if deity_folder.exists() and deity_folder.is_dir():
                # Check for images first
                for ext in (".png", ".jpg", ".jpeg", ".webp"):
                    for candidate in deity_folder.glob(f"*{ext}"):
                        is_approved, _ = _is_trusted_approved_asset(
                            str(candidate),
                            deity=target_deity,
                            avatar=target_avatar,
                        )
                        if is_approved:
                            return candidate
                # Check for videos if no approved images exist
                for v_ext in (".mp4", ".mov", ".webm", ".avi", ".mkv"):
                    for v_candidate in deity_folder.glob(f"*{v_ext}"):
                        is_approved, _ = _is_trusted_approved_asset(
                            str(v_candidate),
                            deity=target_deity,
                            avatar=target_avatar,
                        )
                        if is_approved:
                            temp_dir = Path("data/thumbnails/frames")
                            temp_dir.mkdir(parents=True, exist_ok=True)
                            out_frame = temp_dir / f"extracted_{v_candidate.stem}.png"
                            return extract_video_frame_safely(v_candidate, out_frame)

        raise NoSuitableThumbnailAssetError(
            f"No suitable approved local visual asset found for deity '{target_deity}' (avatar='{target_avatar}'). "
            f"Failing closed to prevent cross-deity substitution."
        )

    def generate_thumbnail(
        self,
        title: str,
        subtitle: str,
        output_path: Path,
        background_image_path: Optional[Path] = None,
        theme: Optional[dict] = None,
        language_code: str = "te-IN",
        **kwargs,
    ) -> Path:
        """
        Generates 1280x720 thumbnail PNG at output_path.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        deity = kwargs.get("deity") or ""
        avatar = kwargs.get("avatar")

        if not deity:
            weekday_info = select_weekday_deity()
            deity = weekday_info["scheduled_deity"]

        if background_image_path and Path(background_image_path).exists():
            bg_p = Path(background_image_path)
            if bg_p.suffix.lower() in VIDEO_EXTENSIONS:
                temp_dir = Path("data/thumbnails/frames")
                temp_dir.mkdir(parents=True, exist_ok=True)
                extracted_frame = temp_dir / f"extracted_bg_{bg_p.stem}.png"
                chosen_bg = extract_video_frame_safely(bg_p, extracted_frame)
            else:
                chosen_bg = bg_p
        else:
            chosen_bg = self.select_best_local_asset(
                deity=deity,
                avatar=avatar,
                topic=kwargs.get("main_event") or title,
            )

        compose_reused_thumbnail(
            background_path=chosen_bg,
            title=title,
            subtitle=subtitle,
            output_path=output_path,
            language_code=language_code,
            theme=theme,
        )

        return output_path

    def generate_for_decision(
        self,
        decision: dict[str, Any],
        script: Optional[dict[str, Any]] = None,
        output_dir: Optional[Path] = None,
        language_code: str = "te-IN",
    ) -> tuple[Path, Path, dict[str, Any]]:
        """
        High-level orchestrator helper:
        Consumes decision and script to produce thumbnail PNG and metadata JSON.
        """
        out_base = Path(output_dir) if output_dir else Path("data/thumbnails")
        out_base.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")

        out_img = out_base / f"thumbnail_{ts}.png"
        out_meta = out_base / f"thumbnail_metadata_{ts}.json"

        topic = decision.get("selected_topic", "")
        deity = decision.get("deity") or ""
        script_title = ""
        if script:
            script_title = script.get("title", "")

        main_title = script_title or topic
        subtitle = "దైవ దర్శనం"
        if ":" in main_title:
            parts = main_title.split(":", 1)
            main_title = parts[0].strip()
            subtitle = parts[1].strip()

        self.generate_thumbnail(
            title=main_title,
            subtitle=subtitle,
            output_path=out_img,
            deity=deity,
            main_event=topic,
            language_code=language_code,
        )

        analysis = analyze_thumbnail_file(
            out_img,
            expected_title=main_title,
            language_code=language_code,
            allow_mock=False,
        )

        metadata = {
            "title": main_title,
            "topic": topic,
            "language_code": language_code,
            "provider": "local",
            "resolution": "1280x720",
            "format": "png",
            "approved_source": decision.get("data_source", "cached_youtube_api"),
            "confidence": decision.get("confidence", "high"),
            "created_at": ts,
            "approval_metadata": {
                "approved_for_generation": decision.get("approved_for_generation", True),
                "selected_topic": topic,
                "language_code": language_code,
                "score": decision.get("score", 85.0),
                "confidence": decision.get("confidence", "high"),
                "data_source": decision.get("data_source", "cached_youtube_api"),
            },
            "validation": analysis,
        }

        ok, err = validate_metadata_output(metadata)
        if not ok:
            raise ValueError(f"Generated thumbnail metadata fails schema validation: {err}")

        with open(out_meta, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        return out_img, out_meta, metadata
