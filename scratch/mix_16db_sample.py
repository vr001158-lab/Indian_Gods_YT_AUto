import subprocess
import json
import re
from pathlib import Path

SAMPLE_DIR = Path("data/audio/phase62_samples")
hi_mp3 = SAMPLE_DIR / "sample_hi_IN.mp3"
hi_wav = SAMPLE_DIR / "_hi_IN_for_mix.wav"
bgm_file = Path("assets/music/devotional/shiva_devotional_mystic_flute.wav")
mixed_out_16 = SAMPLE_DIR / "sample_mixed_hi_bgm_16db.aac"

# Convert narration to 48kHz stereo WAV first
subprocess.run([
    "ffmpeg", "-y", "-v", "error",
    "-i", str(hi_mp3),
    "-ar", "48000", "-ac", "2",
    str(hi_wav)
], check=True)

# Mix with BGM at -16.0dB
subprocess.run([
    "ffmpeg", "-y", "-v", "error",
    "-i", str(hi_wav),
    "-i", str(bgm_file),
    "-filter_complex",
    "[1:a]volume=-16.0dB[a_bgm];"
    "[0:a][a_bgm]amix=inputs=2:duration=first:dropout_transition=1:normalize=0[a_out]",
    "-map", "[a_out]",
    "-c:a", "aac", "-ar", "48000", "-ac", "2",
    str(mixed_out_16)
], check=True)

def probe(p):
    r = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format", str(p)], capture_output=True, text=True)
    d = json.loads(r.stdout)
    fmt = d.get("format", {})
    r2 = subprocess.run(["ffmpeg", "-i", str(p), "-af", "volumedetect", "-vn", "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"mean_volume:\s*([\-\d\.]+)", r2.stderr)
    mx = re.search(r"max_volume:\s*([\-\d\.]+)", r2.stderr)
    return float(fmt.get("duration", 0)), m.group(1) if m else "?", mx.group(1) if mx else "?"

dur1, m1, mx1 = probe(hi_wav)
dur2, m2, mx2 = probe(mixed_out_16)

print(f"Narration WAV: mean={m1} dBFS, max={mx1} dBFS")
print(f"Mixed (-16dB BGM): mean={m2} dBFS, max={mx2} dBFS")
print(f"[OK] Saved {mixed_out_16}")
