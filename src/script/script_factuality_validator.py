# src/script/script_factuality_validator.py
# Phase 2 — Shastric Factuality & Thematic Integrity Validator
# Validates script against canonical scriptures, preventing deity attribute bleeding,
# chronological contradictions, weapon/vahana errors, and fake scriptural claims.

from __future__ import annotations

import re
from typing import Any

from src.assets.selector import resolve_deity
from src.research.scriptural_source_registry import (
    CANONICAL_DEITY_RULES,
    check_chronology_compatibility,
    get_scripture_reference_for_topic,
    verify_scriptural_claim,
)


class ScriptFactualityValidationError(Exception):
    """Raised when a script fails critical factuality verification."""


def validate_script_factuality(
    script_data: dict[str, Any],
    canonical_topic: str | None = None,
    deity_hint: str | None = None,
) -> tuple[bool, list[str], dict[str, Any]]:
    """
    Validates the factual correctness of a devotional script.

    Checks:
      1. Deity Resolution & Consistency between topic and narration
      2. Weapon / Divine Item canon compliance
      3. Vahana (Mount/Vehicle) canon compliance
      4. Consort & Family Relationship accuracy
      5. Episode Attribution (no wrong deity performing other's divine feats)
      6. Chronological Yuga contradiction check
      7. Non-existent / fabricated scripture citations

    Returns:
        (is_valid: bool, violations: list[str], report: dict)
    """
    violations: list[str] = []
    warnings: list[str] = []

    title = script_data.get("title", "")
    narration = script_data.get("narration", "")
    scene_scripts = script_data.get("scene_scripts", [])
    combined_voice = " ".join([s.get("voice_text", "") for s in scene_scripts])
    full_text = f"{title} {narration} {combined_voice}".strip()

    # 1. Resolve canonical deity
    topic_to_check = canonical_topic or title
    resolved_deity = resolve_deity(topic_to_check, deity_hint=deity_hint, default="unknown")
    text_deity = resolve_deity(full_text, deity_hint="", default=None)

    # 2. Check for Cross-Deity Contradiction (e.g. topic is Rama, but script is entirely about Shiva)
    if resolved_deity != "unknown" and text_deity and text_deity != "unknown":
        if resolved_deity != text_deity:
            # Check if this is an allowed cross-deity interaction (e.g. Shiva drinking poison during Kurma/Samudra Manthan)
            allowed_interactions = {
                ("kurma", "lord_shiva"),
                ("lord_vishnu", "lord_shiva"),
                ("lord_shiva", "ganesha"),
                ("lord_shiva", "parvathi"),
                ("ram", "hanuman"),
                ("krishna", "lord_vishnu"),
            }
            pair = (resolved_deity, text_deity)
            reverse_pair = (text_deity, resolved_deity)
            if pair not in allowed_interactions and reverse_pair not in allowed_interactions:
                violations.append(
                    f"Deity divergence detected: Canonical topic resolved to '{resolved_deity}', "
                    f"but script text predominantly reflects '{text_deity}'."
                )

    # 3. Canonical Attribute, Weapon, Vahana, Consort & Episode checks
    is_claim_valid, claim_violations = verify_scriptural_claim(
        topic=topic_to_check,
        deity_key=resolved_deity,
        text_to_verify=full_text,
    )
    if not is_claim_valid:
        violations.extend(claim_violations)

    # 4. Yuga & Chronology check
    # Check if multiple avatars are mentioned as contemporary peers without shastric basis
    avatars_found = []
    text_lower = full_text.lower()
    avatar_keys = ["matsya", "kurma", "varaha", "narasimha", "vamana", "parashurama", "ram", "krishna"]
    for av in avatar_keys:
        if av in text_lower or (av == "ram" and ("rama" in text_lower or "రాముడు" in full_text)):
            avatars_found.append(av)

    if len(avatars_found) >= 2:
        for i in range(len(avatars_found)):
            for j in range(i + 1, len(avatars_found)):
                compat, reason = check_chronology_compatibility(avatars_found[i], avatars_found[j])
                if not compat:
                    # If mentioned in comparative avatar listing (Dashavatara), it's permitted
                    if not any(w in text_lower for w in ["dashavatar", "avatars", "అవతారాలు", "దశావతార"]):
                        violations.append(f"Chronology conflict between {avatars_found[i]} and {avatars_found[j]}: {reason}")

    # 5. Scripture Reference lookup
    scripture_ref = get_scripture_reference_for_topic(topic_to_check, deity=resolved_deity)
    scripture_info = None
    if scripture_ref:
        scripture_info = {
            "text": scripture_ref.text_name,
            "division": scripture_ref.division,
            "telugu_title": scripture_ref.telugu_title,
            "tier": scripture_ref.source_tier,
        }
    else:
        warnings.append("Topic not registered in canonical scripture database; relying on general shastric heuristics.")

    is_valid = len(violations) == 0
    report = {
        "is_valid": is_valid,
        "resolved_deity": resolved_deity,
        "violations": violations,
        "warnings": warnings,
        "scripture_reference": scripture_info,
        "total_violations": len(violations),
    }

    return is_valid, violations, report
