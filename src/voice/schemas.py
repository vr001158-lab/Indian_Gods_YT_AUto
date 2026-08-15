# src/voice/schemas.py
# Phase 3 — Script Input and Audio Output validation schemas
#
# Production providers accepted:
#   - edge_neural_tts  (primary)
#   - google_chirp3_hd (future premium)

REQUIRED_SCRIPT_FIELDS_COMMON = (
    "title",
    "duration_seconds",
    "narration",
    "scene_scripts",
    "retention_hooks",
    "approval_metadata",
)

REQUIRED_SCRIPT_FIELDS_SHORT = REQUIRED_SCRIPT_FIELDS_COMMON + ("shorts_scripts",)
REQUIRED_SCRIPT_FIELDS = REQUIRED_SCRIPT_FIELDS_SHORT

REQUIRED_AUDIO_FIELDS = (
    "script_title",
    "total_duration_seconds",
    "provider",
    "mode",
    "real_tts",
    "language_code",
    "voice_name",
    "audio_scenes",
    "full_narration_audio_file",
)

# Providers that are allowed in production mode.
# gTTS, pyttsx3, sine-wave, and mock are NEVER included here.
PRODUCTION_PROVIDERS = {"edge_neural_tts", "google_chirp3_hd"}

# Providers that must NEVER be used in production (fail-safe explicit deny-list)
NON_PRODUCTION_PROVIDERS = {"gtts", "pyttsx3", "sine_wave", "mock", "elevenlabs"}


def validate_script_input(script: dict, content_type: str = "short") -> tuple:
    """
    Enforces that the incoming script contains narration, scenes, and approved metadata.
    """
    if not isinstance(script, dict):
        return False, "Input script is not a dictionary"

    ct = (content_type or "short").lower().strip()
    required_fields = REQUIRED_SCRIPT_FIELDS_SHORT if ct == "short" else REQUIRED_SCRIPT_FIELDS_COMMON

    # 1. Structural check
    for field in required_fields:
        if field not in script:
            return False, f"Missing required script field: '{field}'"
        if script[field] is None:
            return False, f"Script field '{field}' cannot be null"

    if not isinstance(script["narration"], str) or not script["narration"].strip():
        return False, "Narration text must be a non-empty string"

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


def validate_audio_output(audio: dict) -> tuple:
    """
    Validates that the generated audio mapping strictly adheres to the requested output format.

    Production mode rules:
      - provider must be in PRODUCTION_PROVIDERS (edge_neural_tts or google_chirp3_hd)
      - real_tts must be True
      - Fake providers (gTTS, mock, sine-wave) are NEVER accepted
    """
    if not isinstance(audio, dict):
        return False, "Audio mapping is not a dictionary"

    for field in REQUIRED_AUDIO_FIELDS:
        if field not in audio:
            return False, f"Missing required audio field: '{field}'"
        if audio[field] is None:
            return False, f"Audio field '{field}' cannot be null"

    # Type checks
    if not isinstance(audio["script_title"], str) or not audio["script_title"]:
        return False, "script_title must be a non-empty string"

    if not isinstance(audio["total_duration_seconds"], int) or audio["total_duration_seconds"] <= 0:
        return False, "total_duration_seconds must be a positive integer"

    if not isinstance(audio["provider"], str) or not audio["provider"]:
        return False, "provider must be a non-empty string"

    if audio.get("mode") == "production":
        provider = audio["provider"]
        if provider not in PRODUCTION_PROVIDERS:
            return False, (
                f"production audio must use a production provider "
                f"(got '{provider}', accepted: {sorted(PRODUCTION_PROVIDERS)})"
            )
        if audio.get("real_tts") is not True:
            return False, "production audio must have real_tts=True"
        if provider in NON_PRODUCTION_PROVIDERS:
            return False, f"Provider '{provider}' is explicitly forbidden in production mode"

    if audio.get("mode") not in ("production", "test"):
        return False, "mode must be 'production' or 'test'"

    if not isinstance(audio.get("real_tts"), bool):
        return False, "real_tts must be a boolean"

    if not isinstance(audio.get("language_code"), str) or not audio["language_code"]:
        return False, "language_code must be a non-empty string"

    if not isinstance(audio.get("voice_name"), str):
        return False, "voice_name must be a string"

    if not isinstance(audio["full_narration_audio_file"], str) or not audio["full_narration_audio_file"]:
        return False, "full_narration_audio_file must be a non-empty string"

    if not isinstance(audio["audio_scenes"], list) or len(audio["audio_scenes"]) == 0:
        return False, "audio_scenes must be a non-empty list"

    # Validate individual audio scenes
    for i, scene in enumerate(audio["audio_scenes"]):
        for key in ("scene", "voice_text", "audio_file", "duration_seconds"):
            if key not in scene:
                return False, f"Audio scene {i+1} is missing key: '{key}'"
            if scene[key] is None:
                return False, f"Audio scene {i+1} key '{key}' cannot be null"

        if not isinstance(scene["scene"], int) or scene["scene"] != i + 1:
            return False, f"Audio scene {i+1} index 'scene' must be {i + 1}"

        if not isinstance(scene["voice_text"], str) or not scene["voice_text"]:
            return False, f"Audio scene {i+1} 'voice_text' must be a non-empty string"

        if not isinstance(scene["audio_file"], str) or not scene["audio_file"]:
            return False, f"Audio scene {i+1} 'audio_file' must be a non-empty string"

        if not isinstance(scene["duration_seconds"], int) or scene["duration_seconds"] <= 0:
            return False, f"Audio scene {i+1} 'duration_seconds' must be a positive integer"

    return True, ""
