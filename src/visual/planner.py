# src/visual/planner.py
# Phase 2F — Visual Planner Module
# Converts scene scripts into structured visual plans mapping prompts and styles.


def plan_visuals(script: dict, style_preset: str = "Devotional Cinematic Painting, 8k, divine golden glow") -> list:
    """
    Converts scene scripts from a production script into structured visual plans.

    Parameters
    ----------
    script       : dict — production script JSON
    style_preset : str  — style preset description

    Returns
    -------
    list — list of scene visual plan dicts.
    """
    planned_scenes = []

    for item in script["scene_scripts"]:
        scene_num = item["scene"]
        visual_ref = item["visual_reference"]
        duration = item["duration_seconds"]

        # Formulate rich visual prompt combining reference with the target style preset
        visual_prompt = f"{visual_ref.rstrip('.')}, {style_preset}."

        planned_scenes.append({
            "scene":            scene_num,
            "visual_prompt":    visual_prompt,
            "style":            style_preset,
            "duration_seconds": duration
        })

    return planned_scenes
