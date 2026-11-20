# src/decision/report.py
# Phase 2B.1 — Decision engine: orchestrates validation → selection → output.

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from src.decision.validator import validate_candidates
from src.decision.selector  import select_topic
from src.decision.strategy  import apply_old_format_topic_preferences, apply_content_intelligence_preferences
from src.decision.weekday_deity import (
    select_weekday_deity,
    DEITY_CANONICAL_ALIASES,
    NoApprovedWeekdayDeityAssetsError,
    get_weekday_info,
    get_current_kolkata_datetime,
)

OUTPUT_DIR = Path("data/decision")


def save_decision_report(decision: dict) -> Path | None:
    """Persists decision dictionary to a timestamped JSON file in OUTPUT_DIR."""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUTPUT_DIR / f"decision_{timestamp}.json"
    try:
        out_file.write_text(
            json.dumps(decision, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        print(f"\n📂 Decision saved → {out_file}", file=sys.stderr)
        return out_file
    except Exception as e:
        print(f"⚠️  Warning: Failed to save decision: {e}", file=sys.stderr)
        return None


def _build_selection_reason(candidate: dict, ranked: list) -> str:
    """Produces a human-readable explanation for why this topic was chosen."""
    rank_pos = ranked.index(candidate) + 1 if candidate in ranked else 1
    total    = len(ranked)
    base_reason = (
        f"Ranked #{rank_pos} of {total} validated real-data candidates. "
        f"Score: {candidate['overall_score']}/100, "
        f"Demand: {candidate['demand_score']}, "
        f"Freshness: {candidate['freshness_score']}, "
        f"Confidence: {candidate['confidence']}, "
        f"Source: {candidate['data_source']}."
    )
    if "intelligence_factors" in candidate:
        factors = candidate["intelligence_factors"]
        deity = factors.get("resolved_deity", "unknown")
        fatigue = factors.get("fatigue_penalty", 0.0)
        cal = factors.get("calendar_bonus", 0.0)
        ser = factors.get("series_bonus", 0.0)
        src_bonus = factors.get("source_bonus", 0.0)
        citation = factors.get("source_citation", "")
        base_reason += (
            f" [Intelligence: Deity={deity}, FatiguePenalty={fatigue}, "
            f"CalendarBonus={cal}, SeriesBonus={ser}, SourceBonus={src_bonus}"
            + (f", Citation='{citation}'" if citation else "")
            + "]"
        )
    return base_reason


def run_decision_pipeline(
    candidates: list,
    min_score:  int = 60,
    save:       bool = True,
    format:     str = "narrated",
    language_code: str | None = None,
) -> dict:
    """
    Runs the full decision pipeline on a list of research candidates.

    Parameters
    ----------
    candidates : list  — raw list loaded from a research_results_*.json
    min_score  : int   — minimum overall_score required (default 60)
    save       : bool  — if True, writes decision JSON to data/decision/
    format     : str   — content format ('narrated' or 'old')
    language_code: str | None — 'hi-IN' or 'te-IN'

    Returns
    -------
    Decision dict matching the documented output schema.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    # ── 1. Validate ───────────────────────────────────────────────────────────
    valid, rejected = validate_candidates(candidates, min_score=min_score)

    # ── 2. Select with Weekday Deity Constraint ──────────────────────────────
    if (format or "").lower() == "old":
        candidates_to_select = apply_old_format_topic_preferences(valid)
    elif language_code:
        candidates_to_select = apply_content_intelligence_preferences(valid, language_code=language_code)
    else:
        candidates_to_select = valid

    from src.decision.weekday_deity import (
        select_weekday_deity,
        DEITY_CANONICAL_ALIASES,
        NoApprovedWeekdayDeityAssetsError,
        get_weekday_info,
        get_current_kolkata_datetime,
    )
    try:
        weekday_context = select_weekday_deity()
    except NoApprovedWeekdayDeityAssetsError as exc:
        now_dt = get_current_kolkata_datetime()
        day_info = get_weekday_info(now_dt)
        weekday_context = {
            "weekday_index": now_dt.weekday(),
            "english_day": day_info["english_day"],
            "sanskrit_day": day_info["sanskrit_day"],
            "scheduled_deity": None,
            "display_name": None,
            "repository_folder": None,
            "eligible_deities": list(day_info["primary_deities"]),
            "available_deities": [],
            "unavailable_deities": list(day_info["primary_deities"]),
            "generation_skipped": True,
            "skip_reason": str(exc),
            "significance": list(day_info["significance"]),
            "visual_and_offering_context": dict(day_info["visual_and_offering_context"]),
            "kolkata_date": now_dt.strftime("%Y-%m-%d"),
        }
        decision = {
            "approved_for_generation": False,
            "format": (format or "narrated").lower(),
            "language_code": language_code,
            "selected_topic": None,
            "score": None,
            "confidence": None,
            "data_source": None,
            "category": None,
            "deity": None,
            "suggested_angle": None,
            "content_gap": None,
            "selection_reason": f"Generation skipped: {exc}",
            "reason": f"Generation skipped: {exc}",
            "intelligence_factors": None,
            "weekday_deity_context": weekday_context,
            "rejected_candidates": [{"topic": r["topic"], "reasons": r["reasons"]} for r in rejected],
            "dedup_removed_topics": [],
            "total_input_candidates": len(candidates),
            "total_valid_candidates": len(valid),
            "total_rejected_candidates": len(rejected),
            "min_score_threshold": min_score,
            "selected_at": now_iso,
        }
        if save:
            save_decision_report(decision)
        return decision

    scheduled_deity = weekday_context["scheduled_deity"].lower()
    eligible_deities = [d.lower() for d in weekday_context.get("available_deities", weekday_context["eligible_deities"])]

    from src.assets.selector import resolve_deity
    scheduled_pool = []
    eligible_pool = []
    for c in candidates_to_select:
        cand_hint = (c.get("deity") or "").strip().lower()
        d_key = resolve_deity(c.get("topic", ""), deity_hint=cand_hint, default=cand_hint or "unknown").lower()
        canon_d_key = DEITY_CANONICAL_ALIASES.get(d_key, d_key)
        canon_hint = DEITY_CANONICAL_ALIASES.get(cand_hint, cand_hint)

        matched_deities = {d_key, canon_d_key, cand_hint, canon_hint} - {"", "unknown"}

        if scheduled_deity in matched_deities:
            scheduled_pool.append(c)
        elif any(e in matched_deities for e in eligible_deities):
            eligible_pool.append(c)

    controlled_exception_applied = False
    exception_reason = None

    if scheduled_pool:
        # Primary constraint: Scheduled deity of the day wins
        result = select_topic(scheduled_pool)
    elif eligible_pool:
        # Secondary constraint: Eligible deities of the weekday win
        result = select_topic(eligible_pool)
    else:
        # Controlled Exception: When research pool has no candidates matching the day's deities
        controlled_exception_applied = True
        exception_reason = (
            f"Controlled Exception: No validated candidates available for scheduled deity "
            f"'{scheduled_deity}' or eligible deities {eligible_deities}."
        )
        result = select_topic(candidates_to_select)

    weekday_context["controlled_exception_applied"] = controlled_exception_applied
    weekday_context["exception_reason"] = exception_reason

    selected = result["selected"]
    ranked   = result["ranked"]
    dedup_removed = result["dedup_removed"]

    # ── 3. Build decision object ──────────────────────────────────────────────

    if selected is not None:
        decision = {
            "approved_for_generation": True,
            "format":           (format or "narrated").lower(),
            "language_code":    language_code,
            "selected_topic":   selected["topic"],
            "score":            selected["overall_score"],
            "confidence":       selected["confidence"],
            "data_source":      selected["data_source"],
            "category":         selected["category"],
            "deity":            selected.get("deity", ""),
            "suggested_angle":  selected["suggested_angle"],
            "content_gap":      selected["content_gap"],
            "selection_reason": _build_selection_reason(selected, ranked),
            "intelligence_factors": selected.get("intelligence_factors"),
            "weekday_deity_context": weekday_context,
            "rejected_candidates": [
                {"topic": r["topic"], "reasons": r["reasons"]}
                for r in rejected
            ],
            "dedup_removed_topics": [c["topic"] for c in dedup_removed],
            "total_input_candidates":   len(candidates),
            "total_valid_candidates":   len(valid),
            "total_rejected_candidates": len(rejected),
            "min_score_threshold": min_score,
            "selected_at": now_iso,
        }
    else:
        decision = {
            "approved_for_generation": False,
            "selected_topic": None,
            "score":          None,
            "confidence":     None,
            "data_source":    None,
            "category":       None,
            "deity":          None,
            "suggested_angle": None,
            "content_gap":     None,
            "selection_reason": None,
            "reason": "No research candidate passed production safety gates",
            "rejected_candidates": [
                {"topic": r["topic"], "reasons": r["reasons"]}
                for r in rejected
            ],
            "dedup_removed_topics": [c["topic"] for c in dedup_removed],
            "total_input_candidates":    len(candidates),
            "total_valid_candidates":    len(valid),
            "total_rejected_candidates": len(rejected),
            "min_score_threshold": min_score,
            "selected_at": now_iso,
        }

    # ── 4. Persist ────────────────────────────────────────────────────────────
    if save:
        save_decision_report(decision)

    return decision


def print_decision(decision: dict):
    """Prints the formatted decision report to stdout."""
    approved = decision["approved_for_generation"]
    total_in  = decision["total_input_candidates"]
    total_val = decision["total_valid_candidates"]
    total_rej = decision["total_rejected_candidates"]

    print("\n" + "=" * 50)
    print("🌅  DIVINE DHARSHANAM DAILY — TOPIC DECISION")
    print("=" * 50)
    print(f"\nResearch source:    {total_in} candidate(s) from research JSON")
    print(f"Candidates:         {total_in}")
    print(f"Valid candidates:   {total_val}  (real data, high confidence, score ≥ {decision['min_score_threshold']})")
    print(f"Rejected:           {total_rej}")

    if approved:
        print(f"\n{'─' * 50}")
        print(f"✅  SELECTED TOPIC: {decision['selected_topic']}")
        print(f"{'─' * 50}")
        print(f"\n   Score:       {decision['score']}/100")
        print(f"   Confidence:  {decision['confidence']}")
        print(f"   Data source: {decision['data_source']}")
        print(f"   Category:    {decision['category']}")
        print(f"\n   Suggested Angle:")
        print(f"   \"{decision['suggested_angle']}\"")
        print(f"\n   Content Gap:")
        print(f"   {decision['content_gap']}")
        print(f"\n   Reason:")
        print(f"   {decision['selection_reason']}")
    else:
        print(f"\n{'─' * 50}")
        print("❌  NO TOPIC SELECTED")
        print(f"{'─' * 50}")
        fail_reason = decision.get("reason") or decision.get("selection_reason") or "No research candidate passed production safety gates"
        print(f"\n   Reason: {fail_reason}")

    if decision["rejected_candidates"]:
        print(f"\n{'─' * 50}")
        print("   REJECTED CANDIDATES:")
        for r in decision["rejected_candidates"]:
            print(f"   • {r['topic']}")
            for reason in r["reasons"]:
                print(f"       – {reason}")

    print(f"\n{'=' * 50}")
    status = "✅  APPROVED FOR GENERATION: YES" if approved else "❌  APPROVED FOR GENERATION: NO"
    print(status)
    print("=" * 50)
