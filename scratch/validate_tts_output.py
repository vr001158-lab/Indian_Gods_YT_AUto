"""Validate production TTS output with ffprobe and audio QA."""
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.voice.qa import perform_audio_qa, validate_audio_file_with_ffprobe


def ffprobe_detail(audio_path: Path) -> dict:
    res = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_format", "-show_streams",
            "-of", "json",
            str(audio_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    probe = json.loads(res.stdout)
    fmt = probe.get("format", {})
    aus = next(s for s in probe.get("streams", []) if s.get("codec_type") == "audio")
    bitrate = fmt.get("bit_rate") or aus.get("bit_rate")
    return {
        "file_size_bytes": audio_path.stat().st_size,
        "container": fmt.get("format_name", ""),
        "codec": aus.get("codec_name", ""),
        "sample_rate": int(aus.get("sample_rate", 0) or 0),
        "channels": int(aus.get("channels", 0) or 0),
        "bitrate": int(bitrate) if bitrate else None,
        "duration": round(float(fmt.get("duration", 0) or 0), 2),
    }


def main(audio_map_path: str) -> None:
    amap = json.loads(Path(audio_map_path).read_text(encoding="utf-8"))
    audio_file = Path(amap["full_narration_audio_file"])

    ffprobe = ffprobe_detail(audio_file)
    qa = perform_audio_qa(audio_file, allow_mock=False)

    report = {
        "language_code": amap.get("language_code"),
        "provider": amap.get("provider"),
        "voice_name": amap.get("voice_name"),
        "real_tts": amap.get("real_tts"),
        "mode": amap.get("mode"),
        "audio_file": str(audio_file),
        "ffprobe": ffprobe,
        "audio_qa": qa,
        "scene_durations": [s["duration_seconds"] for s in amap.get("audio_scenes", [])],
        "total_duration_seconds": amap.get("total_duration_seconds"),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scratch/validate_tts_output.py <audio_map.json>")
        sys.exit(1)
    main(sys.argv[1])
