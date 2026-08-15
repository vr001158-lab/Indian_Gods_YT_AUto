import os
import hashlib
import json
import subprocess
from pathlib import Path

music_dir = Path("assets/music/devotional")
music_dir.mkdir(parents=True, exist_ok=True)
wav_path = music_dir / "devotional_ambient_drone.wav"

# Generate 60s soft tanpura harmonic ambient drone audio at 48 kHz stereo
cmd = [
    "ffmpeg", "-y", "-f", "lavfi",
    "-i", "aevalsrc=0.08*sin(2*PI*138.59*t)+0.04*sin(2*PI*207.65*t)+0.04*sin(2*PI*277.18*t)+0.02*sin(2*PI*554.37*t):s=48000:c=stereo:d=60",
    "-af", "lowpass=f=1200,afade=t=in:st=0:d=3,afade=t=out:st=57:d=3",
    "-c:a", "pcm_s16le",
    str(wav_path)
]

res = subprocess.run(cmd, capture_output=True, text=True)
assert res.returncode == 0, f"FFmpeg music generation failed: {res.stderr}"

# Compute SHA256 & file size
raw_bytes = wav_path.read_bytes()
file_sha256 = hashlib.sha256(raw_bytes).hexdigest()
file_size = len(raw_bytes)

# Probe audio stats using ffprobe
cmd_probe = [
    "ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(wav_path)
]
res_probe = subprocess.run(cmd_probe, capture_output=True, text=True)
probe_data = json.loads(res_probe.stdout)

stream = probe_data["streams"][0]
fmt = probe_data["format"]

manifest_data = {
    "tracks": [
        {
            "filename": wav_path.name,
            "relative_path": str(wav_path.as_posix()),
            "category": "devotional",
            "style": "Soft tanpura harmonic ambient drone",
            "source_type": "original_generated",
            "external_source": False,
            "copyright_source": "none",
            "license": "original/generated",
            "generator": "FFmpeg aevalsrc",
            "approved": True,
            "sha256": file_sha256,
            "file_size_bytes": file_size,
            "duration_seconds": float(fmt.get("duration", 60.0)),
            "sample_rate": int(stream.get("sample_rate", 48000)),
            "channels": int(stream.get("channels", 2)),
            "codec_name": stream.get("codec_name", "pcm_s16le")
        }
    ]
}

manifest_path = Path("assets/music/music_manifest.json")
manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")

print(f"Generated music asset: {wav_path}")
print(f"SHA256: {file_sha256}")
print(f"Saved manifest: {manifest_path}")
