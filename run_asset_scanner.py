#!/usr/bin/env python3
# run_asset_scanner.py
# Phase 3 — Repository Deity Asset Scanner CLI
#
# Usage:
#   python run_asset_scanner.py
#
# Scans assets/gods/, validates every image and video asset,
# and generates data/assets/asset_manifest.json.

import io
import sys
from pathlib import Path

# Force UTF-8 stdout/stderr on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from src.assets.manifest import generate_asset_manifest, MANIFEST_PATH

LINE = "=" * 60
THIN = "-" * 60


def main() -> int:
    print("\n" + LINE)
    print("DIVINE DHARSHANAM DAILY — REPOSITORY ASSET SCANNER")
    print(LINE + "\n")

    gods_dir = Path("assets/gods")
    if not gods_dir.exists():
        print(f"❌ ERROR: Directory not found: {gods_dir}", file=sys.stderr)
        return 1

    print(f"Scanning directory: {gods_dir.absolute()}")
    try:
        manifest = generate_asset_manifest(gods_dir=gods_dir, output_manifest_path=MANIFEST_PATH)
    except Exception as exc:
        print(f"❌ SCAN FAILED: {exc}", file=sys.stderr)
        return 1

    stats = manifest.get("stats", {})
    deities = manifest.get("deities", {})

    print("\n" + THIN)
    print("DEITY ASSETS SUMMARY")
    print(THIN)
    print(f"  Deities Count    : {stats.get('deities_count', 0)}")
    print(f"  Total Images     : {stats.get('total_images', 0)}")
    print(f"  Total MP4 Videos : {stats.get('total_videos', 0)}")
    print(f"  Total Valid      : {stats.get('total_valid_assets', 0)}")
    print(f"  Rejected Files   : {stats.get('rejected_assets_count', 0)}")
    print(THIN)

    print("\nDEITY BREAKDOWN:")
    for deity_name, assets in deities.items():
        imgs = len(assets.get("images", []))
        vids = len(assets.get("videos", []))
        print(f"  - {deity_name:<20}: {imgs} images, {vids} videos")

    if stats.get("rejected_files"):
        print("\nREJECTED FILES (INVALID / CORRUPTED):")
        for item in stats["rejected_files"]:
            print(f"  ⚠️ {item['file']}: {item['reason']}")

    print("\n" + LINE)
    print(f"Manifest saved to: {MANIFEST_PATH}")
    print(LINE + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
