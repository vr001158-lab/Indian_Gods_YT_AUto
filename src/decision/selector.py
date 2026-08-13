# src/decision/selector.py
# Phase 2B.1 — Deterministic topic selection from validated candidates.
#
# Selection priority (descending):
#   1. overall_score       — primary ranking signal
#   2. demand_score        — audience search demand
#   3. freshness_score     — recency of competing content
#   4. content_gap quality — numerical proxy derived from gap label
#   5. relevance_score     — festival/calendar proximity
#   6. curiosity_score     — hook strength of the topic title
#
# The sort key is fully deterministic: same input → same selection, always.
# A secondary tie-breaker on the topic string itself prevents non-determinism
# when two candidates are numerically identical on all six dimensions.

import re


# ── Content-gap quality proxy ─────────────────────────────────────────────────
# Maps content_gap label keywords → numeric priority.
# Higher = stronger opportunity signal.
_GAP_STRENGTH = {
    "possible gap":               3,
    "possible evergreen refresh": 2,
    "curiosity-hook":             1,
    "high saturation":            0,
    "insufficient evidence":      0,
}


def _gap_priority(content_gap: str) -> int:
    """Returns a numeric priority for a content_gap string (higher = better)."""
    if not isinstance(content_gap, str):
        return 0
    lower = content_gap.lower()
    for keyword, priority in _GAP_STRENGTH.items():
        if keyword in lower:
            return priority
    return 0


def _sort_key(candidate: dict) -> tuple:
    """
    Returns a fully deterministic sort key for a validated candidate.
    All numeric fields are negated so that sort() with reverse=False gives
    descending order — this avoids reverse=True which is less transparent.
    """
    return (
        -candidate["overall_score"],
        -candidate["demand_score"],
        -candidate["freshness_score"],
        -_gap_priority(candidate.get("content_gap", "")),
        -candidate["relevance_score"],
        -candidate["curiosity_score"],
        candidate["topic"],          # ascending string tie-breaker
    )


def _deduplicate_validated(candidates: list) -> list:
    """
    Removes near-duplicate topics from already-validated candidates.
    Uses the same fingerprint logic as src/research/dedup.py but operates
    independently so the decision layer has no import dependency on research.
    """
    _STOP_WORDS = {
        "the", "a", "an", "of", "in", "on", "at", "and", "or", "is", "was",
        "are", "were", "why", "how", "what", "who", "when", "lord", "goddess",
        "god", "story", "stories", "tale", "legend", "reason", "secret",
        "hidden", "untold", "meaning", "mystery", "mysteries",
    }
    MIN_OVERLAP = 2

    def _fp(topic: str) -> frozenset:
        words = re.sub(r"[^a-z0-9\s]", "", topic.lower()).split()
        return frozenset(w for w in words if w not in _STOP_WORDS)

    seen = []
    unique = []
    for c in candidates:
        fp = _fp(c["topic"])
        if not any(len(fp & s) >= MIN_OVERLAP for s in seen):
            seen.append(fp)
            unique.append(c)
    return unique


def select_topic(valid_candidates: list) -> dict:
    """
    Selects the single best topic from a list of validated candidates.

    Parameters
    ----------
    valid_candidates : list — output of validator.validate_candidates()[0]
                              Must already have passed all safety gates.

    Returns
    -------
    {
        "selected": dict | None,    — the winning candidate, or None
        "ranked":   list,           — all candidates in priority order
        "dedup_removed": list,      — candidates dropped as near-duplicates
    }

    The system fails closed: if valid_candidates is empty, selected is None.
    """
    if not valid_candidates:
        return {"selected": None, "ranked": [], "dedup_removed": []}

    # Sort first so dedup preserves the highest-ranked from each cluster
    ranked = sorted(valid_candidates, key=_sort_key)

    # Remove near-duplicates (keeps first = highest-ranked in each cluster)
    unique = _deduplicate_validated(ranked)
    dedup_removed = [c for c in ranked if c not in unique]

    return {
        "selected":      unique[0] if unique else None,
        "ranked":        ranked,
        "dedup_removed": dedup_removed,
    }
