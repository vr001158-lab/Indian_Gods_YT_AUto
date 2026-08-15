# src/visual/generator.py
# Phase 2F — Visual Generation Engine
# Orchestrates script validation, scene visual planning, and image asset generation.

import json
import time
from pathlib import Path
from src.visual.schemas import validate_script_input, validate_visual_map_output
from src.visual.planner import plan_visuals
from src.visual.providers import (
    FluxProvider,
    MockVisualProvider,
    PollinationsVisualProvider,
    StableDiffusionProvider,
)

PROVIDERS = {
    "flux":               FluxProvider,
    "stable_diffusion":   StableDiffusionProvider,
    "pollinations":       PollinationsVisualProvider,
    "mock":               MockVisualProvider,
}


def generate_visual_mapping(
    script: dict,
    provider_name: str = "mock",
    style_preset: str = "Devotional Cinematic Painting, 8k, divine golden glow",
    output_dir: Path = Path("data/visuals"),
) -> dict:
    """
    Orchestrates the conversion of a validated script into a visual mapping and asset collection.

    Raises ValueError if input fails safety gates.
    """
    ok, error_msg = validate_script_input(script)
    if not ok:
        raise ValueError(f"❌ Safety Gate Rejection: {error_msg}")

    if provider_name not in PROVIDERS:
        raise ValueError(f"Unknown visual provider: {provider_name} (must be one of {list(PROVIDERS.keys())})")

    # Instantiate provider
    provider = PROVIDERS[provider_name](provider_name=provider_name)

    # Establish unique run subfolder to prevent overwrite collisions
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    run_visual_dir = output_dir / f"run_{timestamp}"
    run_visual_dir.mkdir(parents=True, exist_ok=True)

    # 1. Generate language-independent Scene Asset Plan via src.assets.resolver
    from src.assets.resolver import create_scene_asset_plan
    asset_plan = create_scene_asset_plan(
        script=script,
        output_dir=output_dir,
    )

    # 2. Synthesize/resolve scene visual assets according to asset plan
    visual_scenes = []
    for scene_item in asset_plan["scenes"]:
        scene_num = scene_item["scene"]
        asset_type = scene_item["asset_type"]
        asset_path = scene_item["asset"]
        source = scene_item["source"]
        visual_ref = ""
        for sc in script.get("scene_scripts", []):
            if sc["scene"] == scene_num:
                duration = sc.get("duration_seconds", 30)
                visual_ref = sc.get("visual_reference", "")
                break

        # Output asset file for this run
        ext = ".mp4" if asset_type == "video" else ".png"
        image_file = run_visual_dir / f"scene_{scene_num}{ext}"

        if source == "repository" and Path(asset_path).exists():
            # Use repository asset directly
            image_file_str = asset_path
        else:
            # Fallback to provider image synthesis if repo asset unavailable
            prompt = f"Scene {scene_num} for {script['title']}"
            provider.generate_image(prompt, style_preset, image_file)
            image_file_str = str(image_file.absolute()).replace("\\", "/")

        v_prompt = f"{visual_ref} (Scene #{scene_num}: {asset_type} asset from {source})" if visual_ref else f"Scene #{scene_num}: {asset_type} asset from {source}"

        visual_scenes.append({
            "scene": scene_num,
            "visual_prompt": v_prompt,
            "image_file": image_file_str,
            "asset_type": asset_type,
            "source": source,
            "style": style_preset,
            "duration_seconds": duration,
        })

    # 3. Assemble final visual map
    run_id = script.get("run_id") or f"run_{timestamp}"
    visual_map = {
        "run_id": run_id,
        "script_title": script["title"],
        "total_scenes": len(visual_scenes),
        "style_preset": style_preset,
        "provider": provider_name,
        "asset_plan_path": asset_plan.get("_asset_plan_path", ""),
        "visual_scenes": visual_scenes,
        "approval_metadata": script["approval_metadata"],
    }

    # Validate output schema
    ok_out, err_out = validate_visual_map_output(visual_map)
    if not ok_out:
        raise RuntimeError(f"❌ Internal Error: Generated visual map fails schema: {err_out}")

    return visual_map


def process_script_file(
    script_path: Path,
    provider_name: str = "mock",
    style_preset: str = "Devotional Cinematic Painting, 8k, divine golden glow",
    output_dir: Path = Path("data/visuals"),
) -> Path:
    """
    Loads a script file, runs visual generation mapping, and saves the mapping JSON.
    """
    if not script_path.exists():
        raise FileNotFoundError(f"Script file not found: {script_path}")

    try:
        script = json.loads(script_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise ValueError(f"Failed to parse script JSON: {e}")

    visual_map = generate_visual_mapping(
        script=script,
        provider_name=provider_name,
        style_preset=style_preset,
        output_dir=output_dir,
    )

    # Persist the mapping JSON
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_file = output_dir / f"visual_map_{timestamp}.json"

    out_file.write_text(
        json.dumps(visual_map, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    return out_file
