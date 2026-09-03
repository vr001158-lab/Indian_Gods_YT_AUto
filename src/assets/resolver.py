# src/assets/resolver.py
# Main Orchestrator for Scene Asset Plan Generation

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.assets.manifest import load_asset_manifest
from src.assets.selector import resolve_deity, select_scene_assets


def create_scene_asset_plan(
    script: dict[str, Any],
    manifest_path: str | Path = "data/assets/asset_manifest.json",
    gods_dir: str | Path = "assets/gods",
    output_dir: str | Path = "data/visuals",
) -> dict[str, Any]:
    """
    Generate a language-independent Scene Asset Plan (`asset_plan_*.json`).

    The asset plan specifies deity, topic, and scene-by-scene selected assets
    (images/videos) from the local repository (Priority 1).
    This asset plan is reusable across Hindi, Telugu, and Tamil narration tracks.
    """
    topic = script.get("title") or script.get("approval_metadata", {}).get("selected_topic", "")
    deity = resolve_deity(topic)

    manifest = load_asset_manifest(manifest_path=manifest_path, gods_dir=gods_dir)
    scene_scripts = script.get("scene_scripts", [])

    content_type = (script.get("content_type") or "short").lower()
    fmt = (script.get("format") or "").lower()

    # Determine if timeline generator should build multi-segment retention timeline
    if fmt == "old" or len(scene_scripts) <= 2 or script.get("use_retention_timeline"):
        target_dur = float(script.get("duration_seconds") or script.get("total_duration_seconds") or 45.0)
        if content_type == "short" and (target_dur < 35.0 or target_dur >= 60.0):
            target_dur = 45.0
        from src.assets.selector import build_deity_visual_timeline
        scene_decisions = build_deity_visual_timeline(
            deity_key=deity,
            target_duration=target_dur,
            content_type=content_type,
            manifest=manifest,
        )
    else:
        scene_decisions = select_scene_assets(
            deity_key=deity,
            scene_scripts=scene_scripts,
            manifest=manifest,
            allow_online_fallback=True,
        )

    asset_plan = {
        "topic": topic,
        "deity": deity,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "approval_metadata": script.get("approval_metadata", {}),
        "scenes": scene_decisions,
    }

    # Save asset plan to output_dir
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_file = out_dir / f"asset_plan_{ts}.json"
    out_file.write_text(
        json.dumps(asset_plan, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    asset_plan["_asset_plan_path"] = str(out_file).replace("\\", "/")
    return asset_plan
