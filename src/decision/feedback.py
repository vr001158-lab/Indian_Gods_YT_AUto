# src/decision/feedback.py
# Performance Feedback & Deity Diversity Engine
# Analyzes data/publishing_history.json to calculate deity fatigue, recency penalties,
# and topic affinity adjustments for Divine Dharshanam Daily.

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.assets.selector import resolve_deity


DEFAULT_HISTORY_FILE = Path("data/publishing_history.json")


def load_publishing_history(history_file: str | Path = DEFAULT_HISTORY_FILE) -> list[dict[str, Any]]:
    """Safely loads publishing history records from JSON disk."""
    p = Path(history_file)
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return data
    except Exception:
        pass
    return []


def get_recent_deity_frequencies(
    history: list[dict[str, Any]] | None = None,
    limit: int = 10,
) -> dict[str, int]:
    """
    Returns the frequency count of each deity in the last `limit` published videos.
    Most recent entries appear at the end or beginning depending on published_at.
    """
    if history is None:
        history = load_publishing_history()

    # Sort descending by published_at if available
    def _sort_dt(rec: dict) -> str:
        return str(rec.get("published_at") or "")

    sorted_records = sorted(history, key=_sort_dt, reverse=True)[:limit]

    freq: dict[str, int] = {}
    for rec in sorted_records:
        topic = rec.get("topic") or rec.get("title") or ""
        deity = resolve_deity(topic, default="unknown")
        if deity:
            freq[deity] = freq.get(deity, 0) + 1
    return freq


def calculate_deity_fatigue_penalty(
    deity_key: str | None,
    history: list[dict[str, Any]] | None = None,
    max_penalty: float = 25.0,
) -> float:
    """
    Calculates a fatigue penalty score for a given deity based on recency in publishing history.
    - If the deity was the immediately preceding published video: penalty = max_penalty (25.0)
    - If published 2 videos ago: penalty = 15.0
    - If published 3 videos ago: penalty = 8.0
    - Otherwise: 0.0
    """
    if not deity_key or deity_key == "unknown":
        return 0.0

    if history is None:
        history = load_publishing_history()

    if not history:
        return 0.0

    def _sort_dt(rec: dict) -> str:
        return str(rec.get("published_at") or "")

    sorted_records = sorted(history, key=_sort_dt, reverse=True)

    penalty = 0.0
    for idx, rec in enumerate(sorted_records[:5]):
        rec_topic = rec.get("topic") or rec.get("title") or ""
        rec_deity = resolve_deity(rec_topic, default="unknown")
        if rec_deity == deity_key:
            if idx == 0:
                penalty = max(penalty, max_penalty)
            elif idx == 1:
                penalty = max(penalty, 15.0)
            elif idx == 2:
                penalty = max(penalty, 8.0)
            break

    return penalty


def get_day_of_week_deity_bonus(deity_key: str | None, now_dt: datetime | None = None) -> float:
    """
    Returns a cultural calendar bonus based on traditional Hindu devotional days of the week
    in Asia/Kolkata timezone:
    - Monday (Somvar): Lord Shiva, Parvati, Chandra
    - Tuesday (Mangalvar): Lord Hanuman, Ganesha, Durga, Kali, Subramanya
    - Wednesday (Budhvar): Budha, Ganesha, Krishna, Vithal
    - Thursday (Guruvar): Lord Vishnu, Brihaspati, Krishna
    - Friday (Shukravar): Mahalakshmi, Santoshi Ma, Annapurneshwari, Durga
    - Saturday (Shaniwar): Lord Shani, Hanuman
    - Sunday (Ravivar): Surya, Kaal Bhairav
    """
    from src.decision.weekday_deity import get_day_of_week_deity_bonus as _calc_bonus
    return _calc_bonus(deity_key=deity_key, now_dt=now_dt)
