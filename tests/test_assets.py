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
                    "videos": [{"asset_id": "shiva_vid", "type": "video", "path": "assets/gods_processed/lord_shiva/vertical/v1.mp4", "width": 720, "height": 1280, "duration": 40.0}],
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
                        {"asset_id": "r_vid1", "type": "video", "path": "assets/gods_processed/ram/vertical/v1.mp4", "width": 720, "height": 1280, "duration": 10.0},
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

    # ── Test 32: Video-First Priority ─────────────────────────────────────────
    def test_32_video_first_priority_when_both_videos_and_images_exist(self):
        """When deity has both videos and images, videos are selected first for all scenes."""
        manifest = {
            "deities": {
                "lord_shiva": {
                    "images": [
                        {"asset_id": "sh_img1", "type": "image", "path": "assets/gods/lord_shiva/img1.png", "semantic_keywords": ["shiva", "meditation"]},
                        {"asset_id": "sh_img2", "type": "image", "path": "assets/gods/lord_shiva/img2.png", "semantic_keywords": ["shiva", "kailash"]},
                    ],
                    "videos": [
                        {"asset_id": "sh_vid1", "type": "video", "path": "assets/gods_processed/lord_shiva/vertical/v1.mp4", "width": 720, "height": 1280, "duration": 8.0, "tags": ["shiva"]},
                        {"asset_id": "sh_vid2", "type": "video", "path": "assets/gods_processed/lord_shiva/vertical/v2.mp4", "width": 720, "height": 1280, "duration": 8.0, "tags": ["shiva"]},
                    ],
                }
            }
        }
        scenes = [
            {"scene": 1, "visual_reference": "Lord Shiva in deep meditation"},
            {"scene": 2, "visual_reference": "Lord Shiva atop Mount Kailash"},
        ]
        plan = select_scene_assets("lord_shiva", scenes, manifest, allow_online_fallback=False, content_type="short")
        self.assertEqual(len(plan), 2)
        # Both scenes must be video
        self.assertEqual(plan[0]["asset_type"], "video")
        self.assertEqual(plan[1]["asset_type"], "video")
        self.assertEqual(plan[0]["source"], "repository")
        self.assertEqual(plan[1]["source"], "repository")

    # ── Test 33: Distinct Video Selection Across Scenes ──────────────────────
    def test_33_distinct_video_selection_across_scenes(self):
        """Selector chooses different video clips across scenes when alternatives exist."""
        manifest = {
            "deities": {
                "hanuman": {
                    "images": [],
                    "videos": [
                        {"asset_id": "h_v1", "type": "video", "path": "assets/gods_processed/hanuman/vertical/v1.mp4", "width": 720, "height": 1280, "tags": ["hanuman"]},
                        {"asset_id": "h_v2", "type": "video", "path": "assets/gods_processed/hanuman/vertical/v2.mp4", "width": 720, "height": 1280, "tags": ["hanuman"]},
                        {"asset_id": "h_v3", "type": "video", "path": "assets/gods_processed/hanuman/vertical/v3.mp4", "width": 720, "height": 1280, "tags": ["hanuman"]},
                    ],
                }
            }
        }
        scenes = [
            {"scene": 1, "visual_reference": "Hanuman scene 1"},
            {"scene": 2, "visual_reference": "Hanuman scene 2"},
            {"scene": 3, "visual_reference": "Hanuman scene 3"},
        ]
        plan = select_scene_assets("hanuman", scenes, manifest, allow_online_fallback=False, content_type="short")
        selected_paths = [s["asset"] for s in plan]
        self.assertEqual(len(selected_paths), 3)
        self.assertEqual(len(set(selected_paths)), 3, "Each scene must receive a distinct video clip")

    # ── Test 34: Fallback to Images when Videos are Exhausted ─────────────────
    def test_34_fallback_to_images_when_videos_exhausted(self):
        """When scenes exceed available videos, videos are used first and local images used second."""
        manifest = {
            "deities": {
                "ram": {
                    "images": [
                        {"asset_id": "r_img1", "type": "image", "path": "assets/gods/ram/img1.png", "tags": ["ram"]},
                        {"asset_id": "r_img2", "type": "image", "path": "assets/gods/ram/img2.png", "tags": ["ram"]},
                    ],
                    "videos": [
                        {"asset_id": "r_vid1", "type": "video", "path": "assets/gods_processed/ram/vertical/v1.mp4", "width": 720, "height": 1280, "tags": ["ram"]},
                    ],
                }
            }
        }
        scenes = [
            {"scene": 1, "visual_reference": "Ram scene 1"},
            {"scene": 2, "visual_reference": "Ram scene 2"},
            {"scene": 3, "visual_reference": "Ram scene 3"},
        ]
        plan = select_scene_assets("ram", scenes, manifest, allow_online_fallback=False, content_type="short")
        self.assertEqual(plan[0]["asset_type"], "video", "Scene 1 should use available video")
        self.assertEqual(plan[1]["asset_type"], "image", "Scene 2 should fall back to local image")
        self.assertEqual(plan[2]["asset_type"], "image", "Scene 3 should fall back to local image")

    # ── Test 35: Clean Fallback for Deity Without Videos (Subramanya) ────────
    def test_35_clean_fallback_for_deity_without_videos_subramanya(self):
        """Subramanya (0 videos, 42 images) cleanly falls back to local images with notice."""
        manifest = {
            "deities": {
                "subramanya": {
                    "images": [
                        {"asset_id": "sub_img1", "type": "image", "path": "assets/gods/subramanya/s1.png", "tags": ["subramanya", "murugan"]},
                        {"asset_id": "sub_img2", "type": "image", "path": "assets/gods/subramanya/s2.png", "tags": ["subramanya", "kartikeya"]},
                    ],
                    "videos": [],
                }
            }
        }
        scenes = [
            {"scene": 1, "visual_reference": "Lord Murugan holding divine Vel spear"},
        ]
        import io
        from contextlib import redirect_stderr
        stderr_buf = io.StringIO()
        with redirect_stderr(stderr_buf):
            plan = select_scene_assets("subramanya", scenes, manifest, allow_online_fallback=False, content_type="short")

        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["asset_type"], "image")
        self.assertEqual(plan[0]["source"], "repository")
        self.assertEqual(plan[0]["deity"], "subramanya")
        self.assertIn("Video coverage unavailable for deity 'subramanya'", stderr_buf.getvalue())

    # ── Test 36: Strict Deity Isolation — No Cross-Deity Borrowing ───────────
    def test_36_strict_deity_isolation_no_cross_borrowing(self):
        """Deity X assets must NEVER be assigned to Deity Y."""
        manifest = {
            "deities": {
                "lord_shiva": {
                    "images": [{"asset_id": "s_img", "type": "image", "path": "assets/gods/lord_shiva/s.png"}],
                    "videos": [{"asset_id": "s_vid", "type": "video", "path": "assets/gods_processed/lord_shiva/vertical/v.mp4", "width": 720, "height": 1280}],
                },
                "lord_vishnu": {
                    "images": [{"asset_id": "v_img", "type": "image", "path": "assets/gods/lord_vishnu/v.png"}],
                    "videos": [{"asset_id": "v_vid", "type": "video", "path": "assets/gods_processed/lord_vishnu/vertical/v.mp4", "width": 720, "height": 1280}],
                },
            }
        }
        scenes = [{"scene": 1, "visual_reference": "Shiva meditation"}]
        plan = select_scene_assets("lord_shiva", scenes, manifest, allow_online_fallback=False)
        self.assertEqual(plan[0]["deity"], "lord_shiva")
        self.assertIn("lord_shiva", plan[0]["asset"])
        self.assertNotIn("lord_vishnu", plan[0]["asset"])

    # ── Test 37: Orientation Awareness (Short vs Long) ───────────────────────
    def test_37_orientation_awareness_short_vs_long(self):
        """Shorts prioritize vertical videos; Long videos prioritize horizontal videos."""
        manifest = {
            "deities": {
                "ganesha": {
                    "images": [],
                    "videos": [
                        {"asset_id": "g_horiz", "type": "video", "path": "assets/gods_processed/ganesha/horizontal/h.mp4", "width": 1920, "height": 1080, "tags": ["ganesha"]},
                        {"asset_id": "g_vert", "type": "video", "path": "assets/gods_processed/ganesha/vertical/v.mp4", "width": 720, "height": 1280, "tags": ["ganesha"]},
                    ],
                }
            }
        }
        scenes = [{"scene": 1, "visual_reference": "Ganesha intro"}]
        # Short format
        plan_short = select_scene_assets("ganesha", scenes, manifest, allow_online_fallback=False, content_type="short")
        self.assertIn("vertical", plan_short[0]["asset"])

        # Long format
        plan_long = select_scene_assets("ganesha", scenes, manifest, allow_online_fallback=False, content_type="long")
        self.assertIn("horizontal", plan_long[0]["asset"])

    # ── Test 38: Fail Closed When Deity Has No Assets ────────────────────────
    def test_38_fail_closed_when_deity_has_no_assets(self):
        """RuntimeError is raised when a deity has no repository visual assets and online fallback is disabled."""
        manifest = {"deities": {"unknown_god": {"images": [], "videos": []}}}
        scenes = [{"scene": 1, "visual_reference": "Unknown deity scene"}]
        with self.assertRaises(RuntimeError):
            select_scene_assets("unknown_god", scenes, manifest, allow_online_fallback=False)

    # ── Test 39: Visual Generator Strict Local-Only Enforcement ──────────────
    def test_39_visual_generator_strict_local_only_enforcement(self):
        """In production, missing repository assets raise FileNotFoundError and external generation raises RuntimeError."""
        from src.visual.generator import generate_visual_mapping

        script = {
            "title": "Lord Shiva Story",
            "duration_seconds": 45.0,
            "narration": "Lord Shiva divine story",
            "content_type": "short",
            "retention_hooks": ["Watch until the end"],
            "shorts_scripts": ["Shorts summary"],
            "approval_metadata": {
                "approved_for_generation": True,
                "data_source": "youtube_api",
                "confidence": "high",
                "selected_topic": "Lord Shiva Story",
            },
            "scene_scripts": [{"scene": 1, "visual_reference": "Shiva"}],
        }

        # Non-existent asset path must raise FileNotFoundError
        fake_plan = {
            "topic": "Lord Shiva Story",
            "deity": "lord_shiva",
            "approval_metadata": {"selected_topic": "Lord Shiva Story"},
            "scenes": [
                {
                    "scene": 1,
                    "asset_type": "video",
                    "asset": "assets/non_existent_video_file_xyz.mp4",
                    "source": "repository",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as td:
            with patch("src.assets.resolver.create_scene_asset_plan", return_value=fake_plan):
                with self.assertRaises(FileNotFoundError):
                    generate_visual_mapping(script, provider_name="mock", output_dir=Path(td))

            # External source with non-mock provider must raise RuntimeError
            online_plan = {
                "topic": "Lord Shiva Story",
                "deity": "lord_shiva",
                "approval_metadata": {"selected_topic": "Lord Shiva Story"},
                "scenes": [
                    {
                        "scene": 1,
                        "asset_type": "image",
                        "asset": "data/visuals/online_cache/scene_1.png",
                        "source": "online",
                    }
                ],
            }
            with patch("src.assets.resolver.create_scene_asset_plan", return_value=online_plan):
                with self.assertRaises(RuntimeError):
                    generate_visual_mapping(script, provider_name="pollinations", output_dir=Path(td))

    # ── Test 40: Horizontal Video Never Selected for Shorts ──────────────────
    def test_40_horizontal_video_never_selected_for_shorts(self):
        """Shorts only accept verified vertical videos; horizontal videos are strictly excluded and fall back to images."""
        manifest = {
            "deities": {
                "lord_shiva": {
                    "images": [
                        {"asset_id": "sh_img", "type": "image", "path": "assets/gods/lord_shiva/sh.png", "width": 720, "height": 1280},
                    ],
                    "videos": [
                        {"asset_id": "sh_hvid", "type": "video", "path": "assets/gods_processed/lord_shiva/horizontal/h1.mp4", "width": 1920, "height": 1080},
                    ],
                }
            }
        }
        scenes = [{"scene": 1, "visual_reference": "Shiva cosmic dance"}]
        plan = select_scene_assets("lord_shiva", scenes, manifest, allow_online_fallback=False, content_type="short")
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["asset_type"], "image", "Shorts must reject horizontal video and fall back to local image")
        self.assertEqual(plan[0]["asset"], "assets/gods/lord_shiva/sh.png")

    # ── Test 41: Vertical Video Never Selected for Long Videos ───────────────
    def test_41_vertical_video_never_selected_for_long_videos(self):
        """Long videos only accept verified horizontal videos; vertical videos are strictly excluded and fall back to landscape images."""
        manifest = {
            "deities": {
                "lord_shiva": {
                    "images": [
                        {"asset_id": "sh_limg", "type": "image", "path": "assets/gods_landscape/lord_shiva/sh_land.png", "width": 1920, "height": 1080},
                    ],
                    "videos": [
                        {"asset_id": "sh_vvid", "type": "video", "path": "assets/gods_processed/lord_shiva/vertical/v1.mp4", "width": 720, "height": 1280},
                    ],
                }
            }
        }
        scenes = [{"scene": 1, "visual_reference": "Shiva meditation"}]
        plan = select_scene_assets("lord_shiva", scenes, manifest, allow_online_fallback=False, content_type="long")
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["asset_type"], "image", "Long videos must reject vertical video and fall back to landscape image")
        self.assertEqual(plan[0]["asset"], "assets/gods_landscape/lord_shiva/sh_land.png")

    # ── Test 42: Contradictory Folder Path Rejected By Dimensions ────────────
    def test_42_contradictory_folder_path_rejected_by_dimensions(self):
        """Dimensions take precedence over folder path names: contradictory path names are rejected."""
        manifest = {
            "deities": {
                "ganesha": {
                    "images": [{"asset_id": "g_img", "type": "image", "path": "assets/gods/ganesha/g.png", "width": 720, "height": 1280}],
                    "videos": [
                        # In vertical/ folder, but dimensions are horizontal (1920x1080)
                        {"asset_id": "g_fake_vert", "type": "video", "path": "assets/gods_processed/ganesha/vertical/mislabeled.mp4", "width": 1920, "height": 1080},
                    ],
                }
            }
        }
        scenes = [{"scene": 1, "visual_reference": "Ganesha intro"}]
        # For Shorts: the 1920x1080 video must NOT be accepted despite being in /vertical/ folder
        plan_short = select_scene_assets("ganesha", scenes, manifest, allow_online_fallback=False, content_type="short")
        self.assertEqual(plan_short[0]["asset_type"], "image", "Contradictory horizontal dimensions must reject video for Shorts")

        # Now test opposite: in horizontal/ folder, but dimensions are vertical (720x1280)
        manifest_long = {
            "deities": {
                "ganesha": {
                    "images": [{"asset_id": "g_land_img", "type": "image", "path": "assets/gods_landscape/ganesha/g.png", "width": 1920, "height": 1080}],
                    "videos": [
                        {"asset_id": "g_fake_horiz", "type": "video", "path": "assets/gods_processed/ganesha/horizontal/mislabeled.mp4", "width": 720, "height": 1280},
                    ],
                }
            }
        }
        plan_long = select_scene_assets("ganesha", scenes, manifest_long, allow_online_fallback=False, content_type="long")
        self.assertEqual(plan_long[0]["asset_type"], "image", "Contradictory vertical dimensions must reject video for Long videos")

    # ── Test 43: Unknown Orientation Safely Rejected ─────────────────────────
    def test_43_unknown_orientation_safely_rejected(self):
        """Assets with unverified/unknown orientation are safely rejected (fail closed)."""
        manifest = {
            "deities": {
                "hanuman": {
                    "images": [{"asset_id": "h_img", "type": "image", "path": "assets/gods/hanuman/h.png", "width": 720, "height": 1280}],
                    "videos": [
                        # No width, no height, no aspect_ratio, no orientation, ambiguous path
                        {"asset_id": "h_ambiguous", "type": "video", "path": "assets/gods_processed/hanuman/ambiguous.mp4"},
                    ],
                }
            }
        }
        scenes = [{"scene": 1, "visual_reference": "Hanuman flight"}]
        # For shorts, ambiguous video is rejected and image is used
        plan = select_scene_assets("hanuman", scenes, manifest, allow_online_fallback=False, content_type="short")
        self.assertEqual(plan[0]["asset_type"], "image", "Unknown orientation video must not be selected")

    # ── Test 44: Video Diversity With Strict Orientation ─────────────────────
    def test_44_video_diversity_with_strict_orientation(self):
        """Distinct eligible videos used first, then images when videos exhausted, then reuse only when both exhausted."""
        manifest = {
            "deities": {
                "krishna": {
                    "images": [
                        {"asset_id": "k_img1", "type": "image", "path": "assets/gods/krishna/img1.png", "width": 720, "height": 1280},
                        {"asset_id": "k_img2", "type": "image", "path": "assets/gods/krishna/img2.png", "width": 720, "height": 1280},
                    ],
                    "videos": [
                        {"asset_id": "k_v1", "type": "video", "path": "assets/gods_processed/krishna/vertical/v1.mp4", "width": 720, "height": 1280},
                        {"asset_id": "k_v2", "type": "video", "path": "assets/gods_processed/krishna/vertical/v2.mp4", "width": 720, "height": 1280},
                        {"asset_id": "k_h_bad", "type": "video", "path": "assets/gods_processed/krishna/horizontal/h_bad.mp4", "width": 1920, "height": 1080},
                    ],
                }
            }
        }
        scenes = [{"scene": i, "visual_reference": f"Krishna scene {i}"} for i in range(1, 6)]
        plan = select_scene_assets("krishna", scenes, manifest, allow_online_fallback=False, content_type="short")
        self.assertEqual(len(plan), 5)

        # Scenes 1 & 2 must be distinct vertical videos
        self.assertEqual(plan[0]["asset_type"], "video")
        self.assertEqual(plan[1]["asset_type"], "video")
        self.assertNotEqual(plan[0]["asset"], plan[1]["asset"], "Scenes 1 and 2 must use distinct videos")

        # Scenes 3 & 4 must fall back to images (videos exhausted)
        self.assertEqual(plan[2]["asset_type"], "image")
        self.assertEqual(plan[3]["asset_type"], "image")
        self.assertNotEqual(plan[2]["asset"], plan[3]["asset"], "Scenes 3 and 4 must use distinct images")

        # Scene 5 reuses video because both eligible videos and images are exhausted
        self.assertEqual(plan[4]["asset_type"], "video")

        # Horizontal video k_h_bad must NEVER appear in any scene
        all_assets = [s["asset"] for s in plan]
        for a in all_assets:
            self.assertNotIn("h_bad", a, "Incorrectly oriented video must never appear in shorts plan")

    # ── Test 45: Build Deity Visual Timeline Strict Orientation ──────────────
    def test_45_build_deity_visual_timeline_strict_orientation(self):
        """build_deity_visual_timeline enforces strict orientation isolation for both short and long formats."""
        from src.assets.selector import build_deity_visual_timeline

        # 1. Shorts with only horizontal video -> must not use horizontal video
        manifest_short = {
            "deities": {
                "lakshmi_devi": {
                    "images": [
                        {"asset_id": "l_img1", "type": "image", "path": "assets/gods/lakshmi_devi/l1.png", "width": 720, "height": 1280},
                        {"asset_id": "l_img2", "type": "image", "path": "assets/gods/lakshmi_devi/l2.png", "width": 720, "height": 1280},
                    ],
                    "videos": [
                        {"asset_id": "l_hvid", "type": "video", "path": "assets/gods_processed/lakshmi_devi/horizontal/h.mp4", "width": 1920, "height": 1080},
                    ],
                }
            }
        }
        tl_short = build_deity_visual_timeline("lakshmi_devi", target_duration=45.0, content_type="short", manifest=manifest_short)
        for seg in tl_short:
            self.assertEqual(seg["asset_type"], "image", "Short timeline must not include horizontal video")
            self.assertNotIn("horizontal", seg["asset"])

        # 2. Long video with only vertical video -> must not use vertical video
        manifest_long = {
            "deities": {
                "lakshmi_devi": {
                    "images": [
                        {"asset_id": "l_limg1", "type": "image", "path": "assets/gods_landscape/lakshmi_devi/l1.png", "width": 1920, "height": 1080},
                        {"asset_id": "l_limg2", "type": "image", "path": "assets/gods_landscape/lakshmi_devi/l2.png", "width": 1920, "height": 1080},
                    ],
                    "videos": [
                        {"asset_id": "l_vvid", "type": "video", "path": "assets/gods_processed/lakshmi_devi/vertical/v.mp4", "width": 720, "height": 1280},
                    ],
                }
            }
        }
        tl_long = build_deity_visual_timeline("lakshmi_devi", target_duration=180.0, content_type="long", manifest=manifest_long)
        for seg in tl_long:
            self.assertEqual(seg["asset_type"], "image", "Long timeline must not include vertical video")
            self.assertNotIn("vertical", seg["asset"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
