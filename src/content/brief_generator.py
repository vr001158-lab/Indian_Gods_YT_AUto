# src/content/brief_generator.py
# Phase 2C — Content Brief Generator
# Converts approved topics into detailed content blueprints.

import json
from pathlib import Path
from src.content.schemas import validate_decision_input, validate_brief_output

# ── Pre-built templates for known deity topics ────────────────────────────────
_DEITY_BLUEPRINTS = {
    "shiva": {
        "title_options": [
            "Why Does Lord Shiva Wear a Snake Around His Neck?",
            "The Cosmic Mystery of Shiva's Snake Vasuki Explained",
            "Why Shiva Chose the Poisonous Serpent: Untold Story",
            "The Deeper Meaning Behind Lord Shiva's Snake Vasuki",
            "Secrets of Shiva's Snake: The Mastery Over Ego and Poison"
        ],
        "primary_title": "Secrets of Shiva's Snake: The Mastery Over Ego and Poison",
        "hook": "Have you ever wondered why the supreme yogi, Lord Shiva, wears a deadly serpent around his neck instead of gold? This is not just an ornament; it holds a cosmic secret that can transform how you handle poison in your own life.",
        "audience": "Devotional viewers, mythology enthusiasts, spiritual seekers looking for life lessons.",
        "story_arc": [
            "Act 1: The visual mystery of Shiva adorned with the deadly serpent Vasuki.",
            "Act 2: The story of Samudra Manthan, the Halahala poison, and why Vasuki coils around Shiva's neck.",
            "Act 3: The profound life lesson of neutralizing toxic energy and mastering one's own ego."
        ],
        "script_structure": {
            "act_1_opening": "Contrast the serene, meditative posture of Lord Shiva with the deadly, coiled cobra around his neck.",
            "act_2_explanation": "Recount the Samudra Manthan cosmic churning. Shiva drinks the toxic Halahala poison, and Parvati stops it in his throat. Vasuki offers himself to wrap around his neck, acting as a cool binding.",
            "act_3_message": "Explain the symbolism: the snake represents the ego and poison of worldly desires. Mastering the snake means wearing challenges as ornaments instead of letting them consume you."
        },
        "visual_plan": [
            {
                "scene_number": 1,
                "duration_seconds": 15,
                "description": "Serene cinematic close-up of Lord Shiva in deep meditation on Mount Kailash with a coiled cobra around his neck.",
                "image_prompt": "Cinematic close-up of meditating Lord Shiva, blue neck, coiled cobra snake Vasuki, majestic Mount Kailash snow background, warm divine golden light, highly detailed, photorealistic, 8k resolution",
                "video_prompt": "Serene camera panning slowly around meditating Lord Shiva, a coiled cobra gently raising its hood, ambient divine mist on Mount Kailash"
            },
            {
                "scene_number": 2,
                "duration_seconds": 20,
                "description": "The churning of the cosmic ocean (Samudra Manthan) with devas and asuras pulling the serpent Vasuki.",
                "image_prompt": "Samudra Manthan cosmic ocean churning, devas and asuras pulling giant serpent Vasuki, Mount Mandara spinning in center, epic proportions, high fantasy art style, dramatic lighting",
                "video_prompt": "Epic wide shot of devas and asuras pulling a giant snake in a swirling ocean, water spraying, Mount Mandara spinning in center"
            },
            {
                "scene_number": 3,
                "duration_seconds": 25,
                "description": "Lord Shiva calmly drinking the blue Halahala poison while Goddess Parvati places her hand on his throat.",
                "image_prompt": "Lord Shiva drinking shining blue liquid poison Halahala from a small clay cup, Goddess Parvati placing hand on his neck, divine dramatic lighting, intense emotional scene, highly detailed",
                "video_prompt": "Slow motion shot of Lord Shiva drinking glowing blue nectar, Goddess Parvati touching his throat which starts to glow blue, divine aura"
            },
            {
                "scene_number": 4,
                "duration_seconds": 15,
                "description": "Lord Shiva placing the serpent Vasuki around his neck, the cobra bowing in absolute devotion.",
                "image_prompt": "Lord Shiva placing a glowing green-scaled cobra around his blue throat, the cobra bowing with respect, divine master of animals, peaceful expression, detailed",
                "video_prompt": "Lord Shiva smiling and placing a majestic cobra around his neck, the cobra bowing its head, golden sparks flying"
            },
            {
                "scene_number": 5,
                "duration_seconds": 15,
                "description": "A modern individual meditating calmly in a chaotic environment, symbolizing mental mastery.",
                "image_prompt": "A serene modern person meditating in a double exposure with a calm forest, representing mental mastery over city chaos, soft morning light, peaceful, symbolic",
                "video_prompt": "Transition from busy city traffic to a calm meditating person breathing slowly, ambient peaceful glow"
            }
        ],
        "voice_direction": {
            "tone": "Respectful, mysterious, and deeply philosophical.",
            "speed": "Measured and steady (approx. 130 words per minute).",
            "emotion": "Calm, awe-inspiring, and reassuring.",
            "language_style": "Poetic yet clear English, with Sanskrit terms explained simply."
        },
        "shorts_hooks": [
            "Why does Shiva wear a deadly snake? The truth will shock you!",
            "This is why Lord Shiva's neck is blue and wrapped in a serpent!",
            "The secret life lesson hidden behind Shiva's snake Vasuki."
        ],
        "seo_metadata": {
            "description": "Explore the cosmic mystery of why Lord Shiva wears the serpent Vasuki around his neck. Discover the story of Samudra Manthan, Halahala poison, and the profound spiritual lesson on mastering ego and toxic desires in your daily life.",
            "keywords": ["Lord Shiva", "Shiva snake", "Vasuki", "Samudra Manthan", "Halahala poison", "Shiva blue throat", "Neelkanth story", "Shiva symbolism"],
            "hashtags": ["#LordShiva", "#ShivaSymbolism", "#SerpentVasuki", "#HinduMythology", "#SpiritualWisdom"],
            "category": "Education"
        }
    },
    "ganesha": {
        "title_options": [
            "Why Does Lord Ganesha Have a Broken Tusk?",
            "The Hidden Meaning Behind Ganesha's Single Tusk",
            "The Sacrifice of Ganesha: The Story of the Broken Tusk",
            "Secrets of Ganesha: Why the Elephant God Broke His Tusk",
            "The Story Behind Ganesha's Broken Tusk: A Lesson in Devotion"
        ],
        "primary_title": "The Sacrifice of Ganesha: The Story of the Broken Tusk",
        "hook": "Have you ever noticed that one of Lord Ganesha's tusks is broken? This is not an accident. It is the mark of a supreme sacrifice that contains a life-changing secret about focus and dedication.",
        "audience": "Devotional viewers, students, and mythology lovers looking for inspirational stories.",
        "story_arc": [
            "Act 1: The visual detail of Ganesha's single broken tusk.",
            "Act 2: The story of writing the Mahabharata with sage Vyasa and how Ganesha broke his own tusk to use as a pen when his pen failed.",
            "Act 3: The lesson of making sacrifices to acquire wisdom and completing duties without interruption."
        ],
        "script_structure": {
            "act_1_opening": "Show a beautifully detailed idol of Ganesha, focusing on the asymmetry of his tusks.",
            "act_2_explanation": "Explain the agreement between Vyasa and Ganesha: Ganesha would write the Mahabharata continuously, but only if he understood every verse. When his stylus broke, Ganesha did not stop; he broke his tusk to continue.",
            "act_3_message": "Highlight the symbolic lesson: Wisdom requires sacrifices, and no obstacle should prevent us from completing our duties."
        },
        "visual_plan": [
            {
                "scene_number": 1,
                "duration_seconds": 15,
                "description": "Close-up of Lord Ganesha's face, highlighting his single broken tusk and wise eyes.",
                "image_prompt": "Cinematic close-up of Lord Ganesha face, detailing single broken tusk, warm temple lighting, golden ornaments, highly detailed, photorealistic, 8k resolution",
                "video_prompt": "Camera slowly sliding to reveal Ganesha face with the broken tusk, glowing diya lamps in background"
            },
            {
                "scene_number": 2,
                "duration_seconds": 20,
                "description": "Sage Vyasa reciting verses while Lord Ganesha writes them down on palm leaves.",
                "image_prompt": "Sage Vyasa reciting verses with beard and white robes, Lord Ganesha writing on palm leaf scrolls inside a quiet hermitage, mystical ancient India, soft morning light",
                "video_prompt": "Slow camera pan across ancient hermitage showing Ganesha writing intently with focus"
            },
            {
                "scene_number": 3,
                "duration_seconds": 20,
                "description": "Ganesha's stylus breaking, and Ganesha instantly breaking his own tusk with a divine flash.",
                "image_prompt": "Close-up of Ganesha wooden pen breaking in half, Ganesha breaking his own right tusk with a bright flash of golden light, determination in his eyes, detailed",
                "video_prompt": "A sudden snap of a stylus, Ganesha's hand moving to his tusk, a bright golden flash of divine energy"
            },
            {
                "scene_number": 4,
                "duration_seconds": 15,
                "description": "Ganesha continuing to write the epic Mahabharata with his broken tusk.",
                "image_prompt": "Ganesha writing ancient scriptures on palm leaves using his broken tusk, golden ink glowing, serene focus, highly detailed, mythological art style",
                "video_prompt": "Ganesha writing at lightning speed, characters glowing on the page, divine aura around him"
            },
            {
                "scene_number": 5,
                "duration_seconds": 20,
                "description": "A student studying late at night under a lamp, symbolizing dedication.",
                "image_prompt": "A modern student studying late at night under a warm desk lamp, books surrounding them, double exposure with Ganesha writing, symbolizing focus and dedication",
                "video_prompt": "Glow of a study lamp, student turning a page with focus, transition to temple bell"
            }
        ],
        "voice_direction": {
            "tone": "Warm, inspiring, and educational.",
            "speed": "Steady and engaging (approx. 135 words per minute).",
            "emotion": "Motivational and respectful.",
            "language_style": "Accessible English with clear moral lessons."
        },
        "shorts_hooks": [
            "Why is Ganesha's tusk broken? The secret story of Mahabharata!",
            "Ganesha broke his own tusk for THIS reason!",
            "The incredible lesson behind Ganesha's broken tusk."
        ],
        "seo_metadata": {
            "description": "Discover the true story of why Lord Ganesha has a broken tusk. Learn about his sacrifice while writing the Mahabharata with Sage Vyasa, and the spiritual lesson on absolute focus and commitment.",
            "keywords": ["Lord Ganesha", "broken tusk", "Ganesha story", "Mahabharata writer", "Sage Vyasa", "Ekadanta story", "Ganesha symbolism", "Hindu mythology lessons"],
            "hashtags": ["#Ganesha", "#BrokenTusk", "#Mahabharata", "#DevotionalStories", "#SpiritualSacrifice"],
            "category": "Education"
        }
    }
}


def _generate_fallback_brief(topic: str, deity: str, category: str, suggested_angle: str) -> dict:
    """
    Dynamically generates a content brief for any topic not in the pre-built registry.
    Ensures output is clean, respectful, and fully compliant with the brief schema.
    """
    # Normalize deity/subject name for display
    subject = deity.title() if deity else "the Divine"

    title_options = [
        f"The Untold Mystery of {topic}",
        f"Why {topic}: The Deeper Meaning Revealed",
        f"Secrets of {subject}: The Story Behind {topic}",
        f"The Spiritual Lesson Behind {topic}",
        f"What {topic} Teaches Us About Life"
    ]
    primary_title = title_options[2]

    hook = (
        f"Have you ever contemplated the deep spiritual mystery of {topic}? "
        f"This ancient story is not just a legend; it contains a profound cosmic lesson "
        f"that remains highly relevant to our lives today."
    )

    story_arc = [
        f"Act 1: The visual and narrative mystery of {topic}.",
        f"Act 2: The mythological context and deeper symbolism behind this divine event.",
        f"Act 3: Practical life lessons and spiritual takeaways for the modern seeker."
    ]

    script_structure = {
        "act_1_opening": f"Set the scene of {topic}, establishing a tone of curiosity and respect.",
        "act_2_explanation": f"Detail the scriptural accounts of this event, analyzing the symbolism and suggested angle: {suggested_angle}.",
        "act_3_message": f"Conclude with a moral lesson on how we can apply this divine quality of {subject} in our own challenges."
    }

    visual_plan = [
        {
            "scene_number": 1,
            "duration_seconds": 15,
            "description": f"An opening cinematic shot introducing the main deity, {subject}, surrounded by divine light.",
            "image_prompt": f"Cinematic painting of Lord {subject}, radiant glowing aura, ancient temple mandir background, highly detailed, devotional art style, 8k resolution",
            "video_prompt": f"Slow camera zoom into a majestic representation of Lord {subject}, glowing sparks floating in the air, serene atmosphere"
        },
        {
            "scene_number": 2,
            "duration_seconds": 20,
            "description": f"A scene depicting the historical or mythological events associated with {topic}.",
            "image_prompt": f"Mythological illustration depicting {topic}, dramatic epic skies, traditional colors, detailed clothing and expressive faces, high fantasy",
            "video_prompt": f"Dynamic camera panning across a mythic landscape, clouds moving rapidly, soft divine glow"
        },
        {
            "scene_number": 3,
            "duration_seconds": 25,
            "description": f"The climax of the story, showing the resolution of the divine event.",
            "image_prompt": f"Divine resolution of {topic}, lord {subject} showing blessings, glowing celestial light, highly detailed digital painting, peaceful and majestic",
            "video_prompt": f"Celestial light bursting from the center, particles rising, slow motion shot of deity blessing"
        },
        {
            "scene_number": 4,
            "duration_seconds": 20,
            "description": f"Symbolic transition linking the mythological story to a modern reflection.",
            "image_prompt": f"Serene transition from ancient temple stone carvings to a modern person reflecting peacefully, soft evening sunset light, symbolic",
            "video_prompt": f"Slow fade from ancient carvings to soft golden hour sunrays reflecting on water, peaceful transition"
        }
    ]

    voice_direction = {
        "tone": "Respectful, warm, and meditative.",
        "speed": "Steady and deliberate (approx. 130 words per minute).",
        "emotion": "Awe-inspiring and peaceful.",
        "language_style": "Clear, poetic English, explaining traditional concepts simply."
    }

    shorts_hooks = [
        f"Do you know the secret behind {topic}?",
        f"The untold story of {subject} that will inspire you!",
        f"The deeper meaning of {topic} explained."
    ]

    seo_metadata = {
        "description": f"Explore the profound spiritual significance of {topic}. Discover the ancient story, symbolic meaning, and life lessons from {category}.",
        "keywords": [subject, topic, f"{subject} story", f"{subject} symbolism", "Hindu mythology", "spiritual story"],
        "hashtags": [f"#{subject}", f"#{category.replace(' ', '')}", "#DivineWisdom", "#MythologyExplained"],
        "category": "Education"
    }

    return {
        "title_options": title_options,
        "primary_title": primary_title,
        "hook": hook,
        "audience": "Devotional viewers, mythology enthusiasts, and seekers of spiritual wisdom.",
        "story_arc": story_arc,
        "script_structure": script_structure,
        "visual_plan": visual_plan,
        "voice_direction": voice_direction,
        "shorts_hooks": shorts_hooks,
        "seo_metadata": seo_metadata
    }


def generate_content_brief(decision: dict) -> dict:
    """
    Converts a validated decision JSON into a detailed content blueprint.

    Raises ValueError if input does not pass the safety gates.
    """
    ok, error_msg = validate_decision_input(decision)
    if not ok:
        raise ValueError(f"❌ Safety Gate Rejection: {error_msg}")

    topic = decision["selected_topic"]
    deity = decision.get("deity", "").lower()
    category = decision["category"]
    suggested_angle = decision["suggested_angle"]

    # Retrieve pre-built or generate fallback brief
    if deity in _DEITY_BLUEPRINTS:
        # Check if the topic matches or is similar to our pre-built deity profile
        # Use pre-built if appropriate, otherwise build fallback
        brief_data = dict(_DEITY_BLUEPRINTS[deity])
    else:
        brief_data = dict(_generate_fallback_brief(topic, deity, category, suggested_angle))

    # Inject approval metadata for downstream safety gating in script generator
    brief_data["approval_metadata"] = {
        "approved_for_generation": decision["approved_for_generation"],
        "selected_topic": decision["selected_topic"],
        "score": decision["score"],
        "confidence": decision["confidence"],
        "data_source": decision["data_source"],
        "category": decision["category"]
    }
    if decision.get("format"):
        brief_data["format"] = decision["format"]
    if decision.get("content_type"):
        brief_data["content_type"] = decision["content_type"]

    # Validate output structure
    ok_out, err_out = validate_brief_output(brief_data)
    if not ok_out:
        raise RuntimeError(f"❌ Internal Error: Generated brief does not conform to schema: {err_out}")

    return brief_data


def process_decision_file(decision_path: Path, output_dir: Path = Path("data/content_briefs")) -> Path:
    """
    Orchestrates the conversion of a decision file into a content brief file.
    """
    if not decision_path.exists():
        raise FileNotFoundError(f"Decision file not found: {decision_path}")

    try:
        decision = json.loads(decision_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise ValueError(f"Failed to parse decision JSON file: {e}")

    brief = generate_content_brief(decision)

    # Persist brief
    import time
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / f"content_brief_{timestamp}.json"
    
    out_file.write_text(
        json.dumps(brief, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )
    
    return out_file
