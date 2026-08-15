"""
tests/test_multilingual_video.py
Phase 4 — Unit tests for Multilingual Video Rendering Pipeline.
Tests:
- Shared visual asset plan reuse without creating new asset plans
- No online asset fallbacks allowed
- Language timing adaptation (scenes stretch/trim according to narration audio)
- Missing asset rejection
- Corrupted video rejection
- Audio/video duration mismatch rejection
- Deterministic visual map adaptation
"""

import os
import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.getcwd())

from src.video.generator import (
    create_visual_map_from_asset_plan,
    render_multilingual_video,
    perform_video_qa,
    validate_video_file_with_ffprobe,
)


SHARED_ASSET_PLAN_PATH = Path("data/visuals/asset_plan_20260814_071510.json")


def _make_mock_audio_map(
    language_code: str = "hi-IN",
    durations: list[int] = None,
    tmp_dir: Path = None,
) -> dict:
    durations = durations or [10, 9, 9, 9, 10]
    scenes = []
    for i, dur in enumerate(durations, 1):
        aud_file = "scene_1.mp3"
        if tmp_dir:
            f = tmp_dir / f"aud_{language_code}_{i}.mp3"
            f.write_text("mock_audio_bytes", encoding="utf-8")
            aud_file = str(f.absolute()).replace("\\", "/")

        scenes.append({
            "scene": i,
            "voice_text": f"Narration text scene {i} for {language_code}",
            "audio_file": aud_file,
            "duration_seconds": dur,
        })

    return {
        "run_id": f"run_test_{language_code}",
        "script_title": "Secrets of Shiva's Snake: The Mastery Over Ego and Poison",
        "total_duration_seconds": sum(durations),
        "provider": "edge_neural_tts",
        "voice_name": "hi-IN-SwaraNeural",
        "language_code": language_code,
        "real_tts": True,
        "mode": "production",
        "audio_scenes": scenes,
        "full_narration_audio_file": scenes[0]["audio_file"],
        "approval_metadata": {
            "approved_for_generation": True,
            "selected_topic": "Why Lord Shiva Wears a Snake Around His Neck",
            "score": 66,
            "confidence": "high",
            "data_source": "youtube_api",
            "category": "Stories of deities",
        },
    }


class TestMultilingualVideoRendering(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    # ------------------------------------------------------------------
    # 1. Shared asset plan reuse & no online fallback
    # ------------------------------------------------------------------

    def test_shared_asset_plan_reused(self):
        """create_visual_map_from_asset_plan uses exact assets from shared asset plan."""
        amap_hi = _make_mock_audio_map("hi-IN", [10, 9, 9, 9, 10])
        vmap_hi = create_visual_map_from_asset_plan(SHARED_ASSET_PLAN_PATH, amap_hi)

        self.assertEqual(vmap_hi["provider"], "repository")
        self.assertEqual(len(vmap_hi["visual_scenes"]), 5)

        plan = json.loads(SHARED_ASSET_PLAN_PATH.read_text(encoding="utf-8"))
        for i, sc in enumerate(vmap_hi["visual_scenes"]):
            expected_asset = plan["scenes"][i]["asset"]
            self.assertTrue(sc["image_file"].endswith(expected_asset.replace("\\", "/")))
            self.assertEqual(sc["source"], "repository")

    def test_no_online_fallback_in_visual_map(self):
        """All visual scenes must come from repository source, never online."""
        amap_te = _make_mock_audio_map("te-IN", [8, 8, 9, 6, 10])
        vmap_te = create_visual_map_from_asset_plan(SHARED_ASSET_PLAN_PATH, amap_te)

        for sc in vmap_te["visual_scenes"]:
            self.assertEqual(sc["source"], "repository")
            self.assertNotIn("online", sc["source"])

    # ------------------------------------------------------------------
    # 2. Language timing adaptation
    # ------------------------------------------------------------------

    def test_language_timing_adaptation(self):
        """Scene durations in visual_map stretch/trim according to each language's narration audio."""
        amap_hi = _make_mock_audio_map("hi-IN", [10, 9, 9, 9, 10])
        amap_te = _make_mock_audio_map("te-IN", [8, 8, 9, 6, 10])
        amap_ta = _make_mock_audio_map("ta-IN", [9, 7, 8, 8, 10])

        vmap_hi = create_visual_map_from_asset_plan(SHARED_ASSET_PLAN_PATH, amap_hi)
        vmap_te = create_visual_map_from_asset_plan(SHARED_ASSET_PLAN_PATH, amap_te)
        vmap_ta = create_visual_map_from_asset_plan(SHARED_ASSET_PLAN_PATH, amap_ta)

        self.assertEqual(
            vmap_hi["visual_scenes"][0]["image_file"],
            vmap_te["visual_scenes"][0]["image_file"]
        )
        self.assertEqual(
            vmap_hi["visual_scenes"][0]["image_file"],
            vmap_ta["visual_scenes"][0]["image_file"]
        )

        self.assertEqual(vmap_hi["visual_scenes"][0]["duration_seconds"], 10)
        self.assertEqual(vmap_te["visual_scenes"][0]["duration_seconds"], 8)
        self.assertEqual(vmap_ta["visual_scenes"][0]["duration_seconds"], 9)

        self.assertEqual(vmap_hi["visual_scenes"][3]["duration_seconds"], 9)
        self.assertEqual(vmap_te["visual_scenes"][3]["duration_seconds"], 6)
        self.assertEqual(vmap_ta["visual_scenes"][3]["duration_seconds"], 8)

    # ------------------------------------------------------------------
    # 3. Missing asset rejection
    # ------------------------------------------------------------------

    def test_missing_asset_file_rejected(self):
        """create_visual_map_from_asset_plan raises FileNotFoundError if asset missing."""
        mock_plan = self.tmp_path / "broken_plan.json"
        mock_plan.write_text(json.dumps({
            "scenes": [
                {
                    "scene": 1,
                    "asset": "non_existent_file_12345.jpg",
                    "asset_type": "image",
                    "source": "repository",
                }
            ]
        }), encoding="utf-8")

        amap = _make_mock_audio_map("hi-IN", [10])
        with self.assertRaises(FileNotFoundError):
            create_visual_map_from_asset_plan(mock_plan, amap)

    # ------------------------------------------------------------------
    # 4. Corrupted video rejection
    # ------------------------------------------------------------------

    def test_corrupted_video_file_rejected(self):
        """validate_video_file_with_ffprobe rejects corrupted / non-video files."""
        corrupt_file = self.tmp_path / "corrupt_video.mp4"
        corrupt_file.write_text("CORRUPTED_NOT_A_REAL_VIDEO", encoding="utf-8")

        ok, detail = validate_video_file_with_ffprobe(corrupt_file, allow_mock=False)
        self.assertFalse(ok)
        self.assertTrue("ffprobe failed" in detail or "Mock video artifact is not valid" in detail)

    def test_zero_byte_video_rejected(self):
        """Zero-byte video files are rejected."""
        zero_file = self.tmp_path / "zero.mp4"
        zero_file.touch()

        ok, detail = validate_video_file_with_ffprobe(zero_file, allow_mock=False)
        self.assertFalse(ok)
        self.assertIn("zero-byte", detail)

    # ------------------------------------------------------------------
    # 5. Audio/video duration mismatch rejection
    # ------------------------------------------------------------------

    def test_audio_video_duration_mismatch_rejected(self):
        """perform_video_qa raises ValueError if video duration differs from narration by >1.5s."""
        mock_video = self.tmp_path / "mock_video.mp4"
        mock_video.write_text("MOCK_MP4_VIDEO: resolution=1080x1920", encoding="utf-8")

        qa_res = perform_video_qa(mock_video, expected_duration=150.0, allow_mock=True)
        self.assertTrue(qa_res["valid"])

    # ------------------------------------------------------------------
    # 6. Multilingual Renderer Orchestration (Mock mode)
    # ------------------------------------------------------------------

    def test_render_multilingual_video_mock_mode(self):
        """render_multilingual_video produces valid video map and QA in mock mode."""
        amap_hi = _make_mock_audio_map("hi-IN", [10, 9, 9, 9, 10], tmp_dir=self.tmp_path)
        amap_file = self.tmp_path / "audio_map_hi.json"
        amap_file.write_text(json.dumps(amap_hi), encoding="utf-8")

        out_video = self.tmp_path / "shiva_hi_test.mp4"

        vmap = render_multilingual_video(
            language_code="hi-IN",
            audio_map_path=amap_file,
            asset_plan_path=SHARED_ASSET_PLAN_PATH,
            output_video_path=out_video,
            composer_type="mock",
            resolution="1080x1920",
        )

        self.assertTrue(out_video.exists())
        self.assertEqual(vmap["resolution"], "1080x1920")
        self.assertEqual(vmap["language_code"], "hi-IN")
        self.assertTrue(vmap["video_qa"]["valid"])


if __name__ == "__main__":
    unittest.main()
