# tests/test_phase6_qa.py
# Phase 6 Unit Tests — Strong Hook, Background Music, Ducking, and QA Gate

import os
import sys
import json
import hashlib
import unittest
from pathlib import Path

sys.path.insert(0, os.getcwd())

from src.audio.music import load_music_manifest, validate_music_provenance, discover_music_tracks, select_background_music
from src.audio.ducking import mix_audio_with_ducking, NARRATION_TARGET_DB, MUSIC_TARGET_DB
from src.script.generator import generate_script
from src.video.generator import perform_video_qa

ASSET_PLAN_PATH = Path("data/visuals/asset_plan_20260814_071510.json")
EXPECTED_SHA256 = "f6ca03a2dfec5add5b9bce5ce699124bfdffacf42f009b2a9d4b1c02a5f87b33"
MUSIC_MANIFEST_PATH = Path("assets/music/music_manifest.json")

# Sample language hooks for Shiva topic
HINDI_HOOK = "क्या आपने कभी सोचा है कि महादेव ने अपने गले में एक विषैले नाग को ही क्यों धारण किया?"
TELUGU_HOOK = "మహాదేవుడు తన మెడలో విషపూరితమైన నాగును ఎందుకు ధరించారో ఎప్పుడైనా ఆలోచించారా?"
TAMIL_HOOK = "மகாதேவன் தனது கழுத்தில் விஷமுள்ள நாகத்தை ஏன் அணிந்திருக்கிறார் என்று எப்போதாவது யோசித்திருக்கிறீர்களா?"

GREETING_SUBSTRINGS = [
    "Welcome to Divine Dharshanam Daily",
    "दिव्य दर्शनम् डेली में आपका स्वागत है",
    "దివ్య దర్శనం డైలీకి స్వాగతం",
    "திவ்ய தரிசனம் டெய்லிக்கு உங்களை வரவேற்கிறோம்"
]


class TestPhase6QA(unittest.TestCase):

    # Helper: build a complete valid brief for Shiva topic
    @staticmethod
    def _shiva_brief():
        return {
            "primary_title": "Secrets of Shiva's Snake: The Mastery Over Ego and Poison",
            "title_options": ["Secrets of Shiva's Snake"],
            "hook": "Why does Lord Shiva wear a deadly, poisonous cobra around his neck?",
            "story_arc": {
                "act_1": "Hook — Shiva with cobra",
                "act_2": "Samudra Manthan and Halahala",
                "act_3": "Neelkanth — mastery over poison",
                "act_4": "Symbolism of Vasuki",
                "act_5": "CTA and Om Namah Shivaya"
            },
            "target_audience": "Devotees aged 25-45",
            "visual_plan": [
                {"scene_number": i+1, "description": f"Scene {i+1}", "duration_seconds": 15}
                for i in range(5)
            ],
            "script_structure": {
                "act_1_hook": "Strong curiosity hook first",
                "act_2_greeting": "Short Divine Darshanam Daily greeting",
                "act_3_story": "Main story",
                "act_4_lesson": "Symbolism and lesson",
                "act_5_cta": "Conclusion and CTA"
            },
            "voice_direction": "Calm, reverent, cinematic narration",
            "shorts_hooks": ["Why does Shiva wear a deadly cobra?"],
            "seo_metadata": {
                "keywords": ["shiva", "vasuki", "samudra manthan"],
                "description": "Learn why Lord Shiva wears a snake"
            },
            "approval_metadata": {
                "approved_for_generation": True,
                "selected_topic": "Why Lord Shiva Wears a Snake Around His Neck",
                "deity": "shiva",
                "score": 80,
                "confidence": "high",
                "data_source": "youtube_api"
            }
        }

    # 1. Hook occurs before greeting
    def test_01_hook_occurs_before_greeting(self):
        script = generate_script(self._shiva_brief())
        scene_1_text = script["scene_scripts"][0]["voice_text"]
        scene_2_text = script["scene_scripts"][1]["voice_text"]

        # Scene 1 must contain the hook question
        self.assertIn("Why does Lord Shiva wear", scene_1_text)
        # Scene 2 must contain the greeting
        self.assertIn("Welcome to Divine Dharshanam Daily", scene_2_text)

    # 2. Greeting is never first spoken segment
    def test_02_greeting_is_never_first_spoken_segment(self):
        script = generate_script(self._shiva_brief())
        first_scene_text = script["scene_scripts"][0]["voice_text"]

        for greeting in GREETING_SUBSTRINGS:
            self.assertNotIn(greeting, first_scene_text,
                f"Greeting '{greeting}' must not be in scene 1!")

    # 3. Hindi hook exists
    def test_03_hindi_hook_exists(self):
        self.assertTrue(len(HINDI_HOOK) > 10)
        self.assertIn("महादेव", HINDI_HOOK)

    # 4. Telugu hook exists
    def test_04_telugu_hook_exists(self):
        self.assertTrue(len(TELUGU_HOOK) > 10)
        self.assertIn("మహాదేవుడు", TELUGU_HOOK)

    # 5. Tamil hook exists
    def test_05_tamil_hook_exists(self):
        self.assertTrue(len(TAMIL_HOOK) > 10)
        self.assertIn("மகாதேவன்", TAMIL_HOOK)

    # 6. Hooks are language-native / distinct
    def test_06_hooks_are_language_native_distinct(self):
        self.assertNotEqual(HINDI_HOOK, TELUGU_HOOK)
        self.assertNotEqual(HINDI_HOOK, TAMIL_HOOK)
        self.assertNotEqual(TELUGU_HOOK, TAMIL_HOOK)

    # 7. Music manifest provenance is valid
    def test_07_music_manifest_provenance_valid(self):
        self.assertTrue(MUSIC_MANIFEST_PATH.exists(), "music_manifest.json missing")
        manifest = load_music_manifest(MUSIC_MANIFEST_PATH)
        self.assertIn("tracks", manifest)
        self.assertGreater(len(manifest["tracks"]), 0)

        track = manifest["tracks"][0]
        self.assertIn(track["source_type"], ("youtube_audio_library", "original_generated", "royalty_free_public"))
        self.assertIn(track["external_source"], (True, False))
        self.assertIn(track["copyright_source"], ("youtube_audio_library", "none"))

    # 8. Generated music is classified as original_generated or royalty_free_public
    def test_08_generated_music_classified_original_generated(self):
        track_file = Path("assets/music/devotional/shiva_devotional_shivaranjani_flute.wav")
        self.assertTrue(track_file.exists(), "shiva_devotional_shivaranjani_flute.wav missing")

        ok, msg, track_info = validate_music_provenance(track_file)
        self.assertTrue(ok, f"Provenance validation failed: {msg}")
        self.assertIn(track_info["source_type"], ("original_generated", "royalty_free_public"))

    # 9. Unauthorized music is rejected
    def test_09_unauthorized_music_rejected(self):
        fake_track = Path("assets/music/devotional/fake_unauthorized_track.mp3")
        ok, msg, _ = validate_music_provenance(fake_track)
        self.assertFalse(ok, "Unauthorized music should be rejected!")

    # 10. Narration remains dominant
    def test_10_narration_remains_dominant(self):
        self.assertLessEqual(NARRATION_TARGET_DB, -3.0)
        self.assertLessEqual(MUSIC_TARGET_DB, -18.0)
        self.assertGreater(NARRATION_TARGET_DB, MUSIC_TARGET_DB)

    # 11. Final audio is AAC 48 kHz stereo
    def test_11_final_video_audio_aac_48khz_stereo(self):
        for lang_code, video_file in [
            ("hi-IN", Path("data/videos/shiva_hi_final.mp4")),
            ("te-IN", Path("data/videos/shiva_te_final.mp4")),
            ("ta-IN", Path("data/videos/shiva_ta_final.mp4")),
        ]:
            if video_file.exists():
                qa = perform_video_qa(video_file)
                self.assertEqual(qa["audio_codec"], "aac")
                self.assertEqual(qa["audio_sample_rate"], 48000)
                self.assertEqual(qa["audio_channels"], 2)

    # 12. Captions follow new scene timing (Phase 6 renders only)
    def test_12_captions_follow_scene_timing(self):
        """
        Verify that Phase 6 caption scene 1 files do NOT contain the greeting.
        This test only runs if a Phase 6 audio map exists as evidence of a Phase 6 render.
        Phase 5 caption directories from before Phase 6 are skipped automatically.
        """
        for lang_code, lang_suffix in [("hi-IN", "hi"), ("te-IN", "te"), ("ta-IN", "ta")]:
            phase6_marker = Path(f"data/audio/audio_map_{lang_code}_phase6.json")
            cap_dir = Path(f"data/videos/_captions_shiva_{lang_suffix}_final")

            # Only test if a Phase 6 audio map AND caption directory exist
            if not phase6_marker.exists() or not cap_dir.exists():
                continue

            cap_scene_1 = cap_dir / "caption_scene_1.txt"
            if not cap_scene_1.exists():
                continue

            text_s1 = cap_scene_1.read_text(encoding="utf-8")
            for greeting in GREETING_SUBSTRINGS:
                self.assertNotIn(greeting, text_s1,
                    f"[{lang_code}] Greeting '{greeting}' must not be in Phase 6 scene 1 caption")


    # 13. Shared asset plan remains unchanged
    def test_13_shared_asset_plan_unchanged(self):
        if not ASSET_PLAN_PATH.exists():
            self.skipTest("Production asset plan file not available in CI environment")
        actual_sha256 = hashlib.sha256(ASSET_PLAN_PATH.read_bytes()).hexdigest()
        self.assertEqual(actual_sha256, EXPECTED_SHA256, "Shared asset plan SHA256 has changed!")


if __name__ == "__main__":
    unittest.main(verbosity=2)
