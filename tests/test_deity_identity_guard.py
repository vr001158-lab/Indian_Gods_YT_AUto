# tests/test_deity_identity_guard.py
# Regression tests for Deity Identity Consistency Across Video and Thumbnail Pipelines

import json
import tempfile
import unittest
from pathlib import Path
from PIL import Image

from src.assets.exceptions import NoMatchingDeityAssetError, DeityIdentityMismatchError
from src.assets.selector import select_scene_assets, build_deity_visual_timeline
from src.thumbnail.asset_selector import ThumbnailAssetSelector, NoSuitableThumbnailAssetError
from src.thumbnail.frame_extractor import extract_candidate_frames
from src.qa.checks import check_deity_identity_consistency


class TestDeityIdentityConsistency(unittest.TestCase):
    """Verifies fail-closed deity and avatar identity consistency guards."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.temp_dir = Path(self.td.name)

    def tearDown(self):
        self.td.cleanup()

    def test_01_varaha_topic_rejects_kurma_image(self):
        """1. Varaha topic with Kurma image -> strictly rejected."""
        manifest = {
            "deities": {
                "lord_vishnu": {
                    "images": [
                        {
                            "path": "assets/gods/lord_vishnu/kurma_avatar_mandara_mountain_samudra_manthan.png",
                            "avatar": "kurma",
                            "verification_status": "verified_visual",
                            "type": "image",
                        }
                    ],
                    "videos": [],
                }
            }
        }
        scene_scripts = [{"scene": 1, "visual_reference": "Varaha avatar diving into cosmic ocean"}]

        with self.assertRaises(NoMatchingDeityAssetError) as ctx:
            select_scene_assets(
                deity_key="lord_vishnu",
                scene_scripts=scene_scripts,
                manifest=manifest,
                avatar="varaha",
            )
        self.assertIn("varaha", str(ctx.exception).lower())
        self.assertIn("Refusing to substitute unrelated deity or avatar artwork", str(ctx.exception))

    def test_02_varaha_topic_rejects_narasimha_image(self):
        """2. Varaha topic with Narasimha image -> strictly rejected."""
        manifest = {
            "deities": {
                "lord_vishnu": {
                    "images": [
                        {
                            "path": "assets/gods/lord_vishnu/narasimha_emerging_from_pillar.png",
                            "avatar": "narasimha",
                            "verification_status": "verified_visual",
                            "type": "image",
                        }
                    ],
                    "videos": [],
                }
            }
        }
        scene_scripts = [{"scene": 1, "visual_reference": "Varaha emerging with tusks"}]

        with self.assertRaises(NoMatchingDeityAssetError):
            select_scene_assets(
                deity_key="lord_vishnu",
                scene_scripts=scene_scripts,
                manifest=manifest,
                avatar="varaha",
            )

    def test_03_varaha_topic_rejects_generic_unverified_vishnu_image(self):
        """3. Varaha topic with generic Vishnu image -> rejected unless explicitly verified for requested scene."""
        manifest = {
            "deities": {
                "lord_vishnu": {
                    "images": [
                        {
                            "path": "assets/gods/lord_vishnu/ChatGPT Image May 29.png",
                            "avatar": "lord_vishnu",
                            "verification_status": "unverified",
                            "type": "image",
                        }
                    ],
                    "videos": [],
                }
            }
        }
        scene_scripts = [{"scene": 1, "visual_reference": "Varaha lifting Bhudevi"}]

        with self.assertRaises(NoMatchingDeityAssetError):
            select_scene_assets(
                deity_key="lord_vishnu",
                scene_scripts=scene_scripts,
                manifest=manifest,
                avatar="varaha",
            )

    def test_04_varaha_topic_with_verified_varaha_artwork_accepted(self):
        """4. Varaha topic with verified Varaha artwork -> accepted with DEITY_VERIFIED status."""
        varaha_img = self.temp_dir / "varaha_avatar_verified.png"
        im = Image.new("RGB", (720, 1280), color=(40, 20, 25))
        im.save(varaha_img)

        manifest = {
            "deities": {
                "lord_vishnu": {
                    "images": [
                        {
                            "path": str(varaha_img).replace("\\", "/"),
                            "avatar": "varaha",
                            "verification_status": "verified_visual",
                            "type": "image",
                            "asset_id": "varaha_scene_1",
                        }
                    ],
                    "videos": [],
                }
            }
        }
        scene_scripts = [{"scene": 1, "visual_reference": "Varaha lifting Bhudevi"}]

        plan = select_scene_assets(
            deity_key="lord_vishnu",
            scene_scripts=scene_scripts,
            manifest=manifest,
            avatar="varaha",
        )
        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["avatar"], "varaha")
        self.assertEqual(plan[0]["verification_status"], "DEITY_VERIFIED")

    def test_05_unverified_or_mismatched_video_frame_rejected_for_thumbnail(self):
        """5. Unverified or mismatched video frame -> rejected for thumbnail reuse."""
        fake_video = self.temp_dir / "fake_video.mp4"
        fake_video.write_bytes(b"dummy mp4")

        # Visual map with Scene 1 depicting Kurma
        vmap_path = self.temp_dir / "visual_map.json"
        vmap_path.write_text(json.dumps({
            "visual_scenes": [
                {
                    "scene": 1,
                    "duration_seconds": 15.0,
                    "image_file": "assets/gods/lord_vishnu/kurma_avatar_mandara_mountain_samudra_manthan.png",
                    "avatar": "kurma",
                    "canonical_deity": "lord_vishnu",
                    "verification_status": "DEITY_VERIFIED",
                }
            ]
        }), encoding="utf-8")

        selector = ThumbnailAssetSelector()
        with self.assertRaises(NoSuitableThumbnailAssetError) as ctx:
            selector.select_thumbnail_asset(
                topic="వరాహ అవతార రహస్యం: మహావిష్ణువు భూదేవిని ఎందుకు రక్షించారు?",
                deity_hint="lord_vishnu",
                avatar_hint="varaha",
                visual_map_path=vmap_path,
                video_path=fake_video,
                allow_pollinations_fallback=False,
            )
        self.assertIn("varaha", str(ctx.exception).lower())

    def test_06_mismatched_thumbnail_fails_final_qa(self):
        """6. Mismatched thumbnail -> final QA failure."""
        decision = {
            "selected_topic": "The Secret of Varaha Avatar Rescuing Mother Earth",
            "deity": "lord_vishnu",
        }
        script = {"title": "వరాహ అవతార రహస్యం"}
        visual_map = {
            "visual_scenes": [
                {
                    "scene": 1,
                    "image_file": "assets/gods/lord_vishnu/kurma_avatar_mandara_mountain_samudra_manthan.png",
                    "canonical_deity": "lord_vishnu",
                    "avatar": "kurma",
                    "verification_status": "DEITY_VERIFIED",
                    "provenance": "Divine Dharshanam Daily generation workflow; visually verified",
                }
            ]
        }
        video_map = {}
        # Thumbnail depicting Kurma on a Varaha video
        thumbnail_meta = {
            "selected_asset": {
                "source_path": "data/thumbnails/frames/extracted/frame_00_2s.png",
                "avatar": "kurma",
                "deity": "lord_vishnu",
                "verification_status": "QUALITY_VERIFIED",
            }
        }

        ok, detail = check_deity_identity_consistency(
            decision=decision,
            script=script,
            visual_map=visual_map,
            video_map=video_map,
            thumbnail_meta=thumbnail_meta,
        )
        self.assertFalse(ok)
        self.assertIn("mismatch", detail.lower())

    def test_07_missing_matching_assets_fails_closed(self):
        """7. Missing matching assets -> fail closed without generating misleading output."""
        selector = ThumbnailAssetSelector()
        with self.assertRaises(NoSuitableThumbnailAssetError) as ctx:
            selector.select_thumbnail_asset(
                topic="వరాహ అవతార రహస్యం",
                deity_hint="lord_vishnu",
                avatar_hint="varaha",
                allow_pollinations_fallback=False,
            )
        self.assertIn("varaha", str(ctx.exception).lower())
        self.assertIn("Refusing to substitute unrelated deity artwork", str(ctx.exception))

    def test_08_deity_unverified_scene_fails_final_qa(self):
        """8. DEITY_UNVERIFIED scene -> final QA failure."""
        decision = {
            "selected_topic": "Kurma Avatar and the Churning of the Ocean",
            "deity": "lord_vishnu",
        }
        script = {"title": "కూర్మ అవతార వైభవం"}
        visual_map = {
            "visual_scenes": [
                {
                    "scene": 1,
                    "image_file": "assets/gods_landscape_long_video/lord_vishnu/kurma_avatar_mandara_mountain_samudra_manthan_landscape.png",
                    "canonical_deity": "lord_vishnu",
                    "avatar": "kurma",
                    "verification_status": "DEITY_UNVERIFIED",
                    "provenance": "Divine Dharshanam Daily generation workflow; visually verified",
                }
            ]
        }
        ok, detail = check_deity_identity_consistency(
            decision=decision,
            script=script,
            visual_map=visual_map,
            video_map={},
            thumbnail_meta=None,
        )
        self.assertFalse(ok)
        self.assertIn("unverified", detail.lower())

    def test_09_missing_identity_metadata_fails_final_qa(self):
        """9. Missing identity metadata (canonical_deity or verification_status) -> final QA failure."""
        decision = {
            "selected_topic": "Kurma Avatar Mandara Mountain",
            "deity": "lord_vishnu",
        }
        script = {"title": "కూర్మ అవతార కథ"}

        # 9a. Missing canonical_deity
        vmap_missing_deity = {
            "visual_scenes": [
                {
                    "scene": 1,
                    "image_file": "assets/gods_landscape_long_video/lord_vishnu/kurma_avatar_mandara_mountain_samudra_manthan_landscape.png",
                    "avatar": "kurma",
                    "verification_status": "DEITY_VERIFIED",
                    "provenance": "Divine Dharshanam Daily generation workflow; visually verified",
                }
            ]
        }
        ok, detail = check_deity_identity_consistency(decision, script, vmap_missing_deity, {}, None)
        self.assertFalse(ok)
        self.assertIn("missing canonical_deity", detail.lower())

        # 9b. Missing verification_status
        vmap_missing_ver = {
            "visual_scenes": [
                {
                    "scene": 1,
                    "image_file": "assets/gods_landscape_long_video/lord_vishnu/kurma_avatar_mandara_mountain_samudra_manthan_landscape.png",
                    "canonical_deity": "lord_vishnu",
                    "avatar": "kurma",
                    "provenance": "Divine Dharshanam Daily generation workflow; visually verified",
                }
            ]
        }
        ok, detail = check_deity_identity_consistency(decision, script, vmap_missing_ver, {}, None)
        self.assertFalse(ok)
        self.assertIn("missing verification_status", detail.lower())

    def test_10_missing_avatar_for_avatar_topic_fails_final_qa(self):
        """10. Missing avatar for avatar-specific topic -> final QA failure."""
        decision = {
            "selected_topic": "The Story of Varaha Avatar Rescuing Mother Earth",
            "deity": "lord_vishnu",
        }
        script = {"title": "వరాహ అవతార రహస్యం"}
        visual_map = {
            "visual_scenes": [
                {
                    "scene": 1,
                    "image_file": "assets/gods/lord_vishnu/generic_vishnu_art.png",
                    "canonical_deity": "lord_vishnu",
                    "avatar": None,  # Missing avatar on an avatar-specific topic!
                    "verification_status": "DEITY_VERIFIED",
                    "provenance": "Divine Dharshanam Daily generation workflow; visually verified",
                }
            ]
        }
        ok, detail = check_deity_identity_consistency(
            decision=decision,
            script=script,
            visual_map=visual_map,
            video_map={},
            thumbnail_meta=None,
        )
        self.assertFalse(ok)
        self.assertIn("missing required avatar", detail.lower())

    def test_11_missing_provenance_fails_final_qa(self):
        """11. Missing or invalid provenance -> final QA failure."""
        decision = {
            "selected_topic": "Kurma Avatar Supporting Mandara Mountain",
            "deity": "lord_vishnu",
        }
        script = {"title": "కూర్మ అవతారం"}
        visual_map = {
            "visual_scenes": [
                {
                    "scene": 1,
                    "image_file": "assets/gods_landscape_long_video/lord_vishnu/kurma_avatar_mandara_mountain_samudra_manthan_landscape.png",
                    "canonical_deity": "lord_vishnu",
                    "avatar": "kurma",
                    "verification_status": "DEITY_VERIFIED",
                    "provenance": "",  # Empty provenance!
                }
            ]
        }
        ok, detail = check_deity_identity_consistency(
            decision=decision,
            script=script,
            visual_map=visual_map,
            video_map={},
            thumbnail_meta=None,
        )
        self.assertFalse(ok)
        self.assertIn("missing or invalid asset provenance", detail.lower())

    def test_12_matching_but_unapproved_image_fails_final_qa(self):
        """12. Matching but unapproved image -> final QA failure (metadata cannot bypass the guard)."""
        decision = {
            "selected_topic": "The Mystery of Lord Vishnu's Cosmic Sleep",
            "deity": "lord_vishnu",
        }
        script = {"title": "విష్ణువు యోగ నిద్ర"}
        # Unapproved file in assets/gods/lord_vishnu with forged verification_status
        visual_map = {
            "visual_scenes": [
                {
                    "scene": 1,
                    "image_file": "assets/gods/lord_vishnu/ChatGPT Image May 29.png",
                    "canonical_deity": "lord_vishnu",
                    "avatar": None,
                    "verification_status": "verified_visual",  # Fraudulent verification attempt!
                    "provenance": "Divine Dharshanam Daily generation workflow; visually verified",
                }
            ]
        }
        ok, detail = check_deity_identity_consistency(
            decision=decision,
            script=script,
            visual_map=visual_map,
            video_map={},
            thumbnail_meta=None,
            allow_mock=False,
        )
        self.assertFalse(ok)
        self.assertTrue(
            "unapproved status" in detail.lower()
            or "lacks an explicit trusted approval record" in detail.lower()
            or "failed approval verification" in detail.lower()
        )

    def test_13_explicitly_approved_matching_asset_passes_final_qa(self):
        """13. Explicitly approved matching asset -> final QA success."""
        decision = {
            "selected_topic": "Kurma Avatar Mandara Mountain Samudra Manthan",
            "deity": "lord_vishnu",
        }
        script = {"title": "కూర్మ అవతార రహస్యం"}
        visual_map = {
            "visual_scenes": [
                {
                    "scene": 1,
                    "image_file": "assets/gods_landscape_long_video/lord_vishnu/kurma_avatar_mandara_mountain_samudra_manthan_landscape.png",
                    "canonical_deity": "lord_vishnu",
                    "avatar": "kurma",
                    "verification_status": "DEITY_VERIFIED",
                    "provenance": "Divine Dharshanam Daily generation workflow; visually verified",
                }
            ]
        }
        thumbnail_meta = {
            "selected_asset": {
                "source_path": "assets/gods_landscape_long_video/lord_vishnu/kurma_avatar_mandara_mountain_samudra_manthan_landscape.png",
                "avatar": "kurma",
                "canonical_deity": "lord_vishnu",
                "verification_status": "DEITY_VERIFIED",
            },
            "topic": "కూర్మ అవతార రహస్యం",
        }
        ok, detail = check_deity_identity_consistency(
            decision=decision,
            script=script,
            visual_map=visual_map,
            video_map={},
            thumbnail_meta=thumbnail_meta,
            allow_mock=False,
        )
        self.assertTrue(ok, f"Expected success but got: {detail}")
        self.assertEqual(detail, "OK")

    def test_14_mismatched_thumbnail_with_matching_video_fails_final_qa(self):
        """14. Mismatched thumbnail with matching video -> final QA failure."""
        decision = {
            "selected_topic": "Kurma Avatar Samudra Manthan",
            "deity": "lord_vishnu",
        }
        script = {"title": "కూర్మ అవతారం"}
        # Video scenes have verified Kurma asset
        visual_map = {
            "visual_scenes": [
                {
                    "scene": 1,
                    "image_file": "assets/gods_landscape_long_video/lord_vishnu/kurma_avatar_mandara_mountain_samudra_manthan_landscape.png",
                    "canonical_deity": "lord_vishnu",
                    "avatar": "kurma",
                    "verification_status": "DEITY_VERIFIED",
                    "provenance": "Divine Dharshanam Daily generation workflow; visually verified",
                }
            ]
        }
        # Thumbnail depicts Narasimha
        thumbnail_meta = {
            "selected_asset": {
                "source_path": "assets/gods_landscape_long_video/narasimha/narasimha_emerging_from_pillar_prahlada_landscape.png",
                "avatar": "narasimha",
                "canonical_deity": "narasimha",
                "verification_status": "DEITY_VERIFIED",
            },
            "topic": "కూర్మ అవతారం",
        }
        ok, detail = check_deity_identity_consistency(
            decision=decision,
            script=script,
            visual_map=visual_map,
            video_map={},
            thumbnail_meta=thumbnail_meta,
            allow_mock=False,
        )
        self.assertFalse(ok)
        self.assertIn("mismatch", detail.lower())

    def test_15_curated_repository_deity_asset_passes_final_qa(self):
        """15. Curated repository deity asset -> receives DEITY_VERIFIED and passes final QA."""
        # Find a genuine curated asset from assets/gods/ganesha
        ganesha_dir = Path("assets/gods/ganesha")
        cands = [p for p in ganesha_dir.glob("*.jpg") if "chatgpt" not in p.name.lower()]
        self.assertTrue(len(cands) > 0, "Expected at least one curated Ganesha asset in repository")
        selected_cand = cands[0]

        decision = {
            "selected_topic": "The Legend of Chandra Curse Why Ganesha Punished the Moon",
            "deity": "ganesha",
        }
        script = {"title": "వినాయకుడి ఏకదంతం వెనుక ఉన్న అసలు రహస్యం"}
        visual_map = {
            "visual_scenes": [
                {
                    "scene": 1,
                    "image_file": str(selected_cand).replace("\\", "/"),
                    "source_path": str(selected_cand).replace("\\", "/"),
                    "canonical_deity": "ganesha",
                    "avatar": "ganesha",
                    "verification_status": "DEITY_VERIFIED",
                    "provenance": "Repository collection; curated deity visual asset",
                }
            ]
        }
        thumbnail_meta = {
            "selected_asset": {
                "source_path": str(selected_cand).replace("\\", "/"),
                "avatar": "ganesha",
                "canonical_deity": "ganesha",
                "verification_status": "DEITY_VERIFIED",
            },
            "topic": "వినాయకుడి ఏకదంతం వెనుక ఉన్న అసలు రహస్యం",
        }

        # 15a: Correct deity -> passes final QA even with allow_mock=False
        ok, detail = check_deity_identity_consistency(
            decision=decision,
            script=script,
            visual_map=visual_map,
            video_map={},
            thumbnail_meta=thumbnail_meta,
            allow_mock=False,
        )
        self.assertTrue(ok, f"Expected QA pass for curated Ganesha asset, got: {detail}")
        self.assertEqual(detail, "OK")

        # 15b: Cross-deity mismatch (using Ganesha asset on Lord Shiva topic) -> rejected
        shiva_decision = {
            "selected_topic": "The Story of Markandeya How Shiva Defeated Death",
            "deity": "lord_shiva",
        }
        shiva_script = {"title": "శివుని దివ్య లీల"}
        ok_mismatch, detail_mismatch = check_deity_identity_consistency(
            decision=shiva_decision,
            script=shiva_script,
            visual_map=visual_map,
            video_map={},
            thumbnail_meta=None,
            allow_mock=False,
        )
        self.assertFalse(ok_mismatch)
        self.assertIn("deity mismatch", detail_mismatch.lower())

    def test_16_ganesha_scene_with_kurma_avatar_rejected(self):
        """16. Adversarial 1: Ganesha scene with Kurma avatar -> REJECT."""
        ganesha_dir = Path("assets/gods/ganesha")
        cands = [p for p in ganesha_dir.glob("*.jpg") if "chatgpt" not in p.name.lower()]
        img_path = str(cands[0]).replace("\\", "/") if cands else "assets/gods/ganesha/ganesha.jpg"

        decision = {"selected_topic": "Lord Ganesha Divine Wisdom", "deity": "ganesha"}
        script = {"title": "వినాయకుడి మహిమ"}
        visual_map = {
            "visual_scenes": [
                {
                    "scene": 1,
                    "image_file": img_path,
                    "canonical_deity": "ganesha",
                    "avatar": "kurma",  # Contradictory avatar on Ganesha!
                    "verification_status": "DEITY_VERIFIED",
                    "provenance": "Repository collection; curated deity asset",
                }
            ]
        }
        ok, detail = check_deity_identity_consistency(
            decision=decision,
            script=script,
            visual_map=visual_map,
            video_map={},
            thumbnail_meta=None,
            allow_mock=False,
        )
        self.assertFalse(ok)
        self.assertTrue("contradictory" in detail.lower() or "deity_mismatch" in detail.lower())

    def test_17_ganesha_scene_with_shiva_video_rejected(self):
        """17. Adversarial 2: Ganesha scene with Shiva video -> REJECT."""
        decision = {"selected_topic": "Lord Ganesha Divine Tales", "deity": "ganesha"}
        script = {"title": "గణపతి లీలలు"}
        visual_map = {
            "visual_scenes": [
                {
                    "scene": 1,
                    "video_file": "assets/gods_processed/lord_shiva/horizontal/shiva_dance.mp4",
                    "canonical_deity": "ganesha",
                    "avatar": "ganesha",
                    "verification_status": "DEITY_VERIFIED",
                    "provenance": "Repository collection; curated deity asset",
                }
            ]
        }
        ok, detail = check_deity_identity_consistency(
            decision=decision,
            script=script,
            visual_map=visual_map,
            video_map={},
            thumbnail_meta=None,
            allow_mock=False,
        )
        self.assertFalse(ok)
        self.assertIn("lord_shiva", detail.lower())
        self.assertIn("mismatch", detail.lower())

    def test_18_shiva_scene_with_ganesha_video_rejected(self):
        """18. Adversarial 3: Shiva scene with Ganesha video -> REJECT."""
        decision = {"selected_topic": "Lord Shiva Meditation on Mount Kailash", "deity": "lord_shiva"}
        script = {"title": "శివుని ధ్యానం"}
        visual_map = {
            "visual_scenes": [
                {
                    "scene": 1,
                    "video_file": "assets/gods_processed/ganesha/horizontal/ganesha_celebration.mp4",
                    "canonical_deity": "lord_shiva",
                    "avatar": "lord_shiva",
                    "verification_status": "DEITY_VERIFIED",
                    "provenance": "Repository collection; curated deity asset",
                }
            ]
        }
        ok, detail = check_deity_identity_consistency(
            decision=decision,
            script=script,
            visual_map=visual_map,
            video_map={},
            thumbnail_meta=None,
            allow_mock=False,
        )
        self.assertFalse(ok)
        self.assertIn("ganesha", detail.lower())
        self.assertIn("mismatch", detail.lower())

    def test_19_correct_deity_image_with_mismatched_video_rejected(self):
        """19. Adversarial 4: Correct deity image with mismatched video -> REJECT."""
        shiva_dir = Path("assets/gods/lord_shiva")
        cands = [p for p in shiva_dir.glob("*.jpg") if "chatgpt" not in p.name.lower()]
        shiva_img = str(cands[0]).replace("\\", "/") if cands else "assets/gods/lord_shiva/shiva.jpg"

        decision = {"selected_topic": "Secrets of Lord Shiva Neelkanth", "deity": "lord_shiva"}
        script = {"title": "శివుని హాలాహలం"}
        visual_map = {
            "visual_scenes": [
                {
                    "scene": 1,
                    "image_file": shiva_img,  # Correct Shiva image
                    "video_file": "assets/gods_processed/ganesha/horizontal/ganesha_procession.mp4",  # Mismatched Ganesha video
                    "canonical_deity": "lord_shiva",
                    "avatar": "lord_shiva",
                    "verification_status": "DEITY_VERIFIED",
                    "provenance": "Repository collection; curated deity asset",
                }
            ]
        }
        ok, detail = check_deity_identity_consistency(
            decision=decision,
            script=script,
            visual_map=visual_map,
            video_map={},
            thumbnail_meta=None,
            allow_mock=False,
        )
        self.assertFalse(ok)
        self.assertIn("ganesha", detail.lower())
        self.assertIn("mismatch", detail.lower())

    def test_20_correct_deity_and_matching_video_passes_with_catalog_evidence(self):
        """20. Adversarial 5: Correct deity and matching video -> PASS with valid catalog evidence."""
        decision = {"selected_topic": "Sri Rama Ayodhya Pattabhishekam", "deity": "ram"}
        script = {"title": "శ్రీరామ పట్టాభిషేకం"}
        ram_vid = "assets/gods_processed/ram/horizontal/1116118720173406492__img_tmp.mp4"
        visual_map = {
            "visual_scenes": [
                {
                    "scene": 1,
                    "video_file": ram_vid,
                    "canonical_deity": "ram",
                    "avatar": "ram",
                    "verification_status": "DEITY_VERIFIED",
                    "provenance": "Repository collection; curated deity asset",
                }
            ]
        }
        ok, detail = check_deity_identity_consistency(
            decision=decision,
            script=script,
            visual_map=visual_map,
            video_map={},
            thumbnail_meta=None,
            allow_mock=False,
        )
        self.assertTrue(ok, f"Expected PASS for valid indexed Ram video, got: {detail}")
        self.assertEqual(detail, "OK")

    def test_21_missing_video_identity_evidence_rejected(self):
        """21. Adversarial 6: Missing video identity evidence -> REJECT."""
        decision = {"selected_topic": "Lord Shiva Cosmic Tandava Dance", "deity": "lord_shiva"}
        script = {"title": "శివ తాండవం"}
        visual_map = {
            "visual_scenes": [
                {
                    "scene": 1,
                    "video_file": "data/videos/unindexed_unverified_clip.mp4",
                    "canonical_deity": "lord_shiva",
                    "avatar": "lord_shiva",
                    "verification_status": "DEITY_VERIFIED",
                    "provenance": "Repository collection; curated deity asset",
                }
            ]
        }
        ok, detail = check_deity_identity_consistency(
            decision=decision,
            script=script,
            visual_map=visual_map,
            video_map={},
            thumbnail_meta=None,
            allow_mock=False,
        )
        self.assertFalse(ok)
        self.assertTrue("failed approval verification" in detail.lower() or "lacks an explicit trusted" in detail.lower())

    def test_22_correct_indexed_deity_and_avatar_passes(self):
        """22. Adversarial 7: Correct indexed deity and avatar -> PASS."""
        decision = {"selected_topic": "Kurma Avatar Mandara Mountain Samudra Manthan", "deity": "lord_vishnu"}
        script = {"title": "కూర్మ అవతార కథ"}
        visual_map = {
            "visual_scenes": [
                {
                    "scene": 1,
                    "image_file": "assets/gods_landscape_long_video/lord_vishnu/kurma_avatar_mandara_mountain_samudra_manthan_landscape.png",
                    "canonical_deity": "lord_vishnu",
                    "avatar": "kurma",
                    "verification_status": "DEITY_VERIFIED",
                    "provenance": "Divine Dharshanam Daily generation workflow; visually verified",
                }
            ]
        }
        ok, detail = check_deity_identity_consistency(
            decision=decision,
            script=script,
            visual_map=visual_map,
            video_map={},
            thumbnail_meta=None,
            allow_mock=False,
        )
        self.assertTrue(ok, f"Expected PASS for correctly indexed Kurma avatar, got: {detail}")
        self.assertEqual(detail, "OK")

    def test_23_incorrect_deity_asset_index_deity_rejected(self):
        """23. Adversarial 8: Incorrect DeityAssetIndex deity -> REJECT."""
        ganesha_dir = Path("assets/gods/ganesha")
        cands = [p for p in ganesha_dir.glob("*.jpg") if "chatgpt" not in p.name.lower()]
        ganesha_img = str(cands[0]).replace("\\", "/") if cands else "assets/gods/ganesha/ganesha.jpg"

        decision = {"selected_topic": "Secrets of Lord Shiva Neelkanth", "deity": "lord_shiva"}
        script = {"title": "శివుని హాలాహలం"}
        # Asset in index belongs to Ganesha, topic is Lord Shiva
        visual_map = {
            "visual_scenes": [
                {
                    "scene": 1,
                    "image_file": ganesha_img,
                    "canonical_deity": "lord_shiva",
                    "avatar": "lord_shiva",
                    "verification_status": "DEITY_VERIFIED",
                    "provenance": "Repository collection; curated deity asset",
                }
            ]
        }
        ok, detail = check_deity_identity_consistency(
            decision=decision,
            script=script,
            visual_map=visual_map,
            video_map={},
            thumbnail_meta=None,
            allow_mock=False,
        )
        self.assertFalse(ok)
        self.assertTrue("mismatch" in detail.lower() or "ganesha" in detail.lower())

    def test_24_unapproved_generated_image_rejected(self):
        """24. Adversarial 9: Unapproved generated image -> REJECT."""
        decision = {"selected_topic": "Lord Vishnu Cosmic Sleep", "deity": "lord_vishnu"}
        script = {"title": "మహావిష్ణువు యోగనిద్ర"}
        visual_map = {
            "visual_scenes": [
                {
                    "scene": 1,
                    "image_file": "assets/gods/lord_vishnu/ChatGPT Image May 29.png",  # Raw unapproved file
                    "canonical_deity": "lord_vishnu",
                    "avatar": "lord_vishnu",
                    "verification_status": "DEITY_VERIFIED",  # Forged verification flag!
                    "provenance": "Divine Dharshanam Daily generation workflow; visually verified",
                }
            ]
        }
        ok, detail = check_deity_identity_consistency(
            decision=decision,
            script=script,
            visual_map=visual_map,
            video_map={},
            thumbnail_meta=None,
            allow_mock=False,
        )
        self.assertFalse(ok)
        self.assertTrue("failed approval verification" in detail.lower() or "approval status" in detail.lower())

    def test_25_existing_vishnu_avatar_restrictions_remain_intact(self):
        """25. Adversarial 10: Existing Vishnu avatar restrictions remain intact."""
        decision = {"selected_topic": "The Story of Varaha Avatar Rescuing Mother Earth", "deity": "lord_vishnu"}
        script = {"title": "వరాహ అవతార రహస్యం"}
        visual_map = {
            "visual_scenes": [
                {
                    "scene": 1,
                    "image_file": "assets/gods_landscape_long_video/lord_vishnu/kurma_avatar_mandara_mountain_samudra_manthan_landscape.png",
                    "canonical_deity": "lord_vishnu",
                    "avatar": "kurma",  # Kurma avatar supplied on Varaha topic
                    "verification_status": "DEITY_VERIFIED",
                    "provenance": "Divine Dharshanam Daily generation workflow; visually verified",
                }
            ]
        }
        ok, detail = check_deity_identity_consistency(
            decision=decision,
            script=script,
            visual_map=visual_map,
            video_map={},
            thumbnail_meta=None,
            allow_mock=False,
        )
        self.assertFalse(ok)
        self.assertIn("varaha", detail.lower())
        self.assertIn("kurma", detail.lower())


if __name__ == "__main__":
    unittest.main()
