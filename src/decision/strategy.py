# src/decision/strategy.py
# Strategy layer for format-specific candidate selection preferences.
# Isolates channel analytics weighted signals from generic validator.py safety gates.

from typing import Any

# Historical channel analytics weighted signals for Old Format Devotional Visual Shorts.
# Weight bonuses are applied during old-format topic selection prior to ranking.
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
