# src/script/script_quality_evaluator.py
# Phase 2 — Telugu Devotional Script Quality Evaluator
# Evaluates language integrity, vocabulary richness, pacing, reverential tone,
# and structural completeness for Divine Dharshanam Daily.

from __future__ import annotations

import re
import unicodedata
from typing import Any


# Reverential devotional prefixes and honorifics in Telugu
DEVOTIONAL_TERMS_TE = [
    "శ్రీ", "స్వామి", "భగవాన్", "పరమ", "దివ్య", "పవిత్ర", "దేవుడు",
    "మహాదేవుడు", "పరమేశ్వరుడు", "మహాలక్ష్మి", "అవతారం", "దర్శనం",
    "లీల", "మహిమ", "కృప", "అనుగ్రహం", "భక్తి", "సాధన", "ఓం"
]

# Disallowed colloquial or inappropriate terms in sacred devotional scripts
DISALLOWED_TERMS_TE = [
    "అబద్ధం", "మోసగాడు", "చెత్త", "పిచ్చి", "సోది", "టైంపాస్"
]


def evaluate_script_quality(
    script_data: dict[str, Any],
    language_code: str = "te-IN",
    content_type: str = "short",
) -> tuple[bool, float, dict[str, Any], list[str]]:
    """
    Evaluates script quality for production readiness.

    Returns:
        (is_valid: bool, quality_score: float, metrics: dict, recommendations: list[str])
    """
    recommendations: list[str] = []
    flaws: list[str] = []

    title = (script_data.get("title") or "").strip()
    narration = (script_data.get("narration") or "").strip()
    scene_scripts = script_data.get("scene_scripts") or []
    duration = float(script_data.get("duration_seconds") or 0)

    # 1. Structural Checks
    if not title:
        flaws.append("Script title is empty.")
    if not narration:
        flaws.append("Script narration is empty.")
    if not scene_scripts:
        flaws.append("Script has no scene_scripts.")

    # 2. Language & Script Integrity Check
    telugu_char_count = len(re.findall(r"[\u0C00-\u0C7F]", narration))
    latin_char_count = len(re.findall(r"[a-zA-Z]", narration))
    total_letters = telugu_char_count + latin_char_count

    indic_ratio = telugu_char_count / max(1, total_letters)

    if language_code == "te-IN":
        if total_letters > 0 and indic_ratio < 0.60:
            flaws.append(
                f"Telugu Indic script ratio ({indic_ratio:.2%}) is below required 60%. "
                f"Detected {latin_char_count} Latin characters."
            )
        if telugu_char_count < 10 and not (script_data.get("format") == "old"):
            flaws.append("Narration contains insufficient Telugu text.")

    # 3. Devotional Tone & Reverence Evaluation
    reverential_matches = [term for term in DEVOTIONAL_TERMS_TE if term in narration or term in title]
    reverential_score = min(100.0, len(reverential_matches) * 15.0)
    if not reverential_matches and not (script_data.get("format") == "old"):
        recommendations.append("Consider including respectful Telugu honorifics (శ్రీ, స్వామి, భగవాన్, పరమ, దివ్య).")

    # Check for vulgar / inappropriate words
    found_disallowed = [w for w in DISALLOWED_TERMS_TE if w in narration]
    if found_disallowed:
        flaws.append(f"Inappropriate or colloquial terms detected in devotional script: {found_disallowed}")

    # 4. Duration & Pacing Evaluation
    words = narration.split()
    word_count = len(words)
    wpm = (word_count / max(1.0, duration)) * 60.0

    if content_type == "short":
        if duration < 30.0 or duration > 65.0:
            recommendations.append(f"Shorts duration ({duration}s) outside optimal 35s-55s target.")
        if word_count > 160:
            recommendations.append(f"Word count ({word_count}) is high for a short, risk of rushed TTS.")
    else:  # long video
        if duration < 120.0:
            recommendations.append(f"Long video duration ({duration}s) is shorter than target 180s-360s.")

    # 5. Scene Pacing
    for i, scene in enumerate(scene_scripts, 1):
        sc_dur = float(scene.get("duration_seconds") or 0)
        sc_voice = (scene.get("voice_text") or "").strip()
        if sc_dur <= 0:
            flaws.append(f"Scene #{i} has non-positive duration ({sc_dur}s).")
        if not sc_voice and not (script_data.get("format") == "old"):
            recommendations.append(f"Scene #{i} has empty voice text.")

    # Calculate overall quality score (0 - 100)
    base_score = 100.0
    base_score -= len(flaws) * 25.0
    base_score -= len(recommendations) * 5.0
    if reverential_score < 30:
        base_score -= 10.0

    quality_score = max(0.0, min(100.0, round(base_score, 1)))
    is_valid = len(flaws) == 0 and quality_score >= 50.0

    metrics = {
        "indic_ratio": round(indic_ratio, 3),
        "telugu_chars": telugu_char_count,
        "latin_chars": latin_char_count,
        "word_count": word_count,
        "words_per_minute": round(wpm, 1),
        "reverential_matches": reverential_matches,
        "reverential_score": reverential_score,
        "duration_seconds": duration,
        "scene_count": len(scene_scripts),
        "flaws": flaws,
    }

    return is_valid, quality_score, metrics, recommendations
