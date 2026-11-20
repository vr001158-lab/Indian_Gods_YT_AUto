# src/assets/inventory.py
# Batch-Oriented Deity Asset Inventory, Duplicate Detection & Coverage Matrix Engine

from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional
from PIL import Image

from src.assets.approval_registry import get_trusted_registry, normalize_repo_path
from src.decision.weekday_deity import (
    DEITY_CANONICAL_ALIASES,
    WEEKDAY_DEITY_MAPPING,
)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi"}
ALL_VISUAL_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS

# Narrative/Deity keyword tokens to detect potential candidate deity from filename or tags
CANDIDATE_DEITY_TOKENS: dict[str, list[str]] = {
    "surya": ["surya", "suryadev", "aditya", "sun", "solar"],
    "kaal_bhairav": ["kaal_bhairav", "kalabhairav", "kalabhairava", "bhairav", "bhairava"],
    "chandra": ["chandra", "chandradeva", "chandra_deva", "soma", "moon"],
    "durga": ["durga", "durgama", "durga_devi", "mahishasura", "mardini", "sherawali"],
    "kali": ["kali", "mahakali", "bhadrakali", "kalika"],
    "subramanya": ["subramanya", "murugan", "kartikeya", "skanda", "vel"],
    "budha": ["budha", "budhadev", "budha_deva"],
    "vithal": ["vithal", "vitthal", "vithoba", "pandurang", "panduranga"],
    "brihaspati": ["brihaspati", "guru_brihaspati"],
    "santoshi_ma": ["santoshi", "santoshi_ma", "santoshima"],
    "annapurneshwari": ["annapurna", "annapurneshwari"],
    "shani": ["shani", "shanidev", "shaneshwara"],
    "ganesha": ["ganesha", "ganesh", "vinayaka", "gajanana", "vighnaharta", "ekadanta"],
    "hanuman": ["hanuman", "anjaneya", "bajrangbali", "maruti", "sanjeevani", "dronagiri"],
    "krishna": ["krishna", "gopala", "govinda", "kanha", "venugopala", "govardhan"],
    "lord_shiva": ["shiva", "mahadev", "bholenath", "rudra", "nataraja", "kedarnath", "shivling", "trishul"],
    "lord_vishnu": ["vishnu", "narayana", "mahavishnu", "dashavatar", "kurma", "vamana", "trivikrama", "matsya", "varaha"],
    "narasimha": ["narasimha", "narasingh", "prahlada", "stambha"],
    "parvathi": ["parvathi", "parvati", "gauri", "ambika"],
    "lakshmi_devi": ["lakshmi", "lakshmi_devi", "laxmi", "mahalakshmi", "sridevi"],
    "ram": ["ram", "rama", "ramachandra", "raghava", "ayodhya", "sita", "kodanda"],
    "ayyappa": ["ayyappa", "sabarimala", "manikanta"],
    "7Kondala_Swami": ["7kondala", "venkateswara", "balaji", "srinivasa", "tirupati", "tirumala"],
}


@dataclass
class AssetInventoryItem:
    rel_path: str
    file_type: str                         # "image" or "video"
    file_ext: str
    file_size_bytes: int
    sha256: str
    width: int
    height: int
    aspect_ratio: str                      # "9:16", "16:9", "1:1", or "W:H"
    duration_seconds: float                # 0.0 for images
    approval_status: str                   # "APPROVED" or "UNAPPROVED"
    approval_record_id: Optional[str]
    registry_deity: Optional[str]
    registry_avatar: Optional[str]
    candidate_deity: str                   # Human inspection classification candidate
    candidate_avatar: Optional[str]
    provenance_note: str
    is_broken: bool
    broken_reason: Optional[str]
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_file_sha256(file_path: Path, block_size: int = 65536) -> str:
    """Computes fast SHA-256 hash of file contents for duplicate detection."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(block_size), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def probe_video_metadata(video_path: Path) -> tuple[int, int, float, Optional[str]]:
    """Extracts width, height, and duration using ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=width,height,duration:format=duration",
            "-of", "json",
            str(video_path),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if res.returncode != 0:
            return 0, 0, 0.0, f"ffprobe error: {res.stderr[:200]}"
        data = json.loads(res.stdout)
        width, height, dur = 0, 0, 0.0
        for stream in data.get("streams", []):
            if "width" in stream and "height" in stream:
                width = int(stream["width"])
                height = int(stream["height"])
                if "duration" in stream and stream["duration"]:
                    try:
                        dur = float(stream["duration"])
                    except ValueError:
                        pass
                break
        if dur <= 0.0:
            fmt_dur = data.get("format", {}).get("duration")
            if fmt_dur:
                try:
                    dur = float(fmt_dur)
                except ValueError:
                    pass
        return width, height, round(dur, 2), None
    except Exception as exc:
        return 0, 0, 0.0, str(exc)


def classify_candidate_deity_and_avatar(file_path: Path) -> tuple[str, Optional[str]]:
    """
    Infers candidate deity and avatar for human visual review grouping ONLY.
    Never establishes approval.
    """
    path_str = str(file_path).replace("\\", "/").lower()
    stem = file_path.stem.lower()

    # 1. Check parent folder hierarchy
    parts = [p.lower() for p in file_path.parts]
    folder_candidate = None
    for folder in (
        "7kondala_swami", "ayyappa", "ganesha", "hanuman", "krishna",
        "lakshmi_devi", "lord_shiva", "lord_vishnu", "narasimha",
        "parvathi", "ram", "subramanya"
    ):
        if folder in parts:
            folder_candidate = folder
            break

    # 2. Check filename keywords for specific weekday or aspect deities
    # e.g. Kali, Durga, Chandra, Surya, etc. inside shared or parent folders
    detected_token_deity = None
    detected_avatar = None

    for d_key, tokens in CANDIDATE_DEITY_TOKENS.items():
        for tok in tokens:
            if tok in stem:
                detected_token_deity = d_key
                if d_key in ("kurma", "vamana", "trivikrama", "varaha", "matsya", "narasimha", "krishna", "ram"):
                    detected_avatar = d_key
                break
        if detected_token_deity:
            break

    # Check avatar tokens specifically
    for av in ("kurma", "vamana_trivikrama", "vamana", "trivikrama", "varaha", "matsya", "narasimha", "sanjeevani", "govardhan"):
        if av in stem:
            detected_avatar = av
            break

    final_deity = detected_token_deity or folder_candidate or "unclassified"
    return final_deity, detected_avatar


def inspect_single_asset(file_path: Path) -> AssetInventoryItem:
    """Inspects a single image or video asset file with fail-closed safety."""
    rel_p = str(file_path).replace("\\", "/")
    norm_p = normalize_repo_path(rel_p) or rel_p
    ext = file_path.suffix.lower()
    is_vid = ext in VIDEO_EXTENSIONS
    ftype = "video" if is_vid else "image"
    fsize = file_path.stat().st_size

    sha = ""
    try:
        sha = compute_file_sha256(file_path)
    except Exception:
        sha = f"unreadable_{fsize}"

    width, height, dur = 0, 0, 0.0
    is_broken = False
    broken_reason = None

    if fsize == 0:
        is_broken = True
        broken_reason = "File is zero bytes"
    elif is_vid:
        width, height, dur, v_err = probe_video_metadata(file_path)
        if v_err or width == 0 or height == 0:
            is_broken = True
            broken_reason = v_err or "Invalid video stream"
    else:
        # Pillow inspection
        try:
            with Image.open(file_path) as img:
                width, height = img.size
                img.verify()
        except Exception as exc:
            is_broken = True
            broken_reason = f"Corrupt image file: {exc}"

    # Aspect ratio
    ar_str = "unknown"
    if width > 0 and height > 0:
        ratio = width / float(height)
        if 0.50 <= ratio <= 0.65:
            ar_str = "9:16"
        elif 1.70 <= ratio <= 1.85:
            ar_str = "16:9"
        elif 0.95 <= ratio <= 1.05:
            ar_str = "1:1"
        elif 1.30 <= ratio <= 1.40:
            ar_str = "4:3"
        elif 0.70 <= ratio <= 0.80:
            ar_str = "3:4"
        else:
            ar_str = f"{width}:{height}"

    # Registry approval check
    registry = get_trusted_registry()
    rec = registry.get_approval_record(norm_p)
    if rec and rec.approval_status == "APPROVED":
        approval_status = "APPROVED"
        appr_id = rec.record_id
        reg_deity = rec.canonical_deity
        reg_avatar = rec.avatar
        provenance = rec.provenance
    else:
        approval_status = "UNAPPROVED"
        appr_id = None
        reg_deity = None
        reg_avatar = None
        if "data/visuals" in norm_p or "data/render_only" in norm_p:
            provenance = "Pipeline rendered scene output"
        elif "assets/gods_processed" in norm_p:
            provenance = "Repository processed video asset"
        elif "assets/gods_landscape_long_video" in norm_p:
            provenance = "Repository landscape asset collection"
        elif "assets/gods" in norm_p:
            provenance = "Repository collection asset"
        else:
            provenance = "Repository visual asset"

    cand_deity, cand_avatar = classify_candidate_deity_and_avatar(file_path)

    return AssetInventoryItem(
        rel_path=norm_p,
        file_type=ftype,
        file_ext=ext,
        file_size_bytes=fsize,
        sha256=sha,
        width=width,
        height=height,
        aspect_ratio=ar_str,
        duration_seconds=dur,
        approval_status=approval_status,
        approval_record_id=appr_id,
        registry_deity=reg_deity,
        registry_avatar=reg_avatar,
        candidate_deity=cand_deity,
        candidate_avatar=cand_avatar,
        provenance_note=provenance,
        is_broken=is_broken,
        broken_reason=broken_reason,
    )


def scan_all_visual_assets(
    roots: Optional[list[str]] = None,
    max_workers: int = 8,
) -> list[AssetInventoryItem]:
    """
    Scans all visual assets across specified repository directories in parallel.
    Performs duplicate detection by SHA-256 hash.
    """
    if roots is None:
        roots = [
            "assets/gods",
            "assets/gods_landscape_long_video",
            "assets/gods_processed",
            "assets/incoming",
            "data/visuals",
            "data/render_only",
        ]

    candidate_files: list[Path] = []
    for r in roots:
        rp = Path(r)
        if rp.exists():
            for f in rp.rglob("*"):
                if f.is_file() and f.suffix.lower() in ALL_VISUAL_EXTENSIONS:
                    candidate_files.append(f)

    # Sort for deterministic processing
    candidate_files.sort(key=lambda p: str(p).replace("\\", "/").lower())

    results: list[AssetInventoryItem] = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(inspect_single_asset, p): p for p in candidate_files}
        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception as exc:
                p = futures[fut]
                rel_p = str(p).replace("\\", "/")
                results.append(
                    AssetInventoryItem(
                        rel_path=rel_p,
                        file_type="unknown",
                        file_ext=p.suffix.lower(),
                        file_size_bytes=p.stat().st_size if p.exists() else 0,
                        sha256="",
                        width=0,
                        height=0,
                        aspect_ratio="unknown",
                        duration_seconds=0.0,
                        approval_status="UNAPPROVED",
                        approval_record_id=None,
                        registry_deity=None,
                        registry_avatar=None,
                        candidate_deity="unknown",
                        candidate_avatar=None,
                        provenance_note="Unprocessed error",
                        is_broken=True,
                        broken_reason=str(exc),
                    )
                )

    # Sort results by rel_path
    results.sort(key=lambda item: item.rel_path.lower())

    # Duplicate detection by SHA-256
    hash_seen: dict[str, str] = {}
    for item in results:
        if not item.sha256 or item.is_broken:
            continue
        if item.sha256 in hash_seen:
            item.is_duplicate = True
            item.duplicate_of = hash_seen[item.sha256]
        else:
            hash_seen[item.sha256] = item.rel_path

    return results


def build_deity_coverage_matrix(
    inventory: list[AssetInventoryItem],
) -> dict[str, Any]:
    """
    Computes deity coverage matrix across all 7 Hindu weekday groups
    and all mapped deities, identifying approved assets, candidates, and gaps.
    """
    # Collect all unique deities across the 7 weekdays
    all_weekday_deities: dict[str, dict[str, Any]] = {}
    weekday_schedules: list[dict[str, Any]] = []

    for day_idx in range(7):
        day_info = WEEKDAY_DEITY_MAPPING.get(day_idx, {})
        eng_day = day_info.get("english_day", f"Day_{day_idx}")
        sans_day = day_info.get("sanskrit_day", "")
        primary_deities = day_info.get("primary_deities", [])
        display_names = day_info.get("display_names", {})

        deity_summaries = []
        for d in primary_deities:
            disp = display_names.get(d, d.replace("_", " ").title())
            if d not in all_weekday_deities:
                all_weekday_deities[d] = {
                    "deity_key": d,
                    "display_name": disp,
                    "weekdays": [],
                    "approved_portrait_images": [],
                    "approved_landscape_images": [],
                    "approved_portrait_videos": [],
                    "approved_landscape_videos": [],
                    "unapproved_candidates_count": 0,
                    "unapproved_candidate_paths": [],
                    "broken_files_count": 0,
                }
            all_weekday_deities[d]["weekdays"].append(eng_day)
            deity_summaries.append({"deity_key": d, "display_name": disp})

        weekday_schedules.append({
            "day_index": day_idx,
            "english_day": eng_day,
            "sanskrit_day": sans_day,
            "deities": deity_summaries,
        })

    # Also track additional deities found in repository (e.g. Ayyappa, 7Kondala_Swami, Ram, Narasimha)
    additional_deity_keys = ["ayyappa", "7kondala_swami", "ram", "narasimha"]
    for d in additional_deity_keys:
        if d not in all_weekday_deities:
            all_weekday_deities[d] = {
                "deity_key": d,
                "display_name": d.replace("_", " ").title(),
                "weekdays": ["Non-Weekday Scheduled"],
                "approved_portrait_images": [],
                "approved_landscape_images": [],
                "approved_portrait_videos": [],
                "approved_landscape_videos": [],
                "unapproved_candidates_count": 0,
                "unapproved_candidate_paths": [],
                "broken_files_count": 0,
            }

    # Aggregate assets from inventory
    for item in inventory:
        # Check approved assets first
        if item.approval_status == "APPROVED" and item.registry_deity:
            reg_d = item.registry_deity.lower()
            if reg_d in all_weekday_deities:
                target_dict = all_weekday_deities[reg_d]
                is_landscape = item.aspect_ratio == "16:9" or (item.width and item.height and item.width >= item.height)
                if item.file_type == "video":
                    if is_landscape:
                        target_dict["approved_landscape_videos"].append(item.rel_path)
                    else:
                        target_dict["approved_portrait_videos"].append(item.rel_path)
                else:
                    if is_landscape:
                        target_dict["approved_landscape_images"].append(item.rel_path)
                    else:
                        target_dict["approved_portrait_images"].append(item.rel_path)

        # Unapproved candidates
        cand_d = item.candidate_deity.lower()
        if cand_d in all_weekday_deities:
            if item.is_broken:
                all_weekday_deities[cand_d]["broken_files_count"] += 1
            elif item.approval_status != "APPROVED":
                all_weekday_deities[cand_d]["unapproved_candidates_count"] += 1
                if len(all_weekday_deities[cand_d]["unapproved_candidate_paths"]) < 100:
                    all_weekday_deities[cand_d]["unapproved_candidate_paths"].append(item.rel_path)

    # Classify coverage status
    for d_key, data in all_weekday_deities.items():
        total_approved = (
            len(data["approved_portrait_images"])
            + len(data["approved_landscape_images"])
            + len(data["approved_portrait_videos"])
            + len(data["approved_landscape_videos"])
        )
        data["total_approved"] = total_approved

        has_portrait = bool(data["approved_portrait_images"] or data["approved_portrait_videos"])
        has_landscape = bool(data["approved_landscape_images"] or data["approved_landscape_videos"])

        if total_approved == 0:
            data["coverage_status"] = "MISSING_ALL_APPROVED"
        elif has_portrait and has_landscape:
            data["coverage_status"] = "FULL_COVERAGE"
        elif has_portrait:
            data["coverage_status"] = "PORTRAIT_ONLY"
        else:
            data["coverage_status"] = "LANDSCAPE_ONLY"

    return {
        "weekday_schedules": weekday_schedules,
        "deity_coverage": all_weekday_deities,
        "total_tracked_deities": len(all_weekday_deities),
        "total_approved_assets": sum(d["total_approved"] for d in all_weekday_deities.values()),
        "total_unapproved_candidates": sum(d["unapproved_candidates_count"] for d in all_weekday_deities.values()),
    }


def export_inventory_reports(
    inventory: list[AssetInventoryItem],
    matrix: dict[str, Any],
    output_dir: str | Path = "data/review",
) -> dict[str, str]:
    """Exports structured JSON and CSV reports to output_dir."""
    out_p = Path(output_dir)
    out_p.mkdir(parents=True, exist_ok=True)

    json_inventory_path = out_p / "candidate_asset_inventory.json"
    csv_inventory_path = out_p / "candidate_asset_inventory.csv"
    matrix_json_path = out_p / "deity_coverage_matrix.json"
    matrix_md_path = out_p / "deity_coverage_matrix.md"
    duplicates_json_path = out_p / "duplicates_and_broken.json"

    # 1. JSON Inventory
    inventory_dicts = [item.to_dict() for item in inventory]
    json_inventory_path.write_text(
        json.dumps(inventory_dicts, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # 2. CSV Inventory
    fieldnames = [
        "rel_path", "file_type", "file_ext", "file_size_bytes", "width", "height",
        "aspect_ratio", "duration_seconds", "approval_status", "approval_record_id",
        "registry_deity", "registry_avatar", "candidate_deity", "candidate_avatar",
        "is_broken", "broken_reason", "is_duplicate", "duplicate_of", "provenance_note"
    ]
    with open(csv_inventory_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for item in inventory:
            writer.writerow(item.to_dict())

    # 3. Coverage Matrix JSON
    matrix_json_path.write_text(
        json.dumps(matrix, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # 4. Coverage Matrix Markdown
    md_lines = [
        "# DEITY ASSET COVERAGE MATRIX — ALL 7 WEEKDAYS",
        "",
        "| Weekday | Deity Key | Display Name | Approved Portrait Img | Approved Landscape Img | Approved Portrait Vid | Approved Landscape Vid | Total Approved | Unapproved Candidates | Status |",
        "| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |",
    ]

    for sched in matrix["weekday_schedules"]:
        day_str = f"{sched['english_day']} ({sched['sanskrit_day']})"
        for d in sched["deities"]:
            d_key = d["deity_key"]
            info = matrix["deity_coverage"].get(d_key, {})
            p_img = len(info.get("approved_portrait_images", []))
            l_img = len(info.get("approved_landscape_images", []))
            p_vid = len(info.get("approved_portrait_videos", []))
            l_vid = len(info.get("approved_landscape_videos", []))
            tot_appr = info.get("total_approved", 0)
            cand_cnt = info.get("unapproved_candidates_count", 0)
            status = info.get("coverage_status", "MISSING_ALL_APPROVED")
            status_badge = (
                "🟢 FULL" if status == "FULL_COVERAGE"
                else "🟡 PORTRAIT" if status == "PORTRAIT_ONLY"
                else "🟡 LANDSCAPE" if status == "LANDSCAPE_ONLY"
                else "🔴 MISSING"
            )
            md_lines.append(
                f"| {day_str} | `{d_key}` | {d['display_name']} | {p_img} | {l_img} | {p_vid} | {l_vid} | **{tot_appr}** | {cand_cnt} | {status_badge} |"
            )

    md_lines.extend([
        "",
        "## Additional Tracked Deities (Non-Weekday Specific)",
        "",
        "| Deity Key | Display Name | Approved Portrait Img | Approved Landscape Img | Approved Portrait Vid | Approved Landscape Vid | Total Approved | Unapproved Candidates | Status |",
        "| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |",
    ])
    for d_key in ["ayyappa", "7kondala_swami", "ram", "narasimha"]:
        info = matrix["deity_coverage"].get(d_key, {})
        p_img = len(info.get("approved_portrait_images", []))
        l_img = len(info.get("approved_landscape_images", []))
        p_vid = len(info.get("approved_portrait_videos", []))
        l_vid = len(info.get("approved_landscape_videos", []))
        tot_appr = info.get("total_approved", 0)
        cand_cnt = info.get("unapproved_candidates_count", 0)
        status = info.get("coverage_status", "MISSING_ALL_APPROVED")
        status_badge = (
            "🟢 FULL" if status == "FULL_COVERAGE"
            else "🟡 PORTRAIT" if status == "PORTRAIT_ONLY"
            else "🟡 LANDSCAPE" if status == "LANDSCAPE_ONLY"
            else "🔴 MISSING"
        )
        md_lines.append(
            f"| `{d_key}` | {info.get('display_name', d_key)} | {p_img} | {l_img} | {p_vid} | {l_vid} | **{tot_appr}** | {cand_cnt} | {status_badge} |"
        )

    matrix_md_path.write_text("\n".join(md_lines), encoding="utf-8")

    # 5. Duplicates and Broken Files Report
    duplicates = [item.to_dict() for item in inventory if item.is_duplicate]
    broken = [item.to_dict() for item in inventory if item.is_broken]
    dup_report = {
        "summary": {
            "total_items": len(inventory),
            "duplicates_count": len(duplicates),
            "broken_count": len(broken),
        },
        "duplicates": duplicates,
        "broken_files": broken,
    }
    duplicates_json_path.write_text(
        json.dumps(dup_report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return {
        "inventory_json": str(json_inventory_path),
        "inventory_csv": str(csv_inventory_path),
        "matrix_json": str(matrix_json_path),
        "matrix_md": str(matrix_md_path),
        "duplicates_json": str(duplicates_json_path),
    }
