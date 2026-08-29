"""
run_video_generator.py — Video Composer Engine CLI (Phase 2G)
Compiles synchronized audio mapping tracks and visual assets into MP4 videos (Shorts or Long-form).

Usage:
  python run_video_generator.py                        # auto-picks latest maps, short format
  python run_video_generator.py --content-type long    # render as long-form (16:9 1920x1080)
  python run_video_generator.py --composer mock        # compile with mock compiler for tests
  python run_video_generator.py --bgm music.mp3        # mix background music track
  python run_video_generator.py --bgm-volume 0.10      # set background music mixing scale
  python run_video_generator.py --no-save              # skip writing video map JSON to disk
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

from src.video import generator as video_generator
from src.video.format_config import get_format_config, VALID_CONTENT_TYPES, DEFAULT_CONTENT_TYPE

AUDIO_DIR = Path("data/audio")
VISUAL_DIR = Path("data/visuals")
VIDEO_DIR = Path("data/videos")


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _is_mock_only(data: dict) -> bool:
    """
    Returns True when the map was produced by a mock provider AND lacks
    real approval_metadata — i.e. it is a dry-run map that should not
    enter production video composition.
    """
    provider = data.get("provider", "")
    meta = data.get("approval_metadata") or {}
    data_source = meta.get("data_source", "mock")
    return provider == "mock" and data_source not in ("youtube_api", "cached_youtube_api")


def _find_best_map(folder: Path, glob_pattern: str, label: str) -> Path:
    """
    Locate the most suitable timing-map JSON in *folder*.

    Priority:
      1. Non-mock maps with real youtube_api approval_metadata  (newest first)
      2. Any other map (newest first, as fallback)

    Raises FileNotFoundError when no files exist.
    """
    files = sorted(folder.glob(glob_pattern))
    if not files:
        raise FileNotFoundError(
            f"❌ No {glob_pattern} files found in {folder}.\n"
            f"   Generate {label} mapping files first."
        )

    production = [f for f in files if not _is_mock_only(_load_json(f))]
    return (production or files)[-1]  # newest production map, or newest of any


def _find_paired_maps(
    audio_dir: Path,
    visual_dir: Path,
) -> tuple:
    """
    Auto-discover a matching (audio_map_path, visual_map_path) pair.

    Matching strategy:
      1. Build candidate lists filtered to non-mock-only maps.
      2. Try to pair by ``run_id``.
      3. Fall back to pairing by ``script_title``.
      4. If no pair found, return the newest of each independently.
    """
    audio_files  = sorted(audio_dir.glob("audio_map_*.json"))
    visual_files = sorted(visual_dir.glob("visual_map_*.json"))

    if not audio_files:
        raise FileNotFoundError(f"❌ No audio_map_*.json found in {audio_dir}")
    if not visual_files:
        raise FileNotFoundError(f"❌ No visual_map_*.json found in {visual_dir}")

    # Filter to production maps
    prod_audio  = [f for f in audio_files  if not _is_mock_only(_load_json(f))]
    prod_visual = [f for f in visual_files if not _is_mock_only(_load_json(f))]

    candidates_a = prod_audio  or audio_files
    candidates_v = prod_visual or visual_files

    # Build lookup dicts keyed by run_id and script_title
    def _index(files, key_fields):
        idx = {}
        for f in files:
            d = _load_json(f)
            for field in key_fields:
                val = d.get(field)
                if val:
                    idx.setdefault(val, []).append(f)
        return idx

    a_by_run   = _index(candidates_a, ["run_id"])
    v_by_run   = _index(candidates_v, ["run_id"])
    a_by_title = _index(candidates_a, ["script_title"])
    v_by_title = _index(candidates_v, ["script_title"])

    # Try run_id matching
    shared_runs = set(a_by_run) & set(v_by_run)
    if shared_runs:
        best_run = sorted(shared_runs)[-1]  # lexicographically latest
        return a_by_run[best_run][-1], v_by_run[best_run][-1]

    # Try script_title matching
    shared_titles = set(a_by_title) & set(v_by_title)
    if shared_titles:
        best_title = sorted(shared_titles)[-1]
        return a_by_title[best_title][-1], v_by_title[best_title][-1]

    # Last resort: newest of each
    return candidates_a[-1], candidates_v[-1]


def print_video_summary(video_map: dict):
    """Outputs a summary of the composed video to stdout."""
    ct = video_map.get("content_type", "short").upper()
    ar = video_map.get("aspect_ratio", "")
    res = video_map.get("resolution", "")

    print("\n" + "=" * 60)
    print("🌅  DIVINE DHARSHANAM DAILY — VIDEO COMPOSITION SUMMARY")
    print("=" * 60)

    print(f"\n🎥  VIDEO FILE:      {video_map['video_file']}")
    print(f"📂  VIDEO MAP:       {video_map['video_map_file']}")
    print(f"⏱️   TOTAL DURATION:   {video_map['total_duration']} seconds ({video_map['total_duration'] // 60}m {video_map['total_duration'] % 60}s)")
    print(f"🏷️   CONTENT TYPE:     {ct}")
    print(f"📐  ASPECT RATIO:     {ar}")
    print(f"🖥️   RESOLUTION:       {res}")

    print(f"\n{'─' * 60}")
    print("🎬  SYNCHRONIZED VIDEO SCENES:")
    for scene in video_map["scenes"]:
        print(f"   Scene #{scene['scene']} ({scene['duration_seconds']}s):")
        print(f"       Image: {scene['image_file']}")
        print(f"       Audio: {scene['audio_file']}")
        print()

    print("=" * 60)


def main():
    audio_map_path = None
    visual_map_path = None
    composer_type = "ffmpeg"
    background_music = None
    bgm_volume = 0.15
    save_output = True
    content_type = DEFAULT_CONTENT_TYPE

    # ── CLI parsing ───────────────────────────────────────────────────────────
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--audio-map" and i + 1 < len(args):
            audio_map_path = Path(args[i + 1])
            i += 2
        elif args[i] == "--visual-map" and i + 1 < len(args):
            visual_map_path = Path(args[i + 1])
            i += 2
        elif args[i] == "--composer" and i + 1 < len(args):
            composer_type = args[i + 1].lower()
            i += 2
        elif args[i] == "--bgm" and i + 1 < len(args):
            background_music = Path(args[i + 1])
            i += 2
        elif args[i] == "--bgm-volume" and i + 1 < len(args):
            try:
                bgm_volume = float(args[i + 1])
            except ValueError:
                print(f"❌ Invalid volume factor: {args[i+1]}", file=sys.stderr)
                sys.exit(1)
            i += 2
        elif args[i] == "--content-type" and i + 1 < len(args):
            content_type = args[i + 1].lower().strip()
            if content_type not in VALID_CONTENT_TYPES:
                print(f"❌ Invalid content-type: '{args[i+1]}'. Must be one of {sorted(VALID_CONTENT_TYPES)}", file=sys.stderr)
                sys.exit(1)
            i += 2
        elif args[i] == "--no-save":
            save_output = False
            i += 1
        else:
            print(f"❌ Unknown argument: {args[i]}", file=sys.stderr)
            print("Usage: python run_video_generator.py [--content-type short|long] [--audio-map FILE] [--visual-map FILE] [--composer TYPE] [--bgm FILE] [--bgm-volume VOLUME] [--no-save]", file=sys.stderr)
            sys.exit(1)

    # ── Auto-locate map files if needed ───────────────────────────────────────
    try:
        if audio_map_path is None and visual_map_path is None:
            audio_map_path, visual_map_path = _find_paired_maps(AUDIO_DIR, VISUAL_DIR)
        else:
            if audio_map_path is None:
                audio_map_path = _find_best_map(AUDIO_DIR, "audio_map_*.json", "audio timing")
            elif not audio_map_path.exists():
                print(f"❌ Audio map not found: {audio_map_path}", file=sys.stderr)
                sys.exit(1)

            if visual_map_path is None:
                visual_map_path = _find_best_map(VISUAL_DIR, "visual_map_*.json", "visual timing")
            elif not visual_map_path.exists():
                print(f"❌ Visual map not found: {visual_map_path}", file=sys.stderr)
                sys.exit(1)
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    # Load audio map to detect format and extract BGM if needed
    try:
        audio_map_data = json.loads(audio_map_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"❌ Failed to parse audio map: {e}", file=sys.stderr)
        sys.exit(1)

    if background_music is None:
        if audio_map_data.get("format") == "old" or audio_map_data.get("audio_type") == "music_only":
            bgm_str = audio_map_data.get("full_narration_audio_file")
            if bgm_str:
                background_music = Path(bgm_str)
                print(f"🎵 Auto-detected OLD-format BGM from audio map: {background_music}")

    print(f"\n🏷️ Content Type:    {content_type.upper()}")
    print(f"📄 Input Audio Map:  {audio_map_path}")
    print(f"📄 Input Visual Map: {visual_map_path}")

    # ── Process & Compose ────────────────────────────────────────────────────
    try:
        if save_output:
            out_file = video_generator.process_mapping_files(
                audio_map_path=audio_map_path,
                visual_map_path=visual_map_path,
                composer_type=composer_type,
                background_music=background_music,
                bgm_volume=bgm_volume,
                output_dir=VIDEO_DIR,
                content_type=content_type,
            )
            print(f"📂 Video map saved to: {out_file}", file=sys.stderr)
            video_map = json.loads(out_file.read_text(encoding="utf-8"))
        else:
            audio_map = json.loads(audio_map_path.read_text(encoding="utf-8"))
            visual_map = json.loads(visual_map_path.read_text(encoding="utf-8"))
            video_map = video_generator.compose_video_pipeline(
                audio_map=audio_map,
                visual_map=visual_map,
                composer_type=composer_type,
                background_music=background_music,
                bgm_volume=bgm_volume,
                output_dir=VIDEO_DIR,
                content_type=content_type,
            )
            print("🔬 [DRY RUN] Skipping video map file persistence.", file=sys.stderr)

        print_video_summary(video_map)
    except Exception as e:
        print(f"\n❌ FAILED TO COMPOSE VIDEO: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
