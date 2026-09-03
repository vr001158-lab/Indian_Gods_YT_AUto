"""
run_visual_generator.py — Visual Generation Engine CLI (Phase 2F)
Converts approved production scripts into scene-by-scene visual assets and mappings.

Usage:
  python run_visual_generator.py                        # auto-picks latest script JSON
  python run_visual_generator.py --input <file>         # explicit script file path
  python run_visual_generator.py --provider flux        # select visual engine (flux/stable_diffusion/mock)
  python run_visual_generator.py --style-preset "Preset" # supply target visual style details
  python run_visual_generator.py --no-save              # skip writing visual map JSON to disk
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

from src.visual import generator as visual_generator

SCRIPT_DIR = Path("data/scripts")
VISUAL_DIR = Path("data/visuals")
DEFAULT_STYLE = "Devotional Cinematic Painting, 8k, divine golden glow"


def _find_latest_script_file() -> Path:
    """Returns the most recently created script_*.json file."""
    files = sorted(SCRIPT_DIR.glob("script_*.json"))
    if not files:
        raise FileNotFoundError(
            f"❌ No script_*.json files found in {SCRIPT_DIR}.\n"
            "   Run: python run_script_generator.py   to run script generation first."
        )
    return files[-1]


def print_visual_map(visual_map: dict):
    """Outputs the formatted visual mapping to stdout."""
    print("\n" + "=" * 60)
    print("🌅  DIVINE DHARSHANAM DAILY — VISUAL TIMING MAP")
    print("=" * 60)

    print(f"\n🎯  TITLE:            {visual_map['script_title']}")
    print(f"🖼️   VISUAL PROVIDER:  {visual_map['provider'].upper()}")
    print(f"🎨  STYLE PRESET:     {visual_map['style_preset']}")
    print(f"🎬  TOTAL SCENES:     {visual_map['total_scenes']}")

    print(f"\n{'─' * 60}")
    print("🌅  SYNCHRONIZED VISUAL TRACKS:")
    for scene in visual_map["visual_scenes"]:
        print(f"   Scene #{scene['scene']} ({scene['duration_seconds']}s):")
        print(f"       Visual Prompt: \"{scene['visual_prompt'][:80]}...\"")
        print(f"       Image File:    {scene['image_file']}")
        print()

    print("=" * 60)


def main():
    input_file = None
    provider_name = "mock"
    style_preset = DEFAULT_STYLE
    format_type = "narrated"
    content_type = "short"
    save_output = True

    # ── CLI parsing ───────────────────────────────────────────────────────────
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--input" and i + 1 < len(args):
            input_file = Path(args[i + 1])
            i += 2
        elif args[i] == "--provider" and i + 1 < len(args):
            provider_name = args[i + 1].lower()
            i += 2
        elif args[i] == "--style-preset" and i + 1 < len(args):
            style_preset = args[i + 1]
            i += 2
        elif args[i] == "--format" and i + 1 < len(args):
            format_type = args[i + 1].lower().strip()
            i += 2
        elif args[i] == "--content-type" and i + 1 < len(args):
            content_type = args[i + 1].lower().strip()
            i += 2
        elif args[i] == "--no-save":
            save_output = False
            i += 1
        else:
            print(f"❌ Unknown argument: {args[i]}", file=sys.stderr)
            print("Usage: python run_visual_generator.py [--input FILE] [--provider NAME] [--style-preset PRESET] [--format narrated|old] [--content-type short|long] [--no-save]", file=sys.stderr)
            sys.exit(1)

    # ── Locate script file ────────────────────────────────────────────────────
    if input_file is None:
        try:
            input_file = _find_latest_script_file()
        except FileNotFoundError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
    elif not input_file.exists():
        print(f"❌ Specified input file not found: {input_file}", file=sys.stderr)
        sys.exit(1)

    print(f"\n📄 Input Script File: {input_file}")

    # ── Process & Generate ────────────────────────────────────────────────────
    try:
        if save_output:
            out_file = visual_generator.process_script_file(
                script_path=input_file,
                provider_name=provider_name,
                style_preset=style_preset,
                output_dir=VISUAL_DIR,
                format=format_type,
                content_type=content_type,
            )
            print(f"📂 Visual map saved to: {out_file}", file=sys.stderr)
            visual_map = json.loads(out_file.read_text(encoding="utf-8"))
        else:
            script = json.loads(input_file.read_text(encoding="utf-8"))
            visual_map = visual_generator.generate_visual_mapping(
                script=script,
                provider_name=provider_name,
                style_preset=style_preset,
                output_dir=VISUAL_DIR,
                format=format_type,
                content_type=content_type,
            )
            print("🔬 [DRY RUN] Skipping visual map file persistence.", file=sys.stderr)
        
        print_visual_map(visual_map)
    except Exception as e:
        print(f"\n❌ FAILED TO GENERATE VISUAL MAP: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
