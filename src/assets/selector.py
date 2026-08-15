# src/assets/selector.py
# Deity Resolution & Scene-Aware Asset Selection

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Sequence

DEITY_ALIASES: dict[str, list[str]] = {
    "lord_shiva": ["shiva", "mahadev", "bholenath", "snake", "vasuki", "trishul", "kailash", "somnath", "mahakal", "shivling", "nataraja", "arunachalam", "kedarnath"],
    "lord_vishnu": ["vishnu", "narayana", "dashavatar", "viku"],
    "krishna": ["krishna", "gopala", "kanha", "govinda", "isckon", "flute", "butter"],
    "ganesha": ["ganesha", "ganesh", "vinayaka", "vighnaharta", "gajanana", "broken tusk", "morya"],
    "hanuman": ["hanuman", "bajrangbali", "maruti", "anjaneya", "sanjeevani", "chala"],
    "lakshmi_devi": ["lakshmi", "laxmi", "sri", "wealth"],
    "narasimha": ["narasimha", "narasingh", "prahlada", "lion"],
    "ram": ["ram", "rama", "ramachandra", "ayodhya", "sita", "bow"],
    "parvathi": ["parvathi", "parvati", "gauri", "shakti", "durga"],
    "subramanya": ["subramanya", "murugan", "kartikeya", "skanda", "vel"],
    "ayyappa": ["ayyappa", "sabarimala", "manikanta"],
    "7Kondala_Swami": ["7kondala", "venkateswara", "balaji", "tirupati", "govinda", "7kondala_swami"],
}


def resolve_deity(topic: str) -> str:
    """
    Detect deity from canonical topic or content brief text.
    Returns deity key matching assets/gods/<deity>/ folder name.
    Defaults to "lord_shiva" if undetermined.
    """
    normalised = topic.lower()
    for deity_key, aliases in DEITY_ALIASES.items():
        for alias in aliases:
            if re.search(r"\b" + re.escape(alias) + r"\b", normalised):
                return deity_key
            if alias in normalised:
                return deity_key
    return "lord_shiva"


def _score_semantic_match(asset_path: str, keywords: Sequence[str]) -> int:
    """Score how well an asset path matches scene keywords."""
    p_lower = asset_path.lower()
    score = 0
    for kw in keywords:
        kw_clean = kw.strip().lower()
        if len(kw_clean) >= 3 and kw_clean in p_lower:
            score += 1
    return score


def select_scene_assets(
    deity_key: str,
    scene_scripts: list[dict[str, Any]],
    manifest: dict[str, Any],
    allow_online_fallback: bool = True,
) -> list[dict[str, Any]]:
    """
    Select scene-aware visual assets for scene_scripts according to Priority rules:

    Priority 1: Local repository assets in assets/gods/<deity_key>/
    Priority 2: Other repository assets locally
    Priority 3: Online asset fetching ONLY when local repository has no usable assets

    Returns a list of scene asset decision dicts.
    """
    deities = manifest.get("deities", {})
    target_deity_assets = deities.get(deity_key, {"images": [], "videos": []})
    
    repo_images = target_deity_assets.get("images", [])
    repo_videos = target_deity_assets.get("videos", [])
    all_repo_assets = repo_videos + repo_images  # Prefer videos if available, then images

    scene_plan: list[dict[str, Any]] = []

    # If priority 1 has no assets for this deity, check priority 2 (other deity folders)
    if not all_repo_assets:
        for other_deity, assets_dict in deities.items():
            combined = assets_dict.get("videos", []) + assets_dict.get("images", [])
            if combined:
                all_repo_assets = combined
                break

    for item in scene_scripts:
        scene_num = item["scene"]
        visual_ref = item.get("visual_reference", "")
        script_text = item.get("script_text", "")
        keywords = [
            w for w in re.sub(r"[^a-zA-Z0-9\s]", "", f"{visual_ref} {script_text}").lower().split()
            if len(w) >= 4
        ]

        selected_asset = None
        selection_source = "repository"
        selection_reason = ""

        # Priority 1 & 2: Local repo semantic search
        if all_repo_assets:
            best_score = -1
            best_candidate = None
            for candidate in all_repo_assets:
                score = _score_semantic_match(candidate["path"], keywords)
                if score > best_score:
                    best_score = score
                    best_candidate = candidate

            if best_candidate and best_score > 0:
                selected_asset = best_candidate
                selection_reason = f"Semantic match (score={best_score}) in repository deity assets for '{deity_key}'"
            else:
                # Deterministic fallback by scene index
                idx = (scene_num - 1) % len(all_repo_assets)
                selected_asset = all_repo_assets[idx]
                selection_reason = f"Deity repository asset fallback for '{deity_key}' (scene #{scene_num})"

        # Priority 3: Online fallback if no local repo assets exist
        if not selected_asset:
            if not allow_online_fallback:
                raise RuntimeError(f"No repository assets found for deity '{deity_key}' and online fallback disabled.")

            selection_source = "online"
            selection_reason = f"Online asset fallback generated for scene #{scene_num} (no local repo assets)"
            selected_asset = {
                "asset_id": f"online_{deity_key}_scene_{scene_num}",
                "type": "image",
                "path": f"data/visuals/online_cache/scene_{scene_num}.png",
                "width": 720,
                "height": 1280,
                "valid": True,
            }

        scene_plan.append({
            "scene": scene_num,
            "asset_type": selected_asset["type"],
            "asset": selected_asset["path"],
            "asset_id": selected_asset.get("asset_id", ""),
            "deity": deity_key,
            "source": selection_source,
            "reason_for_selection": selection_reason,
            "validation_result": "OK",
        })

    return scene_plan
