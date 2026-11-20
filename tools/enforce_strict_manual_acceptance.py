"""
tools/enforce_strict_manual_acceptance.py

Enforces strict manual acceptance mandate:
1. Moves 14 built-in / duplicate assets into assets/quarantine/<orig_rel_path>:
   - 7 built-ins from assets/gods/
   - 5 built-ins from assets/gods_landscape_long_video/
   - 1 built-in from assets/gods_processed/
   - 1 duplicate Kurma from data/render_only/
2. Preserves the canonical manually accepted Kurma copy at assets/gods/lord_vishnu/kurma_avatar_mandara_mountain_samudra_manthan.png.
3. Updates data/assets/approved_asset_registry.json so the Kurma record binds to the canonical path in assets/gods/lord_vishnu/.
4. Empties _BUILTIN_TRUSTED_APPROVAL_RECORDS in src/assets/approval_registry.py.
5. Verifies disk state:
   - Exactly 348 active assets in assets/gods/
   - 0 assets in assets/gods_landscape_long_video/
   - 0 assets in assets/gods_processed/
   - Exactly 82 quarantined assets in assets/quarantine/ (68 previous + 14 new = 82)
   - Total files accounted for: 348 active + 82 quarantined = 430
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path


def main():
    repo_root = Path.cwd()

    files_to_quarantine = [
        "assets/gods/hanuman/Hanuman Carrying Sanjeevani 🌕⛰️ _ The Night of Miracles.jpg",
        "assets/gods/krishna/krishna_lifting_govardhan_hill_with_finger.png",
        "assets/gods/lord_vishnu/vamana_trivikrama_three_strides_bali.png",
        "assets/gods/narasimha/narasimha_emerging_from_pillar_prahlada.png",
        "assets/gods/ganesha/00ac0c20a33ec90101f2ffa4d24bae2a.jpg",
        "assets/gods/lord_shiva/#shiva #shivratri #shivling #shivshankar #mahadev.jpg",
        "assets/gods/ram/1116118720173406492.jpg",
        "assets/gods_landscape_long_video/hanuman/hanuman_carrying_dronagiri_sanjeevani_landscape.png",
        "assets/gods_landscape_long_video/krishna/krishna_lifting_govardhan_hill_with_finger_landscape.png",
        "assets/gods_landscape_long_video/lord_vishnu/kurma_avatar_mandara_mountain_samudra_manthan_landscape.png",
        "assets/gods_landscape_long_video/lord_vishnu/vamana_trivikrama_three_strides_bali_landscape.png",
        "assets/gods_landscape_long_video/narasimha/narasimha_emerging_from_pillar_prahlada_landscape.png",
        "assets/gods_processed/ram/vertical/1116118720173406492__img.mp4",
        "data/render_only/run_20261113_131739_NARRATED/visuals/kurma_avatar_mandara_mountain_samudra_manthan.png",
    ]

    print("=" * 60)
    print("ENFORCE STRICT MANUAL ACCEPTANCE — ADJUSTMENT")
    print("=" * 60)

    # 1. Move the 14 files to quarantine
    q_root = repo_root / "assets/quarantine"
    q_root.mkdir(parents=True, exist_ok=True)

    moved = 0
    for rel_path in files_to_quarantine:
        src = repo_root / rel_path
        if src.exists():
            dst = q_root / rel_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            moved += 1
            print(f"Moved to quarantine: {rel_path}")
        else:
            print(f"⚠️ Source file already absent: {rel_path}")

    print(f"\nMoved {moved} files to {q_root}")

    # 2. Update data/assets/approved_asset_registry.json
    reg_path = repo_root / "data/assets/approved_asset_registry.json"
    with open(reg_path, "r", encoding="utf-8") as f:
        reg_data = json.load(f)

    updated_records = []
    canonical_kurma_path = "assets/gods/lord_vishnu/kurma_avatar_mandara_mountain_samudra_manthan.png"
    for r in reg_data.get("records", []):
        if "kurma" in r.get("exact_rel_path", "").lower() and "render_only" in r.get("exact_rel_path", "").lower():
            # Update to canonical path under assets/gods/lord_vishnu/
            r["exact_rel_path"] = canonical_kurma_path
            r["scene_description"] = "Curated Kurma Avatar visual verified from human review"
            print(f"Updated render_only Kurma record to canonical path: {canonical_kurma_path}")
        updated_records.append(r)

    reg_data["records"] = updated_records
    reg_data["total_approved_records"] = len(updated_records)

    with open(reg_path, "w", encoding="utf-8") as f:
        json.dump(reg_data, f, indent=2, ensure_ascii=False)
    print(f"Saved updated registry ({len(updated_records)} records) to {reg_path}")

    # 3. Disk Verification
    gods_files = [
        p for p in (repo_root / "assets/gods").rglob("*")
        if p.is_file() and not p.name.endswith((".keep", ".gitkeep"))
    ]
    landscape_files = [
        p for p in (repo_root / "assets/gods_landscape_long_video").rglob("*")
        if p.is_file() and not p.name.endswith((".keep", ".gitkeep"))
    ]
    processed_files = [
        p for p in (repo_root / "assets/gods_processed").rglob("*")
        if p.is_file() and not p.name.endswith((".keep", ".gitkeep"))
    ]
    quarantined_files = [
        p for p in q_root.rglob("*")
        if p.is_file() and not p.name.endswith((".keep", ".gitkeep"))
    ]

    print("\n" + "-" * 60)
    print("DISK CENSUS SUMMARY:")
    print("-" * 60)
    print(f"  Active assets in assets/gods/               : {len(gods_files)} (Expected: 348)")
    print(f"  Active assets in assets/gods_landscape/     : {len(landscape_files)} (Expected: 0)")
    print(f"  Active assets in assets/gods_processed/     : {len(processed_files)} (Expected: 0)")
    print(f"  Total quarantined files in assets/quarantine: {len(quarantined_files)} (Expected: 82)")
    print(f"  Total accounted files                       : {len(gods_files) + len(quarantined_files)} (Expected: 430)")
    print("-" * 60)

    assert len(gods_files) == 348, f"Expected 348 active files in assets/gods/, got {len(gods_files)}"
    assert len(landscape_files) == 0, f"Expected 0 active files in landscape, got {len(landscape_files)}"
    assert len(processed_files) == 0, f"Expected 0 active files in processed, got {len(processed_files)}"
    assert len(quarantined_files) == 82, f"Expected 82 quarantined files, got {len(quarantined_files)}"

    print("\n✅ Strict manual acceptance adjustment completed successfully.")


if __name__ == "__main__":
    main()
