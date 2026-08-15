import sys
import os
sys.path.insert(0, os.getcwd())

import json
import hashlib
from pathlib import Path
from src.video.generator import render_multilingual_video

asset_plan_path = Path("data/visuals/asset_plan_20260814_071510.json")

# Verify SHA256 before render
raw_bytes = asset_plan_path.read_bytes()
sha256_before = hashlib.sha256(raw_bytes).hexdigest()
print(f"Asset plan SHA256 before render: {sha256_before}")
expected_sha256 = "f6ca03a2dfec5add5b9bce5ce699124bfdffacf42f009b2a9d4b1c02a5f87b33"
assert sha256_before == expected_sha256, f"Asset plan SHA256 mismatch! Expected {expected_sha256}, got {sha256_before}"

tasks = [
    ("hi-IN", Path("data/audio/audio_map_20260814_141752.json"), Path("data/videos/shiva_hi_final.mp4")),
    ("te-IN", Path("data/audio/audio_map_20260814_141826.json"), Path("data/videos/shiva_te_final.mp4")),
    ("ta-IN", Path("data/audio/audio_map_20260814_141900.json"), Path("data/videos/shiva_ta_final.mp4")),
]

results = {}

for lang_code, audio_map_path, out_video_path in tasks:
    print(f"\n==================================================")
    print(f"Rendering final video for {lang_code}: {out_video_path}")
    print(f"==================================================")
    res = render_multilingual_video(
        language_code=lang_code,
        audio_map_path=audio_map_path,
        asset_plan_path=asset_plan_path,
        output_video_path=out_video_path,
        composer_type="ffmpeg",
        background_music=None,
        resolution="1080x1920",
    )
    results[lang_code] = res
    print(f"Successfully rendered {out_video_path}")
    print("QA details:", json.dumps(res.get("video_qa", {}), indent=2))

# Verify SHA256 after render
sha256_after = hashlib.sha256(asset_plan_path.read_bytes()).hexdigest()
print(f"\nAsset plan SHA256 after render: {sha256_after}")
assert sha256_after == expected_sha256, "Asset plan was modified!"

print("\nALL THREE FINAL VIDEOS RENDERED SUCCESSFULLY!")
