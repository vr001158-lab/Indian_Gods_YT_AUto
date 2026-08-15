"""
Register Verified YouTube Audio Library Primary Track
Copies data/audio/Downloadrd_yt_music/Aalaap in Raag Jhinjhoti - Sandeep Das, Adhiraj Chaudhuri.mp3
to assets/music/devotional/youtube_audio_library_aalaap_jhinjhoti.mp3
and registers it in music_manifest.json with SHA256 00f72537ebd3c24ad6e5c1d1f6645c717cd6a755d63572833999b36a364faa9b.
"""

import os
import shutil
import hashlib
import json
import subprocess
from pathlib import Path

source_p = Path("data/audio/Downloadrd_yt_music/Aalaap in Raag Jhinjhoti - Sandeep Das, Adhiraj Chaudhuri.mp3")
dest_p   = Path("assets/music/devotional/youtube_audio_library_aalaap_jhinjhoti.mp3")

dest_p.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(source_p, dest_p)

sha256_val = hashlib.sha256(dest_p.read_bytes()).hexdigest()
size_bytes = dest_p.stat().st_size

EXPECTED_SHA = "00f72537ebd3c24ad6e5c1d1f6645c717cd6a755d63572833999b36a364faa9b"
assert sha256_val == EXPECTED_SHA, f"SHA256 mismatch! Got {sha256_val}"
print(f"[OK] Copied verified primary track: {dest_p} ({size_bytes:,} bytes, SHA256: {sha256_val})")

# Probe duration, sample rate, etc.
r = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format", str(dest_p)], capture_output=True, text=True)
info = json.loads(r.stdout)
fmt = info.get("format", {})
astream = next((s for s in info.get("streams", []) if s["codec_type"] == "audio"), {})

manifest_data = {
  "tracks": [
    {
      "filename": "youtube_audio_library_aalaap_jhinjhoti.mp3",
      "relative_path": "assets/music/devotional/youtube_audio_library_aalaap_jhinjhoti.mp3",
      "track_name": "Aalaap in Raag Jhinjhoti",
      "artist": "Sandeep Das, Adhiraj Chaudhuri",
      "deity_relevance": "Lord Shiva / Contemplative Devotional Dharshanam",
      "category": "devotional",
      "style": "Acoustic Indian Classical Raag Jhinjhoti Aalaap",
      "source": "YouTube Audio Library",
      "source_url": "https://www.youtube.com/audiolibrary",
      "license": "YouTube Audio Library License",
      "attribution_requirement": "None",
      "source_type": "youtube_audio_library",
      "commercial_use": True,
      "youtube_shorts_permitted": True,
      "external_source": True,
      "copyright_source": "youtube_audio_library",
      "approved": True,
      "sha256": EXPECTED_SHA,
      "file_size_bytes": size_bytes,
      "duration_seconds": round(float(fmt.get("duration", 0)), 2),
      "sample_rate": int(astream.get("sample_rate", 44100)),
      "channels": int(astream.get("channels", 2)),
      "codec_name": astream.get("codec_name", "mp3"),
      "date_selected": "2026-08-14"
    },
    {
      "filename": "shiva_devotional_shivaranjani_flute.wav",
      "relative_path": "assets/music/devotional/shiva_devotional_shivaranjani_flute.wav",
      "track_name": "Shiva Kailash Raga Shivaranjani Bansuri & Tanpura",
      "deity_relevance": "Lord Shiva / Samudra Manthan / Contemplative Divine Dharshanam",
      "category": "devotional",
      "style": "Raga Shivaranjani Bamboo Flute (Bansuri), Tanpura Drone (136.1Hz Om), Temple Bell",
      "source": "Synthesized acoustic modal composition (Raga Shivaranjani scale modeling)",
      "source_url": "internal://assets/music/devotional/shiva_devotional_shivaranjani_flute.wav",
      "license": "original/generated",
      "attribution_requirement": "None",
      "source_type": "original_generated",
      "commercial_use": True,
      "youtube_shorts_permitted": True,
      "external_source": False,
      "copyright_source": "none",
      "generator": "Acoustic Modal Synthesizer (Bansuri, Tanpura, Ghanta Bell)",
      "approved": True,
      "sha256": "8aa5209f8238dffd53086745edfbbc51864586777b3a6550098d14db563717c2",
      "file_size_bytes": 11520044,
      "duration_seconds": 60.0,
      "sample_rate": 48000,
      "channels": 2,
      "codec_name": "pcm_s16le",
      "date_selected": "2026-08-14"
    }
  ]
}

manifest_path = Path("assets/music/music_manifest.json")
manifest_path.write_text(json.dumps(manifest_data, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"[OK] Registered primary track in music_manifest.json!")
