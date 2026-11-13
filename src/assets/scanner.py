# src/assets/scanner.py
# Recursive Directory Scanner for Repository Deity Assets

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from src.assets.validator import (
    SUPPORTED_IMAGE_EXTS,
    SUPPORTED_VIDEO_EXTS,
    AssetValidationError,
    validate_image_asset,
    validate_video_asset,
    validate_landscape_asset,
)

# Canonical catalog of verified narrative-specific visual assets
KNOWN_NARRATIVE_METADATA: dict[str, dict[str, Any]] = {
    "kurma_avatar_mandara_mountain_samudra_manthan": {
        "avatar": "kurma",
        "narrative_event": "kurma_supporting_mandara_mountain",
        "scene_description": "Kurma Avatar supporting Mount Mandara on tortoise shell in cosmic milk ocean during Samudra Manthan",
        "semantic_keywords": ["kurma", "mandara", "samudra", "manthan", "churning", "tortoise", "vasuki", "ocean", "milk"],
        "aspect_ratio": "9:16",
        "source": "ai_devotional_artist",
        "provenance": "Divine Dharshanam Daily generation workflow; visually verified",
        "verification_status": "verified_visual",
    },
    "krishna_lifting_govardhan_hill_with_finger": {
        "avatar": "krishna",
        "narrative_event": "krishna_lifting_govardhan_hill",
        "scene_description": "Young Lord Krishna lifting Mount Govardhan on little finger sheltering Vrindavan devotees and cows from storm",
        "semantic_keywords": ["krishna", "govardhan", "lifting", "hill", "mountain", "finger", "kanishtha", "storm", "cows", "vrindavan"],
        "aspect_ratio": "9:16",
        "source": "ai_devotional_artist",
        "provenance": "Divine Dharshanam Daily generation workflow; visually verified",
        "verification_status": "verified_visual",
    },
    "narasimha_emerging_from_pillar_prahlada": {
        "avatar": "narasimha",
        "narrative_event": "narasimha_emerging_from_pillar",
        "scene_description": "Lord Narasimha with blazing mane bursting from fractured palace pillar in divine fire with Prahlada bowing",
        "semantic_keywords": ["narasimha", "pillar", "prahlada", "emerging", "shattered", "fractured", "bursting", "hiranyakashipu"],
        "aspect_ratio": "9:16",
        "source": "ai_devotional_artist",
        "provenance": "Divine Dharshanam Daily generation workflow; visually verified",
        "verification_status": "verified_visual",
    },
    "vamana_trivikrama_three_strides_bali": {
        "avatar": "vamana_trivikrama",
        "narrative_event": "vamana_taking_three_strides",
        "scene_description": "Cosmic Trivikrama spanning universe with one foot on Earth and one in heavens washed by Brahma while King Bali kneels",
        "semantic_keywords": ["vamana", "trivikrama", "three", "strides", "steps", "bali", "brahma", "cosmic", "universe"],
        "aspect_ratio": "9:16",
        "source": "ai_devotional_artist",
        "provenance": "Divine Dharshanam Daily generation workflow; visually verified",
        "verification_status": "verified_visual",
    },
    "hanuman carrying sanjeevani": {
        "avatar": "hanuman",
        "narrative_event": "hanuman_carrying_dronagiri_sanjeevani",
        "scene_description": "Lord Hanuman airborne in night sky carrying Mount Dronagiri with glowing Sanjeevani herbs under full moon",
        "semantic_keywords": ["hanuman", "carrying", "sanjeevani", "dronagiri", "mountain", "herb", "flying", "night", "sky"],
        "aspect_ratio": "9:16",
        "source": "repository_collection",
        "provenance": "Repository collection; visually verified",
        "verification_status": "verified_visual",
    },
    # Landscape variants
    "kurma_avatar_mandara_mountain_samudra_manthan_landscape": {
        "avatar": "kurma",
        "narrative_event": "kurma_supporting_mandara_mountain",
        "scene_description": "Panoramic Samudra Manthan with Kurma Avatar supporting Mount Mandara with Devas and Asuras pulling Vasuki",
        "semantic_keywords": ["kurma", "mandara", "samudra", "manthan", "churning", "tortoise", "vasuki", "ocean", "milk"],
        "aspect_ratio": "16:9",
        "source": "ai_devotional_artist",
        "provenance": "Divine Dharshanam Daily generation workflow; visually verified",
        "verification_status": "verified_visual",
    },
    "krishna_lifting_govardhan_hill_with_finger_landscape": {
        "avatar": "krishna",
        "narrative_event": "krishna_lifting_govardhan_hill",
        "scene_description": "Panoramic painting of Lord Krishna lifting Mount Govardhan sheltering Vrindavan from Indra's storm",
        "semantic_keywords": ["krishna", "govardhan", "lifting", "hill", "mountain", "finger", "storm", "cows", "vrindavan"],
        "aspect_ratio": "16:9",
        "source": "ai_devotional_artist",
        "provenance": "Divine Dharshanam Daily generation workflow; visually verified",
        "verification_status": "verified_visual",
    },
    "narasimha_emerging_from_pillar_prahlada_landscape": {
        "avatar": "narasimha",
        "narrative_event": "narasimha_emerging_from_pillar",
        "scene_description": "Panoramic royal hall scene of Lord Narasimha bursting out from fractured golden pillar with Prahlada bowing",
        "semantic_keywords": ["narasimha", "pillar", "prahlada", "emerging", "shattered", "fractured", "bursting", "palace"],
        "aspect_ratio": "16:9",
        "source": "ai_devotional_artist",
        "provenance": "Divine Dharshanam Daily generation workflow; visually verified",
        "verification_status": "verified_visual",
    },
    "vamana_trivikrama_three_strides_bali_landscape": {
        "avatar": "vamana_trivikrama",
        "narrative_event": "vamana_taking_three_strides",
        "scene_description": "Panoramic cosmic scene of Trivikrama spanning universe with Brahma washing divine foot and Bali kneeling on Earth",
        "semantic_keywords": ["vamana", "trivikrama", "three", "strides", "steps", "bali", "brahma", "cosmic", "universe"],
        "aspect_ratio": "16:9",
        "source": "ai_devotional_artist",
        "provenance": "Divine Dharshanam Daily generation workflow; visually verified",
        "verification_status": "verified_visual",
    },
    "hanuman_carrying_dronagiri_sanjeevani_landscape": {
        "avatar": "hanuman",
        "narrative_event": "hanuman_carrying_dronagiri_sanjeevani",
        "scene_description": "Panoramic night sky scene of Lord Hanuman flying over Himalayan peaks carrying Mount Dronagiri with Sanjeevani herbs",
        "semantic_keywords": ["hanuman", "carrying", "sanjeevani", "dronagiri", "mountain", "herb", "flying", "night", "sky"],
        "aspect_ratio": "16:9",
        "source": "ai_devotional_artist",
        "provenance": "Divine Dharshanam Daily generation workflow; visually verified",
        "verification_status": "verified_visual",
    },
}


def _enrich_asset_metadata(meta: dict[str, Any], stem: str, deity_key: str) -> dict[str, Any]:
    """Enriches asset metadata with narrative and verification fields."""
    stem_lower = stem.lower()
    matched_entry = None
    # Check longest pattern keys first (e.g. landscape variants before vertical)
    for pattern_key, entry in sorted(KNOWN_NARRATIVE_METADATA.items(), key=lambda x: len(x[0]), reverse=True):
        if pattern_key in stem_lower:
            matched_entry = entry
            break

    w = meta.get("width", 0)
    h = meta.get("height", 0)
    measured_ar = "16:9" if (w and h and w >= h) else "9:16"

    if matched_entry:
        meta["avatar"] = matched_entry["avatar"]
        meta["narrative_event"] = matched_entry["narrative_event"]
        meta["scene_description"] = matched_entry["scene_description"]
        meta["semantic_keywords"] = matched_entry["semantic_keywords"]
        meta["aspect_ratio"] = measured_ar
        meta["source"] = matched_entry["source"]
        meta["provenance"] = matched_entry["provenance"]
        meta["verification_status"] = matched_entry["verification_status"]
        # Merge semantic keywords into tags so legacy tag matching also finds them
        existing_tags = set(meta.get("tags", []))
        existing_tags.update(matched_entry["semantic_keywords"])
        meta["tags"] = sorted(existing_tags)
    else:
        # Detect avatar from stem if present
        detected_avatar = deity_key
        for av in ("varaha", "kurma", "vamana", "trivikrama", "narasimha", "krishna", "rama", "matsya", "kalki"):
            if av in stem_lower:
                detected_avatar = "vamana_trivikrama" if av in ("vamana", "trivikrama") else av
                break

        meta["avatar"] = detected_avatar
        meta["narrative_event"] = "general_deity_portrait"
        meta["scene_description"] = f"Repository visual asset for {deity_key} (avatar={detected_avatar})"
        meta["semantic_keywords"] = meta.get("tags", [])
        meta["aspect_ratio"] = measured_ar
        meta["source"] = "repository_collection"
        meta["provenance"] = "Existing repository collection"
        meta["verification_status"] = "unverified"

    return meta


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

            stem = item.stem
            # Extract tags only from identifiable non-hash tokens
            tags = [
                t.lower() for t in re.findall(r"#?([a-zA-Z0-9_]+)", stem)
                if len(t) >= 3 and not re.fullmatch(r"[0-9a-f]{32}", t.lower()) and not t.lower().startswith("downloaded")
            ]

            if ext in SUPPORTED_IMAGE_EXTS:
                try:
                    meta = validate_image_asset(item)
                    meta["deity"] = deity_key
                    meta["tags"] = tags
                    meta = _enrich_asset_metadata(meta, stem, deity_key)
                    images.append(meta)
                    total_images += 1
                except AssetValidationError as exc:
                    rejected_files.append({"file": str(item), "reason": str(exc)})

            elif ext in SUPPORTED_VIDEO_EXTS:
                try:
                    meta = validate_video_asset(item)
                    meta["deity"] = deity_key
                    meta["tags"] = tags
                    meta = _enrich_asset_metadata(meta, stem, deity_key)
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


def scan_gods_landscape_assets(
    gods_dir: str | Path = "assets/gods_landscape_long_video",
) -> dict[str, Any]:
    """
    Recursively scans `assets/gods_landscape_long_video/` folder for deity visual assets.
    Enforces landscape-only validation: rejects any asset that is portrait (width < height).
    Never scans or includes assets from assets/gods/.
    """
    base_path = Path(gods_dir)
    if not base_path.exists():
        raise FileNotFoundError(f"Landscape gods assets directory not found: {base_path}")

    deities: dict[str, dict[str, list[dict]]] = {}
    rejected_files: list[dict[str, str]] = []
    total_images = 0
    total_videos = 0

    for folder in sorted(base_path.iterdir()):
        if not folder.is_dir():
            continue

        deity_key = folder.name.lower()
        images: list[dict] = []
        videos: list[dict] = []

        for item in sorted(folder.rglob("*")):
            if not item.is_file():
                continue

            ext = item.suffix.lower()
            if ext not in SUPPORTED_IMAGE_EXTS and ext not in SUPPORTED_VIDEO_EXTS:
                continue

            if ext in SUPPORTED_IMAGE_EXTS:
                try:
                    meta = validate_image_asset(item)
                    meta["deity"] = deity_key
                    meta = _enrich_asset_metadata(meta, item.stem, deity_key)
                    ok_land, land_err = validate_landscape_asset(meta)
                    if not ok_land:
                        rejected_files.append({"file": str(item), "reason": land_err})
                        continue
                    images.append(meta)
                    total_images += 1
                except AssetValidationError as exc:
                    rejected_files.append({"file": str(item), "reason": str(exc)})

            elif ext in SUPPORTED_VIDEO_EXTS:
                try:
                    meta = validate_video_asset(item)
                    meta["deity"] = deity_key
                    meta = _enrich_asset_metadata(meta, item.stem, deity_key)
                    ok_land, land_err = validate_landscape_asset(meta)
                    if not ok_land:
                        rejected_files.append({"file": str(item), "reason": land_err})
                        continue
                    videos.append(meta)
                    total_videos += 1
                except AssetValidationError as exc:
                    rejected_files.append({"file": str(item), "reason": str(exc)})

        # Also scan assets/gods_processed/<folder.name>/horizontal for landscape videos
        processed_dir = base_path.parent / "gods_processed" / folder.name / "horizontal"
        if processed_dir.exists() and processed_dir.is_dir():
            for item in sorted(processed_dir.rglob("*")):
                if not item.is_file():
                    continue
                ext = item.suffix.lower()
                if ext in SUPPORTED_VIDEO_EXTS:
                    try:
                        meta = validate_video_asset(item)
                        meta["deity"] = deity_key
                        meta = _enrich_asset_metadata(meta, item.stem, deity_key)
                        ok_land, land_err = validate_landscape_asset(meta)
                        if not ok_land:
                            rejected_files.append({"file": str(item), "reason": land_err})
                            continue
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
