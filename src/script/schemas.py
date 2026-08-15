# src/script/schemas.py
# Phase 2D — Content Brief Input and Script Output schemas
#
# Phase 2G+: validate_script_output() is now content_type-aware.
#   - content_type="short"  → shorts_scripts required (original behaviour)
#   - content_type="long"   → shorts_scripts NOT required;
#                             long_form_metadata validated if present

# ── Required fields in the incoming content brief JSON ────────────────────────
REQUIRED_BRIEF_FIELDS = (
    "title_options",
    "primary_title",
    "hook",
    "story_arc",
    "script_structure",
    "visual_plan",
    "voice_direction",
    "shorts_hooks",
    "seo_metadata",
    "approval_metadata",
)

# ── Required fields in the generated Script JSON (both formats) ───────────────
REQUIRED_SCRIPT_FIELDS_COMMON = (
    "title",
    "duration_seconds",
    "narration",
    "scene_scripts",
    "retention_hooks",
)

# shorts_scripts is only required for content_type="short"
REQUIRED_SCRIPT_FIELDS_SHORT = REQUIRED_SCRIPT_FIELDS_COMMON + ("shorts_scripts",)

# Legacy alias: keeps import-level references working
REQUIRED_SCRIPT_FIELDS = REQUIRED_SCRIPT_FIELDS_SHORT


def validate_brief_input(brief: dict) -> tuple:
    """
    Enforces that the content brief is structurally sound and carries valid
    approval metadata (production-safety gates).
    """
    if not isinstance(brief, dict):
        return False, "Input brief is not a dictionary"

    # 1. Structural check
    for field in REQUIRED_BRIEF_FIELDS:
        if field not in brief:
            return False, f"Missing required brief field: '{field}'"
        if brief[field] is None:
            return False, f"Brief field '{field}' cannot be null"

    # 2. Safety Gate: Approval metadata verification
    meta = brief.get("approval_metadata")
    if not isinstance(meta, dict):
        return False, "approval_metadata is missing or not a dictionary"

    required_meta = ("approved_for_generation", "data_source", "confidence", "selected_topic")
    for key in required_meta:
        if key not in meta:
            return False, f"Missing approval metadata key: '{key}'"

    if not meta["approved_for_generation"]:
        return False, "approved_for_generation must be True in approval_metadata"

    if meta["data_source"] not in ("youtube_api", "cached_youtube_api"):
        return False, f"Ineligible data_source '{meta['data_source']}' (must be real YouTube API data)"

    if meta["confidence"] != "high":
        return False, f"Ineligible evidence confidence level: '{meta['confidence']}'"

    if not meta["selected_topic"]:
        return False, "selected_topic is missing in approval_metadata"

    return True, ""


def validate_script_output(script: dict, content_type: str = "short") -> tuple:
    """
    Validates that the generated script strictly adheres to the requested output format.

    Parameters
    ----------
    script : dict
        The script JSON produced by the script generator.
    content_type : str
        "short" (default) — requires shorts_scripts.
        "long"            — shorts_scripts is NOT required;
                           long_form_metadata is validated if present.
    """
    if not isinstance(script, dict):
        return False, "Script is not a dictionary"

    ct = (content_type or "short").lower().strip()
    if ct not in ("short", "long"):
        return False, f"content_type must be 'short' or 'long', got '{content_type}'"

    # ── Common required fields (both formats) ──────────────────────────────
    for field in REQUIRED_SCRIPT_FIELDS_COMMON:
        if field not in script:
            return False, f"Missing required script field: '{field}'"
        if script[field] is None:
            return False, f"Script field '{field}' cannot be null"

    # Validate types and nested contents
    if not isinstance(script["title"], str) or not script["title"]:
        return False, "title must be a non-empty string"

    if not isinstance(script["duration_seconds"], int) or script["duration_seconds"] <= 0:
        return False, "duration_seconds must be a positive integer"

    if not isinstance(script["narration"], str) or not script["narration"]:
        return False, "narration must be a non-empty string"

    if not isinstance(script["retention_hooks"], list):
        return False, "retention_hooks must be a list"

    if not isinstance(script["scene_scripts"], list) or len(script["scene_scripts"]) == 0:
        return False, "scene_scripts must be a non-empty list of scene scripts"

    # ── Validate individual scenes ─────────────────────────────────────────
    for i, scene in enumerate(script["scene_scripts"]):
        for key in ("scene", "duration_seconds", "visual_reference", "voice_text", "emotion"):
            if key not in scene:
                return False, f"Scene {i+1} is missing key: '{key}'"
            if scene[key] is None:
                return False, f"Scene {i+1} key '{key}' cannot be null"
        if not isinstance(scene["scene"], int) or scene["scene"] != i + 1:
            return False, f"Scene {i+1} 'scene' index must be {i + 1}"
        if not isinstance(scene["duration_seconds"], int) or scene["duration_seconds"] <= 0:
            return False, f"Scene {i+1} 'duration_seconds' must be a positive integer"

    # ── SHORT-specific: shorts_scripts required ────────────────────────────
    if ct == "short":
        if "shorts_scripts" not in script or script["shorts_scripts"] is None:
            return False, "shorts_scripts is required for content_type='short'"
        if not isinstance(script["shorts_scripts"], list) or len(script["shorts_scripts"]) == 0:
            return False, "shorts_scripts must be a non-empty list of shorts scripts"

        for i, short in enumerate(script["shorts_scripts"]):
            if not isinstance(short, dict):
                return False, f"Shorts script {i+1} must be a dictionary"
            for key in ("title", "hook", "body"):
                if key not in short:
                    return False, f"Shorts script {i+1} is missing key: '{key}'"
                if not isinstance(short[key], str) or not short[key]:
                    return False, f"Shorts script {i+1} key '{key}' must be a non-empty string"

    # ── LONG-specific: long_form_metadata validated if present ────────────
    elif ct == "long":
        lfm = script.get("long_form_metadata")
        if lfm is not None:
            if not isinstance(lfm, dict):
                return False, "long_form_metadata must be a dictionary when present"
            # Optional sub-field validation (non-fatal if absent)
            for key in ("chapters", "target_audience"):
                val = lfm.get(key)
                if val is not None and not isinstance(val, (list, str)):
                    return False, f"long_form_metadata.{key} has unexpected type"

    return True, ""
