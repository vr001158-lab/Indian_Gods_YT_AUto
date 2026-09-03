# src/qa/gate.py
# Phase 2J — Final Pipeline QA Gate: Orchestrator
#
# FinalQAGate runs every check and produces a structured result.
# It is ALWAYS fail-closed: any exception → approved_for_publishing = false.
#
# Phase 2G+: content_type is threaded through video checks so format-specific
# resolution and duration rules are enforced.

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.video.format_config import DEFAULT_CONTENT_TYPE, get_format_config, validate_content_type

from .artifacts import PipelineArtifacts, discover_artifacts
from .checks import (
    check_audio_map,
    check_decision_approval,
    check_json_file,
    check_media_file,
    check_provenance_consistency,
    check_scene_sync,
    check_thumbnail_meta,
    check_topic_consistency,
    check_video_map,
    check_video_with_ffprobe,
    check_visual_map,
)


# ─────────────────────────────────────────────────────────────────────────────
# Result dataclass
# ─────────────────────────────────────────────────────────────────────────────

class QAResult:
    """Holds the complete QA outcome."""

    def __init__(self, artifacts: PipelineArtifacts | None = None) -> None:
        self.approved_for_publishing: bool = False
        self.artifacts_ref: PipelineArtifacts | None = artifacts
        self.checks: dict[str, bool]   = {}
        self.details: dict[str, str]   = {}
        self.errors:  list[str]        = []
        self.approval_metadata: dict   = {}
        self.video_validation: dict    = {}
        self.selected_topic: str       = ""
        self.score:           Any      = None
        self.confidence:      str      = ""
        self.data_source:     str      = ""
        self.approved_at:     str      = ""
        self.content_type:    str      = DEFAULT_CONTENT_TYPE
        self.experiment_tag:  str      = ""
        self.aspect_ratio:    str      = ""
        self.resolution:      str      = ""

    # ── Helpers ──────────────────────────────────────────────────────────────

    def record(self, name: str, passed: bool, detail: str) -> None:
        self.checks[name]  = passed
        self.details[name] = detail
        if not passed:
            self.errors.append(f"{name}: {detail}")

    def all_passed(self) -> bool:
        return all(self.checks.values()) if self.checks else False

    # ── Serialisation ────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        arts = self.artifacts_ref
        return {
            "approved_for_publishing": self.approved_for_publishing,
            "selected_topic":          self.selected_topic,
            "score":                   self.score,
            "confidence":              self.confidence,
            "data_source":             self.data_source,
            "content_type":            self.content_type,
            "experiment_tag":          self.experiment_tag,
            "aspect_ratio":            self.aspect_ratio,
            "resolution":              self.resolution,
            "artifacts": {
                "decision":       arts.decision_file      if arts else "",
                "content_brief":  arts.content_brief_file if arts else "",
                "script":         arts.script_file        if arts else "",
                "audio":          arts.audio_map_file     if arts else "",
                "visual":         arts.visual_map_file    if arts else "",
                "video":          arts.video_map_file     if arts else "",
                "thumbnail":      arts.thumbnail_meta_file if arts else "",
            },
            "checks":  self.checks,
            "details": self.details,
            "errors":  self.errors,
            "video_validation":  self.video_validation,
            "approval_metadata": self.approval_metadata,
            "approved_at":       self.approved_at,
        }

    def save(self, output_dir: Path) -> Path:
        """Write result JSON to data/qa/final_qa_YYYYMMDD_HHMMSS.json."""
        output_dir.mkdir(parents=True, exist_ok=True)
        ts   = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = output_dir / f"final_qa_{ts}.json"
        path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return path


# ─────────────────────────────────────────────────────────────────────────────
# Main gate
# ─────────────────────────────────────────────────────────────────────────────

class FinalQAGate:
    """
    Runs all QA checks against a complete set of pipeline artifacts.

    Usage
    -----
    gate   = FinalQAGate(base_dir=".", content_type="short")
    result = gate.run()
    """

    def __init__(
        self,
        base_dir: str | Path | None = None,
        allow_mock: bool = False,
        content_type: str = DEFAULT_CONTENT_TYPE,
        **artifact_overrides,
    ) -> None:
        self._base_dir         = Path(base_dir) if base_dir else None
        self._allow_mock       = allow_mock
        self._content_type     = content_type
        self._artifact_kwargs  = artifact_overrides

    # ── Public entry point ───────────────────────────────────────────────────

    def run(self, artifacts: PipelineArtifacts | None = None) -> QAResult:
        """
        Execute all checks.  Returns a QAResult — never raises.
        approved_for_publishing is set only when every check passes AND
        the decision truly meets production standards.
        """
        result = QAResult()

        # ── Step 0: Load artifacts ─────────────────────────────────────────
        try:
            if artifacts is None:
                artifacts = discover_artifacts(
                    self._base_dir, **self._artifact_kwargs
                )
            result.artifacts_ref = artifacts
        except Exception as exc:
            result.record("artifact_discovery", False, str(exc))
            result.approved_for_publishing = False
            result.approved_at = datetime.now(timezone.utc).isoformat()
            return result

        arts = artifacts

        # ── Step 1: Approval provenance ───────────────────────────────────
        ok, detail = check_decision_approval(arts.decision)
        result.record("decision_approval", ok, detail)

        # ── Step 2: JSON file integrity for all manifests ─────────────────
        manifest_files = {
            "decision_json":        arts.decision_file,
            "content_brief_json":   arts.content_brief_file,
            "script_json":          arts.script_file,
            "audio_map_json":       arts.audio_map_file,
            "visual_map_json":      arts.visual_map_file,
            "video_map_json":       arts.video_map_file,
            "thumbnail_meta_json":  arts.thumbnail_meta_file,
        }
        for name, fpath in manifest_files.items():
            ok, detail = check_json_file(fpath)
            result.record(f"file_integrity.{name}", ok, detail)

        # ── Step 3: Media file existence ──────────────────────────────────
        ok, detail = check_media_file(arts.video_file)
        result.record("file_integrity.video_file",     ok, detail)

        ok, detail = check_media_file(arts.thumbnail_file)
        result.record("file_integrity.thumbnail_file", ok, detail)

        # ── Step 4: Provenance consistency across manifests ───────────────
        ok, detail = check_provenance_consistency(arts.all_manifests)
        result.record("provenance", ok, detail)

        # ── Step 5: Topic consistency ─────────────────────────────────────
        ok, detail = check_topic_consistency(arts.decision, {
            "script":         arts.script,
            "audio_map":      arts.audio_map,
            "visual_map":     arts.visual_map,
            "content_brief":  arts.content_brief,
            "thumbnail_meta": arts.thumbnail_meta,
        })
        result.record("topic_consistency", ok, detail)

        # ── Step 6: Audio QA ──────────────────────────────────────────────
        ok, detail = check_audio_map(arts.audio_map)
        result.record("audio", ok, detail)

        # ── Step 7: Visual QA ─────────────────────────────────────────────
        ok, detail = check_visual_map(arts.visual_map)
        result.record("visual", ok, detail)

        # ── Step 8: Video QA ──────────────────────────────────────────────
        ok, detail = check_video_map(arts.video_map, content_type=self._content_type)
        result.record("video", ok, detail)

        ok, detail, vval = check_video_with_ffprobe(
            arts.video_file,
            allow_mock=self._allow_mock,
            content_type=self._content_type,
        )
        result.record("video_ffprobe", ok, detail)
        result.video_validation = vval

        # ── Step 9: Thumbnail QA ──────────────────────────────────────────
        ok, detail = check_thumbnail_meta(arts.thumbnail_meta, arts.thumbnail_file)
        result.record("thumbnail", ok, detail)

        # ── Step 10: Scene synchronisation ───────────────────────────────
        ok, detail = check_scene_sync(
            arts.script, arts.audio_map, arts.visual_map, arts.video_map
        )
        result.record("scene_sync", ok, detail)

        # ── Step 11: Populate metadata from decision ───────────────────────
        decision = arts.decision
        result.selected_topic = decision.get("selected_topic", "")
        result.score          = decision.get("score")
        result.confidence     = decision.get("confidence", "")
        result.data_source    = decision.get("data_source", "")
        result.approval_metadata = {
            "approved_for_generation": decision.get("approved_for_generation"),
            "selected_topic":          decision.get("selected_topic"),
            "score":                   decision.get("score"),
            "confidence":              decision.get("confidence"),
            "data_source":             decision.get("data_source"),
        }
        result.approved_at = datetime.now(timezone.utc).isoformat()

        # ── Step 11b: Populate format & experiment metadata ────────────────
        result.content_type = self._content_type
        if arts.script and isinstance(arts.script, dict):
            result.experiment_tag = arts.script.get("experiment_tag", "")
        elif decision and isinstance(decision, dict):
            result.experiment_tag = decision.get("experiment_tag", "")
        try:
            fmt_cfg = get_format_config(self._content_type)
            result.aspect_ratio = fmt_cfg["aspect_ratio"]
            result.resolution   = fmt_cfg["resolution"]
        except Exception:
            pass

        # ── Step 12: Final gate — fail-closed ─────────────────────────────
        # IMPORTANT: approved_for_publishing is ONLY set to True when ALL
        # checks pass AND the decision meets production standards.
        # There is NO fallback, NO partial approval.
        all_checks_pass = result.all_passed()
        is_production = (
            decision.get("approved_for_generation") is True
            and decision.get("data_source") in {"youtube_api", "cached_youtube_api"}
            and decision.get("confidence") == "high"
        )
        result.approved_for_publishing = all_checks_pass and is_production

        return result
