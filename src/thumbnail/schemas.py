# src/thumbnail/schemas.py
# Phase 2H — Thumbnail input and output validation schemas

REQUIRED_DECISION_KEYS = (
    "approved_for_generation",
    "selected_topic",
    "score",
    "confidence",
    "data_source",
)

REQUIRED_METADATA_KEYS = (
    "title",
    "topic",
    "provider",
    "resolution",
    "format",
    "approved_source",
    "confidence",
    "created_at",
    "approval_metadata",
)


def validate_decision_input(decision: dict) -> tuple:
    """
    Validates the safety and completeness of the decision input.
    Fails closed on missing fields, low confidence, or mock/offline data.
    """
    if not isinstance(decision, dict):
        return False, "Input decision must be a dictionary"

    for key in REQUIRED_DECISION_KEYS:
        if key not in decision:
            return False, f"Missing required decision key: '{key}'"
        if decision[key] is None:
            return False, f"Decision key '{key}' cannot be null"

    # Safety checks
    if not decision["approved_for_generation"]:
        return False, "approved_for_generation must be True in decision"

    if decision["data_source"] not in ("youtube_api", "cached_youtube_api"):
        return False, f"Ineligible data_source '{decision['data_source']}' (must be real YouTube API data)"

    if decision["confidence"] != "high":
        return False, f"Ineligible evidence confidence level: '{decision['confidence']}'"

    if not isinstance(decision["selected_topic"], str) or not decision["selected_topic"].strip():
        return False, "selected_topic must be a non-empty string"

    return True, ""


def validate_metadata_output(meta: dict) -> tuple:
    """
    Validates that the thumbnail metadata schema conforms to requested specifications.
    """
    if not isinstance(meta, dict):
        return False, "Metadata must be a dictionary"

    for key in REQUIRED_METADATA_KEYS:
        if key not in meta:
            return False, f"Missing required metadata key: '{key}'"
        if meta[key] is None:
            return False, f"Metadata key '{key}' cannot be null"

    if meta["resolution"] != "1280x720":
        return False, f"Invalid resolution: expected '1280x720', got '{meta['resolution']}'"

    if meta["format"].lower() != "png":
        return False, f"Invalid format: expected 'png', got '{meta['format']}'"

    if not meta["title"] or not isinstance(meta["title"], str):
        return False, "title must be a non-empty string"

    if not meta["topic"] or not isinstance(meta["topic"], str):
        return False, "topic must be a non-empty string"

    meta_app = meta.get("approval_metadata")
    if not isinstance(meta_app, dict):
        return False, "approval_metadata is missing or not a dictionary"

    required_meta = ("approved_for_generation", "data_source", "confidence", "selected_topic")
    for key in required_meta:
        if key not in meta_app:
            return False, f"Missing approval metadata key: '{key}'"

    if not meta_app["approved_for_generation"]:
        return False, "approved_for_generation must be True in approval_metadata"

    if meta_app["data_source"] not in ("youtube_api", "cached_youtube_api"):
        return False, f"Ineligible data_source '{meta_app['data_source']}' (must be real YouTube API data)"

    if meta_app["confidence"] != "high":
        return False, f"Ineligible evidence confidence level: '{meta_app['confidence']}'"

    return True, ""
