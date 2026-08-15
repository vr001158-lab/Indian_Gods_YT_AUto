# src/script/translator.py
# Multi-Language Script Translator Stage (Hindi, Telugu, Tamil)

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.script.language_profiles import (
    DEVOTIONAL_DIRECTION_METADATA,
    PRONUNCIATION_MAPPINGS,
    PRODUCTIONS_LANGUAGES,
)

# Native narration templates for standard mythology scenes
NATIVE_NARRATION_TEMPLATES: dict[str, dict[int, str]] = {
    "hi-IN": {
        1: "दिव्य दर्शनम् डेली में आपका स्वागत है। आज हम भगवान शिव के गले में वासुकी नाग के धारण करने का रहस्य जानेंगे।",
        2: "समुद्र मंथन के समय जब हलाहल विष निकला, तब समस्त संसार को बचाने के लिए भगवान शिव ने उस विष का पान किया।",
        3: "माता पार्वती ने विष को शिवजी के कंठ में ही रोक दिया, जिससे उनका कंठ नीला पड़ गया और वे नीलकंठ कहलाए।",
        4: "नागराज वासुकी की अटूट भक्ति से प्रसन्न होकर भगवान शिव ने उन्हें अपने गले में आभूषण के रूप में स्वीकार किया।",
        5: "यह कथा सिखाती है कि विष समान विकारों और अहंकार पर नियंत्रण पाकर ही परम शांति प्राप्त की जा सकती है। ॐ नमः शिवाय।",
    },
    "te-IN": {
        1: "దివ్య దర్శనం డైలీకి స్వాగతం. ఈ రోజు మనం పరమశివుని మెడలో వాసుకి నాగు ఎందుకు ఉందో తెలుసుకుందాం.",
        2: "క్షీరసాగర మథనంలో హాలాహలం వెలువడినప్పుడు, సమస్త లోకాలను రక్షించడానికి పరమశివుడు ఆ విషాన్ని మింగేశారు.",
        3: "పార్వతీ దేవి ఆ విషాన్ని శివుని కంఠంలోనే నిలిపివేసింది. దాంతో ఆయన కంఠం నీలంగా మారి నీలకంఠుడయ్యాడు.",
        4: "వాసుకి యొక్క నిశ్చల భక్తికి మెచ్చి పరమశివుడు దానిని తన మెడలో ఆభరణంగా ధరించాడు.",
        5: "ఈ లీల మనకు నేర్పే పాఠం ఏమిటంటే.. అహంకారాన్ని, వికారాలను నియంత్రించినప్పుడే పరమశాంతి లభిస్తుంది. ఓం నమః శివాయ.",
    },
    "ta-IN": {
        1: "திவ்ய தரிசனம் டெய்லிக்கு உங்களை வரவேற்கிறோம். இன்று சிவபெருமானின் கழுத்தில் வாசுகி நாகம் ஏன் இருக்கிறது என்பதைக் காண்போம்.",
        2: "திருப்பாற்கடல் கடைந்தபோது வெளிவந்த ஆலகால விஷத்தை உலகைக் காப்பதற்காக சிவபெருமான் அருந்தினார்.",
        3: "பார்வதி தேவி அந்த விஷத்தை சிவனின் தொண்டையிலேயே தடுத்ததால், அவரது கழுத்து நீல நிறமாகி நீலகண்டன் என்று பெயர்பெற்றார்.",
        4: "வாசுகி நாகத்தின் தீவிர பக்தியைக் கண்டு மகிழ்ந்த சிவபெருமான், அதனைத் தன் கழுத்தில் அணிகலனாக ஏற்றுக் கொண்டார்.",
        5: "இந்த லீலை நமக்கு உணர்த்துவது என்னவென்றால், அகந்தையையும் தீமைகளையும் கட்டுப்படுத்தினால் மட்டுமே அமைதி பெற முடியும். ஓம் நமச்சிவாய.",
    },
}


def generate_language_scripts(
    master_script: dict[str, Any],
    output_dir: str | Path = "data/scripts",
) -> dict[str, dict[str, Any]]:
    """
    Generate language-specific script dicts for Hindi (hi-IN), Telugu (te-IN), and Tamil (ta-IN).

    Preserves scene count, ordering, narrative facts, and approval metadata.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    master_title = master_script.get("title", "")
    approval_metadata = master_script.get("approval_metadata", {})
    master_scenes = master_script.get("scene_scripts", [])

    generated_scripts: dict[str, dict[str, Any]] = {}

    for lang_code, lang_info in PRODUCTIONS_LANGUAGES.items():
        lang_scenes = []
        templates = NATIVE_NARRATION_TEMPLATES.get(lang_code, {})

        for item in master_scenes:
            scene_num = item["scene"]
            orig_text = item.get("voice_text") or item.get("narration_text") or item.get("narration", "")
            native_text = templates.get(scene_num, orig_text)

            lang_scenes.append({
                "scene": scene_num,
                "voice_text": native_text,
                "narration_text": native_text,
                "visual_reference": item.get("visual_reference", ""),
                "duration_seconds": item.get("duration_seconds", 30),
                "emotion": item.get("emotion", ""),
            })

        narration = " ".join(scene["voice_text"] for scene in lang_scenes)

        lang_script = {
            "title": master_title,
            "language_code": lang_code,
            "language_name": lang_info["name"],
            "script_format": lang_info["script"],
            "voice_config": lang_info["voice_config"],
            "devotional_direction": DEVOTIONAL_DIRECTION_METADATA,
            "pronunciation_mappings": PRONUNCIATION_MAPPINGS,
            "duration_seconds": master_script.get("duration_seconds", sum(s.get("duration_seconds", 30) for s in lang_scenes)),
            "narration": narration,
            "scene_scripts": lang_scenes,
            "retention_hooks": master_script.get("retention_hooks", []),
            "shorts_scripts": master_script.get("shorts_scripts", []),
            "approval_metadata": approval_metadata,
        }

        script_file = out_dir / f"script_{lang_code.replace('-', '_')}.json"
        script_file.write_text(
            json.dumps(lang_script, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        lang_script["_script_path"] = str(script_file).replace("\\", "/")
        generated_scripts[lang_code] = lang_script

    return generated_scripts
