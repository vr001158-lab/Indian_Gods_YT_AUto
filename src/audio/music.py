# src/audio/music.py
# Phase 6.3 / Music Pipeline v2 — Copyright Safety & Provenance Architecture
#
# Primary Music Path: Verified YouTube Audio Library & Licensed Royalty-Free tracks
# Fallback 1: Verified original-generated tracks (e.g. shiva_devotional_shivaranjani_flute.wav)
# Fallback 2: Narration-only output (None)
#
# Hard Provenance Gate:
#   Tracks that are unverified, non-commercial, non-YouTube permitted, or have SHA256 mismatch MUST BE REJECTED.

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any

MUSIC_DIR = Path("assets/music")
MANIFEST_PATH = MUSIC_DIR / "music_manifest.json"

# Allowed legitimate source types
VALID_SOURCE_TYPES = {"youtube_audio_library", "royalty_free_public", "original_generated"}
PRIMARY_SOURCE_TYPES = {"youtube_audio_library", "royalty_free_public"}


def load_music_manifest(manifest_path: str | Path = MANIFEST_PATH) -> dict:
    """Loads and parses music_manifest.json."""
    mp = Path(manifest_path)
    if not mp.exists():
        return {"tracks": []}
    try:
        return json.loads(mp.read_text(encoding="utf-8"))
    except Exception:
        return {"tracks": []}


def validate_music_provenance(
    music_file: str | Path,
    manifest_path: str | Path = MANIFEST_PATH,
) -> tuple[bool, str, dict[str, Any]]:
    """
    Hard Provenance Gate for Music Pipeline v2.
    Validates that a music track is:
      1. Physical file exists
      2. Registered in music_manifest.json
      3. Marked as approved (approved == True)
      4. Permitted for commercial use (commercial_use == True)
      5. Permitted for YouTube Shorts (youtube_shorts_permitted != False)
      6. Has valid source_type in (youtube_audio_library, royalty_free_public, original_generated)
      7. Passes SHA256 digest verification

    Returns (is_valid, reason, track_info).
    """
    mf = Path(music_file)
    if not mf.exists():
        return False, f"Music file not found: {mf}", {}

    manifest = load_music_manifest(manifest_path)
    tracks = manifest.get("tracks", [])

    rel_str = str(mf.as_posix())

    matched_track = None
    for tr in tracks:
        tr_rel = tr.get("relative_path", "").replace("\\", "/")
        tr_name = tr.get("filename", "")
        if tr_rel == rel_str or tr_name == mf.name:
            matched_track = tr
            break

    if not matched_track:
        return False, f"Unauthorized music track: {mf.name} is not registered in music_manifest.json", {}

    if not matched_track.get("approved", False):
        return False, f"Music track {mf.name} is marked as unapproved in manifest", matched_track

    if matched_track.get("commercial_use") is False:
        return False, f"Music track {mf.name} is not permitted for commercial use", matched_track

    if matched_track.get("youtube_shorts_permitted") is False:
        return False, f"Music track {mf.name} is not permitted for YouTube Shorts distribution", matched_track

    stype = matched_track.get("source_type", "")
    if stype not in VALID_SOURCE_TYPES:
        return False, f"Music track {mf.name} has unauthorized source_type: '{stype}'", matched_track

    # Check SHA256 digest match
    expected_sha256 = matched_track.get("sha256")
    if expected_sha256:
        actual_sha256 = hashlib.sha256(mf.read_bytes()).hexdigest()
        if actual_sha256 != expected_sha256:
            return False, f"Music SHA256 mismatch for {mf.name}: expected {expected_sha256}, got {actual_sha256}", matched_track

    return True, "Approved music track with valid provenance", matched_track


def discover_music_tracks(music_dir: str | Path = MUSIC_DIR) -> dict[str, list[Path]]:
    """
    Discover approved background music tracks in assets/music/.
    Categories: devotional, ambient, transition.
    Only returns files that pass provenance validation.
    """
    base = Path(music_dir)
    manifest_file = base / "music_manifest.json"
    categories = ["devotional", "ambient", "transition"]
    result: dict[str, list[Path]] = {cat: [] for cat in categories}

    if not base.exists():
        return result

    for cat in categories:
        cat_dir = base / cat
        if cat_dir.exists():
            for f in sorted(cat_dir.glob("*")):
                if f.suffix.lower() in (".mp3", ".wav", ".aac", ".flac"):
                    ok, _, _ = validate_music_provenance(f, manifest_path=manifest_file)
                    if ok:
                        result[cat].append(f)

    return result


def select_background_music_v2(
    category: str = "devotional",
    music_dir: str | Path = MUSIC_DIR,
) -> tuple[Path | None, str]:
    """
    Music Pipeline v2 Selection Strategy.

    Priority Order:
      1. Primary: Verified YouTube Audio Library / Commercial Royalty-Free track matching category/deity.
      2. Fallback 1: Verified original-generated track (e.g. shiva_devotional_shivaranjani_flute.wav).
      3. Fallback 2: Narration-only (None).

    Returns (selected_track_path, selection_type)
      selection_type: "primary", "fallback_generated", or "narration_only"
    """
    manifest_file = Path(music_dir) / "music_manifest.json"
    manifest = load_music_manifest(manifest_file)
    tracks = manifest.get("tracks", [])

    primary_candidates = []
    fallback_candidates = []

    for tr in tracks:
        rel_p = tr.get("relative_path", "")
        fpath = Path(music_dir).parent / rel_p if not Path(rel_p).is_absolute() else Path(rel_p)
        if not fpath.exists():
            fpath = Path(music_dir) / tr.get("category", "") / tr.get("filename", "")
        if not fpath.exists():
            continue

        ok, _, tinfo = validate_music_provenance(fpath, manifest_path=manifest_file)
        if not ok:
            continue

        cat = tinfo.get("category", "devotional")
        if cat != category and category != "devotional":
            continue

        stype = tinfo.get("source_type", "")
        if stype in PRIMARY_SOURCE_TYPES:
            primary_candidates.append(fpath)
        elif stype == "original_generated":
            fallback_candidates.append(fpath)

    # 1. Primary path
    if primary_candidates:
        return primary_candidates[0], "primary"

    # 2. Fallback 1 path
    if fallback_candidates:
        return fallback_candidates[0], "fallback_generated"

    # 3. Fallback 2 path
    return None, "narration_only"


def select_background_music(
    category: str = "devotional",
    music_dir: str | Path = MUSIC_DIR,
) -> Path | None:
    """
    Backward compatible helper for existing callers.
    Calls Music Pipeline v2 selection and returns the track Path or None.
    """
    track, _ = select_background_music_v2(category=category, music_dir=music_dir)
    return track
