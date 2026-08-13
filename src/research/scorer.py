# src/research/scorer.py
# Topic Opportunity Score v0.1 — multi-dimensional ranking heuristic.
#
# IMPORTANT: This is a ranking heuristic, NOT a view-count predictor.
# Scores reflect relative opportunity signals from available data.
# Do NOT interpret a high score as a guarantee of views or growth.

import math
import datetime

SCORE_VERSION: str = "v0.1"

# ── Thresholds ────────────────────────────────────────────────────────────────
HIGH_COMPETITION_VIEWS: int = 500_000   # videos above this count as "dominant"
EVERGREEN_AGE_DAYS:     int = 730       # >= 2 years = evergreen candidate
EVERGREEN_MIN_VIEWS:    int = 50_000    # min views for an old video to signal evergreen

# ── Curiosity hook phrases ────────────────────────────────────────────────────
CURIOSITY_TRIGGERS = [
    "why", "secrets of", "mystery", "mysteries of",
    "untold", "hidden", "broken", "curse", "symbolism",
]

# ── Formula weights (must sum to 1.0) ────────────────────────────────────────
WEIGHT_DEMAND:     float = 0.25
WEIGHT_RELEVANCE:  float = 0.25
WEIGHT_COMPETITION:float = 0.20
WEIGHT_EVERGREEN:  float = 0.15
WEIGHT_FRESHNESS:  float = 0.15


def _confidence_from_source(data_source: str, num_videos: int) -> str:
    """
    Derives evidence confidence from data quality signals.
      high   — real API data, ≥3 competitor videos found
      medium — real API data but sparse results, OR cached real data
      low    — mock/offline data or 0 competitors found
    """
    is_real = data_source in ("youtube_api", "cached_youtube_api")
    if not is_real:
        return "low"
    if num_videos >= 3:
        return "high"
    return "medium"


class TopicScorer:
    """
    Topic Opportunity Score v0.1.

    Formula (weights above):
        overall = Demand*0.25 + Relevance*0.25 + Competition*0.20
                + Evergreen*0.15 + Freshness*0.15

    Relevance is halved when the festival date is unverified (lunisolar drift).
    All component scores are in the range [0, 100].
    """

    @staticmethod
    def calculate_score(
        topic_meta:      dict,
        youtube_videos:  list,
        festival_info:   dict,
        data_source:     str = "mock",
    ) -> dict:
        """
        Parameters
        ----------
        topic_meta      : topic dict from SUGGESTED_TOPICS
        youtube_videos  : list of video records (may be empty)
        festival_info   : dict from collector.get_festival_info()
        data_source     : string label ("youtube_api", "mock", …)

        Returns
        -------
        Detailed scoring dict including score_version and confidence.
        """
        today = datetime.datetime.now(datetime.timezone.utc)
        n = len(youtube_videos)

        # ── 1. Demand ─────────────────────────────────────────────────────────
        if n > 0:
            avg_views = sum(v["views"] for v in youtube_videos) / n
            max_views = max(v["views"] for v in youtube_videos)
        else:
            avg_views = 0
            max_views = 0

        demand_score = (
            min(100, max(20, round(math.log10(avg_views) * 16.5)))
            if avg_views > 0 else 20
        )

        # ── 2. Competition ────────────────────────────────────────────────────
        dominant_count = sum(1 for v in youtube_videos if v["views"] >= HIGH_COMPETITION_VIEWS)
        competition_score = max(10, 100 - (dominant_count * 18))

        # ── 3. Audience Relevance (festival proximity) ────────────────────────
        days_left = festival_info["days_remaining"]
        festival_verified = festival_info.get("verified", False)
        raw_relevance = max(50, 100 - days_left)
        # Halve the contribution when date is unverified (lunisolar drift may be ±15 days)
        relevance_score = round(raw_relevance * (1.0 if festival_verified else 0.5))

        # ── 4. Freshness ──────────────────────────────────────────────────────
        fresh_count = 0
        for v in youtube_videos:
            try:
                pub = datetime.datetime.fromisoformat(v["published_at"].replace("Z", "+00:00"))
                if (today - pub).days <= 365:
                    fresh_count += 1
            except Exception:
                pass
        freshness_score = max(30, round((fresh_count / max(1, n)) * 100))

        # ── 5. Evergreen ──────────────────────────────────────────────────────
        evergreen_count = 0
        for v in youtube_videos:
            try:
                pub = datetime.datetime.fromisoformat(v["published_at"].replace("Z", "+00:00"))
                age_d = (today - pub).days
                if age_d >= EVERGREEN_AGE_DAYS and v["views"] >= EVERGREEN_MIN_VIEWS:
                    evergreen_count += 1
            except Exception:
                pass
        evergreen_score = min(100, 65 + (evergreen_count * 10))

        # ── 6. Curiosity ──────────────────────────────────────────────────────
        topic_lower = topic_meta["topic"].lower()
        curiosity_score = 75
        for trigger in CURIOSITY_TRIGGERS:
            if trigger in topic_lower:
                curiosity_score = 92
                break

        # ── 7. Long-form / Shorts potential ──────────────────────────────────
        long_form_potential = min(100, max(40, round(
            (demand_score * 0.6) + (evergreen_score * 0.4)
        )))
        shorts_potential = min(100, max(40, round(
            (curiosity_score * 0.7) + (freshness_score * 0.3)
        )))

        # ── 8. Overall score ──────────────────────────────────────────────────
        overall_score = round(
            (demand_score     * WEIGHT_DEMAND) +
            (relevance_score  * WEIGHT_RELEVANCE) +
            (competition_score* WEIGHT_COMPETITION) +
            (evergreen_score  * WEIGHT_EVERGREEN) +
            (freshness_score  * WEIGHT_FRESHNESS)
        )

        # ── 9. Confidence ─────────────────────────────────────────────────────
        confidence = _confidence_from_source(data_source, n)

        return {
            "score_version":       SCORE_VERSION,
            "overall_score":       overall_score,
            "demand_score":        demand_score,
            "relevance_score":     relevance_score,
            "competition_score":   competition_score,
            "evergreen_score":     evergreen_score,
            "freshness_score":     freshness_score,
            "curiosity_score":     curiosity_score,
            "long_form_potential": long_form_potential,
            "shorts_potential":    shorts_potential,
            "confidence":          confidence,
            "festival_verified":   festival_verified,
            "stats": {
                "avg_views":       round(avg_views),
                "max_views":       max_views,
                "dominant_count":  dominant_count,
                "fresh_count":     fresh_count,
                "evergreen_count": evergreen_count,
                "num_videos":      n,
            },
        }
