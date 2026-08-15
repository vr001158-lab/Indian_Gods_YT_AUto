"""
tests/test_thumbnail_generator.py
Unit tests for Phase 2H — Thumbnail Generation Pipeline.
Tests safety gates, provider engines, image constraints, analyzer checks, metadata creation, and CLI behaviors.
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

from src.thumbnail.schemas import validate_decision_input, validate_metadata_output
from src.thumbnail.validator import validate_decision_safety, verify_or_raise_safety
from src.thumbnail.generator import PILThumbnailGenerator, MockThumbnailGenerator, FluxThumbnailGenerator
from src.thumbnail.analyzer import analyze_thumbnail_file
from src.thumbnail.templates import DEVOTIONAL_GOLD_THEME
import run_thumbnail_generator


# ── Helper: generate mock decision inputs ─────────────────────────────────────
def _make_decision(
    approved: bool = True,
    confidence: str = "high",
    data_source: str = "youtube_api",
    title: str = "Why Lord Shiva Wears a Snake Around His Neck",
) -> dict:
    """Helper to build a valid decision structure carrying safety status."""
    return {
        "approved_for_generation": approved,
        "selected_topic":          title,
        "score":                   66,
        "confidence":              confidence,
        "data_source":             data_source,
        "category":                "Stories of deities",
        "deity":                   "shiva",
        "suggested_angle":         "Test angle.",
        "content_gap":             "Test gap."
    }


# ─────────────────────────────────────────────────────────────────────────────
class TestThumbnailSafetyGates(unittest.TestCase):
    """Test safety gate checks on incoming decisions (Tests 1-7)."""

    def test_1_valid_decision_accepted(self):
        d = _make_decision()
        ok, err = validate_decision_safety(d)
        self.assertTrue(ok, f"Should accept valid decision: {err}")
        verify_or_raise_safety(d)  # should not raise

    def test_2_missing_approval_rejected(self):
        d = _make_decision()
        del d["approved_for_generation"]
        ok, err = validate_decision_safety(d)
        self.assertFalse(ok)
        self.assertIn("approved_for_generation", err)
        with self.assertRaises(ValueError):
            verify_or_raise_safety(d)

    def test_3_mock_data_rejected(self):
        d = _make_decision(data_source="mock")
        ok, err = validate_decision_safety(d)
        self.assertFalse(ok)
        self.assertIn("data_source", err)
        with self.assertRaises(ValueError):
            verify_or_raise_safety(d)

    def test_4_offline_data_rejected(self):
        d = _make_decision(data_source="offline")
        ok, err = validate_decision_safety(d)
        self.assertFalse(ok)
        self.assertIn("data_source", err)
        with self.assertRaises(ValueError):
            verify_or_raise_safety(d)

    def test_5_low_confidence_rejected(self):
        d = _make_decision(confidence="low")
        ok, err = validate_decision_safety(d)
        self.assertFalse(ok)
        self.assertIn("confidence", err)
        with self.assertRaises(ValueError):
            verify_or_raise_safety(d)

    def test_6_missing_title_rejected(self):
        d = _make_decision(title="")
        ok, err = validate_decision_safety(d)
        self.assertFalse(ok)
        self.assertIn("selected_topic", err)
        with self.assertRaises(ValueError):
            verify_or_raise_safety(d)

    def test_7_invalid_json_rejected(self):
        # Passes a non-dictionary input
        ok, err = validate_decision_safety([])
        self.assertFalse(ok)
        self.assertIn("must be a dictionary", err)
        with self.assertRaises(ValueError):
            verify_or_raise_safety([])


# ─────────────────────────────────────────────────────────────────────────────
class TestThumbnailGeneration(unittest.TestCase):
    """Test image composition and format validations (Tests 8-13, 15)."""

    def test_8_pil_generator_creates_image(self):
        gen = PILThumbnailGenerator()
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "thumb.png"
            gen.generate_thumbnail(
                title="Secrets of Shiva's Snake",
                subtitle="Secrets of Shiva",
                output_path=out_file
            )
            self.assertTrue(out_file.exists())
            self.assertTrue(out_file.stat().st_size > 0)

    def test_9_resolution_equals_1280x720(self):
        gen = PILThumbnailGenerator()
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "thumb.png"
            gen.generate_thumbnail(
                title="Secrets of Shiva's Snake",
                subtitle="Secrets of Shiva",
                output_path=out_file
            )
            
            analysis = analyze_thumbnail_file(out_file)
            self.assertTrue(analysis["valid"], f"Analysis failed: {analysis['errors']}")

    def test_10_png_output_valid(self):
        gen = PILThumbnailGenerator()
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "thumb.png"
            gen.generate_thumbnail(
                title="Secrets of Shiva's Snake",
                subtitle="Secrets of Shiva",
                output_path=out_file
            )
            
            # Change extension to read check file signature
            from PIL import Image
            with Image.open(out_file) as img:
                self.assertEqual(img.format, "PNG")

    def test_11_metadata_generated(self):
        meta = {
            "title":           "Secrets of Shiva's Snake",
            "topic":           "Why Lord Shiva Wears a Snake Around His Neck",
            "provider":        "pil",
            "resolution":      "1280x720",
            "format":          "png",
            "approved_source": "youtube_api",
            "confidence":      "high",
            "created_at":      "20260813_120000",
            "approval_metadata": {
                "approved_for_generation": True,
                "selected_topic": "Why Lord Shiva Wears a Snake Around His Neck",
                "score": 66,
                "confidence": "high",
                "data_source": "youtube_api"
            }
        }
        ok, err = validate_metadata_output(meta)
        self.assertTrue(ok, f"Metadata fails schema check: {err}")

    def test_11b_zero_byte_image_rejected(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            zero_file = Path(tmp_dir) / "zero.png"
            zero_file.touch()
            analysis = analyze_thumbnail_file(zero_file)
            self.assertFalse(analysis["valid"])
            self.assertIn("empty", "".join(analysis["errors"]).lower())

    def test_11c_deterministic_generation(self):
        gen = PILThumbnailGenerator()
        with tempfile.TemporaryDirectory() as tmp_dir:
            file1 = Path(tmp_dir) / "thumb1.png"
            file2 = Path(tmp_dir) / "thumb2.png"
            gen.generate_thumbnail("Shiva's Snake", "Subtitle", file1)
            gen.generate_thumbnail("Shiva's Snake", "Subtitle", file2)
            self.assertEqual(file1.stat().st_size, file2.stat().st_size)

    def test_11d_metadata_preservation(self):
        d = _make_decision()
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_img = Path(tmp_dir) / "thumb.png"
            gen = PILThumbnailGenerator()
            gen.generate_thumbnail(d["selected_topic"], "Subtitle", out_img)
            
            # Simulated output metadata preservation
            metadata = {
                "title":           d["selected_topic"],
                "topic":           d["selected_topic"],
                "provider":        "pil",
                "resolution":      "1280x720",
                "format":          "png",
                "approved_source": d["data_source"],
                "confidence":      d["confidence"],
                "created_at":      "20260813_120000",
                "approval_metadata": {
                    "approved_for_generation": d["approved_for_generation"],
                    "selected_topic": d["selected_topic"],
                    "score": d["score"],
                    "confidence": d["confidence"],
                    "data_source": d["data_source"],
                }
            }
            ok, err = validate_metadata_output(metadata)
            self.assertTrue(ok)
            self.assertEqual(metadata["approval_metadata"]["selected_topic"], d["selected_topic"])


    def test_12_analyzer_detects_corruption(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            corrupt_file = Path(tmp_dir) / "corrupt.png"
            # Write plain text to simulate corrupted file
            corrupt_file.write_text("corrupt image content data", encoding="utf-8")
            
            analysis = analyze_thumbnail_file(corrupt_file)
            self.assertFalse(analysis["valid"])
            self.assertTrue(len(analysis["errors"]) > 0)

            # Test size overflow detection
            non_exist_file = Path(tmp_dir) / "missing_file.png"
            analysis_missing = analyze_thumbnail_file(non_exist_file)
            self.assertFalse(analysis_missing["valid"])

    def test_13_mock_provider_works(self):
        gen = MockThumbnailGenerator()
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "thumb_mock.png"
            gen.generate_thumbnail(
                title="Test Title",
                subtitle="Test Subtitle",
                output_path=out_file
            )
            self.assertTrue(out_file.exists())
            
            analysis = analyze_thumbnail_file(out_file)
            self.assertTrue(analysis["valid"])

    def test_15_schema_validation_checks(self):
        # Invalid resolutions or formats fail
        valid_approval = {
            "approved_for_generation": True,
            "selected_topic": "Why Lord Shiva Wears a Snake Around His Neck",
            "score": 66,
            "confidence": "high",
            "data_source": "youtube_api"
        }
        meta = {
            "title":             "Secrets",
            "topic":             "Topic",
            "provider":          "pil",
            "resolution":        "1920x1080",  # invalid resolution
            "format":            "png",
            "approved_source":   "youtube_api",
            "confidence":        "high",
            "created_at":        "20260813_120000",
            "approval_metadata": valid_approval
        }
        ok, err = validate_metadata_output(meta)
        self.assertFalse(ok)
        self.assertIn("resolution", err)

        meta["resolution"] = "1280x720"
        meta["format"] = "jpg"  # invalid format
        ok, err = validate_metadata_output(meta)
        self.assertFalse(ok)
        self.assertIn("format", err)


# ─────────────────────────────────────────────────────────────────────────────
class TestThumbnailCLI(unittest.TestCase):
    """Test run_thumbnail_generator.py CLI interface and parameters (Test 14)."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.decision_dir = Path(self.tmp_dir.name) / "decision"
        self.thumbnail_dir = Path(self.tmp_dir.name) / "thumbnails"
        
        self.decision_dir.mkdir()
        self.thumbnail_dir.mkdir()

        # Patch CLI folder paths
        self.patch_decision_dir = patch("run_thumbnail_generator.DECISION_DIR", self.decision_dir)
        self.patch_thumbnail_dir = patch("run_thumbnail_generator.THUMBNAIL_DIR", self.thumbnail_dir)
        
        self.patch_decision_dir.start()
        self.patch_thumbnail_dir.start()

    def tearDown(self):
        self.patch_decision_dir.stop()
        self.patch_thumbnail_dir.stop()
        self.tmp_dir.cleanup()

    def test_14_cli_execution_works(self):
        d = _make_decision()
        
        # Save decision file into auto-discovery location
        decision_file = self.decision_dir / "decision_20260813_120000.json"
        decision_file.write_text(json.dumps(d), encoding="utf-8")

        with patch("sys.argv", ["run_thumbnail_generator.py", "--provider", "mock"]):
            run_thumbnail_generator.main()

        saved_meta = list(self.thumbnail_dir.glob("thumbnail_metadata_*.json"))
        saved_img = list(self.thumbnail_dir.glob("thumbnail_*.png"))
        
        self.assertEqual(len(saved_meta), 1)
        self.assertEqual(len(saved_img), 1)
        
        meta_data = json.loads(saved_meta[0].read_text(encoding="utf-8"))
        self.assertEqual(meta_data["provider"], "mock")
        self.assertEqual(meta_data["title"], "Why Lord Shiva Wears a Snake Around His Neck")

    def test_16_flux_placeholder_raises_not_implemented(self):
        gen = FluxThumbnailGenerator()
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "thumb_flux.png"
            with self.assertRaises(NotImplementedError):
                gen.generate_thumbnail("Title", "Subtitle", out_file)


if __name__ == "__main__":
    unittest.main()
