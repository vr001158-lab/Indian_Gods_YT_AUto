# src/qa/artifacts.py
# Phase 2J — Final Pipeline QA Gate: Artifact Discovery and Loading
#
# Discovers the most recent compatible set of pipeline artifacts and
# loads them into memory.  All failures raise ValueError (fail-closed).

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# Artifact bundle
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class PipelineArtifacts:
    """All JSON manifests and media file paths for the final QA run."""

    # JSON manifests (parsed dicts)
    decision:        dict
    content_brief:   dict
    script:          dict
    audio_map:       dict
    visual_map:      dict
    video_map:       dict
    thumbnail_meta:  dict

    # Raw file paths (strings, for serialisation)
    decision_file:        str
    content_brief_file:   str
    script_file:          str
    audio_map_file:       str
    visual_map_file:      str
    video_map_file:       str
    thumbnail_meta_file:  str

    # Media files
    video_file:     str
    thumbnail_file: str

    # Convenience: all manifests by short name for provenance/topic checks
    @property
    def all_manifests(self) -> dict[str, dict]:
        return {
            "decision":        self.decision,
            "content_brief":   self.content_brief,
            "script":          self.script,
            "audio_map":       self.audio_map,
            "visual_map":      self.visual_map,
            "video_map":       self.video_map,
            "thumbnail_meta":  self.thumbnail_meta,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _newest(directory: Path, pattern: str) -> Path:
    """Return the newest file matching pattern in directory, or raise."""
    candidates = sorted(directory.glob(pattern))
    if not candidates:
        raise FileNotFoundError(
            f"No file matching '{pattern}' found in {directory}"
        )
    return candidates[-1]  # lexicographic newest == timestamp newest


def _load(path: Path) -> dict:
    """Parse JSON from path; raise ValueError on failure."""
    if not path.exists():
        raise FileNotFoundError(f"Required artifact not found: {path}")
    if path.stat().st_size == 0:
        raise ValueError(f"Artifact is zero bytes: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Corrupted JSON in {path}: {exc}") from exc


# ─────────────────────────────────────────────────────────────────────────────
# Public: discovery
# ─────────────────────────────────────────────────────────────────────────────

def discover_artifacts(
    base_dir: Path | str | None = None,
    *,
    decision_file: str | None        = None,
    content_brief_file: str | None   = None,
    script_file: str | None          = None,
    audio_map_file: str | None       = None,
    visual_map_file: str | None      = None,
    video_map_file: str | None       = None,
    thumbnail_meta_file: str | None  = None,
) -> PipelineArtifacts:
    """
    Locate and load all pipeline artifacts.

    If explicit paths are supplied they take precedence; otherwise the
    newest matching file in each data sub-directory is used.

    Parameters
    ----------
    base_dir:
        Project root.  Defaults to the repository root (two levels above
        this file).
    """
    if base_dir is None:
        base_dir = Path(__file__).parent.parent.parent  # repo root
    base = Path(base_dir)

    # ── Resolve manifest files ────────────────────────────────────────────

    d_file = Path(decision_file) if decision_file else _newest(
        base / "data" / "decision", "decision_*.json"
    )
    cb_file = Path(content_brief_file) if content_brief_file else _newest(
        base / "data" / "content_briefs", "content_brief_*.json"
    )
    sc_file = Path(script_file) if script_file else _newest(
        base / "data" / "scripts", "script_*.json"
    )
    am_file = Path(audio_map_file) if audio_map_file else _newest(
        base / "data" / "audio", "audio_map_*.json"
    )
    vm_file = Path(visual_map_file) if visual_map_file else _newest(
        base / "data" / "visuals", "visual_map_*.json"
    )
    vid_map_file = Path(video_map_file) if video_map_file else _newest(
        base / "data" / "videos", "video_map_*.json"
    )
    tm_file = Path(thumbnail_meta_file) if thumbnail_meta_file else _newest(
        base / "data" / "thumbnails", "thumbnail_metadata_*.json"
    )

    # ── Load manifests ────────────────────────────────────────────────────

    decision       = _load(d_file)
    content_brief  = _load(cb_file)
    script         = _load(sc_file)
    audio_map      = _load(am_file)
    visual_map     = _load(vm_file)
    video_map      = _load(vid_map_file)
    thumbnail_meta = _load(tm_file)

    # ── Resolve media files from manifests ────────────────────────────────

    video_file = video_map.get("video_file", "")
    if not video_file:
        raise ValueError("video_map missing 'video_file' field")

    # Thumbnail file: derive from metadata created_at timestamp
    created_at = thumbnail_meta.get("created_at", "")
    fmt        = thumbnail_meta.get("format", "png")
    thumb_dir  = base / "data" / "thumbnails"
    thumb_file_path = thumb_dir / f"thumbnail_{created_at}.{fmt}"
    if not thumb_file_path.exists():
        # Fallback: newest PNG/JPEG
        candidates = sorted(
            list(thumb_dir.glob("thumbnail_*.png"))
            + list(thumb_dir.glob("thumbnail_*.jpg"))
            + list(thumb_dir.glob("thumbnail_*.jpeg"))
        )
        # Exclude metadata files
        candidates = [f for f in candidates if "metadata" not in f.name]
        if not candidates:
            raise FileNotFoundError(f"No thumbnail image found in {thumb_dir}")
        thumb_file_path = candidates[-1]

    return PipelineArtifacts(
        decision        = decision,
        content_brief   = content_brief,
        script          = script,
        audio_map       = audio_map,
        visual_map      = visual_map,
        video_map       = video_map,
        thumbnail_meta  = thumbnail_meta,
        decision_file       = str(d_file),
        content_brief_file  = str(cb_file),
        script_file         = str(sc_file),
        audio_map_file      = str(am_file),
        visual_map_file     = str(vm_file),
        video_map_file      = str(vid_map_file),
        thumbnail_meta_file = str(tm_file),
        video_file      = str(video_file),
        thumbnail_file  = str(thumb_file_path),
    )
