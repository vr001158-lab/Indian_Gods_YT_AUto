# tests/test_asset_approval_trust.py
# 12 Mandatory Regression Tests for Asset Approval Trust-Model Remediation
#
# Proves:
#   1. Ordinary image in deity folder rejected without approval record.
#   2. Ordinary video in deity folder rejected without approval record.
#   3. Landscape image rejected without approval record.
#   4. Convincing deity filename cannot bypass approval.
#   5. Generated manifest cannot bypass approval.
#   6. Folder-derived deity identity cannot bypass approval.
#   7. Exact approved asset for correct deity is accepted.
#   8. Same asset rejected for another deity.
#   9. Unapproved/quarantined incoming asset rejected.
#   10. Caller-provided `verified_visual` cannot bypass approval.
#   11. Filename-stem collisions cannot cause approval.
#   12. Missing/malformed registry entries fail closed.

from __future__ import annotations

import unittest
from pathlib import Path

from src.assets.approval_registry import (
    TrustedAssetApprovalRecord,
    TrustedAssetApprovalRegistry,
    get_trusted_registry,
    normalize_repo_path,
)
from src.assets.manifest import load_landscape_asset_manifest
from src.assets.scanner import _enrich_asset_metadata
from src.assets.selector import _is_item_verified_visual, select_scene_assets
from src.qa.checks import _is_trusted_approved_asset, check_deity_identity_consistency
from src.thumbnail.asset_index import DeityAssetIndex, reset_asset_index_cache


class TestAssetApprovalTrustModel(unittest.TestCase):
    """
    Mandatory regression tests proving that every automatic asset approval or
    verification path based on folder names, filenames, generated manifests,
    or inferred deity classifications is removed.
    """

    def setUp(self):
        self.registry = get_trusted_registry()
        self.registry.reset_to_builtins()
        reset_asset_index_cache()

    def tearDown(self):
        self.registry.reset_to_builtins()
        reset_asset_index_cache()

    def test_01_ordinary_image_in_deity_folder_rejected_without_approval_record(self):
        """1. Ordinary image in deity folder rejected without explicit approval record."""
        # Unapproved image path in assets/gods/ganesha
        unapproved_img = "assets/gods/ganesha/random_unapproved_photo_download.jpg"
        is_appr, reason, rec = self.registry.is_asset_approved(unapproved_img, deity="ganesha")
        self.assertFalse(is_appr)
        self.assertIn("lacks an explicit trusted asset approval record", reason)
        self.assertIsNone(rec)

        # QA check also rejects it
        qa_ok, qa_msg = _is_trusted_approved_asset(unapproved_img, deity="ganesha")
        self.assertFalse(qa_ok)
        self.assertIn("lacks an explicit trusted asset approval record", qa_msg)

    def test_02_ordinary_video_in_deity_folder_rejected_without_approval_record(self):
        """2. Ordinary video in deity folder rejected without explicit approval record."""
        unapproved_vid = "assets/gods_processed/shiva/vertical/random_unvetted_clip.mp4"
        is_appr, reason, rec = self.registry.is_asset_approved(unapproved_vid, deity="lord_shiva")
        self.assertFalse(is_appr)
        self.assertIn("lacks an explicit trusted asset approval record", reason)
        self.assertIsNone(rec)

        qa_ok, qa_msg = _is_trusted_approved_asset(unapproved_vid, deity="lord_shiva")
        self.assertFalse(qa_ok)
        self.assertIn("lacks an explicit trusted asset approval record", qa_msg)

    def test_03_landscape_image_rejected_without_approval_record(self):
        """3. Landscape image rejected without explicit approval record."""
        unapproved_landscape = "assets/gods_landscape_long_video/lord_shiva/unregistered_shiva_landscape.png"
        is_appr, reason, rec = self.registry.is_asset_approved(unapproved_landscape, deity="lord_shiva")
        self.assertFalse(is_appr)
        self.assertIn("lacks an explicit trusted asset approval record", reason)
        self.assertIsNone(rec)

        qa_ok, qa_msg = _is_trusted_approved_asset(unapproved_landscape, deity="lord_shiva")
        self.assertFalse(qa_ok)
        self.assertIn("lacks an explicit trusted asset approval record", qa_msg)

    def test_04_convincing_deity_filename_cannot_bypass_approval(self):
        """4. Convincing deity filename keywords cannot bypass approval."""
        convincing_path = (
            "assets/gods/lord_shiva/lord_shiva_mahadev_trishul_divine_blessing_4k_ultra_hd.png"
        )
        is_appr, reason, rec = self.registry.is_asset_approved(convincing_path, deity="lord_shiva")
        self.assertFalse(is_appr)
        self.assertIn("lacks an explicit trusted asset approval record", reason)

        # Scanner enrichment does not grant verified_visual
        raw_item = {"path": convincing_path, "type": "image"}
        enriched = _enrich_asset_metadata(raw_item, "lord_shiva_mahadev_trishul_divine_blessing_4k_ultra_hd", "lord_shiva")
        self.assertEqual(enriched.get("approval_status"), "UNAPPROVED")
        self.assertEqual(enriched.get("verification_status"), "unverified")

        # Selector also rejects it
        is_ver = _is_item_verified_visual(raw_item, deity_key="lord_shiva")
        self.assertFalse(is_ver)

    def test_05_generated_manifest_cannot_bypass_approval(self):
        """5. Generated manifest cannot bypass approval by declaring approval fields."""
        manifest_item = {
            "path": "assets/gods/ganesha/generated_manifest_asset.png",
            "canonical_deity": "ganesha",
            "avatar": "ganesha",
            "verification_status": "verified_visual",
            "approval_status": "APPROVED",
            "provenance": "Divine Dharshanam Daily generation workflow; visually verified",
        }
        # Manifest loading and selector verification must fail closed
        is_ver = _is_item_verified_visual(manifest_item, deity_key="ganesha")
        self.assertFalse(is_ver)
        self.assertEqual(manifest_item["approval_status"], "UNAPPROVED")
        self.assertEqual(manifest_item["verification_status"], "unverified")

    def test_06_folder_derived_deity_identity_cannot_bypass_approval(self):
        """6. Folder-derived deity identity cannot bypass approval."""
        # File is placed in lord_shiva folder, but has no trusted record
        folder_item_path = "assets/gods/lord_shiva/image_099.jpg"
        is_appr, reason, _ = self.registry.is_asset_approved(folder_item_path, deity="lord_shiva")
        self.assertFalse(is_appr)

        qa_ok, qa_msg = _is_trusted_approved_asset(folder_item_path, deity="lord_shiva")
        self.assertFalse(qa_ok)
        self.assertIn("lacks an explicit trusted asset approval record", qa_msg)

    def test_07_exact_approved_asset_for_correct_deity_is_accepted(self):
        """7. Exact approved asset for correct deity is accepted."""
        approved_path = "assets/gods/hanuman/01ad7740cff3eb6dc2423c8e01babae5.jpg"
        test_rec = TrustedAssetApprovalRecord(
            record_id="APPR-TEST-HANUMAN-0001",
            exact_rel_path=approved_path,
            canonical_deity="hanuman",
            approval_status="APPROVED",
            provenance="Manual review: 2026-11-20",
            reviewer="REV-HUMAN-01",
            review_timestamp="2026-11-20T12:00:00Z",
        )
        self.registry.register_record(test_rec)

        is_appr, reason, rec = self.registry.is_asset_approved(approved_path, deity="hanuman")
        self.assertTrue(is_appr)
        self.assertIsNotNone(rec)
        self.assertEqual(rec.canonical_deity, "hanuman")
        self.assertEqual(rec.approval_status, "APPROVED")
        self.assertEqual(rec.reviewer, "REV-HUMAN-01")

        # QA gate passes
        qa_ok, qa_msg = _is_trusted_approved_asset(approved_path, deity="hanuman")
        self.assertTrue(qa_ok)
        self.assertIn("verified", qa_msg.lower())

    def test_08_same_asset_rejected_for_another_deity(self):
        """8. Same approved asset rejected for another deity (DEITY_MISMATCH)."""
        approved_path = "assets/gods/hanuman/01ad7740cff3eb6dc2423c8e01babae5.jpg"
        test_rec = TrustedAssetApprovalRecord(
            record_id="APPR-TEST-HANUMAN-0001",
            exact_rel_path=approved_path,
            canonical_deity="hanuman",
            approval_status="APPROVED",
            provenance="Manual review: 2026-11-20",
            reviewer="REV-HUMAN-01",
            review_timestamp="2026-11-20T12:00:00Z",
        )
        self.registry.register_record(test_rec)

        # Attempt to use approved Hanuman artwork for Lord Shiva
        is_appr, reason, rec = self.registry.is_asset_approved(approved_path, deity="lord_shiva")
        self.assertFalse(is_appr)
        self.assertIn("DEITY_MISMATCH", reason)
        self.assertIn("hanuman", reason.lower())

        # QA gate strictly rejects
        qa_ok, qa_msg = _is_trusted_approved_asset(approved_path, deity="lord_shiva")
        self.assertFalse(qa_ok)
        self.assertIn("DEITY_MISMATCH", qa_msg)

    def test_09_unapproved_quarantined_incoming_asset_rejected(self):
        """9. Unapproved/quarantined incoming asset is rejected."""
        incoming_asset = "assets/incoming/downloaded_candidate_01.png"
        is_appr, reason, rec = self.registry.is_asset_approved(incoming_asset, deity="ganesha")
        self.assertFalse(is_appr)
        self.assertIn("lacks an explicit trusted asset approval record", reason)

        qa_ok, qa_msg = _is_trusted_approved_asset(incoming_asset, deity="ganesha")
        self.assertFalse(qa_ok)
        self.assertIn("lacks an explicit trusted asset approval record", qa_msg)

    def test_10_caller_provided_verified_visual_cannot_bypass_approval(self):
        """10. Caller-provided 'verified_visual' cannot bypass approval."""
        unapproved_path = "assets/gods/lord_shiva/unapproved_bypass_attempt.png"
        item = {
            "path": unapproved_path,
            "verification_status": "verified_visual",  # Caller claims verified_visual
            "approval_status": "APPROVED",            # Caller claims APPROVED
            "provenance": "Divine Dharshanam Daily generation workflow; visually verified",
            "canonical_deity": "lord_shiva",
        }
        is_ver = _is_item_verified_visual(item, deity_key="lord_shiva")
        self.assertFalse(is_ver)
        self.assertEqual(item["verification_status"], "unverified")
        self.assertEqual(item["approval_status"], "UNAPPROVED")

        # In scene plan and QA consistency
        visual_map = {"visual_scenes": [{"scene": 1, **item}]}
        qa_ok, qa_msg = check_deity_identity_consistency(
            decision={"selected_topic": "Secrets of Shiva", "deity": "lord_shiva"},
            script={"title": "శివుని రహస్యాలు"},
            visual_map=visual_map,
            video_map={},
            thumbnail_meta=None,
        )
        self.assertFalse(qa_ok)
        self.assertIn("unverified", qa_msg.lower())

    def test_11_filename_stem_collisions_cannot_cause_approval(self):
        """11. Filename-stem collisions cannot cause approval; exact repo path required."""
        # Built-in approved path is assets/gods/lord_vishnu/kurma_avatar_mandara_mountain_samudra_manthan.png
        # Fake stem-colliding path in different folder or slightly modified name:
        fake_path_1 = "assets/gods/lord_shiva/kurma_avatar_mandara_mountain_samudra_manthan.png"
        is_appr, reason, _ = self.registry.is_asset_approved(fake_path_1, deity="lord_vishnu", avatar="kurma")
        self.assertFalse(is_appr)

        fake_path_2 = "data/visuals/kurma_avatar_mandara_mountain_samudra_manthan_scene_1.png"
        is_appr2, reason2, _ = self.registry.is_asset_approved(fake_path_2, deity="lord_vishnu", avatar="kurma")
        self.assertFalse(is_appr2)

    def test_12_missing_or_malformed_registry_entries_fail_closed(self):
        """12. Missing or malformed registry entries and traversal paths fail closed."""
        # Path traversal attempts
        traversal_1 = "assets/gods/../../etc/passwd"
        self.assertEqual(normalize_repo_path(traversal_1), "")
        is_appr, reason, _ = self.registry.is_asset_approved(traversal_1, deity="lord_shiva")
        self.assertFalse(is_appr)

        traversal_2 = "../assets/gods/lord_shiva/shiva.jpg"
        self.assertEqual(normalize_repo_path(traversal_2), "")

        # Empty path
        is_appr, reason, _ = self.registry.is_asset_approved("", deity="lord_shiva")
        self.assertFalse(is_appr)

        # Registering malformed record must raise ValueError
        with self.assertRaises(ValueError):
            self.registry.register_record(
                TrustedAssetApprovalRecord(
                    record_id="",  # Missing record_id
                    exact_rel_path="assets/gods/ganesha/test.png",
                    canonical_deity="ganesha",
                    approval_status="APPROVED",
                    provenance="Test",
                )
            )

        with self.assertRaises(ValueError):
            self.registry.register_record(
                TrustedAssetApprovalRecord(
                    record_id="APPR-TEST-001",
                    exact_rel_path="assets/gods/ganesha/test.png",
                    canonical_deity="ganesha",
                    approval_status="PENDING",  # Must be strictly APPROVED
                    provenance="Test",
                    reviewer="REV-01",
                    review_timestamp="2026-11-20T12:00:00Z",
                )
            )

    def test_13_proposed_for_approval_cannot_enter_trusted_registry(self):
        """13. Status 'PROPOSED_FOR_APPROVAL' must strictly fail validation when registering."""
        with self.assertRaises(ValueError):
            self.registry.register_record(
                TrustedAssetApprovalRecord(
                    record_id="APPR-PROP-001",
                    exact_rel_path="assets/gods/ganesha/68d484fa7f5c87548d34873a63ade733.jpg",
                    canonical_deity="ganesha",
                    approval_status="PROPOSED_FOR_APPROVAL",
                    provenance="Review decision proposal",
                    reviewer="REV-01",
                    review_timestamp="2026-11-20T12:00:00Z",
                )
            )

    def test_14_missing_reviewer_identity_fails_approval_validation(self):
        """14. An APPROVED record missing reviewer identity is rejected."""
        with self.assertRaises(ValueError):
            self.registry.register_record(
                TrustedAssetApprovalRecord(
                    record_id="APPR-NO-REV-001",
                    exact_rel_path="assets/gods/ganesha/68d484fa7f5c87548d34873a63ade733.jpg",
                    canonical_deity="ganesha",
                    approval_status="APPROVED",
                    provenance="Human review",
                    reviewer=None,  # Missing reviewer
                    review_timestamp="2026-11-20T12:00:00Z",
                )
            )

    def test_15_missing_review_timestamp_fails_approval_validation(self):
        """15. An APPROVED record missing review timestamp is rejected."""
        with self.assertRaises(ValueError):
            self.registry.register_record(
                TrustedAssetApprovalRecord(
                    record_id="APPR-NO-TIME-001",
                    exact_rel_path="assets/gods/ganesha/68d484fa7f5c87548d34873a63ade733.jpg",
                    canonical_deity="ganesha",
                    approval_status="APPROVED",
                    provenance="Human review",
                    reviewer="REV-HUMAN-01",
                    review_timestamp="",  # Empty timestamp
                )
            )

    def test_16_empty_or_missing_registry_fails_closed(self):
        """16. Empty registry fails closed and rejects all asset approval lookups."""
        self.registry.clear()
        is_appr, reason, rec = self.registry.is_asset_approved(
            "assets/gods/ganesha/68d484fa7f5c87548d34873a63ade733.jpg",
            deity="ganesha"
        )
        self.assertFalse(is_appr)
        self.assertIn("lacks an explicit trusted asset approval record", reason)
        self.assertIsNone(rec)


if __name__ == "__main__":
    unittest.main()
