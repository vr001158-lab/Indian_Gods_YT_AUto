# tests/test_phase5_qa.py
# Phase 5 Unit Tests — Audio Mastering, Captions, Visual Polish, QA

import os
import unittest
import hashlib
import json
from pathlib import Path
from src.video.composer import format_caption_text, FFmpegVideoComposer
from src.video.effects import get_ken_burns_filter, get_caption_filter, get_video_filtergraph_for_scene
from src.video.generator import validate_video_file_with_ffprobe, perform_video_qa

ASSET_PLAN_PATH = Path("data/visuals/asset_plan_20260814_071510.json")
EXPECTED_SHA256 = "f6ca03a2dfec5add5b9bce5ce699124bfdffacf42f009b2a9d4b1c02a5f87b33"


class TestPhase5Pipeline(unittest.TestCase):

    def test_01_shared_asset_plan_sha256_unchanged(self):
        """Verify shared asset plan file has not been modified."""
        if not ASSET_PLAN_PATH.exists():
            self.skipTest("Production asset plan file not available in CI environment")
        actual_sha256 = hashlib.sha256(ASSET_PLAN_PATH.read_bytes()).hexdigest()
        self.assertEqual(actual_sha256, EXPECTED_SHA256, "Asset plan SHA256 hash has changed!")

    def test_02_format_caption_text(self):
        """Test caption text wrapping for long lines."""
        text = "दिव्य दर्शनम् डेली में आपका स्वागत है। आज हम भगवान शिव के गले में वासुकी नाग के धारण करने का रहस्य जानेंगे।"
        wrapped = format_caption_text(text, max_chars_per_line=35)
        lines = wrapped.split("\n")
        self.assertGreater(len(lines), 1, "Caption text should be wrapped into multiple lines")
        for line in lines:
            self.assertLessEqual(len(line.split()), 10)

    def test_03_ken_burns_motion_types(self):
        """Test Ken Burns filter generation for all 4 motion types."""
        for motion in ["zoom_in", "zoom_out", "pan_left", "pan_right"]:
            filter_str = get_ken_burns_filter(motion_type=motion, duration_seconds=5.0)
            self.assertIn("zoompan=", filter_str)
            self.assertIn("1080x1920", filter_str)

    def test_04_caption_filter_generation(self):
        """Test caption drawtext filter string formulation across platforms."""
        from src.video.effects import resolve_caption_font
        expected_font = resolve_caption_font(language_code="hi-IN")
        escaped_font = expected_font.replace("\\", "/").replace(":", "\\:")

        filter_str = get_caption_filter("data/videos/_captions_test/scene_1.txt")
        self.assertIn("drawtext=", filter_str)
        self.assertIn(f"fontfile='{escaped_font}':", filter_str)
        self.assertIn("textfile='data/videos/_captions_test/scene_1.txt':", filter_str)
        self.assertIn("box=1:boxcolor=black@0.65:boxborderw=12:", filter_str)
        self.assertIn("fontsize=42:", filter_str)
        self.assertIn("x=(w-text_w)/2:y=h*0.72", filter_str)

        # Platform-specific regression guard:
        if os.name == "nt":
            self.assertTrue(
                any(f in filter_str for f in ["Nirmala", "mangal", "aparaj", "arial", "segoeui"]),
                f"Windows filter string should contain a known Windows font: {filter_str}",
            )
        else:
            self.assertTrue(
                any(f in filter_str for f in ["NotoSans", "lohit", "Gargi", "nakula", "DejaVu", "FreeSans", "Liberation"]),
                f"Linux filter string should contain a known Linux font: {filter_str}",
            )

    def test_04b_caption_filter_explicit_font(self):
        """Test caption drawtext filter with explicit font path."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".ttf") as tmp:
            custom_filter = get_caption_filter(
                "data/videos/_captions_test/scene_1.txt",
                font_path=tmp.name,
                language_code="te-IN",
                fontsize=36,
                y_position_ratio=0.80,
            )
            escaped_tmp = Path(tmp.name).resolve().as_posix().replace(":", "\\:")
            self.assertIn("drawtext=", custom_filter)
            self.assertIn(f"fontfile='{escaped_tmp}':", custom_filter)
            self.assertIn("fontsize=36:", custom_filter)
            self.assertIn("x=(w-text_w)/2:y=h*0.8", custom_filter)

    def test_05_final_hindi_video_qa(self):
        """Validate rendered final Hindi video against production specifications."""
        hi_video = Path("data/videos/shiva_hi_final.mp4")
        if not hi_video.exists():
            self.skipTest("Hindi production video asset (shiva_hi_final.mp4) not available in CI environment")
        qa_res = perform_video_qa(hi_video)
        self.assertTrue(qa_res["valid"])
        self.assertEqual(qa_res["resolution"], "1080x1920")
        self.assertEqual(qa_res["video_codec"], "h264")
        self.assertEqual(qa_res["audio_codec"], "aac")
        self.assertEqual(qa_res["audio_sample_rate"], 48000)
        self.assertEqual(qa_res["audio_channels"], 2)
        self.assertTrue(qa_res["no_corruption"])

    def test_06_final_telugu_video_qa(self):
        """Validate rendered final Telugu video against production specifications."""
        te_video = Path("data/videos/shiva_te_final.mp4")
        if not te_video.exists():
            self.skipTest("Telugu production video asset (shiva_te_final.mp4) not available in CI environment")
        qa_res = perform_video_qa(te_video)
        self.assertTrue(qa_res["valid"])
        self.assertEqual(qa_res["resolution"], "1080x1920")
        self.assertEqual(qa_res["video_codec"], "h264")
        self.assertEqual(qa_res["audio_codec"], "aac")
        self.assertEqual(qa_res["audio_sample_rate"], 48000)
        self.assertEqual(qa_res["audio_channels"], 2)
        self.assertTrue(qa_res["no_corruption"])

    def test_07_final_tamil_video_qa(self):
        """Validate rendered final Tamil video against production specifications."""
        ta_video = Path("data/videos/shiva_ta_final.mp4")
        if not ta_video.exists():
            self.skipTest("Tamil production video asset (shiva_ta_final.mp4) not available in CI environment")
        qa_res = perform_video_qa(ta_video)
        self.assertTrue(qa_res["valid"])
        self.assertEqual(qa_res["resolution"], "1080x1920")
        self.assertEqual(qa_res["video_codec"], "h264")
        self.assertEqual(qa_res["audio_codec"], "aac")
        self.assertEqual(qa_res["audio_sample_rate"], 48000)
        self.assertEqual(qa_res["audio_channels"], 2)
        self.assertTrue(qa_res["no_corruption"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
