# tests/test_phase3_remediation.py
"""
Regression tests for Phase 3 Remediation:
1. Proposed decisions cannot enter trusted registry.
2. Explicitly approved records can enter registry only with valid evidence.
3. Missing reviewer identity fails approval validation.
4. Missing registry fails closed.
5. Ayyappa image cannot pass Rama identity QA.
6. Hanuman–Rama image cannot pass solo-Hanuman compatibility.
7. Kali–Murugan image cannot pass solo-Kali compatibility.
8. Landscape images cannot enter Shorts selection (APPR-REV-LORD_VISHNU-0260 & APPR-REV-SUBRAMANYA-0347).
9. Square images cannot enter portrait-only Shorts selection.
10. Fallback selection cannot bypass orientation filtering.
11. Long-form selection continues to support landscape images.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from src.assets.approval_registry import (
    TrustedAssetApprovalRecord,
    get_trusted_registry,
)
from src.assets.selector import (
    is_matching_orientation,
    select_scene_assets,
    build_deity_visual_timeline,
    NoMatchingDeityAssetError,
)
from src.qa.checks import (
    _is_trusted_approved_asset,
    check_deity_identity_consistency,
    check_visual_map,
)


class TestPhase3Remediation(unittest.TestCase):
    def setUp(self):
        self.registry = get_trusted_registry()
        self.registry.clear()

    def tearDown(self):
        self.registry.clear()

    def test_01_proposed_decisions_cannot_enter_trusted_registry(self):
        """Proposed decisions without approved status are strictly rejected."""
        with self.assertRaises(ValueError) as ctx:
            self.registry.register_record(
                TrustedAssetApprovalRecord(
                    record_id="APPR-PROP-001",
                    exact_rel_path="assets/gods/hanuman/01ad7740cff3eb6dc2423c8e01babae5.jpg",
                    canonical_deity="hanuman",
                    approval_status="PROPOSED_FOR_APPROVAL",
                    provenance="Review proposal",
                    reviewer="REV-01",
                    review_timestamp="2026-11-20T12:00:00Z",
                )
            )
        self.assertIn("status must be APPROVED", str(ctx.exception))

    def test_02_explicitly_approved_records_enter_only_with_valid_evidence(self):
        """Only explicitly approved records with reviewer and timestamp enter."""
        rec = TrustedAssetApprovalRecord(
            record_id="APPR-VALID-001",
            exact_rel_path="assets/gods/hanuman/01ad7740cff3eb6dc2423c8e01babae5.jpg",
            canonical_deity="hanuman",
            approval_status="APPROVED",
            provenance="Human review completed",
            reviewer="HUMAN-AUDITOR-01",
            review_timestamp="2026-11-20T12:00:00Z",
        )
        self.registry.register_record(rec)
        is_appr, reason, stored = self.registry.is_asset_approved(
            "assets/gods/hanuman/01ad7740cff3eb6dc2423c8e01babae5.jpg",
            deity="hanuman"
        )
        self.assertTrue(is_appr)
        self.assertEqual(stored.reviewer, "HUMAN-AUDITOR-01")

    def test_03_missing_reviewer_identity_fails_approval_validation(self):
        """Missing reviewer identity fails validation."""
        with self.assertRaises(ValueError) as ctx:
            self.registry.register_record(
                TrustedAssetApprovalRecord(
                    record_id="APPR-NO-REV-001",
                    exact_rel_path="assets/gods/hanuman/01ad7740cff3eb6dc2423c8e01babae5.jpg",
                    canonical_deity="hanuman",
                    approval_status="APPROVED",
                    provenance="Human review",
                    reviewer="",  # empty
                    review_timestamp="2026-11-20T12:00:00Z",
                )
            )
        self.assertIn("missing verifiable human reviewer identity", str(ctx.exception))

    def test_04_missing_registry_fails_closed(self):
        """Missing or empty registry rejects all asset queries."""
        self.registry.clear()
        is_appr, reason, rec = self.registry.is_asset_approved(
            "assets/gods/hanuman/01ad7740cff3eb6dc2423c8e01babae5.jpg",
            deity="hanuman"
        )
        self.assertFalse(is_appr)
        self.assertIsNone(rec)

    def test_05_ayyappa_image_cannot_pass_rama_identity_qa(self):
        """Ayyappa/Manikanta image is strictly barred from Lord Rama identity QA."""
        ayyappa_path = "assets/gods/subramanya/HD Photo Frame Of Manikanta.jpg"
        visual_map = {
            "visual_scenes": [
                {
                    "scene": 1,
                    "canonical_deity": "ram",
                    "deity": "ram",
                    "avatar": "ram",
                    "verification_status": "DEITY_VERIFIED",
                    "source_verification_status": "verified_visual",
                    "source_approval_status": "APPROVED",
                    "provenance": "Curated",
                    "image_file": ayyappa_path,
                    "source_asset_path": ayyappa_path,
                }
            ]
        }
        ok, msg = check_deity_identity_consistency(
            decision={"selected_topic": "Lord Rama Dharma", "deity": "ram"},
            script={"title": "Lord Rama"},
            visual_map=visual_map,
            video_map=None,
            thumbnail_meta=None,
            allow_mock=False,
        )
        self.assertFalse(ok)
        self.assertIn("IDENTITY_MISCLASSIFICATION", msg)
        self.assertIn("Manikanta/Ayyappa", msg)

    def test_06_hanuman_rama_image_cannot_pass_solo_hanuman_compatibility(self):
        """Dual Hanuman-Rama artwork is prohibited for solo-Hanuman scenes."""
        dual_path = "assets/gods/ram/lord Rama with hanuman.jpg"
        # Register with allow_solo=False
        self.registry.register_record(
            TrustedAssetApprovalRecord(
                record_id="APPR-HAN-RAM-001",
                exact_rel_path=dual_path,
                canonical_deity="hanuman",
                approval_status="APPROVED",
                provenance="Curated dual",
                reviewer="HUMAN-REV",
                review_timestamp="2026-11-20T12:00:00Z",
                co_depicted_deities=("hanuman", "ram"),
                allow_solo=False,
            )
        )
        visual_map = {
            "visual_scenes": [
                {
                    "scene": 1,
                    "canonical_deity": "hanuman",
                    "deity": "hanuman",
                    "verification_status": "DEITY_VERIFIED",
                    "source_verification_status": "verified_visual",
                    "source_approval_status": "APPROVED",
                    "provenance": "Curated",
                    "image_file": dual_path,
                    "source_asset_path": dual_path,
                }
            ]
        }
        # Solo topic (no Rama keywords)
        ok, msg = check_deity_identity_consistency(
            decision={"selected_topic": "Veer Hanuman Bravery and Strength", "deity": "hanuman"},
            script={"title": "Veer Hanuman"},
            visual_map=visual_map,
            video_map=None,
            thumbnail_meta=None,
            allow_mock=False,
        )
        self.assertFalse(ok)
        self.assertIn("dual Hanuman-Rama depiction", msg)

    def test_07_kali_murugan_image_cannot_pass_solo_kali_compatibility(self):
        """Dual Kali-Murugan artwork is prohibited for solo-Kali scenes."""
        dual_path = "assets/gods/subramanya/Kali and murugan.jpg"
        self.registry.register_record(
            TrustedAssetApprovalRecord(
                record_id="APPR-KALI-MUR-001",
                exact_rel_path=dual_path,
                canonical_deity="kali",
                approval_status="APPROVED",
                provenance="Curated dual",
                reviewer="HUMAN-REV",
                review_timestamp="2026-11-20T12:00:00Z",
                co_depicted_deities=("kali", "subramanya"),
                allow_solo=False,
            )
        )
        visual_map = {
            "visual_scenes": [
                {
                    "scene": 1,
                    "canonical_deity": "kali",
                    "deity": "kali",
                    "verification_status": "DEITY_VERIFIED",
                    "source_verification_status": "verified_visual",
                    "source_approval_status": "APPROVED",
                    "provenance": "Curated",
                    "image_file": dual_path,
                    "source_asset_path": dual_path,
                }
            ]
        }
        # Solo Kali topic
        ok, msg = check_deity_identity_consistency(
            decision={"selected_topic": "Goddess Kali Fierce Form and Grace", "deity": "kali"},
            script={"title": "Goddess Kali"},
            visual_map=visual_map,
            video_map=None,
            thumbnail_meta=None,
            allow_mock=False,
        )
        self.assertFalse(ok)
        self.assertIn("dual Kali-Murugan depiction", msg)

    def test_08_landscape_images_cannot_enter_shorts_selection(self):
        """Landscape assets APPR-REV-LORD_VISHNU-0260 & APPR-REV-SUBRAMANYA-0347 are rejected for Shorts."""
        vishnu_landscape = "assets/gods/lord_vishnu/ChatGPT Image May 29, 2026, 11_57_34 AM.png"
        murugan_landscape = "assets/gods/subramanya/Parvati Have Time For Her Children (Vinayagar Murugan).jpg"

        # Direct orientation helper test
        self.assertFalse(is_matching_orientation({"path": vishnu_landscape, "width": 1402, "height": 1122}, "short"))
        self.assertFalse(is_matching_orientation({"path": murugan_landscape, "width": 736, "height": 581}, "short"))

        # Visual map QA check rejects landscape in Shorts
        vm = {
            "content_type": "short",
            "provider": "local",
            "visual_scenes": [
                {"scene": 1, "image_file": vishnu_landscape, "duration_seconds": 5}
            ]
        }
        ok, msg = check_visual_map(vm)
        self.assertFalse(ok)
        self.assertIn("non-portrait dimensions", msg)

    def test_09_square_images_cannot_enter_portrait_only_shorts_selection(self):
        """Square images (width == height) are strictly rejected for Shorts."""
        square_ganesha = {"path": "assets/gods/ganesha/68d484fa7f5c87548d34873a63ade733.jpg", "width": 736, "height": 736}
        self.assertFalse(is_matching_orientation(square_ganesha, "short"))

        # QA check rejects square image in Shorts
        vm = {
            "content_type": "short",
            "provider": "local",
            "visual_scenes": [
                {"scene": 1, "image_file": square_ganesha["path"], "duration_seconds": 5}
            ]
        }
        ok, msg = check_visual_map(vm)
        self.assertFalse(ok)
        self.assertIn("non-portrait dimensions (736x736)", msg)

    def test_10_fallback_selection_cannot_bypass_orientation_filtering(self):
        """Fallback selection cannot select square or landscape images for Shorts."""
        manifest = {
            "deities": {
                "ganesha": {
                    "images": [
                        # Only square images available
                        {"path": "assets/gods/ganesha/68d484fa7f5c87548d34873a63ade733.jpg", "width": 736, "height": 736}
                    ],
                    "videos": []
                }
            }
        }
        # Attempt to build timeline for Shorts: must fail closed because no portrait images exist
        with self.assertRaises((NoMatchingDeityAssetError, ValueError)):
            build_deity_visual_timeline("ganesha", target_duration=10.0, content_type="short", manifest=manifest)

    def test_11_long_form_selection_continues_to_support_landscape_images(self):
        """Long-form selection continues to support horizontal/landscape artwork."""
        vishnu_landscape = {"path": "assets/gods/lord_vishnu/ChatGPT Image May 29, 2026, 11_57_34 AM.png", "width": 1402, "height": 1122}
        self.assertTrue(is_matching_orientation(vishnu_landscape, "long"))


if __name__ == "__main__":
    unittest.main()
