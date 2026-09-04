"""
tests/test_content_brief.py
Unit tests for Phase 2C — Content Brief Generator.
Tests safety gates, deterministic blueprint mapping, output schema validation, file operations, and CLI behaviors.
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

from src.content.schemas import validate_decision_input, validate_brief_output
from src.content.brief_generator import generate_content_brief, process_decision_file
import run_content_brief


# ── Helper: generate mock decision inputs ─────────────────────────────────────
def _make_decision(
    topic: str = "Why Lord Shiva Wears a Snake Around His Neck",
    deity: str = "shiva",
    approved: bool = True,
    confidence: str = "high",
    data_source: str = "youtube_api",
    **kwargs
) -> dict:
    """Helper to build a structurally valid decision dict matching the output of Phase 2B.1."""
    base = {
        "approved_for_generation": approved,
        "selected_topic": topic,
        "score": 66,
        "confidence": confidence,
        "data_source": data_source,
        "category": "Stories of deities",
        "deity": deity,
        "suggested_angle": "The snake Vasuki around Shiva's neck represents the mastery of ego and poison.",
        "content_gap": "Possible gap — low saturation with moderate-to-high demand signals.",
        "selection_reason": "Ranked #1 of 3 validated real-data candidates.",
        "rejected_candidates": [],
        "selected_at": "2026-08-13T12:00:00Z"
    }
    base.update(kwargs)
    return base


# ─────────────────────────────────────────────────────────────────────────────
class TestContentBriefSafetyGates(unittest.TestCase):
    """Test safety gate rejections on incoming topic decisions."""

    def test_1_valid_decision_accepted(self):
        d = _make_decision()
        ok, err = validate_decision_input(d)
        self.assertTrue(ok)
        self.assertEqual(err, "")

        # Generator runs without error
        brief = generate_content_brief(d)
        self.assertIsNotNone(brief)

    def test_2_unapproved_topic_rejected(self):
        d = _make_decision(approved=False)
        ok, err = validate_decision_input(d)
        self.assertFalse(ok)
        self.assertIn("approved_for_generation", err)

        with self.assertRaises(ValueError):
            generate_content_brief(d)

    def test_3_mock_topic_rejected(self):
        d = _make_decision(data_source="mock")
        ok, err = validate_decision_input(d)
        self.assertFalse(ok)
        self.assertIn("data_source", err)

        with self.assertRaises(ValueError):
            generate_content_brief(d)

    def test_4_offline_topic_rejected(self):
        d = _make_decision(data_source="offline")
        ok, err = validate_decision_input(d)
        self.assertFalse(ok)
        self.assertIn("data_source", err)

        with self.assertRaises(ValueError):
            generate_content_brief(d)

    def test_5_low_confidence_topic_rejected(self):
        d = _make_decision(confidence="low")
        ok, err = validate_decision_input(d)
        self.assertFalse(ok)
        self.assertIn("confidence", err)

        with self.assertRaises(ValueError):
            generate_content_brief(d)

    def test_6_medium_confidence_topic_rejected(self):
        d = _make_decision(confidence="medium")
        ok, err = validate_decision_input(d)
        self.assertFalse(ok)
        self.assertIn("confidence", err)

        with self.assertRaises(ValueError):
            generate_content_brief(d)

    def test_7_missing_decision_fields_rejected(self):
        d = _make_decision()
        del d["category"]
        ok, err = validate_decision_input(d)
        self.assertFalse(ok)
        self.assertIn("category", err)

        with self.assertRaises(ValueError):
            generate_content_brief(d)

    def test_8_null_decision_fields_rejected(self):
        d = _make_decision()
        d["suggested_angle"] = None
        ok, err = validate_decision_input(d)
        self.assertFalse(ok)
        self.assertIn("suggested_angle", err)

        with self.assertRaises(ValueError):
            generate_content_brief(d)

    def test_8b_missing_topic_rejected(self):
        d = _make_decision()
        d["selected_topic"] = ""
        ok, err = validate_decision_input(d)
        self.assertFalse(ok)
        self.assertIn("selected_topic", err)

        with self.assertRaises(ValueError):
            generate_content_brief(d)

    def test_8c_malformed_decision_rejected(self):
        ok, err = validate_decision_input("not-a-dictionary")
        self.assertFalse(ok)
        self.assertIn("is not a dictionary", err)

        with self.assertRaises(ValueError):
            generate_content_brief("not-a-dictionary")


# ─────────────────────────────────────────────────────────────────────────────
class TestContentBriefGeneration(unittest.TestCase):
    """Test blueprint validation, content structuring, and output correctness."""

    def test_9_deterministic_output(self):
        d1 = _make_decision(deity="shiva")
        d2 = _make_decision(deity="shiva")
        
        brief1 = generate_content_brief(d1)
        brief2 = generate_content_brief(d2)
        
        # Verify strict determinism
        self.assertEqual(brief1, brief2)

    def test_10_schema_validation(self):
        d = _make_decision(deity="shiva")
        brief = generate_content_brief(d)
        
        ok, err = validate_brief_output(brief)
        self.assertTrue(ok, f"Generated brief fails schema: {err}")

    def test_11_title_options_count(self):
        d = _make_decision(deity="shiva")
        brief = generate_content_brief(d)
        
        self.assertEqual(len(brief["title_options"]), 5)
        for title in brief["title_options"]:
            self.assertIsInstance(title, str)
            self.assertTrue(len(title) > 0)

    def test_12_visual_scene_format(self):
        d = _make_decision(deity="shiva")
        brief = generate_content_brief(d)
        
        scenes = brief["visual_plan"]
        self.assertTrue(len(scenes) >= 3, "Visual plan should have multiple scenes")
        
        for i, scene in enumerate(scenes, 1):
            self.assertEqual(scene["scene_number"], i)
            self.assertIsInstance(scene["duration_seconds"], int)
            self.assertTrue(scene["duration_seconds"] > 0)
            self.assertIsInstance(scene["description"], str)
            self.assertIsInstance(scene["image_prompt"], str)
            self.assertIsInstance(scene["video_prompt"], str)

    def test_13_seo_metadata_fields(self):
        d = _make_decision(deity="shiva")
        brief = generate_content_brief(d)
        
        seo = brief["seo_metadata"]
        self.assertIsInstance(seo["description"], str)
        self.assertTrue(len(seo["description"]) > 0)
        self.assertIsInstance(seo["keywords"], list)
        self.assertTrue(len(seo["keywords"]) > 0)
        self.assertIsInstance(seo["hashtags"], list)
        self.assertTrue(len(seo["hashtags"]) > 0)
        self.assertIsInstance(seo["category"], str)

    def test_14_shorts_hooks_present(self):
        d = _make_decision(deity="shiva")
        brief = generate_content_brief(d)
        
        self.assertIsInstance(brief["shorts_hooks"], list)
        self.assertTrue(len(brief["shorts_hooks"]) > 0)
        for h in brief["shorts_hooks"]:
            self.assertIsInstance(h, str)
            self.assertTrue(len(h) > 0)

    def test_15_file_generation_works(self):
        d = _make_decision(deity="shiva")
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            dec_file = Path(tmp_dir) / "decision_test.json"
            dec_file.write_text(json.dumps(d), encoding="utf-8")
            
            out_dir = Path(tmp_dir) / "briefs"
            out_file = process_decision_file(dec_file, out_dir)
            
            self.assertTrue(out_file.exists())
            saved_brief = json.loads(out_file.read_text(encoding="utf-8"))
            ok, err = validate_brief_output(saved_brief)
            self.assertTrue(ok, f"Persisted file fails schema: {err}")

    def test_16_fallback_generator_works(self):
        # A completely unknown deity topic should trigger the fallback builder safely
        d = _make_decision(
            topic="Mystery of the Sun God chariot wheels at Konark",
            deity="surya",
            category="Architectural mysteries"
        )
        brief = generate_content_brief(d)
        ok, err = validate_brief_output(brief)
        self.assertTrue(ok, f"Fallback generator output fails schema: {err}")
        self.assertIn("Surya", brief["primary_title"])


# ─────────────────────────────────────────────────────────────────────────────
class TestContentBriefCLI(unittest.TestCase):
    """Test run_content_brief.py CLI actions and arg parsing."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.dec_dir = Path(self.tmp_dir.name) / "decision"
        self.brief_dir = Path(self.tmp_dir.name) / "content_briefs"
        self.dec_dir.mkdir()
        self.brief_dir.mkdir()

        # Patch paths inside CLI module
        self.patch_dec_dir = patch("run_content_brief.DECISION_DIR", self.dec_dir)
        self.patch_brief_dir = patch("run_content_brief.BRIEF_DIR", self.brief_dir)
        self.patch_dec_dir.start()
        self.patch_brief_dir.start()

    def tearDown(self):
        self.patch_dec_dir.stop()
        self.patch_brief_dir.stop()
        self.tmp_dir.cleanup()

    def test_cli_auto_discovery(self):
        # Write mock decision JSON
        dec_file = self.dec_dir / "decision_20260813_120000.json"
        dec_file.write_text(json.dumps(_make_decision()), encoding="utf-8")

        with patch("sys.argv", ["run_content_brief.py"]):
            run_content_brief.main()

        # Verify output saved to patched brief dir
        saved = list(self.brief_dir.glob("content_brief_*.json"))
        self.assertEqual(len(saved), 1)
        brief_data = json.loads(saved[0].read_text(encoding="utf-8"))
        self.assertEqual(brief_data["primary_title"], "Secrets of Shiva's Snake: The Mastery Over Ego and Poison")

    def test_cli_custom_input_works(self):
        custom_dec = Path(self.tmp_dir.name) / "custom_decision.json"
        custom_dec.write_text(json.dumps(_make_decision(deity="ganesha", topic="Why Does Lord Ganesha Have a Broken Tusk?")), encoding="utf-8")

        with patch("sys.argv", ["run_content_brief.py", "--input", str(custom_dec)]):
            run_content_brief.main()

        saved = list(self.brief_dir.glob("content_brief_*.json"))
        self.assertEqual(len(saved), 1)
        brief_data = json.loads(saved[0].read_text(encoding="utf-8"))
        self.assertEqual(brief_data["primary_title"], "The Sacrifice of Ganesha: The Story of the Broken Tusk")

    def test_cli_no_save_works(self):
        dec_file = self.dec_dir / "decision_20260813_120000.json"
        dec_file.write_text(json.dumps(_make_decision()), encoding="utf-8")

        with patch("sys.argv", ["run_content_brief.py", "--no-save"]):
            run_content_brief.main()

        # No file should be saved in the brief folder
        saved = list(self.brief_dir.glob("content_brief_*.json"))
        self.assertEqual(len(saved), 0)


if __name__ == "__main__":
    unittest.main()
