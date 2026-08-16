# src/decision/validator.py
# Phase 2B.1 — Production-safety gate for research candidates.
#
# SAFETY CONTRACT:
#   A candidate may ONLY be approved when ALL of the following are true:
#     1. data_source is "youtube_api" or "cached_youtube_api"
#     2. confidence == "high"
#     3. overall_score >= min_score (default 60)
#     4. All required fields are present with non-None values
#
# The validator is deliberately strict:
#   - Never converts invalid data into valid data.
#   - Never promotes mock/offline candidates, regardless of score.
#   - Returns explicit rejection reasons for every failed candidate.

# ── Required fields in every research candidate ───────────────────────────────
# These are the actual field names produced by src/research/report.py.
# Note: the spec says "long_form_score"/"shorts_score"/"score" but the
# pipeline produces "long_form_potential"/"shorts_potential"/"overall_score".
# The validator uses the real pipeline field names.
REQUIRED_FIELDS = (
    "topic",
    "category",
    "overall_score",       # spec: "score"
    "demand_score",
    "relevance_score",
    "competition_score",
    "evergreen_score",
    "freshness_score",
    "curiosity_score",
    "long_form_potential", # spec: "long_form_score"
    "shorts_potential",    # spec: "shorts_score"
    "data_source",
    "confidence",
    "suggested_angle",
    "content_gap",
)

# ── Accepted real-data sources ────────────────────────────────────────────────
import json
from pathlib import Path

REAL_DATA_SOURCES = frozenset({"youtube_api", "cached_youtube_api"})


def _load_published_topics(history_file: str | Path = "data/publishing_history.json") -> set[str]:
    p = Path(history_file)
    published = set()
    if p.exists():
        try:
            records = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(records, list):
                for rec in records:
                    top = (rec.get("topic") or "").strip().lower()
                    if top:
                        published.add(top)
        except Exception:
            pass
    return published


def validate_candidate(
    candidate: dict,
    min_score: int = 60,
    published_topics: set[str] | None = None,
) -> tuple:
    """
    Validates a single research candidate against all production-safety gates.

    Parameters
    ----------
    candidate : dict   — one item from a research_results_*.json list
    min_score : int    — minimum overall_score required (default 60)
    published_topics : set — set of lowercase topic strings already published

    Returns
    -------
    (True, [])                  — candidate passed all gates
    (False, [reason, ...])      — candidate rejected; reasons list is non-empty
    """
    reasons = []

    # Gate 0: input must be a dict
    if not isinstance(candidate, dict):
        return False, ["Candidate is not a dict — malformed input"]

    # Gate 1: Required fields must be present and not None
    for field in REQUIRED_FIELDS:
        if field not in candidate:
            reasons.append(f"Missing required field: '{field}'")
        elif candidate[field] is None:
            reasons.append(f"Required field '{field}' is None")

    # Stop early if the candidate is structurally invalid — later checks
    # would produce misleading errors on missing/None fields.
    if reasons:
        return False, reasons

    # Gate 2: data_source must be real (never mock or offline)
    data_source = candidate["data_source"]
    if data_source not in REAL_DATA_SOURCES:
        reasons.append(
            f"data_source '{data_source}' is not production-safe "
            f"(must be one of {sorted(REAL_DATA_SOURCES)})"
        )

    # Gate 3: confidence must be "high"
    confidence = candidate["confidence"]
    if confidence != "high":
        reasons.append(
            f"confidence '{confidence}' is not 'high' — "
            "only high-confidence evidence is approved for production"
        )

    # Gate 4: score must meet the minimum threshold
    overall_score = candidate["overall_score"]
    if not isinstance(overall_score, (int, float)):
        reasons.append(f"overall_score is not numeric: {overall_score!r}")
    elif overall_score < min_score:
        reasons.append(
            f"overall_score {overall_score} is below minimum threshold {min_score}"
        )

    # Gate 5: topic must not already be in publishing_history
    if published_topics and candidate.get("topic"):
        t_norm = candidate["topic"].strip().lower()
        if t_norm in published_topics:
            reasons.append(f"Topic '{candidate['topic']}' was already published in publishing_history.json")

    if reasons:
        return False, reasons
    return True, []


def validate_candidates(
    candidates: list,
    min_score: int = 60,
    history_file: str | Path = "data/publishing_history.json",
) -> tuple:
    """
    Validates a list of research candidates.

    Returns
    -------
    (valid_list, rejected_list)

    Each item in rejected_list is:
        {"topic": str, "reasons": [str, ...], "original": dict}
    """
    if not isinstance(candidates, list):
        return [], [{"topic": "<invalid input>", "reasons": ["Input is not a list"], "original": candidates}]

    published_topics = _load_published_topics(history_file)
    valid = []
    rejected = []

    for i, c in enumerate(candidates):
        ok, reasons = validate_candidate(c, min_score=min_score, published_topics=published_topics)
        if ok:
            valid.append(c)
        else:
            rejected.append({
                "topic":    c.get("topic", f"<candidate[{i}]>") if isinstance(c, dict) else f"<candidate[{i}]>",
                "reasons":  reasons,
                "original": c,
            })

    return valid, rejected
