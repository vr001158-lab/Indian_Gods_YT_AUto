# src/script/language_profiles.py
# Language Profiles & Pronunciation Mappings for hi-IN, te-IN, ta-IN

from __future__ import annotations

from typing import Any

PRODUCTIONS_LANGUAGES = {
    "hi-IN": {
        "name": "Hindi",
        "code": "hi-IN",
        "script": "Devanagari",
        "voice_config": {
            "provider": "google_chirp3_hd",
            "voice_name": "hi-IN-Chirp3-HD-D",
            "ssml_gender": "MALE",
            "style": "devotional_storytelling",
        },
    },
    "te-IN": {
        "name": "Telugu",
        "code": "te-IN",
        "script": "Telugu",
        "voice_config": {
            "provider": "google_chirp3_hd",
            "voice_name": "te-IN-Chirp3-HD-A",
            "ssml_gender": "MALE",
            "style": "devotional_storytelling",
        },
    },
    "ta-IN": {
        "name": "Tamil",
        "code": "ta-IN",
        "script": "Tamil",
        "voice_config": {
            "provider": "google_chirp3_hd",
            "voice_name": "ta-IN-Chirp3-HD-A",
            "ssml_gender": "MALE",
            "style": "devotional_storytelling",
        },
    },
}

DEVOTIONAL_DIRECTION_METADATA: dict[str, Any] = {
    "tone": "devotional_storytelling",
    "pace": "moderate",
    "energy": "warm",
    "emotion": "reverent",
    "pause_style": "natural",
    "sentence_emphasis": "semantic",
}

PRONUNCIATION_MAPPINGS: dict[str, dict[str, str]] = {
    "Shiva": {
        "hi-IN": "शिव",
        "te-IN": "శివుడు",
        "ta-IN": "சிவன்",
    },
    "Vasuki": {
        "hi-IN": "वासुकी",
        "te-IN": "వాసుకి",
        "ta-IN": "வாசுகி",
    },
    "Mahadev": {
        "hi-IN": "महादेव",
        "te-IN": "మహాదేవుడు",
        "ta-IN": "மகாதேவன்",
    },
    "Kailash": {
        "hi-IN": "कैलाश",
        "te-IN": "కైలాసము",
        "ta-IN": "கைலாசம்",
    },
    "Vishnu": {
        "hi-IN": "विष्णु",
        "te-IN": "విష్ణువు",
        "ta-IN": "விஷ்ணு",
    },
    "Narasimha": {
        "hi-IN": "नरसिंह",
        "te-IN": "నరసింహ స్వామి",
        "ta-IN": "நரசிம்மர்",
    },
    "Hiranyakashipu": {
        "hi-IN": "हिरण्यकशिपु",
        "te-IN": "హిరణ్యకశిపుడు",
        "ta-IN": "இரணியகசிபு",
    },
    "Ganesh": {
        "hi-IN": "गणेश",
        "te-IN": "గణపతి",
        "ta-IN": "விநாயகர்",
    },
    "Subramanya": {
        "hi-IN": "सुब्रह्मण्य",
        "te-IN": "సుబ్రహ్మణ్యేశ్వరుడు",
        "ta-IN": "முருகன்",
    },
    "Ayodhya": {
        "hi-IN": "अयोध्या",
        "te-IN": "అయోధ్య",
        "ta-IN": "அயோத்தி",
    },
}
