# scratch/render_phase6_te_ta.py
# Re-run Phase 6 validation builds for te-IN and ta-IN only
# (Hindi already rendered successfully)

import os
import sys
import json
import time
import hashlib
sys.path.insert(0, os.getcwd())

from pathlib import Path
from src.audio.music import select_background_music, validate_music_provenance
from src.voice.generator import generate_voice_mapping
from src.video.generator import render_multilingual_video

ASSET_PLAN_PATH = Path("data/visuals/asset_plan_20260814_071510.json")
EXPECTED_SHA256 = "f6ca03a2dfec5add5b9bce5ce699124bfdffacf42f009b2a9d4b1c02a5f87b33"

sha256_check = hashlib.sha256(ASSET_PLAN_PATH.read_bytes()).hexdigest()
assert sha256_check == EXPECTED_SHA256, f"SHA256 mismatch! Got {sha256_check}"
print("[OK] Asset plan SHA256 verified.")

bgm_track = select_background_music("devotional")
ok_music, msg_music, music_info = validate_music_provenance(bgm_track)
assert ok_music, f"Music provenance check failed: {msg_music}"
print(f"[OK] Background music: {bgm_track}")

SCRIPTS = {
    "te-IN": {
        "title": "Secrets of Shiva's Snake: The Mastery Over Ego and Poison",
        "language_code": "te-IN",
        "duration_seconds": 300,
        "narration": (
            "maha devudu tana medalo visha poorita naagunu enduku dharincharo evvadaina aalochinchara? "
            "Divya Darshanam Daily ki swaagatam. Ee roju paramasivudu maatrame cheppaagalina samudra manthanam kathaanu "
            "telusukuntamu. Ksheerasagara mathanam lo Halaahalam veluvadina ppudu, paralokalu rakshinchadaaniki Paramasivudu "
            "aa vishaanni migeeshaaru. Parvati Devi vishanni kantham lone nilichivesindi. "
            "Vaasuki ahamkaraanni suchisatundi. Shivudu daanini jayinchi aabharanaanga dharinchaaru. "
            "Om Namah Shivaya. Divya Darshanam Daily ki subscribe cheyandi."
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
            "At 60s: How Shiva saves the cosmos from destruction.",
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
            "Mahaadevan thanutha kazhuththil visham ulla naagaththai yen anidhirukkiraar endru eppodhaavathu yosithirukkireerkalaaa? "
            "Divya Darshanam Daily ku ungalai varaverpkirom. Indru Sivaperumanin kazhuththil vaasuki naagam irukkum "
            "rahasyam kaanpom. Thiruppaar kadal kadaindha pothu aalakaaala visham veluvandhathu. "
            "Sivaperumanin kazhuththil visham indriyadai Parvati devi thaduthaar. "
            "Vaasuki naagam ahankaaraththai kurippikirathhu. Sivan adhai vendu aaparanmaaga anidhukondaar. "
            "Om Namassivaaya. Subscribe seyungal."
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
                    "Namma vaazhvil varum thadaigalai vendu avalai valimayaaga maattrungal. "
                    "Om Namassivaaya. Divya Darshanam Daily ai subscribe seyungal."
                ),
                "emotion": "Reassuring and calm"
            }
        ],
        "retention_hooks": [
            "At 60s: How Shiva saves all creation from Halahala.",
            "At 140s: What the serpent means for your daily life."
        ],
        "shorts_scripts": [
            {
                "title": "Why Shiva Wears a Cobra",
                "hook": "Why does Shiva wear a poisonous cobra?",
                "body": "The serpent Vasuki represents conquered ego. Shiva wears it as a symbol of supreme mastery."
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
    "te-IN": {"provider": "edge_neural_tts", "voice_name": "te-IN-ShrutiNeural"},
    "ta-IN": {"provider": "edge_neural_tts", "voice_name": "ta-IN-PallaviNeural"},
}

LANG_SUFFIX = {"te-IN": "te", "ta-IN": "ta"}

rendered_summary = {}

for lang_code, script_dict in SCRIPTS.items():
    print(f"\n=== Generating TTS: {lang_code} ===")

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
                print(f"  Retrying in 5s...")
                time.sleep(5)
            else:
                print(f"  All {MAX_RETRIES} attempts failed. Skipping {lang_code}.")
                amap = None

    if amap is None:
        continue

    amap_file = Path(f"data/audio/audio_map_{lang_code}_phase6.json")
    amap_file.parent.mkdir(parents=True, exist_ok=True)
    amap_file.write_text(json.dumps(amap, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] Audio map saved: {amap_file}")

    out_video = Path(f"data/videos/shiva_{LANG_SUFFIX[lang_code]}_final.mp4")
    print(f"  Rendering video: {out_video}")

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
    rendered_summary[lang_code] = {"output": str(out_video), "bytes": size, "qa": res.get("video_qa", {})}
    print(f"[OK] Rendered {out_video} ({size:,} bytes)")
    time.sleep(3)  # brief pause between languages to avoid Edge TTS rate limiting

# Final SHA256 guard
sha256_after = hashlib.sha256(ASSET_PLAN_PATH.read_bytes()).hexdigest()
assert sha256_after == EXPECTED_SHA256, f"Asset plan was modified!"
print(f"\n[OK] Asset plan SHA256 unchanged.")

print("\n=== Telugu + Tamil Phase 6 Validation Summary ===")
for lang_code, info in rendered_summary.items():
    qa = info.get("qa", {})
    print(f"  {lang_code}: {info['output']} | {info['bytes']:,} bytes | valid={qa.get('valid', '?')}")
print("[DONE]")
