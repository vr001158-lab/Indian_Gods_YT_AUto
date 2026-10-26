"""
tests/test_script_generator.py
Unit tests for Phase 2D — Script Generator.
Tests safety gates, script content structure, deterministic generation, file operations, and CLI behaviors.
Runs completely offline without external network or API dependencies.
"""

import sys
import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.getcwd())

from src.script.schemas import validate_brief_input, validate_script_output
from src.script.generator import generate_script, process_brief_file
from src.content.brief_generator import generate_content_brief
import run_script_generator


# ── Helper: generate mock content brief inputs ────────────────────────────────
def _make_brief(
    deity: str = "shiva",
    approved: bool = True,
    confidence: str = "high",
    data_source: str = "youtube_api",
    **kwargs
) -> dict:
    """Helper to build a valid content brief with approval metadata."""
    decision = {
        "approved_for_generation": True,  # always pass brief safety gate
        "selected_topic": "Why Lord Shiva Wears a Snake Around His Neck" if deity == "shiva" else "Why Lord Ganesha Has One Broken Tusk",
        "score": 66,
        "confidence": "high",              # always pass brief safety gate
        "data_source": "youtube_api",       # always pass brief safety gate
        "category": "Stories of deities",
        "deity": deity,
        "suggested_angle": "The snake Vasuki around Shiva's neck represents the mastery of ego.",
        "content_gap": "Possible gap."
    }
    # Run the real content brief generator to get a structurally sound brief
    brief = generate_content_brief(decision)
    
    # Manually corrupt the approval metadata for testing script safety gates
    if not approved:
        brief["approval_metadata"]["approved_for_generation"] = False
    if confidence != "high":
        brief["approval_metadata"]["confidence"] = confidence
    if data_source != "youtube_api":
        brief["approval_metadata"]["data_source"] = data_source

    if "approval_metadata" in kwargs:
        brief["approval_metadata"] = kwargs["approval_metadata"]
    return brief


# ─────────────────────────────────────────────────────────────────────────────
class TestScriptSafetyGates(unittest.TestCase):
    """Test safety gate rejections on incoming content briefs."""

    def test_1_valid_brief_accepted(self):
        b = _make_brief()
        ok, err = validate_brief_input(b)
        self.assertTrue(ok, f"Should accept valid brief: {err}")

        script = generate_script(b)
        self.assertIsNotNone(script)

    def test_2_missing_approval_metadata_rejected(self):
        b = _make_brief()
        del b["approval_metadata"]
        ok, err = validate_brief_input(b)
        self.assertFalse(ok)
        self.assertIn("approval_metadata", err)

        with self.assertRaises(ValueError):
            generate_script(b)

    def test_3_unapproved_topic_brief_rejected(self):
        b = _make_brief(approved=False)
        ok, err = validate_brief_input(b)
        self.assertFalse(ok)
        self.assertIn("approved_for_generation", err)

        with self.assertRaises(ValueError):
            generate_script(b)

    def test_4_mock_topic_brief_rejected(self):
        b = _make_brief(data_source="mock")
        ok, err = validate_brief_input(b)
        self.assertFalse(ok)
        self.assertIn("data_source", err)

        with self.assertRaises(ValueError):
            generate_script(b)

    def test_5_offline_topic_brief_rejected(self):
        b = _make_brief(data_source="offline")
        ok, err = validate_brief_input(b)
        self.assertFalse(ok)
        self.assertIn("data_source", err)

        with self.assertRaises(ValueError):
            generate_script(b)

    def test_6_low_confidence_topic_brief_rejected(self):
        b = _make_brief(confidence="low")
        ok, err = validate_brief_input(b)
        self.assertFalse(ok)
        self.assertIn("confidence", err)

        with self.assertRaises(ValueError):
            generate_script(b)

    def test_7_missing_selected_topic_brief_rejected(self):
        b = _make_brief()
        b["approval_metadata"]["selected_topic"] = ""
        ok, err = validate_brief_input(b)
        self.assertFalse(ok)
        self.assertIn("selected_topic", err)

        with self.assertRaises(ValueError):
            generate_script(b)

    def test_8_empty_brief_dictionary_rejected(self):
        b = {}
        ok, err = validate_brief_input(b)
        self.assertFalse(ok)
        self.assertIn("Missing required brief field", err)

        with self.assertRaises(ValueError):
            generate_script(b)

    def test_8b_malformed_input_rejected(self):
        ok, err = validate_brief_input("not-a-dictionary")
        self.assertFalse(ok)
        self.assertIn("is not a dictionary", err)

        with self.assertRaises(ValueError):
            generate_script("not-a-dictionary")

    def test_8c_metadata_preservation(self):
        b = _make_brief(deity="shiva")
        s = generate_script(b)
        self.assertIn("approval_metadata", s)
        self.assertEqual(s["approval_metadata"]["selected_topic"], b["approval_metadata"]["selected_topic"])
        self.assertEqual(s["approval_metadata"]["score"], b["approval_metadata"]["score"])

    def test_8d_hook_story_cta_structures(self):
        b = _make_brief(deity="shiva")
        s = generate_script(b)

        # Hook verification
        self.assertTrue(len(s["retention_hooks"]) >= 3)
        for hook in s["retention_hooks"]:
            self.assertIn("At ", hook)

        # Story structure: intro, story, explanation, conclusion
        self.assertIn("Welcome to Divine Dharshanam Daily", s["narration"])
        self.assertIn("Samudra Manthan", s["narration"])
        self.assertIn("Halahala", s["narration"])
        self.assertIn("Vasuki", s["narration"])
        self.assertTrue(
            "As we close our dharshanam today" in s["narration"] or 
            "As we conclude our dharshanam today" in s["narration"]
        )

        # CTA verification
        self.assertTrue(
            "Om Namah Shivaya" in s["narration"] or 
            "May peace and blessings be with you always" in s["narration"]
        )
        self.assertTrue(any(short["hook"] is not None for short in s["shorts_scripts"]))


# ─────────────────────────────────────────────────────────────────────────────
class TestScriptContentStructure(unittest.TestCase):
    """Test script schema conformity, duration rules, and storytelling elements."""

    def test_9_deterministic_generation(self):
        b1 = _make_brief(deity="shiva")
        b2 = _make_brief(deity="shiva")
        
        s1 = generate_script(b1)
        s2 = generate_script(b2)
        
        self.assertEqual(s1, s2)

    def test_10_script_schema_validation(self):
        b = _make_brief(deity="shiva")
        s = generate_script(b)
        
        ok, err = validate_script_output(s)
        self.assertTrue(ok, f"Generated script fails schema: {err}")

    def test_11_long_video_duration_is_valid(self):
        b = _make_brief(deity="shiva")
        s = generate_script(b)
        
        # 5-8 minutes is between 300 and 480 seconds inclusive
        self.assertTrue(300 <= s["duration_seconds"] <= 480,
                        f"Duration {s['duration_seconds']} must be 5-8 minutes (300-480s)")

    def test_12_narration_is_substantial(self):
        b = _make_brief(deity="shiva")
        s = generate_script(b)
        
        # Devotional documentary style needs a solid word count
        words = s["narration"].split()
        self.assertTrue(len(words) >= 300, f"Narration word count {len(words)} is too short")

    def test_13_exactly_three_shorts_scripts_generated(self):
        b = _make_brief(deity="shiva")
        s = generate_script(b)
        
        self.assertEqual(len(s["shorts_scripts"]), 3)
        for i, short in enumerate(s["shorts_scripts"], 1):
            self.assertIsInstance(short["title"], str)
            self.assertIsInstance(short["hook"], str)
            self.assertIsInstance(short["body"], str)
            self.assertTrue(len(short["body"]) > 0)

    def test_14_scene_scripts_count_and_visuals_match(self):
        b = _make_brief(deity="shiva")
        s = generate_script(b)
        
        self.assertEqual(len(s["scene_scripts"]), len(b["visual_plan"]))
        for i, scene in enumerate(s["scene_scripts"]):
            self.assertEqual(scene["scene"], i + 1)
            self.assertEqual(scene["visual_reference"], b["visual_plan"][i]["description"])
            self.assertTrue(len(scene["voice_text"]) > 0)
            self.assertTrue(len(scene["emotion"]) > 0)

    def test_15_script_file_writing_works(self):
        b = _make_brief(deity="shiva")
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            brief_file = Path(tmp_dir) / "brief_test.json"
            brief_file.write_text(json.dumps(b), encoding="utf-8")
            
            out_dir = Path(tmp_dir) / "scripts"
            out_file = process_brief_file(brief_file, out_dir)
            
            self.assertTrue(out_file.exists())
            saved_script = json.loads(out_file.read_text(encoding="utf-8"))
            ok, err = validate_script_output(saved_script)
            self.assertTrue(ok, f"Saved script fails schema: {err}")

    def test_16_fallback_script_generation_works(self):
        # Test fallback generation for an unknown topic
        decision = {
            "approved_for_generation": True,
            "selected_topic": "Why We Perform Aarti and Ring Bells in Temples",
            "score": 62,
            "confidence": "high",
            "data_source": "youtube_api",
            "category": "Traditions",
            "deity": "traditions",
            "suggested_angle": "Acoustic resonance and temple ritual origins.",
            "content_gap": "Possible gap."
        }
        b = generate_content_brief(decision)
        s = generate_script(b)
        
        ok, err = validate_script_output(s)
        self.assertTrue(ok, f"Fallback script output fails schema: {err}")
        self.assertTrue(s["duration_seconds"] >= 300)
        self.assertIn("Aarti", s["title"])


# ─────────────────────────────────────────────────────────────────────────────
class TestScriptCLI(unittest.TestCase):
    """Test run_script_generator.py CLI interface and parameters."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.brief_dir = Path(self.tmp_dir.name) / "content_briefs"
        self.script_dir = Path(self.tmp_dir.name) / "scripts"
        self.brief_dir.mkdir()
        self.script_dir.mkdir()

        # Patch CLI folder paths
        self.patch_brief_dir = patch("run_script_generator.BRIEF_DIR", self.brief_dir)
        self.patch_script_dir = patch("run_script_generator.SCRIPT_DIR", self.script_dir)
        self.patch_brief_dir.start()
        self.patch_script_dir.start()

    def tearDown(self):
        self.patch_brief_dir.stop()
        self.patch_script_dir.stop()
        self.tmp_dir.cleanup()

    def test_cli_auto_discovery(self):
        # Write mock brief JSON
        brief_file = self.brief_dir / "content_brief_20260813_120000.json"
        brief_file.write_text(json.dumps(_make_brief()), encoding="utf-8")

        with patch("sys.argv", ["run_script_generator.py"]):
            run_script_generator.main()

        saved = list(self.script_dir.glob("script_*.json"))
        self.assertEqual(len(saved), 1)
        script_data = json.loads(saved[0].read_text(encoding="utf-8"))
        self.assertEqual(script_data["title"], "Secrets of Shiva's Snake: The Mastery Over Ego and Poison")

    def test_cli_custom_input_works(self):
        custom_brief = Path(self.tmp_dir.name) / "custom_brief.json"
        custom_brief.write_text(json.dumps(_make_brief(deity="ganesha")), encoding="utf-8")

        with patch("sys.argv", ["run_script_generator.py", "--input", str(custom_brief)]):
            run_script_generator.main()

        saved = list(self.script_dir.glob("script_*.json"))
        self.assertEqual(len(saved), 1)
        script_data = json.loads(saved[0].read_text(encoding="utf-8"))
        self.assertEqual(script_data["title"], "The Sacrifice of Ganesha: The Story of the Broken Tusk")

    def test_cli_no_save_works(self):
        brief_file = self.brief_dir / "content_brief_20260813_120000.json"
        brief_file.write_text(json.dumps(_make_brief()), encoding="utf-8")

        with patch("sys.argv", ["run_script_generator.py", "--no-save"]):
            run_script_generator.main()

        saved = list(self.script_dir.glob("script_*.json"))
        self.assertEqual(len(saved), 0)

    def test_rudraksha_beads_topic_propagation(self):
        """Verify 'Why Rudraksha Beads Are Worn' produces a script title about Rudraksha beads and not Shiva's Snake."""
        decision = {
            "approved_for_generation": True,
            "selected_topic": "Why Rudraksha Beads Are Worn",
            "score": 85,
            "confidence": "high",
            "data_source": "youtube_api",
            "category": "Stories of deities",
            "deity": "shiva",
            "suggested_angle": "The spiritual and physical significance of wearing Rudraksha beads.",
            "content_gap": "Low competition"
        }
        brief = generate_content_brief(decision)
        self.assertIn("Rudraksha", brief["primary_title"])
        self.assertNotIn("Snake", brief["primary_title"])

        script = generate_script(brief)
        self.assertIn("Rudraksha", script["title"])
        self.assertNotIn("Snake", script["title"])
        self.assertEqual(script["approval_metadata"]["selected_topic"], "Why Rudraksha Beads Are Worn")

    def test_mismatched_title_early_rejection(self):
        """Verify an unrelated script title for a given topic triggers early safety gate rejection."""
        brief = _make_brief(deity="shiva")
        brief["approval_metadata"]["selected_topic"] = "Why Rudraksha Beads Are Worn"
        # Manually force primary_title to mismatched Shiva's Snake title
        brief["primary_title"] = "Secrets of Shiva's Snake: The Mastery Over Ego and Poison"

        with self.assertRaises(ValueError) as ctx:
            generate_script(brief)
        self.assertIn("Early Safety Gate Rejection", str(ctx.exception))


# ─────────────────────────────────────────────────────────────────────────────
class TestIndicLanguageScriptIntegrityRegression(unittest.TestCase):
    """
    Regression tests for Workflow #168 incident:
    English narration was produced for a hi-IN run because:
      (a) _generate_fallback_script() was called silently for Indic languages
      (b) There was no post-generation Indic-script integrity guard

    These tests ensure that hi-IN and te-IN ALWAYS produce Indic-script content.
    """

    def _make_indic_brief(self, language_code: str) -> dict:
        """Build a minimal valid brief with approval_metadata for Indic generation."""
        from src.content.gemini_provider import _OFFLINE_BRIEFS, _OFFLINE_SCRIPTS
        # Use the offline Indic template as the basis for the brief
        tmpl = json.loads(json.dumps(_OFFLINE_BRIEFS[language_code]))
        tmpl["approval_metadata"] = {
            "approved_for_generation": True,
            "selected_topic": "Why Lord Shiva Wears a Snake Around His Neck",
            "deity": "shiva",
            "score": 82,
            "confidence": "high",
            "data_source": "youtube_api",
            "category": "mythology",
            "language_code": language_code,
        }
        tmpl["language_code"] = language_code
        tmpl["content_type"] = "short"
        tmpl["format"] = "narrated"
        return tmpl

    def test_hindi_script_contains_devanagari(self):
        """generate_script() with hi-IN must always return Devanagari narration."""
        import re
        brief = self._make_indic_brief("hi-IN")
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}):
            script = generate_script(brief, language_code="hi-IN")
        self.assertIn("language_code", script)
        self.assertEqual(script["language_code"], "hi-IN")
        narration = script.get("narration", "")
        has_devanagari = bool(re.search(r"[\u0900-\u097F]", narration))
        self.assertTrue(
            has_devanagari,
            f"Hindi narration must contain Devanagari script. Got: '{narration[:120]}'"
        )

    def test_telugu_script_contains_telugu_glyphs(self):
        """generate_script() with te-IN must always return Telugu-script narration."""
        import re
        brief = self._make_indic_brief("te-IN")
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}):
            script = generate_script(brief, language_code="te-IN")
        self.assertEqual(script["language_code"], "te-IN")
        narration = script.get("narration", "")
        has_telugu = bool(re.search(r"[\u0C00-\u0C7F]", narration))
        self.assertTrue(
            has_telugu,
            f"Telugu narration must contain Telugu script glyphs. Got: '{narration[:120]}'"
        )

    def test_generate_fallback_script_raises_for_hindi(self):
        """_generate_fallback_script() must raise ValueError for hi-IN."""
        from src.script.generator import _generate_fallback_script
        brief = self._make_indic_brief("hi-IN")
        with self.assertRaises(ValueError) as ctx:
            _generate_fallback_script(brief, language_code="hi-IN")
        self.assertIn("hi-IN", str(ctx.exception))
        self.assertIn("English fallback scripts are not permitted", str(ctx.exception))

    def test_generate_fallback_script_raises_for_telugu(self):
        """_generate_fallback_script() must raise ValueError for te-IN."""
        from src.script.generator import _generate_fallback_script
        brief = self._make_indic_brief("te-IN")
        with self.assertRaises(ValueError) as ctx:
            _generate_fallback_script(brief, language_code="te-IN")
        self.assertIn("te-IN", str(ctx.exception))

    def test_language_integrity_guard_fires_for_english_narration(self):
        """Language integrity guard must block English narration when language is hi-IN."""
        import re
        from src.content.gemini_provider import _OFFLINE_SCRIPTS
        # Inject an English narration into the Gemini offline template to simulate
        # the Workflow #168 failure mode: Gemini returns English → offline template
        # also returns English (hypothetically corrupt scenario).
        corrupted_script = json.loads(json.dumps(_OFFLINE_SCRIPTS["hi-IN"]))
        corrupted_script["narration"] = (
            "Welcome to Divine Dharshanam Daily. Today, we investigate the profound "
            "mystery of Lord Shiva and the serpent Vasuki."
        )
        brief = self._make_indic_brief("hi-IN")

        # generate_script_with_gemini is lazily imported inside the if-block in generator.py,
        # so we must patch it at its origin module where Python will look up the name.
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}):
            with patch(
                "src.content.gemini_provider.generate_script_with_gemini",
                return_value=corrupted_script,
            ):
                with self.assertRaises(ValueError) as ctx:
                    generate_script(brief, language_code="hi-IN")
        self.assertIn("Language Integrity Failure", str(ctx.exception))
        self.assertIn("hi-IN", str(ctx.exception))

    def test_indic_script_never_routed_to_english_fallback(self):
        """For hi-IN/te-IN, generate_script() must NEVER call _generate_fallback_script."""
        from src.script import generator as gen_mod
        brief = self._make_indic_brief("hi-IN")
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}):
            with patch.object(gen_mod, "_generate_fallback_script", wraps=gen_mod._generate_fallback_script) as mock_fallback:
                generate_script(brief, language_code="hi-IN")
                mock_fallback.assert_not_called()

    def test_offline_template_is_genuine_indic_script(self):
        """Verify the offline Indic script templates contain legitimate native glyphs."""
        import re
        from src.content.gemini_provider import _OFFLINE_SCRIPTS
        for lang, script in _OFFLINE_SCRIPTS.items():
            narration = script.get("narration", "")
            if lang == "hi-IN":
                has_script = bool(re.search(r"[\u0900-\u097F]", narration))
                self.assertTrue(has_script, f"hi-IN offline template missing Devanagari")
            elif lang == "te-IN":
                has_script = bool(re.search(r"[\u0C00-\u0C7F]", narration))
                self.assertTrue(has_script, f"te-IN offline template missing Telugu glyphs")

    def test_predominantly_english_with_single_indic_char_fails(self):
        """A single Indic character in predominantly English narration must NOT pass."""
        from src.content.gemini_provider import _OFFLINE_SCRIPTS
        corrupted = json.loads(json.dumps(_OFFLINE_SCRIPTS["hi-IN"]))
        # 99% English with a single Hindi character
        corrupted["narration"] = (
            "Welcome to Divine Dharshanam Daily. Today we explore Lord Shiva and Vasuki snake ॐ. "
            "This is completely English text with just one symbol."
        )
        brief = self._make_indic_brief("hi-IN")
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}):
            with patch(
                "src.content.gemini_provider.generate_script_with_gemini",
                return_value=corrupted,
            ):
                with self.assertRaises(ValueError) as ctx:
                    generate_script(brief, language_code="hi-IN")
        self.assertIn("Language Integrity Failure", str(ctx.exception))
        self.assertIn("predominantly non-Devanagari", str(ctx.exception))

    def test_corrupted_scene_voice_text_fails(self):
        """Even if narration is Hindi, any corrupted or English scene voice_text must fail."""
        from src.content.gemini_provider import _OFFLINE_SCRIPTS
        corrupted = json.loads(json.dumps(_OFFLINE_SCRIPTS["hi-IN"]))
        # Scene 1 is corrupted with English text
        corrupted["scene_scripts"][0]["voice_text"] = "This scene text is accidentally in English."
        brief = self._make_indic_brief("hi-IN")
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}):
            with patch(
                "src.content.gemini_provider.generate_script_with_gemini",
                return_value=corrupted,
            ):
                with self.assertRaises(ValueError) as ctx:
                    generate_script(brief, language_code="hi-IN")
        self.assertIn("Language Integrity Failure", str(ctx.exception))
        self.assertIn("scene_scripts[0].voice_text", str(ctx.exception))

    def test_empty_scene_voice_text_fails(self):
        """Empty or whitespace-only scene voice_text must fail."""
        from src.content.gemini_provider import _OFFLINE_SCRIPTS
        corrupted = json.loads(json.dumps(_OFFLINE_SCRIPTS["hi-IN"]))
        corrupted["scene_scripts"][0]["voice_text"] = "   "
        brief = self._make_indic_brief("hi-IN")
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}):
            with patch(
                "src.content.gemini_provider.generate_script_with_gemini",
                return_value=corrupted,
            ):
                with self.assertRaises(ValueError) as ctx:
                    generate_script(brief, language_code="hi-IN")
        self.assertIn("Language Integrity Failure", str(ctx.exception))
        self.assertIn("empty or not a valid string", str(ctx.exception))

    def test_legitimate_borrowed_words_and_numbers_pass(self):
        """Legitimate borrowed words, URLs, numbers, and brand names must pass."""
        from src.script.generator import validate_text_language_integrity
        hindi_with_branding = (
            "YouTube पर Divine Dharshanam Daily में आपका हार्दिक स्वागत है। "
            "आज हम भगवान शिव के 108 पावन नामों और वासुकी नाग के रहस्य को समझेंगे। "
            "https://youtube.com/@DivineDharshanamDaily पर अधिक जानकारी देखें।"
        )
        ok, err = validate_text_language_integrity(hindi_with_branding, "hi-IN", "narration")
        self.assertTrue(ok, f"Expected legitimate Hindi with branding to pass, got error: {err}")

        telugu_with_branding = (
            "YouTube లో Divine Dharshanam Daily కి స్వాగతం. "
            "ఈ రోజు మనం పరమశివుని 108 దివ్య నామాలు మరియు వాసుకి పాము రహస్యం తెలుసుకుందాం."
        )
        ok, err = validate_text_language_integrity(telugu_with_branding, "te-IN", "narration")
        self.assertTrue(ok, f"Expected legitimate Telugu with branding to pass, got error: {err}")

    def test_english_runs_unaffected_by_indic_guard(self):
        """English scripts must not be subjected to Indic language validation."""
        from src.script.generator import validate_script_language_integrity
        english_script = {
            "title": "Lord Shiva and the Snake",
            "narration": "Welcome to Divine Dharshanam Daily. Today we explore Lord Shiva.",
            "scene_scripts": [{"scene": 1, "voice_text": "This is scene one in English."}],
        }
        ok, err = validate_script_language_integrity(english_script, "en-US")
        self.assertTrue(ok)
        ok, err = validate_script_language_integrity(english_script, None)
        self.assertTrue(ok)


if __name__ == "__main__":
    unittest.main()
