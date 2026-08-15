# tests/test_format_config.py
# Phase 12 — Unit Tests for Canonical Content Format Configuration

import unittest
from src.video.format_config import (
    FORMAT_CONFIGS,
    VALID_CONTENT_TYPES,
    DEFAULT_CONTENT_TYPE,
    get_format_config,
    resolution_for,
    content_type_from_resolution,
    validate_content_type,
    validate_resolution_for_content_type,
    validate_duration_for_content_type,
)


class TestFormatConfig(unittest.TestCase):

    def test_01_canonical_configs_exist(self):
        self.assertIn("short", FORMAT_CONFIGS)
        self.assertIn("long", FORMAT_CONFIGS)
        self.assertEqual(DEFAULT_CONTENT_TYPE, "short")
        self.assertEqual(VALID_CONTENT_TYPES, frozenset(["short", "long"]))

    def test_02_short_config_values(self):
        cfg = get_format_config("short")
        self.assertEqual(cfg["content_type"], "short")
        self.assertEqual(cfg["aspect_ratio"], "9:16")
        self.assertEqual(cfg["resolution"], "1080x1920")
        self.assertEqual(cfg["width"], 1080)
        self.assertEqual(cfg["height"], 1920)
        self.assertEqual(cfg["max_duration_seconds"], 180)
        self.assertEqual(cfg["publish_classification"], "short")

    def test_03_long_config_values(self):
        cfg = get_format_config("long")
        self.assertEqual(cfg["content_type"], "long")
        self.assertEqual(cfg["aspect_ratio"], "16:9")
        self.assertEqual(cfg["resolution"], "1920x1080")
        self.assertEqual(cfg["width"], 1920)
        self.assertEqual(cfg["height"], 1080)
        self.assertEqual(cfg["min_duration_seconds"], 1)
        self.assertEqual(cfg["publish_classification"], "long")

    def test_04_unknown_format_raises_error(self):
        with self.assertRaises(ValueError):
            get_format_config("medium")

    def test_05_resolution_for_helpers(self):
        self.assertEqual(resolution_for("short"), "1080x1920")
        self.assertEqual(resolution_for("long"), "1920x1080")

    def test_06_content_type_from_resolution_lookup(self):
        self.assertEqual(content_type_from_resolution(1080, 1920), "short")
        self.assertEqual(content_type_from_resolution(1920, 1080), "long")
        self.assertIsNone(content_type_from_resolution(800, 600))

    def test_07_validate_content_type(self):
        ok, err = validate_content_type("short")
        self.assertTrue(ok)
        self.assertEqual(err, "")

        ok, err = validate_content_type("LONG")
        self.assertTrue(ok)

        ok, err = validate_content_type("invalid_type")
        self.assertFalse(ok)
        self.assertIn("not valid", err)

        ok, err = validate_content_type("")
        self.assertFalse(ok)

    def test_08_validate_resolution_for_content_type(self):
        # Matching resolution
        ok, err = validate_resolution_for_content_type("1080x1920", "short")
        self.assertTrue(ok)

        ok, err = validate_resolution_for_content_type("1920x1080", "long")
        self.assertTrue(ok)

        # Mismatched resolution
        ok, err = validate_resolution_for_content_type("1920x1080", "short")
        self.assertFalse(ok)
        self.assertIn("Invalid resolution", err)

        ok, err = validate_resolution_for_content_type("1080x1920", "long")
        self.assertFalse(ok)
        self.assertIn("Invalid resolution", err)

    def test_09_validate_duration_for_content_type(self):
        # Short duration bounds (10s - 180s)
        self.assertTrue(validate_duration_for_content_type(60, "short")[0])
        self.assertFalse(validate_duration_for_content_type(5, "short")[0])
        self.assertFalse(validate_duration_for_content_type(200, "short")[0])

        # Long duration bounds: any positive duration is valid (content_type is authoritative)
        self.assertTrue(validate_duration_for_content_type(60, "long")[0])   # <181s is VALID
        self.assertTrue(validate_duration_for_content_type(300, "long")[0])  # 5 min is VALID
        self.assertFalse(validate_duration_for_content_type(0, "long")[0])   # 0s is invalid

        # Zero or negative duration
        self.assertFalse(validate_duration_for_content_type(0, "short")[0])
        self.assertFalse(validate_duration_for_content_type(-10, "long")[0])

    def test_10_regression_short_duration_long_format(self):
        """Proves content_type='long' with duration < 181s and resolution 1920x1080 passes validation."""
        ok_dur, err_dur = validate_duration_for_content_type(60.0, "long")
        self.assertTrue(ok_dur, f"60s long format failed duration check: {err_dur}")

        ok_res, err_res = validate_resolution_for_content_type("1920x1080", "long")
        self.assertTrue(ok_res, f"1920x1080 long format failed resolution check: {err_res}")


if __name__ == "__main__":
    unittest.main()
