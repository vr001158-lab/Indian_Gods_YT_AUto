"""
run_thumbnail_generator.py — Thumbnail Generation Pipeline CLI (Phase 2H / Phase 4)
Converts approved topic decisions and Telugu scripts into high-quality YouTube thumbnails.
Pollinations is the exclusive AI image generation provider for backgrounds.
PIL handles Telugu typography, channel branding ('దైవ దర్శనం'), and final 1280x720 composition.

Usage:
  python run_thumbnail_generator.py                             # auto-picks latest decision & script
  python run_thumbnail_generator.py --input <decision_file>     # explicit decision file
  python run_thumbnail_generator.py --script <script_file>       # explicit script file (for Telugu title)
  python run_thumbnail_generator.py --provider pollinations     # exclusive AI engine (pollinations/pil/mock)
  python run_thumbnail_generator.py --bg background.png          # mix custom background image
  python run_thumbnail_generator.py --no-save                   # skip writing metadata JSON to disk
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
from src.thumbnail.generator import (
    PollinationsThumbnailGenerator,
    PILThumbnailGenerator,
    MockThumbnailGenerator,
    FluxThumbnailGenerator,
    ThumbnailReuseGenerator,
)
from src.thumbnail.analyzer import analyze_thumbnail_file
from src.thumbnail.schemas import validate_metadata_output

DECISION_DIR = Path("data/decision")
SCRIPTS_DIR = Path("data/scripts")
THUMBNAIL_DIR = Path("data/thumbnails")

PROVIDERS = {
    "reuse":        ThumbnailReuseGenerator,
    "pollinations": PollinationsThumbnailGenerator,
    "pil":          PILThumbnailGenerator,
    "mock":         MockThumbnailGenerator,
    "flux":         FluxThumbnailGenerator,
}


def _find_latest_file(directory: Path, pattern: str) -> Path:
    """Returns the most recently created file matching a pattern."""
    files = sorted(directory.glob(pattern), key=lambda p: p.stat().st_mtime)
    if not files:
        raise FileNotFoundError(f"❌ No files matching {pattern} found in {directory}.")
    return files[-1]


def main():
    input_file = None
    script_file = None
    provider_name = "pollinations"
    bg_image = None
    save_output = True
    language_code = None
    visual_map_file = None
    video_file = None

    # ── CLI parsing ───────────────────────────────────────────────────────────
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--input" and i + 1 < len(args):
            input_file = Path(args[i + 1])
            i += 2
        elif args[i] == "--script" and i + 1 < len(args):
            script_file = Path(args[i + 1])
            i += 2
        elif args[i] in ("--language", "-l") and i + 1 < len(args):
            language_code = args[i + 1].strip()
            i += 2
        elif args[i] == "--provider" and i + 1 < len(args):
            provider_name = args[i + 1].lower()
            i += 2
        elif args[i] == "--bg" and i + 1 < len(args):
            bg_image = Path(args[i + 1])
            i += 2
        elif args[i] == "--visual-map" and i + 1 < len(args):
            visual_map_file = Path(args[i + 1])
            i += 2
        elif args[i] == "--video" and i + 1 < len(args):
            video_file = Path(args[i + 1])
            i += 2
        elif args[i] == "--no-save":
            save_output = False
            i += 1
        else:
            print(f"❌ Unknown argument: {args[i]}", file=sys.stderr)
            print(
                "Usage: python run_thumbnail_generator.py [--input DECISION] [--script SCRIPT] "
                "[--language te-IN] [--provider reuse|pollinations|pil|mock] [--bg FILE] "
                "[--visual-map FILE] [--video FILE] [--no-save]",
                file=sys.stderr,
            )
            sys.exit(1)

    # ── Provider check ────────────────────────────────────────────────────────
    if provider_name == "flux":
        print(
            "❌ Architectural Violation: Flux is strictly prohibited for YouTube thumbnails.\n"
            "   Flux is reserved exclusively for video scene generation.\n"
            "   Pollinations is the exclusive AI thumbnail image generation provider.",
            file=sys.stderr,
        )
        sys.exit(1)

    if provider_name not in PROVIDERS:
        print(f"❌ Unknown provider: {provider_name} (must be one of {list(PROVIDERS.keys())})", file=sys.stderr)
        sys.exit(1)

    # ── Auto-locate decision file ─────────────────────────────────────────────
    if input_file is None:
        try:
            input_file = _find_latest_file(DECISION_DIR, "decision_*.json")
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

    # ── Resolve Title & Script ────────────────────────────────────────────────
    title = decision.get("selected_topic", "")
    deity = decision.get("deity", "Divine Deity")

    # If script_file is available or auto-discoverable, extract genuine Telugu title
    if script_file is None and SCRIPTS_DIR.exists():
        try:
            script_file = _find_latest_file(SCRIPTS_DIR, "script_*.json")
        except Exception:
            script_file = None

    if script_file and Path(script_file).exists():
        try:
            script_data = json.loads(Path(script_file).read_text(encoding="utf-8"))
            s_title = script_data.get("title")
            if s_title and s_title.strip():
                title = s_title.strip()
        except Exception as e:
            print(f"⚠️ Warning: Could not read title from script {script_file}: {e}", file=sys.stderr)

    resolved_lang = (
        language_code
        or decision.get("language_code")
        or (decision.get("approval_metadata") or {}).get("language_code")
        or os.environ.get("LANGUAGE_CODE", "te-IN")
    )

    main_title = title
    subtitle = "దైవ దర్శనం" if resolved_lang == "te-IN" else "दिव्य दर्शनम्"
    if ":" in title:
        parts = title.split(":", 1)
        main_title = parts[0].strip()
        subtitle = parts[1].strip()

    print("==================================================")
    print("DIVINE DHARSHANAM DAILY")
    print("THUMBNAIL GENERATOR (POLLINATIONS EXCLUSIVE)")
    print("==================================================")
    print(f"Main Title:  {main_title}")
    print(f"Subtitle:    {subtitle}")
    print(f"Deity:       {deity}")
    print(f"Provider:    {provider_name}")
    print(f"Language:    {resolved_lang}")
    print(f"Confidence:  {decision.get('confidence')}")
    print("\nGenerating thumbnail...")

    # ── Generate Thumbnail ────────────────────────────────────────────────────
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True)
    out_img = THUMBNAIL_DIR / f"thumbnail_{timestamp}.png"

    try:
        generator = PROVIDERS[provider_name]()
        generator.generate_thumbnail(
            title=main_title,
            subtitle=subtitle,
            output_path=out_img,
            background_image_path=bg_image,
            language_code=resolved_lang,
            deity=deity,
            main_event=decision.get("selected_topic"),
            emotional_theme=decision.get("suggested_angle"),
            visual_map_path=visual_map_file,
            video_path=video_file,
        )

        # ── Analyze Thumbnail ─────────────────────────────────────────────────
        analysis = analyze_thumbnail_file(
            out_img,
            expected_title=main_title,
            language_code=resolved_lang,
            allow_mock=(provider_name == "mock"),
        )
        if not analysis["valid"]:
            print(f"\n❌ Thumbnail generation produced invalid image: {analysis['errors']}", file=sys.stderr)
            sys.exit(1)

        # ── Write Metadata ────────────────────────────────────────────────────
        metadata = {
            "title":           title,
            "topic":           decision.get("selected_topic", title),
            "language_code":   resolved_lang,
            "provider":        provider_name,
            "resolution":      "1280x720",
            "format":          "png",
            "approved_source": decision["data_source"],
            "confidence":      decision["confidence"],
            "created_at":      timestamp,
            "approval_metadata": {
                "approved_for_generation": decision["approved_for_generation"],
                "selected_topic": decision["selected_topic"],
                "language_code": resolved_lang,
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
        print(f"\n❌ FAILED TO GENERATE THUMBNAIL (Prohibited or Unsupported Provider): {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ FAILED TO GENERATE THUMBNAIL: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
