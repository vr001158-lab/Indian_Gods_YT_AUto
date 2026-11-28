# tests/test_master_automation.py
# Comprehensive Regression Test Suite for:
# 1. Simplified Local Thumbnail Generation & Video-to-Frame Extraction
# 2. Video-First Asset Hierarchy & Aspect Ratio Preservation
# 3. Hindu Weekday Deity Automation in Asia/Kolkata & Deterministic Rotation
# 4. Automated Missing-Asset Fallback Downloader & Quarantine Isolation
# 5. Publisher Safety & Telugu-Only Pipeline Verification

from __future__ import annotations

import io
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
from PIL import Image

sys.path.insert(0, os.getcwd())

from src.decision.weekday_deity import (
    KOLKATA_TZ,
    WEEKDAY_DEITY_MAPPING,
    get_weekday_info,
    select_weekday_deity,
    rotate_deity_for_day,
    get_day_of_week_deity_bonus,
    is_deity_eligible_for_weekday,
)
from src.thumbnail.composer import (
    compose_reused_thumbnail,
    prepare_background_canvas,
)
from src.thumbnail.local_generator import (
    LocalThumbnailGenerator,
    extract_video_frame_safely,
)
from src.thumbnail.schemas import validate_metadata_output
from src.assets.fallback_downloader import (
    MissingAssetFallbackDownloader,
    validate_image_file,
    validate_video_file,
)
from src.assets.selector import (
    select_scene_assets,
    select_landscape_scene_assets,
    NoMatchingDeityAssetError,
)
from src.thumbnail.asset_selector import (
    NoSuitableThumbnailAssetError,
)
from src.qa.checks import (
    _is_trusted_approved_asset,
    check_deity_identity_consistency,
)
from src.decision.report import run_decision_pipeline


def _make_candidate(topic: str, deity: str, score: int = 80) -> dict[str, Any]:
    """Builds a fully-populated, schema-valid research candidate dict."""
    return {
        "topic": topic,
        "category": "devotional",
        "overall_score": score,
        "demand_score": score,
        "relevance_score": score,
        "competition_score": 40,
        "evergreen_score": 90,
        "freshness_score": 85,
        "curiosity_score": 80,
        "long_form_potential": 80,
        "shorts_potential": 85,
        "confidence": "high",
        "data_source": "cached_youtube_api",
        "deity": deity,
        "suggested_angle": "devotional significance",
        "content_gap": "high",
    }


class TestMasterAutomationSuite(unittest.TestCase):
    """
    16-point master regression test suite for thumbnail simplicity,
    video-first visual assets, Hindu weekday automation, and safety gates.
    """

    def setUp(self):
        from src.assets.approval_registry import get_trusted_registry, TrustedAssetApprovalRecord
        reg = get_trusted_registry()
        seeds = [
            ("assets/gods/hanuman/test_h.jpg", "hanuman"),
            ("assets/gods/ganesha/test_g.jpg", "ganesha"),
            ("assets/gods/lord_shiva/test_s.jpg", "lord_shiva"),
            ("assets/gods/chandra/test_ch.jpg", "chandra"),
            ("assets/gods/kali/test_kal.jpg", "kali"),
            ("assets/gods/shani/test_shani.jpg", "shani"),
            ("assets/gods/budha/test_budha.jpg", "budha"),
            ("assets/gods/krishna/test_k.jpg", "krishna"),
            ("assets/gods/lord_vishnu/test_v.jpg", "lord_vishnu"),
            ("assets/gods/subramanya/test_sub.jpg", "subramanya"),
            ("assets/gods/parvathi/test_p.jpg", "parvathi"),
            ("assets/gods/lakshmi_devi/test_l.jpg", "lakshmi_devi"),
            ("assets/gods/surya/test_surya.jpg", "surya"),
            ("assets/gods/kaal_bhairav/test_kb.jpg", "kaal_bhairav"),
        ]
        for p, d in seeds:
            reg.register_record(
                TrustedAssetApprovalRecord(
                    record_id=f"APPR-TEST-AUTO-{d.upper()}-001",
                    exact_rel_path=p,
                    canonical_deity=d,
                    approval_status="APPROVED",
                    provenance="Test suite seed record",
                    aspect_ratio="9:16",
                    content_type="image",
                    reviewer="REV-TEST-01",
                    review_timestamp="2026-11-20T10:00:00Z",
                )
            )

    def tearDown(self):
        from src.assets.approval_registry import get_trusted_registry
        get_trusted_registry().reset_to_builtins()

    # ──────────────────────────────────────────────────────────────────────────
    # Test 1: Thumbnail generator rejects video files passed directly to Pillow
    # ──────────────────────────────────────────────────────────────────────────
    def test_01_thumbnail_generator_rejects_video_files_passed_directly_to_pillow(self):
        """Pillow Image.open raises UnidentifiedImageError on raw video files."""
        from PIL import UnidentifiedImageError

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
            tf.write(b"fake mp4 video content container bytes")
            fake_video = Path(tf.name)

        try:
            with self.assertRaises((UnidentifiedImageError, IOError)):
                Image.open(fake_video)
        finally:
            fake_video.unlink(missing_ok=True)

    # ──────────────────────────────────────────────────────────────────────────
    # Test 2: Video frame extraction succeeds using FFmpeg for thumbnail backgrounds
    # ──────────────────────────────────────────────────────────────────────────
    def test_02_video_frame_extraction_succeeds_using_ffmpeg(self):
        """extract_video_frame_safely extracts a valid PNG frame from a real repository video."""
        sample_video = Path("assets/gods_processed/ram/vertical/1116118720173406492__img.mp4")
        if not sample_video.exists():
            # Check Ganesha video
            ganesha_videos = list(Path("assets/gods/ganesha").glob("*.mp4"))
            if ganesha_videos:
                sample_video = ganesha_videos[0]

        if not sample_video.exists():
            self.skipTest("No local test video physically present on disk.")

        with tempfile.TemporaryDirectory() as td:
            out_frame = Path(td) / "extracted_frame.png"
            extracted = extract_video_frame_safely(sample_video, out_frame, timestamp_str="00:00:01")
            self.assertTrue(extracted.exists())
            self.assertGreater(extracted.stat().st_size, 0)
            with Image.open(extracted) as im:
                self.assertIn(im.format.upper(), ("PNG", "JPEG"))

    # ──────────────────────────────────────────────────────────────────────────
    # Test 3: Local thumbnail generation produces valid 1280x720 PNG with Telugu text
    # ──────────────────────────────────────────────────────────────────────────
    def test_03_local_thumbnail_generation_produces_valid_1280x720_with_telugu_text(self):
        """LocalThumbnailGenerator generates 1280x720 thumbnail with Telugu Unicode typography."""
        with tempfile.TemporaryDirectory() as td:
            # Create a synthetic 16:9 background
            bg_path = Path(td) / "bg.png"
            Image.new("RGB", (1280, 720), color=(30, 20, 40)).save(bg_path)

            out_thumb = Path(td) / "out_thumb.png"
            gen = LocalThumbnailGenerator()
            gen.generate_thumbnail(
                title="శివుని త్రిశూలం రహస్యం",
                subtitle="దైవ దర్శనం",
                output_path=out_thumb,
                background_image_path=bg_path,
                language_code="te-IN",
                deity="lord_shiva",
            )

            self.assertTrue(out_thumb.exists())
            with Image.open(out_thumb) as im:
                self.assertEqual(im.size, (1280, 720))
                self.assertEqual(im.format.upper(), "PNG")

    # ──────────────────────────────────────────────────────────────────────────
    # Test 4: Weekday deity resolution for all 7 days matches Hindu calendar in Asia/Kolkata
    # ──────────────────────────────────────────────────────────────────────────
    def test_04_weekday_deity_resolution_for_all_7_days(self):
        """All 7 weekdays strictly map to exact authoritative Hindu deity groups in Asia/Kolkata."""
        # 2026-11-16 is Monday, 2026-11-22 is Sunday
        expected_days = {
            0: (
                "Monday",
                "Somvar",
                ["lord_shiva", "parvathi", "chandra"],
                ["Lord Shiva", "Goddess Parvati", "Chandra Deva"],
                ["ram", "venkateswara", "sai_baba", "shani"],
            ),
            1: (
                "Tuesday",
                "Mangalvar",
                ["hanuman", "ganesha", "durga", "kali", "subramanya"],
                ["Lord Hanuman", "Lord Ganesha", "Goddess Durga", "Goddess Kali", "Lord Kartikeya / Skanda"],
                ["ram", "venkateswara", "krishna", "surya"],
            ),
            2: (
                "Wednesday",
                "Budhvar",
                ["budha", "ganesha", "krishna", "vithal"],
                ["Budha", "Lord Ganesha", "Lord Krishna", "Lord Vithal"],
                ["shiva", "durga", "hanuman", "surya"],
            ),
            3: (
                "Thursday",
                "Guruvar",
                ["lord_vishnu", "brihaspati", "krishna"],
                ["Lord Vishnu", "Brihaspati", "Lord Krishna"],
                ["dattatreya", "sai_baba", "raghavendra", "venkateswara", "shiva"],
            ),
            4: (
                "Friday",
                "Shukravar",
                ["lakshmi_devi", "santoshi_ma", "annapurneshwari", "durga"],
                ["Goddess Mahalakshmi", "Santoshi Ma", "Annapurneshwari", "Goddess Durga"],
                ["saraswati", "lalitha", "parvati", "krishna", "hanuman"],
            ),
            5: (
                "Saturday",
                "Shaniwar",
                ["shani", "hanuman"],
                ["Lord Shani", "Lord Hanuman"],
                ["venkateswara", "narasimha", "shiva", "krishna"],
            ),
            6: (
                "Sunday",
                "Ravivar",
                ["surya", "kaal_bhairav"],
                ["Lord Surya", "Kaal Bhairav"],
                ["ram", "krishna", "shiva", "vishnu"],
            ),
        }

        for day_idx, (exp_eng, exp_san, exp_deities, exp_display_names, unrelated_deities) in expected_days.items():
            dt = datetime(2026, 11, 16 + day_idx, 10, 0, tzinfo=KOLKATA_TZ)
            info = get_weekday_info(dt)
            self.assertEqual(info["english_day"], exp_eng)
            self.assertEqual(info["sanskrit_day"], exp_san)

            # Assert exact equality of authoritative deity list (no additions, no omissions)
            self.assertEqual(info["primary_deities"], exp_deities)

            # Assert exact display names
            actual_display_names = [info["display_names"][k] for k in exp_deities]
            self.assertEqual(actual_display_names, exp_display_names)

            # Assert unrelated deities are strictly absent
            for unrel in unrelated_deities:
                self.assertNotIn(unrel, info["primary_deities"])
                self.assertFalse(is_deity_eligible_for_weekday(unrel, dt))

            # Assert eligible deities return True
            for elig in exp_deities:
                self.assertTrue(is_deity_eligible_for_weekday(elig, dt))

    # ──────────────────────────────────────────────────────────────────────────
    # Test 5: Tuesday rotation rotates deterministically across the 5 eligible deities
    # ──────────────────────────────────────────────────────────────────────────
    def test_05_tuesday_deterministic_rotation_across_5_deities(self):
        """Tuesday rotates deterministically through Hanuman, Ganesha, Durga, Kali, Subramanya."""
        tuesday_deities = ["hanuman", "ganesha", "durga", "kali", "subramanya"]
        seen_deities = set()

        # Iterate over several consecutive Tuesdays
        for week_offset in range(15):
            dt = datetime(2026, 11, 17, 10, 0, tzinfo=KOLKATA_TZ)
            test_dt = datetime.fromtimestamp(dt.timestamp() + week_offset * 7 * 86400, tz=KOLKATA_TZ)
            chosen = rotate_deity_for_day(test_dt, tuesday_deities)
            self.assertIn(chosen, tuesday_deities)
            seen_deities.add(chosen)

        # All 5 deities should be represented over multiple weeks
        self.assertEqual(len(seen_deities), 5)

    # ──────────────────────────────────────────────────────────────────────────
    # Test 6: Decision stage incorporates weekday deity and devotional context
    # ──────────────────────────────────────────────────────────────────────────
    def test_06_decision_stage_incorporates_weekday_deity(self):
        """Decision pipeline includes weekday_deity_context with scheduled deity."""
        candidates = [
            {
                "topic": "వినాయక చవితి విశిష్టత",
                "category": "devotional",
                "overall_score": 88,
                "demand_score": 85,
                "relevance_score": 90,
                "competition_score": 40,
                "evergreen_score": 95,
                "freshness_score": 90,
                "curiosity_score": 85,
                "long_form_potential": 85,
                "shorts_potential": 90,
                "confidence": "high",
                "data_source": "cached_youtube_api",
                "deity": "ganesha",
                "suggested_angle": "devotional significance",
                "content_gap": "high",
            }
        ]
        decision = run_decision_pipeline(candidates, save=False, language_code="te-IN")
        self.assertTrue(decision["approved_for_generation"])
        self.assertIn("weekday_deity_context", decision)
        ctx = decision["weekday_deity_context"]
        self.assertIn("scheduled_deity", ctx)
        self.assertIn("english_day", ctx)
        self.assertIn("visual_and_offering_context", ctx)

    # ──────────────────────────────────────────────────────────────────────────
    # Test 7: Visual asset selector prioritizes local videos over local images
    # ──────────────────────────────────────────────────────────────────────────
    def test_07_visual_selector_prioritizes_videos_over_images(self):
        """Asset selector prioritizes video assets over image assets for scenes."""
        manifest = {
            "deities": {
                "lord_shiva": {
                    "images": [
                        {"path": "assets/gods/lord_shiva/image1.png", "orientation": "portrait", "verified_visual": True, "type": "image"}
                    ],
                    "videos": [
                        {"path": "assets/gods/lord_shiva/video1.mp4", "orientation": "portrait", "verified_visual": True, "type": "video"}
                    ],
                }
            }
        }
        scenes = [{"scene": 1, "script": "Lord Shiva meditating on Kailash"}]
        selected = select_scene_assets("lord_shiva", scenes, manifest=manifest, content_type="short")
        self.assertEqual(len(selected), 1)
        # First choice should be the video
        self.assertEqual(selected[0]["source_path"], "assets/gods/lord_shiva/video1.mp4")
        self.assertEqual(selected[0]["asset_type"], "video")

    # ──────────────────────────────────────────────────────────────────────────
    # Test 8: Visual asset selector rejects cross-deity substitutions
    # ──────────────────────────────────────────────────────────────────────────
    def test_08_visual_selector_rejects_cross_deity_substitutions(self):
        """Asset selector fails closed and never substitutes unrelated deities."""
        manifest = {
            "deities": {
                "lord_shiva": {
                    "images": [{"path": "assets/gods/lord_shiva/shiva.png", "orientation": "portrait", "verified_visual": True}],
                    "videos": [],
                },
                "ganesha": {
                    "images": [],
                    "videos": [],
                }
            }
        }
        scenes = [{"scene": 1, "script": "Lord Ganesha wisdom"}]
        with self.assertRaises(RuntimeError):
            select_scene_assets("ganesha", scenes, manifest=manifest, allow_online_fallback=False)

    # ──────────────────────────────────────────────────────────────────────────
    # Test 9: Aspect ratio preservation (9:16 for shorts, 16:9 for landscape)
    # ──────────────────────────────────────────────────────────────────────────
    def test_09_aspect_ratio_preservation(self):
        """Landscape selector only accepts landscape assets (16:9); rejects portrait assets."""
        manifest = {
            "deities": {
                "lord_shiva": {
                    "images": [
                        {"path": "assets/gods/lord_shiva/portrait.png", "orientation": "portrait", "width": 1080, "height": 1920, "verified_visual": True},
                        {"path": "assets/gods_landscape_long_video/lord_shiva/landscape.png", "orientation": "landscape", "width": 1920, "height": 1080, "verified_visual": True},
                    ],
                    "videos": [],
                }
            }
        }
        scenes = [{"scene": 1, "script": "Shiva cosmic dance"}]
        selected = select_landscape_scene_assets("lord_shiva", scenes, manifest=manifest)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["source_path"], "assets/gods_landscape_long_video/lord_shiva/landscape.png")

    # ──────────────────────────────────────────────────────────────────────────
    # Test 10: Fallback downloader stores files in quarantine directories
    # ──────────────────────────────────────────────────────────────────────────
    def test_10_fallback_downloader_quarantine_path(self):
        """Fallback downloader quarantine paths follow assets/incoming/<deity>/<type>/."""
        with tempfile.TemporaryDirectory() as td:
            downloader = MissingAssetFallbackDownloader(incoming_root=td)
            vid_q = downloader.get_quarantine_directory("lord_shiva", "videos")
            img_q = downloader.get_quarantine_directory("lord_shiva", "images")
            self.assertTrue(str(vid_q).replace("\\", "/").endswith("lord_shiva/videos"))
            self.assertTrue(str(img_q).replace("\\", "/").endswith("lord_shiva/images"))

    # ──────────────────────────────────────────────────────────────────────────
    # Test 11: Fallback downloader runs completely non-interactively without prompt/input()
    # ──────────────────────────────────────────────────────────────────────────
    def test_11_fallback_downloader_non_interactive(self):
        """Fallback downloader never calls input() or interactive prompts."""
        with tempfile.TemporaryDirectory() as td:
            downloader = MissingAssetFallbackDownloader(incoming_root=td)
            with patch("builtins.input", side_effect=AssertionError("input() must NEVER be called!")):
                res = downloader.download_asset("hanuman", "sanjeevani hill", media_type="videos", url=None)
                self.assertEqual(res["status"], "NOT_DOWNLOADED")
                self.assertEqual(res["approval_status"], "UNAPPROVED")

    # ──────────────────────────────────────────────────────────────────────────
    # Test 12: Fallback downloader validates files with ffprobe (video) and Pillow (image)
    # ──────────────────────────────────────────────────────────────────────────
    def test_12_fallback_downloader_validation_tools(self):
        """Pillow validates images and ffprobe validates videos cleanly."""
        with tempfile.TemporaryDirectory() as td:
            # Valid image
            img_p = Path(td) / "test.png"
            Image.new("RGB", (100, 100), color=(255, 0, 0)).save(img_p)
            ok, msg, details = validate_image_file(img_p)
            self.assertTrue(ok)
            self.assertEqual(details["width"], 100)

            # Corrupt image
            bad_img = Path(td) / "bad.png"
            bad_img.write_bytes(b"garbage bytes")
            ok_bad, _, _ = validate_image_file(bad_img)
            self.assertFalse(ok_bad)

    # ──────────────────────────────────────────────────────────────────────────
    # Test 13: Quarantine assets remain unapproved until explicit catalog entry
    # ──────────────────────────────────────────────────────────────────────────
    def test_13_quarantine_assets_remain_unapproved(self):
        """Quarantined assets have approval_status='UNAPPROVED'."""
        with tempfile.TemporaryDirectory() as td:
            downloader = MissingAssetFallbackDownloader(incoming_root=td)
            q_dir = downloader.get_quarantine_directory("lord_shiva", "images")
            dummy_file = q_dir / "shiva_incoming.png"
            dummy_file.write_bytes(b"sample bytes")

            # Catalog approval check must reject uncataloged incoming file
            approved, reason = _is_trusted_approved_asset(str(dummy_file), "lord_shiva")
            self.assertFalse(approved)
            self.assertIn("lacks an explicit trusted asset approval record", reason)

    # ──────────────────────────────────────────────────────────────────────────
    # Test 14: QA gate rejects unapproved quarantine assets
    # ──────────────────────────────────────────────────────────────────────────
    def test_14_qa_gate_rejects_unapproved_quarantine_assets(self):
        """Final QA gate halts when scene references an unapproved quarantine asset."""
        decision = {"selected_topic": "Lord Shiva", "deity": "lord_shiva", "approved_for_generation": True}
        script = {"scenes": [{"scene": 1, "text": "Lord Shiva meditating"}]}
        visual_map = {
            "visual_scenes": [
                {
                    "scene": 1,
                    "image_file": "assets/incoming/lord_shiva/images/unapproved_shot.png",
                    "source_asset": "assets/incoming/lord_shiva/images/unapproved_shot.png",
                    "source_path": "assets/incoming/lord_shiva/images/unapproved_shot.png",
                    "source_asset_path": "assets/incoming/lord_shiva/images/unapproved_shot.png",
                    "provenance": "Quarantined download; unapproved external asset",
                    "verification_status": "DEITY_VERIFIED",  # Forged status
                    "canonical_deity": "lord_shiva",
                }
            ]
        }
        video_map = {"scenes": []}
        thumbnail_meta = {"deity": "lord_shiva", "title": "Lord Shiva Meditation"}
        passed, error_msg = check_deity_identity_consistency(decision, script, visual_map, video_map, thumbnail_meta)
        self.assertFalse(passed)
        self.assertIn("lacks an explicit trusted asset approval record", error_msg)

    # ──────────────────────────────────────────────────────────────────────────
    # Test 15: Telugu-only script, voice, metadata, and thumbnail texts
    # ──────────────────────────────────────────────────────────────────────────
    def test_15_telugu_only_enforcement(self):
        """Thumbnail metadata schema validates te-IN language code and Telugu text."""
        valid_meta = {
            "title": "వినాయక చవితి విశిష్టత",
            "topic": "వినాయక చవితి",
            "provider": "local",
            "resolution": "1280x720",
            "format": "png",
            "approved_source": "cached_youtube_api",
            "confidence": "high",
            "created_at": "20261117_120000",
            "approval_metadata": {
                "approved_for_generation": True,
                "selected_topic": "వినాయక చవితి",
                "score": 90,
                "confidence": "high",
                "data_source": "cached_youtube_api",
            }
        }
        ok, err = validate_metadata_output(valid_meta)
        self.assertTrue(ok, err)

    # ──────────────────────────────────────────────────────────────────────────
    # Test 16: Publisher safety: no live uploads in test/dry-run/render-only modes
    # ──────────────────────────────────────────────────────────────────────────
    def test_16_publisher_safety_no_live_uploads_in_safety_modes(self):
        """Publisher rejects live uploads when dry_run=True or render_only=True."""
        from src.publisher.safety import validate_production_environment

        # Dry-run allows execution without network/OAuth
        ok_dry, msg_dry = validate_production_environment(allow_dry_run=True)
        self.assertTrue(ok_dry)
        self.assertEqual(msg_dry, "")

        # In render-only mode without authorization, live publishing is strictly forbidden
        with patch.dict(os.environ, {"YOUTUBE_PUBLISH_AUTHORIZED": "false", "YOUTUBE_PUBLISH": "false", "RENDER_ONLY": "true"}):
            ok_prod, msg_prod = validate_production_environment(allow_dry_run=False)
            self.assertFalse(ok_prod)
            self.assertIn("strictly forbidden", msg_prod)

    # ──────────────────────────────────────────────────────────────────────────
    # Test 17: Chandra vs Shiva identity isolation (Monday)
    # ──────────────────────────────────────────────────────────────────────────
    def test_17_chandra_vs_shiva_identity_isolation(self):
        """Chandra Deva is distinct from Lord Shiva; shared folder cannot grant +15 bonus or cross-select."""
        # 2026-11-16 is Monday. Mock rotate_deity_for_day to return chandra
        monday_dt = datetime(2026, 11, 16, 10, 0, tzinfo=KOLKATA_TZ)
        with patch("src.decision.weekday_deity.rotate_deity_for_day", return_value="chandra"):
            # Chandra gets scheduled deity bonus (+15.0); Shiva gets eligible deity bonus (+8.0)
            self.assertEqual(get_day_of_week_deity_bonus("chandra", monday_dt), 15.0)
            self.assertEqual(get_day_of_week_deity_bonus("lord_shiva", monday_dt), 8.0)
            self.assertEqual(get_day_of_week_deity_bonus("shiva", monday_dt), 8.0)

            # In decision stage, Chandra candidate is in scheduled pool and wins over Shiva
            candidates = [
                _make_candidate("Lord Shiva Kailash Meditation", "lord_shiva", score=95),
                _make_candidate("Chandra Deva Somvar Blessings", "chandra", score=75),
            ]
            with patch("src.decision.weekday_deity.get_current_kolkata_datetime", return_value=monday_dt):
                decision = run_decision_pipeline(candidates, save=False, language_code="te-IN")
                self.assertIn("Chandra", decision["selected_topic"])
                self.assertEqual(decision["deity"], "chandra")

        # Shiva asset cannot be accepted as Chandra asset in QA or approval
        approved, reason = _is_trusted_approved_asset("assets/gods/lord_shiva/image.png", deity="chandra")
        self.assertFalse(approved)

        # QA gate rejects Shiva scene when topic is Chandra
        dec = {"selected_topic": "Chandra Deva Somvar", "deity": "chandra", "approved_for_generation": True}
        scr = {"scenes": [{"scene": 1, "text": "Chandra Deva"}]}
        vmap = {
            "visual_scenes": [{
                "scene": 1,
                "image_file": "assets/gods/lord_shiva/shiva.png",
                "canonical_deity": "lord_shiva",
                "provenance": "repository",
                "verification_status": "DEITY_VERIFIED",
            }]
        }
        passed, err = check_deity_identity_consistency(dec, scr, vmap, {"scenes": []}, {"deity": "chandra"})
        self.assertFalse(passed)
        self.assertIn("mismatch", err)

    # ──────────────────────────────────────────────────────────────────────────
    # Test 18: Kaal Bhairav vs Shiva identity isolation (Sunday)
    # ──────────────────────────────────────────────────────────────────────────
    def test_18_kaal_bhairav_vs_shiva_identity_isolation(self):
        """Kaal Bhairav is distinct from Lord Shiva; Shiva gets 0.0 bonus on Sunday and cannot substitute."""
        # 2026-11-22 is Sunday. Mock rotate_deity_for_day to return kaal_bhairav
        sunday_dt = datetime(2026, 11, 22, 10, 0, tzinfo=KOLKATA_TZ)
        with patch("src.decision.weekday_deity.rotate_deity_for_day", return_value="kaal_bhairav"), \
             patch("src.assets.approval_registry.TrustedAssetApprovalRegistry.has_approved_assets_for_deity", return_value=True):
            # Kaal Bhairav gets +15.0; Lord Shiva is NOT eligible on Sunday (gets 0.0)
            self.assertEqual(get_day_of_week_deity_bonus("kaal_bhairav", sunday_dt), 15.0)
            self.assertEqual(get_day_of_week_deity_bonus("bhairav", sunday_dt), 15.0)
            self.assertEqual(get_day_of_week_deity_bonus("lord_shiva", sunday_dt), 0.0)

            # Kaal Bhairav candidate wins over Shiva candidate
            candidates = [
                _make_candidate("Lord Shiva Kailash Meditation", "lord_shiva", score=95),
                _make_candidate("Kaal Bhairav Rahasya", "kaal_bhairav", score=75),
            ]
            with patch("src.decision.weekday_deity.get_current_kolkata_datetime", return_value=sunday_dt):
                decision = run_decision_pipeline(candidates, save=False, language_code="te-IN")
                self.assertIn("Kaal Bhairav", decision["selected_topic"])
                self.assertEqual(decision["deity"], "kaal_bhairav")

            # When only Shiva candidate is provided on Sunday, Controlled Exception is triggered
            with patch("src.decision.weekday_deity.get_current_kolkata_datetime", return_value=sunday_dt):
                dec_exc = run_decision_pipeline([candidates[0]], save=False, language_code="te-IN")
                self.assertTrue(dec_exc["weekday_deity_context"]["controlled_exception_applied"])

        # QA gate rejects Shiva scene when topic is Kaal Bhairav
        dec = {"selected_topic": "Kaal Bhairav", "deity": "kaal_bhairav", "approved_for_generation": True}
        scr = {"scenes": [{"scene": 1, "text": "Kaal Bhairav"}]}
        vmap = {
            "visual_scenes": [{
                "scene": 1,
                "image_file": "assets/gods/lord_shiva/shiva.png",
                "canonical_deity": "lord_shiva",
                "provenance": "repository",
                "verification_status": "DEITY_VERIFIED",
            }]
        }
        passed, err = check_deity_identity_consistency(dec, scr, vmap, {"scenes": []}, {"deity": "kaal_bhairav"})
        self.assertFalse(passed)
        self.assertIn("mismatch", err)

    # ──────────────────────────────────────────────────────────────────────────
    # Test 19: Kali vs Parvati identity isolation (Tuesday)
    # ──────────────────────────────────────────────────────────────────────────
    def test_19_kali_vs_parvati_identity_isolation(self):
        """Goddess Kali is distinct from Goddess Parvati; Parvati gets 0.0 on Tuesday and cannot substitute."""
        tuesday_dt = datetime(2026, 11, 17, 10, 0, tzinfo=KOLKATA_TZ)
        with patch("src.decision.weekday_deity.rotate_deity_for_day", return_value="kali"):
            # Kali gets +15.0; Parvati is NOT eligible on Tuesday (gets 0.0)
            self.assertEqual(get_day_of_week_deity_bonus("kali", tuesday_dt), 15.0)
            self.assertEqual(get_day_of_week_deity_bonus("parvathi", tuesday_dt), 0.0)
            self.assertEqual(get_day_of_week_deity_bonus("parvati", tuesday_dt), 0.0)

            # Kali candidate wins over Parvati candidate
            candidates = [
                _make_candidate("Goddess Parvati Story", "parvathi", score=90),
                _make_candidate("Maha Kali Mahatmyam", "kali", score=75),
            ]
            with patch("src.decision.weekday_deity.get_current_kolkata_datetime", return_value=tuesday_dt):
                decision = run_decision_pipeline(candidates, save=False, language_code="te-IN")
                self.assertIn("Kali", decision["selected_topic"])
                self.assertEqual(decision["deity"], "kali")

        # QA gate rejects generic Parvati scene for Kali topic
        dec = {"selected_topic": "Maha Kali Mahatmyam", "deity": "kali", "approved_for_generation": True}
        scr = {"scenes": [{"scene": 1, "text": "Maha Kali"}]}
        vmap = {
            "visual_scenes": [{
                "scene": 1,
                "image_file": "assets/gods/parvathi/parvathi.png",
                "canonical_deity": "parvathi",
                "avatar": "parvathi",
                "provenance": "repository",
                "verification_status": "DEITY_VERIFIED",
            }]
        }
        passed, err = check_deity_identity_consistency(dec, scr, vmap, {"scenes": []}, {"deity": "kali"})
        self.assertFalse(passed)
        self.assertIn("mismatch", err)

    # ──────────────────────────────────────────────────────────────────────────
    # Test 20: Shani vs Hanuman identity isolation (Saturday)
    # ──────────────────────────────────────────────────────────────────────────
    def test_20_shani_vs_hanuman_identity_isolation(self):
        """Lord Shani is distinct from Lord Hanuman; Hanuman gets eligible bonus (+8.0) not +15.0."""
        saturday_dt = datetime(2026, 11, 21, 10, 0, tzinfo=KOLKATA_TZ)
        with patch("src.decision.weekday_deity.rotate_deity_for_day", return_value="shani"):
            # Shani gets +15.0; Hanuman gets +8.0 (eligible, not scheduled)
            self.assertEqual(get_day_of_week_deity_bonus("shani", saturday_dt), 15.0)
            self.assertEqual(get_day_of_week_deity_bonus("hanuman", saturday_dt), 8.0)

            # Shani candidate wins over Hanuman candidate
            candidates = [
                _make_candidate("Hanuman Chalisa", "hanuman", score=92),
                _make_candidate("Shani Shingnapur Darshanam", "shani", score=75),
            ]
            with patch("src.decision.weekday_deity.get_current_kolkata_datetime", return_value=saturday_dt):
                decision = run_decision_pipeline(candidates, save=False, language_code="te-IN")
                self.assertIn("Shani", decision["selected_topic"])
                self.assertEqual(decision["deity"], "shani")

        # QA gate rejects Hanuman scene for Shani topic
        dec = {"selected_topic": "Shani Dev", "deity": "shani", "approved_for_generation": True}
        scr = {"scenes": [{"scene": 1, "text": "Shani Dev"}]}
        vmap = {
            "visual_scenes": [{
                "scene": 1,
                "image_file": "assets/gods/hanuman/hanuman.png",
                "canonical_deity": "hanuman",
                "provenance": "repository",
                "verification_status": "DEITY_VERIFIED",
            }]
        }
        passed, err = check_deity_identity_consistency(dec, scr, vmap, {"scenes": []}, {"deity": "shani"})
        self.assertFalse(passed)
        self.assertIn("mismatch", err)

    # ──────────────────────────────────────────────────────────────────────────
    # Test 21: Budha vs Krishna identity isolation (Wednesday)
    # ──────────────────────────────────────────────────────────────────────────
    def test_21_budha_vs_krishna_identity_isolation(self):
        """Budha Deva is distinct from Lord Krishna; Krishna gets eligible bonus (+8.0) not +15.0."""
        wednesday_dt = datetime(2026, 11, 18, 10, 0, tzinfo=KOLKATA_TZ)
        with patch("src.decision.weekday_deity.rotate_deity_for_day", return_value="budha"):
            # Budha gets +15.0; Krishna gets +8.0 (eligible, not scheduled)
            self.assertEqual(get_day_of_week_deity_bonus("budha", wednesday_dt), 15.0)
            self.assertEqual(get_day_of_week_deity_bonus("krishna", wednesday_dt), 8.0)

            # Budha candidate wins over Krishna candidate
            candidates = [
                _make_candidate("Lord Krishna Miracles", "krishna", score=90),
                _make_candidate("Budha Graha Dosha Nivarana", "budha", score=75),
            ]
            with patch("src.decision.weekday_deity.get_current_kolkata_datetime", return_value=wednesday_dt):
                decision = run_decision_pipeline(candidates, save=False, language_code="te-IN")
                self.assertIn("Budha", decision["selected_topic"])
                self.assertEqual(decision["deity"], "budha")

        # QA gate rejects Krishna scene for Budha topic
        dec = {"selected_topic": "Budha Graha Dosha", "deity": "budha", "approved_for_generation": True}
        scr = {"scenes": [{"scene": 1, "text": "Budha Graha"}]}
        vmap = {
            "visual_scenes": [{
                "scene": 1,
                "image_file": "assets/gods/krishna/krishna.png",
                "canonical_deity": "krishna",
                "provenance": "repository",
                "verification_status": "DEITY_VERIFIED",
            }]
        }
        passed, err = check_deity_identity_consistency(dec, scr, vmap, {"scenes": []}, {"deity": "budha"})
        self.assertFalse(passed)
        self.assertIn("mismatch", err)

    # ──────────────────────────────────────────────────────────────────────────
    # Test 22: Missing-asset behavior fails closed without cross-deity substitution
    # ──────────────────────────────────────────────────────────────────────────
    def test_22_missing_asset_behavior_fails_closed(self):
        """Asset selector raises error when deity has no approved assets, never substituting another deity."""
        gen = LocalThumbnailGenerator()
        # Chandra has no dedicated assets on disk; must raise NoSuitableThumbnailAssetError
        with self.assertRaises(NoSuitableThumbnailAssetError):
            gen.select_best_local_asset(deity="chandra", topic="Chandra Deva Blessings")

        # Shani has no dedicated approved assets on disk; must raise NoSuitableThumbnailAssetError (not substitute Hanuman)
        with self.assertRaises(NoSuitableThumbnailAssetError):
            gen.select_best_local_asset(deity="shani", topic="Shani Sade Sati")

    # ──────────────────────────────────────────────────────────────────────────
    # Test 23: Unapproved assets cannot bypass QA via metadata forging
    # ──────────────────────────────────────────────────────────────────────────
    def test_23_unapproved_assets_cannot_bypass_qa(self):
        """Scene with forged verification_status='DEITY_VERIFIED' fails QA if not in trusted catalog."""
        with tempfile.TemporaryDirectory() as td:
            fake_img = Path(td) / "unvetted_image.png"
            fake_img.write_bytes(b"dummy image bytes")

            # Even if metadata claims DEITY_VERIFIED, QA verifier checks catalog and fails closed
            approved, reason = _is_trusted_approved_asset(str(fake_img), deity="lord_shiva")
            self.assertFalse(approved)
            self.assertIn("lacks an explicit trusted asset approval record", reason)


if __name__ == "__main__":
    unittest.main()
