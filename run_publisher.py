#!/usr/bin/env python3
# run_publisher.py
# Phase 2K — YouTube Publisher CLI
#
# Usage:
#   python run_publisher.py --qa data/qa/final_qa_YYYYMMDD_HHMMSS.json
#
# This script NEVER uploads publicly.  Privacy is always PRIVATE.
# STOP: Do NOT call this until explicitly authorized for a real upload.
#
# Safety rules enforced:
#  - QA result must have approved_for_publishing = true
#  - data_source must be youtube_api or cached_youtube_api
#  - confidence must be high
#  - approved_for_generation must be true
#  - video must exist and be non-zero .mp4
#  - Privacy is ALWAYS "private" — cannot be changed via CLI

import argparse
import sys
from pathlib import Path

# Windows-safe stdout
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from publisher.safety   import load_qa_result, validate_qa_for_publishing, PublisherSafetyError
from publisher.metadata import build_video_metadata
from publisher.uploader import publish_video, REQUIRED_PRIVACY


LINE = "=" * 52
THIN = "-" * 52


def _print_banner():
    print()
    print(LINE)
    print("DIVINE DHARSHANAM DAILY")
    print("YOUTUBE PUBLISHER  [PRIVATE ONLY]")
    print(LINE)
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="YouTube Publisher — uploads to YouTube as PRIVATE"
    )
    parser.add_argument(
        "--qa",
        required=True,
        help="Path to the Final QA result JSON (approved_for_publishing=true required)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/publishing",
        help="Directory for publishing manifest (default: data/publishing)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate all inputs but do NOT perform any upload",
    )
    args = parser.parse_args()

    _print_banner()

    # ── Step 1: Load and validate QA result ──────────────────────────────────
    print(f"QA file  : {args.qa}")
    try:
        qa = load_qa_result(args.qa)
        validate_qa_for_publishing(qa)
    except PublisherSafetyError as exc:
        print(f"\n[BLOCKED] Publisher safety gate rejected QA result:")
        print(f"  {exc}")
        print()
        print("APPROVED FOR PUBLISHING: NO")
        return 1

    print(f"Topic    : {qa.get('selected_topic', '')}")
    print(f"Source   : {qa.get('data_source', '')}")
    print(f"Score    : {qa.get('score', '')}")
    print(f"Conf     : {qa.get('confidence', '')}")
    print(f"Privacy  : {REQUIRED_PRIVACY.upper()} (enforced)")
    print()

    # ── Step 2: Build metadata ───────────────────────────────────────────────
    try:
        meta = build_video_metadata(qa)
    except Exception as exc:
        print(f"[ERROR] Metadata build failed: {exc}", file=sys.stderr)
        return 1

    print(THIN)
    print("VIDEO METADATA")
    print(THIN)
    print(f"  Title     : {meta['title'][:80]}")
    print(f"  Video     : {meta['video_file']}")
    print(f"  Thumbnail : {meta['thumbnail_file']}")
    print(f"  Tags      : {len(meta['tags'])} tags")
    print(f"  Category  : {meta['category_id']}")
    print()

    if args.dry_run:
        print(THIN)
        print("DRY RUN — no upload performed")
        print(THIN)
        print()
        print("All inputs validated successfully.")
        print("Remove --dry-run when authorized to upload.")
        return 0

    # ── Step 3: Load credentials ──────────────────────────────────────────────
    # Credentials are loaded but NEVER printed, logged, or stored in manifests.
    try:
        import google_auth_config
        creds = google_auth_config.get_google_credentials()
    except Exception as exc:
        print(f"[BLOCKED] OAuth credentials unavailable: {exc}", file=sys.stderr)
        print("Ensure TOKEN_JSON is configured correctly.", file=sys.stderr)
        return 1

    # ── Step 4: Publish ──────────────────────────────────────────────────────
    print(THIN)
    print("UPLOADING TO YOUTUBE [PRIVATE]")
    print(THIN)
    try:
        manifest = publish_video(
            creds          = creds,
            video_file     = meta["video_file"],
            title          = meta["title"],
            description    = meta["description"],
            tags           = meta["tags"],
            category_id    = meta["category_id"],
            thumbnail_file = meta["thumbnail_file"] or None,
            qa             = qa,
            output_dir     = args.output_dir,
        )
    except Exception as exc:
        print(f"\n[FAILED] Upload failed: {exc}", file=sys.stderr)
        return 1

    print()
    print(LINE)
    print(f"  VIDEO ID  : {manifest['video_id']}")
    print(f"  URL       : {manifest['youtube_url']}")
    print(f"  PRIVACY   : {manifest['privacy_status'].upper()}")
    print(f"  THUMBNAIL : {'YES' if manifest['thumbnail_uploaded'] else 'NO'}")
    print(LINE)
    print()
    print(f"Manifest saved: {manifest.get('_manifest_path', args.output_dir)}")
    print()
    print("UPLOAD COMPLETE: PRIVATE")
    print("Do NOT change privacy to PUBLIC without explicit authorization.")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
