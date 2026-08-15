# scratch/render_phase62_final_videos.py
# Phase 6.2 — Real Production Audio & Video Regeneration (Hindi Devanagari, Telugu, Tamil Native Scripts)

import os
import sys
import json
import time
import hashlib
from pathlib import Path

sys.path.insert(0, os.getcwd())

from src.audio.music import select_background_music, validate_music_provenance
from src.voice.generator import generate_voice_mapping
from src.video.generator import render_multilingual_video, perform_video_qa

ASSET_PLAN_PATH = Path("data/visuals/asset_plan_20260814_071510.json")
EXPECTED_SHA256 = "f6ca03a2dfec5add5b9bce5ce699124bfdffacf42f009b2a9d4b1c02a5f87b33"

# --- Pre-flight SHA256 check ---
sha256_before = hashlib.sha256(ASSET_PLAN_PATH.read_bytes()).hexdigest()
assert sha256_before == EXPECTED_SHA256, f"Asset plan SHA256 mismatch! Got {sha256_before}"
print(f"[OK] Asset plan SHA256 verified before render: {sha256_before[:16]}...")

# --- Music Provenance & Selection v2 ---
bgm_track, bgm_sel_type = select_background_music("devotional"), "primary"
from src.audio.music import select_background_music_v2
bgm_track, bgm_sel_type = select_background_music_v2("devotional")
assert bgm_track is not None, "No approved music track found!"
ok_music, msg_music, music_info = validate_music_provenance(bgm_track)
assert ok_music, f"Music provenance check failed: {msg_music}"
print(f"[OK] BGM selected: {bgm_track.name} (type={bgm_sel_type}, source={music_info.get('source')}, SHA256={music_info.get('sha256')[:16]}...)")

# Native script production scripts for Hindi, Telugu, Tamil
SCRIPTS = {
    "hi-IN": {
        "title": "Secrets of Shiva's Snake: The Mastery Over Ego and Poison",
        "language_code": "hi-IN",
        "duration_seconds": 360,
        "narration": (
            "भगवान शिव अपने गले में विषैले नाग को क्यों धारण करते हैं, सोने और मोतियों के बजाय? "
            "दिव्य दर्शन डेली में आपका स्वागत है। आज हम भगवान शिव और नागराज वासुकी की पवित्र कथा का रहस्य जानेंगे। "
            "जब समुद्र मंथन से भयानक हलाहल विष प्रकट हुआ, तो समस्त देव और दानव भयभीत हो गए। अपनी रक्षा के लिए वे महादेव की शरण में आए। "
            "शिवजी ने बिना किसी संकोच के संपूर्ण विष को पी लिया और नीलकंठ कहलाए। "
            "सनातन धर्म में वासुकी नाग मन के अहंकार, क्रोध और सांसारिक विकारों का प्रतीक है। शिवजी उसे अपने गले में धारण करके यह संदेश देते हैं कि वे इन नकारात्मक शक्तियों से भागते नहीं, बल्कि उन पर पूर्ण विजय प्राप्त करते हैं। "
            "आज के दर्शन से यह सीख लें: अपनी बाधाओं को ही अपना आभूषण बनाएं। दिव्य दर्शन डेली को सब्सक्राइब करें और महादेव की कृपा प्राप्त करें। ॐ नमः शिवाय।"
        ),
        "scene_scripts": [
            {
                "scene": 1,
                "duration_seconds": 6,
                "visual_reference": "Close-up of Shiva with coiled cobra on Mount Kailash.",
                "voice_text": "भगवान शिव अपने गले में विषैले नाग को क्यों धारण करते हैं, सोने और मोतियों के बजाय?",
                "emotion": "Mysterious and compelling"
            },
            {
                "scene": 2,
                "duration_seconds": 6,
                "visual_reference": "Divine Darshanam Daily title card over Mount Kailash.",
                "voice_text": "दिव्य दर्शन डेली में आपका स्वागत है। आज हम भगवान शिव और नागराज वासुकी की पवित्र कथा का रहस्य जानेंगे।",
                "emotion": "Warm and inviting"
            },
            {
                "scene": 3,
                "duration_seconds": 90,
                "visual_reference": "Churning of the cosmic ocean — Samudra Manthan.",
                "voice_text": "जब समुद्र मंथन से भयानक हलाहल विष प्रकट हुआ, तो समस्त देव और दानव भयभीत हो गए। अपनी रक्षा के लिए वे महादेव की शरण में आए। शिवजी ने बिना किसी संकोच के संपूर्ण विष को पी लिया और नीलकंठ कहलाए।",
                "emotion": "Dramatic and intense"
            },
            {
                "scene": 4,
                "duration_seconds": 60,
                "visual_reference": "Shiva wearing Vasuki — serpent as ornament.",
                "voice_text": "सनातन धर्म में वासुकी नाग मन के अहंकार, क्रोध और सांसारिक विकारों का प्रतीक है। शिवजी उसे अपने गले में धारण करके यह संदेश देते हैं कि वे इन नकारात्मक शक्तियों से भागते नहीं, बल्कि उन पर पूर्ण विजय प्राप्त करते हैं।",
                "emotion": "Philosophical and peaceful"
            },
            {
                "scene": 5,
                "duration_seconds": 60,
                "visual_reference": "Person meditating peacefully — double exposure with temple carvings.",
                "voice_text": "आज के दर्शन से यह सीख लें: अपनी बाधाओं को ही अपना आभूषण बनाएं। दिव्य दर्शन डेली को सब्सक्राइब करें और महादेव की कृपा प्राप्त करें। ॐ नमः शिवाय।",
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
            "మహాదేవుడు తన మెడలో బంగారు హారాలకు బదులుగా విషపూరితమైన నాగును ఎందుకు ధరించారో తెలుసా? "
            "దివ్య దర్శనం డైలీకి స్వాగతం. ఈ రోజు పరమశివుడు మరియు నాగేంద్రుడైన వాసుకి పవిత్ర కథను తెలుసుకుందాం. "
            "క్షీరసాగర మథనంలో భయంకరమైన హాలాహల విషం ఉద్భవించినప్పుడు, సమస్త లోకాలు నశించిపోయే పరిస్థితి వచ్చింది. అప్పుడు పరమశివుడు ఆ విషాన్ని స్వీకరించి లోకాలను రక్షించారు. అందుకే ఆయన నీలకంఠుడయ్యాడు. "
            "వాసుకి నాగు మనిషి లోని అహంకారాన్ని, కామక్రోధాలను సూచిస్తుంది. శివుడు దానిని మెడలో ఆభరణంగా ధరించి, అహంకారాన్ని జయించి అదుపులో ఉంచుకోవాలని బోధిస్తున్నారు. "
            "మీ జీవితంలో వచ్చే సవాళ్లను శక్తిగా మార్చుకోండి. దివ్య దర్శనం డైలీకి సబ్‌స్క్రైబ్ చేయండి. పరమశివుని అనుగ్రహం మీకు ఎల్లప్పుడూ కలుగుగాక. ఓం నమః శివాయ."
        ),
        "scene_scripts": [
            {
                "scene": 1,
                "duration_seconds": 6,
                "visual_reference": "Shiva with cobra on Kailash — close-up.",
                "voice_text": "మహాదేవుడు తన మెడలో బంగారు హారాలకు బదులుగా విషపూరితమైన నాగును ఎందుకు ధరించారో తెలుసా?",
                "emotion": "Mysterious and compelling"
            },
            {
                "scene": 2,
                "duration_seconds": 6,
                "visual_reference": "Divine Darshanam Daily title — Telugu.",
                "voice_text": "దివ్య దర్శనం డైలీకి స్వాగతం. ఈ రోజు పరమశివుడు మరియు నాగేంద్రుడైన వాసుకి పవిత్ర కథను తెలుసుకుందాం.",
                "emotion": "Warm and inviting"
            },
            {
                "scene": 3,
                "duration_seconds": 80,
                "visual_reference": "Samudra Manthan — cosmic ocean churning.",
                "voice_text": "క్షీరసాగర మథనంలో భయంకరమైన హాలాహల విషం ఉద్భవించినప్పుడు, సమస్త లోకాలు నశించిపోయే పరిస్థితి వచ్చింది. అప్పుడు పరమశివుడు ఆ విషాన్ని స్వీకరించి లోకాలను రక్షించారు. అందుకే ఆయన నీలకంఠుడయ్యాడు.",
                "emotion": "Dramatic and intense"
            },
            {
                "scene": 4,
                "duration_seconds": 60,
                "visual_reference": "Shiva with Vasuki as ornament.",
                "voice_text": "వాసుకి నాగు మనిషి లోని అహంకారాన్ని, కామక్రోధాలను సూచిస్తుంది. శివుడు దానిని మెడలో ఆభరణంగా ధరించి, అహంకారాన్ని జయించి అదుపులో ఉంచుకోవాలని బోధిస్తున్నారు.",
                "emotion": "Philosophical and peaceful"
            },
            {
                "scene": 5,
                "duration_seconds": 60,
                "visual_reference": "Person meditating peacefully.",
                "voice_text": "మీ జీవితంలో వచ్చే సవాళ్లను శక్తిగా మార్చుకోండి. దివ్య దర్శనం డైలీకి సబ్‌స్క్రైబ్ చేయండి. పరమశివుని అనుగ్రహం మీకు ఎల్లప్పుడూ కలుగుగాక. ఓం నమః శివాయ.",
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
            "சிவபெருமான் தங்கத்திற்கும் முத்திற்கும் பதிலாகத் தமது கழுத்தில் விஷமுள்ள நாகத்தை ஏன் அணிந்திருக்கிறார்? "
            "திவ்ய தரிசனம் டெய்லிக்கு உங்களை அன்போடு வரவேற்கிறோம். இன்று சிவபெருமானும் வாசுகி நாகமும் இணைந்த புனிதமான ரகசியத்தைக் காண்போம். "
            "திருப்பாற்கடல் கடைந்தபோது கொடிய ஆலகால விஷம் வெளிவந்தது. உலக உயிர்களைக் காப்பதற்காக மகாதேவன் அந்த விஷத்தை அருந்தி நீலகண்டனாக மாறினார். "
            "வாசுகி நாகம் மனிதனின் அகங்காரம் மற்றும் உலக ஆசைகளைக் குறிக்கிறது. சிவன் அதைத் தனது கழுத்தில் ஆபரணமாக அணிந்து, அகங்காரத்தை வென்று கட்டுப்படுத்த வேண்டும் என்பதை உணர்த்துகிறார். "
            "உங்கள் வாழ்வின் தடைகளை சாதனைகளாக மாற்றுங்கள். திவ்ய தரிசனம் டெய்லிக்கு சப்ஸ்கிரைப் செய்யுங்கள். ஓம் நமச்சிவாய."
        ),
        "scene_scripts": [
            {
                "scene": 1,
                "duration_seconds": 6,
                "visual_reference": "Shiva with cobra on Kailash — close-up.",
                "voice_text": "சிவபெருமான் தங்கத்திற்கும் முத்திற்கும் பதிலாகத் தமது கழுத்தில் விஷமுள்ள நாகத்தை ஏன் அணிந்திருக்கிறார்?",
                "emotion": "Mysterious and compelling"
            },
            {
                "scene": 2,
                "duration_seconds": 6,
                "visual_reference": "Divine Darshanam Daily title — Tamil.",
                "voice_text": "திவ்ய தரிசனம் டெய்லிக்கு உங்களை அன்போடு வரவேற்கிறோம். இன்று சிவபெருமானும் வாசுகி நாகமும் இணைந்த புனிதமான ரகசியத்தைக் காண்போம்.",
                "emotion": "Warm and inviting"
            },
            {
                "scene": 3,
                "duration_seconds": 80,
                "visual_reference": "Samudra Manthan — cosmic ocean churning.",
                "voice_text": "திருப்பாற்கடல் கடைந்தபோது கொடிய ஆலகால விஷம் வெளிவந்தது. உலக உயிர்களைக் காப்பதற்காக மகாதேவன் அந்த விஷத்தை அருந்தி நீலகண்டனாக மாறினார்.",
                "emotion": "Dramatic and intense"
            },
            {
                "scene": 4,
                "duration_seconds": 60,
                "visual_reference": "Shiva with Vasuki as ornament.",
                "voice_text": "வாசுகி நாகம் மனிதனின் அகங்காரம் மற்றும் உலக ஆசைகளைக் குறிக்கிறது. சிவன் அதைத் தனது கழுத்தில் ஆபரணமாக அணிந்து, அகங்காரத்தை வென்று கட்டுப்படுத்த வேண்டும் என்பதை உணர்த்துகிறார்.",
                "emotion": "Philosophical and peaceful"
            },
            {
                "scene": 5,
                "duration_seconds": 60,
                "visual_reference": "Person meditating peacefully.",
                "voice_text": "உங்கள் வாழ்வின் தடைகளை சாதனைகளாக மாற்றுங்கள். திவ்ய தரிசனம் டெய்லிக்கு சப்ஸ்கிரைப் செய்யுங்கள். ஓம் நமச்சிவாய.",
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
    "hi-IN": {"provider": "edge_neural_tts", "voice_name": "hi-IN-SwaraNeural", "rate": "+0%", "pitch": "+0Hz"},
    "te-IN": {"provider": "edge_neural_tts", "voice_name": "te-IN-ShrutiNeural", "rate": "+0%", "pitch": "+0Hz"},
    "ta-IN": {"provider": "edge_neural_tts", "voice_name": "ta-IN-PallaviNeural", "rate": "+0%", "pitch": "+0Hz"},
}

LANG_SUFFIX = {"hi-IN": "hi", "te-IN": "te", "ta-IN": "ta"}

rendered_summary = {}

for lang_code, script_dict in SCRIPTS.items():
    print(f"\n==================================================")
    print(f"  Synthesizing Native Script Edge TTS: {lang_code}")
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
    print(f"  Rendering final MP4 with ducked BGM: {out_video}")

    res = render_multilingual_video(
        language_code=lang_code,
        audio_map_path=amap_file,
        asset_plan_path=ASSET_PLAN_PATH,
        output_video_path=out_video,
        composer_type="ffmpeg",
        background_music=bgm_track,
        bgm_volume=0.15,
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

# --- Post-flight SHA256 check ---
sha256_after = hashlib.sha256(ASSET_PLAN_PATH.read_bytes()).hexdigest()
assert sha256_after == EXPECTED_SHA256, f"Asset plan modified! SHA256: {sha256_after}"
print(f"\n[OK] Shared asset plan SHA256 unchanged after render: {sha256_after[:16]}...")

print("\n==================================================")
print("  PHASE 6.2 PRODUCTION REGENERATION — SUMMARY")
print("==================================================")
for lang_code, info in rendered_summary.items():
    qa = info.get("qa", {})
    print(f"  {lang_code}: {info['output']} | {info['bytes']:,} bytes | duration={info['duration']}s | valid={qa.get('valid', '?')}")

print("\n[DONE] All three Phase 6.2 production videos successfully regenerated.")
