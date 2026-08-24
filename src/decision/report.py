# src/decision/report.py
# Phase 2B.1 — Decision engine: orchestrates validation → selection → output.

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from src.decision.validator import validate_candidates
from src.decision.selector  import select_topic
from src.decision.strategy  import apply_old_format_topic_preferences

OUTPUT_DIR = Path("data/decision")


def _build_selection_reason(candidate: dict, ranked: list) -> str:
    """Produces a human-readable explanation for why this topic was chosen."""
    rank_pos = ranked.index(candidate) + 1 if candidate in ranked else 1
    total    = len(ranked)
    return (
        f"Ranked #{rank_pos} of {total} validated real-data candidates. "
        f"Score: {candidate['overall_score']}/100, "
        f"Demand: {candidate['demand_score']}, "
        f"Freshness: {candidate['freshness_score']}, "
        f"Confidence: {candidate['confidence']}, "
        f"Source: {candidate['data_source']}."
    )


def run_decision_pipeline(
    candidates: list,
    min_score:  int = 60,
    save:       bool = True,
    format:     str = "narrated",
) -> dict:
    """
    Runs the full decision pipeline on a list of research candidates.

    Parameters
    ----------
    candidates : list  — raw list loaded from a research_results_*.json
    min_score  : int   — minimum overall_score required (default 60)
    save       : bool  — if True, writes decision JSON to data/decision/
    format     : str   — content format ('narrated' or 'old')

    Returns
    -------
    Decision dict matching the documented output schema.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    # ── 1. Validate ───────────────────────────────────────────────────────────
    valid, rejected = validate_candidates(candidates, min_score=min_score)

    # ── 2. Select ─────────────────────────────────────────────────────────────
    candidates_to_select = apply_old_format_topic_preferences(valid) if (format or "").lower() == "old" else valid
    result = select_topic(candidates_to_select)
    selected = result["selected"]
    ranked   = result["ranked"]
    dedup_removed = result["dedup_removed"]

    # ── 3. Build decision object ──────────────────────────────────────────────
    if selected is not None:
        decision = {
            "approved_for_generation": True,
            "format":           (format or "narrated").lower(),
            "selected_topic":   selected["topic"],
            "score":            selected["overall_score"],
            "confidence":       selected["confidence"],
            "data_source":      selected["data_source"],
            "category":         selected["category"],
            "deity":            selected.get("deity", ""),
            "suggested_angle":  selected["suggested_angle"],
            "content_gap":      selected["content_gap"],
            "selection_reason": _build_selection_reason(selected, ranked),
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
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        out_file = OUTPUT_DIR / f"decision_{timestamp}.json"
        try:
            out_file.write_text(
                json.dumps(decision, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            print(f"\n📂 Decision saved → {out_file}", file=sys.stderr)
        except Exception as e:
            print(f"⚠️  Warning: Failed to save decision: {e}", file=sys.stderr)

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
        print(f"\n   Reason: {decision['reason']}")

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
