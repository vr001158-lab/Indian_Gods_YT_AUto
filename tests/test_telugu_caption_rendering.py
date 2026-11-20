# tests/test_telugu_caption_rendering.py
# Regression Test Suite: Telugu Caption Shaping and Multi-Line Stacked Rendering

import os
import shutil
import tempfile
import unittest
from pathlib import Path

from src.video.effects import get_caption_filter, resolve_caption_font


class TestTeluguCaptionRendering(unittest.TestCase):
    """
    Verifies that Telugu caption rendering produces properly shaped Indic conjuncts
    and multi-line captions without HarfBuzz \\n .notdef missing-glyph box artifacts.
    """

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="telugu_cap_test_"))
        self.conjunct_words = [
            "క్షీరసాగర",
            "మహాలక్ష్మి",
            "సౌభాగ్యాలు",
            "మహాలక్ష్మ్యై",
        ]

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_telugu_font_resolution(self):
        """Verifies that te-IN resolves to a valid Indic-compatible font."""
        font_path = resolve_caption_font(language_code="te-IN")
        self.assertTrue(Path(font_path).exists(), f"Resolved font does not exist: {font_path}")
        self.assertTrue(
            any(name in font_path.lower() for name in ["notosanstelugu", "nirmala", "gautami", "lohit", "pothana"]),
            f"Font {font_path} should be a recognized Telugu font",
        )

    def test_multiline_stacked_filter_generation_and_conjuncts(self):
        """
        Verifies that multi-line Telugu caption text generates stacked single-line drawtext filters
        with calculated vertical offsets and zero newline characters in individual line files.
        """
        line1 = "క్షీరసాగర మథనంలో పవిత్ర కమలంపై"
        line2 = "సౌభాగ్యాలు ప్రసాదించే శ్రీ మహాలక్ష్మి"
        line3 = "భక్తితో శరణు వేడుకుందాం ఓం శ్రీ మహాలక్ష్మ్యై నమః"

        cap_file = self.test_dir / "caption_test.txt"
        cap_file.write_text(f"{line1}\n{line2}\n{line3}", encoding="utf-8")

        filter_str = get_caption_filter(
            str(cap_file),
            language_code="te-IN",
            fontsize=44,
            y_position_ratio=0.65,
            total_height=1920,
            line_spacing=24,
        )

        drawtext_filters = [f for f in filter_str.split("drawtext=") if f]
        self.assertEqual(len(drawtext_filters), 3, "Must generate exactly 3 stacked drawtext filters for 3 lines")

        # Verify each line file exists and has 0 newlines
        line1_file = self.test_dir / "caption_test_line_1.txt"
        line2_file = self.test_dir / "caption_test_line_2.txt"
        line3_file = self.test_dir / "caption_test_line_3.txt"

        self.assertTrue(line1_file.exists(), "Line 1 file must be created")
        self.assertTrue(line2_file.exists(), "Line 2 file must be created")
        self.assertTrue(line3_file.exists(), "Line 3 file must be created")

        content1 = line1_file.read_text(encoding="utf-8")
        content2 = line2_file.read_text(encoding="utf-8")
        content3 = line3_file.read_text(encoding="utf-8")

        self.assertEqual(content1, line1)
        self.assertEqual(content2, line2)
        self.assertEqual(content3, line3)

        # Zero newline characters (which cause HarfBuzz .notdef boxes)
        for idx, content in enumerate([content1, content2, content3], 1):
            self.assertNotIn("\n", content, f"Line {idx} file must not contain newline character")
            self.assertNotIn("\r", content, f"Line {idx} file must not contain carriage return")

        # Verify all four required Telugu conjunct words are covered
        all_content = f"{content1} {content2} {content3}"
        for word in self.conjunct_words:
            self.assertIn(word, all_content, f"Required Telugu conjunct '{word}' must be present in captions")

        # Verify text_shaping=1 is enabled on all drawtext filters
        for filt in drawtext_filters:
            self.assertIn("text_shaping=1", filt, "Each drawtext filter must enable HarfBuzz text_shaping=1")

    def test_single_line_filter_generation(self):
        """Verifies that single-line caption file generates a clean filter without newlines."""
        line = "ఓం శ్రీ మహాలక్ష్మ్యై నమః"
        cap_file = self.test_dir / "single_test.txt"
        cap_file.write_text(f"{line}\n", encoding="utf-8")

        filter_str = get_caption_filter(
            str(cap_file),
            language_code="te-IN",
            fontsize=44,
            y_position_ratio=0.65,
            total_height=1920,
        )

        line1_file = self.test_dir / "single_test_line_1.txt"
        self.assertTrue(line1_file.exists())
        content = line1_file.read_text(encoding="utf-8")
        self.assertEqual(content, line)
        self.assertNotIn("\n", content)
        self.assertIn("text_shaping=1", filter_str)

    def test_nonexistent_file_fallback(self):
        """Verifies fallback filter generation when caption file does not yet exist on disk."""
        filter_str = get_caption_filter(
            "dummy_nonexistent_caption.txt",
            language_code="te-IN",
            fontsize=44,
            y_position_ratio=0.65,
        )
        self.assertIn("drawtext=", filter_str)
        self.assertIn("text_shaping=1", filter_str)
        self.assertIn("dummy_nonexistent_caption.txt", filter_str)

    def test_ffmpeg_render_telugu_conjunct_frame(self):
        """
        Renders a frame using FFmpeg with the stacked caption filter containing
        all 4 Telugu conjunct words, verifying end-to-end execution without errors.
        """
        import subprocess

        line1 = "క్షీరసాగర మథనంలో పవిత్ర కమలంపై"
        line2 = "సౌభాగ్యాలు ప్రసాదించే శ్రీ మహాలక్ష్మి"
        line3 = "భక్తితో శరణు వేడుకుందాం ఓం శ్రీ మహాలక్ష్మ్యై నమః"

        cap_file = self.test_dir / "render_test.txt"
        cap_file.write_text(f"{line1}\n{line2}\n{line3}", encoding="utf-8")

        filter_str = get_caption_filter(
            str(cap_file),
            language_code="te-IN",
            fontsize=44,
            y_position_ratio=0.65,
            total_height=1920,
            line_spacing=24,
        )

        out_frame = self.test_dir / "rendered_test_frame.png"
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=darkblue:s=1080x1920:d=1",
            "-vf", filter_str,
            "-frames:v", "1",
            str(out_frame),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"FFmpeg render failed with stderr: {res.stderr}")
        self.assertTrue(out_frame.exists(), "Rendered frame PNG must exist")
        self.assertGreater(out_frame.stat().st_size, 10000, "Rendered PNG must be a non-empty image")


if __name__ == "__main__":
    unittest.main()
