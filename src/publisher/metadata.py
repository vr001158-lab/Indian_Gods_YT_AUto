# src/publisher/metadata.py
# Phase 2K — Publisher Metadata Builder
#
# Constructs YouTube video metadata (title, description, tags, category)
# from the pipeline artifacts.  The caller supplies the QA result dict
# and optional overrides.  No credentials are handled here.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# YouTube category IDs — 29 = Nonprofits & Activism, 27 = Education, 22 = People & Blogs
CATEGORY_ID_EDUCATION = "27"
CATEGORY_ID_DEFAULT   = "22"

# Maximum lengths imposed by YouTube Data API
MAX_TITLE_LEN       = 100
MAX_DESCRIPTION_LEN = 5000
MAX_TAGS            = 500
MAX_TAG_LEN         = 500


def _load_json(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def build_video_metadata(qa: dict) -> dict:
    """
    Derive YouTube upload metadata from a passed QA result.

    Returns a dict with keys:
        title, description, tags, category_id, video_file, thumbnail_file, content_type
    """
    arts         = qa.get("artifacts", {})
    topic        = qa.get("selected_topic", "")
    score        = qa.get("score", 0)
    src          = qa.get("data_source", "")
    conf         = qa.get("confidence", "")
    content_type = qa.get("content_type", "short")

    # ── Script metadata ──────────────────────────────────────────────────────
    script_file = arts.get("script", "")
    script: dict = {}
    if script_file and Path(script_file).exists():
        script = _load_json(script_file)

    script_title = script.get("title", topic)
    narration    = script.get("narration", "")
    hook         = ""

    # ── Content brief metadata ───────────────────────────────────────────────
    brief_file = arts.get("content_brief", "")
    brief: dict = {}
    if brief_file and Path(brief_file).exists():
        brief = _load_json(brief_file)
    hook = brief.get("hook", "")

    # ── Title ────────────────────────────────────────────────────────────────
    # Use script creative title; fall back to canonical topic.
    title = (script_title or topic)[:MAX_TITLE_LEN]

    # ── Description ──────────────────────────────────────────────────────────
    channel_tagline = (
        "Divine Dharshanam Daily — Explore the stories, symbolism and wisdom "
        "of Indian mythology.\n\n"
    )
    hook_block = f"{hook}\n\n" if hook else ""
    narration_excerpt = narration[:800] + "..." if len(narration) > 800 else narration
    narration_block = f"{narration_excerpt}\n\n" if narration_excerpt else ""

    hashtag_shorts = " #Shorts" if content_type == "short" else ""
    disclaimer = (
        f"#IndianMythology #HinduDharma #DivineStories{hashtag_shorts}\n\n"
        "This video is created for educational and devotional purposes."
    )
    description = (
        channel_tagline + hook_block + narration_block + disclaimer
    )[:MAX_DESCRIPTION_LEN]

    # ── Tags ─────────────────────────────────────────────────────────────────
    base_tags = [
        "Indian mythology",
        "Hindu gods",
        "divine stories",
        "Sanatan Dharma",
        "devotional",
        "spirituality",
        "Hinduism",
        "mythology explained",
    ]
    if content_type == "short":
        base_tags.append("Shorts")
    base_tags.append("Divine Dharshanam Daily")

    # Derive deity/topic-specific tags from content brief
    keywords = brief.get("seo_keywords", [])
    topic_words = [w.strip() for w in topic.replace(".", " ").split() if len(w.strip()) > 3]
    tags = list(dict.fromkeys(base_tags + keywords + topic_words))[:MAX_TAGS]

    # ── Video and thumbnail files ─────────────────────────────────────────────
    video_map_file = arts.get("video", "")
    video_file     = ""
    if video_map_file and Path(video_map_file).exists():
        vm = _load_json(video_map_file)
        video_file = vm.get("video_file", "")

    thumbnail_meta_file = arts.get("thumbnail", "")
    thumbnail_file      = ""
    if thumbnail_meta_file and Path(thumbnail_meta_file).exists():
        tm = _load_json(thumbnail_meta_file)
        created_at = tm.get("created_at", "")
        fmt        = tm.get("format", "png")
        thumb_dir  = Path(thumbnail_meta_file).parent
        candidate  = thumb_dir / f"thumbnail_{created_at}.{fmt}"
        if candidate.exists():
            thumbnail_file = str(candidate)
        else:
            # Newest fallback
            candidates = sorted([
                f for f in thumb_dir.glob("thumbnail_*.png")
                if "metadata" not in f.name
            ] + [
                f for f in thumb_dir.glob("thumbnail_*.jpg")
                if "metadata" not in f.name
            ])
            if candidates:
                thumbnail_file = str(candidates[-1])

    return {
        "title":          title,
        "description":    description,
        "tags":           tags,
        "category_id":    CATEGORY_ID_EDUCATION,
        "video_file":     video_file,
        "thumbnail_file": thumbnail_file,
        "content_type":   content_type,
    }
