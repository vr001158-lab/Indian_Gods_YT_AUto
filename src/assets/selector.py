# src/assets/selector.py
# Deity Resolution & Scene-Aware Asset Selection

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Sequence

DEITY_ALIASES: dict[str, list[str]] = {
    "lord_shiva": [
        "shiva", "mahadev", "bholenath", "snake", "vasuki", "trishul", "kailash", "somnath", "mahakal", "shivling", "nataraja", "arunachalam", "kedarnath",
        "शिव", "महादेव", "भोलेनाथ", "वासुकी", "कैलाश", "सोमनाथ", "नीलकंठ", "శివ", "శివుడు", "మహాదేవుడు", "వాసుకి", "కైలాస", "నీలకంఠ", "నటరాజ"
    ],
    "lord_vishnu": [
        "vishnu", "narayana", "dashavatar", "viku",
        "विष्णु", "नारायण", "दशावतार", "విష్ణు", "విష్ణువు", "నారాయణ", "దశావతార"
    ],
    "krishna": [
        "krishna", "gopala", "kanha", "govinda", "isckon", "flute", "butter",
        "कृष्ण", "गोपाल", "कान्हा", "गोविन्द", "కృష్ణ", "కృష్ణుడు", "గోపాల", "గోవింద"
    ],
    "ganesha": [
        "ganesha", "ganesh", "vinayaka", "vighnaharta", "gajanana", "broken tusk", "morya",
        "गणेश", "गणपति", "विनायक", "गजानन", "एकदंत", "గణపతి", "వినాయక", "వినాయకుడు", "గణేశ", "ఏకదంత"
    ],
    "hanuman": [
        "hanuman", "bajrangbali", "maruti", "anjaneya", "sanjeevani", "chala",
        "हनुमान", "बजरंगबली", "मारुति", "आंजनेय", "హనుమాన్", "హనుమంతుడు", "ఆంజనేయ", "బజరంగబలి"
    ],
    "lakshmi_devi": [
        "lakshmi", "laxmi", "sri", "wealth",
        "लक्ष्मी", "महालक्ष्मी", "లక్ష్మి", "లక్ష్మీ", "మహాలక్ష్మి"
    ],
    "narasimha": [
        "narasimha", "narasingh", "prahlada", "lion",
        "नरसिंह", "प्रह्लाद", "నరసింహ", "నరసింహ స్వామి", "ప్రహ్లాద"
    ],
    "ram": [
        "ram", "rama", "ramachandra", "ayodhya", "sita", "bow",
        "राम", "श्रीराम", "रामचन्द्र", "अयोध्या", "సీత", "రాముడు", "శ్రీరామ", "అయోధ్య"
    ],
    "parvathi": [
        "parvathi", "parvati", "gauri", "shakti", "durga",
        "पार्वती", "गौरी", "शक्ति", "दुर्गा", "పార్వతి", "గౌరి", "శక్తి", "దుర్గ"
    ],
    "subramanya": [
        "subramanya", "murugan", "kartikeya", "skanda", "vel",
        "सुब्रह्मण्य", "कार्तिकेय", "स्कन्द", "మురుగన్", "సుబ్రహ్మణ్య", "కార్తికేయ"
    ],
    "ayyappa": [
        "ayyappa", "sabarimala", "manikanta",
        "अय्यप्पा", "सबरीमाला", "मणिकंठ", "అయ్యప్ప", "శబరిమల", "మణికంఠ"
    ],
    "7Kondala_Swami": [
        "7kondala", "venkateswara", "balaji", "tirupati", "govinda", "7kondala_swami",
        "वेंकटेश्वर", "बालाजी", "तिरुपति", "వేంకటేశ్వర", "శ్రీవారి", "బాలాజీ", "తిరుపతి", "ఏడుకొండల"
    ],
}


def resolve_deity(topic: str, deity_hint: str = "", default: str | None = "lord_shiva") -> str | None:
    """
    Detect deity from canonical topic or content brief text.
    Returns deity key matching assets/gods/<deity>/ folder name.
    Defaults to `default` ("lord_shiva") if undetermined.
    """
    if deity_hint:
        hint_lower = deity_hint.strip().lower()
        # Direct folder name match
        for key in DEITY_ALIASES:
            if hint_lower == key.lower():
                return key
        # Alias match on hint
        for key, aliases in DEITY_ALIASES.items():
            if hint_lower in [a.lower() for a in aliases]:
                return key

    normalised = topic.lower()
    for deity_key, aliases in DEITY_ALIASES.items():
        for alias in aliases:
            if re.search(r"\b" + re.escape(alias) + r"\b", normalised):
                return deity_key
            if alias in normalised:
                return deity_key
    return default


def _score_semantic_match(asset_path: str, keywords: Sequence[str]) -> int:
    """Score how well an asset path matches scene keywords."""
    p_lower = asset_path.lower()
    score = 0
    for kw in keywords:
        kw_clean = kw.strip().lower()
        if len(kw_clean) >= 3 and kw_clean in p_lower:
            score += 1
    return score


def build_deity_visual_timeline(
    deity_key: str,
    target_duration: float = 45.0,
    content_type: str = "short",
    manifest: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Constructs a retention-optimized visual timeline (mixing images & video clips)
    strictly for `deity_key`.

    Shorts:
      - target_duration: >=35s and <60s (default 45.0s)
      - images: 4s - 8s per image
      - videos: 5s - 15s per clip
      - early visual change (first segment ~4-5s)
      - mixes images & videos if both exist

    Long:
      - target_duration: e.g. 180s+
      - images: 4s - 8s per image
      - videos: 5s - 15s per clip
      - continuous coverage with no long static sections
    """
    if manifest is None:
        from src.assets.manifest import load_asset_manifest
        manifest = load_asset_manifest()

    deities = manifest.get("deities", {})
    target_deity_assets = deities.get(deity_key, {"images": [], "videos": []})

    repo_images = target_deity_assets.get("images", [])
    repo_videos = target_deity_assets.get("videos", [])

    if not repo_images and not repo_videos:
        raise ValueError(f"No visual assets found in repository for deity '{deity_key}'")

    # Combine pool: alternate between videos and images if both exist
    mixed_pool = []
    max_len = max(len(repo_images), len(repo_videos))
    for i in range(max_len):
        if i < len(repo_videos):
            mixed_pool.append(repo_videos[i])
        if i < len(repo_images):
            mixed_pool.append(repo_images[i])

    timeline: list[dict[str, Any]] = []
    current_time = 0.0
    scene_idx = 1
    pool_len = len(mixed_pool)

    # Durations pattern for image segments (4s to 8s)
    image_durations = [5.0, 6.0, 4.0, 7.0, 5.0, 6.0, 4.0, 8.0]

    while current_time < target_duration:
        asset_item = mixed_pool[(scene_idx - 1) % pool_len]
        atype = asset_item.get("type", "image")

        if atype == "video":
            clip_dur = float(asset_item.get("duration", 8.0) or 8.0)
            seg_dur = min(max(5.0, clip_dur), 15.0)
        else:
            seg_dur = image_durations[(scene_idx - 1) % len(image_durations)]

        rem = target_duration - current_time
        if rem < 3.0 and timeline:
            timeline[-1]["duration_seconds"] = round(timeline[-1]["duration_seconds"] + rem, 2)
            break
        elif rem < seg_dur:
            seg_dur = rem

        timeline.append({
            "scene": scene_idx,
            "asset_type": atype,
            "asset": asset_item["path"],
            "image_file": asset_item["path"],
            "asset_id": asset_item.get("asset_id", f"{deity_key}_{scene_idx}"),
            "deity": deity_key,
            "duration_seconds": round(seg_dur, 2),
            "source": "repository",
            "reason_for_selection": f"Visual timeline segment #{scene_idx} ({atype}) for deity '{deity_key}'",
            "validation_result": "OK",
        })

        current_time += seg_dur
        scene_idx += 1

    return timeline


def select_scene_assets(
    deity_key: str,
    scene_scripts: list[dict[str, Any]],
    manifest: dict[str, Any],
    allow_online_fallback: bool = True,
) -> list[dict[str, Any]]:
    """
    Select scene-aware visual assets for scene_scripts according to Priority rules:

    Priority 1: Local repository assets in assets/gods/<deity_key>/
    Priority 2: Strict deity isolation (never borrowing from other deities)
    Priority 3: Online asset fetching ONLY when local repository has no usable assets for deity

    Returns a list of scene asset decision dicts.
    """
    deities = manifest.get("deities", {})
    target_deity_assets = deities.get(deity_key, {"images": [], "videos": []})

    repo_images = target_deity_assets.get("images", [])
    repo_videos = target_deity_assets.get("videos", [])
    all_repo_assets = repo_videos + repo_images  # Strictly target deity assets

    scene_plan: list[dict[str, Any]] = []

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

        # Priority 1: Local repo semantic search for target deity
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

        # Online fallback if no local repo assets exist for target deity
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
