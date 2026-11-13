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


def _extract_video_frame(video_path: Path, output_frame_path: Path) -> bool:
    """
    Extracts a representative still frame (at 00:00:00) from video_path and saves it to output_frame_path.
    Returns True if extraction succeeded and output_frame_path is a valid non-empty file.
    Returns False on FFmpeg missing, non-zero return code, or extraction failure.
    NEVER creates synthetic RGB placeholder images.
    """
    output_frame_path.parent.mkdir(parents=True, exist_ok=True)
    if not video_path.exists() or video_path.stat().st_size == 0:
        return False

    try:
        import subprocess
        cmd = [
            "ffmpeg", "-y",
            "-ss", "00:00:00",
            "-i", str(video_path),
            "-vframes", "1",
            "-q:v", "2",
            str(output_frame_path),
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        if res.returncode == 0 and output_frame_path.exists() and output_frame_path.stat().st_size > 0:
            return True
    except Exception:
        pass

    return False


def _find_genuine_deity_image(deity_key: str, scene_num: int = 1, content_type: str = "short") -> Path | None:
    """
    Finds an existing genuine repository deity image on disk to serve as normal image fallback.
    Strictly preserves deity isolation (only from the same deity directory).
    """
    if not deity_key:
        return None

    gods_dirs = []
    if content_type == "long":
        gods_dirs.append(Path("assets/gods_landscape_long_video") / deity_key)
    gods_dirs.append(Path("assets/gods") / deity_key)

    candidates: list[Path] = []
    for g_dir in gods_dirs:
        if g_dir.exists() and g_dir.is_dir():
            for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
                candidates.extend([p for p in g_dir.glob(ext) if p.is_file() and p.stat().st_size > 0])

    if not candidates:
        return None

    candidates.sort(key=lambda p: p.name)
    idx = (scene_num - 1) % len(candidates)
    return candidates[idx]


def generate_visual_mapping(
    script: dict,
    provider_name: str = "mock",
    style_preset: str = "Devotional Cinematic Painting, 8k, divine golden glow",
    output_dir: Path = Path("data/visuals"),
    format: str | None = None,
    content_type: str | None = None,
) -> dict:
    """
    Orchestrates the conversion of a validated script into a visual mapping and asset collection.

    Raises ValueError if input fails safety gates.
    """
    if format:
        script["format"] = format
    if content_type:
        script["content_type"] = content_type

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

    fmt = (script.get("format") or "").lower()
    is_retention_timeline = (fmt == "old" or script.get("use_retention_timeline"))

    # 2. Synthesize/resolve scene visual assets according to asset plan
    visual_scenes = []
    for scene_item in asset_plan["scenes"]:
        scene_num = scene_item["scene"]
        asset_type = scene_item["asset_type"]
        asset_path = scene_item["asset"]
        source = scene_item["source"]
        visual_ref = ""
        duration = int(round(scene_item.get("duration_seconds", 30)))
        for sc in script.get("scene_scripts", []):
            if sc["scene"] == scene_num:
                visual_ref = sc.get("visual_reference", "")
                if not is_retention_timeline:
                    duration = int(round(sc.get("duration_seconds", 30)))
                break

        # Output asset file for this run
        image_file = run_visual_dir / f"scene_{scene_num}.png"
        video_file_str = None

        if source in ("repository", "landscape_repository"):
            if not Path(asset_path).exists():
                raise FileNotFoundError(
                    f"Local repository visual asset not found on disk: {asset_path} for deity '{scene_item.get('deity')}'"
                )
            if asset_type == "video":
                frame_ok = _extract_video_frame(Path(asset_path), image_file)
                if frame_ok:
                    image_file_str = str(image_file.absolute()).replace("\\", "/")
                    video_file_str = str(Path(asset_path).absolute()).replace("\\", "/")
                else:
                    # FFmpeg missing or extraction failure:
                    # If an existing genuine deity-specific image is available, use normal image fallback.
                    # Otherwise fail the scene safely.
                    deity = scene_item.get("deity") or ""
                    fallback_img = _find_genuine_deity_image(deity, scene_num=scene_num, content_type=content_type or "short")
                    if fallback_img and fallback_img.exists() and fallback_img.stat().st_size > 0:
                        image_file_str = str(fallback_img.absolute()).replace("\\", "/")
                        video_file_str = None
                        asset_type = "image"
                    else:
                        raise RuntimeError(
                            f"FFmpeg frame extraction failed for video asset: {asset_path} "
                            f"and no genuine fallback image exists for deity '{deity}'"
                        )
            else:
                image_file_str = str(Path(asset_path).absolute()).replace("\\", "/")
        else:
            # Fallback to provider image synthesis ONLY in test/mock mode
            if provider_name != "mock":
                raise RuntimeError(
                    f"External or synthesized visual assets are strictly prohibited in production. "
                    f"Asset source: '{source}', path: '{asset_path}'"
                )
            prompt = f"Scene {scene_num} for {script['title']}"
            provider.generate_image(prompt, style_preset, image_file)
            image_file_str = str(image_file.absolute()).replace("\\", "/")
            if asset_type == "video":
                if Path(asset_path).exists():
                    video_file_str = str(Path(asset_path).absolute()).replace("\\", "/")
                else:
                    mock_vid = run_visual_dir / f"scene_{scene_num}.mp4"
                    mock_vid.write_text("MOCK_MP4_VIDEO", encoding="utf-8")
                    video_file_str = str(mock_vid.absolute()).replace("\\", "/")

        v_prompt = f"{visual_ref} (Scene #{scene_num}: {asset_type} asset from {source})" if visual_ref else f"Scene #{scene_num}: {asset_type} asset from {source}"

        visual_scenes.append({
            "scene": scene_num,
            "visual_prompt": v_prompt,
            "image_file": image_file_str,
            "video_file": video_file_str,
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
    format: str | None = None,
    content_type: str | None = None,
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
        format=format,
        content_type=content_type,
    )

    # Persist the mapping JSON
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_file = output_dir / f"visual_map_{timestamp}.json"

    out_file.write_text(
        json.dumps(visual_map, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    return out_file
