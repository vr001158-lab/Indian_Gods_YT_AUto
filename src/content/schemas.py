# src/content/schemas.py
# Phase 2C — Content Brief and Decision Input schemas

# ── Expected fields in the incoming decision JSON ─────────────────────────────
REQUIRED_DECISION_FIELDS = (
    "approved_for_generation",
    "selected_topic",
    "score",
    "confidence",
    "data_source",
    "category",
    "suggested_angle",
    "content_gap",
)

# ── Expected fields in the generated content brief JSON ───────────────────────
REQUIRED_BRIEF_FIELDS = (
    "title_options",
    "primary_title",
    "hook",
    "audience",
    "story_arc",
    "script_structure",
    "visual_plan",
    "voice_direction",
    "shorts_hooks",
    "seo_metadata",
)


def validate_decision_input(decision: dict) -> tuple:
    """
    Ensures the incoming decision candidate is production-safe.
    Rejects mock/offline data, low-confidence entries, and unapproved topics.
    """
    if not isinstance(decision, dict):
        return False, "Input decision is not a dictionary"

    # 1. Structural check
    for field in REQUIRED_DECISION_FIELDS:
        if field not in decision:
            return False, f"Missing required decision field: '{field}'"
        if decision[field] is None and field != "selected_topic":
            return False, f"Decision field '{field}' cannot be null"

    # 2. Safety gates
    if not decision["approved_for_generation"]:
        return False, "Decision is not approved for generation (approved_for_generation must be True)"

    if decision["data_source"] not in ("youtube_api", "cached_youtube_api"):
        return False, f"Ineligible data_source: '{decision['data_source']}' (must be real API data)"

    if decision["confidence"] != "high":
        return False, f"Ineligible confidence level: '{decision['confidence']}' (must be high)"

    if not decision["selected_topic"]:
        return False, "selected_topic is empty or null"

    return True, ""


def validate_brief_output(brief: dict) -> tuple:
    """
    Ensures the generated content brief strictly conforms to the target schema.
    """
    if not isinstance(brief, dict):
        return False, "Brief is not a dictionary"

    for field in REQUIRED_BRIEF_FIELDS:
        if field not in brief:
            return False, f"Missing required brief field: '{field}'"
        if brief[field] is None:
            return False, f"Brief field '{field}' cannot be null"

    # Validate lists
    if not isinstance(brief["title_options"], list) or len(brief["title_options"]) != 5:
        return False, "title_options must be a list of exactly 5 options"

    if not isinstance(brief["story_arc"], list) or len(brief["story_arc"]) == 0:
        return False, "story_arc must be a non-empty list"

    if not isinstance(brief["visual_plan"], list) or len(brief["visual_plan"]) == 0:
        return False, "visual_plan must be a non-empty list"

    if not isinstance(brief["shorts_hooks"], list) or len(brief["shorts_hooks"]) == 0:
        return False, "shorts_hooks must be a non-empty list"

    # Validate nested dicts
    if not isinstance(brief["script_structure"], dict):
        return False, "script_structure must be a dictionary"

    if not isinstance(brief["voice_direction"], dict):
        return False, "voice_direction must be a dictionary"

    if not isinstance(brief["seo_metadata"], dict):
        return False, "seo_metadata must be a dictionary"

    # Verify visual scene details
    for i, scene in enumerate(brief["visual_plan"]):
        for key in ("scene_number", "duration_seconds", "description", "image_prompt", "video_prompt"):
            if key not in scene:
                return False, f"Visual scene {i+1} is missing key: '{key}'"

    # Verify SEO details
    for key in ("description", "keywords", "hashtags", "category"):
        if key not in brief["seo_metadata"]:
            return False, f"seo_metadata is missing key: '{key}'"

    # Verify voice direction details
    for key in ("tone", "speed", "emotion", "language_style"):
        if key not in brief["voice_direction"]:
            return False, f"voice_direction is missing key: '{key}'"

    return True, ""
