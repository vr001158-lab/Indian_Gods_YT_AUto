# src/decision/strategy.py
# Strategy layer for format-specific and intelligence-driven candidate selection preferences.
# Isolates channel analytics weighted signals and deity diversity from generic validator.py safety gates.

from __future__ import annotations

import re
from typing import Any

from src.assets.selector import resolve_deity
from src.decision.feedback import (
    calculate_deity_fatigue_penalty,
    get_day_of_week_deity_bonus,
    load_publishing_history,
)
from src.research.scriptural_source_registry import get_scripture_reference_for_topic


# Historical channel analytics weighted signals for Old Format Devotional Visual Shorts.
OLD_FORMAT_TOPIC_PREFERENCES: dict[str, float] = {
    "venkateshwara": 15.0,
    "tirumala": 15.0,
    "7 kondala": 15.0,
    "hanuman": 12.0,
    "ayyappa": 12.0,
    "shiva": 10.0,
    "mahadev": 10.0,
    "narasimha": 10.0,
    "lakshmi narasimha": 12.0,
    "suprabhatam": 10.0,
}

# Series keywords that indicate serial narrative potential
SERIES_KEYWORDS = {
    "dashavatar": 8.0,
    "avatar": 5.0,
    "ramayana": 7.0,
    "mahabharata": 7.0,
    "samudra manthan": 8.0,
    "jyotirlinga": 8.0,
    "shakti peeth": 8.0,
    "leela": 5.0,
    "bhakti": 4.0,
    "rahasyam": 6.0,
}


def apply_old_format_topic_preferences(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Applies topic preference bonuses to research candidates for old-format selection.
    Does not modify the original candidate dicts in-place.
    """
    adjusted = []
    for candidate in candidates:
        c_copy = dict(candidate)
        topic_lower = (c_copy.get("topic") or "").lower()
        bonus = 0.0
        for keyword, weight in OLD_FORMAT_TOPIC_PREFERENCES.items():
            if keyword in topic_lower:
                bonus = max(bonus, weight)

        # Apply preference bonus to overall_score signal
        c_copy["overall_score"] = float(c_copy.get("overall_score", 0)) + bonus
        adjusted.append(c_copy)
    return adjusted


def apply_content_intelligence_preferences(
    candidates: list[dict[str, Any]],
    language_code: str = "te-IN",
    history: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """
    Applies multi-factor devotional content intelligence adjustments:
      1. Deity Fatigue Penalty (reduces score if recently published to avoid monotony)
      2. Telugu Cultural / Day-of-Week Calendar Bonus
      3. Series Potential Bonus (narrative arcs & avatar sequences)
      4. Scriptural Source Reliability Bonus (primary shastra backing)

    Attaches `intelligence_factors` to each candidate dict for explainable logs.
    """
    if history is None:
        history = load_publishing_history()

    adjusted = []
    for candidate in candidates:
        c_copy = dict(candidate)
        topic = c_copy.get("topic", "")
        deity_hint = c_copy.get("deity", "")
        deity_key = resolve_deity(topic, deity_hint=deity_hint, default="unknown")

        # 1. Deity Fatigue Penalty
        fatigue_penalty = calculate_deity_fatigue_penalty(deity_key, history=history)

        # 2. Day of Week Cultural Calendar Bonus
        calendar_bonus = get_day_of_week_deity_bonus(deity_key)

        # 3. Series Potential
        topic_lower = topic.lower()
        series_bonus = 0.0
        matched_series = []
        for kw, weight in SERIES_KEYWORDS.items():
            if kw in topic_lower:
                series_bonus = max(series_bonus, weight)
                matched_series.append(kw)

        # 4. Scriptural Reliability
        scripture_ref = get_scripture_reference_for_topic(topic, deity=deity_hint or deity_key)
        source_bonus = 0.0
        source_tier = "unregistered"
        source_citation = ""
        if scripture_ref:
            source_tier = scripture_ref.source_tier
            source_citation = f"{scripture_ref.text_name} ({scripture_ref.division})"
            source_bonus = 6.0 if source_tier == "primary" else 3.0

        # Compute net adjustment
        base_score = float(c_copy.get("overall_score", 0))
        net_adjustment = -fatigue_penalty + calendar_bonus + series_bonus + source_bonus
        final_score = max(0.0, round(base_score + net_adjustment, 2))

        c_copy["overall_score"] = final_score
        c_copy["intelligence_factors"] = {
            "resolved_deity": deity_key,
            "base_score": base_score,
            "fatigue_penalty": fatigue_penalty,
            "calendar_bonus": calendar_bonus,
            "series_bonus": series_bonus,
            "source_tier": source_tier,
            "source_bonus": source_bonus,
            "source_citation": source_citation,
            "matched_series": matched_series,
            "final_score": final_score,
        }
        adjusted.append(c_copy)

    return adjusted
