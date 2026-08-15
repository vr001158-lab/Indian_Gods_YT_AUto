"""
Phase 6.2 Audit Script — Music Presence & Loudness Analysis
Measures narration level, music level, and overall loudness in final MP4s.
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")
import subprocess
import json
import re
from pathlib import Path

videos = {
    "hi-IN": Path("data/videos/shiva_hi_final.mp4"),
    "te-IN": Path("data/videos/shiva_te_final.mp4"),
    "ta-IN": Path("data/videos/shiva_ta_final.mp4"),
}

print("=" * 60)
print("  AUDIO LOUDNESS AUDIT — ALL THREE FINAL VIDEOS")
print("=" * 60)

for lang, v in videos.items():
    print(f"\n── {lang}: {v} ──")
    if not v.exists():
        print(f"  ERROR: FILE MISSING!")
        continue

    # ffprobe streams
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_streams", str(v)],
        capture_output=True, text=True
    )
    streams = json.loads(r.stdout).get("streams", [])
    for s in streams:
        if s["codec_type"] == "video":
            print(f"  VIDEO stream: {s['width']}x{s['height']} {s['codec_name']} {s.get('pix_fmt','?')}")
        elif s["codec_type"] == "audio":
            print(f"  AUDIO stream: codec={s['codec_name']} sr={s['sample_rate']} ch={s['channels']}")

    # ffmpeg volumedetect — measures overall loudness of final mixed audio
    r2 = subprocess.run(
        ["ffmpeg", "-i", str(v), "-af", "volumedetect", "-vn",
         "-f", "null", "-"],
        capture_output=True, text=True
    )
    stderr = r2.stderr
    mean_vol = re.search(r"mean_volume:\s*([\-\d\.]+)\s*dB", stderr)
    max_vol  = re.search(r"max_volume:\s*([\-\d\.]+)\s*dB", stderr)
    print(f"  VOLUMEDETECT mean_volume: {mean_vol.group(1) if mean_vol else 'N/A'} dBFS")
    print(f"  VOLUMEDETECT max_volume:  {max_vol.group(1) if max_vol else 'N/A'} dBFS")

    # Check number of audio channels (if 2, could have music)
    # Try EBUR128 loudness analysis (ITU-R BS.1770)
    r3 = subprocess.run(
        ["ffmpeg", "-i", str(v), "-af", "ebur128=peak=true", "-vn",
         "-f", "null", "-"],
        capture_output=True, text=True
    )
    ebur = r3.stderr
    integrated = re.search(r"I:\s*([\-\d\.]+)\s*LUFS", ebur)
    lra       = re.search(r"LRA:\s*([\-\d\.]+)\s*LU", ebur)
    peak      = re.search(r"Peak:\s*([\-\d\.]+)\s*dBFS", ebur)
    truepeak  = re.findall(r"True peak:\s*([\-\d\.]+)\s*dBTP", ebur)
    print(f"  EBU R128 Integrated Loudness: {integrated.group(1) if integrated else 'N/A'} LUFS")
    print(f"  EBU R128 LRA: {lra.group(1) if lra else 'N/A'} LU")

print("\n" + "=" * 60)
print("  AUDIO FILE PRESENCE CHECK")
print("=" * 60)

# Check if music WAV file exists and is non-trivial
music_file = Path("assets/music/devotional/shiva_devotional_mystic_flute.wav")
drone_file = Path("assets/music/devotional/devotional_ambient_drone.wav")
print(f"\n  shiva_devotional_mystic_flute.wav: exists={music_file.exists()}, size={music_file.stat().st_size if music_file.exists() else 0}")
print(f"  devotional_ambient_drone.wav:      exists={drone_file.exists()}, size={drone_file.stat().st_size if drone_file.exists() else 0}")

# Probe music WAV loudness
if music_file.exists():
    r4 = subprocess.run(
        ["ffmpeg", "-i", str(music_file), "-af", "volumedetect", "-vn",
         "-f", "null", "-"],
        capture_output=True, text=True
    )
    m_mean = re.search(r"mean_volume:\s*([\-\d\.]+)\s*dB", r4.stderr)
    m_max  = re.search(r"max_volume:\s*([\-\d\.]+)\s*dB", r4.stderr)
    print(f"\n  BGM WAV mean_volume: {m_mean.group(1) if m_mean else 'N/A'} dBFS")
    print(f"  BGM WAV max_volume:  {m_max.group(1) if m_max else 'N/A'} dBFS")

print("\n" + "=" * 60)
print("  COMPOSER BGM VOLUME SETTING AUDIT")
print("=" * 60)
print("""
  In render_phase6_validation_builds.py, the call was:
    render_multilingual_video(..., bgm_volume=0.10, ...)

  In FFmpegVideoComposer.build_ffmpeg_command():
    filter_parts.append(f\"[{bgm_idx}:a]volume={bgm_volume}[a_bgm]\")
    → [10:a]volume=0.1[a_bgm]
    → then: amix=inputs=2:duration=first:dropout_transition=2

  volume=0.10 means linear scale: -20 dBFS relative to input.
  If BGM WAV itself is at ~-20 dBFS (very quiet drone),
  the mixed result would be: -20 + (-20 log10(0.10)) = -20 + (-20) = -40 dBFS
  This is effectively INAUDIBLE under narration at -4 dBFS.
""")
