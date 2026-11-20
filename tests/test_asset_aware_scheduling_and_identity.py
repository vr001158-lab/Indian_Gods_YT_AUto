"""
tests/test_asset_aware_scheduling_and_identity.py

Regression test suite for:
1. Kali identity verification (accepted asset in subramanya/ passes Visual QA)
2. Unapproved Kali asset remains strictly rejected
3. Rama / Subramanya substring collision fix:
   - "Glory of Subramanya" -> Subramanya
   - "Lord Rama devotional story" -> Rama
   - "Ramayana story" -> Rama
   - "Shri Ram Navami" -> Rama
4. Asset-aware weekday scheduling:
   - Tuesday never selects unavailable Durga
   - Wednesday never selects unavailable Budha or Vithal
   - Thursday never selects unavailable Brihaspati
   - Saturday never selects unavailable Shani
   - Sunday fails closed and skips generation safely (neither Surya nor Kaal Bhairav has assets)
   - Deterministic rotation remains stable across available deities
   - Quarantined assets remain inaccessible
   - No cross-deity artwork fallback
"""

import os
import sys
import json
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

sys.path.insert(0, os.getcwd())

from src.decision.weekday_deity import (
    KOLKATA_TZ,
    WEEKDAY_DEITY_MAPPING,
    get_weekday_info,
    select_weekday_deity,
    rotate_deity_for_day,
    is_deity_eligible_for_weekday,
    NoApprovedWeekdayDeityAssetsError,
)
from src.thumbnail.asset_index import (
    resolve_deity_and_avatar,
    DeityAssetIndex,
)
from src.qa.checks import (
    check_deity_identity_consistency,
    check_visual_map,
)
from src.assets.approval_registry import get_trusted_registry
from src.decision.report import run_decision_pipeline


class TestAssetAwareSchedulingAndIdentity(unittest.TestCase):

    def setUp(self):
        self.registry = get_trusted_registry()
        # Seed test approval records with verifiable reviewer evidence for scheduled deities
        test_records = [
            ("assets/gods/hanuman/test_h.jpg", "hanuman"),
            ("assets/gods/ganesha/test_g.jpg", "ganesha"),
            ("assets/gods/lord_shiva/test_s.jpg", "lord_shiva"),
            ("assets/gods/krishna/test_k.jpg", "krishna"),
            ("assets/gods/lord_vishnu/test_v.jpg", "lord_vishnu"),
            ("assets/gods/subramanya/test_sub.jpg", "subramanya"),
            ("assets/gods/parvathi/test_p.jpg", "parvathi"),
            ("assets/gods/lakshmi_devi/test_l.jpg", "lakshmi_devi"),
        ]
        from src.assets.approval_registry import TrustedAssetApprovalRecord
        for p, d in test_records:
            self.registry.register_record(
                TrustedAssetApprovalRecord(
                    record_id=f"APPR-TEST-{d.upper()}-001",
                    exact_rel_path=p,
                    canonical_deity=d,
                    approval_status="APPROVED",
                    provenance="Test suite approved asset",
                    reviewer="REV-TEST-01",
                    review_timestamp="2026-11-20T12:00:00Z",
                )
            )
        # Register Kali and murugan dual record
        self.registry.register_record(
            TrustedAssetApprovalRecord(
                record_id="APPR-TEST-KALI-001",
                exact_rel_path="assets/gods/subramanya/Kali and murugan.jpg",
                canonical_deity="kali",
                approval_status="APPROVED",
                provenance="Test dual asset",
                reviewer="REV-TEST-01",
                review_timestamp="2026-11-20T12:00:00Z",
                co_depicted_deities=("kali", "subramanya"),
                allow_solo=False,
            )
        )

    def tearDown(self):
        self.registry.reset_to_builtins()

    # ──────────────────────────────────────────────────────────────────────────
    # 1. Kali Identity Verification (Accepted asset in physical folder subramanya/)
    # ──────────────────────────────────────────────────────────────────────────

    def test_01_accepted_kali_asset_in_subramanya_folder_passes_visual_qa(self):
        """Accepted Kali asset passes Visual QA for dual-compatible topic, rejected for solo topic."""
        kali_path = "assets/gods/subramanya/Kali and murugan.jpg"
        # Confirm registry record
        rec = self.registry.get_approval_record(kali_path)
        self.assertIsNotNone(rec, "Expected Kali and murugan.jpg to be in approval registry")
        self.assertEqual(rec.canonical_deity, "kali")
        self.assertEqual(rec.approval_status, "APPROVED")
        self.assertFalse(rec.allow_solo)

        # 1. Solo Kali topic must fail QA due to dual-deity restriction
        solo_decision = {"selected_topic": "Goddess Kali Divine Form and Cosmic Energy", "deity": "kali"}
        solo_script = {
            "title": "Goddess Kali Divine Form and Cosmic Energy",
            "approval_metadata": {"selected_topic": "Goddess Kali Divine Form and Cosmic Energy", "deity": "kali"},
            "scene_scripts": [{"scene": 1, "visual_reference": "Goddess Kali blessing devotees", "duration_seconds": 10}],
        }
        visual_map = {
            "provider": "repository",
            "visual_scenes": [
                {
                    "scene": 1,
                    "image_file": kali_path,
                    "source_asset_path": kali_path,
                    "canonical_deity": "kali",
                    "verification_status": "DEITY_VERIFIED",
                    "provenance": rec.provenance,
                    "duration_seconds": 10,
                }
            ],
        }
        solo_ok, solo_detail = check_deity_identity_consistency(
            decision=solo_decision,
            script=solo_script,
            visual_map=visual_map,
            video_map={},
            thumbnail_meta=None,
            allow_mock=False,
        )
        self.assertFalse(solo_ok, "Expected solo Kali topic to be rejected for dual Kali-Murugan asset")
        self.assertIn("dual Kali-Murugan depiction", solo_detail)

        # 2. Dual-compatible topic mentioning Murugan must pass QA
        dual_decision = {"selected_topic": "Goddess Kali and Lord Murugan Divine Darshan", "deity": "kali"}
        dual_script = {
            "title": "Goddess Kali and Lord Murugan Divine Darshan",
            "approval_metadata": {"selected_topic": "Goddess Kali and Lord Murugan Divine Darshan", "deity": "kali"},
            "scene_scripts": [{"scene": 1, "visual_reference": "Kali and Murugan blessing devotees", "duration_seconds": 10}],
        }
        ok, detail = check_deity_identity_consistency(
            decision=dual_decision,
            script=dual_script,
            visual_map=visual_map,
            video_map={},
            thumbnail_meta=None,
            allow_mock=False,
        )
        self.assertTrue(ok, f"Expected dual-compatible Kali asset to pass QA, but got: {detail}")
        self.assertEqual(detail, "OK")

    def test_02_unapproved_kali_asset_remains_strictly_rejected(self):
        """Unapproved asset pretending to be Kali is strictly rejected by Visual QA."""
        fake_path = "assets/gods/subramanya/unapproved_forged_kali.jpg"
        decision = {"selected_topic": "Goddess Kali Victory Over Darkness", "deity": "kali"}
        script = {
            "title": "Goddess Kali Victory Over Darkness",
            "approval_metadata": {"selected_topic": "Goddess Kali Victory Over Darkness", "deity": "kali"},
        }
        visual_map = {
            "provider": "repository",
            "visual_scenes": [
                {
                    "scene": 1,
                    "image_file": fake_path,
                    "source_asset_path": fake_path,
                    "canonical_deity": "kali",
                    "verification_status": "DEITY_VERIFIED",
                    "provenance": "Forged metadata",
                    "duration_seconds": 10,
                }
            ],
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
            "failed approval verification" in detail.lower() or "deity_mismatch" in detail.lower(),
            f"Expected rejection detail, got: {detail}",
        )

    def test_03_cross_deity_substitution_using_approved_subramanya_asset_rejected(self):
        """Approved Subramanya asset cannot be substituted on a Kali topic (cross-deity guard)."""
        subramanya_path = "assets/gods/subramanya/1076571485939987930.jpg"
        decision = {"selected_topic": "Goddess Kali Fierce Protection", "deity": "kali"}
        script = {
            "title": "Goddess Kali Fierce Protection",
            "approval_metadata": {"selected_topic": "Goddess Kali Fierce Protection", "deity": "kali"},
        }
        visual_map = {
            "provider": "repository",
            "visual_scenes": [
                {
                    "scene": 1,
                    "image_file": subramanya_path,
                    "source_asset_path": subramanya_path,
                    "canonical_deity": "kali",  # forged deity key on scene
                    "verification_status": "DEITY_VERIFIED",
                    "provenance": "Curated deity asset",
                    "duration_seconds": 10,
                }
            ],
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
        self.assertIn("deity_mismatch", detail.lower())

    # ──────────────────────────────────────────────────────────────────────────
    # 2. Rama / Subramanya Substring Collision
    # ──────────────────────────────────────────────────────────────────────────

    def test_04_subramanya_not_misidentified_as_rama(self):
        """'Glory of Subramanya' resolves strictly to Subramanya, never Rama."""
        deity, avatar = resolve_deity_and_avatar("Glory of Subramanya")
        self.assertEqual(deity, "subramanya")
        self.assertIsNone(avatar)

        deity2, avatar2 = resolve_deity_and_avatar("Lord Murugan Divine Vel and Peacock")
        self.assertEqual(deity2, "subramanya")
        self.assertIsNone(avatar2)

    def test_05_rama_devotional_topics_remain_correctly_identified(self):
        """'Lord Rama devotional story' and 'Shri Ram Navami' resolve to Rama."""
        deity, avatar = resolve_deity_and_avatar("Lord Rama devotional story")
        self.assertEqual(deity, "ram")
        self.assertEqual(avatar, "rama")

        deity2, avatar2 = resolve_deity_and_avatar("Shri Ram Navami Celebration")
        self.assertEqual(deity2, "ram")
        self.assertEqual(avatar2, "ram")

    def test_06_ramayana_story_resolves_to_rama(self):
        """'Ramayana story' follows existing intended Rama resolution."""
        deity, avatar = resolve_deity_and_avatar("Ramayana story and virtues of Dharma")
        self.assertEqual(deity, "ram")
        self.assertEqual(avatar, "rama")

    # ──────────────────────────────────────────────────────────────────────────
    # 3. Asset-Aware Weekday Scheduler
    # ──────────────────────────────────────────────────────────────────────────

    def test_07_tuesday_never_selects_unavailable_durga(self):
        """Tuesday rotates only across Hanuman, Ganesha, Kali, Subramanya; Durga is unavailable."""
        tuesday_dt = datetime(2026, 11, 17, 10, 0, tzinfo=KOLKATA_TZ)
        seen = set()
        for week in range(20):
            test_dt = tuesday_dt + timedelta(days=7 * week)
            ctx = select_weekday_deity(test_dt)
            self.assertEqual(ctx["english_day"], "Tuesday")
            self.assertIn("durga", ctx["unavailable_deities"])
            self.assertNotIn("durga", ctx["available_deities"])
            self.assertNotEqual(ctx["scheduled_deity"], "durga")
            self.assertIn(ctx["scheduled_deity"], ["hanuman", "ganesha", "kali", "subramanya"])
            seen.add(ctx["scheduled_deity"])
        self.assertEqual(len(seen), 4, f"Expected all 4 available Tuesday deities to be chosen over 20 weeks: {seen}")

    def test_08_wednesday_never_selects_unavailable_budha_or_vithal(self):
        """Wednesday rotates only across Ganesha and Krishna; Budha and Vithal are unavailable."""
        wednesday_dt = datetime(2026, 11, 18, 10, 0, tzinfo=KOLKATA_TZ)
        seen = set()
        for week in range(10):
            test_dt = wednesday_dt + timedelta(days=7 * week)
            ctx = select_weekday_deity(test_dt)
            self.assertEqual(ctx["english_day"], "Wednesday")
            self.assertIn("budha", ctx["unavailable_deities"])
            self.assertIn("vithal", ctx["unavailable_deities"])
            self.assertNotIn("budha", ctx["available_deities"])
            self.assertNotIn("vithal", ctx["available_deities"])
            self.assertIn(ctx["scheduled_deity"], ["ganesha", "krishna"])
            seen.add(ctx["scheduled_deity"])
        self.assertEqual(seen, {"ganesha", "krishna"})

    def test_09_thursday_never_selects_unavailable_brihaspati(self):
        """Thursday rotates only across Lord Vishnu and Krishna; Brihaspati is unavailable."""
        thursday_dt = datetime(2026, 11, 19, 10, 0, tzinfo=KOLKATA_TZ)
        seen = set()
        for week in range(52):
            test_dt = thursday_dt + timedelta(days=7 * week)
            ctx = select_weekday_deity(test_dt)
            self.assertEqual(ctx["english_day"], "Thursday")
            self.assertIn("brihaspati", ctx["unavailable_deities"])
            self.assertNotIn("brihaspati", ctx["available_deities"])
            self.assertIn(ctx["scheduled_deity"], ["lord_vishnu", "krishna"])
            seen.add(ctx["scheduled_deity"])
        self.assertEqual(seen, {"lord_vishnu", "krishna"})

    def test_10_saturday_never_selects_unavailable_shani(self):
        """Saturday always selects Hanuman; Shani is unavailable."""
        saturday_dt = datetime(2026, 11, 21, 10, 0, tzinfo=KOLKATA_TZ)
        for week in range(5):
            test_dt = saturday_dt + timedelta(days=7 * week)
            ctx = select_weekday_deity(test_dt)
            self.assertEqual(ctx["english_day"], "Saturday")
            self.assertIn("shani", ctx["unavailable_deities"])
            self.assertNotIn("shani", ctx["available_deities"])
            self.assertEqual(ctx["scheduled_deity"], "hanuman")

    def test_11_sunday_fails_closed_when_neither_surya_nor_bhairav_has_assets(self):
        """Sunday raises NoApprovedWeekdayDeityAssetsError and skips generation (fail-closed)."""
        sunday_dt = datetime(2026, 11, 22, 10, 0, tzinfo=KOLKATA_TZ)
        with self.assertRaises(NoApprovedWeekdayDeityAssetsError) as exc_cm:
            select_weekday_deity(sunday_dt)
        self.assertIn("No approved assets found", str(exc_cm.exception))
        self.assertIn("surya", str(exc_cm.exception))

    def test_12_decision_pipeline_on_sunday_safely_skips_generation(self):
        """Decision pipeline on Sunday cleanly skips generation with detailed context."""
        sunday_dt = datetime(2026, 11, 22, 10, 0, tzinfo=KOLKATA_TZ)
        with patch("src.decision.report.get_current_kolkata_datetime", return_value=sunday_dt), \
             patch("src.decision.weekday_deity.get_current_kolkata_datetime", return_value=sunday_dt):
            candidates = [
                {
                    "topic": "సూర్య నమస్కార విశిష్టత",
                    "category": "devotional",
                    "overall_score": 85,
                    "demand_score": 80,
                    "relevance_score": 90,
                    "competition_score": 40,
                    "evergreen_score": 90,
                    "freshness_score": 85,
                    "curiosity_score": 80,
                    "long_form_potential": 80,
                    "shorts_potential": 85,
                    "confidence": "high",
                    "data_source": "cached_youtube_api",
                    "deity": "surya",
                    "suggested_angle": "health and vitality",
                    "content_gap": "high",
                }
            ]
            decision = run_decision_pipeline(candidates, save=False, language_code="te-IN")
            self.assertFalse(decision["approved_for_generation"])
            self.assertIsNone(decision["selected_topic"])
            self.assertIn("Generation skipped", decision["selection_reason"])
            ctx = decision["weekday_deity_context"]
            self.assertTrue(ctx["generation_skipped"])
            self.assertEqual(ctx["available_deities"], [])
            self.assertIn("surya", ctx["unavailable_deities"])
            self.assertIn("kaal_bhairav", ctx["unavailable_deities"])

    def test_13_quarantined_assets_cannot_be_selected_or_verified(self):
        """Quarantined files cannot satisfy deity coverage or pass Visual QA."""
        quarantine_file = "assets/quarantine/assets/gods_landscape_long_video/hanuman/hanuman_carrying_dronagiri_sanjeevani_landscape.png"
        ok, reason, rec = self.registry.is_asset_approved(quarantine_file, deity="hanuman")
        self.assertFalse(ok)
        self.assertIn("unapproved", reason.lower())


if __name__ == "__main__":
    unittest.main()
