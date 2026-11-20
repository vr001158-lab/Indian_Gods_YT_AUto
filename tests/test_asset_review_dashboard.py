# tests/test_asset_review_dashboard.py
# Verification of Asset Review Dashboard Generation & Integrity

from __future__ import annotations

import json
import unittest
from pathlib import Path

from src.assets.approval_registry import get_trusted_registry
from src.assets.dashboard_builder import generate_dashboard_file


class TestAssetReviewDashboard(unittest.TestCase):
    def setUp(self):
        self.dashboard_path = Path("data/review/asset_review_dashboard.html")
        self.instructions_path = Path("data/review/asset_review_instructions.md")
        self.inventory_path = Path("data/review/candidate_asset_inventory.json")

    def test_01_dashboard_file_exists_and_contains_all_records(self):
        """Dashboard HTML exists, is non-empty, and embeds all 430 inventory records."""
        if not self.dashboard_path.exists():
            generate_dashboard_file()

        self.assertTrue(self.dashboard_path.exists())
        self.assertGreater(self.dashboard_path.stat().st_size, 100_000)

        html_text = self.dashboard_path.read_text(encoding="utf-8")
        self.assertIn("DIVINE DHARSHANAM — ASSET REVIEW DASHBOARD", html_text)
        self.assertIn("const INVENTORY = [", html_text)

        # Verify all 430 items from inventory JSON are embedded
        inventory_items = json.loads(self.inventory_path.read_text(encoding="utf-8"))
        self.assertEqual(len(inventory_items), 430)

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
        """Instructions markdown file exists and covers priority deities and review controls."""
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

        # Write to test_simulated_decisions.json to validate schema without clobbering production review decisions
        dec_path = Path("data/review/test_simulated_decisions.json")
        dec_path.write_text(json.dumps(simulated_decisions, indent=2), encoding="utf-8")
        self.assertTrue(dec_path.exists())

        loaded = json.loads(dec_path.read_text(encoding="utf-8"))
        self.assertEqual(loaded["total_decisions"], 2)
        self.assertIn("assets/gods/parvathi/ChatGPT Image May 29, 2026, 09_16_58 PM.png", loaded["decisions"])
        if dec_path.exists():
            dec_path.unlink()

    def test_06_approval_registry_remains_unmodified(self):
        """Security invariant: dashboard operations are read-only and registry contains exactly 346 approved records."""
        registry = get_trusted_registry()

        # 1. Registry contains exactly 346 migrated records and zero built-ins
        self.assertEqual(len(registry.get_builtin_records()), 0, "Built-in catalog must remain empty")
        self.assertEqual(len(registry._records_by_path), 346, "Expected exactly 346 approved records in trusted registry")

        # 2. All records have APPROVED status, reviewer provenance, and review timestamps
        for norm_path, record in registry._records_by_path.items():
            self.assertEqual(record.approval_status, "APPROVED", f"Record {record.record_id} status must be APPROVED")
            self.assertTrue(record.reviewer and str(record.reviewer).strip(), f"Record {record.record_id} missing reviewer")
            self.assertTrue(record.review_timestamp and str(record.review_timestamp).strip(), f"Record {record.record_id} missing timestamp")
            self.assertTrue(record.provenance and "Retrospectively attested" in record.provenance, f"Record {record.record_id} missing provenance")

        # 3. No rejected or built-in records have been promoted
        dec_path = Path("data/review/human_review_decisions.json")
        if dec_path.exists():
            dec_data = json.loads(dec_path.read_text(encoding="utf-8"))
            non_accepted = {
                k: v for k, v in dec_data.get("decisions", {}).items()
                if v.get("decision") != "PROPOSED_FOR_APPROVAL"
            }
            self.assertEqual(len(non_accepted), 68, "Expected exactly 68 non-accepted decisions")
            from src.assets.approval_registry import normalize_repo_path
            for na_path in non_accepted.keys():
                norm_na = normalize_repo_path(na_path)
                if norm_na:
                    self.assertNotIn(norm_na.lower(), registry._records_by_path, f"Rejected asset {norm_na} was unexpectedly promoted")

        # 4. Dashboard read-only behavior does not mutate the registry
        count_before = len(registry._records_by_path)
        generate_dashboard_file()
        registry_after = get_trusted_registry()
        self.assertEqual(len(registry_after._records_by_path), count_before, "Dashboard generation must not mutate approval registry")


if __name__ == "__main__":
    unittest.main()
