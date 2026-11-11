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
        "vishnu", "narayana", "dashavatar", "viku", "kurma", "vamana", "trivikrama", "matsya", "varaha", "parashurama", "kalki", "gajendra", "makara",
        "विष्णु", "नारायण", "दशावतार", "कूर्म", "वामन", "त्रिविक्रम", "మత్స్య", "కూర్మ", "వామన", "త్రివిక్రమ", "విష్ణు", "విష్ణువు", "నారాయణ", "దశావతార", "గజేంద్ర"
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
        "hanuman", "bajrangbali", "maruti", "anjaneya", "sanjeevani", "chala", "dronagiri",
        "हनुमान", "बजरंगबली", "मारुति", "आंजनेय", "संजीवनी", "द्रोणागिरि", "హనుమాన్", "హనుమంతుడు", "హనుమంతుని", "హనుమ", "సంజీవని", "ద్రోణగిరి", "ఆంజనేయ", "బజరంగబలి"
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


TELUGU_NARRATIVE_CONCEPTS: dict[str, list[str]] = {
    "కైలాస": ["kailash", "mountain", "snow"],
    "పాము": ["snake", "cobra", "serpent", "vasuki"],
    "సర్పం": ["snake", "cobra", "serpent", "vasuki"],
    "వాసుకి": ["vasuki", "snake", "cobra"],
    "విషం": ["halahala", "poison", "blue"],
    "హాలాహల": ["halahala", "poison"],
    "నీలకంఠ": ["neelkanth", "blue"],
    "ధ్యానం": ["meditation", "meditating", "serene"],
    "మథనం": ["churning", "manthan", "mandara"],
    "దంతం": ["tusk", "broken tusk", "ekadanta"],
    "ఏకదంత": ["ekadanta", "tusk"],
    "మహాభారత": ["mahabharata", "vyasa", "writing"],
    "గోవర్ధన": ["govardhan", "hill", "mountain", "lift", "rain"],
    "గోవర్ధనగిరి": ["govardhan", "hill", "mountain", "lift"],
    "చిటికెన వేలు": ["little finger", "finger", "lift"],
    "కొండ": ["hill", "mountain"],
    "వర్షం": ["rain", "storm", "clouds", "thunder"],
    "ఇంద్రుని": ["indra", "storm", "surrender"],
    "శబరి": ["shabari", "devotion", "fruits", "berries"],
    "కోదండ": ["kodanda", "bow", "arrow"],
    "బాణం": ["arrow", "bow"],
    "రామసేతు": ["setu", "bridge", "ocean"],
    "సేతు": ["setu", "bridge"],
    "సంజీవని": ["sanjeevani", "herb", "mountain", "dronagiri"],
    "ద్రోణగిరి": ["dronagiri", "mountain", "carry", "lifting"],
    "లక్ష్మణుని": ["lakshmana", "healing", "revive"],
    "మహిషాసుర": ["mahishasura", "demon", "slaying"],
    "సింహం": ["lion", "simha"],
    "త్రిశూలం": ["trishul", "trident"],
    "నవరాత్రి": ["navaratri", "durga"],
    "వామన": ["vamana", "trivikrama", "dwarf", "brahmachari"],
    "త్రివిక్రమ": ["trivikrama", "strides", "three steps", "vishwaroopa"],
    "మూడు అడుగులు": ["three steps", "three strides", "trivikrama"],
    "బలి": ["bali", "mahabali"],
    "కూర్మ": ["kurma", "tortoise", "mandara", "churning", "ocean"],
    "తాబేలు": ["tortoise", "kurma"],
    "పాలసముద్రం": ["milk ocean", "churning", "mandara", "ocean"],
    "నరసింహ": ["narasimha", "lion", "stambha", "pillar"],
    "స్తంభం": ["pillar", "stambha", "emerging", "shattering"],
    "హిరణ్యకశిపు": ["hiranyakashipu", "demon", "slaying"],
    "ప్రహ్లాద": ["prahlada", "devotion", "child"],
    "తిరుపతి": ["tirupati", "tirumala", "temple", "balaji"],
    "తిరుమల": ["tirumala", "tirupati", "temple", "ananda nilayam"],
    "శ్రీనివాస": ["srinivasa", "balaji", "venkateswara"],
    "ఏడుకొండల": ["7kondala", "seven hills", "balaji", "govinda"],
    "గజేంద్ర": ["gajendra", "elephant", "lotus"],
    "మొసలి": ["crocodile", "makara"],
    "సుదర్శన": ["sudarshana", "chakra"],
    "చక్రం": ["chakra"],
    "గరుడ": ["garuda"],
}


SEMANTIC_STOP_WORDS: set[str] = {
    # Generic entity and devotional words
    "lord", "god", "gods", "deity", "avatar", "swami", "image", "picture", "photo", "wallpaper",
    "download", "downloaded", "file", "scene", "prompt", "video", "visual", "reference",
    # Generic devotional and aesthetic adjectives (not scene-specific actions)
    "cosmic", "divine", "celestial", "sacred", "holy", "eternal", "golden", "radiant", "ancient",
    "blessed", "supreme", "universe", "magnificent", "beautiful", "peaceful", "powerful",
    # English grammar stop words
    "the", "and", "with", "from", "into", "onto", "over", "under", "about", "taking", "before",
    "after", "through", "while", "that", "this", "they", "them", "then", "their", "there",
    "some", "more", "most", "also", "have", "been", "were", "what", "when", "where", "which",
    "who", "whom", "whose", "why", "how", "all", "any", "both", "each", "few", "other", "such",
    "than", "too", "very", "can", "will", "just", "should", "now", "for", "are", "his", "her", "its",
    # Common Telugu functional words
    "స్వామి", "దేవుడు", "భగవంతుడు", "చిత్రం", "దృశ్యం", "మరియు", "యొక్క", "కోసం",
}

ASSET_PATH_NOISE_WORDS: set[str] = {
    "assets", "gods", "god", "lord", "chatgpt", "image", "photo", "wallpaper",
    "download", "downloaded", "file", "horizontal", "vertical", "jpeg", "jpg", "png", "webp", "mp4",
}


def extract_scene_semantic_keywords(item: dict[str, Any]) -> list[str]:
    """
    Extracts semantic search keywords from a scene script item.
    Supports English prompts as well as Telugu narrative concept translations.
    Filters out generic stop words to prevent false semantic matches.
    """
    visual_ref = item.get("visual_reference", "")
    script_text = item.get("script_text", "") or item.get("voice_text", "")
    img_prompt = item.get("image_prompt", "")
    vid_prompt = item.get("video_prompt", "")
    combined = f"{visual_ref} {script_text} {img_prompt} {vid_prompt}".lower()

    # 1. English keywords
    keywords = [
        w for w in re.sub(r"[^a-zA-Z0-9\s]", " ", combined).split()
        if len(w) >= 3 and w not in SEMANTIC_STOP_WORDS
    ]

    # 2. Telugu Concept Translations
    for te_term, en_translations in TELUGU_NARRATIVE_CONCEPTS.items():
        if te_term in combined or te_term in visual_ref or te_term in script_text:
            keywords.extend([w for w in en_translations if w not in SEMANTIC_STOP_WORDS])

    return list(dict.fromkeys(keywords))


def _score_semantic_match(asset: dict[str, Any] | str, keywords: Sequence[str]) -> int:
    """Score how well an asset path or candidate matches scene keywords."""
    score, _ = _get_semantic_match_details(asset, keywords)
    return score


def _get_semantic_match_details(asset: dict[str, Any] | str, keywords: Sequence[str]) -> tuple[int, list[str]]:
    """
    Returns (score: int, matched_keywords: list[str]).
    Searches strictly within the asset filename stem, clean tags,
    semantic_keywords, and narrative_event, avoiding folder path prefixes.
    """
    if isinstance(asset, dict):
        path_str = asset.get("path", "")
        tags = asset.get("tags", [])
        sem_kws = asset.get("semantic_keywords", [])
        event = asset.get("narrative_event", "")
    else:
        path_str = str(asset)
        tags = []
        sem_kws = []
        event = ""

    stem = Path(path_str).stem.lower()
    stem_words = [
        w.lower() for w in re.sub(r"[^a-zA-Z0-9\s]", " ", stem).split()
        if len(w) >= 3 and w.lower() not in ASSET_PATH_NOISE_WORDS
    ]
    clean_tags = [
        t.lower() for t in tags
        if isinstance(t, str) and len(t) >= 3 and t.lower() not in ASSET_PATH_NOISE_WORDS
    ]
    clean_sem_kws = [
        k.lower() for k in sem_kws
        if isinstance(k, str) and len(k) >= 3 and k.lower() not in ASSET_PATH_NOISE_WORDS
    ]
    event_words = [
        w.lower() for w in re.sub(r"[^a-zA-Z0-9\s]", " ", event).split()
        if len(w) >= 3 and w.lower() not in ASSET_PATH_NOISE_WORDS
    ]

    all_tokens = stem_words + clean_tags + clean_sem_kws + event_words
    search_tokens = set(all_tokens)
    search_text = f" {' '.join(all_tokens)} "

    matched: list[str] = []
    for kw in keywords:
        kw_clean = kw.strip().lower()
        if len(kw_clean) >= 3 and kw_clean not in SEMANTIC_STOP_WORDS:
            if kw_clean in search_tokens or f" {kw_clean} " in search_text:
                matched.append(kw_clean)

    return len(matched), matched


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
        keywords = extract_scene_semantic_keywords(item)

        selected_asset = None
        selection_source = "repository"
        selection_reason = ""
        semantic_confidence = "NONE"
        semantic_match_found = False
        matched_keywords: list[str] = []

        # Priority 1: Local repo semantic search for target deity
        if all_repo_assets:
            best_score = -1
            best_candidate = None
            best_matched: list[str] = []
            best_is_verified = False
            for candidate in all_repo_assets:
                score, matched = _get_semantic_match_details(candidate, keywords)
                is_ver = (candidate.get("verification_status") == "verified_visual") if isinstance(candidate, dict) else False
                if score > best_score or (score == best_score and score > 0 and is_ver and not best_is_verified):
                    best_score = score
                    best_candidate = candidate
                    best_matched = matched
                    best_is_verified = is_ver

            if best_candidate and best_score > 0:
                selected_asset = best_candidate
                semantic_match_found = True
                matched_keywords = best_matched
                semantic_confidence = "HIGH" if best_score >= 2 else "MEDIUM"
                verified_str = " [VERIFIED]" if best_is_verified else ""
                selection_reason = (
                    f"Semantic match{verified_str} (score={best_score}, matched={best_matched}) "
                    f"in repository deity assets for '{deity_key}'"
                )
            else:
                # Deterministic fallback by scene index within the SAME deity
                semantic_confidence = "NONE"
                semantic_match_found = False
                idx = (scene_num - 1) % len(all_repo_assets)
                selected_asset = all_repo_assets[idx]
                sample_kws = keywords[:3] if keywords else ["general"]
                selection_reason = (
                    f"Deity repository general asset fallback for '{deity_key}' (scene #{scene_num}). "
                    f"Missing specific semantic asset for keywords {sample_kws}."
                )

        # Online fallback if no local repo assets exist for target deity
        if not selected_asset:
            if not allow_online_fallback:
                raise RuntimeError(
                    f"Missing scene asset: No repository assets found for deity '{deity_key}' "
                    f"and online fallback is disabled."
                )

            selection_source = "online"
            semantic_confidence = "NONE"
            semantic_match_found = False
            selection_reason = (
                f"Reported missing scene #{scene_num}: using approved online asset fallback "
                f"(no local repo assets found for '{deity_key}')"
            )
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
            "semantic_confidence": semantic_confidence,
            "semantic_match_found": semantic_match_found,
            "matched_keywords": matched_keywords,
            "missing_semantic_match": not semantic_match_found,
            "fallback_triggered": not semantic_match_found,
            "validation_result": "OK",
        })

    return scene_plan


def select_landscape_scene_assets(
    deity_key: str,
    scene_scripts: list[dict[str, Any]],
    manifest: dict[str, Any] | None = None,
    gods_dir: str | Path = "assets/gods_landscape_long_video",
) -> list[dict[str, Any]]:
    """
    Select scene-aware landscape assets strictly from `assets/gods_landscape_long_video/<deity_key>/`.
    Enforces:
      - Only landscape assets (width >= height)
      - Never uses assets/gods/ or portrait assets
      - Rejects if deity folder has no valid landscape assets
      - Logs selected folder and assets
    """
    if manifest is None:
        from src.assets.manifest import load_landscape_asset_manifest
        manifest = load_landscape_asset_manifest(gods_dir=gods_dir)

    deities = manifest.get("deities", {})
    target_deity_assets = deities.get(deity_key, {"images": [], "videos": []})
    repo_images = [img for img in target_deity_assets.get("images", []) if img.get("width", 0) >= img.get("height", 0)]
    repo_videos = [vid for vid in target_deity_assets.get("videos", []) if vid.get("width", 0) >= vid.get("height", 0)]
    all_repo_assets = repo_videos + repo_images

    if not all_repo_assets:
        folder_path = Path(gods_dir) / deity_key
        raise ValueError(
            f"No valid landscape visual assets found for deity '{deity_key}' in {folder_path}. "
            f"Fallback to portrait assets/gods/ is strictly prohibited."
        )

    import sys
    print(
        f"  [LANDSCAPE ASSET SELECTION] Deity: '{deity_key}' | Source folder: {Path(gods_dir)/deity_key} | "
        f"Valid landscape assets: {len(all_repo_assets)}",
        file=sys.stderr,
    )

    scene_plan: list[dict[str, Any]] = []
    for item in scene_scripts:
        scene_num = item["scene"]
        keywords = extract_scene_semantic_keywords(item)

        best_score = -1
        best_candidate = None
        best_matched: list[str] = []
        best_is_verified = False
        for candidate in all_repo_assets:
            score, matched = _get_semantic_match_details(candidate, keywords)
            is_ver = (candidate.get("verification_status") == "verified_visual") if isinstance(candidate, dict) else False
            if score > best_score or (score == best_score and score > 0 and is_ver and not best_is_verified):
                best_score = score
                best_candidate = candidate
                best_matched = matched
                best_is_verified = is_ver

        if best_candidate and best_score > 0:
            selected_asset = best_candidate
            semantic_match_found = True
            semantic_confidence = "HIGH" if best_score >= 2 else "MEDIUM"
            verified_str = " [VERIFIED]" if best_is_verified else ""
            selection_reason = (
                f"Landscape semantic match{verified_str} (score={best_score}, matched={best_matched}) for '{deity_key}'"
            )
        else:
            idx = (scene_num - 1) % len(all_repo_assets)
            selected_asset = all_repo_assets[idx]
            semantic_match_found = False
            semantic_confidence = "NONE"
            sample_kws = keywords[:3] if keywords else ["general"]
            selection_reason = (
                f"Landscape asset #{idx+1} for '{deity_key}' (scene #{scene_num}). "
                f"Missing specific semantic asset for keywords {sample_kws}."
            )

        scene_plan.append({
            "scene": scene_num,
            "asset_type": selected_asset["type"],
            "asset": selected_asset["path"],
            "asset_id": selected_asset.get("asset_id", ""),
            "deity": deity_key,
            "source": "landscape_repository",
            "reason_for_selection": selection_reason,
            "semantic_confidence": semantic_confidence,
            "semantic_match_found": semantic_match_found,
            "matched_keywords": best_matched,
            "missing_semantic_match": not semantic_match_found,
            "fallback_triggered": not semantic_match_found,
            "validation_result": "OK",
            "width": selected_asset.get("width"),
            "height": selected_asset.get("height"),
        })

    return scene_plan


def build_landscape_visual_timeline(
    deity_key: str,
    target_duration: float = 180.0,
    manifest: dict[str, Any] | None = None,
    gods_dir: str | Path = "assets/gods_landscape_long_video",
) -> list[dict[str, Any]]:
    """
    Constructs a visual timeline (mixing landscape images & landscape video clips)
    strictly from `assets/gods_landscape_long_video/<deity_key>/`.
    """
    if manifest is None:
        from src.assets.manifest import load_landscape_asset_manifest
        manifest = load_landscape_asset_manifest(gods_dir=gods_dir)

    deities = manifest.get("deities", {})
    target_deity_assets = deities.get(deity_key, {"images": [], "videos": []})
    repo_images = [img for img in target_deity_assets.get("images", []) if img.get("width", 0) >= img.get("height", 0)]
    repo_videos = [vid for vid in target_deity_assets.get("videos", []) if vid.get("width", 0) >= vid.get("height", 0)]

    if not repo_images and not repo_videos:
        folder_path = Path(gods_dir) / deity_key
        raise ValueError(
            f"No valid landscape visual assets found for deity '{deity_key}' in {folder_path}. "
            f"Fallback to portrait assets/gods/ is strictly prohibited."
        )

    import sys
    print(
        f"  [LANDSCAPE TIMELINE] Deity: '{deity_key}' | Folder: {Path(gods_dir)/deity_key} | "
        f"Images: {len(repo_images)}, Videos: {len(repo_videos)}",
        file=sys.stderr,
    )

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
    image_durations = [5.0, 6.0, 5.5, 7.0, 6.0, 5.0, 6.5, 8.0]

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
            "source": "landscape_repository",
            "reason_for_selection": f"Landscape segment #{scene_idx} ({atype}) for deity '{deity_key}'",
            "validation_result": "OK",
            "width": asset_item.get("width"),
            "height": asset_item.get("height"),
        })

        current_time += seg_dur
        scene_idx += 1

    return timeline
