# src/script/script_qa_gate.py
# Phase 2 — Unified Pre-Voice Script QA Gate
# Enforces mandatory, fail-closed validation between Script Generation and Voice Synthesis:
# Execution Order:
#   1. Script Structure & Integrity Validation
#   2. Scriptural Factuality Verification (no attribute bleeding, chronology errors)
#   3. Telugu Linguistic Quality Evaluation (reverence, Indic ratio >= 60%, vocabulary)
#   4. Retention Structure Evaluation (curiosity gap, narrative progression, hooks, payoff)
#   5. Aggregate QA Verdict & Structured Reporting
#   6. Enforce Gate: Only Approved Scripts May Reach Voice Generation.

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from src.script.schemas import validate_script_output
from src.script.script_factuality_validator import validate_script_factuality
from src.script.script_quality_evaluator import evaluate_script_quality
from src.script.script_retention_optimizer import evaluate_script_retention


class ScriptQAError(Exception):
    """Base error raised when a devotional script fails Pre-Voice QA."""


class ScriptFactualityError(ScriptQAError):
    """Raised when a script fails scriptural factuality validation."""


class ScriptQualityError(ScriptQAError):
    """Raised when a script fails linguistic quality or devotional reverence evaluation."""


class ScriptStructureError(ScriptQAError):
    """Raised when a script contains empty narration or invalid structural parameters."""


def compute_script_content_hash(script_data: dict[str, Any]) -> str:
    """Computes a deterministic SHA-256 fingerprint of the script's spoken text and structure."""
    title = (script_data.get("title") or "").strip()
    narration = (script_data.get("narration") or "").strip()
    scenes = script_data.get("scene_scripts") or []
    scene_texts = [str(s.get("voice_text") or "").strip() for s in scenes]
    lang = script_data.get("language_code") or ""
    fmt = script_data.get("format") or ""

    raw = f"{title}|{narration}|{'#'.join(scene_texts)}|{lang}|{fmt}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def run_pre_voice_script_qa(
    script_data: dict[str, Any],
    canonical_topic: str | None = None,
    deity_hint: str | None = None,
    language_code: str = "te-IN",
    content_type: str = "short",
    fail_fast: bool = False,
) -> tuple[bool, dict[str, Any], list[str]]:
    """
    Executes the full Pre-Voice Script QA pipeline.

    Guarantees:
      - Factuality failure blocks approval.
      - Invalid Telugu / non-Indic output blocks approval.
      - Empty or truncated narration blocks approval.
      - Title-topic mismatch blocks approval.
      - Retention warnings are distinguished from critical blocking failures.
      - Prevents duplicate execution if the exact same script content was already verified.

    Returns:
        (approved: bool, qa_report: dict, critical_errors: list[str])
    """
    # ── Check for previous approval (Idempotency / Prevent Duplicate Run) ─────
    content_hash = compute_script_content_hash(script_data)
    existing_report = script_data.get("qa_report")
    if (
        isinstance(existing_report, dict)
        and existing_report.get("approved") is True
        and existing_report.get("content_hash") == content_hash
    ):
        return True, existing_report, []

    critical_errors: list[str] = []
    advisory_warnings: list[str] = []

    # 1. Structure & Basic Schema Validation
    title = (script_data.get("title") or "").strip()
    narration = (script_data.get("narration") or "").strip()
    scene_scripts = script_data.get("scene_scripts") or []
    is_old_format = script_data.get("format") == "old"

    if not title:
        critical_errors.append("Script title is empty.")
    if not narration:
        critical_errors.append("Script narration is empty.")
    if not scene_scripts:
        critical_errors.append("Script scene_scripts list is empty.")

    for i, sc in enumerate(scene_scripts, 1):
        dur = sc.get("duration_seconds", 0)
        vt = (sc.get("voice_text") or "").strip()
        if dur <= 0:
            critical_errors.append(f"Scene #{i} has non-positive duration ({dur}s).")
        if not is_old_format and not vt:
            critical_errors.append(f"Scene #{i} has empty voice_text narration.")
        elif not is_old_format and vt:
            from src.content.telugu_blueprints import validate_spoken_narration
            ok_narr, leak_reasons = validate_spoken_narration(vt)
            if not ok_narr:
                critical_errors.append(f"Scene #{i} narration contains leaked prompt metadata: {leak_reasons}")

    ok_schema, schema_err = validate_script_output(script_data, content_type=content_type)
    if not ok_schema:
        critical_errors.append(f"Schema validation failure: {schema_err}")

    # 2. Title-Topic Semantic Alignment (Early Safety Gate)
    topic_to_check = canonical_topic
    if not topic_to_check:
        meta = script_data.get("approval_metadata") or {}
        topic_to_check = meta.get("selected_topic")

    from src.script.generator import check_title_topic_semantic_alignment, validate_script_language_integrity

    if topic_to_check and title:
        aligned, align_reason = check_title_topic_semantic_alignment(
            canonical_topic=topic_to_check,
            script_title=title,
            deity_hint=deity_hint or "",
        )
        if not aligned:
            critical_errors.append(f"Title-Topic Semantic Alignment Mismatch: {align_reason}")

    # 3. Language & Script Integrity
    target_lang = script_data.get("language_code") or language_code
    if target_lang in ("te-IN", "hi-IN"):
        ok_lang, lang_err = validate_script_language_integrity(script_data, target_lang)
        if not ok_lang:
            critical_errors.append(f"Language integrity failure: {lang_err}")

    # 4. Scriptural Factuality Verification
    is_fact_valid, fact_violations, fact_report = validate_script_factuality(
        script_data=script_data,
        canonical_topic=topic_to_check,
        deity_hint=deity_hint,
    )
    if not is_fact_valid:
        critical_errors.extend([f"Factuality violation: {v}" for v in fact_violations])
    advisory_warnings.extend(fact_report.get("warnings", []))

    # 5. Telugu Linguistic Quality Evaluation
    is_qual_valid, quality_score, qual_metrics, qual_recs = evaluate_script_quality(
        script_data=script_data,
        language_code=target_lang,
        content_type=content_type,
    )
    if not is_qual_valid:
        for flaw in qual_metrics.get("flaws", []):
            critical_errors.append(f"Linguistic quality flaw: {flaw}")
    advisory_warnings.extend(qual_recs)

    # 6. Retention Structure Evaluation
    is_ret_opt, ret_score, ret_suggestions = evaluate_script_retention(script_data)
    advisory_warnings.extend([f"Retention note: {s}" for s in ret_suggestions])

    # 7. Aggregate QA Report
    approved = len(critical_errors) == 0

    qa_report: dict[str, Any] = {
        "approved": approved,
        "content_hash": content_hash,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "stage": "PRE_VOICE_SCRIPT_QA",
        "language_code": target_lang,
        "content_type": content_type,
        "critical_errors": critical_errors,
        "warnings": advisory_warnings,
        "scores": {
            "quality_score": quality_score,
            "retention_score": ret_score,
            "factuality_valid": is_fact_valid,
        },
        "checks": {
            "structure": {
                "passed": len([e for e in critical_errors if "empty" in e or "duration" in e or "Schema" in e]) == 0,
            },
            "alignment": {
                "passed": len([e for e in critical_errors if "Title-Topic" in e]) == 0,
            },
            "language_integrity": {
                "passed": len([e for e in critical_errors if "Language integrity" in e]) == 0,
            },
            "factuality": fact_report,
            "quality": {
                "score": quality_score,
                "metrics": qual_metrics,
            },
            "retention": {
                "score": ret_score,
                "is_optimized": is_ret_opt,
                "suggestions": ret_suggestions,
            },
        },
    }

    # Attach qa_report to the script structure
    script_data["qa_report"] = qa_report

    if not approved and fail_fast:
        raise ScriptQAError(
            f"❌ Pre-Voice Script QA REJECTION: Script failed verification with {len(critical_errors)} critical error(s):\n"
            + "\n".join(f"  - {err}" for err in critical_errors)
        )

    return approved, qa_report, critical_errors
