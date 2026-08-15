# scratch/render_phase6_validation_builds.py
# Phase 6.1 — Targeted Voice Pacing & Devotional Background Music Integration

import os
import sys
import json
import time
import hashlib
sys.path.insert(0, os.getcwd())

from pathlib import Path
from src.audio.music import select_background_music, validate_music_provenance
from src.voice.generator import generate_voice_mapping
from src.video.generator import render_multilingual_video, perform_video_qa

ASSET_PLAN_PATH = Path("data/visuals/asset_plan_20260814_071510.json")
EXPECTED_SHA256 = "f6ca03a2dfec5add5b9bce5ce699124bfdffacf42f009b2a9d4b1c02a5f87b33"

# --- Pre-flight: SHA256 guard ---
sha256_before = hashlib.sha256(ASSET_PLAN_PATH.read_bytes()).hexdigest()
assert sha256_before == EXPECTED_SHA256, f"SHA256 mismatch! Got {sha256_before}"
print("[OK] Asset plan SHA256 verified before render.")

# --- Music: select approved Shiva devotional track & provenance guard ---
bgm_track = select_background_music("devotional")
assert bgm_track is not None, "Approved background music track not found!"
ok_music, msg_music, music_info = validate_music_provenance(bgm_track)
assert ok_music, f"Music provenance check failed: {msg_music}"
print(f"[OK] Background music: {bgm_track} | Source: {music_info.get('source')} | License: {music_info.get('license')}")

SCRIPTS = {
    "hi-IN": {
        "title": "Secrets of Shiva's Snake: The Mastery Over Ego and Poison",
        "language_code": "hi-IN",
        "duration_seconds": 360,
        "narration": (
            "Why does Lord Shiva wear a deadly, poisonous cobra around his neck instead of gold and pearls? "
            "Welcome to Divine Dharshanam Daily. Today, we investigate the sacred story of Lord Shiva and the serpent Vasuki. "
            "When the cosmic ocean was churned, the deadly Halahala poison threatened all creation. "
            "With absolute composure, Shiva stepped forward and drank the poison, becoming Neelkanth. "
            "The serpent Vasuki represents ego and desires. Shiva masters them, wearing the snake as an ornament of strength. "
            "Emulate Shiva. Transform your obstacles into ornaments. Om Namah Shivaya."
        ),
        "scene_scripts": [
            {
                "scene": 1,
                "duration_seconds": 6,
                "visual_reference": "Close-up of Shiva with coiled cobra on Mount Kailash.",
                "voice_text": "Why does Lord Shiva wear a deadly, poisonous cobra around his neck instead of gold and pearls?",
                "emotion": "Mysterious and compelling"
            },
            {
                "scene": 2,
                "duration_seconds": 6,
                "visual_reference": "Divine Darshanam Daily title card over Mount Kailash.",
                "voice_text": (
                    "Welcome to Divine Dharshanam Daily. Today, we investigate "
                    "the sacred story of Lord Shiva and the serpent Vasuki."
                ),
                "emotion": "Warm and inviting"
            },
            {
                "scene": 3,
                "duration_seconds": 90,
                "visual_reference": "Churning of the cosmic ocean — Samudra Manthan.",
                "voice_text": (
                    "When the cosmic ocean was churned, the deadly Halahala poison threatened all creation. "
                    "Both gods and demons fled in terror. In their desperation, they turned to the only one "
                    "who could withstand such devastation: Lord Shiva. With absolute composure, Shiva drank the "
                    "poison to save the cosmos, becoming Neelkanth — the Blue-Throated Savior."
                ),
                "emotion": "Dramatic and intense"
            },
            {
                "scene": 4,
                "duration_seconds": 60,
                "visual_reference": "Shiva wearing Vasuki — serpent as ornament.",
                "voice_text": (
                    "In Hindu symbolism, the snake Vasuki represents ego, worldly desires, and the poisons of the "
                    "mind — anger, jealousy, and greed. By wearing the serpent around his neck, Shiva demonstrates "
                    "that he does not run away from these forces. He conquers and tames them."
                ),
                "emotion": "Philosophical and peaceful"
            },
            {
                "scene": 5,
                "duration_seconds": 60,
                "visual_reference": "Person meditating peacefully — double exposure with temple carvings.",
                "voice_text": (
                    "As we close our dharshanam today, carry this wisdom. "
                    "Stand firm, master your reactions, and transform your obstacles into ornaments. "
                    "You have the power. Thank you for joining Divine Dharshanam Daily. "
                    "May the peace of Kailash be with you always. Om Namah Shivaya."
                ),
                "emotion": "Reassuring and calm"
            }
        ],
        "retention_hooks": [
            "At 60s: How Shiva resolves the deadly threat when even gods flee.",
            "At 140s: What the serpent truly symbolizes in your life."
        ],
        "shorts_scripts": [
            {
                "title": "Why Shiva Wears a Cobra",
                "hook": "Why does Lord Shiva wear a poisonous cobra?",
                "body": "The serpent Vasuki represents conquered ego. Shiva wears it as a symbol of mastery."
            }
        ],
        "approval_metadata": {
            "approved_for_generation": True,
            "selected_topic": "Why Lord Shiva Wears a Snake Around His Neck",
            "score": 66,
            "confidence": "high",
            "data_source": "youtube_api",
            "category": "Stories of deities"
        }
    },
    "te-IN": {
        "title": "Secrets of Shiva's Snake: The Mastery Over Ego and Poison",
        "language_code": "te-IN",
        "duration_seconds": 300,
        "narration": (
            "మహాదేవుడు తన మెడలో విషపూరితమైన నాగును ఎందుకు ధరించారో ఎప్పుడైనా ఆలోచించారా? "
            "దివ్య దర్శనం డైలీకి స్వాగతం. ఈ రోజు పరమశివుడు మరియు వాసుకి నాగు పవిత్ర రహస్యం తెలుసుకుందాం. "
            "క్షీరసాగర మథనంలో హాలాహలం వెలువడినప్పుడు, పరమశివుడు లోకాలను రక్షించడానికి ఆ విషాన్ని మింగేశారు. "
            "వాసుకి అహంకారాన్ని సూచిస్తుంది. శివుడు దానిని జయించి ఆభరణంగా ధరించారు. "
            "ఓం నమః శివాయ. దివ్య దర్శనం డైలీకి సబ్‌స్క్రైబ్ చేయండి."
        ),
        "scene_scripts": [
            {
                "scene": 1,
                "duration_seconds": 6,
                "visual_reference": "Shiva with cobra on Kailash — close-up.",
                "voice_text": "Maha Devudu tana medalo vishapoorithamaina naagunu enduku dharincharo evvadaina aalochinchaaraaa?",
                "emotion": "Mysterious and compelling"
            },
            {
                "scene": 2,
                "duration_seconds": 6,
                "visual_reference": "Divine Darshanam Daily title — Telugu.",
                "voice_text": "Divya Darshanam Daily ki swaagatam. Ee roju Paramasivudu mariyu Vaasuki naagu pavithra rahasyam telusukuntamu.",
                "emotion": "Warm and inviting"
            },
            {
                "scene": 3,
                "duration_seconds": 80,
                "visual_reference": "Samudra Manthan — cosmic ocean churning.",
                "voice_text": (
                    "Ksheerasagara mathanam lo Halaahalam veluvadina ppudu, samasta lokaalanu rakshinchadaaniki "
                    "Paramasivudu aa vishaanni migeeshaaru. Parvati Devi vishanni shivuni kantham lone nilichivesindi."
                ),
                "emotion": "Dramatic and intense"
            },
            {
                "scene": 4,
                "duration_seconds": 60,
                "visual_reference": "Shiva with Vasuki as ornament.",
                "voice_text": (
                    "Vaasuki naagu ahamkaaraanni, praapaanchika korikalaanu suchisatundi. "
                    "Shivudu vaatini jayinchi aabharanaanga dharinchaaru. Idi mana jeevitaaniki goppa sandesam."
                ),
                "emotion": "Philosophical and peaceful"
            },
            {
                "scene": 5,
                "duration_seconds": 60,
                "visual_reference": "Person meditating peacefully.",
                "voice_text": (
                    "Mana jeevitam lo vacche adanki mulu ni jayinchi vaatini saktiga marchukondaaam. "
                    "Om Namah Shivaya. Divya Darshanam Daily ki subscribe cheyandi."
                ),
                "emotion": "Reassuring and calm"
            }
        ],
        "retention_hooks": [
            "At 60s: How Shiva resolves the deadly threat when even gods flee.",
            "At 140s: What the serpent truly symbolizes in your life."
        ],
        "shorts_scripts": [
            {
                "title": "Why Shiva Wears a Cobra",
                "hook": "Why does Lord Shiva wear a poisonous cobra?",
                "body": "The serpent Vasuki represents conquered ego. Shiva wears it as a symbol of mastery."
            }
        ],
        "approval_metadata": {
            "approved_for_generation": True,
            "selected_topic": "Why Lord Shiva Wears a Snake Around His Neck",
            "score": 66,
            "confidence": "high",
            "data_source": "youtube_api",
            "category": "Stories of deities"
        }
    },
    "ta-IN": {
        "title": "Secrets of Shiva's Snake: The Mastery Over Ego and Poison",
        "language_code": "ta-IN",
        "duration_seconds": 300,
        "narration": (
            "மகாதேவன் தனது கழுத்தில் விஷமுள்ள நாகத்தை ஏன் அணிந்திருக்கிறார் என்று எப்போதாவது யோசித்திருக்கிறீர்களா? "
            "திவ்ய தரிசனம் டெய்லிக்கு உங்களை வரவேற்கிறோம். இன்று சிவபெருமானின் கழுத்தில் வாசுகி நாகம் ஏன் இருக்கிறது என்று காண்போம். "
            "திருப்பாற்கடல் கடைந்தபோது ஆலகால விஷம் வெளிவந்தது. சிவபெருமான் அதை அருந்தி உலகைக் காத்தார். "
            "வாசுகி அகங்காரத்தை குறிக்கிறது. சிவன் அதை வென்று ஆபரணமாக அணிந்துகொண்டார். "
            "ஓம் நமச்சிவாய. சப்ஸ்கிரைப் செய்யுங்கள்."
        ),
        "scene_scripts": [
            {
                "scene": 1,
                "duration_seconds": 6,
                "visual_reference": "Shiva with cobra on Kailash — close-up.",
                "voice_text": "Mahaadevan thanutha kazhuththil visham ulla naagaththai yen anidhirukkiraar endru eppodhaavathu yosithirukkireerkalaaa?",
                "emotion": "Mysterious and compelling"
            },
            {
                "scene": 2,
                "duration_seconds": 6,
                "visual_reference": "Divine Darshanam Daily title — Tamil.",
                "voice_text": "Divya Darshanam Daily ku ungalai varaverpkirom. Indru Sivaperumanin kazhuththil vaasuki naagam irukkum rahasyam kaanpom.",
                "emotion": "Warm and inviting"
            },
            {
                "scene": 3,
                "duration_seconds": 80,
                "visual_reference": "Samudra Manthan — cosmic ocean churning.",
                "voice_text": (
                    "Thiruppaar kadal kadaindha pothu aalakaaala visham veluvandhathu. "
                    "Ulakai kaappatratharkaaga Sivaperumanin aa vishaththai arundhinar. "
                    "Parvati devi vishatthai thondaiyileye thaduththaar."
                ),
                "emotion": "Dramatic and intense"
            },
            {
                "scene": 4,
                "duration_seconds": 60,
                "visual_reference": "Shiva with Vasuki as ornament.",
                "voice_text": (
                    "Vaasuki naagam ahankaaram matrum ulaga aasaigalai kurippikirathhu. "
                    "Sivan adhai vendu aaparanmaaga anidhukondaar. Idhu namakku oru periya padam."
                ),
                "emotion": "Philosophical and peaceful"
            },
            {
                "scene": 5,
                "duration_seconds": 60,
                "visual_reference": "Person meditating peacefully.",
                "voice_text": (
                    "Nam vaazhvil varum thadaigalai vendu avalai valimayaaga maattrungal. "
                    "Om Namassivaaya. Divya Darshanam Daily ai subscribe seyungal."
                ),
                "emotion": "Reassuring and calm"
            }
        ],
        "retention_hooks": [
            "At 60s: How Shiva resolves the deadly threat when even gods flee.",
            "At 140s: What the serpent truly symbolizes in your life."
        ],
        "shorts_scripts": [
            {
                "title": "Why Shiva Wears a Cobra",
                "hook": "Why does Lord Shiva wear a poisonous cobra?",
                "body": "The serpent Vasuki represents conquered ego. Shiva wears it as a symbol of mastery."
            }
        ],
        "approval_metadata": {
            "approved_for_generation": True,
            "selected_topic": "Why Lord Shiva Wears a Snake Around His Neck",
            "score": 66,
            "confidence": "high",
            "data_source": "youtube_api",
            "category": "Stories of deities"
        }
    }
}

VOICE_CONFIG = {
    "hi-IN": {"provider": "edge_neural_tts", "voice_name": "hi-IN-SwaraNeural", "rate": "+10%", "pitch": "+0Hz"},
    "te-IN": {"provider": "edge_neural_tts", "voice_name": "te-IN-ShrutiNeural", "rate": "+10%", "pitch": "+0Hz"},
    "ta-IN": {"provider": "edge_neural_tts", "voice_name": "ta-IN-PallaviNeural", "rate": "+10%", "pitch": "+0Hz"},
}

LANG_SUFFIX = {"hi-IN": "hi", "te-IN": "te", "ta-IN": "ta"}

rendered_summary = {}

for lang_code, script_dict in SCRIPTS.items():
    print(f"\n==================================================")
    print(f"  Generating Edge Neural TTS (Pacing: +10%): {lang_code}")
    print(f"==================================================")

    MAX_RETRIES = 3
    amap = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            amap = generate_voice_mapping(
                script=script_dict,
                provider_name=VOICE_CONFIG[lang_code]["provider"],
                output_dir=Path("data/audio"),
                mode="production",
            )
            break
        except Exception as e:
            print(f"  Attempt {attempt} failed: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(4)

    if amap is None:
        raise RuntimeError(f"Voice generation failed for {lang_code}")

    amap_file = Path(f"data/audio/audio_map_{lang_code}_phase6.json")
    amap_file.parent.mkdir(parents=True, exist_ok=True)
    amap_file.write_text(json.dumps(amap, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] Audio map saved: {amap_file} (Duration: {amap['total_duration_seconds']}s)")

    out_video = Path(f"data/videos/shiva_{LANG_SUFFIX[lang_code]}_final.mp4")
    print(f"  Rendering video with ducked devotional music: {out_video}")

    res = render_multilingual_video(
        language_code=lang_code,
        audio_map_path=amap_file,
        asset_plan_path=ASSET_PLAN_PATH,
        output_video_path=out_video,
        composer_type="ffmpeg",
        background_music=bgm_track,
        bgm_volume=0.10,
        resolution="1080x1920",
    )

    size = out_video.stat().st_size if out_video.exists() else 0
    rendered_summary[lang_code] = {
        "output": str(out_video),
        "bytes": size,
        "duration": amap['total_duration_seconds'],
        "qa": res.get("video_qa", {})
    }
    print(f"[OK] Rendered {out_video} ({size:,} bytes, {amap['total_duration_seconds']}s)")

# --- Post-flight: SHA256 guard ---
sha256_after = hashlib.sha256(ASSET_PLAN_PATH.read_bytes()).hexdigest()
assert sha256_after == EXPECTED_SHA256, f"Asset plan was modified! SHA256: {sha256_after}"
print(f"\n[OK] Shared asset plan SHA256 unchanged after render.")

print("\n==================================================")
print("  PHASE 6.1 VALIDATION BUILDS — SUMMARY REPORT")
print("==================================================")
for lang_code, info in rendered_summary.items():
    qa = info.get("qa", {})
    print(f"  {lang_code}: {info['output']} | {info['bytes']:,} bytes | duration={info['duration']}s | valid={qa.get('valid', '?')}")

print("\n[DONE] All three Phase 6.1 validation builds complete.")
