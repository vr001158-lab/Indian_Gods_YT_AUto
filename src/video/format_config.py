# src/video/format_config.py
# Phase 2G+ — Canonical Content Format Configuration
#
# Single source of truth for SHORT and LONG format definitions.
# Every module that needs resolution, aspect ratio, or duration limits
# imports from here — never hard-codes its own constants.

from __future__ import annotations
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# Format registry
# ─────────────────────────────────────────────────────────────────────────────

FORMAT_CONFIGS: dict[str, dict[str, Any]] = {
    "short": {
        "content_type":           "short",
        "aspect_ratio":           "9:16",
        "resolution":             "1080x1920",
        "width":                  1080,
        "height":                 1920,
        "min_duration_seconds":   10,
        "max_duration_seconds":   180,   # YouTube Shorts ≤ 3 minutes
        "publish_classification": "short",
        "audio_sample_rate":      48000,
        "audio_channels":         2,
        "audio_codec":            "aac",
    },
    "long": {
        "content_type":           "long",
        "aspect_ratio":           "16:9",
        "resolution":             "1920x1080",
        "width":                  1920,
        "height":                 1080,
        "min_duration_seconds":   1,      # Any valid positive duration (content_type is authoritative)
        "max_duration_seconds":   43200,  # Up to 12 hours YouTube limit
        "publish_classification": "long",
        "audio_sample_rate":      48000,
        "audio_channels":         2,
        "audio_codec":            "aac",
    },
}

OLD_FORMAT_CONFIG: dict[str, Any] = {
    "format":                 "old",
    "content_type":           "short",
    "aspect_ratio":           "9:16",
    "resolution":             "1080x1920",
    "width":                  1080,
    "height":                 1920,
    "min_duration_seconds":   24,
    "max_duration_seconds":   45,
    "preferred_target_min":   28,
    "preferred_target_max":   40,
    "audio_narration_required": False,
    "publish_classification": "short",
    "audio_sample_rate":      48000,
    "audio_channels":         2,
    "audio_codec":            "aac",
}

VALID_CONTENT_TYPES: frozenset[str] = frozenset(FORMAT_CONFIGS.keys())
DEFAULT_CONTENT_TYPE: str = "short"

# Convenience lookup: (width, height) → content_type
_RESOLUTION_TO_CONTENT_TYPE: dict[tuple[int, int], str] = {
    (cfg["width"], cfg["height"]): ct
    for ct, cfg in FORMAT_CONFIGS.items()
}

ALLOWED_RESOLUTIONS_PER_FORMAT: dict[str, set[str]] = {
    "short": {"1080x1920", "720x1280"},
    "long": {"1920x1080", "1280x720"},
}

# All valid resolution strings
ALL_ALLOWED_RESOLUTIONS: frozenset[str] = frozenset(
    res for res_set in ALLOWED_RESOLUTIONS_PER_FORMAT.values() for res in res_set
)


# ─────────────────────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────────────────────

def get_format_config(content_type: str) -> dict[str, Any]:
    """
    Return the canonical format config dict for *content_type*.

    Raises ValueError for unknown content types.
    """
    ct = (content_type or DEFAULT_CONTENT_TYPE).lower().strip()
    if ct not in FORMAT_CONFIGS:
        raise ValueError(
            f"Unknown content_type '{content_type}'. "
            f"Valid types: {sorted(VALID_CONTENT_TYPES)}"
        )
    return FORMAT_CONFIGS[ct]


def resolution_for(content_type: str) -> str:
    """Return the canonical resolution string for *content_type*."""
    return get_format_config(content_type)["resolution"]


def content_type_from_resolution(width: int, height: int) -> str | None:
    """
    Reverse-lookup: return content_type matching (width, height), or None if unknown.
    Used only for informational / diagnostic purposes — NOT as a substitute for
    explicit content_type metadata.
    """
    return _RESOLUTION_TO_CONTENT_TYPE.get((width, height))


def validate_content_type(content_type: str) -> tuple[bool, str]:
    """
    Validate that *content_type* is a known format.

    Returns (True, "") on success; (False, error_message) on failure.
    """
    if not content_type or not isinstance(content_type, str):
        return False, "content_type is missing or not a string"
    ct = content_type.lower().strip()
    if ct not in VALID_CONTENT_TYPES:
        return False, (
            f"content_type '{content_type}' is not valid. "
            f"Must be one of: {sorted(VALID_CONTENT_TYPES)}"
        )
    return True, ""


def validate_resolution_for_content_type(resolution: str, content_type: str) -> tuple[bool, str]:
    """
    Check that *resolution* matches what *content_type* requires.

    Returns (True, "") on match; (False, error_message) on mismatch.
    """
    ok, err = validate_content_type(content_type)
    if not ok:
        return False, err

    ct = content_type.lower().strip()
    allowed = ALLOWED_RESOLUTIONS_PER_FORMAT[ct]
    if resolution not in allowed:
        return False, (
            f"Invalid resolution '{resolution}' for content_type='{ct}': "
            f"expected one of {sorted(allowed)}"
        )
    return True, ""


def validate_duration_for_content_type(duration_seconds: float, content_type: str) -> tuple[bool, str]:
    """
    Check that *duration_seconds* falls within the bounds for *content_type*.

    Returns (True, "") on success; (False, error_message) on failure.
    """
    ok, err = validate_content_type(content_type)
    if not ok:
        return False, err

    cfg = get_format_config(content_type)
    lo = cfg["min_duration_seconds"]
    hi = cfg["max_duration_seconds"]

    if duration_seconds <= 0:
        return False, f"Duration must be positive, got {duration_seconds}s"
    if duration_seconds < lo:
        return False, (
            f"Duration {duration_seconds:.1f}s is below the minimum for "
            f"content_type='{content_type}' ({lo}s)"
        )
    if duration_seconds > hi:
        return False, (
            f"Duration {duration_seconds:.1f}s exceeds the maximum for "
            f"content_type='{content_type}' ({hi}s)"
        )
    return True, ""
