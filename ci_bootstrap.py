import os
import wave
import struct
import json
import hashlib
from pathlib import Path
from PIL import Image

def bootstrap():
    """Generates minimal deterministic test fixtures for clean CI runners."""

    # ─────────────────────────────────────────────────────────────────────────────
    # 1. Create minimal valid 1280x720 PNG thumbnail and metadata
    # ─────────────────────────────────────────────────────────────────────────────
    thumb_dir = Path("data/thumbnails")
    thumb_dir.mkdir(parents=True, exist_ok=True)

    thumb_png = thumb_dir / "thumbnail_20260814_071510.png"
    if not thumb_png.exists():
        img = Image.new("RGB", (1280, 720), color=(20, 25, 40))
        img.save(thumb_png, format="PNG")
        print(f"[CI BOOTSTRAP] Thumbnail created: {thumb_png}")

    thumb_meta = thumb_dir / "thumbnail_metadata_20260814_071510.json"
    if not thumb_meta.exists():
        meta_data = {
            "created_at": "20260814_071510",
            "format": "png",
            "width": 1280,
            "height": 720,
            "topic": "Why Lord Shiva Wears a Snake Around His Neck",
            "provider": "pil"
        }
        thumb_meta.write_text(json.dumps(meta_data, indent=2), encoding="utf-8")
        print(f"[CI BOOTSTRAP] Thumbnail metadata created: {thumb_meta}")

    # ─────────────────────────────────────────────────────────────────────────────
    # 2. Shared visual asset plan fixture (data/visuals/asset_plan_20260814_071510.json)
    # ─────────────────────────────────────────────────────────────────────────────
    visuals_dir = Path("data/visuals")
    visuals_dir.mkdir(parents=True, exist_ok=True)
    asset_plan_file = visuals_dir / "asset_plan_20260814_071510.json"

    if not asset_plan_file.exists():
        asset_plan_content = {
            "topic": "Secrets of Shiva's Snake: The Mastery Over Ego and Poison",
            "deity": "lord_shiva",
            "created_at": "2026-08-14T07:15:10.915458+00:00",
            "approval_metadata": {
                "approved_for_generation": True,
                "selected_topic": "Why Lord Shiva Wears a Snake Around His Neck",
                "score": 66,
                "confidence": "high",
                "data_source": "youtube_api",
                "category": "Stories of deities"
            },
            "scenes": [
                {
                    "scene": 1,
                    "asset_type": "image",
                    "asset": "assets/gods/lord_shiva/#shiva #shivratri #shivling #shivshankar #mahadev.jpg",
                    "asset_id": "#shiva #shivratri #shivling #shivshankar #mahadev",
                    "deity": "lord_shiva",
                    "source": "repository",
                    "reason_for_selection": "Semantic match in repository deity assets",
                    "validation_result": "OK"
                },
                {
                    "scene": 2,
                    "asset_type": "image",
                    "asset": "assets/gods/lord_shiva/Divine Trident of Cosmic Power⚡️🔱 Powerful Shiva Trishul Wallpaper in Blue Cosmtic Energy.jpg",
                    "asset_id": "Divine Trident of Cosmic Power",
                    "deity": "lord_shiva",
                    "source": "repository",
                    "reason_for_selection": "Semantic match in repository deity assets",
                    "validation_result": "OK"
                },
                {
                    "scene": 3,
                    "asset_type": "image",
                    "asset": "assets/gods/lord_shiva/Divine Trident of Cosmic Power⚡️🔱 Powerful Shiva Trishul Wallpaper in Blue Cosmtic Energy.jpg",
                    "asset_id": "Divine Trident of Cosmic Power",
                    "deity": "lord_shiva",
                    "source": "repository",
                    "reason_for_selection": "Semantic match in repository deity assets",
                    "validation_result": "OK"
                },
                {
                    "scene": 4,
                    "asset_type": "image",
                    "asset": "assets/gods/lord_shiva/#shiva #shivratri #shivling #shivshankar #mahadev.jpg",
                    "asset_id": "#shiva #shivratri #shivling #shivshankar #mahadev",
                    "deity": "lord_shiva",
                    "source": "repository",
                    "reason_for_selection": "Semantic match in repository deity assets",
                    "validation_result": "OK"
                },
                {
                    "scene": 5,
                    "asset_type": "image",
                    "asset": "assets/gods/lord_shiva/181199585004244858.jpg",
                    "asset_id": "181199585004244858",
                    "deity": "lord_shiva",
                    "source": "repository",
                    "reason_for_selection": "Deity repository asset fallback",
                    "validation_result": "OK"
                }
            ]
        }
        asset_plan_file.write_text(json.dumps(asset_plan_content, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[CI BOOTSTRAP] Asset plan created: {asset_plan_file}")

    # ─────────────────────────────────────────────────────────────────────────────
    # 3. Deterministic WAV music fixture & music manifest sync
    # ─────────────────────────────────────────────────────────────────────────────
    music_paths = [
        Path("assets/music/devotional/shiva_devotional_shivaranjani_flute.wav"),
        Path("data/music/shiva_devotional_shivaranjani_flute.wav"),
    ]
    
    # Generate 1 second of deterministic 48 kHz 16-bit stereo silent WAV
    sample_rate = 48000
    duration = 1.0
    num_frames = int(sample_rate * duration)
    frames_bytes = struct.pack("<h", 0) * num_frames * 2

    for mpath in music_paths:
        mpath.parent.mkdir(parents=True, exist_ok=True)
        if not mpath.exists():
            with wave.open(str(mpath), "wb") as wav_file:
                wav_file.setnchannels(2)      # Stereo
                wav_file.setsampwidth(2)     # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(frames_bytes)
            print(f"[CI BOOTSTRAP] WAV created: {mpath}")

    primary_wav = music_paths[0]
    actual_wav_bytes = primary_wav.read_bytes()
    wav_sha256 = hashlib.sha256(actual_wav_bytes).hexdigest()
    wav_size = len(actual_wav_bytes)

    # Synchronize music_manifest.json provenance source of truth with bootstrap WAV
    manifest_path = Path("assets/music/music_manifest.json")
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
                "sha256": wav_sha256,
                "file_size_bytes": wav_size,
                "duration_seconds": duration,
                "sample_rate": sample_rate,
                "channels": 2,
                "codec_name": "pcm_s16le",
                "date_selected": "2026-08-14"
            }
        ]
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[CI BOOTSTRAP] Synced music_manifest.json with WAV SHA256: {wav_sha256[:16]}... ({wav_size} bytes)")

if __name__ == "__main__":
    bootstrap()
