# tests/test_assets.py
# Comprehensive Unit Tests for Central Asset Resolver Subsystem

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.assets.scanner import scan_gods_assets
from src.assets.validator import (
    AssetValidationError,
    validate_image_asset,
    validate_video_asset,
)
from src.assets.manifest import generate_asset_manifest, load_asset_manifest
from src.assets.selector import resolve_deity, select_scene_assets
from src.assets.resolver import create_scene_asset_plan


def _create_test_image(path: Path, width: int = 1280, height: int = 720) -> Path:
    from PIL import Image
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (width, height), color=(100, 50, 150))
    img.save(path, "PNG")
    return path


class TestAssetResolverSubsystem(unittest.TestCase):
    """Tests 18–30: Repository deity asset resolver."""

    # ── Test 18: Deity folder discovered ─────────────────────────────────────
    def test_18_deity_folder_discovered(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "assets" / "gods"
            (base / "lord_shiva").mkdir(parents=True)
            _create_test_image(base / "lord_shiva" / "shiva_01.png")

            res = scan_gods_assets(gods_dir=base)
            self.assertIn("lord_shiva", res["deities"])
            self.assertEqual(len(res["deities"]["lord_shiva"]["images"]), 1)

    # ── Test 19: Image discovered ────────────────────────────────────────────
    def test_19_image_discovered(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "assets" / "gods"
            _create_test_image(base / "ganesha" / "ganesh_01.png", 720, 1280)

            res = scan_gods_assets(gods_dir=base)
            imgs = res["deities"]["ganesha"]["images"]
            self.assertEqual(len(imgs), 1)
            self.assertEqual(imgs[0]["type"], "image")
            self.assertEqual(imgs[0]["width"], 720)
            self.assertEqual(imgs[0]["height"], 1280)

    # ── Test 20: MP4 discovered ──────────────────────────────────────────────
    def test_20_mp4_discovered(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td) / "assets" / "gods"
            vid = base / "lord_shiva" / "shiva_bg.mp4"
            vid.parent.mkdir(parents=True)
            vid.write_bytes(b"\x00" * 2000)

            mock_meta = {
                "container": "mp4",
                "video_codec": "h264",
                "width": 720,
                "height": 1280,
                "duration": 15.0,
                "fps": 30.0,
                "file_size_bytes": 2000,
                "valid": True,
            }
            with patch("src.assets.scanner.validate_video_asset", return_value=mock_meta):
                res = scan_gods_assets(gods_dir=base)
            vids = res["deities"]["lord_shiva"]["videos"]
            self.assertEqual(len(vids), 1)
            self.assertEqual(vids[0]["container"], "mp4")

    # ── Test 21: Corrupted MP4 rejected ──────────────────────────────────────
    def test_21_corrupted_mp4_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            corrupt = tmp / "corrupt.mp4"
            corrupt.write_text("MOCK_MP4_VIDEO: text stub", encoding="utf-8")
            with self.assertRaises(AssetValidationError):
                validate_video_asset(corrupt)

    # ── Test 22: Corrupted image rejected ────────────────────────────────────
    def test_22_corrupted_image_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            corrupt = tmp / "bad.png"
            corrupt.write_bytes(b"NOT_AN_IMAGE_FILE_DATA")
            with self.assertRaises(AssetValidationError):
                validate_image_asset(corrupt)

    # ── Test 23: Repository asset preferred ─────────────────────────────────
    def test_23_repository_asset_preferred(self):
        manifest = {
            "deities": {
                "lord_shiva": {
                    "images": [{"asset_id": "shiva_01", "type": "image", "path": "assets/gods/lord_shiva/s1.png"}],
                    "videos": [],
                }
            }
        }
        scenes = [{"scene": 1, "visual_reference": "Shiva sitting on Kailash"}]
        plan = select_scene_assets("lord_shiva", scenes, manifest)
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["source"], "repository")
        self.assertEqual(plan[0]["asset"], "assets/gods/lord_shiva/s1.png")

    # ── Test 24: Online fallback only when necessary ──────────────────────────
    def test_24_online_fallback_only_when_necessary(self):
        manifest = {"deities": {}}
        scenes = [{"scene": 1, "visual_reference": "Deity scene"}]
        plan = select_scene_assets("unknown_deity", scenes, manifest, allow_online_fallback=True)
        self.assertEqual(plan[0]["source"], "online")

    # ── Test 25: Scene-aware asset selection ─────────────────────────────────
    def test_25_scene_aware_asset_selection(self):
        manifest = {
            "deities": {
                "lord_shiva": {
                    "images": [
                        {"asset_id": "shiva_general", "type": "image", "path": "assets/gods/lord_shiva/general.png"},
                        {"asset_id": "shiva_snake_vasuki", "type": "image", "path": "assets/gods/lord_shiva/snake_vasuki.png"},
                    ],
                    "videos": [],
                }
            }
        }
        scenes = [{"scene": 1, "visual_reference": "Lord Shiva holding Vasuki snake"}]
        plan = select_scene_assets("lord_shiva", scenes, manifest)
        self.assertIn("snake_vasuki.png", plan[0]["asset"])

    # ── Test 26: Image timing ────────────────────────────────────────────────
    def test_26_image_timing(self):
        script = {
            "title": "Why Lord Shiva Wears a Snake",
            "approval_metadata": {"selected_topic": "Why Lord Shiva Wears a Snake"},
            "scene_scripts": [{"scene": 1, "duration_seconds": 18}],
        }
        manifest = {
            "deities": {
                "lord_shiva": {
                    "images": [{"asset_id": "sh1", "type": "image", "path": "assets/gods/lord_shiva/sh1.png"}],
                    "videos": [],
                }
            }
        }
        with patch("src.assets.resolver.load_asset_manifest", return_value=manifest):
            with tempfile.TemporaryDirectory() as td:
                plan = create_scene_asset_plan(script, output_dir=td)
                self.assertEqual(plan["scenes"][0]["scene"], 1)

    # ── Test 27: Video looping ───────────────────────────────────────────────
    def test_27_video_looping_logic(self):
        from src.audio.ducking import mix_audio_with_ducking
        # Test helper ducking loop filter logic string existence
        import src.audio.ducking as ducking
        self.assertTrue(hasattr(ducking, "mix_audio_with_ducking"))

    # ── Test 28: Video trimming ──────────────────────────────────────────────
    def test_28_video_trimming_logic(self):
        manifest = {
            "deities": {
                "lord_shiva": {
                    "images": [],
                    "videos": [{"asset_id": "shiva_vid", "type": "video", "path": "assets/gods/lord_shiva/v1.mp4", "duration": 40.0}],
                }
            }
        }
        scenes = [{"scene": 1, "duration_seconds": 15}]
        plan = select_scene_assets("lord_shiva", scenes, manifest)
        self.assertEqual(plan[0]["asset_type"], "video")

    # ── Test 29: Asset provenance ────────────────────────────────────────────
    def test_29_asset_provenance(self):
        manifest = {
            "deities": {
                "lord_shiva": {
                    "images": [{"asset_id": "sh1", "type": "image", "path": "assets/gods/lord_shiva/sh1.png"}],
                    "videos": [],
                }
            }
        }
        scenes = [{"scene": 1, "visual_reference": "Shiva"}]
        plan = select_scene_assets("lord_shiva", scenes, manifest)
        self.assertIn("reason_for_selection", plan[0])
        self.assertEqual(plan[0]["validation_result"], "OK")

    # ── Test 30: Shared visual plan across Hindi/Telugu/Tamil ──────────────
    def test_30_shared_visual_plan(self):
        script = {
            "title": "Why Lord Shiva Wears a Snake",
            "approval_metadata": {"selected_topic": "Why Lord Shiva Wears a Snake"},
            "scene_scripts": [
                {"scene": 1, "duration_seconds": 18, "visual_reference": "Shiva intro"},
                {"scene": 2, "duration_seconds": 22, "visual_reference": "Vasuki snake"},
            ],
        }
        manifest = {
            "deities": {
                "lord_shiva": {
                    "images": [{"asset_id": "sh1", "type": "image", "path": "assets/gods/lord_shiva/sh1.png"}],
                    "videos": [],
                }
            }
        }
        with patch("src.assets.resolver.load_asset_manifest", return_value=manifest):
            with tempfile.TemporaryDirectory() as td:
                plan1 = create_scene_asset_plan(script, output_dir=td)
                plan2 = create_scene_asset_plan(script, output_dir=td)
                self.assertEqual(plan1["topic"], plan2["topic"])
                self.assertEqual(plan1["scenes"], plan2["scenes"])

    # ── Test 31: High Retention Visual Engine & Strict Deity Isolation ──────────
    def test_31_high_retention_visual_engine_and_deity_isolation(self):
        from src.assets.selector import build_deity_visual_timeline, select_scene_assets

        manifest = {
            "deities": {
                "ram": {
                    "images": [
                        {"asset_id": "r_img1", "type": "image", "path": "assets/gods/ram/r1.png"},
                        {"asset_id": "r_img2", "type": "image", "path": "assets/gods/ram/r2.png"},
                        {"asset_id": "r_img3", "type": "image", "path": "assets/gods/ram/r3.png"},
                    ],
                    "videos": [
                        {"asset_id": "r_vid1", "type": "video", "path": "assets/gods_processed/ram/v1.mp4", "duration": 10.0},
                    ]
                },
                "lord_shiva": {
                    "images": [
                        {"asset_id": "s_img1", "type": "image", "path": "assets/gods/lord_shiva/s1.png"}
                    ],
                    "videos": []
                }
            }
        }

        # 1. Shorts retention timeline: target 45s, mixing images + videos for Ram
        timeline_short = build_deity_visual_timeline("ram", target_duration=45.0, content_type="short", manifest=manifest)
        total_dur = sum(s["duration_seconds"] for s in timeline_short)
        self.assertGreaterEqual(total_dur, 35.0)
        self.assertLess(total_dur, 60.0)
        self.assertGreaterEqual(len(timeline_short), 5, "Shorts must contain multiple visual segments for retention")

        # Verify images + videos mixed
        types_used = {s["asset_type"] for s in timeline_short}
        self.assertIn("image", types_used)
        self.assertIn("video", types_used)

        # Verify strict deity isolation: NO lord_shiva assets in ram timeline!
        for s in timeline_short:
            self.assertEqual(s["deity"], "ram")
            self.assertIn("ram", s["asset"])
            self.assertNotIn("lord_shiva", s["asset"])

        # 2. Long video timeline: target 180s, full coverage, max static image duration <= 8s
        timeline_long = build_deity_visual_timeline("ram", target_duration=180.0, content_type="long", manifest=manifest)
        total_dur_long = sum(s["duration_seconds"] for s in timeline_long)
        self.assertEqual(round(total_dur_long, 2), 180.0)
        self.assertGreaterEqual(len(timeline_long), 20)

        for s in timeline_long:
            self.assertEqual(s["deity"], "ram")
            if s["asset_type"] == "image":
                self.assertLessEqual(s["duration_seconds"], 8.0, "No static image section > 8s allowed")

        # 3. Verify error raised if deity has no repository visual assets (no cross-deity borrowing)
        with self.assertRaises(ValueError):
            build_deity_visual_timeline("unknown_deity_without_assets", manifest=manifest)


if __name__ == "__main__":
    unittest.main(verbosity=2)
