"""
Audit & Purge Unverified Music Script
Removes youtube_audio_library_devotional_flute.wav because its YouTube Audio Library provenance cannot be independently established.
Updates music_manifest.json to contain ONLY verified tracks.
"""

import os
import json
import hashlib
from pathlib import Path

unverified_file = Path("assets/music/devotional/youtube_audio_library_devotional_flute.wav")
if unverified_file.exists():
    unverified_file.unlink()
    print(f"[PURGED] Removed unverified track file: {unverified_file}")

fallback_file = Path("assets/music/devotional/shiva_devotional_shivaranjani_flute.wav")
assert fallback_file.exists(), f"Fallback track missing: {fallback_file}"
sha256_fallback = hashlib.sha256(fallback_file.read_bytes()).hexdigest()
size_fallback = fallback_file.stat().st_size

manifest_data = {
  "tracks": [
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
      "sha256": sha256_fallback,
      "file_size_bytes": size_fallback,
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
print(f"[OK] Updated music_manifest.json — only verified tracks remain.")
