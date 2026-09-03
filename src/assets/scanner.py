# src/assets/scanner.py
# Recursive Directory Scanner for Repository Deity Assets

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.assets.validator import (
    SUPPORTED_IMAGE_EXTS,
    SUPPORTED_VIDEO_EXTS,
    AssetValidationError,
    validate_image_asset,
    validate_video_asset,
)


def scan_gods_assets(
    gods_dir: str | Path = "assets/gods",
) -> dict[str, Any]:
    """
    Recursively scan `assets/gods/` folder for deity visual assets.

    Returns structured dict:
      {
        "scanned_at": "...",
        "deities": {
          "lord_shiva": {
            "images": [ ... ],
            "videos": [ ... ]
          },
          ...
        },
        "stats": {
          "deities_count": int,
          "total_images": int,
          "total_videos": int,
          "total_valid_assets": int,
          "rejected_assets_count": int,
          "rejected_files": [ ... ]
        }
      }
    """
    base_path = Path(gods_dir)
    if not base_path.exists():
        raise FileNotFoundError(f"Gods assets directory not found: {base_path}")

    deities: dict[str, dict[str, list[dict]]] = {}
    rejected_files: list[dict[str, str]] = []
    total_images = 0
    total_videos = 0

    # Scan deity directories
    for folder in sorted(base_path.iterdir()):
        if not folder.is_dir():
            continue

        deity_key = folder.name.lower()
        images: list[dict] = []
        videos: list[dict] = []

        # Recursively find all files inside deity directory
        for item in sorted(folder.rglob("*")):
            if not item.is_file():
                continue

            ext = item.suffix.lower()

            # Ignore unsupported files (.keep, .txt, .json, etc.)
            if ext not in SUPPORTED_IMAGE_EXTS and ext not in SUPPORTED_VIDEO_EXTS:
                continue

            if ext in SUPPORTED_IMAGE_EXTS:
                try:
                    meta = validate_image_asset(item)
                    meta["deity"] = deity_key
                    images.append(meta)
                    total_images += 1
                except AssetValidationError as exc:
                    rejected_files.append({"file": str(item), "reason": str(exc)})

            elif ext in SUPPORTED_VIDEO_EXTS:
                try:
                    meta = validate_video_asset(item)
                    meta["deity"] = deity_key
                    videos.append(meta)
                    total_videos += 1
                except AssetValidationError as exc:
                    rejected_files.append({"file": str(item), "reason": str(exc)})

        # Also scan assets/gods_processed/<deity> if it exists
        processed_dir = base_path.parent / "gods_processed" / folder.name
        if processed_dir.exists() and processed_dir.is_dir():
            for item in sorted(processed_dir.rglob("*")):
                if not item.is_file():
                    continue
                ext = item.suffix.lower()
                if ext in SUPPORTED_VIDEO_EXTS:
                    try:
                        meta = validate_video_asset(item)
                        meta["deity"] = deity_key
                        if not any(v.get("path") == meta.get("path") for v in videos):
                            videos.append(meta)
                            total_videos += 1
                    except AssetValidationError as exc:
                        rejected_files.append({"file": str(item), "reason": str(exc)})

        deities[deity_key] = {
            "images": images,
            "videos": videos,
        }

    return {
        "deities": deities,
        "stats": {
            "deities_count": len(deities),
            "total_images": total_images,
            "total_videos": total_videos,
            "total_valid_assets": total_images + total_videos,
            "rejected_assets_count": len(rejected_files),
            "rejected_files": rejected_files,
        },
    }
