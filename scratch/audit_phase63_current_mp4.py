import sys
sys.stdout.reconfigure(encoding="utf-8")
import subprocess
import json
import re
from pathlib import Path

video = Path("data/videos/shiva_hi_final.mp4")

print("=" * 60)
print("  PHASE 6.3 AUDIT: CURRENT MP4 AUDIO WAVEFORM ANALYSIS")
print("=" * 60)

if not video.exists():
    print(f"ERROR: {video} missing!")
    sys.exit(1)

# 1. ffprobe stream info
r1 = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", str(video)], capture_output=True, text=True)
streams = json.loads(r1.stdout).get("streams", [])
audio_stream = next((s for s in streams if s["codec_type"] == "audio"), {})
print(f"Audio Stream: codec={audio_stream.get('codec_name')} | sample_rate={audio_stream.get('sample_rate')} Hz | channels={audio_stream.get('channels')}")

# 2. Volume detect overall
r2 = subprocess.run(["ffmpeg", "-i", str(video), "-af", "volumedetect", "-vn", "-f", "null", "-"], capture_output=True, text=True)
mean_vol = re.search(r"mean_volume:\s*([\-\d\.]+)\s*dB", r2.stderr)
max_vol  = re.search(r"max_volume:\s*([\-\d\.]+)\s*dB", r2.stderr)
print(f"Overall Audio Mean Loudness: {mean_vol.group(1) if mean_vol else '?'} dBFS")
print(f"Overall Audio Max Peak:     {max_vol.group(1) if max_vol else '?'} dBFS")

# 3. Inspect standalone narration MP3 vs final mixed MP4
narr_mp3 = Path("data/audio/audio_map_hi-IN_phase6.json")
if narr_mp3.exists():
    amap = json.loads(narr_mp3.read_text(encoding="utf-8"))
    narr_file = Path(amap["audio_scenes"][0]["audio_file"])
    if narr_file.exists():
        r3 = subprocess.run(["ffmpeg", "-i", str(narr_file), "-af", "volumedetect", "-vn", "-f", "null", "-"], capture_output=True, text=True)
        n_mean = re.search(r"mean_volume:\s*([\-\d\.]+)\s*dB", r3.stderr)
        n_max  = re.search(r"max_volume:\s*([\-\d\.]+)\s*dB", r3.stderr)
        print(f"\nStandalone Hindi Scene 1 Narration Mean: {n_mean.group(1) if n_mean else '?'} dBFS")

print("""
AUDIT VERDICT ON CURRENT MUSIC:
- The background track used previously was an FFmpeg synthesized sine-wave harmonic drone (Om 136.1Hz oscillator).
- While technically encoded in the audio stream, it lacks musical dynamics, instruments (flute/tanpura/sitar), rhythm, or emotional resonance.
- To a human listener, it sounds like low static/hum or silence rather than authentic Indian devotional background music.
""")
