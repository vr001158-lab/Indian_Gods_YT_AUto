# tests/test_landscape_publishing.py
# Automated tests for Landscape Long-Video Profile & Asset Validation
#
# Covers:
#  - Correct 16:9 landscape resolution (1920x1080)
#  - Landscape duration bounds: min 120s, max 300s, target 180s-240s
#  - Portrait assets rejected for landscape long videos
#  - Missing landscape assets cause graceful failure (no silent fallback to assets/gods/)
#  - Landscape asset selection and timeline building from assets/gods_landscape_long_video/<deity>/
#  - Existing Shorts behavior preserved (9:16, 1080x1920, duration < 180s)

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from PIL import Image

from src.video.format_config import (
    get_format_config,
    validate_content_type,
    validate_duration_for_content_type,
    validate_resolution_for_content_type,
)
from src.assets.validator import (
    is_landscape_dimensions,
    validate_landscape_asset,
    validate_image_asset,
)
from src.assets.scanner import (
    scan_gods_landscape_assets,
)
from src.assets.selector import (
    select_landscape_scene_assets,
    build_landscape_visual_timeline,
    build_deity_visual_timeline,
)
from src.assets.resolver import (
    create_scene_asset_plan,
)
from src.video.composer import (
    MockVideoComposer,
    FFmpegVideoComposer,
    format_caption_text,
)


class TestLandscapePublishing(unittest.TestCase):

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.landscape_gods_dir = self.temp_dir / "gods_landscape_long_video"
        self.deities = ["lord_shiva", "krishna", "ganesha", "hanuman"]
        for d in self.deities:
            (self.landscape_gods_dir / d).mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _create_image(self, path: Path, width: int, height: int, color=(100, 150, 200)) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (width, height), color=color)
        img.save(path, format="PNG")
        return path

    # ── 1. Landscape 16:9 Resolution & Duration Rules ──────────────────────────

    def test_landscape_resolution_config(self):
        """Landscape profile must use 1920x1080 resolution and 16:9 aspect ratio."""
        cfg = get_format_config("long")
        self.assertEqual(cfg["resolution"], "1920x1080")
        self.assertEqual(cfg["aspect_ratio"], "16:9")
        self.assertEqual(cfg["width"], 1920)
        self.assertEqual(cfg["height"], 1080)

        ok, _ = validate_resolution_for_content_type("1920x1080", "long")
        self.assertTrue(ok)
        bad_res, _ = validate_resolution_for_content_type("1080x1920", "long")
        self.assertFalse(bad_res)

    def test_landscape_duration_minimum_120_seconds(self):
        """Duration under 120s must be rejected for long videos."""
        self.assertFalse(validate_duration_for_content_type(60, "long")[0])
        self.assertFalse(validate_duration_for_content_type(119.9, "long")[0])
        self.assertTrue(validate_duration_for_content_type(120.0, "long")[0])

    def test_landscape_duration_maximum_300_seconds(self):
        """Duration over 300s must be rejected for long videos."""
        self.assertTrue(validate_duration_for_content_type(300.0, "long")[0])
        self.assertFalse(validate_duration_for_content_type(300.1, "long")[0])
        self.assertFalse(validate_duration_for_content_type(600.0, "long")[0])

    def test_landscape_target_duration_passes(self):
        """Target duration (180s - 240s) must pass cleanly."""
        for target in (180.0, 200.0, 210.0, 240.0):
            ok, msg = validate_duration_for_content_type(target, "long")
            self.assertTrue(ok, f"Target duration {target}s failed: {msg}")

    # ── 2. Landscape Asset Validation ──────────────────────────────────────────

    def test_is_landscape_dimensions(self):
        """Validates is_landscape_dimensions identifies landscape vs portrait."""
        self.assertTrue(is_landscape_dimensions(1920, 1080))
        self.assertTrue(is_landscape_dimensions(1280, 720))
        self.assertTrue(is_landscape_dimensions(1080, 1080))  # square is >=
        self.assertFalse(is_landscape_dimensions(1080, 1920)) # portrait
        self.assertFalse(is_landscape_dimensions(720, 1280))  # portrait

    def test_portrait_assets_rejected_for_landscape(self):
        """Portrait image asset must be rejected by validate_landscape_asset."""
        portrait_file = self.temp_dir / "portrait.png"
        self._create_image(portrait_file, 1080, 1920)

        meta = validate_image_asset(portrait_file)
        ok, reason = validate_landscape_asset(meta)
        self.assertFalse(ok)
        self.assertIn("Asset is portrait", reason)

    def test_landscape_assets_accepted(self):
        """16:9 landscape image asset must be accepted by validate_landscape_asset."""
        landscape_file = self.temp_dir / "landscape.png"
        self._create_image(landscape_file, 1920, 1080)

        meta = validate_image_asset(landscape_file)
        ok, reason = validate_landscape_asset(meta)
        self.assertTrue(ok, reason)

    # ── 3. Landscape Asset Scanner & Selection ─────────────────────────────────

    def test_scanner_rejects_portrait_assets_in_landscape_dir(self):
        """scan_gods_landscape_assets must ignore/reject portrait images."""
        deity_dir = self.landscape_gods_dir / "lord_shiva"
        self._create_image(deity_dir / "shiva_land_1.png", 1920, 1080)
        self._create_image(deity_dir / "shiva_land_2.png", 1280, 720)
        self._create_image(deity_dir / "shiva_port_1.png", 1080, 1920)  # Portrait

        results = scan_gods_landscape_assets(self.landscape_gods_dir)
        shiva_imgs = results["deities"]["lord_shiva"]["images"]
        self.assertEqual(len(shiva_imgs), 2)
        # Verify portrait image was rejected
        paths = [img["path"] for img in shiva_imgs]
        self.assertTrue(any("shiva_land_1" in p for p in paths))
        self.assertTrue(any("shiva_land_2" in p for p in paths))
        self.assertFalse(any("shiva_port_1" in p for p in paths))

    def test_missing_landscape_assets_causes_graceful_failure(self):
        """When a deity has no landscape assets, selector must fail gracefully without fallback to assets/gods/."""
        # ganesha folder is empty
        scene_scripts = [{"scene": 1, "script_text": "Ganesha narration", "duration_seconds": 30}]
        with self.assertRaises(ValueError) as ctx:
            select_landscape_scene_assets(
                deity_key="ganesha",
                scene_scripts=scene_scripts,
                gods_dir=self.landscape_gods_dir,
            )
        self.assertIn("No valid landscape visual assets found for deity 'ganesha'", str(ctx.exception))
        self.assertIn("Fallback to portrait assets/gods/ is strictly prohibited", str(ctx.exception))

    def test_landscape_asset_selection_and_timeline(self):
        """Landscape timeline must be constructed with continuous coverage for target duration."""
        deity_dir = self.landscape_gods_dir / "krishna"
        self._create_image(deity_dir / "krishna_1.png", 1920, 1080)
        self._create_image(deity_dir / "krishna_2.png", 1920, 1080)

        timeline = build_landscape_visual_timeline(
            deity_key="krishna",
            target_duration=180.0,
            gods_dir=self.landscape_gods_dir,
        )
        total_dur = sum(s["duration_seconds"] for s in timeline)
        self.assertAlmostEqual(total_dur, 180.0, places=1)
        self.assertTrue(all(s["source"] == "landscape_repository" for s in timeline))

    def test_resolver_routes_long_to_landscape_folder(self):
        """create_scene_asset_plan must select landscape assets when content_type='long'."""
        deity_dir = self.landscape_gods_dir / "lord_shiva"
        self._create_image(deity_dir / "shiva_1.png", 1920, 1080)

        script = {
            "title": "Secrets of Shiva",
            "content_type": "long",
            "format": "narrated",
            "duration_seconds": 180,
            "scene_scripts": [
                {"scene": 1, "script_text": "Scene 1", "duration_seconds": 60},
                {"scene": 2, "script_text": "Scene 2", "duration_seconds": 60},
                {"scene": 3, "script_text": "Scene 3", "duration_seconds": 60},
            ],
            "approval_metadata": {
                "approved_for_generation": True,
                "data_source": "youtube_api",
                "confidence": "high",
                "selected_topic": "Secrets of Shiva",
                "deity": "lord_shiva",
            },
        }

        plan = create_scene_asset_plan(
            script=script,
            gods_dir=self.landscape_gods_dir,
            output_dir=self.temp_dir / "visuals",
        )
        self.assertEqual(len(plan["scenes"]), 3)
        self.assertEqual(plan["scenes"][0]["source"], "landscape_repository")

    # ── 4. Shorts Behavior Preserved ──────────────────────────────────────────

    def test_shorts_behavior_preserved(self):
        """Verifies Shorts format config remains 1080x1920, 9:16, max 180s."""
        cfg = get_format_config("short")
        self.assertEqual(cfg["resolution"], "1080x1920")
        self.assertEqual(cfg["aspect_ratio"], "9:16")
        self.assertEqual(cfg["max_duration_seconds"], 180)

        ok, _ = validate_resolution_for_content_type("1080x1920", "short")
        self.assertTrue(ok)
        ok_dur, _ = validate_duration_for_content_type(45.0, "short")
        self.assertTrue(ok_dur)


if __name__ == "__main__":
    unittest.main()
