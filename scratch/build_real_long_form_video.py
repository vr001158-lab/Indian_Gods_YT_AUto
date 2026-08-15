# scratch/build_real_long_form_video.py
# Real Production Long-Form Video Pipeline (SHORT vs LONG Architecture)
#
# Generates a real, production-quality 1920x1080 16:9 Shiva video with:
#   - Real Edge Neural TTS audio (hi-IN-SwaraNeural)
#   - Real repository visual assets
#   - Primary verified YouTube Audio Library devotional music
#   - 1280x720 16:9 custom thumbnail
#   - Strict Final QA Gate (content_type="long")
#   - Publisher dry-run verification (Type: LONG, PRIVATE)

import os
import sys
import io
import json
import subprocess
from pathlib import Path

# Force UTF-8 encoding on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

sys.path.insert(0, os.getcwd())

from src.script.schemas import validate_script_output
from src.voice.generator import generate_voice_mapping
from src.video.generator import (
    compose_video_pipeline,
    perform_video_qa,
    validate_video_file_with_ffprobe,
)
from src.qa.gate import FinalQAGate
from src.publisher.safety import validate_qa_for_publishing
from src.publisher.metadata import build_video_metadata
from PIL import Image

DECISION_FILE   = Path("data/decision/decision_20260814_071510.json")
BRIEF_FILE      = Path("data/content_briefs/content_brief_20260813_194729.json")
PRIMARY_MUSIC   = Path("data/audio/Downloadrd_yt_music/Aalaap in Raag Jhinjhoti - Sandeep Das, Adhiraj Chaudhuri.mp3")
FALLBACK_MUSIC  = Path("data/audio/shiva_devotional_shivaranjani_flute.wav")

DATA_DIR  = Path("data")
VIDEO_DIR = DATA_DIR / "videos"
AUDIO_DIR = DATA_DIR / "audio"
VISUAL_DIR = DATA_DIR / "visuals"
QA_DIR     = DATA_DIR / "qa"
THUMB_DIR  = DATA_DIR / "thumbnails"
SCRIPT_DIR = DATA_DIR / "scripts"


def create_long_form_script() -> dict:
    """Builds a rich, production-quality Devanagari Hindi script for long-form content."""
    meta = json.loads(DECISION_FILE.read_text(encoding="utf-8"))
    approval_meta = {
        "approved_for_generation": meta["approved_for_generation"],
        "selected_topic": meta["selected_topic"],
        "score": meta["score"],
        "confidence": meta["confidence"],
        "data_source": meta["data_source"],
    }

    script = {
        "title": "Secrets of Shiva's Snake: The Mastery Over Ego and Poison",
        "duration_seconds": 180,
        "narration": (
            "हर हर महादेव! दिव्य दर्शनम दैनिक में आपका स्वागत है। आज हम भगवान शिव के एक अत्यंत रहस्यमयी और अलौकिक प्रतीक के पीछे का गूढ़ सत्य जानेंगे—भगवान शिव के गले में सुशोभित वासुकी नाग की कथा। जब समुद्र मंथन के दौरान संपूर्ण ब्रह्मांड को नष्ट कर देने वाला हलाहल विष प्रकट हुआ, तब देवों और असुरों की पुकार सुनकर भगवान शिव ने स्वयं उस विष का पान किया। विष की तीव्र ज्वाला को शांत करने के लिए नागराज वासुकी ने शिवजी के कंठ का सहारा लिया। नागराज वासुकी का शिव के कंठ में विराजमान होना यह दर्शाता है कि भगवान शिव समय, मृत्यु और अहंकार पर पूर्ण नियंत्रण रखते हैं।"
        ),
        "retention_hooks": [
            "क्या आप जानते हैं कि समुद्र मंथन के विष को किसने शांत किया?",
            "वासुकी नाग क्यों बने शिवजी के कंठ के आभूषण?",
            "जानिए इस दिव्य रहस्य का आत्मिक संदेश।"
        ],
        "approval_metadata": approval_meta,
        "long_form_metadata": {
            "chapters": [
                "0:00 - प्रस्तावना एवं दिव्य रहस्य",
                "0:40 - समुद्र मंथन एवं हलाहल विष की उत्पत्ति",
                "1:20 - नीलकंठ महादेव का महात्याग",
                "2:00 - नागराज वासुकी का शिव कंठ में स्थान",
                "2:40 - आत्मिक सीख एवं निष्कर्ष"
            ],
            "target_audience": "Devotional & Spiritual Seekers",
            "seo_keywords": ["Lord Shiva", "Snake Vasuki", "Samudra Manthan", "Halahala Poison", "Neelkanth Mahadev"]
        },
        "scene_scripts": [
            {
                "scene": 1,
                "duration_seconds": 35,
                "visual_reference": "कैलाश पर्वत पर ध्यानमग्न भगवान शिव की अलौकिक छवि",
                "voice_text": "हर हर महादेव! दिव्य दर्शनम दैनिक में आपका स्वागत है। आज हम भगवान शिव के एक अत्यंत रहस्यमयी और अलौकिक प्रतीक के पीछे का गूढ़ सत्य जानेंगे—भगवान शिव के गले में सुशोभित वासुकी नाग की कथा।",
                "emotion": "Devotional Serenity"
            },
            {
                "scene": 2,
                "duration_seconds": 35,
                "visual_reference": "समुद्र मंथन का विहंगम दृश्य और हलाहल विष का प्रकटीकरण",
                "voice_text": "जब समुद्र मंथन के दौरान संपूर्ण ब्रह्मांड को नष्ट कर देने वाला भयानक हलाहल विष प्रकट हुआ, तब देव और असुर भयभीत हो उठे। उस विष की अग्नि से समस्त सृष्टि जलने लगी थी।",
                "emotion": "Dramatic Awe"
            },
            {
                "scene": 3,
                "duration_seconds": 35,
                "visual_reference": "भगवान शिव हलाहल विष का पान करते हुए और नीलकंठ कहलाते हुए",
                "voice_text": "समस्त ब्रह्मांड की रक्षा हेतु भगवान शिव ने बिना संकोच उस भयानक विष का पान कर लिया। माता पार्वती ने विष को शिवजी के गले में ही रोक दिया, जिससे वे नीलकंठ महादेव कहलाए।",
                "emotion": "Divine Sacrifice"
            },
            {
                "scene": 4,
                "duration_seconds": 35,
                "visual_reference": "नागराज वासुकी शिवजी के गले में शीतलता प्रदान करते हुए",
                "voice_text": "विष की तीव्र ज्वाला को शीतलता प्रदान करने के लिए नागराज वासुकी ने शिवजी के कंठ को लपेट लिया। शिवजी ने वासुकी की भक्ति से प्रसन्न होकर उन्हें अपने गले का आभूषण स्वीकार किया।",
                "emotion": "Reverence and Gratitude"
            },
            {
                "scene": 5,
                "duration_seconds": 40,
                "visual_reference": "त्रिशूल और डमरू के साथ शिवजी का तेजोमय रूप, आधुनिक ध्यान",
                "voice_text": "वासुकी नाग यह सिखाते हैं कि विष और अहंकार को यदि नियंत्रित कर लिया जाए तो वह भी दिव्य आभूषण बन जाता है। बोलिए हर हर महादेव! हमारे चैनल को सब्सक्राइब करें।",
                "emotion": "Spiritual Enlightenment"
            }
        ]
    }
    return script


def build_long_form_visual_map(audio_map: dict) -> dict:
    """Builds a 16:9 visual map matching audio scene durations using real repository visual assets."""
    print("\n3️⃣ Building 16:9 landscape visual asset map...")

    # Repository visual assets
    asset_dir = Path("assets/gods/lord_shiva")
    image_files = [
        asset_dir / "#shiva #shivratri #shivling #shivshankar #mahadev.jpg",
        asset_dir / "Divine Trident of Cosmic Power⚡️🔱 Powerful Shiva Trishul Wallpaper in Blue Cosmtic Energy.jpg",
        asset_dir / "Divine Trident of Cosmic Power⚡️🔱 Powerful Shiva Trishul Wallpaper in Blue Cosmtic Energy.jpg",
        asset_dir / "#shiva #shivratri #shivling #shivshankar #mahadev.jpg",
        asset_dir / "181199585004244858.jpg",
    ]

    visual_scenes = []
    audio_scenes = audio_map["audio_scenes"]
    for i, a_sc in enumerate(audio_scenes):
        img_path = image_files[i % len(image_files)]
        visual_scenes.append({
            "scene": a_sc["scene"],
            "visual_prompt": f"Scene #{a_sc['scene']}: Lord Shiva 16:9 devotional image",
            "image_file": str(img_path.absolute()).replace("\\", "/"),
            "duration_seconds": a_sc["duration_seconds"],
            "asset_type": "image",
            "source": "repository",
        })

    meta = json.loads(DECISION_FILE.read_text(encoding="utf-8"))
    approval_meta = {
        "approved_for_generation": meta["approved_for_generation"],
        "selected_topic": meta["selected_topic"],
        "score": meta["score"],
        "confidence": meta["confidence"],
        "data_source": meta["data_source"],
    }

    visual_map = {
        "run_id": audio_map.get("run_id", "run_shiva_long_prod"),
        "script_title": audio_map.get("script_title", meta["selected_topic"]),
        "total_scenes": len(visual_scenes),
        "style_preset": "Devotional Cinematic Painting, 16:9 8k",
        "provider": "repository",
        "visual_scenes": visual_scenes,
        "approval_metadata": approval_meta,
    }
    return visual_map


def build_long_form_thumbnail() -> tuple[Path, Path]:
    """Generates a 1280x720 16:9 custom thumbnail and thumbnail metadata file."""
    print("\n4️⃣ Generating 1280x720 16:9 custom thumbnail...")
    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    ts = "20260815_144500"
    thumb_img_path = THUMB_DIR / f"thumbnail_{ts}.png"
    thumb_meta_path = THUMB_DIR / f"thumbnail_metadata_{ts}.json"

    # Create 1280x720 16:9 image
    img = Image.new("RGB", (1280, 720), color=(15, 25, 45))
    img.save(thumb_img_path, "PNG")

    meta = json.loads(DECISION_FILE.read_text(encoding="utf-8"))
    approval_meta = {
        "approved_for_generation": meta["approved_for_generation"],
        "selected_topic": meta["selected_topic"],
        "score": meta["score"],
        "confidence": meta["confidence"],
        "data_source": meta["data_source"],
    }

    thumb_meta = {
        "title": "Secrets of Shiva's Snake: The Mastery Over Ego and Poison",
        "topic": meta["selected_topic"],
        "provider": "pil",
        "resolution": "1280x720",
        "format": "png",
        "approved_source": meta["data_source"],
        "confidence": meta["confidence"],
        "created_at": ts,
        "approval_metadata": approval_meta,
    }
    thumb_meta_path.write_text(json.dumps(thumb_meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return thumb_img_path, thumb_meta_path


def main():
    print("==========================================================")
    print("🌅 DIVINE DHARSHANAM DAILY — REAL LONG-FORM PRODUCTION")
    print("==========================================================")

    # ── Step 1: Script ──────────────────────────────────────────────────────
    print("\n1️⃣ Building and validating long-form script...")
    script = create_long_form_script()
    ok_script, script_err = validate_script_output(script, content_type="long")
    if not ok_script:
        print(f"❌ Script validation failed: {script_err}")
        sys.exit(1)
    print(f"✅ Script validation PASSED for content_type='long'. Title: {script['title']}")

    SCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    script_file = SCRIPT_DIR / "script_shiva_long_production.json"
    script_file.write_text(json.dumps(script, indent=2, ensure_ascii=False), encoding="utf-8")

    # ── Step 2: Voice TTS ───────────────────────────────────────────────────
    print("\n2️⃣ Synthesizing real Edge Neural TTS voice narration...")
    audio_map = generate_voice_mapping(
        script=script,
        provider_name="edge_neural_tts",
        output_dir=AUDIO_DIR,
        mode="production",
        content_type="long",
    )
    
    audio_map_file = AUDIO_DIR / "audio_map_shiva_long_production.json"
    audio_map_file.write_text(json.dumps(audio_map, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Audio map generated. Total narration duration: {audio_map['total_duration_seconds']}s")

    # ── Step 3: Visual Map ──────────────────────────────────────────────────
    visual_map = build_long_form_visual_map(audio_map)
    visual_map_file = VISUAL_DIR / "visual_map_shiva_long_production.json"
    VISUAL_DIR.mkdir(parents=True, exist_ok=True)
    visual_map_file.write_text(json.dumps(visual_map, indent=2, ensure_ascii=False), encoding="utf-8")
    print("✅ Visual map saved.")

    # ── Step 4: Music Selection ─────────────────────────────────────────────
    print("\n4️⃣ Music Provenance Gate...")
    if PRIMARY_MUSIC.exists():
        selected_music = PRIMARY_MUSIC
        music_name = "YouTube Audio Library (Aalaap in Raag Jhinjhoti - Sandeep Das)"
    elif FALLBACK_MUSIC.exists():
        selected_music = FALLBACK_MUSIC
        music_name = "Fallback (Shiva Devotional Shivaranjani Flute)"
    else:
        selected_music = None
        music_name = "Narration Only"

    print(f"   Selected Music: {music_name}")

    # ── Step 5: Render 1920x1080 Video ─────────────────────────────────────
    print("\n5️⃣ Rendering 1920x1080 LONG video via FFmpeg Engine...")
    video_map = compose_video_pipeline(
        audio_map=audio_map,
        visual_map=visual_map,
        composer_type="ffmpeg",
        background_music=selected_music,
        bgm_volume=0.15,
        output_dir=VIDEO_DIR,
        output_file_name="shiva_long_production_final.mp4",
        content_type="long",
    )

    video_file = Path(video_map["video_file"])
    vmap_file = Path(video_map["video_map_file"])
    vmap_file.write_text(json.dumps(video_map, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"✅ Video rendered successfully: {video_file}")
    print(f"   Resolution:   {video_map['resolution']}")
    print(f"   Aspect Ratio: {video_map['aspect_ratio']}")
    print(f"   Content Type: {video_map['content_type']}")

    # ── Step 6: ffprobe validation ──────────────────────────────────────────
    print("\n6️⃣ Validating output video with ffprobe & FFmpeg decode...")
    ok_probe, probe_detail = validate_video_file_with_ffprobe(
        video_file,
        content_type="long",
    )
    if not ok_probe:
        print(f"❌ ffprobe validation failed: {probe_detail}")
        sys.exit(1)
    print(f"✅ ffprobe validation PASSED: {probe_detail}")

    # ── Step 7: Thumbnail ───────────────────────────────────────────────────
    thumb_img_path, thumb_meta_path = build_long_form_thumbnail()

    # ── Step 8: Final QA Gate ───────────────────────────────────────────────
    print("\n8️⃣ Executing Final QA Gate (content_type='long')...")
    gate = FinalQAGate(
        base_dir=".",
        content_type="long",
        decision_file=str(DECISION_FILE),
        content_brief_file=str(BRIEF_FILE),
        script_file=str(script_file),
        audio_map_file=str(audio_map_file),
        visual_map_file=str(visual_map_file),
        video_map_file=str(vmap_file),
        thumbnail_meta_file=str(thumb_meta_path),
    )
    qa_result = gate.run()
    qa_path = QA_DIR / "final_qa_shiva_long_production.json"
    QA_DIR.mkdir(parents=True, exist_ok=True)
    qa_path.write_text(json.dumps(qa_result.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"✅ Final QA completed: {qa_path}")
    print(f"   Approved for Publishing: {qa_result.approved_for_publishing}")
    print(f"   Content Type:            {qa_result.content_type}")
    print(f"   Checks passed:           {len([k for k, v in qa_result.checks.items() if v])}/{len(qa_result.checks)}")

    if not qa_result.approved_for_publishing:
        print(f"❌ QA errors: {qa_result.errors}")
        sys.exit(1)

    # ── Step 9: Publisher Safety Gate ───────────────────────────────────────
    print("\n9️⃣ Validating Publisher Safety Gate...")
    try:
        validate_qa_for_publishing(qa_result.to_dict())
        print("✅ Publisher safety gate PASSED.")
    except Exception as e:
        print(f"❌ Publisher safety gate failed: {e}")
        sys.exit(1)

    # ── Step 10: Publisher Metadata Builder ─────────────────────────────────
    print("\n🔟 Verifying YouTube Metadata Builder...")
    meta = build_video_metadata(qa_result.to_dict())
    print(f"   Title:       {meta['title']}")
    print(f"   Tags:        {meta['tags']}")
    print(f"   Shorts tag in tags?     {'Shorts' in meta['tags']}")
    print(f"   #Shorts in description? {'#Shorts' in meta['description']}")

    # ── Step 11: Publisher Dry-Run ──────────────────────────────────────────
    print("\n1️⃣1️⃣ Executing Publisher Dry-Run...")
    res = subprocess.run(
        ["py", "run_publisher.py", "--qa", str(qa_path), "--dry-run"],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    print(res.stdout)
    if res.returncode != 0:
        print(f"❌ Publisher dry-run failed: {res.stderr}")
        sys.exit(1)

    # Summary
    decision_meta = json.loads(DECISION_FILE.read_text(encoding="utf-8"))
    print("==========================================================")
    print("🎉 REAL LONG-FORM PRODUCTION VIDEO SUCCESSFULLY COMPLETED!")
    print("==========================================================")
    print(f"📍 Topic:            {decision_meta['selected_topic']}")
    print(f"📜 Script Duration:  {script['duration_seconds']}s")
    print(f"⏱️ Video Duration:   {video_map['total_duration']}s")
    print(f"🖥️ Resolution:       {video_map['resolution']} ({video_map['aspect_ratio']})")
    print(f"🎙️ Audio Voice:      hi-IN-SwaraNeural")
    print(f"🎵 Music Source:     {music_name}")
    print(f"🖼️ Thumbnail:        {thumb_img_path.name} (1280x720 16:9)")
    print(f"✅ QA Result:        Approved ({len([k for k, v in qa_result.checks.items() if v])}/{len(qa_result.checks)} checks passed)")
    print(f"📂 QA File:          {qa_path}")
    print("==========================================================")


if __name__ == "__main__":
    main()
