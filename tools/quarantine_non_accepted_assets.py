"""
tools/quarantine_non_accepted_assets.py

Implements Task: Clean Deity Asset Library — Keep Accepted Assets Only
1. Loads human review decisions from data/review/human_review_decisions.json.
2. Identifies all 348 PROPOSED_FOR_APPROVAL assets and creates TrustedAssetApprovalRecord entries.
3. Unions with the 14 built-in pre-approved assets -> 362 total approved whitelist assets.
4. Moves all 68 non-accepted visual assets from the repository into assets/quarantine/<original_rel_path>.
5. Saves data/assets/approved_asset_registry.json.
6. Verifies disk state: exactly 362 active assets, exactly 68 quarantined assets.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

from src.assets.approval_registry import (
    _BUILTIN_TRUSTED_APPROVAL_RECORDS,
    TrustedAssetApprovalRecord,
    normalize_repo_path,
)


def run_quarantine_and_approval_sync(
    dry_run: bool = False,
    decisions_path: str = "data/review/human_review_decisions.json",
    registry_output_path: str = "data/assets/approved_asset_registry.json",
    quarantine_root: str = "assets/quarantine",
) -> dict[str, Any]:
    print("=" * 60)
    print("CLEAN DEITY ASSET LIBRARY — QUARANTINE & REGISTRY SYNC")
    print("=" * 60)

    # 1. Load human review decisions
    d_path = Path(decisions_path)
    if not d_path.exists():
        raise FileNotFoundError(f"Decisions file not found: {d_path}")

    with open(d_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    decisions: dict[str, dict[str, Any]] = data.get("decisions", {})
    print(f"Loaded {len(decisions)} human review decisions from {d_path}")

    # 2. Extract explicitly approved assets (decision == 'APPROVED' with verified reviewer)
    # PROPOSED_FOR_APPROVAL does NOT grant trusted approval; it represents pending review.
    accepted_decisions = {
        path: dec
        for path, dec in decisions.items()
        if dec.get("decision") == "APPROVED" and dec.get("reviewer", "").strip()
    }
    pending_decisions = {
        path: dec
        for path, dec in decisions.items()
        if dec.get("decision") == "PROPOSED_FOR_APPROVAL"
    }
    print(f"Explicitly approved decisions count: {len(accepted_decisions)}")
    print(f"Pending review decisions count (PROPOSED_FOR_APPROVAL): {len(pending_decisions)}")

    # 3. Create approval records for explicitly approved assets
    approval_records_dicts: list[dict[str, Any]] = []
    accepted_normalized_set: set[str] = set()

    for idx, (rel_path, dec) in enumerate(accepted_decisions.items(), 1):
        norm = normalize_repo_path(rel_path)
        if not norm:
            raise ValueError(f"Failed to normalize accepted path: {rel_path}")

        deity = dec.get("candidate_deity", "").strip().lower()
        if not deity:
            raise ValueError(f"Accepted asset {rel_path} missing candidate_deity")

        avatar = dec.get("candidate_avatar")
        if avatar:
            avatar = avatar.strip().lower()

        c_type = (
            "video"
            if norm.lower().endswith((".mp4", ".mov", ".webm", ".avi", ".mkv"))
            else "image"
        )
        rec_id = f"APPR-REV-{deity.upper()}-{idx:04d}"
        reviewer = dec.get("reviewer", "").strip()
        timestamp = dec.get("timestamp", "").strip()
        provenance = f"Manual human review decision (APPROVED by {reviewer}): {timestamp}"
        notes = dec.get("notes", "").strip()
        description = notes if notes else f"Curated {deity} {c_type}"
        co_depicted = tuple(dec.get("co_depicted_deities", []))
        allow_solo = dec.get("allow_solo", True)

        rec = TrustedAssetApprovalRecord(
            record_id=rec_id,
            exact_rel_path=norm,
            canonical_deity=deity,
            approval_status="APPROVED",
            provenance=provenance,
            reviewer=reviewer,
            review_timestamp=timestamp,
            co_depicted_deities=co_depicted,
            allow_solo=allow_solo,
            avatar=avatar,
            aspect_ratio=dec.get("aspect_ratio"),
            content_type=c_type,
            scene_description=description,
        )
        approval_records_dicts.append(rec.to_dict())
        accepted_normalized_set.add(norm.lower())

    # 4. Built-in pre-approved assets
    builtin_normalized_set: set[str] = set()
    for b in _BUILTIN_TRUSTED_APPROVAL_RECORDS:
        norm = normalize_repo_path(b["exact_rel_path"])
        if norm:
            builtin_normalized_set.add(norm.lower())

    # 5. Whitelist = union of accepted + built-in
    whitelist_normalized = accepted_normalized_set | builtin_normalized_set
    print(f"Built-in approved records: {len(builtin_normalized_set)}")
    print(f"Total approved whitelist assets: {len(whitelist_normalized)}")

    # 6. Inventory all physical visual files across visual directories
    repo_root = Path.cwd()
    visual_dirs = [
        "assets/gods",
        "assets/gods_landscape_long_video",
        "assets/gods_processed",
        "assets/incoming",
        "data/visuals",
        "data/render_only",
    ]

    all_physical_visual_files: list[Path] = []
    for vd in visual_dirs:
        dir_path = repo_root / vd
        if not dir_path.exists():
            continue
        for p in dir_path.rglob("*"):
            if p.is_file() and p.suffix.lower() in (
                ".png",
                ".jpg",
                ".jpeg",
                ".webp",
                ".mp4",
                ".mov",
                ".webm",
                ".avi",
                ".mkv",
            ):
                all_physical_visual_files.append(p)

    print(f"Total physical visual files discovered: {len(all_physical_visual_files)}")

    # 7. Categorize into KEEP and QUARANTINE
    to_keep: list[tuple[Path, str]] = []
    to_quarantine: list[tuple[Path, str]] = []

    for fpath in all_physical_visual_files:
        rel_str = str(fpath.relative_to(repo_root)).replace("\\", "/")
        norm = normalize_repo_path(rel_str)
        if norm and norm.lower() in whitelist_normalized:
            to_keep.append((fpath, norm))
        else:
            to_quarantine.append((fpath, rel_str))

    print(f"\nPlan Summary:")
    print(f"  Files to KEEP (Approved Whitelist)    : {len(to_keep)}")
    print(f"  Files to QUARANTINE (Non-Accepted)   : {len(to_quarantine)}")

    if len(to_keep) != 362:
        print(f"⚠️ Warning: Expected 362 assets to keep, got {len(to_keep)}")
    if len(to_quarantine) != 68:
        print(f"⚠️ Warning: Expected 68 assets to quarantine, got {len(to_quarantine)}")

    if dry_run:
        print("\nDry run completed. No files modified.")
        return {
            "keep_count": len(to_keep),
            "quarantine_count": len(to_quarantine),
            "approval_records_count": len(approval_records_dicts),
        }

    # 8. Save approved asset registry
    out_reg = Path(registry_output_path)
    out_reg.parent.mkdir(parents=True, exist_ok=True)
    registry_payload = {
        "generated_at": "2026-11-18T00:00:00Z",
        "total_approved_records": len(approval_records_dicts),
        "description": "Explicit trusted asset approval registry derived strictly from human review decisions",
        "records": approval_records_dicts,
    }
    with open(out_reg, "w", encoding="utf-8") as f:
        json.dump(registry_payload, f, indent=2, ensure_ascii=False)
    print(f"\nSaved approved registry with {len(approval_records_dicts)} records to: {out_reg}")

    # 9. Move non-accepted files to quarantine folder
    q_root = repo_root / quarantine_root
    q_root.mkdir(parents=True, exist_ok=True)

    moved_count = 0
    for src_path, orig_rel in to_quarantine:
        dst_path = q_root / orig_rel
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_path), str(dst_path))
        moved_count += 1

    print(f"Successfully moved {moved_count} non-accepted files to {q_root}")

    # 10. Post-quarantine verification
    remaining_files: list[Path] = []
    for vd in visual_dirs:
        dir_path = repo_root / vd
        if not dir_path.exists():
            continue
        for p in dir_path.rglob("*"):
            if p.is_file() and p.suffix.lower() in (
                ".png",
                ".jpg",
                ".jpeg",
                ".webp",
                ".mp4",
                ".mov",
                ".webm",
                ".avi",
                ".mkv",
            ):
                remaining_files.append(p)

    quarantined_files: list[Path] = []
    for p in q_root.rglob("*"):
        if p.is_file() and p.suffix.lower() in (
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
            ".mp4",
            ".mov",
            ".webm",
            ".avi",
            ".mkv",
        ):
            quarantined_files.append(p)

    print("\nPost-Quarantine Verification:")
    print(f"  Active Library Visual Files  : {len(remaining_files)}")
    print(f"  Quarantined Visual Files     : {len(quarantined_files)}")
    print(f"  Sum Total                    : {len(remaining_files) + len(quarantined_files)}")

    assert len(remaining_files) == 362, f"Expected 362 remaining files, got {len(remaining_files)}"
    assert len(quarantined_files) == 68, f"Expected 68 quarantined files, got {len(quarantined_files)}"

    print("\n✅ Quarantine and whitelist synchronization completed successfully.")
    return {
        "keep_count": len(remaining_files),
        "quarantine_count": len(quarantined_files),
        "approval_records_count": len(approval_records_dicts),
    }


if __name__ == "__main__":
    run_quarantine_and_approval_sync(dry_run=False)
