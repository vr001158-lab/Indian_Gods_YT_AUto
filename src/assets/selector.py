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
        "lakshmi", "laxmi", "sridevi", "sri devi", "mahalakshmi", "wealth",
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
        "tirumala", "srinivasa", "seshachala", "venkanna", "seven hills",
        "वेंकटेश्वर", "बालाजी", "तिरुपति", "తిరుమల", "శ్రీనివాస", "శ్రీనివాసుడు", "వేంకటేశ్వర",
        "శ్రీవారి", "బాలాజీ", "తిరుపతి", "ఏడుకొండల", "ఏడుకొండలవాడు", "ఏడుకొండలవాడా",
        "గోవింద", "గోవిందా", "శేషాచల", "వెంకటేశ్వర", "వెంకన్న"
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

    if not topic or not str(topic).strip():
        return default

    normalised = str(topic).lower()

    # Score each candidate deity by alias occurrences in the text
    deity_scores: dict[str, int] = {}
    for deity_key, aliases in DEITY_ALIASES.items():
        score = 0
        for alias in aliases:
            a_lower = alias.lower()
            if not a_lower:
                continue
            if a_lower.isascii() and a_lower.isalnum():
                matches = len(re.findall(r"\b" + re.escape(a_lower) + r"\b", normalised))
                score += matches
            else:
                if a_lower in normalised:
                    score += normalised.count(a_lower)
        if score > 0:
            deity_scores[deity_key] = score

    if deity_scores:
        # Return deity with highest match score
        best_deity = max(deity_scores, key=lambda k: deity_scores[k])
        return best_deity

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


def is_matching_orientation(asset: dict[str, Any] | str, content_type: str) -> bool:
    """
    Strictly determine whether an asset matches the target orientation.
    - 'short': Requires vertical (9:16 or height >= width).
    - 'long': Requires horizontal (16:9 or width >= height).

    Rules:
    1. Reliable dimensions (width > 0 and height > 0) take precedence over path or folder names.
       If width/height metadata contradicts a folder name, dimensions win.
    2. If dimensions are unavailable (0 or None), check explicit aspect_ratio / orientation metadata.
    3. If metadata is unavailable, inspect validated folder / path structure.
    4. Safe fail-closed: If orientation cannot be verified, returns False (never silently accept unknown orientation).
    """
    target_is_long = (content_type == "long")

    if isinstance(asset, str):
        path_str = asset.lower().replace("\\", "/")
        if "/horizontal/" in path_str:
            return target_is_long
        if "/vertical/" in path_str:
            return not target_is_long
        if "horizontal" in path_str or "landscape" in path_str:
            return target_is_long
        if "vertical" in path_str or "portrait" in path_str:
            return not target_is_long
        return False

    if not isinstance(asset, dict):
        return False

    w = int(asset.get("width") or 0)
    h = int(asset.get("height") or 0)

    # 1. Concrete dimensions take precedence over folder/path metadata
    if w > 0 and h > 0:
        if target_is_long:
            return w >= h
        else:
            return h >= w

    # 2. Explicit aspect_ratio metadata
    ar = str(asset.get("aspect_ratio") or "").lower().strip()
    if ar in ("16:9", "horizontal", "landscape"):
        return target_is_long
    if ar in ("9:16", "vertical", "portrait"):
        return not target_is_long

    # 3. Explicit orientation attribute
    orient = str(asset.get("orientation") or "").lower().strip()
    if orient in ("horizontal", "landscape", "16:9"):
        return target_is_long
    if orient in ("vertical", "portrait", "9:16"):
        return not target_is_long

    # 4. Folder / path structure
    path_str = str(asset.get("path") or "").lower().replace("\\", "/")
    if "/horizontal/" in path_str:
        return target_is_long
    if "/vertical/" in path_str:
        return not target_is_long
    if "horizontal" in path_str or "landscape" in path_str:
        return target_is_long
    if "vertical" in path_str or "portrait" in path_str:
        return not target_is_long

    # Fail closed on unverified/unknown orientation
    return False


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

    target_ct = "long" if content_type == "long" else "short"
    deity_videos = [v for v in repo_videos if is_matching_orientation(v, target_ct)]

    if content_type == "long":
        preferred_images = [img for img in repo_images if is_matching_orientation(img, "long")]
        eligible_images = preferred_images if preferred_images else repo_images
    else:
        eligible_images = repo_images

    # When genuine deity images exist on disk but listed videos do not (e.g. sparse checkout),
    # cleanly fall back to the available genuine images on disk.
    disk_videos = [v for v in deity_videos if Path(v.get("path", "")).exists()]
    disk_images = [img for img in repo_images if Path(img.get("path", "")).exists()]
    if disk_images and not disk_videos and deity_videos:
        deity_videos = []

    if not deity_videos and not eligible_images:
        raise ValueError(f"No visual assets found in repository for deity '{deity_key}'")

    if not deity_videos and eligible_images:
        import sys
        print(f"[ASSET NOTICE] Video coverage unavailable for deity '{deity_key}'. Falling back to local deity images.", file=sys.stderr)

    # Videos first, then images as secondary/fallback
    pool = deity_videos + eligible_images

    timeline: list[dict[str, Any]] = []
    current_time = 0.0
    scene_idx = 1
    pool_len = len(pool)

    # Canonical retention segment durations (4s to 8s, 8 segments summing to 45.0s for shorts)
    if content_type == "long":
        segment_durations = [5.0, 6.0, 5.5, 7.0, 6.0, 5.0, 6.5, 8.0]
    else:
        segment_durations = [5.0, 6.0, 4.0, 7.0, 5.0, 6.0, 4.0, 8.0]

    while current_time < target_duration:
        asset_item = pool[(scene_idx - 1) % pool_len]
        atype = asset_item.get("type", "image")

        if atype == "video" and content_type == "long":
            clip_dur = float(asset_item.get("duration", 8.0) or 8.0)
            seg_dur = min(max(5.0, clip_dur), 15.0)
        else:
            seg_dur = segment_durations[(scene_idx - 1) % len(segment_durations)]

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
    allow_online_fallback: bool = False,
    content_type: str = "short",
) -> list[dict[str, Any]]:
    """
    Select scene-aware visual assets for scene_scripts strictly from repository deity assets.
    Enforces Video-First Priority:
      Priority 1: Videos are the primary visual source. Used for majority/all scenes where available.
      Priority 2: Images are secondary source when suitable videos are unavailable or exhausted.
      Priority 3: Strict deity isolation (never borrowing from other deities).
      Priority 4: Fail closed if deity has no visual assets (no external synthesis in production).

    Returns a list of scene asset decision dicts.
    """
    deities = manifest.get("deities", {})
    target_deity_assets = deities.get(deity_key, {"images": [], "videos": []})

    repo_images = list(target_deity_assets.get("images", []))
    repo_videos = list(target_deity_assets.get("videos", []))

    target_ct = "long" if content_type == "long" else "short"
    deity_videos = [v for v in repo_videos if is_matching_orientation(v, target_ct)]

    if content_type == "long":
        preferred_images = [img for img in repo_images if is_matching_orientation(img, "long")]
        eligible_images = preferred_images if preferred_images else repo_images
    else:
        eligible_images = repo_images

    # When genuine deity images exist on disk but listed videos do not (e.g. sparse checkout),
    # cleanly fall back to the available genuine images on disk.
    disk_videos = [v for v in deity_videos if Path(v.get("path", "")).exists()]
    disk_images = [img for img in repo_images if Path(img.get("path", "")).exists()]
    if disk_images and not disk_videos and deity_videos:
        deity_videos = []

    has_videos = bool(deity_videos)
    has_images = bool(eligible_images)

    if not has_videos and has_images:
        import sys
        print(
            f"[ASSET NOTICE] Video coverage unavailable for deity '{deity_key}'. "
            f"Falling back to local deity images.",
            file=sys.stderr,
        )

    if not has_videos and not has_images:
        if not allow_online_fallback:
            raise RuntimeError(
                f"Missing scene asset: No repository assets found for deity '{deity_key}' "
                f"and online fallback is disabled."
            )

    scene_plan: list[dict[str, Any]] = []
    used_asset_paths: set[str] = set()

    for item in scene_scripts:
        scene_num = item["scene"]
        keywords = extract_scene_semantic_keywords(item)

        selected_asset = None
        selection_source = "repository"
        selection_reason = ""
        semantic_confidence = "NONE"
        semantic_match_found = False
        matched_keywords: list[str] = []

        if has_videos:
            unused_videos = [v for v in deity_videos if v.get("path") not in used_asset_paths]
            best_candidate = None
            best_score = -1
            best_matched = []
            best_is_ver = False
            for cand in unused_videos:
                score, matched = _get_semantic_match_details(cand, keywords)
                is_ver = (cand.get("verification_status") == "verified_visual") if isinstance(cand, dict) else False
                if score > best_score or (score == best_score and score > 0 and is_ver and not best_is_ver):
                    best_score = score
                    best_candidate = cand
                    best_matched = matched
                    best_is_ver = is_ver

            if best_candidate and best_score > 0:
                selected_asset = best_candidate
                semantic_match_found = True
                matched_keywords = best_matched
                semantic_confidence = "HIGH" if best_score >= 2 else "MEDIUM"
                ver_str = " [VERIFIED]" if best_is_ver else ""
                selection_reason = (
                    f"Video semantic match{ver_str} (score={best_score}, matched={best_matched}) "
                    f"in repository deity assets for '{deity_key}'"
                )
            elif unused_videos:
                selected_asset = unused_videos[0]
                semantic_confidence = "NONE"
                semantic_match_found = False
                sample_kws = keywords[:3] if keywords else ["general"]
                selection_reason = (
                    f"Deity repository video asset for '{deity_key}' (scene #{scene_num}). "
                    f"Missing specific semantic asset (video) for keywords {sample_kws}."
                )
            else:
                unused_images = [img for img in eligible_images if img.get("path") not in used_asset_paths]
                if unused_images:
                    img_best_cand = None
                    img_best_score = -1
                    img_best_matched = []
                    img_best_is_ver = False
                    for cand in unused_images:
                        score, matched = _get_semantic_match_details(cand, keywords)
                        is_ver = (cand.get("verification_status") == "verified_visual") if isinstance(cand, dict) else False
                        if score > img_best_score or (score == img_best_score and score > 0 and is_ver and not img_best_is_ver):
                            img_best_score = score
                            img_best_cand = cand
                            img_best_matched = matched
                            img_best_is_ver = is_ver

                    if img_best_cand and img_best_score > 0:
                        selected_asset = img_best_cand
                        semantic_match_found = True
                        matched_keywords = img_best_matched
                        semantic_confidence = "HIGH" if img_best_score >= 2 else "MEDIUM"
                        ver_str = " [VERIFIED]" if img_best_is_ver else ""
                        selection_reason = (
                            f"Secondary image semantic match{ver_str} (score={img_best_score}, matched={img_best_matched}) "
                            f"for '{deity_key}' (videos exhausted)"
                        )
                    else:
                        selected_asset = unused_images[0]
                        semantic_confidence = "NONE"
                        semantic_match_found = False
                        sample_kws = keywords[:3] if keywords else ["general"]
                        selection_reason = (
                            f"Secondary image asset fallback for '{deity_key}' (scene #{scene_num}). "
                            f"Videos exhausted and missing specific semantic asset (image) for keywords {sample_kws}."
                        )
                else:
                    idx = (scene_num - 1) % len(deity_videos)
                    selected_asset = deity_videos[idx]
                    semantic_confidence = "NONE"
                    semantic_match_found = False
                    sample_kws = keywords[:3] if keywords else ["general"]
                    selection_reason = (
                        f"Deity repository video loop #{idx+1} for '{deity_key}' (scene #{scene_num}). "
                        f"Missing specific semantic asset (video loop) for keywords {sample_kws}."
                    )

        elif has_images:
            unused_images = [img for img in eligible_images if img.get("path") not in used_asset_paths]
            img_pool = unused_images if unused_images else eligible_images
            best_candidate = None
            best_score = -1
            best_matched = []
            best_is_ver = False
            for cand in img_pool:
                score, matched = _get_semantic_match_details(cand, keywords)
                is_ver = (cand.get("verification_status") == "verified_visual") if isinstance(cand, dict) else False
                if score > best_score or (score == best_score and score > 0 and is_ver and not best_is_ver):
                    best_score = score
                    best_candidate = cand
                    best_matched = matched
                    best_is_ver = is_ver

            if best_candidate and best_score > 0:
                selected_asset = best_candidate
                semantic_match_found = True
                matched_keywords = best_matched
                semantic_confidence = "HIGH" if best_score >= 2 else "MEDIUM"
                ver_str = " [VERIFIED]" if best_is_ver else ""
                selection_reason = (
                    f"Semantic match{ver_str} (score={best_score}, matched={best_matched}) "
                    f"in repository deity images for '{deity_key}'"
                )
            elif unused_images:
                selected_asset = unused_images[0]
                semantic_confidence = "NONE"
                semantic_match_found = False
                sample_kws = keywords[:3] if keywords else ["general"]
                selection_reason = (
                    f"Deity repository image fallback for '{deity_key}' (scene #{scene_num}). "
                    f"Missing specific semantic asset for keywords {sample_kws}."
                )
            else:
                idx = (scene_num - 1) % len(eligible_images)
                selected_asset = eligible_images[idx]
                semantic_confidence = "NONE"
                semantic_match_found = False
                sample_kws = keywords[:3] if keywords else ["general"]
                selection_reason = (
                    f"Deity repository image loop #{idx+1} for '{deity_key}' (scene #{scene_num}). "
                    f"Missing specific semantic asset (image loop) for keywords {sample_kws}."
                )

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

        if selected_asset.get("path"):
            used_asset_paths.add(selected_asset["path"])

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
    Select scene-aware landscape assets strictly from `assets/gods_landscape_long_video/<deity_key>/`
    and `assets/gods_processed/<deity_key>/horizontal/`.
    Enforces Video-First Priority:
      Priority 1: Landscape videos (width >= height) are primary source.
      Priority 2: Landscape images (width >= height) when videos are unavailable or exhausted.
      Priority 3: Strict deity isolation.
      Priority 4: Reject portrait assets.
    """
    if manifest is None:
        from src.assets.manifest import load_landscape_asset_manifest
        manifest = load_landscape_asset_manifest(gods_dir=gods_dir)

    deities = manifest.get("deities", {})
    target_deity_assets = deities.get(deity_key, {"images": [], "videos": []})
    repo_images = [img for img in target_deity_assets.get("images", []) if is_matching_orientation(img, "long")]
    repo_videos = [vid for vid in target_deity_assets.get("videos", []) if is_matching_orientation(vid, "long")]

    if not repo_images and not repo_videos:
        folder_path = Path(gods_dir) / deity_key
        raise ValueError(
            f"No valid landscape visual assets found for deity '{deity_key}' in {folder_path}. "
            f"Fallback to portrait assets/gods/ is strictly prohibited."
        )

    has_videos = bool(repo_videos)
    has_images = bool(repo_images)

    import sys
    if not has_videos and has_images:
        print(
            f"[ASSET NOTICE] Video coverage unavailable for deity '{deity_key}'. "
            f"Falling back to local deity images.",
            file=sys.stderr,
        )

    print(
        f"  [LANDSCAPE ASSET SELECTION] Deity: '{deity_key}' | Source folder: {Path(gods_dir)/deity_key} | "
        f"Valid landscape assets: {len(repo_videos) + len(repo_images)} (Videos: {len(repo_videos)}, Images: {len(repo_images)})",
        file=sys.stderr,
    )

    scene_plan: list[dict[str, Any]] = []
    used_asset_paths: set[str] = set()

    for item in scene_scripts:
        scene_num = item["scene"]
        keywords = extract_scene_semantic_keywords(item)

        selected_asset = None
        selection_reason = ""
        semantic_confidence = "NONE"
        semantic_match_found = False
        matched_keywords: list[str] = []

        if has_videos:
            unused_videos = [v for v in repo_videos if v.get("path") not in used_asset_paths]
            best_candidate = None
            best_score = -1
            best_matched = []
            best_is_ver = False
            for candidate in unused_videos:
                score, matched = _get_semantic_match_details(candidate, keywords)
                is_ver = (candidate.get("verification_status") == "verified_visual") if isinstance(candidate, dict) else False
                if score > best_score or (score == best_score and score > 0 and is_ver and not best_is_ver):
                    best_score = score
                    best_candidate = candidate
                    best_matched = matched
                    best_is_ver = is_ver

            if best_candidate and best_score > 0:
                selected_asset = best_candidate
                semantic_match_found = True
                matched_keywords = best_matched
                semantic_confidence = "HIGH" if best_score >= 2 else "MEDIUM"
                verified_str = " [VERIFIED]" if best_is_ver else ""
                selection_reason = (
                    f"Landscape video semantic match{verified_str} (score={best_score}, matched={best_matched}) for '{deity_key}'"
                )
            elif unused_videos:
                selected_asset = unused_videos[0]
                semantic_match_found = False
                semantic_confidence = "NONE"
                sample_kws = keywords[:3] if keywords else ["general"]
                selection_reason = (
                    f"Landscape video #{scene_num} for '{deity_key}'. "
                    f"Missing specific semantic asset (video) for keywords {sample_kws}."
                )
            else:
                # Videos exhausted: use unused images
                unused_images = [img for img in repo_images if img.get("path") not in used_asset_paths]
                if unused_images:
                    img_best_cand = None
                    img_best_score = -1
                    img_best_matched = []
                    img_best_is_ver = False
                    for candidate in unused_images:
                        score, matched = _get_semantic_match_details(candidate, keywords)
                        is_ver = (candidate.get("verification_status") == "verified_visual") if isinstance(candidate, dict) else False
                        if score > img_best_score or (score == img_best_score and score > 0 and is_ver and not img_best_is_ver):
                            img_best_score = score
                            img_best_cand = candidate
                            img_best_matched = matched
                            img_best_is_ver = is_ver

                    if img_best_cand and img_best_score > 0:
                        selected_asset = img_best_cand
                        semantic_match_found = True
                        matched_keywords = img_best_matched
                        semantic_confidence = "HIGH" if img_best_score >= 2 else "MEDIUM"
                        verified_str = " [VERIFIED]" if img_best_is_ver else ""
                        selection_reason = (
                            f"Landscape secondary image semantic match{verified_str} (score={img_best_score}, matched={img_best_matched}) for '{deity_key}'"
                        )
                    else:
                        selected_asset = unused_images[0]
                        semantic_match_found = False
                        semantic_confidence = "NONE"
                        sample_kws = keywords[:3] if keywords else ["general"]
                        selection_reason = (
                            f"Landscape secondary image #{scene_num} for '{deity_key}'. "
                            f"Videos exhausted and missing specific semantic asset (image) for keywords {sample_kws}."
                        )
                else:
                    idx = (scene_num - 1) % len(repo_videos)
                    selected_asset = repo_videos[idx]
                    semantic_match_found = False
                    semantic_confidence = "NONE"
                    sample_kws = keywords[:3] if keywords else ["general"]
                    selection_reason = (
                        f"Landscape video loop #{idx+1} for '{deity_key}' (scene #{scene_num}). "
                        f"Missing specific semantic asset (video loop) for keywords {sample_kws}."
                    )

        elif has_images:
            unused_images = [img for img in repo_images if img.get("path") not in used_asset_paths]
            img_pool = unused_images if unused_images else repo_images
            best_candidate = None
            best_score = -1
            best_matched = []
            best_is_ver = False
            for candidate in img_pool:
                score, matched = _get_semantic_match_details(candidate, keywords)
                is_ver = (candidate.get("verification_status") == "verified_visual") if isinstance(candidate, dict) else False
                if score > best_score or (score == best_score and score > 0 and is_ver and not best_is_ver):
                    best_score = score
                    best_candidate = candidate
                    best_matched = matched
                    best_is_ver = is_ver

            if best_candidate and best_score > 0:
                selected_asset = best_candidate
                semantic_match_found = True
                matched_keywords = best_matched
                semantic_confidence = "HIGH" if best_score >= 2 else "MEDIUM"
                verified_str = " [VERIFIED]" if best_is_ver else ""
                selection_reason = (
                    f"Landscape image semantic match{verified_str} (score={best_score}, matched={best_matched}) for '{deity_key}'"
                )
            elif unused_images:
                selected_asset = unused_images[0]
                semantic_match_found = False
                semantic_confidence = "NONE"
                sample_kws = keywords[:3] if keywords else ["general"]
                selection_reason = (
                    f"Landscape image #{scene_num} for '{deity_key}'. "
                    f"Missing specific semantic asset for keywords {sample_kws}."
                )
            else:
                idx = (scene_num - 1) % len(repo_images)
                selected_asset = repo_images[idx]
                semantic_match_found = False
                semantic_confidence = "NONE"
                sample_kws = keywords[:3] if keywords else ["general"]
                selection_reason = (
                    f"Landscape image loop #{idx+1} for '{deity_key}' (scene #{scene_num}). "
                    f"Missing specific semantic asset (image loop) for keywords {sample_kws}."
                )

        if selected_asset.get("path"):
            used_asset_paths.add(selected_asset["path"])

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
            "matched_keywords": matched_keywords,
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
    strictly from `assets/gods_landscape_long_video/<deity_key>/` and
    `assets/gods_processed/<deity_key>/horizontal/`.
    Enforces Video-First Priority: Landscape videos used first up to target duration.
    """
    if manifest is None:
        from src.assets.manifest import load_landscape_asset_manifest
        manifest = load_landscape_asset_manifest(gods_dir=gods_dir)

    deities = manifest.get("deities", {})
    target_deity_assets = deities.get(deity_key, {"images": [], "videos": []})
    repo_images = [img for img in target_deity_assets.get("images", []) if is_matching_orientation(img, "long")]
    repo_videos = [vid for vid in target_deity_assets.get("videos", []) if is_matching_orientation(vid, "long")]

    if not repo_images and not repo_videos:
        folder_path = Path(gods_dir) / deity_key
        raise ValueError(
            f"No valid landscape visual assets found for deity '{deity_key}' in {folder_path}. "
            f"Fallback to portrait assets/gods/ is strictly prohibited."
        )

    import sys
    if not repo_videos and repo_images:
        print(
            f"[ASSET NOTICE] Video coverage unavailable for deity '{deity_key}'. "
            f"Falling back to local deity images.",
            file=sys.stderr,
        )

    print(
        f"  [LANDSCAPE TIMELINE] Deity: '{deity_key}' | Folder: {Path(gods_dir)/deity_key} | "
        f"Videos: {len(repo_videos)}, Images: {len(repo_images)}",
        file=sys.stderr,
    )

    # Videos first, then images
    pool = repo_videos + repo_images

    timeline: list[dict[str, Any]] = []
    current_time = 0.0
    scene_idx = 1
    pool_len = len(pool)
    image_durations = [5.0, 6.0, 5.5, 7.0, 6.0, 5.0, 6.5, 8.0]

    while current_time < target_duration:
        asset_item = pool[(scene_idx - 1) % pool_len]
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
