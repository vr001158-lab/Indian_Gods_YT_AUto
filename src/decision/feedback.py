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
    Returns a cultural calendar bonus based on traditional Hindu devotional days of the week:
    - Monday: Lord Shiva
    - Tuesday: Lord Hanuman / Subrahmanya
    - Wednesday: Lord Ganesha / Lord Krishna
    - Thursday: Lord Vishnu / Guru / Dattatreya / Sai
    - Friday: Goddess Lakshmi / Parvati / Durga
    - Saturday: Lord Venkateswara / Balaji / Shani / Hanuman
    - Sunday: Surya Bhagavan
    """
    if not deity_key:
        return 0.0

    if now_dt is None:
        now_dt = datetime.now(timezone.utc)

    # 0 = Monday, 1 = Tuesday, ..., 6 = Sunday
    weekday = now_dt.weekday()

    DAY_AFFINITY: dict[int, list[str]] = {
        0: ["lord_shiva"],
        1: ["hanuman", "subramanya"],
        2: ["ganesha", "krishna"],
        3: ["lord_vishnu"],
        4: ["lakshmi_devi", "parvathi"],
        5: ["7Kondala_Swami", "hanuman"],
        6: ["surya"],
    }

    matching_deities = DAY_AFFINITY.get(weekday, [])
    if deity_key in matching_deities:
        return 5.0
    return 0.0
