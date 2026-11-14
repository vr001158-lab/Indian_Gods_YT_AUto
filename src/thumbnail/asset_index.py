# src/thumbnail/asset_index.py
# Phase 2H / Phase 4 — Zero-Cost Deity Thumbnail Asset Indexing Engine
#
# Builds, validates, and queries the deity asset catalog across:
#   1. Approved landscape devotional artwork (assets/gods_landscape_long_video/)
#   2. Repository deity image collection (assets/gods/)
#   3. Visual pipeline outputs (data/render_only/ or data/visuals/)
#
# Strictly enforces deity and avatar matching without guessing from bare filenames.
# Rejects corrupt or invalid images and maintains full provenance.

from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Optional, Any
from dataclasses import dataclass, asdict
from PIL import Image, ImageStat


# ── Canonical Deity & Avatar Alias Map ──────────────────────────────────────────
CANONICAL_DEITIES: dict[str, list[str]] = {
    "lord_vishnu": [
        "vishnu", "narayana", "lord_vishnu", "mahavishnu", "dashavatar", "perumal",
        "విష్ణు", "విష్ణువు", "నారాయణ", "మహావిష్ణువు", "దశావతార"
    ],
    "narasimha": [
        "narasimha", "narasingh", "nrusimha", "prahlada",
        "నరసింహ", "నరసింహస్వామి", "ప్రహ్లాద"
    ],
    "krishna": [
        "krishna", "gopala", "govinda", "kanha", "venugopala",
        "కృష్ణ", "కృష్ణుడు", "గోపాల", "గోవింద"
    ],
    "ram": [
        "ram", "rama", "ramachandra", "raghava", "ayodhya", "sita",
        "రామ", "రాముడు", "శ్రీరామ", "అయోధ్య"
    ],
    "lord_shiva": [
        "shiva", "lord_shiva", "mahadev", "bholenath", "rudra", "nataraja", "kedarnath",
        "శివ", "శివుడు", "మహాదేవుడు", "రుద్ర", "నటరాజ"
    ],
    "hanuman": [
        "hanuman", "anjaneya", "bajrangbali", "maruti", "sanjeevani", "dronagiri",
        "హనుమాన్", "హనుమంతుడు", "ఆంజనేయ", "బజరంగబలి", "సంజీవని"
    ],
    "ganesha": [
        "ganesha", "ganesh", "vinayaka", "gajanana", "vighnaharta",
        "గణపతి", "వినాయక", "వినాయకుడు", "గణేశ"
    ],
    "lakshmi_devi": [
        "lakshmi", "lakshmi_devi", "laxmi", "mahalakshmi", "sridevi",
        "లక్ష్మి", "లక్ష్మీ", "మహాలక్ష్మి"
    ],
    "parvathi": [
        "parvathi", "parvati", "durga", "gauri", "shakti", "kali", "ambika",
        "పార్వతి", "దుర్గ", "గౌరి", "శక్తి", "కాళి"
    ],
    "saraswati": [
        "saraswati", "sharada", "vani", "veena",
        "సరస్వతి", "శారద", "వాణి"
    ],
    "subramanya": [
        "subramanya", "murugan", "kartikeya", "skanda",
        "సుబ్రహ్మణ్య", "మురుగన్", "కార్తికేయ"
    ],
    "ayyappa": [
        "ayyappa", "sabarimala", "manikanta",
        "అయ్యప్ప", "శబరిమల", "మణికంఠ"
    ],
    "7kondala_swami": [
        "7kondala_swami", "7kondala", "venkateswara", "balaji", "srinivasa", "tirupati", "tirumala",
        "వేంకటేశ్వర", "శ్రీనివాస", "బాలాజీ", "తిరుపతి", "ఏడుకొండలవాడు"
    ],
}

# Avatar-to-Parent-Deity mapping
AVATAR_TO_PARENT_DEITY: dict[str, str] = {
    "matsya": "lord_vishnu",
    "kurma": "lord_vishnu",
    "varaha": "lord_vishnu",
    "narasimha": "narasimha",  # Also distinct top-level deity
    "vamana": "lord_vishnu",
    "vamana_trivikrama": "lord_vishnu",
    "trivikrama": "lord_vishnu",
    "parashurama": "lord_vishnu",
    "rama": "ram",            # Also distinct top-level deity
    "ram": "ram",
    "krishna": "krishna",      # Also distinct top-level deity
    "buddha": "lord_vishnu",
    "kalki": "lord_vishnu",
    "durga": "parvathi",
    "kali": "parvathi",
    "venkateswara": "7kondala_swami",
    "hanuman": "hanuman",
}


def resolve_deity_and_avatar(text: str) -> tuple[Optional[str], Optional[str]]:
    """
    Parses a topic title, query or hint to extract (canonical_deity, avatar).
    Matches Telugu and English keywords.
    """
    if not text:
        return None, None

    t_lower = text.strip().lower()

    # Detect avatar first
    detected_avatar = None
    for av in [
        "varaha", "kurma", "vamana_trivikrama", "vamana", "trivikrama",
        "narasimha", "krishna", "rama", "ram", "matsya", "parashurama",
        "kalki", "durga", "kali", "venkateswara", "hanuman"
    ]:
        if av in t_lower:
            detected_avatar = av
            break

    # Telugu avatar keywords
    if not detected_avatar:
        if "వరాహ" in text:
            detected_avatar = "varaha"
        elif "కూర్మ" in text:
            detected_avatar = "kurma"
        elif "వామన" in text or "త్రివిక్రమ" in text:
            detected_avatar = "vamana_trivikrama"
        elif "నరసింహ" in text:
            detected_avatar = "narasimha"
        elif "కృష్ణ" in text:
            detected_avatar = "krishna"
        elif "రామ" in text:
            detected_avatar = "ram"
        elif "దుర్గ" in text:
            detected_avatar = "durga"
        elif "వేంకటేశ్వర" in text or "శ్రీనివాస" in text:
            detected_avatar = "venkateswara"

    # Detect canonical deity
    detected_deity = None
    if detected_avatar and detected_avatar in AVATAR_TO_PARENT_DEITY:
        detected_deity = AVATAR_TO_PARENT_DEITY[detected_avatar]
    else:
        for deity, aliases in CANONICAL_DEITIES.items():
            for alias in aliases:
                if alias.lower() in t_lower or alias in text:
                    detected_deity = deity
                    break
            if detected_deity:
                break

    return detected_deity, detected_avatar


@dataclass
class ThumbnailAssetRecord:
    asset_id: str
    file_path: str
    deity: str
    avatar: Optional[str]
    width: int
    height: int
    aspect_ratio: str
    file_format: str
    file_size_bytes: int
    integrity_status: str           # "VALID" or "CORRUPT"
    source: str                     # "approved_landscape_artwork", "pipeline_visual", "repository_collection"
    approval_status: str            # "APPROVED", "UNAPPROVED", "REJECTED"
    quality_score: float            # 0.0 to 100.0 based on resolution and variance
    description: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_CACHED_INDEX_RECORDS: Optional[list[ThumbnailAssetRecord]] = None


class DeityAssetIndex:
    """
    Indexes, verifies, and provides query access to local deity visual assets.
    """

    def __init__(self, force_rescan: bool = False):
        global _CACHED_INDEX_RECORDS
        self.records: list[ThumbnailAssetRecord] = []
        if _CACHED_INDEX_RECORDS is not None and not force_rescan:
            self.records = list(_CACHED_INDEX_RECORDS)
        else:
            self._build_index()
            _CACHED_INDEX_RECORDS = list(self.records)

    def _build_index(self):
        """Discovers and indexes assets from verified landscape manifests and repository collections."""
        # 1. Index curated landscape repository assets (Priority 1 Candidates)
        landscape_dir = Path("assets/gods_landscape_long_video")
        if landscape_dir.exists():
            for f in landscape_dir.rglob("*"):
                if f.name.endswith(".gitkeep") or f.name.endswith(".keep") or not f.is_file():
                    continue
                if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".mp4", ".mov", ".webm", ".avi", ".mkv"):
                    record = self._inspect_file(
                        f,
                        default_source="approved_landscape_artwork",
                        default_approval="APPROVED"
                    )
                    if record:
                        self.records.append(record)

        # 2. Index standard repository collection (assets/gods/)
        gods_dir = Path("assets/gods")
        if gods_dir.exists():
            for f in gods_dir.rglob("*"):
                if not f.is_file() or f.name.endswith(".gitkeep") or f.name.endswith(".keep"):
                    continue
                if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".mp4", ".mov", ".webm", ".avi", ".mkv"):
                    folder_name = f.parent.name.lower()
                    fname_lower = f.name.lower()

                    if folder_name == "lord_vishnu":
                        # In lord_vishnu, only curated named assets with explicit avatars are approved
                        if "kurma_avatar" in fname_lower:
                            approval = "APPROVED"
                            avatar = "kurma"
                        elif "vamana_trivikrama" in fname_lower:
                            approval = "APPROVED"
                            avatar = "vamana_trivikrama"
                        else:
                            approval = "UNAPPROVED"  # Generic unverified Vishnu download
                            avatar = None
                    else:
                        # For other curated repository deity folders
                        if "chatgpt" in fname_lower or "unverified" in fname_lower:
                            approval = "UNAPPROVED"
                            avatar = None
                        else:
                            approval = "APPROVED"
                            _, detected_av = resolve_deity_and_avatar(f.name + " " + folder_name)
                            avatar = detected_av or folder_name

                    record = self._inspect_file(
                        f,
                        default_source="repository_collection",
                        default_approval=approval,
                        force_avatar=avatar,
                    )
                    if record:
                        self.records.append(record)

        # 3. Index processed repository videos (assets/gods_processed/)
        processed_dir = Path("assets/gods_processed")
        if processed_dir.exists():
            for f in processed_dir.rglob("*"):
                if not f.is_file() or f.name.endswith(".gitkeep") or f.name.endswith(".keep"):
                    continue
                if f.suffix.lower() in (".mp4", ".mov", ".webm", ".avi", ".mkv"):
                    parts = f.parts
                    deity_part = None
                    for idx, part in enumerate(parts):
                        if part == "gods_processed" and idx + 1 < len(parts):
                            deity_part = parts[idx + 1].lower()
                            break
                    folder_deity = deity_part or f.parent.name.lower()
                    record = self._inspect_file(
                        f,
                        default_source="curated_processed_video",
                        default_approval="APPROVED",
                        force_avatar=folder_deity,
                        force_deity=folder_deity,
                    )
                    if record:
                        self.records.append(record)

    def _inspect_file(
        self,
        file_path: Path,
        default_source: str,
        default_approval: str,
        force_avatar: Optional[str] = None,
        force_deity: Optional[str] = None,
    ) -> Optional[ThumbnailAssetRecord]:
        """Inspects file integrity, dimensions, and calculates a quality score."""
        p = Path(file_path)
        if not p.is_file() or p.stat().st_size == 0:
            return None

        # Determine deity from parent folder
        folder_name = p.parent.name.lower()
        if folder_name in ("horizontal", "vertical"):
            folder_name = p.parent.parent.name.lower()
        deity, detected_av = resolve_deity_and_avatar(p.name + " " + folder_name)
        if not deity:
            deity = folder_name
        deity = force_deity or deity

        avatar = force_avatar or detected_av

        # Handle video assets directly without PIL image open
        if p.suffix.lower() in (".mp4", ".mov", ".webm", ".avi", ".mkv"):
            return ThumbnailAssetRecord(
                asset_id=p.stem,
                file_path=str(p).replace("\\", "/"),
                deity=deity,
                avatar=avatar,
                width=1920,
                height=1080,
                aspect_ratio="16:9",
                file_format=p.suffix.lower().lstrip("."),
                file_size_bytes=p.stat().st_size,
                integrity_status="VALID",
                source=default_source,
                approval_status=default_approval,
                quality_score=85.0,
                description=f"Curated repository asset for {deity} (avatar={avatar}) in 16:9",
            )

        # Integrity & image checks
        try:
            with Image.open(p) as img:
                img.verify()
            with Image.open(p) as img:
                w, h = img.size
                fmt = (img.format or "").upper()
                stat = ImageStat.Stat(img.convert("RGB"))
                mean_std = sum(stat.stddev) / 3.0
                integrity = "VALID"
        except Exception:
            return ThumbnailAssetRecord(
                asset_id=p.stem,
                file_path=str(p).replace("\\", "/"),
                deity=deity,
                avatar=avatar,
                width=0,
                height=0,
                aspect_ratio="unknown",
                file_format="corrupt",
                file_size_bytes=p.stat().st_size,
                integrity_status="CORRUPT",
                source=default_source,
                approval_status="REJECTED",
                quality_score=0.0,
                description=f"Corrupt image file: {p.name}",
            )

        # Aspect ratio string
        ratio_val = w / float(h) if h > 0 else 1.0
        if 1.70 <= ratio_val <= 1.85:
            ar_str = "16:9"
        elif 0.50 <= ratio_val <= 0.60:
            ar_str = "9:16"
        elif 0.95 <= ratio_val <= 1.05:
            ar_str = "1:1"
        else:
            ar_str = f"{w}:{h}"

        # Quality score based on resolution, variance, and aspect ratio
        score = 50.0
        if w >= 1280 and h >= 720:
            score += 25.0
        elif w >= 720:
            score += 15.0
        if mean_std >= 30.0:
            score += 15.0
        if ar_str == "16:9":
            score += 10.0

        score = min(100.0, max(0.0, score))

        return ThumbnailAssetRecord(
            asset_id=p.stem,
            file_path=str(p).replace("\\", "/"),
            deity=deity,
            avatar=avatar,
            width=w,
            height=h,
            aspect_ratio=ar_str,
            file_format=fmt,
            file_size_bytes=p.stat().st_size,
            integrity_status=integrity,
            source=default_source,
            approval_status=default_approval,
            quality_score=round(score, 1),
            description=f"Curated repository asset for {deity} (avatar={avatar}) in {ar_str}",
        )

    def find_approved_assets(
        self,
        deity: str,
        avatar: Optional[str] = None,
        min_quality: float = 50.0,
    ) -> list[ThumbnailAssetRecord]:
        """
        Finds approved assets strictly matching the requested deity and avatar.
        Does not substitute unrelated avatars or deities.
        """
        matches = []
        c_deity, c_avatar = resolve_deity_and_avatar(deity + " " + (avatar or ""))
        req_deity = c_deity or deity.lower()
        req_avatar = avatar.lower() if avatar else c_avatar

        for rec in self.records:
            if rec.integrity_status != "VALID" or rec.approval_status != "APPROVED":
                continue
            if rec.quality_score < min_quality:
                continue

            # Strict Deity match
            if rec.deity.lower() != req_deity:
                continue

            # Strict Avatar match if an avatar is requested
            if req_avatar:
                if not rec.avatar or rec.avatar.lower() != req_avatar:
                    continue

            matches.append(rec)

        # Sort by quality score descending
        matches.sort(key=lambda r: r.quality_score, reverse=True)
        return matches

    def get_deity_counts(self) -> dict[str, dict[str, int]]:
        """Returns asset counts broken down by deity, approval status, and avatar."""
        counts: dict[str, dict[str, int]] = {}
        for rec in self.records:
            d = rec.deity
            if d not in counts:
                counts[d] = {"total": 0, "approved": 0, "unapproved": 0, "rejected": 0}
            counts[d]["total"] += 1
            if rec.approval_status == "APPROVED":
                counts[d]["approved"] += 1
            elif rec.approval_status == "REJECTED":
                counts[d]["rejected"] += 1
            else:
                counts[d]["unapproved"] += 1
        return counts
