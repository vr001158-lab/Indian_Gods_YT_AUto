"""
run_voice_generator.py — Voice Generation Engine CLI (Phase 3)
Converts approved production scripts into scene-synchronized audio mapping tracks.

Primary production provider: edge_neural_tts (Microsoft Edge Neural TTS)
  hi-IN → hi-IN-SwaraNeural
  te-IN → te-IN-ShrutiNeural
  ta-IN → ta-IN-PallaviNeural

Future premium provider: google_chirp3_hd (billing-gated, kept for future use)

Usage:
  python run_voice_generator.py                               # auto-picks latest script JSON
  python run_voice_generator.py --input <file>               # explicit script file path
  python run_voice_generator.py --provider edge_neural_tts   # production TTS (default)
  python run_voice_generator.py --provider mock --mode test   # unit-test style offline run
  python run_voice_generator.py --language hi-IN             # override language (else from script)
  python run_voice_generator.py --no-save                    # skip writing audio map JSON to disk
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

from src.voice import generator as voice_generator

SCRIPT_DIR = Path("data/scripts")
AUDIO_DIR = Path("data/audio")
PRODUCTION_PROVIDER = "edge_neural_tts"


def _find_latest_script_file() -> Path:
    """Returns the most recently created script_*.json file."""
    files = sorted(SCRIPT_DIR.glob("script_*.json"))
    if not files:
        raise FileNotFoundError(
            f"❌ No script_*.json files found in {SCRIPT_DIR}.\n"
            "   Run: python run_script_generator.py   to run script generation first."
        )
    return files[-1]


def print_audio_map(audio_map: dict):
    """Outputs the formatted voice mapping to stdout."""
    print("\n" + "=" * 60)
    print("🌅  DIVINE DHARSHANAM DAILY — VOICE TIMING MAP")
    print("=" * 60)

    print(f"\n🎯  TITLE:            {audio_map['script_title']}")
    print(f"🎙️   VOICE PROVIDER:   {audio_map['provider']}")
    print(f"🔊  REAL TTS:         {audio_map.get('real_tts')}")
    print(f"⚙️   MODE:             {audio_map.get('mode')}")
    print(f"🌐  LANGUAGE:         {audio_map.get('language_code')}")
    print(f"🗣️   VOICE:            {audio_map.get('voice_name')}")
    print(f"⏱️   TOTAL DURATION:   {audio_map['total_duration_seconds']} seconds "
          f"({audio_map['total_duration_seconds'] // 60}m "
          f"{audio_map['total_duration_seconds'] % 60}s)")
    print(f"🔗  FULL NARRATION:   {audio_map['full_narration_audio_file']}")
    if audio_map.get("audio_qa"):
        qa = audio_map["audio_qa"]
        print(
            f"📊  AUDIO QA:         duration={qa.get('duration')}s, "
            f"sample_rate={qa.get('sample_rate')}, channels={qa.get('channels')}"
        )

    print(f"\n{'─' * 60}")
    print("🎬  SYNCHRONIZED SCENE TRACKS:")
    for scene in audio_map["audio_scenes"]:
        preview = scene['voice_text'][:80]
        suffix = "..." if len(scene['voice_text']) > 80 else ""
        print(f"   Scene #{scene['scene']} ({scene['duration_seconds']}s):")
        print(f"       Voice Text: \"{preview}{suffix}\"")
        print(f"       Audio File:  {scene['audio_file']}")
        print()

    print("=" * 60)


def main():
    input_file = None
    provider_name = PRODUCTION_PROVIDER
    voice_id = "default"
    language_code = None
    mode = "production"
    format_type = "narrated"
    content_type = "short"
    save_output = True

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--input" and i + 1 < len(args):
            input_file = Path(args[i + 1])
            i += 2
        elif args[i] == "--provider" and i + 1 < len(args):
            provider_name = args[i + 1].lower()
            i += 2
        elif args[i] == "--voice-id" and i + 1 < len(args):
            voice_id = args[i + 1]
            i += 2
        elif args[i] == "--language" and i + 1 < len(args):
            language_code = args[i + 1]
            i += 2
        elif args[i] == "--mode" and i + 1 < len(args):
            mode = args[i + 1].lower()
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
            print(
                "Usage: python run_voice_generator.py "
                "[--input FILE] [--provider NAME] [--voice-id ID] "
                "[--language hi-IN|te-IN|ta-IN] [--mode production|test] [--format narrated|old] [--content-type short|long] [--no-save]",
                file=sys.stderr,
            )
            sys.exit(1)

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

    try:
        script = json.loads(input_file.read_text(encoding="utf-8"))
        if language_code:
            script["language_code"] = language_code

        if save_output:
            out_file = voice_generator.process_script_file(
                script_path=input_file,
                provider_name=provider_name,
                voice_id=voice_id,
                output_dir=AUDIO_DIR,
                mode=mode,
                language_code=language_code,
                format=format_type,
                content_type=content_type,
            )
            print(f"📂 Audio timing map saved to: {out_file}", file=sys.stderr)
            audio_map = json.loads(out_file.read_text(encoding="utf-8"))
        else:
            audio_map = voice_generator.generate_voice_mapping(
                script=script,
                provider_name=provider_name,
                voice_id=voice_id,
                output_dir=AUDIO_DIR,
                mode=mode,
                format=format_type,
                content_type=content_type,
            )
            print("🔬 [DRY RUN] Skipping timing map file persistence.", file=sys.stderr)

        print_audio_map(audio_map)
    except Exception as e:
        print(f"\n❌ FAILED TO GENERATE VOICE TIMING MAP: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
