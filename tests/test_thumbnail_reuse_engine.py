# tests/test_thumbnail_reuse_engine.py
# Unit tests for Phase 2H / Phase 4 — Zero-Cost Thumbnail Asset Reuse Engine

import os
import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from PIL import Image, ImageDraw

sys.path.insert(0, os.getcwd())

from src.thumbnail.asset_index import (
    DeityAssetIndex,
    ThumbnailAssetRecord,
    resolve_deity_and_avatar,
    CANONICAL_DEITIES,
)
from src.thumbnail.frame_extractor import (
    compute_frame_sharpness,
    is_frame_suitable,
    extract_candidate_frames,
)
from src.thumbnail.asset_selector import (
    ThumbnailAssetSelector,
    NoSuitableThumbnailAssetError,
    SelectedThumbnailAsset,
)
from src.thumbnail.composer import (
    prepare_background_canvas,
    compose_reused_thumbnail,
)
from src.thumbnail.reuse_engine import ThumbnailReuseEngine
from src.thumbnail.analyzer import analyze_thumbnail_file


class TestThumbnailAssetIndex(unittest.TestCase):
    """Tests for deity asset indexing, alias resolution, corrupt rejection, and approval filtering."""

    def test_alias_and_avatar_resolution(self):
        # Varaha
        d, av = resolve_deity_and_avatar("The Secret of Lord Varaha Avatar Rescuing Earth")
        self.assertEqual(d, "lord_vishnu")
        self.assertEqual(av, "varaha")

        # Telugu Varaha
        d, av = resolve_deity_and_avatar("వరాహ అవతార రహస్యం: మహావిష్ణువు భూదేవిని ఎందుకు రక్షించారు?")
        self.assertEqual(d, "lord_vishnu")
        self.assertEqual(av, "varaha")

        # Kurma
        d, av = resolve_deity_and_avatar("Lord Kurma Avatar churning the ocean")
        self.assertEqual(d, "lord_vishnu")
        self.assertEqual(av, "kurma")

        # Narasimha
        d, av = resolve_deity_and_avatar("Lord Narasimha emerging from pillar")
        self.assertEqual(d, "narasimha")
        self.assertEqual(av, "narasimha")

        # Shiva
        d, av = resolve_deity_and_avatar("Lord Shiva Kailash Mahadev")
        self.assertEqual(d, "lord_shiva")
        self.assertIsNone(av)

        # Hanuman
        d, av = resolve_deity_and_avatar("Lord Hanuman carrying Sanjeevani Dronagiri")
        self.assertEqual(d, "hanuman")
        self.assertEqual(av, "hanuman")

    def test_corrupt_image_rejection(self):
        with tempfile.TemporaryDirectory() as td:
            bad_img = Path(td) / "corrupt.png"
            bad_img.write_bytes(b"NOT_A_REAL_PNG_DATA_XYZ")

            index = DeityAssetIndex()
            record = index._inspect_file(
                bad_img,
                default_source="test",
                default_approval="APPROVED"
            )
            self.assertIsNotNone(record)
            self.assertEqual(record.integrity_status, "CORRUPT")
            self.assertEqual(record.approval_status, "REJECTED")
            self.assertEqual(record.quality_score, 0.0)

    def test_approved_asset_filtering_and_no_cross_avatar(self):
        index = DeityAssetIndex()
        # Find approved assets for kurma
        kurma_assets = index.find_approved_assets(deity="lord_vishnu", avatar="kurma")
        self.assertTrue(len(kurma_assets) >= 1)
        for a in kurma_assets:
            self.assertEqual(a.avatar, "kurma")
            self.assertEqual(a.approval_status, "APPROVED")

        # Searching for Varaha when no approved Varaha exists must return EMPTY list (NO Kurma fallback)
        varaha_assets = index.find_approved_assets(deity="lord_vishnu", avatar="varaha")
        self.assertEqual(len(varaha_assets), 0, "Must NOT return Kurma or Vamana assets for Varaha!")


class TestFrameExtractor(unittest.TestCase):
    """Tests for video frame quality filtering and rejection of dark/blurry/flat frames."""

    def test_black_frame_rejection(self):
        with tempfile.TemporaryDirectory() as td:
            black_img = Path(td) / "black.png"
            Image.new("RGB", (640, 360), color=(5, 5, 5)).save(black_img)

            suitable, details = is_frame_suitable(black_img)
            self.assertFalse(suitable)
            self.assertIn("dark/black", details.get("rejection_reason", ""))

    def test_blank_solid_frame_rejection(self):
        with tempfile.TemporaryDirectory() as td:
            flat_img = Path(td) / "flat.png"
            Image.new("RGB", (640, 360), color=(120, 120, 120)).save(flat_img)

            suitable, details = is_frame_suitable(flat_img)
            self.assertFalse(suitable)
            self.assertIn("flat/blank", details.get("rejection_reason", ""))

    def test_suitable_rich_frame(self):
        with tempfile.TemporaryDirectory() as td:
            rich_img = Path(td) / "rich.png"
            im = Image.new("RGB", (640, 360), color=(40, 60, 180))
            draw = ImageDraw.Draw(im)
            draw.rectangle([100, 50, 400, 300], fill=(255, 215, 0), outline=(255, 255, 255), width=4)
            draw.text((150, 100), "SHARP TEST ARTWORK", fill=(0, 0, 0))
            im.save(rich_img)

            suitable, details = is_frame_suitable(rich_img, min_sharpness_variance=20.0)
            self.assertTrue(suitable, f"Should pass suitable test: {details}")


class TestAssetSelectorPriority(unittest.TestCase):
    """Tests the strict 4-priority selection order and anti-cross-deity enforcement."""

    def setUp(self):
        self.selector = ThumbnailAssetSelector()

    def test_priority_1_selected_when_approved_exists(self):
        # For kurma, approved landscape artwork exists in repository
        selected = self.selector.select_thumbnail_asset(
            topic="Kurma Avatar churning ocean",
            deity_hint="lord_vishnu",
            avatar_hint="kurma",
        )
        self.assertEqual(selected.priority_level, 1)
        self.assertEqual(selected.priority_name, "APPROVED_LOCAL_ARTWORK")
        self.assertEqual(selected.avatar, "kurma")
        self.assertIn("kurma", selected.asset_path.lower())

    def test_priority_failure_when_no_approved_asset_and_fallback_disabled(self):
        # Varaha has no approved asset in repository
        with self.assertRaises(NoSuitableThumbnailAssetError) as ctx:
            self.selector.select_thumbnail_asset(
                topic="వరాహ అవతార రహస్యం",
                deity_hint="lord_vishnu",
                avatar_hint="varaha",
                allow_pollinations_fallback=False,  # strictly local
            )
        self.assertIn("varaha", str(ctx.exception).lower())
        self.assertIn("Refusing to substitute unrelated deity artwork", str(ctx.exception))

    def test_pollinations_fallback_quota_failure_handling(self):
        # When Pollinations throws PollinationsError (e.g. 402/429 quota exhaustion), selector fails closed cleanly
        with patch.object(self.selector, "_attempt_pollinations_fallback", return_value=None):
            with self.assertRaises(NoSuitableThumbnailAssetError) as ctx:
                self.selector.select_thumbnail_asset(
                    topic="Varaha Avatar",
                    deity_hint="lord_vishnu",
                    avatar_hint="varaha",
                    allow_pollinations_fallback=True,
                )
            self.assertIn("Pollinations free endpoint unavailable", str(ctx.exception))


class TestThumbnailComposer(unittest.TestCase):
    """Tests aspect ratio adaptation, 1280x720 canvas, Telugu typography, and safe margins."""

    def test_landscape_composition(self):
        with tempfile.TemporaryDirectory() as td:
            bg_path = Path(td) / "bg_landscape.png"
            out_path = Path(td) / "thumb_landscape.png"

            # Create 1376x768 landscape image
            im = Image.new("RGB", (1376, 768), color=(15, 25, 45))
            draw = ImageDraw.Draw(im)
            draw.ellipse([600, 200, 1100, 700], fill=(255, 215, 0))
            im.save(bg_path)

            compose_reused_thumbnail(
                background_path=bg_path,
                title="నరసింహ స్వామి అవతారం",
                subtitle="మహావిష్ణువు భక్త రక్షణ",
                output_path=out_path,
                language_code="te-IN",
            )

            self.assertTrue(out_path.exists())
            with Image.open(out_path) as res:
                self.assertEqual(res.size, (1280, 720))
                self.assertEqual(res.format, "PNG")

            analysis = analyze_thumbnail_file(out_path, expected_title="నరసింహ స్వామి అవతారం")
            self.assertTrue(analysis["valid"], f"Errors: {analysis.get('errors')}")

    def test_vertical_portrait_adaptation(self):
        with tempfile.TemporaryDirectory() as td:
            bg_path = Path(td) / "bg_portrait.png"
            out_path = Path(td) / "thumb_portrait.png"

            # Create 720x1280 portrait image
            im = Image.new("RGB", (720, 1280), color=(40, 15, 20))
            draw = ImageDraw.Draw(im)
            draw.rectangle([100, 200, 620, 1000], fill=(220, 180, 30))
            im.save(bg_path)

            compose_reused_thumbnail(
                background_path=bg_path,
                title="హనుమాన్ సంజీవని కథ",
                subtitle="దైవ దర్శనం",
                output_path=out_path,
                language_code="te-IN",
            )

            self.assertTrue(out_path.exists())
            with Image.open(out_path) as res:
                self.assertEqual(res.size, (1280, 720))

            analysis = analyze_thumbnail_file(out_path, expected_title="హనుమాన్ సంజీవని కథ")
            self.assertTrue(analysis["valid"], f"Errors: {analysis.get('errors')}")


class TestThumbnailReuseEngine(unittest.TestCase):
    """End-to-end tests for the complete ₹0 Thumbnail Reuse Engine."""

    def test_successful_approved_artwork_reuse(self):
        with tempfile.TemporaryDirectory() as td:
            out_img = Path(td) / "thumb.png"
            out_meta = Path(td) / "meta.json"

            engine = ThumbnailReuseEngine()
            meta = engine.generate(
                topic="Lord Narasimha emerging from pillar to protect Prahlada",
                script_title="నరసింహ అవతార రహస్యం",
                subtitle="ప్రహ్లాదుని భక్తి రక్షణ",
                deity="narasimha",
                avatar="narasimha",
                output_image_path=out_img,
                output_meta_path=out_meta,
            )

            self.assertEqual(meta["status"], "SUCCESS")
            self.assertEqual(meta["api_spending_inr"], 0.0)
            self.assertEqual(meta["selected_asset"]["priority_level"], 1)
            self.assertEqual(meta["selected_asset"]["priority_name"], "APPROVED_LOCAL_ARTWORK")
            self.assertTrue(out_img.exists())
            self.assertTrue(out_meta.exists())

    def test_varaha_fails_closed_when_no_approved_asset(self):
        # Strict requirement: If no suitable Varaha asset exists, report missing without substituting unrelated deity
        engine = ThumbnailReuseEngine()
        with self.assertRaises(NoSuitableThumbnailAssetError) as ctx:
            engine.generate(
                topic="వరాహ అవతార రహస్యం: మహావిష్ణువు భూదేవిని ఎందుకు రక్షించారు?",
                script_title="వరాహ అవతార రహస్యం",
                subtitle="మహావిష్ణువు భూదేవిని ఎందుకు రక్షించారు?",
                deity="lord_vishnu",
                avatar="varaha",
                allow_pollinations_fallback=False,  # Strict ₹0 local requirement
            )
        self.assertIn("varaha", str(ctx.exception).lower())
        self.assertIn("Refusing to substitute unrelated deity artwork", str(ctx.exception))


class TestOrchestratorThumbnailIntegration(unittest.TestCase):
    """Verifies that PipelineRunner correctly selects 'reuse' provider in render-only mode."""

    def test_orchestrator_selects_reuse_in_render_only_mode(self):
        from unittest.mock import patch, MagicMock
        from src.pipeline.orchestrator import PipelineRunner

        with tempfile.TemporaryDirectory() as td:
            dec_file = Path(td) / "decision_test.json"
            dec_file.write_text(json.dumps({
                "selected_topic": "Test Topic",
                "deity": "lord_shiva",
                "data_source": "manual",
                "score": 100,
                "confidence": "HIGH",
                "approved_for_generation": True,
            }), encoding="utf-8")

            script_file = Path(td) / "script_test.json"
            script_file.write_text(json.dumps({"title": "శివుని కథ"}), encoding="utf-8")

            vis_file = Path(td) / "visual_map.json"
            vis_file.write_text("{}", encoding="utf-8")

            vid_file = Path(td) / "video.mp4"
            vid_file.write_text("fake video", encoding="utf-8")

            # Initialize orchestrator runner in render_only mode
            orch = PipelineRunner(
                dry_run=False,
                render_only=True,
                content_type="short",
                format="narrated",
                language_code="te-IN",
            )
            orch.state.set_output("decision_output", dec_file)
            orch.state.set_output("script_output", script_file)
            orch.state.set_output("visual_map_output", vis_file)
            orch.state.set_output("video_output", vid_file)

            executed_cmds = []

            def fake_execute(cmd, stage):
                executed_cmds.append((cmd, stage))

            with patch.object(orch, "_execute_cmd", side_effect=fake_execute), \
                 patch.object(orch, "_find_latest_file", return_value=Path(td) / "thumb.png"):
                orch.run_thumbnail()

            self.assertEqual(len(executed_cmds), 1)
            cmd, stage = executed_cmds[0]
            self.assertEqual(stage, "THUMBNAIL")
            self.assertIn("--provider", cmd)
            p_idx = cmd.index("--provider")
            self.assertEqual(cmd[p_idx + 1], "reuse")
            self.assertIn("--visual-map", cmd)
            self.assertIn("--video", cmd)

    def test_orchestrator_selects_mock_in_dry_run_mode(self):
        from unittest.mock import patch
        from src.pipeline.orchestrator import PipelineRunner

        with tempfile.TemporaryDirectory() as td:
            dec_file = Path(td) / "decision_test.json"
            dec_file.write_text(json.dumps({"selected_topic": "Test"}), encoding="utf-8")

            orch = PipelineRunner(dry_run=True, render_only=False)
            orch.state.set_output("decision_output", dec_file)

            executed_cmds = []
            with patch.object(orch, "_execute_cmd", side_effect=lambda c, s: executed_cmds.append(c)), \
                 patch.object(orch, "_find_latest_file", return_value=Path(td) / "thumb.png"):
                orch.run_thumbnail()

            cmd = executed_cmds[0]
            p_idx = cmd.index("--provider")
            self.assertEqual(cmd[p_idx + 1], "mock")

    def test_orchestrator_selects_pollinations_in_default_mode(self):
        from unittest.mock import patch
        from src.pipeline.orchestrator import PipelineRunner

        with tempfile.TemporaryDirectory() as td:
            dec_file = Path(td) / "decision_test.json"
            dec_file.write_text(json.dumps({"selected_topic": "Test"}), encoding="utf-8")

            orch = PipelineRunner(dry_run=False, render_only=False)
            orch.state.set_output("decision_output", dec_file)

            executed_cmds = []
            with patch.object(orch, "_execute_cmd", side_effect=lambda c, s: executed_cmds.append(c)), \
                 patch.object(orch, "_find_latest_file", return_value=Path(td) / "thumb.png"):
                orch.run_thumbnail()

            cmd = executed_cmds[0]
            p_idx = cmd.index("--provider")
            self.assertEqual(cmd[p_idx + 1], "pollinations")


if __name__ == "__main__":
    unittest.main()
