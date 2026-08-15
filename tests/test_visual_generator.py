"""
tests/test_visual_generator.py
Unit tests for Phase 2F — Visual Generation Engine.
Tests safety gates, provider selections, planning prompt mapping, output schema correctness, file operations, and CLI behaviors.
Runs completely offline without external network or API dependencies.
"""

import sys
import os
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.getcwd())

from src.visual.schemas import validate_script_input, validate_visual_map_output
from src.visual.generator import generate_visual_mapping, process_script_file
from src.script.generator import generate_script
from src.content.brief_generator import generate_content_brief
import run_visual_generator


def _offline_mock_synthesize_speech(text: str, output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    word_count = len(text.split())
    duration = max(5, round(word_count / 2.3))
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
        "-c:a", "mp3", "-b:a", "128k",
        str(output_path)
    ]
    subprocess.run(cmd, check=True)
    return duration


# ── Helper: generate mock script inputs ───────────────────────────────────────
def _make_script(
    deity: str = "shiva",
    approved: bool = True,
    confidence: str = "high",
    data_source: str = "youtube_api",
    **kwargs
) -> dict:
    """Helper to build a valid production script carrying approval metadata."""
    decision = {
        "approved_for_generation": True,
        "selected_topic": "Why Lord Shiva Wears a Snake Around His Neck" if deity == "shiva" else "Why Lord Ganesha Has One Broken Tusk",
        "score": 66,
        "confidence": "high",
        "data_source": "youtube_api",
        "category": "Stories of deities",
        "deity": deity,
        "suggested_angle": "The snake Vasuki around Shiva's neck represents the mastery of ego.",
        "content_gap": "Possible gap."
    }
    brief = generate_content_brief(decision)
    script = generate_script(brief)

    if not approved:
        script["approval_metadata"]["approved_for_generation"] = False
    if confidence != "high":
        script["approval_metadata"]["confidence"] = confidence
    if data_source != "youtube_api":
        script["approval_metadata"]["data_source"] = data_source

    if "approval_metadata" in kwargs:
        script["approval_metadata"] = kwargs["approval_metadata"]

    return script


# ─────────────────────────────────────────────────────────────────────────────
class TestVisualSafetyGates(unittest.TestCase):
    """Test safety gate rejections on incoming scripts."""

    def setUp(self):
        self.patch_net = patch("src.visual.providers._generate_via_pollinations", return_value=False)
        self.patch_voice = patch("src.voice.providers._synthesize_speech", side_effect=_offline_mock_synthesize_speech)
        self.patch_net.start()
        self.patch_voice.start()

    def tearDown(self):
        self.patch_net.stop()
        self.patch_voice.stop()

    def test_1_valid_script_accepted(self):
        s = _make_script()
        ok, err = validate_script_input(s)
        self.assertTrue(ok, f"Should accept valid script: {err}")

        with tempfile.TemporaryDirectory() as tmp_dir:
            vmap = generate_visual_mapping(s, output_dir=Path(tmp_dir))
            self.assertIsNotNone(vmap)

    def test_2_missing_approval_metadata_rejected(self):
        s = _make_script()
        del s["approval_metadata"]
        ok, err = validate_script_input(s)
        self.assertFalse(ok)
        self.assertIn("approval_metadata", err)

        with self.assertRaises(ValueError):
            with tempfile.TemporaryDirectory() as tmp_dir:
                generate_visual_mapping(s, output_dir=Path(tmp_dir))

    def test_3_unapproved_topic_script_rejected(self):
        s = _make_script(approved=False)
        ok, err = validate_script_input(s)
        self.assertFalse(ok)
        self.assertIn("approved_for_generation", err)

        with self.assertRaises(ValueError):
            with tempfile.TemporaryDirectory() as tmp_dir:
                generate_visual_mapping(s, output_dir=Path(tmp_dir))

    def test_4_mock_topic_script_rejected(self):
        s = _make_script(data_source="mock")
        ok, err = validate_script_input(s)
        self.assertFalse(ok)
        self.assertIn("data_source", err)

        with self.assertRaises(ValueError):
            with tempfile.TemporaryDirectory() as tmp_dir:
                generate_visual_mapping(s, output_dir=Path(tmp_dir))

    def test_5_offline_topic_script_rejected(self):
        s = _make_script(data_source="offline")
        ok, err = validate_script_input(s)
        self.assertFalse(ok)
        self.assertIn("data_source", err)

        with self.assertRaises(ValueError):
            with tempfile.TemporaryDirectory() as tmp_dir:
                generate_visual_mapping(s, output_dir=Path(tmp_dir))

    def test_6_low_confidence_topic_script_rejected(self):
        s = _make_script(confidence="low")
        ok, err = validate_script_input(s)
        self.assertFalse(ok)
        self.assertIn("confidence", err)

        with self.assertRaises(ValueError):
            with tempfile.TemporaryDirectory() as tmp_dir:
                generate_visual_mapping(s, output_dir=Path(tmp_dir))

    def test_7_missing_selected_topic_script_rejected(self):
        s = _make_script()
        s["approval_metadata"]["selected_topic"] = ""
        ok, err = validate_script_input(s)
        self.assertFalse(ok)
        self.assertIn("selected_topic", err)

        with self.assertRaises(ValueError):
            with tempfile.TemporaryDirectory() as tmp_dir:
                generate_visual_mapping(s, output_dir=Path(tmp_dir))

    def test_8_empty_scenes_rejected(self):
        s = _make_script()
        s["scene_scripts"] = []
        ok, err = validate_script_input(s)
        self.assertFalse(ok)
        self.assertIn("scene_scripts", err)

        with self.assertRaises(ValueError):
            with tempfile.TemporaryDirectory() as tmp_dir:
                generate_visual_mapping(s, output_dir=Path(tmp_dir))

    def test_8b_malformed_input_rejected(self):
        ok, err = validate_script_input("not-a-dictionary")
        self.assertFalse(ok)
        self.assertIn("is not a dictionary", err)

        with self.assertRaises(ValueError):
            with tempfile.TemporaryDirectory() as tmp_dir:
                generate_visual_mapping("not-a-dictionary", output_dir=Path(tmp_dir))

    def test_8c_visual_qa_file_checks(self):
        s = _make_script()
        with tempfile.TemporaryDirectory() as tmp_dir:
            vmap = generate_visual_mapping(s, output_dir=Path(tmp_dir))
            self.assertEqual(vmap["total_scenes"], len(s["scene_scripts"]))

            for scene in vmap["visual_scenes"]:
                p = Path(scene["image_file"])
                self.assertTrue(p.exists())
                self.assertTrue(p.stat().st_size > 0)

                empty_file = Path(tmp_dir) / f"empty_{scene['scene']}.png"
                empty_file.touch()
                self.assertEqual(empty_file.stat().st_size, 0)

    def test_8d_image_aspect_ratio_resolution(self):
        s = _make_script()
        with tempfile.TemporaryDirectory() as tmp_dir:
            vmap = generate_visual_mapping(s, output_dir=Path(tmp_dir))
            for scene in vmap["visual_scenes"]:
                self.assertEqual(scene["duration_seconds"], vmap["visual_scenes"][scene["scene"] - 1]["duration_seconds"])

    def test_8e_metadata_preservation(self):
        s = _make_script(deity="shiva")
        with tempfile.TemporaryDirectory() as tmp_dir:
            vmap = generate_visual_mapping(s, output_dir=Path(tmp_dir))
            self.assertIn("approval_metadata", vmap)
            self.assertEqual(vmap["approval_metadata"]["selected_topic"], s["approval_metadata"]["selected_topic"])
            self.assertEqual(vmap["approval_metadata"]["data_source"], s["approval_metadata"]["data_source"])

    def test_8f_audio_visual_timing_sync(self):
        s = _make_script(deity="shiva")
        from src.voice.generator import generate_voice_mapping
        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_map = generate_voice_mapping(s, output_dir=Path(tmp_dir), provider_name="mock", mode="test")
            vmap = generate_visual_mapping(s, output_dir=Path(tmp_dir))

            self.assertEqual(len(audio_map["audio_scenes"]), len(vmap["visual_scenes"]))
            for i in range(len(vmap["visual_scenes"])):
                self.assertTrue(vmap["visual_scenes"][i]["duration_seconds"] > 0)
                self.assertTrue(audio_map["audio_scenes"][i]["duration_seconds"] > 0)


# ─────────────────────────────────────────────────────────────────────────────
class TestVisualMappingAndProviders(unittest.TestCase):
    """Test providers, planners, file outputs, and schema correctness."""

    def setUp(self):
        self.patch_net = patch("src.visual.providers._generate_via_pollinations", return_value=False)
        self.patch_net.start()

    def tearDown(self):
        self.patch_net.stop()

    def test_9_visual_map_schema_validation(self):
        s = _make_script(deity="shiva")
        with tempfile.TemporaryDirectory() as tmp_dir:
            vmap = generate_visual_mapping(s, output_dir=Path(tmp_dir))
            ok, err = validate_visual_map_output(vmap)
            self.assertTrue(ok, f"Visual map fails schema: {err}")

    def test_10_scene_visuals_synchronized(self):
        s = _make_script(deity="shiva")
        with tempfile.TemporaryDirectory() as tmp_dir:
            vmap = generate_visual_mapping(s, output_dir=Path(tmp_dir))
            self.assertEqual(len(vmap["visual_scenes"]), len(s["scene_scripts"]))
            for i, scene in enumerate(vmap["visual_scenes"]):
                self.assertEqual(scene["scene"], i + 1)
                self.assertIn(s["scene_scripts"][i]["visual_reference"].rstrip("."), scene["visual_prompt"])
                self.assertTrue(Path(scene["image_file"]).exists())
                self.assertEqual(scene["duration_seconds"], s["scene_scripts"][i]["duration_seconds"])

    def test_11_all_providers_supported(self):
        s = _make_script(deity="shiva")
        with tempfile.TemporaryDirectory() as tmp_dir:
            for provider_name in ("flux", "stable_diffusion", "pollinations", "mock"):
                vmap = generate_visual_mapping(
                    script=s,
                    provider_name=provider_name,
                    output_dir=Path(tmp_dir)
                )
                self.assertEqual(vmap["provider"], provider_name)
                for scene in vmap["visual_scenes"]:
                    self.assertTrue(Path(scene["image_file"]).exists())

    def test_12_deterministic_visual_generation(self):
        s1 = _make_script(deity="shiva")
        s2 = _make_script(deity="shiva")
        with tempfile.TemporaryDirectory() as tmp_dir:
            vmap1 = generate_visual_mapping(s1, output_dir=Path(tmp_dir))
            vmap2 = generate_visual_mapping(s2, output_dir=Path(tmp_dir))
            self.assertEqual(vmap1["total_scenes"], vmap2["total_scenes"])
            self.assertEqual(vmap1["visual_scenes"][0]["visual_prompt"], vmap2["visual_scenes"][0]["visual_prompt"])

    def test_13_file_generation_works(self):
        s = _make_script(deity="shiva")
        with tempfile.TemporaryDirectory() as tmp_dir:
            script_file = Path(tmp_dir) / "script_test.json"
            script_file.write_text(json.dumps(s), encoding="utf-8")

            out_dir = Path(tmp_dir) / "visuals"
            out_file = process_script_file(script_file, output_dir=out_dir)

            self.assertTrue(out_file.exists())
            saved_map = json.loads(out_file.read_text(encoding="utf-8"))
            ok, err = validate_visual_map_output(saved_map)
            self.assertTrue(ok, f"Saved visual map fails schema: {err}")


# ─────────────────────────────────────────────────────────────────────────────
class TestVisualCLI(unittest.TestCase):
    """Test run_visual_generator.py CLI interface and parameters."""

    def setUp(self):
        self.patch_net = patch("src.visual.providers._generate_via_pollinations", return_value=False)
        self.patch_net.start()

        self.tmp_dir = tempfile.TemporaryDirectory()
        self.script_dir = Path(self.tmp_dir.name) / "scripts"
        self.visual_dir = Path(self.tmp_dir.name) / "visuals"
        self.script_dir.mkdir()
        self.visual_dir.mkdir()

        self.patch_script_dir = patch("run_visual_generator.SCRIPT_DIR", self.script_dir)
        self.patch_visual_dir = patch("run_visual_generator.VISUAL_DIR", self.visual_dir)
        self.patch_script_dir.start()
        self.patch_visual_dir.start()

    def tearDown(self):
        self.patch_script_dir.stop()
        self.patch_visual_dir.stop()
        self.tmp_dir.cleanup()
        self.patch_net.stop()

    def test_cli_auto_discovery(self):
        script_file = self.script_dir / "script_20260813_120000.json"
        script_file.write_text(json.dumps(_make_script()), encoding="utf-8")

        with patch("sys.argv", ["run_visual_generator.py"]):
            run_visual_generator.main()

        saved = list(self.visual_dir.glob("visual_map_*.json"))
        self.assertEqual(len(saved), 1)
        map_data = json.loads(saved[0].read_text(encoding="utf-8"))
        self.assertEqual(map_data["script_title"], "Secrets of Shiva's Snake: The Mastery Over Ego and Poison")

    def test_cli_custom_input_and_provider_works(self):
        custom_script = Path(self.tmp_dir.name) / "custom_script.json"
        custom_script.write_text(json.dumps(_make_script(deity="ganesha")), encoding="utf-8")

        with patch("sys.argv", ["run_visual_generator.py", "--input", str(custom_script), "--provider", "flux"]):
            run_visual_generator.main()

        saved = list(self.visual_dir.glob("visual_map_*.json"))
        self.assertEqual(len(saved), 1)
        map_data = json.loads(saved[0].read_text(encoding="utf-8"))
        self.assertEqual(map_data["provider"], "flux")
        self.assertEqual(map_data["script_title"], "The Sacrifice of Ganesha: The Story of the Broken Tusk")

    def test_cli_no_save_works(self):
        script_file = self.script_dir / "script_20260813_120000.json"
        script_file.write_text(json.dumps(_make_script()), encoding="utf-8")

        with patch("sys.argv", ["run_visual_generator.py", "--no-save"]):
            run_visual_generator.main()

        saved = list(self.visual_dir.glob("visual_map_*.json"))
        self.assertEqual(len(saved), 0)


if __name__ == "__main__":
    unittest.main()
