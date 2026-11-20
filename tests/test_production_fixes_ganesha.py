# tests/test_production_fixes_ganesha.py
# Comprehensive regression tests for the First Ganesha Telugu Short production fix phase:
# 1. Caption LF line endings (no CRLF / box glyphs)
# 2. Telugu script integrity (rejection of foreign Indic scripts e.g. Odia, Devanagari, Bengali)
# 3. Telugu complex shaping & HarfBuzz filter
# 4. Watermark exclusion (APPR-REV-GANESHA-0066 excluded, APPR-REV-GANESHA-0070 selected)
# 5. Caption layout & safe margin positioning
# 6. Duration compliance for Shorts

import subprocess
import unittest
from pathlib import Path

from src.assets.approval_registry import get_trusted_registry, normalize_repo_path
from src.assets.manifest import load_asset_manifest
from src.assets.selector import (
    PRODUCTION_EXCLUDED_ASSET_PATHS,
    PRODUCTION_REPLACEMENT_ASSETS,
    build_deity_visual_timeline,
    is_asset_production_eligible,
    select_scene_assets,
    _is_item_verified_visual,
)
from src.script.generator import (
    validate_script_language_integrity,
    validate_text_language_integrity,
)
from src.video.composer import format_caption_text
from src.video.effects import get_caption_filter, get_video_filtergraph_for_scene, resolve_caption_font
from src.video.format_config import validate_production_short_duration


class TestCaptionEncodingAndLayout(unittest.TestCase):
    """Phase 1 & Phase 6: Caption encoding, layout, and line count."""

    def test_caption_file_generation_pure_lf(self):
        """Verifies caption text files are strictly LF and contain zero CR bytes (0x0D)."""
        sample_text = (
            "సమస్త లోకాలకు విఘ్నాలను తొలగించే వినాయకుడు తన ఒక దంతాన్ని "
            "ఎందుకు కోల్పోయాడో మీకు తెలుసా? ఈ వీడియోలో ఆ మహా త్యాగ రహస్యాన్ని తెలుసుకుందాం."
        )
        formatted = format_caption_text(sample_text, max_chars_per_line=36, max_lines=3)
        self.assertNotIn("\r", formatted)

        # Write to temporary file with explicit LF newline
        out_dir = Path("data/test_caption_output")
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "test_lf_caption.txt"

        clean_lf = formatted.replace("\r\n", "\n").replace("\r", "\n")
        out_file.write_text(clean_lf, encoding="utf-8", newline="\n")

        raw_bytes = out_file.read_bytes()
        self.assertNotIn(b"\r", raw_bytes, "Caption file contains CR bytes (0x0D), which cause empty square boxes in FFmpeg")
        self.assertIn(b"\n", raw_bytes, "Caption file must contain LF bytes")

    def test_format_caption_text_max_lines(self):
        """Verifies caption text wrapping respects max_lines=3 for mobile safe areas."""
        long_text = (
            "మొదటి లైను చాలా పెద్దదిగా ఉంది. రెండవ లైను కూడా అంతే పెద్దదిగా ఉంది. "
            "మూడవ లైను ఇక్కడ మొదలవుతుంది. నాల్గవ లైను ఖచ్చితంగా తగ్గించబడాలి లేదా కట్ అవ్వాలి."
        )
        wrapped = format_caption_text(long_text, max_chars_per_line=30, max_lines=3)
        lines = wrapped.split("\n")
        self.assertLessEqual(len(lines), 3, "Captions must not exceed max_lines=3 per cue")

    def test_caption_filter_has_text_shaping(self):
        """Verifies drawtext filter string explicitly includes text_shaping=1."""
        filt = get_caption_filter("dummy_captions.txt", language_code="te-IN", fontsize=44, y_position_ratio=0.65)
        self.assertIn("text_shaping=1", filt, "Caption filter must explicitly enable HarfBuzz text shaping")
        self.assertIn("fontsize=44", filt)
        self.assertIn("y=h*0.65", filt)

    def test_vertical_scene_filtergraph_safe_margin(self):
        """Verifies vertical filtergraph uses safe y_ratio=0.65 and fontsize=44."""
        filter_chain = get_video_filtergraph_for_scene(
            duration_seconds=5,
            width=1080,
            height=1920,
            caption_text_file="test_cap.txt",
            language_code="te-IN",
        )
        self.assertIn("y=h*0.65", filter_chain)
        self.assertIn("fontsize=44", filter_chain)
        self.assertIn("text_shaping=1", filter_chain)


class TestTeluguScriptIntegrity(unittest.TestCase):
    """Phase 2: Foreign Indic script rejection and Telugu integrity."""

    def test_pure_telugu_passes(self):
        """Valid Telugu text with proper punctuation passes cleanly."""
        valid_telugu = "విఘ్న నాయకుడైన శ్రీ గణేశుని ఏకదంత దివ్య రూపం జ్ఞానానికి నిదర్శనం!"
        ok, err = validate_text_language_integrity(valid_telugu, "te-IN")
        self.assertTrue(ok, f"Expected valid Telugu to pass, got error: {err}")

    def test_telugu_with_danda_passes(self):
        """Telugu text with Sanskrit danda (U+0964) and double danda (U+0965) passes."""
        telugu_sloka = "శుక్లాంబరధరం విష్ణుం శశివర్ణం చతుర్భుజం । ప్రసన్నవదనం ధ్యాయేత్ సర్వవిఘ్నోపశాంతయే ॥"
        ok, err = validate_text_language_integrity(telugu_sloka, "te-IN")
        self.assertTrue(ok, f"Expected danda to be permitted in Telugu, got: {err}")

    def test_odia_character_rejection(self):
        """Explicitly detects and rejects Odia script (U+0B00-U+0B7F), e.g. U+0B05."""
        # The exact corrupted text from the audit
        corrupted_text = "ఆయన చేసిన ఈ త్యాగం \u0B05ద్వితీయం!"  # contains Odia letter A U+0B05
        ok, err = validate_text_language_integrity(corrupted_text, "te-IN", field_name="scene_3_voice_text")
        self.assertFalse(ok)
        self.assertIn("foreign Indic character", err)
        self.assertIn("U+0B05", err)
        self.assertIn("Odia", err)

    def test_devanagari_character_rejection_in_telugu(self):
        """Rejects Devanagari letters (e.g. U+0915, U+0905) inside Telugu text."""
        corrupted_text = "శ్రీ గణేశునికి \u0915 పూజ చేయండి."
        ok, err = validate_text_language_integrity(corrupted_text, "te-IN")
        self.assertFalse(ok)
        self.assertIn("Devanagari", err)
        self.assertIn("U+0915", err)

    def test_bengali_character_rejection_in_telugu(self):
        """Rejects Bengali characters (U+0980-U+09FF) in Telugu text."""
        corrupted_text = "శ్రీ గణేశునికి \u0985 పూజ చేయండి."
        ok, err = validate_text_language_integrity(corrupted_text, "te-IN")
        self.assertFalse(ok)
        self.assertIn("Bengali", err)

    def test_validate_script_data_structure_rejection(self):
        """Verifies validate_script_language_integrity rejects corrupted scene_scripts."""
        script_dict = {
            "title": "వినాయకుడి ఏకదంతం వెనుక ఉన్న అసలు రహస్యం ఏమిటి?",
            "narration": "సమస్త లోకాలకు విఘ్నాలను తొలగించే వినాయకుని కథ.",
            "scene_scripts": [
                {"scene": 1, "voice_text": "మొదటి దృశ్యం పవిత్రమైనది."},
                {"scene": 2, "voice_text": "రెండవ దృశ్యం \u0B05ద్వితీయం!"},  # Odia glyph in scene 2
            ],
        }
        ok, err = validate_script_language_integrity(script_dict, "te-IN")
        self.assertFalse(ok)
        self.assertIn("scene_scripts[1].voice_text", err)
        self.assertIn("U+0B05", err)


class TestWatermarkExclusionAndReplacement(unittest.TestCase):
    """Phase 4: Watermark exclusion and clean approved replacement."""

    WATERMARKED_ASSET = "assets/gods/ganesha/0f8a0b018493cd68cc55168ee1764e14.jpg"
    CLEAN_REPLACEMENT = "assets/gods/ganesha/20837852b7fe042b03cf0421442a16fa.jpg"

    def setUp(self):
        from src.assets.approval_registry import get_trusted_registry, TrustedAssetApprovalRecord
        reg = get_trusted_registry()
        reg.register_record(
            TrustedAssetApprovalRecord(
                record_id="APPR-REV-GANESHA-0070",
                exact_rel_path=self.CLEAN_REPLACEMENT,
                canonical_deity="ganesha",
                avatar="ganesha",
                approval_status="APPROVED",
                provenance="Test clean replacement",
                aspect_ratio="9:16",
                content_type="image",
                reviewer="REV-TEST-01",
                review_timestamp="2026-11-20T10:00:00Z",
            )
        )

    def tearDown(self):
        from src.assets.approval_registry import get_trusted_registry
        get_trusted_registry().reset_to_builtins()

    def test_exclusion_registry_membership(self):
        """Confirms 0f8a is in PRODUCTION_EXCLUDED_ASSET_PATHS and 2083 is target replacement."""
        self.assertIn(self.WATERMARKED_ASSET, PRODUCTION_EXCLUDED_ASSET_PATHS)
        self.assertEqual(PRODUCTION_REPLACEMENT_ASSETS.get(self.WATERMARKED_ASSET), self.CLEAN_REPLACEMENT)
        self.assertFalse(is_asset_production_eligible(self.WATERMARKED_ASSET))
        self.assertTrue(is_asset_production_eligible(self.CLEAN_REPLACEMENT))

    def test_is_item_verified_visual_blocks_watermarked_asset(self):
        """Confirms _is_item_verified_visual returns False for watermarked asset."""
        item = {"path": self.WATERMARKED_ASSET}
        is_ver = _is_item_verified_visual(item, deity_key="ganesha")
        self.assertFalse(is_ver)
        self.assertEqual(item.get("approval_status"), "EXCLUDED")
        self.assertEqual(item.get("verification_status"), "excluded_watermark")

    def test_clean_replacement_is_approved_and_verified(self):
        """Confirms replacement 2083 is approved in trusted registry and passes verification."""
        registry = get_trusted_registry()
        is_app, reason, rec = registry.is_asset_approved(self.CLEAN_REPLACEMENT, deity="ganesha")
        self.assertTrue(is_app, f"Replacement {self.CLEAN_REPLACEMENT} must be approved: {reason}")
        self.assertEqual(rec.record_id, "APPR-REV-GANESHA-0070")

        item = {"path": self.CLEAN_REPLACEMENT}
        is_ver = _is_item_verified_visual(item, deity_key="ganesha")
        self.assertTrue(is_ver)
        self.assertEqual(item.get("approval_status"), "APPROVED")

    def test_select_scene_assets_never_picks_watermarked_asset(self):
        """Confirms select_scene_assets never selects 0f8a and selects 2083 for Scene 2."""
        manifest = load_asset_manifest()
        scenes = [
            {"scene": 1, "voice_text": "Scene 1 text"},
            {"scene": 2, "voice_text": "Scene 2 text with Vyasa and writing"},
            {"scene": 3, "voice_text": "Scene 3 text"},
        ]
        decisions = select_scene_assets("ganesha", scenes, manifest)
        selected_paths = [d.get("image_file") or d.get("path") for d in decisions]

        for p in selected_paths:
            norm = normalize_repo_path(p)
            self.assertNotEqual(norm, self.WATERMARKED_ASSET, f"Watermarked asset {norm} was selected!")

        scene_2_norm = normalize_repo_path(selected_paths[1])
        self.assertEqual(scene_2_norm, self.CLEAN_REPLACEMENT, "Scene 2 must select clean approved replacement 2083")

    def test_build_deity_visual_timeline_excludes_watermarked_asset(self):
        """Confirms build_deity_visual_timeline excludes 0f8a from timeline."""
        manifest = load_asset_manifest()
        timeline = build_deity_visual_timeline("ganesha", target_duration=45.0, manifest=manifest)
        timeline_paths = [normalize_repo_path(item.get("path")) for item in timeline]
        self.assertNotIn(self.WATERMARKED_ASSET, timeline_paths)


class TestDurationCompliance(unittest.TestCase):
    """Phase 7: Duration compliance for Shorts."""

    def test_duration_under_30s_fails(self):
        """Shorts under 30.0s must fail compliance."""
        ok, err = validate_production_short_duration(29.84)
        self.assertFalse(ok)
        self.assertIn("below production target minimum", err)

    def test_duration_between_30s_and_45s_passes(self):
        """Shorts between 30.0s and 45.0s pass cleanly."""
        for d in [30.0, 35.5, 40.0, 42.0, 45.0]:
            ok, err = validate_production_short_duration(d)
            self.assertTrue(ok, f"Duration {d}s should pass, got: {err}")

    def test_duration_over_55s_fails(self):
        """Shorts over 55s fail compliance."""
        ok, err = validate_production_short_duration(58.0)
        self.assertFalse(ok)
        self.assertIn("exceeds production target maximum", err)


class TestTeluguComplexShapingFFmpeg(unittest.TestCase):
    """Phase 3: Visual rendering test for complex Telugu shaping with FFmpeg."""

    def test_ffmpeg_telugu_shaping_renders(self):
        """Confirms FFmpeg renders complex Telugu conjuncts with text_shaping=1 without error."""
        font_path = resolve_caption_font(language_code="te-IN")
        self.assertTrue(Path(font_path).exists(), f"Font does not exist: {font_path}")

        test_caption = Path("data/test_caption_output/shaping_test.txt")
        test_caption.parent.mkdir(parents=True, exist_ok=True)
        # Complex conjuncts: శ్రీ, విఘ్న, దంతం, స్తంభం
        complex_telugu = "శ్రీ విఘ్నేశ్వర స్వామి ఏకదంతం - అద్వితీయ త్యాగం"
        test_caption.write_text(complex_telugu, encoding="utf-8", newline="\n")

        out_frame = Path("data/test_caption_output/test_shaping_frame.png")
        escaped_font = font_path.replace("\\", "/").replace(":", "\\:")
        escaped_txt = str(test_caption.absolute()).replace("\\", "/").replace(":", "\\:")

        drawtext_filter = (
            f"drawtext=fontfile='{escaped_font}':textfile='{escaped_txt}':"
            f"fontsize=44:fontcolor=white:text_shaping=1:box=1:boxcolor=black@0.65:"
            f"boxborderw=12:line_spacing=10:x=(w-text_w)/2:y=h*0.65"
        )

        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=black:s=1080x1920:d=1",
            "-vf", drawtext_filter,
            "-frames:v", "1",
            str(out_frame),
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"FFmpeg drawtext failed: {res.stderr}")
        self.assertTrue(out_frame.exists(), "Rendered frame was not created")
        self.assertGreater(out_frame.stat().st_size, 1000, "Rendered frame is unexpectedly small")


if __name__ == "__main__":
    unittest.main()
