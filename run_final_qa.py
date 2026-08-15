#!/usr/bin/env python3
# run_final_qa.py
# Phase 2J — Final Pipeline QA Gate CLI
#
# Usage:
#   python run_final_qa.py
#   python run_final_qa.py --decision path/to/decision.json ...
#
# Automatically discovers newest artifacts when no explicit paths provided.
# Output is written to data/qa/final_qa_YYYYMMDD_HHMMSS.json

import argparse
import io
import sys
from pathlib import Path

# ── Windows-safe stdout: replace unencodable chars instead of crashing ────────
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Ensure src/ is on the path ────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent / "src"))

from qa.gate import FinalQAGate


# ─────────────────────────────────────────────────────────────────────────────
# Banner helpers
# ─────────────────────────────────────────────────────────────────────────────

LINE  = "=" * 48
THIN  = "-" * 48

def _status(ok: bool) -> str:
    return "PASS" if ok else "FAIL"

def _print_banner():
    print()
    print(LINE)
    print("DIVINE DHARSHANAM DAILY")
    print("FINAL PIPELINE QA GATE")
    print(LINE)
    print()


def _print_report(result, qa_file: Path) -> None:
    _print_banner()

    arts = result.artifacts_ref
    if arts:
        print(f"Topic : {result.selected_topic}")
        print(f"Source: {result.data_source}")
        print(f"Score : {result.score}")
        print(f"Conf  : {result.confidence}")
        print()

    print(THIN)
    print("CHECK RESULTS")
    print(THIN)

    # Group the checks into human-readable labels
    groups = [
        ("Decision Approval",      ["decision_approval"]),
        ("Provenance Consistency", ["provenance"]),
        ("Topic Consistency",      ["topic_consistency"]),
        ("File Integrity",         [k for k in result.checks if k.startswith("file_integrity.")]),
        ("Audio",                  ["audio"]),
        ("Visual",                 ["visual"]),
        ("Video",                  ["video", "video_ffprobe"]),
        ("Thumbnail",              ["thumbnail"]),
        ("Scene Synchronisation",  ["scene_sync"]),
    ]

    for label, keys in groups:
        group_pass = all(result.checks.get(k, True) for k in keys)
        print(f"  {label:<28} {_status(group_pass)}")
        for k in keys:
            if k in result.checks and not result.checks[k]:
                print(f"      >> {k}: {result.details.get(k, '')}")

    print()
    print(LINE)
    if result.approved_for_publishing:
        print("  APPROVED FOR PUBLISHING: YES")
    else:
        print("  APPROVED FOR PUBLISHING: NO")
    print(LINE)
    print()

    if result.errors:
        print("FAILURES:")
        for err in result.errors:
            print(f"  ✗ {err}")
        print()

    print(f"QA report saved: {qa_file}")
    print()


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Final Pipeline QA Gate — validates complete artifact set for publishing"
    )
    parser.add_argument("--decision",       help="Path to decision JSON")
    parser.add_argument("--content-brief",  help="Path to content brief JSON")
    parser.add_argument("--script",         help="Path to script JSON")
    parser.add_argument("--audio-map",      help="Path to audio map JSON")
    parser.add_argument("--visual-map",     help="Path to visual map JSON")
    parser.add_argument("--video-map",      help="Path to video map JSON")
    parser.add_argument("--thumbnail-meta", help="Path to thumbnail metadata JSON")
    parser.add_argument(
        "--output-dir",
        default="data/qa",
        help="Directory for QA report (default: data/qa)",
    )
    parser.add_argument(
        "--allow-mock",
        action="store_true",
        help="Bypass strict video production checks for mock/text video files (only for tests)",
    )
    args = parser.parse_args()

    # Build kwargs for artifact overrides (only if explicitly provided)
    overrides = {}
    if args.decision:
        overrides["decision_file"] = args.decision
    if args.content_brief:
        overrides["content_brief_file"] = args.content_brief
    if args.script:
        overrides["script_file"] = args.script
    if args.audio_map:
        overrides["audio_map_file"] = args.audio_map
    if args.visual_map:
        overrides["visual_map_file"] = args.visual_map
    if args.video_map:
        overrides["video_map_file"] = args.video_map
    if args.thumbnail_meta:
        overrides["thumbnail_meta_file"] = args.thumbnail_meta

    gate   = FinalQAGate(base_dir=".", allow_mock=args.allow_mock, **overrides)
    result = gate.run()

    qa_file = result.save(Path(args.output_dir))
    _print_report(result, qa_file)

    return 0 if result.approved_for_publishing else 1


if __name__ == "__main__":
    sys.exit(main())
