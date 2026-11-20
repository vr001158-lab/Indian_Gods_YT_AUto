#!/usr/bin/env python3
# run_asset_inventory.py
# Fast-Track Deity Asset Inventory, Duplicate Detection & Contact Sheet CLI
#
# Usage:
#   python run_asset_inventory.py [--output-dir data/review] [--workers 8]

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Force UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from src.assets.inventory import (
    scan_all_visual_assets,
    build_deity_coverage_matrix,
    export_inventory_reports,
)
from src.assets.contact_sheet import generate_all_contact_sheets

LINE = "=" * 80
THIN = "-" * 80


def main() -> int:
    parser = argparse.ArgumentParser(description="Deity Asset Inventory and Visual Review Contact Sheet Generator")
    parser.add_argument("--output-dir", default="data/review", help="Directory to save inventory reports and contact sheets")
    parser.add_argument("--workers", type=int, default=8, help="Number of worker threads for parallel inspection")
    parser.add_argument("--skip-contact-sheets", action="store_true", help="Skip generating visual contact sheets")
    args = parser.parse_args()

    start_time = time.time()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + LINE)
    print("DIVINE DHARSHANAM DAILY — FAST-TRACK DEITY ASSET INVENTORY & REVIEW")
    print(LINE + "\n")

    # Step 1: Scan all repository visual asset directories
    print("🔍 [STEP 1/4] Scanning all repository visual assets...")
    roots = [
        "assets/gods",
        "assets/gods_landscape_long_video",
        "assets/gods_processed",
        "assets/incoming",
        "data/visuals",
        "data/render_only",
    ]
    inventory = scan_all_visual_assets(roots=roots, max_workers=args.workers)
    scan_dur = round(time.time() - start_time, 2)
    print(f"   Scanned {len(inventory)} total visual files across {len(roots)} root directories in {scan_dur}s.")

    # Step 2: Compute coverage matrix
    print("\n📊 [STEP 2/4] Computing Hindu weekday deity coverage matrix...")
    matrix = build_deity_coverage_matrix(inventory)
    reports = export_inventory_reports(inventory, matrix, output_dir=out_dir)
    print(f"   Exported inventory reports to: {out_dir}")

    # Step 3: Generate visual review contact sheets
    contact_sheets: dict[str, list[str]] = {}
    if not args.skip_contact_sheets:
        print("\n🖼️  [STEP 3/4] Generating visual review contact sheets for unapproved candidates...")
        cs_start = time.time()
        cs_dir = out_dir / "contact_sheets"
        frames_dir = out_dir / "extracted_frames"
        contact_sheets = generate_all_contact_sheets(
            inventory=inventory,
            output_dir=cs_dir,
            frames_dir=frames_dir,
        )
        total_sheets = sum(len(sheets) for sheets in contact_sheets.values())
        cs_dur = round(time.time() - cs_start, 2)
        print(f"   Generated {total_sheets} contact sheet pages across {len(contact_sheets)} candidate groups in {cs_dur}s.")
    else:
        print("\n⏩ [STEP 3/4] Skipping contact sheets (--skip-contact-sheets flag set).")

    # Step 4: Summary output
    elapsed = round(time.time() - start_time, 2)

    total_files = len(inventory)
    approved_files = sum(1 for item in inventory if item.approval_status == "APPROVED")
    unapproved_files = total_files - approved_files
    duplicates = [item for item in inventory if item.is_duplicate]
    broken = [item for item in inventory if item.is_broken]

    print("\n" + THIN)
    print("ASSET INVENTORY SUMMARY")
    print(THIN)
    print(f"  Total Visual Files   : {total_files}")
    print(f"  Approved Assets      : {approved_files}")
    print(f"  Unapproved Candidates: {unapproved_files}")
    print(f"  Duplicate Assets     : {len(duplicates)}")
    print(f"  Broken/Corrupt Files : {len(broken)}")
    print(f"  Total Execution Time : {elapsed} seconds")
    print(THIN)

    # Print Weekday Coverage Status
    print("\nHINDU WEEKDAY DEITY COVERAGE STATUS:")
    missing_deities = []
    full_deities = []
    partial_deities = []

    for sched in matrix["weekday_schedules"]:
        day_str = f"{sched['english_day']} ({sched['sanskrit_day']})"
        for d in sched["deities"]:
            d_key = d["deity_key"]
            cov = matrix["deity_coverage"].get(d_key, {})
            tot_appr = cov.get("total_approved", 0)
            cand_cnt = cov.get("unapproved_candidates_count", 0)
            status = cov.get("coverage_status", "MISSING_ALL_APPROVED")
            if status == "MISSING_ALL_APPROVED":
                missing_deities.append(f"{d_key} ({d['display_name']} - {sched['english_day']})")
                icon = "🔴"
            elif status == "FULL_COVERAGE":
                full_deities.append(d_key)
                icon = "🟢"
            else:
                partial_deities.append(d_key)
                icon = "🟡"

            print(f"  {icon} {day_str:<22} | {d['display_name']:<24} (`{d_key}`): {tot_appr} approved, {cand_cnt} candidates ({status})")

    print("\n" + THIN)
    print("COVERAGE STATUS OVERVIEW:")
    print(f"  Full Coverage (Portrait + Landscape) : {len(set(full_deities))} deities: {', '.join(sorted(set(full_deities)))}")
    print(f"  Partial Coverage                     : {len(set(partial_deities))} deities: {', '.join(sorted(set(partial_deities)))}")
    print(f"  Missing All Approved Assets          : {len(missing_deities)} weekday deity assignments:")
    for m in missing_deities:
        print(f"    - ❌ {m}")
    print(THIN)

    print("\nGENERATED OUTPUT ARTIFACTS:")
    print(f"  📄 Inventory JSON        : {reports['inventory_json']}")
    print(f"  📄 Inventory CSV         : {reports['inventory_csv']}")
    print(f"  📄 Coverage Matrix JSON  : {reports['matrix_json']}")
    print(f"  📄 Coverage Matrix MD    : {reports['matrix_md']}")
    print(f"  📄 Duplicates Report     : {reports['duplicates_json']}")
    if contact_sheets:
        print(f"  🖼️  Contact Sheets Folder : {out_dir / 'contact_sheets'} ({sum(len(v) for v in contact_sheets.values())} image pages)")

    print("\n" + LINE)
    print("FAST-TRACK INVENTORY & REVIEW WORKFLOW COMPLETE")
    print(LINE + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
