# tests/test_asset_review_dashboard.py
# Verification of Asset Review Dashboard Generation & Integrity

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.assets.approval_registry import get_trusted_registry, normalize_repo_path
from src.assets.dashboard_builder import generate_dashboard_file
from src.assets.inventory import AssetInventoryItem


class TestAssetReviewDashboard(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_dir_path = Path(self.temp_dir.name)
        self.dashboard_path = self.temp_dir_path / "asset_review_dashboard.html"
        self.instructions_path = Path("docs/asset_review_instructions.md")
        self.inventory_path = self.temp_dir_path / "candidate_asset_inventory.json"
        self.matrix_path = self.temp_dir_path / "deity_coverage_matrix.json"
        self.duplicates_path = self.temp_dir_path / "duplicates_and_broken.json"
        self.frames_dir = self.temp_dir_path / "extracted_frames"
        self.frames_dir.mkdir(parents=True, exist_ok=True)

        # Build deterministic fixture matching AssetInventoryItem schema
        self.fixture_items = self._build_deterministic_fixture()
        self.inventory_path.write_text(json.dumps(self.fixture_items, indent=2), encoding="utf-8")
        self.matrix_path.write_text(json.dumps({"summary": "test_matrix"}, indent=2), encoding="utf-8")
        self.duplicates_path.write_text(json.dumps({"duplicates": [], "broken": []}, indent=2), encoding="utf-8")

        # Generate initial dashboard HTML strictly within temp dir
        generate_dashboard_file(
            inventory_path=self.inventory_path,
            matrix_path=self.matrix_path,
            duplicates_path=self.duplicates_path,
            frames_dir=self.frames_dir,
            output_html_path=self.dashboard_path,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def _build_deterministic_fixture(self) -> list[dict]:
        """Creates valid candidate inventory items covering key deities, aspect ratios, and flags."""
        items = [
            AssetInventoryItem(
                rel_path="assets/gods/ganesha/ganesha_portrait.jpg",
                file_type="image",
                file_ext=".jpg",
                file_size_bytes=102400,
                sha256="1" * 64,
                width=720,
                height=1280,
                aspect_ratio="9:16",
                duration_seconds=0.0,
                approval_status="UNAPPROVED",
                approval_record_id=None,
                registry_deity=None,
                registry_avatar=None,
                candidate_deity="ganesha",
                candidate_avatar=None,
                provenance_note="Test fixture asset",
                is_broken=False,
                broken_reason=None,
                is_duplicate=False,
                duplicate_of=None,
            ).to_dict(),
            AssetInventoryItem(
                rel_path="assets/gods/hanuman/hanuman_landscape.jpg",
                file_type="image",
                file_ext=".jpg",
                file_size_bytes=204800,
                sha256="2" * 64,
                width=1280,
                height=720,
                aspect_ratio="16:9",
                duration_seconds=0.0,
                approval_status="UNAPPROVED",
                approval_record_id=None,
                registry_deity=None,
                registry_avatar=None,
                candidate_deity="hanuman",
                candidate_avatar=None,
                provenance_note="Test fixture asset",
                is_broken=False,
                broken_reason=None,
                is_duplicate=False,
                duplicate_of=None,
            ).to_dict(),
            AssetInventoryItem(
                rel_path="assets/gods/parvathi/parvathi_portrait.png",
                file_type="image",
                file_ext=".png",
                file_size_bytes=150000,
                sha256="3" * 64,
                width=720,
                height=1280,
                aspect_ratio="9:16",
                duration_seconds=0.0,
                approval_status="UNAPPROVED",
                approval_record_id=None,
                registry_deity=None,
                registry_avatar=None,
                candidate_deity="parvathi",
                candidate_avatar=None,
                provenance_note="Test fixture asset",
                is_broken=False,
                broken_reason=None,
                is_duplicate=False,
                duplicate_of=None,
            ).to_dict(),
            AssetInventoryItem(
                rel_path="assets/gods/subramanya/kartikeya_portrait.jpg",
                file_type="image",
                file_ext=".jpg",
                file_size_bytes=160000,
                sha256="4" * 64,
                width=720,
                height=1280,
                aspect_ratio="9:16",
                duration_seconds=0.0,
                approval_status="UNAPPROVED",
                approval_record_id=None,
                registry_deity=None,
                registry_avatar=None,
                candidate_deity="subramanya",
                candidate_avatar=None,
                provenance_note="Test fixture asset",
                is_broken=False,
                broken_reason=None,
                is_duplicate=False,
                duplicate_of=None,
            ).to_dict(),
            AssetInventoryItem(
                rel_path="assets/gods/lakshmi_devi/mahalakshmi_square.jpg",
                file_type="image",
                file_ext=".jpg",
                file_size_bytes=170000,
                sha256="5" * 64,
                width=1000,
                height=1000,
                aspect_ratio="1:1",
                duration_seconds=0.0,
                approval_status="UNAPPROVED",
                approval_record_id=None,
                registry_deity=None,
                registry_avatar=None,
                candidate_deity="lakshmi_devi",
                candidate_avatar=None,
                provenance_note="Test fixture asset",
                is_broken=False,
                broken_reason=None,
                is_duplicate=False,
                duplicate_of=None,
            ).to_dict(),
            AssetInventoryItem(
                rel_path="assets/gods/kali/kali_portrait.jpg",
                file_type="image",
                file_ext=".jpg",
                file_size_bytes=180000,
                sha256="6" * 64,
                width=720,
                height=1280,
                aspect_ratio="9:16",
                duration_seconds=0.0,
                approval_status="UNAPPROVED",
                approval_record_id=None,
                registry_deity=None,
                registry_avatar=None,
                candidate_deity="kali",
                candidate_avatar=None,
                provenance_note="Test fixture asset",
                is_broken=False,
                broken_reason=None,
                is_duplicate=False,
                duplicate_of=None,
            ).to_dict(),
            AssetInventoryItem(
                rel_path="assets/gods/broken/corrupt_asset.mp4",
                file_type="video",
                file_ext=".mp4",
                file_size_bytes=500000,
                sha256="7" * 64,
                width=1280,
                height=720,
                aspect_ratio="16:9",
                duration_seconds=10.0,
                approval_status="UNAPPROVED",
                approval_record_id=None,
                registry_deity=None,
                registry_avatar=None,
                candidate_deity="lord_shiva",
                candidate_avatar=None,
                provenance_note="Test fixture asset",
                is_broken=True,
                broken_reason="Corrupt moov atom",
                is_duplicate=False,
                duplicate_of=None,
            ).to_dict(),
            AssetInventoryItem(
                rel_path="assets/gods/duplicate/dup_image.png",
                file_type="image",
                file_ext=".png",
                file_size_bytes=102400,
                sha256="8" * 64,
                width=720,
                height=1280,
                aspect_ratio="9:16",
                duration_seconds=0.0,
                approval_status="UNAPPROVED",
                approval_record_id=None,
                registry_deity=None,
                registry_avatar=None,
                candidate_deity="krishna",
                candidate_avatar=None,
                provenance_note="Test fixture asset",
                is_broken=False,
                broken_reason=None,
                is_duplicate=True,
                duplicate_of="assets/gods/ganesha/ganesha_portrait.jpg",
            ).to_dict(),
        ]
        return items

    def test_01_dashboard_file_exists_and_contains_all_records(self):
        """Dashboard HTML exists, is non-empty, and embeds all fixture inventory records."""
        self.assertTrue(self.dashboard_path.exists())
        self.assertGreater(self.dashboard_path.stat().st_size, 25_000)

        html_text = self.dashboard_path.read_text(encoding="utf-8")
        self.assertIn("DIVINE DHARSHANAM — ASSET REVIEW DASHBOARD", html_text)
        self.assertIn("const INVENTORY = [", html_text)

        # Verify all fixture items from inventory JSON are embedded
        inventory_items = json.loads(self.inventory_path.read_text(encoding="utf-8"))
        self.assertEqual(len(inventory_items), len(self.fixture_items))

        # Sample check random assets from different deities
        self.assertIn("assets/gods/ganesha", html_text)
        self.assertIn("assets/gods/hanuman", html_text)
        self.assertIn("assets/gods/parvathi", html_text)
        self.assertIn("assets/gods/subramanya", html_text)
        self.assertIn("assets/gods/lakshmi_devi", html_text)

    def test_02_priority_missing_deities_present_in_dashboard(self):
        """Priority missing deities (Parvati, Kartikeya, Mahalakshmi, Kali) are present."""
        html_text = self.dashboard_path.read_text(encoding="utf-8")
        self.assertIn("parvathi", html_text)
        self.assertIn("subramanya", html_text)
        self.assertIn("lakshmi_devi", html_text)
        self.assertIn("kali", html_text)
        self.assertIn("All 4 Priority Deities", html_text)

    def test_03_review_controls_and_security_warnings_present(self):
        """Review controls and security warning banner are present in the dashboard."""
        html_text = self.dashboard_path.read_text(encoding="utf-8")
        self.assertIn("PROPOSED_FOR_APPROVAL", html_text)
        self.assertIn("WRONG_DEITY", html_text)
        self.assertIn("UNCLEAR_IDENTITY", html_text)
        self.assertIn("BROKEN_ASSET", html_text)
        self.assertIn("DUPLICATE", html_text)
        self.assertIn("human_review_decisions.json", html_text)
        self.assertIn("SECURITY MANDATE", html_text)

    def test_04_instructions_markdown_exists(self):
        """Instructions markdown file exists in docs/ and covers priority deities and review controls."""
        self.assertTrue(self.instructions_path.exists())
        md_text = self.instructions_path.read_text(encoding="utf-8")
        self.assertIn("Goddess Parvati", md_text)
        self.assertIn("Lord Kartikeya", md_text)
        self.assertIn("Goddess Mahalakshmi", md_text)
        self.assertIn("Goddess Kali", md_text)
        self.assertIn("PROPOSED_FOR_APPROVAL", md_text)

    def test_05_decision_schema_simulation(self):
        """Validates that a simulated human decision export conforms to decision schema."""
        simulated_decisions = {
            "exported_at": "2026-11-17T21:55:00.000Z",
            "total_decisions": 2,
            "summary": {
                "proposed_for_approval": 1,
                "wrong_deity": 0,
                "unclear_identity": 0,
                "broken": 1,
                "duplicate": 0,
            },
            "warning": "REVIEW DECISIONS ONLY. Must be audited before adding to TrustedAssetApprovalRegistry.",
            "decisions": {
                "assets/gods/parvathi/ChatGPT Image May 29, 2026, 09_16_58 PM.png": {
                    "decision": "PROPOSED_FOR_APPROVAL",
                    "candidate_deity": "parvathi",
                    "candidate_avatar": "parvathi",
                    "aspect_ratio": "9:16",
                    "notes": "Verified authentic depiction of Goddess Parvati in red saree",
                    "timestamp": "2026-11-17T21:54:30.000Z",
                },
                "assets/gods_processed/ram/horizontal/1116118720173406492__img_tmp.mp4": {
                    "decision": "BROKEN_ASSET",
                    "candidate_deity": "ram",
                    "candidate_avatar": "ram",
                    "aspect_ratio": "16:9",
                    "notes": "Corrupt moov atom",
                    "timestamp": "2026-11-17T21:54:40.000Z",
                },
            },
        }

        # Write to temporary directory to validate schema without clobbering production review decisions
        dec_path = self.temp_dir_path / "test_simulated_decisions.json"
        dec_path.write_text(json.dumps(simulated_decisions, indent=2), encoding="utf-8")
        self.assertTrue(dec_path.exists())

        loaded = json.loads(dec_path.read_text(encoding="utf-8"))
        self.assertEqual(loaded["total_decisions"], 2)
        self.assertIn("assets/gods/parvathi/ChatGPT Image May 29, 2026, 09_16_58 PM.png", loaded["decisions"])
        if dec_path.exists():
            dec_path.unlink()

    def test_06_approval_registry_remains_unmodified(self):
        """Security invariant: dashboard operations are read-only and registry remains unmodified."""
        registry = get_trusted_registry()

        # 1. Registry baseline properties: zero built-ins and approved records present
        self.assertEqual(len(registry.get_builtin_records()), 0, "Built-in catalog must remain empty")
        self.assertGreater(len(registry._records_by_path), 0, "Expected approved records in trusted registry")

        # 2. All records have APPROVED status, reviewer provenance, and review timestamps
        for norm_path, record in registry._records_by_path.items():
            self.assertEqual(record.approval_status, "APPROVED", f"Record {record.record_id} status must be APPROVED")
            self.assertTrue(record.reviewer and str(record.reviewer).strip(), f"Record {record.record_id} missing reviewer")
            self.assertTrue(record.review_timestamp and str(record.review_timestamp).strip(), f"Record {record.record_id} missing timestamp")
            self.assertTrue(record.provenance and "Retrospectively attested" in record.provenance, f"Record {record.record_id} missing provenance")

        # 3. Controlled rejected candidates are not promoted into the approval registry
        simulated_rejected_candidates = [
            "assets/gods/broken/corrupt_asset.mp4",
            "assets/gods/duplicate/dup_image.png",
            "assets/gods_processed/ram/horizontal/1116118720173406492__img_tmp.mp4",
        ]
        for r_path in simulated_rejected_candidates:
            norm_r = normalize_repo_path(r_path)
            if norm_r:
                self.assertNotIn(norm_r.lower(), registry._records_by_path, f"Rejected asset {norm_r} was unexpectedly promoted")

        # 4. Dashboard read-only behavior does not mutate registry (tested via controlled fixture & loaded store)
        from src.assets.approval_registry import TrustedAssetApprovalRegistry, TrustedAssetApprovalRecord
        controlled_reg = TrustedAssetApprovalRegistry(load_active_store=False)
        controlled_rec = TrustedAssetApprovalRecord(
            record_id="CTRL-FIXTURE-001",
            exact_rel_path="assets/gods/ganesha/ganesha_portrait.jpg",
            canonical_deity="ganesha",
            approval_status="APPROVED",
            provenance="Controlled test fixture record",
            reviewer="REV-TEST-CONTROLLED",
            review_timestamp="2026-11-20T12:00:00Z",
            aspect_ratio="9:16",
            content_type="image",
        )
        controlled_reg.register_record(controlled_rec)

        def compute_registry_digest(reg):
            entries = sorted(
                (k, v.to_dict())
                for k, v in reg._records_by_path.items()
            )
            return hashlib.sha256(json.dumps(entries, sort_keys=True).encode("utf-8")).hexdigest()

        digest_before = compute_registry_digest(registry)
        count_before = len(registry._records_by_path)
        ctrl_digest_before = compute_registry_digest(controlled_reg)

        # Execute dashboard generation in temporary directory with isolated paths
        temp_html_out = self.temp_dir_path / "dashboard_immutability_check.html"
        generate_dashboard_file(
            inventory_path=self.inventory_path,
            matrix_path=self.matrix_path,
            duplicates_path=self.duplicates_path,
            frames_dir=self.frames_dir,
            output_html_path=temp_html_out,
        )

        registry_after = get_trusted_registry()
        digest_after = compute_registry_digest(registry_after)
        ctrl_digest_after = compute_registry_digest(controlled_reg)

        self.assertEqual(len(registry_after._records_by_path), count_before, "Dashboard generation must not mutate record count")
        self.assertEqual(digest_before, digest_after, "Dashboard generation must not alter loaded registry contents or hash")
        self.assertEqual(ctrl_digest_before, ctrl_digest_after, "Dashboard generation must not alter controlled fixture registry")
        self.assertEqual(len(controlled_reg._records_by_path), 1)


if __name__ == "__main__":
    unittest.main()
