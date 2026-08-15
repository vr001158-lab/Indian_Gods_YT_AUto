"""
run_script_generator.py — Script Generator CLI (Phase 2D)
Converts approved content briefs into detailed long-form and Shorts scripts.

Usage:
  python run_script_generator.py                        # auto-picks latest content brief JSON
  python run_script_generator.py --input <file>         # explicit content brief file
  python run_script_generator.py --no-save              # skip writing script JSON to disk
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

from src.script import generator as script_generator

BRIEF_DIR = Path("data/content_briefs")
SCRIPT_DIR = Path("data/scripts")


def _find_latest_brief_file() -> Path:
    """Returns the most recently created content_brief_*.json file."""
    files = sorted(BRIEF_DIR.glob("content_brief_*.json"))
    if not files:
        raise FileNotFoundError(
            f"❌ No content_brief_*.json files found in {BRIEF_DIR}.\n"
            "   Run: python run_content_brief.py   to run brief generation first."
        )
    return files[-1]


def print_script(script: dict):
    """Outputs the formatted production script to stdout."""
    print("\n" + "=" * 60)
    print("🌅  DIVINE DHARSHANAM DAILY — PRODUCTION SCRIPT")
    print("=" * 60)

    print(f"\n🎯  TITLE:            {script['title']}")
    print(f"⏱️   TOTAL DURATION:   {script['duration_seconds']} seconds ({script['duration_seconds'] // 60}m {script['duration_seconds'] % 60}s)")

    print(f"\n{'─' * 60}")
    print("📢  FULL VOICE NARRATION:")
    print(f"   \"{script['narration']}\"")

    print(f"\n{'─' * 60}")
    print("🎬  SCENE-BY-SCENE SCRIPTS:")
    for scene in script["scene_scripts"]:
        print(f"   Scene #{scene['scene']} ({scene['duration_seconds']}s):")
        print(f"       Visual:  {scene['visual_reference']}")
        print(f"       Voice:   \"{scene['voice_text']}\"")
        print(f"       Emotion: {scene['emotion']}")
        print()

    print(f"\n{'─' * 60}")
    print("🧲  RETENTION HOOKS:")
    for hook in script["retention_hooks"]:
        print(f"   • {hook}")

    print(f"\n{'─' * 60}")
    print("✂️  VERTICAL SHORTS SCRIPTS (Exactly 3):")
    for i, short in enumerate(script["shorts_scripts"], 1):
        print(f"   Short #{i}: {short['title']}")
        print(f"       Hook:  \"{short['hook']}\"")
        print(f"       Body:  \"{short['body']}\"")
        print()

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
            print("Usage: python run_script_generator.py [--input FILE] [--no-save]", file=sys.stderr)
            sys.exit(1)

    # ── Locate content brief file ─────────────────────────────────────────────
    if input_file is None:
        try:
            input_file = _find_latest_brief_file()
        except FileNotFoundError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
    elif not input_file.exists():
        print(f"❌ Specified input file not found: {input_file}", file=sys.stderr)
        sys.exit(1)

    print(f"\n📄 Input Content Brief File: {input_file}")

    # ── Process & Generate ────────────────────────────────────────────────────
    try:
        if save_output:
            out_file = script_generator.process_brief_file(input_file, SCRIPT_DIR)
            print(f"📂 Script saved to: {out_file}", file=sys.stderr)
            # Load and print
            script = json.loads(out_file.read_text(encoding="utf-8"))
        else:
            brief = json.loads(input_file.read_text(encoding="utf-8"))
            script = script_generator.generate_script(brief)
            print("🔬 [DRY RUN] Skipping file persistence.", file=sys.stderr)
        
        print_script(script)
    except Exception as e:
        print(f"\n❌ FAILED TO GENERATE SCRIPT: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
