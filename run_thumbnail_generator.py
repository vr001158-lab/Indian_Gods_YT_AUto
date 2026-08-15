"""
run_thumbnail_generator.py — Thumbnail Generation Pipeline CLI (Phase 2H)
Converts approved topic decisions into high-quality YouTube thumbnails.

Usage:
  python run_thumbnail_generator.py                        # auto-picks latest decision JSON
  python run_thumbnail_generator.py --input <file>         # explicit decision file path
  python run_thumbnail_generator.py --provider pil         # select engine (pil/mock/flux)
  python run_thumbnail_generator.py --bg background.png     # mix custom background image
  python run_thumbnail_generator.py --no-save              # skip writing metadata JSON to disk
"""

import sys
import os
import io
import json
import time
from pathlib import Path

# Force UTF-8 stdout/stderr on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

sys.path.insert(0, os.getcwd())

from src.thumbnail.validator import verify_or_raise_safety
from src.thumbnail.generator import PILThumbnailGenerator, MockThumbnailGenerator, FluxThumbnailGenerator
from src.thumbnail.analyzer import analyze_thumbnail_file
from src.thumbnail.schemas import validate_metadata_output

DECISION_DIR = Path("data/decision")
THUMBNAIL_DIR = Path("data/thumbnails")

PROVIDERS = {
    "pil":   PILThumbnailGenerator,
    "mock":  MockThumbnailGenerator,
    "flux":  FluxThumbnailGenerator,
}


def _find_latest_decision_file() -> Path:
    """Returns the most recently created decision_*.json file."""
    files = sorted(DECISION_DIR.glob("decision_*.json"))
    if not files:
        raise FileNotFoundError(
            f"❌ No decision_*.json files found in {DECISION_DIR}.\n"
            "   Run: run_research.py and run_decision.py first."
        )
    return files[-1]


def main():
    input_file = None
    provider_name = "pil"
    bg_image = None
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
        elif args[i] == "--bg" and i + 1 < len(args):
            bg_image = Path(args[i + 1])
            i += 2
        elif args[i] == "--no-save":
            save_output = False
            i += 1
        else:
            print(f"❌ Unknown argument: {args[i]}", file=sys.stderr)
            print("Usage: python run_thumbnail_generator.py [--input FILE] [--provider NAME] [--bg FILE] [--no-save]", file=sys.stderr)
            sys.exit(1)

    # ── Auto-locate decision file ─────────────────────────────────────────────
    if input_file is None:
        try:
            input_file = _find_latest_decision_file()
        except FileNotFoundError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
    elif not input_file.exists():
        print(f"❌ Specified input file not found: {input_file}", file=sys.stderr)
        sys.exit(1)

    # ── Load and validate decision safety ─────────────────────────────────────
    try:
        decision = json.loads(input_file.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"❌ Failed to parse decision JSON: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        verify_or_raise_safety(decision)
    except ValueError as e:
        print(f"❌ Safety Gate Rejection: {e}", file=sys.stderr)
        sys.exit(1)

    if provider_name not in PROVIDERS:
        print(f"❌ Unknown provider: {provider_name} (must be one of {list(PROVIDERS.keys())})", file=sys.stderr)
        sys.exit(1)

    # ── Setup print details ───────────────────────────────────────────────────
    title = decision["selected_topic"]
    deity = decision.get("deity", "Divine Deity")
    subtitle = f"Secrets of {deity.title()}"

    print("==================================================")
    print("DIVINE DHARSHANAM DAILY")
    print("THUMBNAIL GENERATOR")
    print("==================================================")
    print(f"\nDecision:\n{title}")
    print(f"\nSource:\n{decision['data_source']}")
    print(f"\nConfidence:\n{decision['confidence']}")
    print("\n\nGenerating thumbnail...")

    # ── Generate Thumbnail ────────────────────────────────────────────────────
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)
    out_img = THUMBNAIL_DIR / f"thumbnail_{timestamp}.png"

    try:
        generator = PROVIDERS[provider_name]()
        generator.generate_thumbnail(
            title=title,
            subtitle=subtitle,
            output_path=out_img,
            background_image_path=bg_image,
        )

        # ── Analyze Thumbnail ─────────────────────────────────────────────────
        analysis = analyze_thumbnail_file(out_img)
        if not analysis["valid"]:
            print(f"\n❌ Thumbnail generation produced invalid image: {analysis['errors']}", file=sys.stderr)
            sys.exit(1)

        # ── Write Metadata ────────────────────────────────────────────────────
        metadata = {
            "title":           title,
            "topic":           title,
            "provider":        provider_name,
            "resolution":      "1280x720",
            "format":          "png",
            "approved_source": decision["data_source"],
            "confidence":      decision["confidence"],
            "created_at":      timestamp,
            "approval_metadata": {
                "approved_for_generation": decision["approved_for_generation"],
                "selected_topic": decision["selected_topic"],
                "score": decision["score"],
                "confidence": decision["confidence"],
                "data_source": decision["data_source"],
            }
        }

        # Double check schema
        ok_schema, err_schema = validate_metadata_output(metadata)
        if not ok_schema:
            print(f"❌ Internal Error: Generated metadata fails schema: {err_schema}", file=sys.stderr)
            sys.exit(1)

        if save_output:
            out_meta = THUMBNAIL_DIR / f"thumbnail_metadata_{timestamp}.json"
            out_meta.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

        print("\nSUCCESS\n")
        print("Saved:\n")
        print(str(out_img.absolute()).replace("\\", "/"))
        print()

    except NotImplementedError as e:
        print(f"\n❌ FAILED TO GENERATE THUMBNAIL (Provider Placeholder): {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ FAILED TO GENERATE THUMBNAIL: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
