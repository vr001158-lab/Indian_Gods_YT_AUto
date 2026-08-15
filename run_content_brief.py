"""
run_content_brief.py — Content Brief Generator CLI (Phase 2C)
Converts approved topic decisions into detailed production-ready content blueprints.

Usage:
  python run_content_brief.py                        # auto-picks latest decision JSON
  python run_content_brief.py --input <file>         # explicit decision file
  python run_content_brief.py --no-save              # skip writing brief JSON to disk
"""

import sys
import os
import io
import json
from pathlib import Path

# Force UTF-8 stdout/stderr on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

sys.path.insert(0, os.getcwd())

from src.content import brief_generator

DECISION_DIR = Path("data/decision")
BRIEF_DIR = Path("data/content_briefs")


def _find_latest_decision_file() -> Path:
    """Returns the most recently created decision_*.json file."""
    files = sorted(DECISION_DIR.glob("decision_*.json"))
    if not files:
        raise FileNotFoundError(
            f"❌ No decision_*.json files found in {DECISION_DIR}.\n"
            "   Run: python run_decision.py   to run decision gates first."
        )
    return files[-1]


def print_brief(brief: dict):
    """Outputs the formatted content brief to stdout."""
    print("\n" + "=" * 60)
    print("🌅  DIVINE DHARSHANAM DAILY — PRODUCTION CONTENT BRIEF")
    print("=" * 60)

    print(f"\n🎯  PRIMARY TITLE: {brief['primary_title']}")
    print(f"👥  AUDIENCE:      {brief['audience']}")

    print(f"\n{'─' * 60}")
    print("📜  CURIOSITY HOOK (First 15 Seconds):")
    print(f"   \"{brief['hook']}\"")

    print(f"\n{'─' * 60}")
    print("📖  STORY ARC:")
    for act in brief["story_arc"]:
        print(f"   • {act}")

    print(f"\n{'─' * 60}")
    print("🎬  SCRIPT STRUCTURE:")
    for act, desc in brief["script_structure"].items():
        act_label = act.replace("_", " ").upper()
        print(f"   [{act_label}]:")
        print(f"       {desc}")

    print(f"\n{'─' * 60}")
    print("🎨  VISUAL PLAN (SCENES):")
    for scene in brief["visual_plan"]:
        print(f"   Scene #{scene['scene_number']} ({scene['duration_seconds']}s):")
        print(f"       Description:  {scene['description']}")
        print(f"       Image Prompt: \"{scene['image_prompt']}\"")
        print(f"       Video Prompt: \"{scene['video_prompt']}\"")

    print(f"\n{'─' * 60}")
    print("🎙️  VOICE DIRECTION:")
    for k, v in brief["voice_direction"].items():
        print(f"   • {k.replace('_', ' ').title():<15}: {v}")

    print(f"\n{'─' * 60}")
    print("✂️  SHORTS HOOKS (Vertical Video Extraction):")
    for h in brief["shorts_hooks"]:
        print(f"   • \"{h}\"")

    print(f"\n{'─' * 60}")
    print("🌐  SEO METADATA:")
    seo = brief["seo_metadata"]
    print(f"   • Category:    {seo['category']}")
    print(f"   • Description: {seo['description']}")
    print(f"   • Keywords:    {', '.join(seo['keywords'])}")
    print(f"   • Hashtags:    {', '.join(seo['hashtags'])}")

    print("=" * 60)


def main():
    input_file = None
    save_output = True

    # ── CLI parsing ───────────────────────────────────────────────────────────
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--input" and i + 1 < len(args):
            input_file = Path(args[i + 1])
            i += 2
        elif args[i] == "--no-save":
            save_output = False
            i += 1
        else:
            print(f"❌ Unknown argument: {args[i]}", file=sys.stderr)
            print("Usage: python run_content_brief.py [--input FILE] [--no-save]", file=sys.stderr)
            sys.exit(1)

    # ── Locate decision file ──────────────────────────────────────────────────
    if input_file is None:
        try:
            input_file = _find_latest_decision_file()
        except FileNotFoundError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
    elif not input_file.exists():
        print(f"❌ Specified input file not found: {input_file}", file=sys.stderr)
        sys.exit(1)

    print(f"\n📄 Input Decision File: {input_file}")

    # ── Process & Generate ────────────────────────────────────────────────────
    try:
        if save_output:
            out_file = brief_generator.process_decision_file(input_file, BRIEF_DIR)
            print(f"📂 Content brief saved to: {out_file}", file=sys.stderr)
            # Load and print
            brief = json.loads(out_file.read_text(encoding="utf-8"))
        else:
            decision = json.loads(input_file.read_text(encoding="utf-8"))
            brief = brief_generator.generate_content_brief(decision)
            print("🔬 [DRY RUN] Skipping file persistence.", file=sys.stderr)
        
        print_brief(brief)
    except Exception as e:
        print(f"\n❌ FAILED TO GENERATE CONTENT BRIEF: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
