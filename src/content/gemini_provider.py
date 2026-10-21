# src/content/gemini_provider.py
# Multilingual Content & Script Generation via Google Gemini API
# Supports Hindi (hi-IN, Devanagari) and Telugu (te-IN, Telugu script).
# Fail-closed in production; provides robust deterministic offline fallbacks for testing.

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any

import requests

from src.content.schemas import validate_brief_output
from src.script.schemas import validate_script_output

logger = logging.getLogger("gemini_provider")

DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
FALLBACK_MODELS = ["gemini-2.5-flash-lite", "gemini-3.5-flash-lite", "gemini-2.5-flash"]
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
REQUEST_TIMEOUT_SECONDS = 30
MAX_RETRIES = 2


class GeminiProviderError(Exception):
    """Raised when the Gemini API encounters a terminal failure."""


class GeminiAuthError(GeminiProviderError):
    """Raised on authentication/authorization errors (HTTP 401/403)."""


class GeminiRateLimitError(GeminiProviderError):
    """Raised on quota or rate limit exhaustion (HTTP 429)."""


class GeminiModelNotFoundError(GeminiProviderError):
    """Raised when the requested model is unsupported or not found (HTTP 404)."""


def _redact_key(text: str, key: str | None = None) -> str:
    """Scrub sensitive API keys from text, exceptions, and logged URLs."""
    if not text:
        return ""
    redacted = str(text)
    if key and len(key) >= 6:
        redacted = redacted.replace(key, "[REDACTED_API_KEY]")
    # Also scrub generic AIza patterns (Google API keys)
    redacted = re.sub(r"AIza[0-9A-Za-z-_]{35}", "[REDACTED_API_KEY]", redacted)
    # Scrub query string key params if any
    redacted = re.sub(r"([?&]key=)[^&\s]+", r"\1[REDACTED_API_KEY]", redacted)
    return redacted


def _build_generation_config(model: str) -> dict[str, Any]:
    """
    Build generation config. For Gemini 3.x/4.x models, omit temperature/top_p/top_k
    per official Google documentation to avoid future HTTP 400 errors.
    """
    base_model = model.lower().split("/")[-1]
    if base_model.startswith(("gemini-3", "gemini-4")):
        return {
            "responseMimeType": "application/json",
        }
    return {
        "temperature": 0.4,
        "responseMimeType": "application/json",
    }


def validate_indic_script(text: str, language_code: str) -> bool:
    """Verifies that the generated text genuinely contains native Indic script glyphs."""
    if not text:
        return False
    if language_code == "hi-IN":
        return bool(re.search(r"[\u0900-\u097F]", text))
    if language_code == "te-IN":
        return bool(re.search(r"[\u0C00-\u0C7F]", text))
    return False


def _clean_json_markdown(raw_text: str) -> str:
    """Strip markdown code fence wrappers from raw LLM output."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
        cleaned = re.sub(r"\n?```$", "", cleaned)
    return cleaned.strip()


def call_gemini_api(
    prompt: str,
    system_instruction: str = "",
    model: str | None = None,
    api_key: str | None = None,
) -> str:
    """
    Invokes the Google Gemini REST API with model fallback and bounded exponential backoff.
    Never exposes API key in URL or error logs; uses 'x-goog-api-key' request header.
    """
    key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise GeminiProviderError(
            "GEMINI_API_KEY is not set or empty. Please set GEMINI_API_KEY in environment or GitHub secrets."
        )

    target_model = model or DEFAULT_MODEL
    candidate_models = [target_model] + [m for m in FALLBACK_MODELS if m != target_model]

    last_error: Exception | None = None
    rate_limited = False

    for candidate in candidate_models:
        payload: dict[str, Any] = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": _build_generation_config(candidate),
        }
        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        url = GEMINI_API_URL.format(model=candidate)
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": key,
        }

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        raise GeminiProviderError(f"Gemini API returned no candidates: {data}")
                    first_candidate = candidates[0]
                    finish_reason = first_candidate.get("finishReason")
                    if finish_reason and finish_reason not in ("STOP", "MAX_TOKENS"):
                        logger.warning("Gemini candidate finishReason: %s", finish_reason)
                    parts = first_candidate.get("content", {}).get("parts", [])
                    if not parts or "text" not in parts[0]:
                        raise GeminiProviderError(f"Malformed Gemini candidate structure: {first_candidate}")
                    return parts[0]["text"]

                # Authentication error: fail immediately (do not retry invalid key)
                if resp.status_code in (401, 403):
                    safe_msg = _redact_key(resp.text, key)
                    raise GeminiAuthError(
                        f"Gemini API authentication failed (HTTP {resp.status_code}): {safe_msg}"
                    )

                # Rate limit / Quota exceeded
                if resp.status_code == 429:
                    rate_limited = True
                    logger.warning("Gemini model %s rate limited (HTTP 429), retrying (attempt %d)...", candidate, attempt)
                    time.sleep(1.0 * attempt)
                    continue

                # Model not found / deprecated
                if resp.status_code == 404:
                    logger.warning("Gemini model %s not found (HTTP 404), trying next model...", candidate)
                    last_error = GeminiModelNotFoundError(f"Gemini model '{candidate}' not found (HTTP 404).")
                    break

                # Transient server errors
                if resp.status_code in (500, 502, 503, 504):
                    logger.warning("Gemini model %s server error (HTTP %s), retrying (attempt %d)...", candidate, resp.status_code, attempt)
                    time.sleep(1.0 * attempt)
                    continue

                # Other terminal client error (e.g. 400 Bad Request)
                safe_msg = _redact_key(resp.text, key)
                raise GeminiProviderError(
                    f"Gemini API error (HTTP {resp.status_code}): {safe_msg}"
                )

            except (requests.Timeout, requests.ConnectionError) as exc:
                last_error = exc
                logger.warning("Gemini model %s connection/timeout error: %s (attempt %d)", candidate, _redact_key(str(exc), key), attempt)
                time.sleep(1.0 * attempt)

    if rate_limited:
        raise GeminiRateLimitError(f"Gemini API quota/rate limit exhausted across candidate models {candidate_models}.")

    safe_last = _redact_key(str(last_error), key)
    raise GeminiProviderError(f"Gemini API failed across candidate models {candidate_models}. Last error: {safe_last}")


# ─────────────────────────────────────────────────────────────────────────────
# Multilingual Deterministic Offline Profiles (for unit tests and offline use)
# ─────────────────────────────────────────────────────────────────────────────

_OFFLINE_BRIEFS = {
    "hi-IN": {
        "title_options": [
            "भगवान शिव के गले में सर्प क्यों है? जानिए रहस्य",
            "शिव जी के नाग वासुकि की अनसुनी कथा",
            "समुद्र मंथन और नीलकंठ शिव का दिव्य रहस्य",
            "शिव के गले का सर्प: अहंकार पर विजय का प्रतीक",
            "भगवान शिव और वासुकि नाग का अलौकिक संबंध"
        ],
        "primary_title": "भगवान शिव के गले में सर्प क्यों है? जानिए रहस्य",
        "hook": "क्या आपने कभी सोचा है कि देवाधिदेव महादेव स्वर्ण आभूषणों के स्थान पर गले में विषधर सर्प क्यों धारण करते हैं? यह केवल एक आभूषण नहीं, बल्कि जीवन की विषमताओं को जीतने का एक गूढ़ संदेश है।",
        "audience": "भक्त, धर्मप्रेमी और सनातन दर्शन में रुचि रखने वाले दर्शक।",
        "story_arc": [
            "पहला भाग: भगवान शिव के गले में लिपटे विषधर सर्प वासुकि का दिव्य दर्शन।",
            "दूसरा भाग: समुद्र मंथन, हलाहल विष और वासुकि द्वारा शिव जी के गले को शीतलता प्रदान करने की कथा।",
            "तीसरा भाग: जीवन में नकारात्मक ऊर्जा और अहंकार को नियंत्रित करने की प्रेरणा।"
        ],
        "script_structure": {
            "act_1_opening": "कैलाश पर्वत पर ध्यानस्थ शांत भगवान शिव और उनके गले में नाग के स्वरूप का वर्णन।",
            "act_2_explanation": "समुद्र मंथन में हलाहल विष के पान और वासुकि के समर्पण का आख्यान।",
            "act_3_message": "विष और अहंकार को वश में कर जीवन में शांति बनाए रखने की सीख।"
        },
        "visual_plan": [
            {
                "scene_number": 1,
                "duration_seconds": 15,
                "description": "कैलाश पर्वत पर भगवान शिव ध्यान मुद्रा में, गले में नाग वासुकि।",
                "image_prompt": "Cinematic close-up of meditating Lord Shiva, coiled cobra snake Vasuki on neck, Mount Kailash background, divine golden light, 8k",
                "video_prompt": "Serene camera panning slowly around meditating Lord Shiva, coiled cobra gently raising hood, divine mist"
            },
            {
                "scene_number": 2,
                "duration_seconds": 20,
                "description": "समुद्र मंथन का दृश्य, देवता और दानव वासुकि नाग को मथनी के रूप में खींचते हुए।",
                "image_prompt": "Samudra Manthan cosmic churning, devas and asuras pulling giant serpent Vasuki, Mount Mandara spinning, dramatic lighting",
                "video_prompt": "Epic wide shot of devas and asuras churning cosmic milk ocean with giant serpent Vasuki"
            },
            {
                "scene_number": 3,
                "duration_seconds": 25,
                "description": "भगवान शिव हलाहल विष का पान करते हुए और माता पार्वती उनके कंठ को स्पर्श करती हुई।",
                "image_prompt": "Lord Shiva calmly drinking blue glowing Halahala poison, Goddess Parvati placing hand on his neck, divine dramatic aura",
                "video_prompt": "Slow motion shot of Lord Shiva drinking blue poison, throat glowing blue as Parvati touches it"
            },
            {
                "scene_number": 4,
                "duration_seconds": 15,
                "description": "भगवान शिव वासुकि नाग को अपने गले में धारण करते हुए।",
                "image_prompt": "Lord Shiva gently placing cobra Vasuki around his blue throat, cobra bowing in devotion, peaceful expression",
                "video_prompt": "Lord Shiva smiling and placing majestic cobra around his neck, golden aura sparks"
            },
            {
                "scene_number": 5,
                "duration_seconds": 15,
                "description": "साधक शांत मन से ध्यान करता हुआ, मानसिक शांति और विजय का प्रतीक।",
                "image_prompt": "Serene individual meditating calmly in peaceful nature, soft morning sunlight, symbolic harmony",
                "video_prompt": "Peaceful meditation scene transitioning to sacred temple glow, ambient serenity"
            }
        ],
        "voice_direction": {
            "tone": "गंभीर, श्रद्धापूर्ण और अत्यंत मनोहारी।",
            "speed": "संतुलित और स्पष्ट (लगभग 120 शब्द प्रति मिनट)।",
            "emotion": "शांति, भक्ति और प्रेरणादायक।",
            "language_style": "शुद्ध एवं कर्णप्रिय हिंदी, सरल और प्रभावशाली शब्दावली।"
        },
        "shorts_hooks": [
            "भगवान शिव गले में जहरीला सांप क्यों पहनते हैं?",
            "जानिए क्यों शिव जी का कंठ नीला पड़ा और सर्प ने क्या किया!",
            "महादेव के गले में लिपटे नाग का गहरा आध्यात्मिक रहस्य!"
        ],
        "seo_metadata": {
            "description": "भगवान शिव के गले में सर्प वासुकि क्यों रहता है? जानिए समुद्र मंथन और हलाहल विष की पावन कथा। दिव्य दर्शनम् पर सनातन ज्ञान।",
            "keywords": ["भगवान शिव", "महादेव", "वासुकि नाग", "समुद्र मंथन", "नीलकंठ कथा", "सनातन धर्म", "शिव रहस्य"],
            "hashtags": ["#भगवानशिव", "#महादेव", "#शिवकथा", "#सनातनधर्म", "#दिव्यदर्शनम्"],
            "category": "Education"
        }
    },
    "te-IN": {
        "title_options": [
            "శివుని మెడలో పాము ఎందుకు ఉంటుంది? అసలు రహస్యం",
            "వాసుకి నాగరాజు మరియు పరమశివుని పవిత్ర గాథ",
            "సముద్ర మథనం మరియు నీలకంఠుని అద్భుత లీల",
            "శివుని మెడలోని సర్పం: అహంకారాన్ని జయించే దివ్య సందేశం",
            "పరమేశ్వరుడు వాసుకిని ఆభరణంగా ఎందుకు ధరించాడు?"
        ],
        "primary_title": "శివుని మెడలో పాము ఎందుకు ఉంటుంది? అసలు రహస్యం",
        "hook": "దేవాది దేవుడైన పరమేశ్వరుడు బంగారు ఆభరణాలకు బదులుగా ప్రాణాంతకమైన సర్పాన్ని ఎందుకు ధరించాడో మీకు తెలుసా? ఇది కేవలం అలంకారం కాదు, మన జీవితంలోని సమస్యలను ఎదుర్కొనేందుకు ఒక గొప్ప ఆధ్యాత్మిక పాఠం.",
        "audience": "భక్తులు, పురాణ ఆసక్తిపరులు మరియు ఆధ్యాత్మిక సాధకులు.",
        "story_arc": [
            "మొదటి భాగం: కైలాసంలో ప్రశాంత ధ్యానంలో ఉన్న శివుడు మరియు మెడలో వాసుకి సర్పం.",
            "రెండవ భాగం: క్షీరసాగర మథనం, హాలాహల విషం మరియు పరమశివునికి తోడుగా నిలిచిన వాసుకి కథ.",
            "మూడవ భాగం: ప్రతికూల పరిస్థితులను నియంత్రించి అంతరంగిక ప్రశాంతతను పొందే దివ్య సందేశం."
        ],
        "script_structure": {
            "act_1_opening": "కైలాస పర్వతంపై ధ్యానముద్రలో ఉన్న పరమశివుడు మరియు ఆయన మెడలోని నాగేంద్రుని వర్ణన.",
            "act_2_explanation": "సముద్ర మథనంలో హాలాహలం పుట్టడం, శివుడు దానిని సేవించడం, వాసుకి సమర్పణ.",
            "act_3_message": "విషాన్ని సైతం కంఠంలో నిలిపి లోకాలను రక్షించిన స్వామి మనోశక్తిని అనుసరించాలనే సందేశం."
        },
        "visual_plan": [
            {
                "scene_number": 1,
                "duration_seconds": 15,
                "description": "కైలాస పర్వతముపై పరమశివుడు ధ్యానంలో ఉండగా మెడలో వాసుకి పాము ప్రశాంతంగా ఉన్న దృశ్యం.",
                "image_prompt": "Cinematic close-up of meditating Lord Shiva, coiled cobra snake Vasuki on neck, Mount Kailash background, divine golden light, 8k",
                "video_prompt": "Serene camera panning slowly around meditating Lord Shiva, coiled cobra gently raising hood, divine mist"
            },
            {
                "scene_number": 2,
                "duration_seconds": 20,
                "description": "దేవదానవులు వాసుకిని తాడుగా చేసుకుని సముద్ర మథనం చేస్తున్న అద్భుత దృశ్యం.",
                "image_prompt": "Samudra Manthan cosmic churning, devas and asuras pulling giant serpent Vasuki, Mount Mandara spinning, dramatic lighting",
                "video_prompt": "Epic wide shot of devas and asuras churning cosmic milk ocean with giant serpent Vasuki"
            },
            {
                "scene_number": 3,
                "duration_seconds": 25,
                "description": "హాలాహల విషాన్ని శివుడు సేవిస్తుండగా పార్వతీదేవి కంఠంపై చేయి వేసిన దివ్య ఘట్టం.",
                "image_prompt": "Lord Shiva calmly drinking blue glowing Halahala poison, Goddess Parvati placing hand on his neck, divine dramatic aura",
                "video_prompt": "Slow motion shot of Lord Shiva drinking blue poison, throat glowing blue as Parvati touches it"
            },
            {
                "scene_number": 4,
                "duration_seconds": 15,
                "description": "శివుడు వాసుకి సర్పాన్ని కంఠాభరణంగా ధరించి అనుగ్రహిస్తున్న దృశ్యం.",
                "image_prompt": "Lord Shiva gently placing cobra Vasuki around his blue throat, cobra bowing in devotion, peaceful expression",
                "video_prompt": "Lord Shiva smiling and placing majestic cobra around his neck, golden aura sparks"
            },
            {
                "scene_number": 5,
                "duration_seconds": 15,
                "description": "ఆధ్యాత్మిక సాధకుడు ప్రశాంత వాతావరణంలో ధ్యానిస్తున్న దృశ్యం.",
                "image_prompt": "Serene individual meditating calmly in peaceful nature, soft morning sunlight, symbolic harmony",
                "video_prompt": "Peaceful meditation scene transitioning to sacred temple glow, ambient serenity"
            }
        ],
        "voice_direction": {
            "tone": "భక్తిపూర్వకం, ప్రశాంతం మరియు గాంభీర్యం.",
            "speed": "సహజమైన, స్పష్టమైన వేగం (నిమిషానికి సుమారు 115 పదాలు).",
            "emotion": "ఆధ్యాత్మిక అనుభూతిని కలిగించేలా.",
            "language_style": "తేట తెలుగు, స్పష్టమైన ఉచ్ఛారణతో కూడిన భక్తి సంభాషణ."
        },
        "shorts_hooks": [
            "శివుని మెడలో పాము ఎందుకు ఉంటుందో మీకు తెలుసా?",
            "హాలాహల విషాన్ని అమృతంగా మార్చిన పరమేశ్వరుని కథ!",
            "మెడలోని పాము ద్వారా పరమశివుడు మనకిచ్చే అద్భుత సందేశం!"
        ],
        "seo_metadata": {
            "description": "పరమశివుని మెడలో వాసుకి సర్పం ఎందుకు ఉంటుంది? సముద్ర మథనం మరియు నీలకంఠుని పవిత్ర గాథ. దివ్య దర్శనంలో ఆధ్యాత్మిక సత్యాలు.",
            "keywords": ["శివుడు", "వాసుకి", "సముద్ర మథనం", "నీలకంఠుడు", "తెలుగు భక్తి", "పరమేశ్వరుడు", "దివ్య దర్శనం"],
            "hashtags": ["#శివుడు", "#మహాదేవ్", "#భక్తికథలు", "#దివ్యదర్శనం", "#తెలుగుభక్తి"],
            "category": "Education"
        }
    }
}

_OFFLINE_SCRIPTS = {
    "hi-IN": {
        "title": "भगवान शिव के गले में सर्प क्यों है? जानिए रहस्य",
        "duration_seconds": 45,
        "narration": (
            "दिव्य दर्शनम् में आपका स्वागत है। क्या आपने कभी सोचा है कि भगवान शिव अपने गले में सर्प क्यों धारण करते हैं? "
            "समुद्र मंथन के समय जब संसार को नष्ट करने वाला हलाहल विष निकला, तब महादेव ने उसे पीकर अपने कंठ में रोक लिया। "
            "विष की तपन को शांत करने के लिए नागराज वासुकि ने शिव जी के कंठ का सहारा लिया। "
            "यह कथा हमें सिखाती है कि क्रोध और नकारात्मकता को अपने मन पर हावी न होने दें, बल्कि संयम से उन्हें अपने वश में रखें। ॐ नमः शिवाय।"
        ),
        "scene_scripts": [
            {
                "scene": 1,
                "duration_seconds": 45,
                "visual_reference": "कैलाश पर्वत पर भगवान शिव ध्यान मुद्रा में, गले में नाग वासुकि।",
                "voice_text": (
                    "दिव्य दर्शनम् में आपका स्वागत है। क्या आपने कभी सोचा है कि भगवान शिव अपने गले में सर्प क्यों धारण करते हैं? "
                    "समुद्र मंथन के समय जब संसार को नष्ट करने वाला हलाहल विष निकला, तब महादेव ने उसे पीकर अपने कंठ में रोक लिया। "
                    "विष की तपन को शांत करने के लिए नागराज वासुकि ने शिव जी के कंठ का सहारा लिया। "
                    "यह कथा हमें सिखाती है कि क्रोध और नकारात्मकता को अपने मन पर हावी न होने दें, बल्कि संयम से उन्हें अपने वश में रखें। ॐ नमः शिवाय।"
                ),
                "emotion": "भक्तिपूर्ण और शांत"
            }
        ],
        "retention_hooks": [
            "भगवान शिव के गले में सर्प का रहस्य आपको चकित कर देगा।",
            "समुद्र मंथन का वह क्षण जिसने महादेव को नीलकंठ बना दिया।"
        ],
        "shorts_scripts": [
            {
                "title": "शिव जी के गले में नाग क्यों है?",
                "hook": "क्या आप जानते हैं शिव जी गले में सांप क्यों पहनते हैं?",
                "body": "समुद्र मंथन से निकले भयंकर हलाहल विष को पीकर शिव जी ने सृष्टि की रक्षा की। विष की ज्वाला को शांत करने के लिए वासुकि नाग उनके गले में लिपट गए। हर हर महादेव!"
            },
            {
                "title": "नीलकंठ महादेव का दिव्य रहस्य",
                "hook": "महादेव का कंठ नीला कैसे पड़ा?",
                "body": "जब विष से तीनों लोक जलने लगे, तब शिव जी ने उसे कंठ में धारण किया और वासुकि नाग ने उन्हें शीतलता दी। लाइक और सब्सक्राइब करें!"
            },
            {
                "title": "शिव और वासुकि की पावन कथा",
                "hook": "सांप को आभूषण बनाने वाले एकमात्र देव!",
                "body": "महादेव सिखाते हैं कि संसार की विषमताओं को आभूषण बना लो। ॐ नमः शिवाय।"
            }
        ]
    },
    "te-IN": {
        "title": "శివుని మెడలో పాము ఎందుకు ఉంటుంది? అసలు రహస్యం",
        "duration_seconds": 45,
        "narration": (
            "దివ్య దర్శనానికి స్వాగతం. పరమశివుడు తన మెడలో ప్రాణాంతకమైన సర్పాన్ని ఎందుకు ధరించాడో ఎప్పుడైనా ఆలోచించారా? "
            "క్షీరసాగర మథనంలో సృష్టిని దహించివేసే హాలాహల విషం పుట్టినప్పుడు, లోక రక్షణ కోసం పరమేశ్వరుడు ఆ విషాన్ని స్వీకరించి తన కంఠంలో నిలిపాడు. "
            "ఆ విష జ్వాలల తాపాన్ని ఉపశమింపజేయడానికి నాగేంద్రుడైన వాసుకి శివుని మెడను ఆశ్రయించాడు. "
            "కోపాన్ని, అహంకారాన్ని నియంత్రించి జీవితంలో స్థైర్యాన్ని కలిగి ఉండాలని ఈ లీల మనకు బోధిస్తుంది. ఓం నమః శివాయ."
        ),
        "scene_scripts": [
            {
                "scene": 1,
                "duration_seconds": 45,
                "visual_reference": "కైలాస పర్వతముపై పరమశివుడు ధ్యానంలో ఉండగా మెడలో వాసుకి పాము ప్రశాంతంగా ఉన్న దృశ్యం.",
                "voice_text": (
                    "దివ్య దర్శనానికి స్వాగతం. పరమశివుడు తన మెడలో ప్రాణాంతకమైన సర్పాన్ని ఎందుకు ధరించాడో ఎప్పుడైనా ఆలోచించారా? "
                    "క్షీరసాగర మథనంలో సృష్టిని దహించివేసే హాలాహల విషం పుట్టినప్పుడు, లోక రక్షణ కోసం పరమేశ్వరుడు ఆ విషాన్ని స్వీకరించి తన కంఠంలో నిలిపాడు. "
                    "ఆ విష జ్వాలల తాపాన్ని ఉపశమింపజేయడానికి నాగేంద్రుడైన వాసుకి శివుని మెడను ఆశ్రయించాడు. "
                    "కోపాన్ని, అహంకారాన్ని నియంత్రించి జీవితంలో స్థైర్యాన్ని కలిగి ఉండాలని ఈ లీల మనకు బోధిస్తుంది. ఓం నమః శివాయ."
                ),
                "emotion": "భక్తిపూర్వకం మరియు ప్రశాంతం"
            }
        ],
        "retention_hooks": [
            "శివుని మెడలోని వాసుకి నాగరాజు కథ మీకు దివ్య జ్ఞానాన్ని అందిస్తుంది.",
            "సముద్ర మథనంలో నీలకంఠుని లీల మానవాళికి ఇచ్చే పరమ సందేశం."
        ],
        "shorts_scripts": [
            {
                "title": "శివుని మెడలో పాము ఎందుకు ఉంటుంది?",
                "hook": "పరమశివుడు మెడలో పామును ఎందుకు ధరించాడో మీకు తెలుసా?",
                "body": "లోకాలను కాపాడేందుకు హాలాహల విషాన్ని కంఠంలో నిలిపిన నీలకంఠునికి తోడుగా వాసుకి నిలిచాడు. రోజూ దివ్య దర్శనం కోసం సబ్‌స్క్రైబ్ చేయండి!"
            },
            {
                "title": "నీలకంఠుని అద్భుత లీల",
                "hook": "శివుని కంఠం నీలంగా ఎందుకు మారిందో తెలుసా?",
                "body": "సముద్ర మథన విషాన్ని తాగి లోక కళ్యాణం చేసిన స్వామికి వాసుకి చల్లదనాన్ని ఇచ్చే ఆభరణంగా మారాడు. ఓం నమః శివాయ!"
            },
            {
                "title": "వాసుకి నాగరాజు - పరమశివుని బంధం",
                "hook": "భయంకరమైన పాము శివునికి ఆభరణం ఎలా అయ్యింది?",
                "body": "అహంకారాన్ని, కష్టాలను సైతం మన అలంకారంగా మార్చుకోవాలని స్వామి మనకు నేర్పుతున్నారు. లైక్ చేసి షేర్ చేయండి!"
            }
        ]
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# Public Generation Functions
# ─────────────────────────────────────────────────────────────────────────────

def generate_brief_with_gemini(
    decision: dict,
    language_code: str = "hi-IN",
    allow_fallback: bool = True,
) -> dict:
    """
    Generates a structured content brief via Gemini in the target language (hi-IN or te-IN).
    Falls back to deterministic offline template if API key is missing or call fails (when allow_fallback=True).
    """
    if language_code not in ("hi-IN", "te-IN"):
        raise GeminiProviderError(f"Unsupported language code '{language_code}'. Must be 'hi-IN' or 'te-IN'.")

    lang_name = "Hindi in Devanagari script (हिन्दी)" if language_code == "hi-IN" else "Telugu in Telugu script (తెలుగు)"
    selected_topic = decision.get("selected_topic", "Hindu Deity Devotional Story")
    deity = decision.get("deity", "Lord Shiva")
    suggested_angle = decision.get("suggested_angle", "Spiritual wisdom and life lesson")

    prompt = f"""
You are an expert Hindu devotional content researcher and scriptwriter for YouTube channel "Divine Dharshanam Daily" (దివ్య దర్శనం / दिव्य दर्शनम्).
Generate a complete, production-ready Content Brief in {lang_name} for the topic:
Topic: "{selected_topic}"
Deity: "{deity}"
Angle: "{suggested_angle}"

Language Requirement:
- ALL titles, hook, audience, story_arc, script_structure, voice_direction, shorts_hooks, seo_metadata description/keywords/hashtags MUST be in natural, devotional, respectful {lang_name}.
- In visual_plan, image_prompt and video_prompt should be detailed English visual prompts (best for AI video/image generators) with Indian aesthetic specifications, while the scene description can be in {lang_name}.
- Provide EXACTLY 5 title_options in {lang_name}.
- Provide EXACTLY 5 scenes in visual_plan.
- Provide EXACTLY 3 shorts_hooks in {lang_name}.

Output must be ONLY valid JSON matching this schema:
{{
  "title_options": ["Title 1", "Title 2", "Title 3", "Title 4", "Title 5"],
  "primary_title": "Primary chosen title",
  "hook": "Engaging 1-2 sentence hook question or revelation",
  "audience": "Description of devotional viewers",
  "story_arc": ["Act 1 ...", "Act 2 ...", "Act 3 ..."],
  "script_structure": {{
    "act_1_opening": "...",
    "act_2_explanation": "...",
    "act_3_message": "..."
  }},
  "visual_plan": [
    {{
      "scene_number": 1,
      "duration_seconds": 15,
      "description": "...",
      "image_prompt": "Cinematic 8k ...",
      "video_prompt": "Cinematic camera movement ..."
    }},
    ...
  ],
  "voice_direction": {{
    "tone": "Respectful, devotional, captivating",
    "speed": "Measured and clear (approx 120 wpm)",
    "emotion": "Deep reverence, wonder, peace",
    "language_style": "Natural devotional {lang_name}"
  }},
  "shorts_hooks": ["Short Hook 1", "Short Hook 2", "Short Hook 3"],
  "seo_metadata": {{
    "description": "Engaging YouTube video description in {lang_name}",
    "keywords": ["tag1", "tag2", "tag3"],
    "hashtags": ["#tag1", "#tag2", "#tag3"],
    "category": "Education"
  }}
}}
"""
    system_instruction = (
        f"You are a master Hindu devotional storyteller. Generate authentic, respectful content strictly in {lang_name}."
    )

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if api_key:
        try:
            raw_output = call_gemini_api(prompt, system_instruction=system_instruction)
            cleaned = _clean_json_markdown(raw_output)
            brief_data = json.loads(cleaned)
            ok, err = validate_brief_output(brief_data)
            if ok:
                # Ensure output is genuinely in the target Indic script
                p_title = brief_data.get("primary_title", "")
                if not validate_indic_script(p_title, language_code):
                    raise GeminiProviderError(
                        f"Gemini returned non-Indic script for {language_code}: '{p_title[:50]}'"
                    )
                brief_data["language_code"] = language_code
                brief_data["generation_source"] = "gemini"
                logger.info("Content brief generated via Google Gemini API (%s)", language_code)
                return brief_data
            logger.warning("Gemini output failed schema validation: %s", err)
        except Exception as exc:
            safe_exc = _redact_key(str(exc), api_key)
            logger.warning("Gemini API call failed: %s", safe_exc)
            if not allow_fallback:
                raise GeminiProviderError(f"Gemini brief generation failed: {safe_exc}") from exc

    if not allow_fallback:
        raise GeminiProviderError("GEMINI_API_KEY missing or Gemini generation failed and fallback is disabled.")

    # Multilingual offline fallback
    if language_code not in ("hi-IN", "te-IN"):
        raise GeminiProviderError(f"Unsupported language code '{language_code}'. Only 'hi-IN' and 'te-IN' are supported.")

    template = _OFFLINE_BRIEFS.get(language_code)
    if not template:
        raise GeminiProviderError(f"No offline template available for language '{language_code}'.")

    fallback_brief = json.loads(json.dumps(template))
    fallback_brief["language_code"] = language_code
    fallback_brief["generation_source"] = "template_fallback"
    logger.warning("Content brief generated via deterministic offline template fallback (%s)", language_code)
    return fallback_brief


def generate_script_with_gemini(
    brief: dict,
    language_code: str = "hi-IN",
    content_type: str = "short",
    allow_fallback: bool = True,
) -> dict:
    """
    Generates a structured production script via Gemini in the target language (hi-IN or te-IN).
    Follows content_type ('short' or 'long'/'narrated').
    """
    if language_code not in ("hi-IN", "te-IN"):
        raise GeminiProviderError(f"Unsupported language code '{language_code}'. Must be 'hi-IN' or 'te-IN'.")

    lang_name = "Hindi in Devanagari script (हिन्दी)" if language_code == "hi-IN" else "Telugu in Telugu script (తెలుగు)"
    primary_title = brief.get("primary_title", "Divine Story")
    hook = brief.get("hook", "")
    story_arc = brief.get("story_arc", [])
    ct = (content_type or "short").lower().strip()

    prompt = f"""
You are an expert Hindu devotional narrator writing for YouTube channel "Divine Dharshanam Daily" (దివ్య దర్శనం / दिव्य दर्शनम्).
Generate a complete, production-ready script in {lang_name}.

Content Type: {ct.upper()}
Title: "{primary_title}"
Hook: "{hook}"
Story Arc: {json.dumps(story_arc, ensure_ascii=False)}

Requirements:
1. Language: Strictly {lang_name}. The spoken narration and voice text MUST be completely in {lang_name} using standard native script.
2. Structure:
   - "title": Title in {lang_name}.
   - "duration_seconds": Total duration in seconds (for 'short': 35 to 55 seconds, target ~45s; for 'long': 180 to 360 seconds).
   - "narration": Complete continuous voice narration text in {lang_name}.
   - "scene_scripts": Array of scenes. Each scene must have:
       "scene": integer (1, 2, ...),
       "duration_seconds": integer duration,
       "visual_reference": visual description,
       "voice_text": spoken text for this scene in {lang_name},
       "emotion": emotional tone.
   - "retention_hooks": list of 2-3 engaging retention hook questions in {lang_name}.
   - "shorts_scripts": list of exactly 3 vertical short scripts (EACH with "title", "hook", "body" in {lang_name}). (Required for 'short').

Output must be ONLY valid JSON matching this schema:
{{
  "title": "{primary_title}",
  "duration_seconds": 45,
  "narration": "Full narration text in {lang_name}...",
  "scene_scripts": [
    {{
      "scene": 1,
      "duration_seconds": 45,
      "visual_reference": "Visual reference...",
      "voice_text": "Spoken text in {lang_name}...",
      "emotion": "Devotional, calm"
    }}
  ],
  "retention_hooks": [
    "Hook 1 in {lang_name}",
    "Hook 2 in {lang_name}"
  ],
  "shorts_scripts": [
    {{
      "title": "Shorts 1 title in {lang_name}",
      "hook": "Shorts 1 hook in {lang_name}",
      "body": "Shorts 1 body in {lang_name}"
    }},
    {{
      "title": "Shorts 2 title in {lang_name}",
      "hook": "Shorts 2 hook in {lang_name}",
      "body": "Shorts 2 body in {lang_name}"
    }},
    {{
      "title": "Shorts 3 title in {lang_name}",
      "hook": "Shorts 3 hook in {lang_name}",
      "body": "Shorts 3 body in {lang_name}"
    }}
  ]
}}
"""
    system_instruction = (
        f"You are a master Hindu devotional narrator. Write natural, pure, respectful devotional spoken scripts in {lang_name}."
    )

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if api_key:
        try:
            raw_output = call_gemini_api(prompt, system_instruction=system_instruction)
            cleaned = _clean_json_markdown(raw_output)
            script_data = json.loads(cleaned)
            ok, err = validate_script_output(script_data, content_type=ct)
            if ok:
                # Ensure output is genuinely in the target Indic script
                narration = script_data.get("narration", "")
                if not validate_indic_script(narration, language_code):
                    raise GeminiProviderError(
                        f"Gemini returned non-Indic script for {language_code}: '{narration[:50]}'"
                    )
                script_data["language_code"] = language_code
                script_data["generation_source"] = "gemini"
                logger.info("Script generated via Google Gemini API (%s)", language_code)
                return script_data
            logger.warning("Gemini script output failed schema validation: %s", err)
        except Exception as exc:
            safe_exc = _redact_key(str(exc), api_key)
            logger.warning("Gemini API call failed: %s", safe_exc)
            if not allow_fallback:
                raise GeminiProviderError(f"Gemini script generation failed: {safe_exc}") from exc

    if not allow_fallback:
        raise GeminiProviderError("GEMINI_API_KEY missing or Gemini generation failed and fallback is disabled.")

    # Multilingual offline fallback
    if language_code not in ("hi-IN", "te-IN"):
        raise GeminiProviderError(f"Unsupported language code '{language_code}'. Only 'hi-IN' and 'te-IN' are supported.")

    template = _OFFLINE_SCRIPTS.get(language_code)
    if not template:
        raise GeminiProviderError(f"No offline template available for language '{language_code}'.")

    fallback_script = json.loads(json.dumps(template))
    fallback_script["language_code"] = language_code
    fallback_script["generation_source"] = "template_fallback"
    logger.warning("Script generated via deterministic offline template fallback (%s)", language_code)
    return fallback_script
