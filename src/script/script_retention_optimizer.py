# src/script/script_retention_optimizer.py
# Phase 2 — Telugu Script Retention & Narrative Engagement Optimizer
# Evaluates structural storytelling dimensions:
#   1. Opening Hook Relevance & Curiosity Gap
#   2. Narrative Progression & Scene Transitions
#   3. Emotional Development & Devotional Arc
#   4. Climax & Divine Manifestation
#   5. Resolution & Sacred Devotional Payoff
#   6. Lexical Repetition & Redundancy Detection
#
# Deterministic & bounded. Does not invent retention predictions or guarantee audience numbers.
# Advisory retention warnings are distinguished from critical factuality failures.

from __future__ import annotations

import re
import unicodedata
from typing import Any


# Structural curiosity and inquiry markers in Telugu
INQUIRY_MARKERS_TE: list[str] = [
    "తెలుసా", "ఎందుకు", "ఎలా", "ఏమిటి", "రహస్యం", "కారణం", "ఆశ్చర్యం",
    "విశేషం", "ఆలోచించారా", "ఈ కథ విన్నారా", "సత్యం", "ఎలాంటి", "ఏమిటో"
]

# Narrative transition & temporal progression markers in Telugu
TRANSITION_MARKERS_TE: list[str] = [
    "అప్పుడు", "తరువాత", "అంతట", "ఆ సమయంలో", "చివరికి", "వెంటనే",
    "అందుకే", "క్షణంలో", "వేళ", "ముందు", "క్రమంగా", "సాగాడు", "సాగిస్తూ",
    "మధ్యలో", "అనంతరం", "ఇంతలో", "సమయంలో"
]

# Climax & Divine action indicators in Telugu
CLIMAX_INDICATORS_TE: list[str] = [
    "అద్భుతం", "విశ్వరూపం", "ఆవిర్భావం", "రక్షించిన", "సంహరించి", "మోక్షం",
    "ఎత్తాడు", "ధరించిన", "పూర్తయి", "విజయం", "సంజీవని", "ఆవిర్భవించాడు",
    "విరిచి", "పెకలించి", "ధరించాడు", "చేధించి", "స్వీకరించి"
]

# Resolution, blessing, and sacred payoff indicators in Telugu
PAYOFF_INDICATORS_TE: list[str] = [
    "ఆశీస్సులు", "అనుగ్రహం", "శరణు", "శాంతి", "సందేశం", "పాఠం", "రక్షణ",
    "జయించే", "పుణ్యం", "మోక్షం", "ధర్మం", "కళ్యాణం", "ఓం", "నమః", "జై",
    "గోవిందా", "నారాయణాయ", "హర", "శుభం", "సమర్పణ"
]


def _tokenize_indic(text: str) -> set[str]:
    """Tokenize Indic and Latin words stripping punctuation."""
    cleaned = "".join(
        ch if not unicodedata.category(ch).startswith(("P", "S", "Z", "C")) else " "
        for ch in text
    )
    return {w.lower() for w in cleaned.split() if len(w) >= 2}


def evaluate_script_retention(
    script_data: dict[str, Any],
) -> tuple[bool, float, list[str]]:
    """
    Evaluates audience retention structure for a devotional script.

    Examines:
      - Opening hook relevance & curiosity gap
      - Narrative progression & event transitions
      - Emotional development
      - Climax detection
      - Resolution & devotional payoff
      - Lexical repetition detection

    Returns:
        (is_optimized: bool, retention_score: float, suggestions: list[str])
    """
    suggestions: list[str] = []
    title = (script_data.get("title") or "").strip()
    narration = (script_data.get("narration") or "").strip()
    scene_scripts = script_data.get("scene_scripts") or []
    retention_hooks = script_data.get("retention_hooks") or []
    shorts_scripts = script_data.get("shorts_scripts") or []
    is_old = script_data.get("format") == "old"

    if is_old:
        # Music-only format is evaluated on musical timing rather than spoken hooks
        return True, 85.0, ["Music-only format: spoken retention checks bypassed."]

    score = 0.0

    # ── 1. Opening Hook Relevance & Curiosity Gap (20 pts) ────────────────────
    opening_text = ""
    if scene_scripts:
        opening_text = scene_scripts[0].get("voice_text", "")
    else:
        opening_text = narration[:150]

    hook_score = 0.0
    title_tokens = _tokenize_indic(title)
    open_tokens = _tokenize_indic(opening_text)

    # Check topical connection
    has_title_connection = len(title_tokens & open_tokens) > 0 or any(t in opening_text for t in title_tokens if len(t) >= 4)
    if has_title_connection:
        hook_score += 10.0
    else:
        suggestions.append("Hook relevance: Ensure Scene 1 mentions the central deity or question from the title.")

    # Check curiosity gap
    has_inquiry = any(marker in opening_text or marker in title for marker in INQUIRY_MARKERS_TE)
    has_qmark = "?" in opening_text or "?" in title
    if has_inquiry or has_qmark:
        hook_score += 10.0
    else:
        suggestions.append("Curiosity gap: Introduce a clear devotional question or mystery in the opening seconds.")

    score += hook_score

    # ── 2. Narrative Progression & Scene Transitions (20 pts) ────────────────
    progression_score = 0.0
    num_scenes = len(scene_scripts)
    full_voice = " ".join([s.get("voice_text", "") for s in scene_scripts]) or narration

    if num_scenes >= 3:
        # Check transition words
        found_transitions = [tr for tr in TRANSITION_MARKERS_TE if tr in full_voice]
        if len(found_transitions) >= 2:
            progression_score += 10.0
        elif len(found_transitions) == 1:
            progression_score += 6.0
            suggestions.append("Narrative transitions: Use progressive connectors (e.g. 'అప్పుడు', 'తరువాత', 'ఆ సమయంలో').")
        else:
            suggestions.append("Narrative flow: Connect scenes with temporal transitions for smoother story progression.")

        # Check scene duration balance
        durations = [float(s.get("duration_seconds", 0)) for s in scene_scripts]
        total_dur = sum(durations)
        if total_dur > 0:
            max_share = max(durations) / total_dur
            if max_share <= 0.50:
                progression_score += 10.0
            else:
                progression_score += 5.0
                suggestions.append("Pacing: Balance scene durations so no single scene monopolizes more than 50% of the video.")
    else:
        progression_score += 10.0
        suggestions.append("Structure: Multi-scene scripts (4-5 scenes) retain audience attention better than single blocks.")

    score += progression_score

    # ── 3. Emotional Development & Devotional Arc (15 pts) ───────────────────
    emotional_score = 0.0
    emotions = [s.get("emotion", "").strip() for s in scene_scripts if s.get("emotion")]
    distinct_emotions = set(emotions)

    if len(distinct_emotions) >= 2:
        emotional_score += 10.0
    else:
        emotional_score += 6.0

    # Check for devotional sentiment progression
    reverential_words = ["భక్తి", "ప్రశాంతం", "అద్భుతం", "ధైర్యం", "ఆనందం", "కరుణ", "శరణాగతి"]
    found_sentiments = [w for w in reverential_words if w in full_voice] if num_scenes > 0 else []
    if len(found_sentiments) >= 2:
        emotional_score += 5.0
    else:
        suggestions.append("Emotional development: Weave an emotional arc transitioning from wonder or crisis into divine peace.")

    score += min(15.0, emotional_score)

    # ── 4. Climax & Divine Manifestation (15 pts) ────────────────────────────
    climax_score = 0.0
    middle_scenes = scene_scripts[1:-1] if len(scene_scripts) >= 3 else scene_scripts
    mid_text = " ".join([s.get("voice_text", "") for s in middle_scenes])

    has_climax = any(ind in mid_text for ind in CLIMAX_INDICATORS_TE)
    if has_climax:
        climax_score = 15.0
    else:
        climax_score = 7.0
        suggestions.append("Story climax: Emphasize the miraculous turning point or divine manifestation in the middle scenes.")

    score += climax_score

    # ── 5. Resolution & Sacred Devotional Payoff (15 pts) ─────────────────────
    resolution_score = 0.0
    closing_text = scene_scripts[-1].get("voice_text", "") if scene_scripts else narration[-150:]

    has_payoff = any(p in closing_text for p in PAYOFF_INDICATORS_TE)
    if has_payoff:
        resolution_score = 15.0
    else:
        resolution_score = 6.0
        suggestions.append("Devotional payoff: End with a meaningful blessing, moral message, or sacred chant (e.g. 'ఓం', 'జై శ్రీరామ్').")

    score += resolution_score

    # ── 6. Retention Hooks & Shorts Structure (15 pts) ───────────────────────
    hook_pts = 0.0
    if len(retention_hooks) >= 2:
        hook_pts += 8.0
    else:
        suggestions.append("Retention hooks: Include at least 2 structured mid-video curiosity anchors.")

    if script_data.get("content_type", "short") == "short":
        if len(shorts_scripts) >= 3:
            hook_pts += 7.0
        else:
            suggestions.append("Vertical Shorts: Include 3 dedicated shorts variants with custom hooks.")
    else:
        hook_pts += 7.0

    score += hook_pts

    # ── 7. Repetition & Redundancy Penalty (Deduction up to -15 pts) ──────────
    penalty = 0.0
    if len(scene_scripts) >= 2:
        for i in range(len(scene_scripts) - 1):
            t1 = _tokenize_indic(scene_scripts[i].get("voice_text", ""))
            t2 = _tokenize_indic(scene_scripts[i + 1].get("voice_text", ""))
            if t1 and t2:
                overlap = len(t1 & t2) / max(len(t1), len(t2))
                if overlap > 0.60:
                    penalty += 7.5
                    suggestions.append(f"Repetition: Scenes #{i+1} and #{i+2} have excessive phrase overlap ({overlap:.0%}).")

    final_score = max(0.0, min(100.0, round(score - penalty, 1)))
    is_optimized = final_score >= 70.0

    return is_optimized, final_score, suggestions
