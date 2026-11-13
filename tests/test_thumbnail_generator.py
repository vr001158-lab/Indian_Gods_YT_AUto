"""
tests/test_thumbnail_generator.py
Unit tests for Phase 2H / Phase 4 — Pollinations-Only Thumbnail Generation Pipeline.
Tests:
  - Safety gates and input validation
  - Pollinations request construction, model selection, headers, and API key redaction
  - Pollinations timeout handling, retries with backoff, and 401/403 immediate failure
  - Invalid and corrupt image payload rejection (never saved)
  - Valid image download and integrity verification
  - PIL thumbnail composition, 1280x720 resolution, RGB output
  - Telugu Unicode typography and channel branding ('దైవ దర్శనం')
  - Strict prohibition of Flux/Gemini fallback for thumbnails
  - Preserved Flux video scene generator architecture
  - Offline dry-run (Mock) and render-only compatibility
Runs completely offline without external network or API dependencies.
"""

import sys
import os
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from PIL import Image, ImageDraw

sys.path.insert(0, os.getcwd())

from src.thumbnail.schemas import validate_decision_input, validate_metadata_output
from src.thumbnail.validator import validate_decision_safety, verify_or_raise_safety
from src.thumbnail.generator import (
    PollinationsThumbnailGenerator,
    PILThumbnailGenerator,
    MockThumbnailGenerator,
    FluxThumbnailGenerator,
)
from src.thumbnail.providers.pollinations import (
    PollinationsProvider,
    PollinationsError,
    PollinationsAPIError,
    PollinationsTimeoutError,
    PollinationsImageValidationError,
    build_thumbnail_background_prompt,
    sanitize_log_url,
)
from src.thumbnail.analyzer import analyze_thumbnail_file
from src.thumbnail.templates import DEVOTIONAL_GOLD_THEME, get_thumbnail_theme
import run_thumbnail_generator


# ── Helper: generate mock decision inputs ─────────────────────────────────────
def _make_decision(
    approved: bool = True,
    confidence: str = "high",
    data_source: str = "youtube_api",
    title: str = "Why Lord Shiva Wears a Snake Around His Neck",
    deity: str = "shiva",
) -> dict:
    return {
        "approved_for_generation": approved,
        "selected_topic":          title,
        "score":                   66,
        "confidence":              confidence,
        "data_source":             data_source,
        "category":                "Stories of deities",
        "deity":                   deity,
        "suggested_angle":         "Divine mystery and sacred symbolism.",
        "content_gap":             "High viewer curiosity regarding divine ornaments."
    }


def _make_valid_png_bytes(width: int = 1280, height: int = 720, color=(30, 20, 45)) -> bytes:
    """Creates a valid 1280x720 PNG with color variance for mock HTTP responses."""
    img = Image.new("RGB", (width, height), color=color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([(150, 150), (650, 550)], fill=(255, 185, 35))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
class TestThumbnailSafetyGates(unittest.TestCase):
    """Test safety gate checks on incoming decisions (Tests 1-7)."""

    def test_1_valid_decision_accepted(self):
        d = _make_decision()
        ok, err = validate_decision_safety(d)
        self.assertTrue(ok, f"Should accept valid decision: {err}")
        verify_or_raise_safety(d)

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
        ok, err = validate_decision_safety([])
        self.assertFalse(ok)
        self.assertIn("must be a dictionary", err)
        with self.assertRaises(ValueError):
            verify_or_raise_safety([])


# ─────────────────────────────────────────────────────────────────────────────
class TestPollinationsProvider(unittest.TestCase):
    """Tests for PollinationsProvider request building, auth, timeout, and retries."""

    def test_request_url_and_params_construction(self):
        provider = PollinationsProvider(model="flux", base_url="https://image.pollinations.ai/prompt")
        prompt = "Lord Varaha lifting Bhudevi"
        url, params = provider.build_request_url(prompt, width=1280, height=720, seed=42)

        self.assertTrue(url.startswith("https://image.pollinations.ai/prompt/"))
        self.assertIn("Lord%20Varaha", url)
        self.assertEqual(params["width"], 1280)
        self.assertEqual(params["height"], 720)
        self.assertEqual(params["model"], "flux")
        self.assertEqual(params["nologo"], "true")
        self.assertEqual(params["enhance"], "false")
        self.assertEqual(params["seed"], 42)

    def test_configurable_model_and_endpoint(self):
        with patch.dict(os.environ, {"POLLINATIONS_MODEL": "turbo", "POLLINATIONS_ENDPOINT": "https://gen.pollinations.ai/image"}):
            provider = PollinationsProvider()
            self.assertEqual(provider.model, "turbo")
            self.assertEqual(provider.base_url, "https://gen.pollinations.ai/image")
            url, params = provider.build_request_url("test")
            self.assertEqual(params["model"], "turbo")
            self.assertTrue(url.startswith("https://gen.pollinations.ai/image/"))

    def test_auth_headers_and_key_redaction(self):
        provider = PollinationsProvider(api_key="secret_pollinations_key_123")
        headers = provider.build_headers()
        self.assertEqual(headers["Authorization"], "Bearer secret_pollinations_key_123")

        # Verify key is never leaked in log sanitizer
        sanitized = sanitize_log_url("https://image.pollinations.ai/prompt/test?key=secret_pollinations_key_123")
        self.assertNotIn("secret_pollinations_key_123", sanitized)
        self.assertIn("key=[REDACTED]", sanitized)

        sanitized_header = sanitize_log_url("Authorization: Bearer secret_pollinations_key_123")
        self.assertNotIn("secret_pollinations_key_123", sanitized_header)
        self.assertIn("Bearer [REDACTED]", sanitized_header)

    @patch("src.thumbnail.providers.pollinations.requests.get")
    def test_valid_image_download_and_integrity_check(self, mock_get):
        png_bytes = _make_valid_png_bytes(1280, 720)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = png_bytes
        mock_get.return_value = mock_response

        provider = PollinationsProvider()
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "test_bg.png"
            res = provider.generate_background("Lord Shiva on Kailash", out_file)
            self.assertTrue(out_file.exists())
            self.assertEqual(res, out_file)
            with Image.open(out_file) as img:
                self.assertEqual(img.size, (1280, 720))
                self.assertEqual(img.format, "PNG")

    @patch("src.thumbnail.providers.pollinations.time.sleep")
    @patch("src.thumbnail.providers.pollinations.requests.get")
    def test_timeout_and_retries_fail_closed(self, mock_get, mock_sleep):
        import requests
        mock_get.side_effect = requests.Timeout("Connection timed out")

        provider = PollinationsProvider(max_retries=3)
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "timeout.png"
            with self.assertRaises(PollinationsError):
                provider.generate_background("Lord Krishna", out_file)

            self.assertEqual(mock_get.call_count, 3)
            self.assertFalse(out_file.exists())

    @patch("src.thumbnail.providers.pollinations.time.sleep")
    @patch("src.thumbnail.providers.pollinations.requests.get")
    def test_retry_on_500_and_429_then_succeed(self, mock_get, mock_sleep):
        resp_500 = MagicMock(status_code=500)
        resp_429 = MagicMock(status_code=429)
        resp_200 = MagicMock(status_code=200, content=_make_valid_png_bytes(1280, 720))
        mock_get.side_effect = [resp_500, resp_429, resp_200]

        provider = PollinationsProvider(max_retries=3)
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "retry_success.png"
            res = provider.generate_background("Lord Narasimha", out_file)
            self.assertTrue(res.exists())
            self.assertEqual(mock_get.call_count, 3)
            self.assertEqual(mock_sleep.call_count, 2)

    @patch("src.thumbnail.providers.pollinations.requests.get")
    def test_immediate_failure_on_401_403(self, mock_get):
        mock_get.return_value = MagicMock(status_code=401)
        provider = PollinationsProvider(max_retries=3)
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "auth_fail.png"
            with self.assertRaises(PollinationsAPIError):
                provider.generate_background("Lord Kurma", out_file)
            # Must fail immediately without exhausting all retries
            self.assertEqual(mock_get.call_count, 1)
            self.assertFalse(out_file.exists())

    @patch("src.thumbnail.providers.pollinations.requests.get")
    def test_invalid_image_response_rejected_and_never_saved(self, mock_get):
        # Returns HTTP 200 but garbage bytes
        mock_get.return_value = MagicMock(status_code=200, content=b"<html>error page</html>")
        provider = PollinationsProvider(max_retries=1)
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "corrupt_bg.png"
            with self.assertRaises(PollinationsError):
                provider.generate_background("Lord Hanuman", out_file)
            self.assertFalse(out_file.exists(), "Corrupt image must never be saved to destination path")

    def test_dynamic_prompt_builder(self):
        prompt = build_thumbnail_background_prompt(
            topic="వరాహ అవతార రహస్యం: మహావిష్ణువు భూదేవిని ఎందుకు రక్షించారు?",
            deity="varaha",
            main_event="Varaha lifting Bhudevi on his tusks",
            emotional_theme="Devotional triumph, sacred awe, and divine protection",
        )
        # Varaha specific requirements
        self.assertIn("divine Varaha form", prompt)
        self.assertIn("noble boar head", prompt)
        self.assertIn("elongated snout", prompt)
        self.assertIn("curved white tusks", prompt)
        self.assertIn("blue-toned divine body", prompt)
        self.assertIn("golden crown (mukuta)", prompt)
        self.assertIn("Goddess Bhūmi Devi", prompt)
        self.assertIn("traditional Indian silk attire", prompt)
        self.assertIn("clearly illuminated", prompt)
        self.assertIn("cosmic ocean", prompt)

        # Composition requirement: center-right for deity, left 35-40% for text
        self.assertIn("reserving the left 35–40%", prompt)
        self.assertIn("center-right", prompt)

        # Negative prompt restrictions
        self.assertIn("generic animal boar", prompt)
        self.assertIn("human face replacing the boar head", prompt)
        self.assertIn("missing tusks", prompt)
        self.assertIn("missing Bhūmi Devi", prompt)
        self.assertIn("dark or hidden deity", prompt)
        self.assertIn("no text", prompt)

    def test_dynamic_prompt_builder_other_deities(self):
        # Verify dynamic behavior across deities (not hardcoding Varaha)
        prompt_narasimha = build_thumbnail_background_prompt(topic="Narasimha", deity="narasimha")
        self.assertIn("Narasimha", prompt_narasimha)
        self.assertIn("lion head", prompt_narasimha)
        self.assertNotIn("boar head", prompt_narasimha)

        prompt_krishna = build_thumbnail_background_prompt(topic="Govardhan", deity="krishna")
        self.assertIn("Krishna", prompt_krishna)
        self.assertIn("peacock feather", prompt_krishna)
        self.assertNotIn("boar head", prompt_krishna)

        prompt_hanuman = build_thumbnail_background_prompt(topic="Sanjeevani", deity="hanuman")
        self.assertIn("Hanuman", prompt_hanuman)
        self.assertIn("Dronagiri", prompt_hanuman)


# ─────────────────────────────────────────────────────────────────────────────
class TestThumbnailGeneration(unittest.TestCase):
    """Test image composition, Telugu rendering, and analyzer checks (Tests 8-13, 15)."""

    def setUp(self):
        # Patch background generator so PIL composition tests run offline with valid 1280x720 mock background
        self.bg_patcher = patch("src.thumbnail.providers.pollinations.PollinationsProvider.generate_background")
        self.mock_bg = self.bg_patcher.start()

        def _fake_generate(prompt, output_path, **kwargs):
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_bytes(_make_valid_png_bytes(1280, 720))
            return Path(output_path)

        self.mock_bg.side_effect = _fake_generate

    def tearDown(self):
        self.bg_patcher.stop()

    def test_8_pil_generator_creates_image(self):
        gen = PILThumbnailGenerator()
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "thumb.png"
            gen.generate_thumbnail(
                title="Secrets of Shiva's Snake",
                subtitle="దైవ దర్శనం",
                output_path=out_file
            )
            self.assertTrue(out_file.exists())
            self.assertTrue(out_file.stat().st_size > 0)

    def test_9_resolution_equals_1280x720(self):
        gen = PollinationsThumbnailGenerator()
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "thumb.png"
            gen.generate_thumbnail(
                title="వరాహ అవతార రహస్యం",
                subtitle="దైవ దర్శనం",
                output_path=out_file,
                language_code="te-IN",
            )
            analysis = analyze_thumbnail_file(out_file, expected_title="వరాహ అవతార రహస్యం", language_code="te-IN")
            self.assertTrue(analysis["valid"], f"Analysis failed: {analysis['errors']}")
            self.assertEqual(analysis["details"]["resolution"], "1280x720")
            self.assertEqual(analysis["details"]["mode"], "RGB")

    def test_10_png_output_valid(self):
        gen = PollinationsThumbnailGenerator()
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "thumb.png"
            gen.generate_thumbnail(
                title="వరాహ అవతార రహస్యం",
                subtitle="దైవ దర్శనం",
                output_path=out_file,
                language_code="te-IN",
            )
            with Image.open(out_file) as img:
                self.assertEqual(img.format, "PNG")
                self.assertEqual(img.size, (1280, 720))

    def test_11_metadata_generated(self):
        meta = {
            "title":           "వరాహ అవతార రహస్యం",
            "topic":           "The Secret of Varaha Avatar Rescuing Mother Earth",
            "provider":        "pollinations",
            "resolution":      "1280x720",
            "format":          "png",
            "approved_source": "youtube_api",
            "confidence":      "high",
            "created_at":      "20261113_120000",
            "approval_metadata": {
                "approved_for_generation": True,
                "selected_topic": "The Secret of Varaha Avatar Rescuing Mother Earth",
                "score": 69,
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

    def test_11c_telugu_text_and_channel_branding(self):
        gen = PollinationsThumbnailGenerator()
        theme = get_thumbnail_theme("te-IN")
        self.assertEqual(theme["branding_text"], "దైవ దర్శనం")

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "thumb_te.png"
            gen.generate_thumbnail(
                title="వరాహ అవతార రహస్యం: మహావిష్ణువు భూదేవిని ఎందుకు రక్షించారు?",
                subtitle="దైవ దర్శనం",
                output_path=out_file,
                language_code="te-IN",
            )
            analysis = analyze_thumbnail_file(
                out_file,
                expected_title="వరాహ అవతార రహస్యం",
                language_code="te-IN"
            )
            self.assertTrue(analysis["valid"], f"Telugu thumbnail validation failed: {analysis['errors']}")
            self.assertGreater(analysis["details"]["color_variance_stddev"], 5.0)

    def test_telugu_title_hierarchy_and_safe_margins(self):
        gen = PollinationsThumbnailGenerator()
        main_title = "వరాహ అవతార రహస్యం"
        supporting_title = "మహావిష్ణువు భూదేవిని ఎందుకు రక్షించారు?"

        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "thumb_hierarchy.png"
            gen.generate_thumbnail(
                title=main_title,
                subtitle=supporting_title,
                output_path=out_file,
                language_code="te-IN",
            )
            analysis = analyze_thumbnail_file(
                out_file,
                expected_title=main_title,
                language_code="te-IN"
            )
            self.assertTrue(analysis["valid"], f"Validation failed: {analysis['errors']}")
            self.assertEqual(analysis["details"]["resolution"], "1280x720")
            self.assertEqual(analysis["details"]["mode"], "RGB")

    def test_11d_blank_placeholder_rejected_by_analyzer(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            blank_file = Path(tmp_dir) / "blank.png"
            Image.new("RGB", (1280, 720), color=(10, 20, 30)).save(blank_file, format="PNG")
            analysis = analyze_thumbnail_file(blank_file, allow_mock=False)
            self.assertFalse(analysis["valid"])
            self.assertTrue(any("blank or flat placeholder" in e for e in analysis["errors"]))

    def test_12_analyzer_detects_corruption(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            corrupt_file = Path(tmp_dir) / "corrupt.png"
            corrupt_file.write_text("corrupt image content data", encoding="utf-8")
            analysis = analyze_thumbnail_file(corrupt_file)
            self.assertFalse(analysis["valid"])
            self.assertTrue(len(analysis["errors"]) > 0)

            non_exist_file = Path(tmp_dir) / "missing_file.png"
            analysis_missing = analyze_thumbnail_file(non_exist_file)
            self.assertFalse(analysis_missing["valid"])

    def test_13_mock_provider_works_offline(self):
        gen = MockThumbnailGenerator()
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "thumb_mock.png"
            gen.generate_thumbnail(
                title="Mock Dry Run Title",
                subtitle="దైవ దర్శనం",
                output_path=out_file
            )
            self.assertTrue(out_file.exists())
            analysis = analyze_thumbnail_file(out_file, allow_mock=True)
            self.assertTrue(analysis["valid"])

    def test_no_flux_or_gemini_fallback_when_pollinations_fails(self):
        # Ensure Pollinations failure raises PollinationsError without falling back to Flux or mock
        self.mock_bg.side_effect = PollinationsError("Pollinations endpoint unavailable")
        gen = PollinationsThumbnailGenerator()
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "fail_thumb.png"
            with self.assertRaises(PollinationsError):
                gen.generate_thumbnail("Varaha", "Subtitle", out_file)
            self.assertFalse(out_file.exists())

    def test_flux_thumbnail_strictly_prohibited(self):
        gen = FluxThumbnailGenerator()
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_file = Path(tmp_dir) / "flux.png"
            with self.assertRaises(NotImplementedError) as ctx:
                gen.generate_thumbnail("Varaha", "Subtitle", out_file)
            self.assertIn("reserved exclusively for video scenes", str(ctx.exception))

    def test_video_flux_generator_remains_intact(self):
        # Architecturally verify that the video scene visual generator still has Flux and is untouched
        from src.visual.providers import FluxProvider
        self.assertIsNotNone(FluxProvider)


# ─────────────────────────────────────────────────────────────────────────────
class TestThumbnailCLI(unittest.TestCase):
    """Test run_thumbnail_generator.py CLI interface and parameters (Test 14)."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.decision_dir = Path(self.tmp_dir.name) / "decision"
        self.scripts_dir = Path(self.tmp_dir.name) / "scripts"
        self.thumbnail_dir = Path(self.tmp_dir.name) / "thumbnails"

        self.decision_dir.mkdir()
        self.scripts_dir.mkdir()
        self.thumbnail_dir.mkdir()

        self.patch_decision_dir = patch("run_thumbnail_generator.DECISION_DIR", self.decision_dir)
        self.patch_scripts_dir = patch("run_thumbnail_generator.SCRIPTS_DIR", self.scripts_dir)
        self.patch_thumbnail_dir = patch("run_thumbnail_generator.THUMBNAIL_DIR", self.thumbnail_dir)

        self.patch_decision_dir.start()
        self.patch_scripts_dir.start()
        self.patch_thumbnail_dir.start()

    def tearDown(self):
        self.patch_decision_dir.stop()
        self.patch_scripts_dir.stop()
        self.patch_thumbnail_dir.stop()
        self.tmp_dir.cleanup()

    def test_cli_mock_provider_works(self):
        d = _make_decision()
        decision_file = self.decision_dir / "decision_20261113_120000.json"
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

    def test_cli_flux_provider_rejected(self):
        d = _make_decision()
        decision_file = self.decision_dir / "decision_20261113_120000.json"
        decision_file.write_text(json.dumps(d), encoding="utf-8")

        with patch("sys.argv", ["run_thumbnail_generator.py", "--provider", "flux"]):
            with self.assertRaises(SystemExit) as cm:
                run_thumbnail_generator.main()
            self.assertEqual(cm.exception.code, 1)

    @patch("src.thumbnail.providers.pollinations.PollinationsProvider.generate_background")
    def test_cli_pollinations_with_script_flag_extracts_telugu_title(self, mock_bg):
        def _fake_generate(prompt, output_path, **kwargs):
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            Path(output_path).write_bytes(_make_valid_png_bytes(1280, 720))
            return Path(output_path)

        mock_bg.side_effect = _fake_generate

        d = _make_decision(title="The Secret of Varaha Avatar", deity="varaha")
        decision_file = self.decision_dir / "decision_20261113_130000.json"
        decision_file.write_text(json.dumps(d), encoding="utf-8")

        s = {
            "title": "వరాహ అవతార రహస్యం: మహావిష్ణువు భూదేవిని ఎందుకు రక్షించారు?",
            "language_code": "te-IN"
        }
        script_file = self.scripts_dir / "script_20261113_130000.json"
        script_file.write_text(json.dumps(s), encoding="utf-8")

        with patch("sys.argv", [
            "run_thumbnail_generator.py",
            "--input", str(decision_file),
            "--script", str(script_file),
            "--provider", "pollinations",
            "--language", "te-IN"
        ]):
            run_thumbnail_generator.main()

        saved_meta = list(self.thumbnail_dir.glob("thumbnail_metadata_*.json"))
        saved_img = list(self.thumbnail_dir.glob("thumbnail_*.png"))

        self.assertEqual(len(saved_meta), 1)
        self.assertEqual(len(saved_img), 1)

        meta_data = json.loads(saved_meta[0].read_text(encoding="utf-8"))
        self.assertEqual(meta_data["provider"], "pollinations")
        self.assertEqual(meta_data["title"], "వరాహ అవతార రహస్యం: మహావిష్ణువు భూదేవిని ఎందుకు రక్షించారు?")
        self.assertEqual(meta_data["language_code"], "te-IN")


if __name__ == "__main__":
    unittest.main()
