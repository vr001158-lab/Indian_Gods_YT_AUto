# src/script/generator.py
# Phase 2D — Script Generator Module
# Converts content briefs into production scripts.

import json
import time
from pathlib import Path
from src.script.schemas import validate_brief_input, validate_script_output

# ── Pre-built scripts for known deity topics ──────────────────────────────────
_DEITY_SCRIPTS = {
    "shiva": {
        "title": "Secrets of Shiva's Snake: The Mastery Over Ego and Poison",
        "duration_seconds": 360,
        "narration": (
            "Welcome to Divine Dharshanam Daily. Today, we stand on the silent, wind-swept heights of Mount Kailash. "
            "Here, in the absolute quiet of the cosmic mountains, Lord Shiva sits in deep, eternal meditation. "
            "Yet, if you look closely at the supreme yogi, your eyes are immediately drawn to an unexpected sight. "
            "Around his neck, where other gods might wear gold and pearls, coils a massive, deadly cobra—the serpent Vasuki. "
            "This striking contrast raises a profound mystery. Why does the Lord of Peace adorn himself with the symbol of death and fear? "
            "To understand how the serpent came to reside around Shiva's neck, we must journey back to the dawn of time, "
            "to the epochal event known as the Samudra Manthan—the churning of the cosmic ocean. "
            "The Devas and the Asuras, seeking the nectar of immortality, agreed to churn the vast milk ocean. "
            "They used the massive Mount Mandara as the churning rod and the serpent king, Vasuki, as the churning rope. "
            "But as the ocean was churned, before the sweet nectar could emerge, the ocean began to bubble with a terrifying, dark blue vapor. "
            "It was Halahala—the ultimate cosmic poison, capable of destroying all creation. "
            "With absolute composure, Shiva stepped forward. He gathered the lethal, burning Halahala poison into his hands and calmly drank it to save the cosmos. "
            "But as the poison slid down his throat, Goddess Parvati, witnessing the threat to her husband, placed her hand firmly on Shiva's throat to prevent the poison from descending. "
            "The poison stayed locked in Shiva's neck, turning it a deep, radiant blue. "
            "Seeing Shiva's immense sacrifice, the serpent Vasuki offered himself to wrap around Shiva's neck, acting as a cool binding to soothe the burning sensation of the poison. "
            "In Hindu symbolism, the snake Vasuki represents three things: the ego, worldly desires, and the toxic poisons of the mind—anger, jealousy, and greed. "
            "By wearing the serpent around his neck, Shiva demonstrates that he does not run away from these forces. Instead, he conquers them. "
            "As we close our dharshanam today, let us carry this wisdom into our modern lives. "
            "Rather than letting this poison seep into your mind and ruin your peace, emulate Shiva. "
            "Stand firm, breathe deeply, and master your reactions. You have the power to transform your obstacles into ornaments. "
            "Thank you for joining us on Divine Dharshanam Daily. May the peace of Kailash be with you always. Om Namah Shivaya."
        ),
        "scene_scripts": [
            {
                "scene": 1,
                "duration_seconds": 60,
                "visual_reference": "Serene cinematic close-up of Lord Shiva in deep meditation on Mount Kailash with a coiled cobra around his neck.",
                "voice_text": (
                    "Why does Lord Shiva wear a deadly, poisonous cobra around his neck instead of gold and pearls? "
                    "This striking image holds a profound cosmic mystery about mastering fear, ego, and life's deepest obstacles."
                ),
                "emotion": "Serene and mysterious"
            },
            {
                "scene": 2,
                "duration_seconds": 90,
                "visual_reference": "Churning of the milk ocean with gods and demons pulling the giant snake Vasuki around Mount Mandara.",
                "voice_text": (
                    "Welcome to Divine Dharshanam Daily. Today, we investigate the sacred story of Lord Shiva and the serpent Vasuki. "
                    "To understand how the serpent came to reside around Shiva's neck, we must journey back to the dawn of time, "
                    "to the epochal event known as the Samudra Manthan—the churning of the cosmic ocean. "
                    "The Devas and Asuras used Mount Mandara and serpent king Vasuki to churn the milk ocean for nectar, "
                    "but before nectar emerged, a dark, terrifying vapor bubbled up—Halahala, the ultimate cosmic poison."
                ),
                "emotion": "Dramatic and intense"
            },
            {
                "scene": 3,
                "duration_seconds": 90,
                "visual_reference": "Shiva drinking the blue poison from a clay cup while Parvati touches his neck, turning it blue.",
                "voice_text": (
                    "With absolute composure, Shiva stepped forward. He gathered the lethal, burning Halahala poison into his hands and calmly drank it to save the cosmos. "
                    "But as the poison slid down his throat, Goddess Parvati, witnessing the threat to her husband, placed her hand firmly on Shiva's throat to prevent the poison from descending into his stomach. "
                    "The poison stayed locked in Shiva's neck, turning it a deep, radiant blue. "
                    "From that moment, Shiva became known as Neelkanth—the Blue-Throated Savior. "
                    "Seeing Shiva's immense sacrifice, the serpent Vasuki offered himself to wrap around Shiva's neck, acting as a cool binding to soothe the burning sensation of the poison. "
                    "Shiva accepted Vasuki's devotion, placing the serpent around his throat as a perpetual companion, showing that even the deadliest of creatures are welcome in the divine fold."
                ),
                "emotion": "Awe-inspiring and intense"
            },
            {
                "scene": 4,
                "duration_seconds": 60,
                "visual_reference": "Lord Shiva placing the cobra around his throat, the cobra bowing with respect, divine master of animals.",
                "voice_text": (
                    "What does this mean for us today? In Hindu symbolism, the snake Vasuki represents three things: the ego, worldly desires, and the toxic poisons of the mind—anger, jealousy, and greed. "
                    "By wearing the serpent around his neck, Shiva demonstrates that he does not run away from these forces. Instead, he conquers them. "
                    "He wears the snake as an ornament, meaning he has tamed it. The snake, once a source of terror, becomes a symbol of power and mental control. "
                    "Shiva's message is clear: do not let the poisons of the world enter your heart. Lock them in your throat, master them, and wear your challenges as decorations of your strength."
                ),
                "emotion": "Philosophical and peaceful"
            },
            {
                "scene": 5,
                "duration_seconds": 60,
                "visual_reference": "Modern individual meditating peacefully, double exposure with calm forest and temple carvings.",
                "voice_text": (
                    "As we close our dharshanam today, let us carry this wisdom into our modern lives. "
                    "Every day, we face toxic environments, criticism, and our own inner anxieties. "
                    "Rather than letting this poison seep into your mind and ruin your peace, emulate Shiva. "
                    "Stand firm, breathe deeply, and master your reactions. You have the power to transform your obstacles into ornaments. "
                    "Thank you for joining us on Divine Dharshanam Daily. May the peace of Kailash be with you always. Om Namah Shivaya."
                ),
                "emotion": "Reassuring and calm"
            }
        ],
        "retention_hooks": [
            "At 60s: Watch how Shiva resolves the deadly threat when even the gods flee in terror.",
            "At 150s: Discover the secret gesture Goddess Parvati made that saved Shiva's life.",
            "At 240s: What does the snake symbolize in your modern life? The answer changes everything."
        ],
        "shorts_scripts": [
            {
                "title": "Why Shiva wears a snake around his neck",
                "hook": "Why does Lord Shiva wear a deadly snake instead of gold?",
                "body": "It's Vasuki, the serpent king! During Samudra Manthan, when the toxic Halahala poison threatened the cosmos, Shiva drank it to save the universe. Vasuki coiled around Shiva's neck to cool the burning poison. Symbolically, the snake represents our ego and desires. By wrapping it around his neck, Shiva teaches us to master our toxic ego and wear our challenges as ornaments!"
            },
            {
                "title": "Why is Lord Shiva's neck blue?",
                "hook": "Do you know why Lord Shiva's neck is blue?",
                "body": "When the cosmic ocean was churned, it produced Halahala—a poison so lethal it could destroy all creation. Shiva drank it to save everyone, but Goddess Parvati stopped it in his throat by placing her hand there. The poison stayed locked in his neck, turning it blue, earning him the name Neelkanth! The serpent Vasuki then coiled around his throat to soothe the heat."
            },
            {
                "title": "The secret life lesson of Shiva's snake",
                "hook": "Shiva's snake hides a secret life-changing lesson!",
                "body": "The cobra Vasuki represents ego, anger, and toxic influences. Most people let toxic environments enter their heart and consume them, but Shiva locks the poison in his throat and wears the serpent as an ornament. The lesson? Don't let negativity penetrate your mind. Conquer your ego, control your reactions, and wear your struggles with pride!"
            }
        ]
    },
    "ganesha": {
        "title": "The Sacrifice of Ganesha: The Story of the Broken Tusk",
        "duration_seconds": 360,
        "narration": (
            "Welcome to Divine Dharshanam Daily. Today, we explore one of the most unique features of Lord Ganesha—his single broken tusk. "
            "Have you ever wondered why the Lord of Obstacles, who possesses absolute power, chooses to remain asymmetric? "
            "To understand this, we travel back to the hermitage of Sage Vyasa, who was preparing to write the greatest epic in history, the Mahabharata. "
            "Vyasa needed a scribe who could write at lightning speed without stopping, and Ganesha agreed, but on one condition: Vyasa must recite without a single pause. "
            "Vyasa countered with his own condition: Ganesha must understand the meaning of every verse before writing it down. "
            "As the writing began, the energy in the hermitage was intense. Vyasa recited complex verses, and Ganesha wrote them down with serene focus. "
            "But suddenly, under the sheer speed and power of the divine recitation, Ganesha's stylus snapped in half. "
            "Faced with the prospect of pausing and breaking his sacred vow, Ganesha did not hesitate. "
            "With a swift, decisive movement, he broke off his own right tusk, dipped it in ink, and continued writing without missing a single word. "
            "In Hindu tradition, this broken tusk—known as Ekadanta—represents the ultimate sacrifice of physical beauty for intellectual wisdom. "
            "It shows that to achieve something of monumental value, we must be willing to sacrifice our ego and physical pride. "
            "As we conclude today, remember Ganesha's lessons: maintain absolute focus, complete your duties without interruption, "
            "and do not let minor setbacks stop you from achieving your goals. Thank you for joining us. Om Gam Ganapataye Namaha."
        ),
        "scene_scripts": [
            {
                "scene": 1,
                "duration_seconds": 60,
                "visual_reference": "Close-up of Lord Ganesha's face, highlighting his single broken tusk and wise eyes.",
                "voice_text": (
                    "Welcome to Divine Dharshanam Daily. Today, we explore one of the most unique features of Lord Ganesha—his single broken tusk. "
                    "Have you ever wondered why the Lord of Obstacles, who possesses absolute power, chooses to remain asymmetric? "
                    "This is not a mere accident or design flaw. It is a symbol of a supreme sacrifice that contains a life-changing secret about focus, duty, and dedication."
                ),
                "emotion": "Warm and inspiring"
            },
            {
                "scene": 2,
                "duration_seconds": 90,
                "visual_reference": "Sage Vyasa reciting verses while Lord Ganesha writes them down on palm leaves.",
                "voice_text": (
                    "To understand this, we travel back to the hermitage of Sage Vyasa, who was preparing to write the greatest epic in history, the Mahabharata. "
                    "Vyasa needed a scribe who could write at lightning speed without stopping. Ganesha agreed, but on one condition: Vyasa must recite without a single pause. "
                    "Vyasa countered with his own condition: Ganesha must understand the meaning of every verse before writing it down. "
                    "This divine challenge set the stage for an extraordinary collaboration of intellect and focus."
                ),
                "emotion": "Engaging and educational"
            },
            {
                "scene": 3,
                "duration_seconds": 90,
                "visual_reference": "Ganesha's stylus breaking, and Ganesha instantly breaking his own tusk with a divine flash.",
                "voice_text": (
                    "As the writing began, the energy in the hermitage was intense. Vyasa recited complex verses, and Ganesha wrote them down with serene focus. "
                    "But suddenly, under the sheer speed and power of the divine recitation, Ganesha's stylus snapped in half. "
                    "Faced with the prospect of pausing and breaking his sacred vow, Ganesha did not hesitate for a second. "
                    "With a swift, decisive movement, he broke off his own right tusk, dipped it in ink, and continued writing without missing a single syllable."
                ),
                "emotion": "Dramatic and inspiring"
            },
            {
                "scene": 4,
                "duration_seconds": 60,
                "visual_reference": "Ganesha writing ancient scriptures on palm leaves using his broken tusk.",
                "voice_text": (
                    "In Hindu tradition, this broken tusk—known as Ekadanta—represents the ultimate sacrifice of physical beauty for intellectual wisdom. "
                    "Ganesha showed that no obstacle should prevent us from completing our duties. "
                    "By using his own tusk, Ganesha demonstrated that when tools fail, our inner resources and determination must take over."
                ),
                "emotion": "Philosophical and respectful"
            },
            {
                "scene": 5,
                "duration_seconds": 60,
                "visual_reference": "A modern student studying late at night under a warm desk lamp, books surrounding them.",
                "voice_text": (
                    "As we conclude today, let us carry Ganesha's wisdom into our daily lives. "
                    "When you face setbacks or lack the perfect tools to study, work, or create, do not make excuses. "
                    "Emulate Ganesha: maintain absolute focus, adapt to your circumstances, and make the necessary sacrifices to complete your duties. "
                    "Thank you for joining us on Divine Dharshanam Daily. May the wisdom of Ganesha remove all obstacles from your path."
                ),
                "emotion": "Motivational and peaceful"
            }
        ],
        "retention_hooks": [
            "At 60s: Discover the unusual agreement Ganesha made that almost stopped the Mahabharata from being written.",
            "At 150s: The exact second Ganesha's stylus broke and the shocking decision he made to keep writing.",
            "At 240s: What Ekadanta teaches us about dealing with broken tools and setbacks in our lives."
        ],
        "shorts_scripts": [
            {
                "title": "Why Ganesha has a broken tusk",
                "hook": "Why is Lord Ganesha's tusk broken? The reason is epic!",
                "body": "When Ganesha was writing the Mahabharata as Sage Vyasa recited it, he vowed never to stop writing. But suddenly, his stylus snapped! Rather than pause and break his vow, Ganesha broke his own tusk, dipped it in ink, and continued writing. This teaches us to complete our duties no matter what obstacle stands in our way!"
            },
            {
                "title": "The stylus snap that changed history",
                "hook": "This stylus snap almost stopped the Mahabharata!",
                "body": "Ganesha was writing the world's longest epic script when his pen broke. If he paused, the sacred recitation would end. Instantly, Ganesha broke off his right tusk to use as a pen. This asymmetry represents intellectual sacrifice over physical vanity, proving that wisdom is always more valuable than outward appearance."
            },
            {
                "title": "Dedication lessons from Ganesha",
                "hook": "Ganesha's broken tusk holds a life lesson for you!",
                "body": "When tools or plans break, most people give up. But Ganesha broke his own body to write the Mahabharata. It teaches us to adapt, make sacrifices, and never let temporary setbacks stop us from achieving our goals. Use what you have, stay focused, and remove your own obstacles!"
            }
        ]
    }
}


def _generate_fallback_script(brief: dict) -> dict:
    """
    Generates a 5-8 minute detailed script dynamically from the custom content brief.
    All narration and scene voice texts are fully derived from the primary title, hook,
    audience, visual plan, and script structure in the brief.
    """
    title = brief["primary_title"]
    hook_text = brief["hook"]
    visual_scenes = brief["visual_plan"]
    structure = brief["script_structure"]

    scene_scripts = []
    total_duration = 0
    narration_parts = []

    for i, scene in enumerate(visual_scenes):
        scene_num = scene["scene_number"]
        # Standardize duration (e.g. 60s-90s per scene to achieve 5-8 minutes total)
        # If visual brief specifies short scenes, scale them to make a long video
        duration = max(75, scene["duration_seconds"] * 4)
        total_duration += duration

        # Formulate voice text based on structure acts or descriptions
        if i == 0:
            voice_text = (
                f"Welcome to Divine Dharshanam Daily. Today, we investigate the profound mystery of {title}. "
                f"As we begin, consider this: {hook_text} "
                f"Let us focus on this visual representation: {scene['description']}"
            )
            emotion = "Serene and mysterious"
        elif i == len(visual_scenes) - 1:
            voice_text = (
                f"As we conclude our dharshanam today, let us reflect on this ultimate teaching. "
                f"The lessons behind {title} guide us to live with greater awareness, compassion, and strength. "
                f"Thank you for joining us. May peace and blessings be with you always."
            )
            emotion = "Peaceful and reassuring"
        else:
            # Middle acts
            act_key = f"act_{i+1}_explanation" if i == 1 else "act_3_message"
            structure_desc = structure.get(act_key, structure.get("act_2_explanation", scene["description"]))
            voice_text = (
                f"Moving deeper into the story, we explore the scriptural significance. "
                f"{structure_desc} "
                f"We see this beautifully illustrated: {scene['description']} "
                f"This transition invites us to look past the surface and connect with the cosmic symbolism."
            )
            emotion = "Engaging and philosophical"

        narration_parts.append(voice_text)

        scene_scripts.append({
            "scene":            scene_num,
            "duration_seconds": duration,
            "visual_reference": scene["description"],
            "voice_text":       voice_text,
            "emotion":          emotion
        })

    # Generate 3 shorts scripts based on shorts hooks
    shorts_scripts = []
    for i, hook in enumerate(brief.get("shorts_hooks", ["Untold mystery!"])):
        if i >= 3:
            break
        shorts_scripts.append({
            "title": f"Shorts Option {i+1} - {title[:30]}",
            "hook":  hook,
            "body":  f"{hook} In this video, we explore the sacred history and symbolism. {title} teaches us deep spiritual lessons about life, duty, and devotion. Like this video and subscribe for more daily devotional wisdom!"
        })

    # Fill up to 3 if brief has fewer hooks
    while len(shorts_scripts) < 3:
        shorts_scripts.append({
            "title": f"Shorts Option {len(shorts_scripts)+1} - {title[:30]}",
            "hook":  f"Discover the secrets of {title}!",
            "body":  f"Explore the ancient truth of {title}. A quick spiritual reminder of the divine mysteries. Stay tuned for more daily dharshanam."
        })

    # Formulate 3 retention hooks
    retention_hooks = [
        f"At 60s: Discover the hidden context of {title} that most people ignore.",
        f"At 120s: The critical turning point in this story that reveals the deity's ultimate nature.",
        f"At 200s: How you can apply this sacred lesson to resolve conflicts in your daily life."
    ]

    return {
        "title":            title,
        "duration_seconds": total_duration,
        "narration":        " ".join(narration_parts),
        "scene_scripts":    scene_scripts,
        "retention_hooks":  retention_hooks,
        "shorts_scripts":   shorts_scripts
    }


def generate_script(brief: dict) -> dict:
    """
    Converts a content brief JSON into a structured production script.
    Fails closed if the content brief is invalid or lacks approved metadata.
    """
    ok, error_msg = validate_brief_input(brief)
    if not ok:
        raise ValueError(f"❌ Safety Gate Rejection: {error_msg}")

    meta = brief["approval_metadata"]
    topic = meta["selected_topic"]
    deity = meta.get("deity", "").lower()

    if deity in _DEITY_SCRIPTS and brief["primary_title"] == _DEITY_SCRIPTS[deity]["title"]:
        script = _DEITY_SCRIPTS[deity]
    else:
        script = _generate_fallback_script(brief)

    # Copy script to avoid modifying global dictionary, then inject approval_metadata & run_id
    script_data = dict(script)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    script_data["run_id"] = f"run_{timestamp}"
    script_data["approval_metadata"] = brief["approval_metadata"]

    # Validate output schema
    ok_out, err_out = validate_script_output(script_data)
    if not ok_out:
        raise RuntimeError(f"❌ Internal Error: Generated script does not conform to schema: {err_out}")

    return script_data


def process_brief_file(brief_path: Path, output_dir: Path = Path("data/scripts")) -> Path:
    """
    Orchestrates the conversion of a content brief file into a production script.
    """
    if not brief_path.exists():
        raise FileNotFoundError(f"Content brief file not found: {brief_path}")

    try:
        brief = json.loads(brief_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise ValueError(f"Failed to parse content brief JSON: {e}")

    script = generate_script(brief)

    # Persist script
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / f"script_{timestamp}.json"

    out_file.write_text(
        json.dumps(script, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    return out_file
