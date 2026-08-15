import os
import wave
import struct
import json
from pathlib import Path
from PIL import Image

def bootstrap():
    """Generates minimal lightweight test fixtures for clean CI runners."""
    # 1. Create minimal valid 1280x720 PNG thumbnail and metadata
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

    # 2. Create minimal valid WAV music file
    music_paths = [
        Path("assets/music/devotional/shiva_devotional_shivaranjani_flute.wav"),
        Path("data/music/shiva_devotional_shivaranjani_flute.wav"),
    ]
    for mpath in music_paths:
        mpath.parent.mkdir(parents=True, exist_ok=True)
        if not mpath.exists():
            with wave.open(str(mpath), "wb") as wav_file:
                wav_file.setnchannels(2)      # Stereo
                wav_file.setsampwidth(2)     # 16-bit
                wav_file.setframerate(44100)  # 44.1 kHz
                # Write 1 second of silence
                frames = struct.pack("<h", 0) * 44100 * 2
                wav_file.writeframes(frames)
            print(f"[CI BOOTSTRAP] WAV created: {mpath}")

if __name__ == "__main__":
    bootstrap()
