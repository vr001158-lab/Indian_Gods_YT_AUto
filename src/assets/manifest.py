# src/assets/manifest.py
# Asset Manifest Generator and Cache Manager

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.assets.scanner import scan_gods_assets, scan_gods_landscape_assets

MANIFEST_PATH = Path("data/assets/asset_manifest.json")
LANDSCAPE_MANIFEST_PATH = Path("data/assets/landscape_asset_manifest.json")


def generate_asset_manifest(
    gods_dir: str | Path = "assets/gods",
    output_manifest_path: str | Path = MANIFEST_PATH,
) -> dict[str, Any]:
    """
    Scans repository assets/gods/ directory, builds asset manifest structure,
    saves to output_manifest_path, and returns the manifest dict.
    """
    scan_results = scan_gods_assets(gods_dir=gods_dir)

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "deities": scan_results["deities"],
        "stats": scan_results["stats"],
    }

    out_p = Path(output_manifest_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return manifest


def load_asset_manifest(
    manifest_path: str | Path = MANIFEST_PATH,
    gods_dir: str | Path = "assets/gods",
    force_rescan: bool = False,
) -> dict[str, Any]:
    """
    Load asset_manifest.json. If missing, empty, or force_rescan is True,
    generates a fresh manifest by scanning assets/gods/.
    """
    p = Path(manifest_path)
    if not force_rescan and p.exists() and p.stat().st_size > 0:
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass

    return generate_asset_manifest(gods_dir=gods_dir, output_manifest_path=manifest_path)


def generate_landscape_asset_manifest(
    gods_dir: str | Path = "assets/gods_landscape_long_video",
    output_manifest_path: str | Path | None = LANDSCAPE_MANIFEST_PATH,
) -> dict[str, Any]:
    """
    Scans repository assets/gods_landscape_long_video/ directory, builds landscape manifest structure,
    saves to output_manifest_path, and returns the manifest dict.
    """
    scan_results = scan_gods_landscape_assets(gods_dir=gods_dir)

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "deities": scan_results["deities"],
        "stats": scan_results["stats"],
    }

    if output_manifest_path is not None:
        out_p = Path(output_manifest_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    return manifest


def load_landscape_asset_manifest(
    manifest_path: str | Path | None = None,
    gods_dir: str | Path = "assets/gods_landscape_long_video",
    force_rescan: bool = False,
) -> dict[str, Any]:
    """
    Load landscape_asset_manifest.json. If missing, empty, or force_rescan is True,
    generates a fresh manifest by scanning assets/gods_landscape_long_video/.
    """
    if str(gods_dir) != "assets/gods_landscape_long_video":
        return generate_landscape_asset_manifest(gods_dir=gods_dir, output_manifest_path=None)

    m_path = Path(manifest_path or LANDSCAPE_MANIFEST_PATH)
    if not force_rescan and m_path.exists() and m_path.stat().st_size > 0:
        try:
            return json.loads(m_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    return generate_landscape_asset_manifest(gods_dir=gods_dir, output_manifest_path=m_path)
