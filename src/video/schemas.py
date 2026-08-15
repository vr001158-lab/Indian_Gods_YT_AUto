# src/video/schemas.py
# Phase 2G/Phase 4 — Video Composer Input and Output schemas
#
# Resolution constants are now sourced from format_config so there is
# exactly one definition across the whole codebase.

from src.video.format_config import (
    ALL_ALLOWED_RESOLUTIONS,
    validate_content_type,
    validate_resolution_for_content_type,
)

# Kept for backwards-compatibility with any direct import
ALLOWED_RESOLUTIONS = ALL_ALLOWED_RESOLUTIONS


def validate_input_maps(audio_map: dict, visual_map: dict) -> tuple:
    """
    Enforces safety checks on the timing maps.
    Rejects mock data, unapproved content, and mismatched parameters.
    """
    if not isinstance(audio_map, dict) or not isinstance(visual_map, dict):
        return False, "Inputs must be dictionaries"

    # 1. Run ID alignment check (if present)
    run_a = audio_map.get("run_id")
    run_v = visual_map.get("run_id")
    if run_a and run_v and run_a != run_v:
        return False, f"Mismatched run_id in timing maps: '{run_a}' vs '{run_v}'"

    # 2. Title alignment check
    title_a = audio_map.get("script_title")
    title_v = visual_map.get("script_title")
    if not title_a or not title_v or title_a != title_v:
        return False, f"Mismatched script titles: '{title_a}' vs '{title_v}'"

    # 3. Scene alignment check
    scenes_a = audio_map.get("audio_scenes", [])
    scenes_v = visual_map.get("visual_scenes", [])
    if len(scenes_a) != len(scenes_v):
        return False, f"Mismatched scene counts: audio has {len(scenes_a)} vs visual {len(scenes_v)}"

    # 4. Safety Gate: approval metadata verification
    meta_a = audio_map.get("approval_metadata")
    meta_v = visual_map.get("approval_metadata")
    if not isinstance(meta_a, dict) or not isinstance(meta_v, dict):
        return False, "approval_metadata is missing in timing maps"

    if meta_a.get("selected_topic") != meta_v.get("selected_topic"):
        return False, f"Mismatched selected_topic in approval_metadata: '{meta_a.get('selected_topic')}' vs '{meta_v.get('selected_topic')}'"

    for meta in (meta_a, meta_v):
        required_keys = ("approved_for_generation", "data_source", "confidence", "selected_topic")
        for key in required_keys:
            if key not in meta:
                return False, f"Missing approval metadata key: '{key}'"

        if not meta["approved_for_generation"]:
            return False, "Topic is not approved for generation in approval_metadata"

        if meta["data_source"] not in ("youtube_api", "cached_youtube_api"):
            return False, f"Ineligible data_source '{meta['data_source']}' (must be real YouTube API data)"

        if meta["confidence"] != "high":
            return False, f"Ineligible evidence confidence level: '{meta['confidence']}'"

        if not meta.get("selected_topic"):
            return False, "selected_topic is missing or empty in approval_metadata"

    return True, ""


def validate_output_video_map(vmap: dict) -> tuple:
    """
    Validates that the output video mapping JSON matches the schema.

    Now requires:
      - content_type  (must be a known format)
      - aspect_ratio
      - resolution    (must match the declared content_type)
    """
    if not isinstance(vmap, dict):
        return False, "Output map is not a dictionary"

    required_fields = (
        "video_file", "video_map_file", "total_duration",
        "resolution", "scenes", "content_type", "aspect_ratio",
    )
    for f in required_fields:
        if f not in vmap:
            return False, f"Missing required output field: '{f}'"
        if vmap[f] is None:
            return False, f"Field '{f}' cannot be null"

    if not isinstance(vmap["video_file"], str) or not vmap["video_file"].endswith(".mp4"):
        return False, "video_file must be a string path ending in .mp4"

    if not isinstance(vmap["total_duration"], (int, float)) or vmap["total_duration"] <= 0:
        return False, "total_duration must be a positive number"

    # content_type must be valid
    ok, err = validate_content_type(vmap["content_type"])
    if not ok:
        return False, f"Invalid content_type in output map: {err}"

    # resolution must match declared content_type
    ok, err = validate_resolution_for_content_type(vmap["resolution"], vmap["content_type"])
    if not ok:
        return False, err

    if not isinstance(vmap["scenes"], list) or len(vmap["scenes"]) == 0:
        return False, "scenes must be a non-empty list of compositions"

    # Validate individual composed scenes
    for i, scene in enumerate(vmap["scenes"]):
        for key in ("scene", "image_file", "audio_file", "duration_seconds"):
            if key not in scene:
                return False, f"Composed scene {i+1} is missing key: '{key}'"
            if scene[key] is None:
                return False, f"Composed scene {i+1} key '{key}' cannot be null"
        if not isinstance(scene["scene"], int) or scene["scene"] != i + 1:
            return False, f"Composed scene {i+1} index 'scene' must be {i + 1}"

    return True, ""
