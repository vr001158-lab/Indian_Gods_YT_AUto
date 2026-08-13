# src/publisher/safety.py
# Phase 2K — Publisher Safety Gate
#
# Validates a Final QA result before any upload is attempted.
# Fail-closed: any missing/invalid field → raises PublisherSafetyError.
# NEVER logs, prints, or stores credential values.

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PRODUCTION_SOURCES = {"youtube_api", "cached_youtube_api"}
REJECTED_SOURCES   = {"mock", "offline"}


class PublisherSafetyError(ValueError):
    """Raised when the QA result fails the publisher safety gate."""


def _require(condition: bool, msg: str) -> None:
    if not condition:
        raise PublisherSafetyError(msg)


def validate_qa_for_publishing(qa: dict) -> None:
    """
    Validate a Final QA result dict for publishing eligibility.

    Rules (all must pass):
    1. approved_for_publishing must be exactly True.
    2. approval_metadata.approved_for_generation must be True.
    3. data_source must be in PRODUCTION_SOURCES.
    4. confidence must be "high".
    5. selected_topic must be non-empty.
    6. artifacts.video must reference a real, non-zero MP4.

    Raises PublisherSafetyError on any violation.
    """
    _require(
        qa.get("approved_for_publishing") is True,
        "approved_for_publishing is not True — Final QA must pass before publishing",
    )

    meta = qa.get("approval_metadata") or {}
    _require(
        meta.get("approved_for_generation") is True,
        "approval_metadata.approved_for_generation is not True",
    )

    src = qa.get("data_source", "")
    _require(
        src in PRODUCTION_SOURCES,
        f"data_source '{src}' is not a production source — "
        f"must be one of {sorted(PRODUCTION_SOURCES)}",
    )

    conf = qa.get("confidence", "")
    _require(
        conf == "high",
        f"confidence '{conf}' is not 'high'",
    )

    topic = qa.get("selected_topic", "")
    _require(
        bool(topic and topic.strip()),
        "selected_topic is missing or empty",
    )

    # Validate video file from QA artifacts
    arts = qa.get("artifacts") or {}
    video_map_file = arts.get("video", "")
    _require(bool(video_map_file), "QA artifacts missing 'video' (video map path)")

    video_map_path = Path(video_map_file)
    _require(video_map_path.exists(), f"Video map file not found: {video_map_path}")

    try:
        video_map = json.loads(video_map_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise PublisherSafetyError(f"Cannot parse video map: {exc}") from exc

    video_file = video_map.get("video_file", "")
    _require(bool(video_file), "video_map missing 'video_file' field")

    vp = Path(video_file)
    _require(vp.exists(), f"Video file not found: {vp}")
    _require(vp.stat().st_size > 0, f"Video file is zero bytes: {vp}")
    _require(
        vp.suffix.lower() == ".mp4",
        f"Video file must be .mp4, got: {vp.suffix}",
    )


def load_qa_result(qa_file: str | Path) -> dict:
    """
    Load and minimally validate a QA result JSON.
    Raises PublisherSafetyError if the file is missing, unparseable, or
    missing required top-level keys.
    """
    p = Path(qa_file)
    _require(p.exists(), f"QA result file not found: {p}")
    _require(p.stat().st_size > 0, f"QA result file is empty: {p}")

    try:
        qa = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PublisherSafetyError(f"QA result file is not valid JSON: {exc}") from exc

    for key in ("approved_for_publishing", "artifacts", "approval_metadata"):
        _require(key in qa, f"QA result missing required key: '{key}'")

    return qa
