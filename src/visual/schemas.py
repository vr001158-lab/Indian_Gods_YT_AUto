# src/visual/schemas.py
# Phase 2F — Script Input and Visual Output validation schemas

REQUIRED_SCRIPT_FIELDS = (
    "title",
    "duration_seconds",
    "narration",
    "scene_scripts",
    "retention_hooks",
    "shorts_scripts",
    "approval_metadata",
)

REQUIRED_VISUAL_MAP_FIELDS = (
    "script_title",
    "total_scenes",
    "style_preset",
    "provider",
    "visual_scenes",
)


def validate_script_input(script: dict) -> tuple:
    """
    Enforces that the incoming script contains narration, scenes, and approved metadata.
    """
    if not isinstance(script, dict):
        return False, "Input script is not a dictionary"

    # 1. Structural check
    for field in REQUIRED_SCRIPT_FIELDS:
        if field not in script:
            return False, f"Missing required script field: '{field}'"
        if script[field] is None:
            return False, f"Script field '{field}' cannot be null"

    if not isinstance(script["scene_scripts"], list) or len(script["scene_scripts"]) == 0:
        return False, "scene_scripts must be a non-empty list"

    # 2. Safety Gate: approval metadata check
    meta = script.get("approval_metadata")
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


def validate_visual_map_output(vmap: dict) -> tuple:
    """
    Validates that the generated visual mapping strictly adheres to the requested output format.
    """
    if not isinstance(vmap, dict):
        return False, "Visual map is not a dictionary"

    for field in REQUIRED_VISUAL_MAP_FIELDS:
        if field not in vmap:
            return False, f"Missing required visual map field: '{field}'"
        if vmap[field] is None:
            return False, f"Visual map field '{field}' cannot be null"

    # Type checks
    if not isinstance(vmap["script_title"], str) or not vmap["script_title"]:
        return False, "script_title must be a non-empty string"

    if not isinstance(vmap["total_scenes"], int) or vmap["total_scenes"] <= 0:
        return False, "total_scenes must be a positive integer"

    if not isinstance(vmap["style_preset"], str) or not vmap["style_preset"]:
        return False, "style_preset must be a non-empty string"

    if not isinstance(vmap["provider"], str) or not vmap["provider"]:
        return False, "provider must be a non-empty string"

    if not isinstance(vmap["visual_scenes"], list) or len(vmap["visual_scenes"]) == 0:
        return False, "visual_scenes must be a non-empty list"

    # Validate individual visual scenes
    for i, scene in enumerate(vmap["visual_scenes"]):
        for key in ("scene", "visual_prompt", "image_file", "style", "duration_seconds"):
            if key not in scene:
                return False, f"Visual scene {i+1} is missing key: '{key}'"
            if scene[key] is None:
                return False, f"Visual scene {i+1} key '{key}' cannot be null"

        if not isinstance(scene["scene"], int) or scene["scene"] != i + 1:
            return False, f"Visual scene {i+1} index 'scene' must be {i + 1}"

        if not isinstance(scene["visual_prompt"], str) or not scene["visual_prompt"]:
            return False, f"Visual scene {i+1} 'visual_prompt' must be a non-empty string"

        if not isinstance(scene["image_file"], str) or not scene["image_file"]:
            return False, f"Visual scene {i+1} 'image_file' must be a non-empty string"

        if not isinstance(scene["style"], str) or not scene["style"]:
            return False, f"Visual scene {i+1} 'style' must be a non-empty string"

        if not isinstance(scene["duration_seconds"], int) or scene["duration_seconds"] <= 0:
            return False, f"Visual scene {i+1} 'duration_seconds' must be a positive integer"

    return True, ""
