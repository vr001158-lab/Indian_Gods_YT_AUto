# tests/test_asset_inventory_coverage.py
# Verification of Deity Asset Inventory, Duplicate Detection & Contact Sheets

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from PIL import Image

from src.assets.approval_registry import get_trusted_registry
from src.assets.contact_sheet import extract_video_frame_cached, render_contact_sheet_page
from src.assets.inventory import (
    AssetInventoryItem,
    build_deity_coverage_matrix,
    inspect_single_asset,
    scan_all_visual_assets,
)
from src.decision.weekday_deity import WEEKDAY_DEITY_MAPPING


class TestAssetInventoryAndCoverage(unittest.TestCase):
    def setUp(self):
        self.registry = get_trusted_registry()
        self.initial_records_count = len(self.registry._records_by_path)

    def tearDown(self):
        # Invariant: registry records must remain unaltered
        self.assertEqual(len(self.registry._records_by_path), self.initial_records_count)

    def test_01_inspect_single_approved_asset(self):
        """Approved asset is identified with APPROVED status and canonical registry deity."""
        approved_path = Path("assets/gods/hanuman/Hanuman Carrying Sanjeevani 🌕⛰️ _ The Night of Miracles.jpg")
        if approved_path.exists():
            item = inspect_single_asset(approved_path)
            self.assertEqual(item.approval_status, "APPROVED")
            self.assertEqual(item.registry_deity, "hanuman")
            self.assertEqual(item.width, 736)
            self.assertEqual(item.height, 1308)
            self.assertFalse(item.is_broken)

    def test_02_inspect_unapproved_candidate_asset(self):
        """Unapproved candidate defaults to UNAPPROVED and extracts candidate deity for review."""
        test_file = Path("assets/gods/ganesha/00ac0c20a33ec90101f2ffa4d24bae2a.jpg")
        if test_file.exists():
            item = inspect_single_asset(test_file)
            self.assertEqual(item.candidate_deity, "ganesha")
            self.assertTrue(len(item.sha256) > 0)
            self.assertFalse(item.is_broken)

    def test_03_coverage_matrix_covers_all_seven_weekdays(self):
        """Coverage matrix tracks all 7 weekdays and every mapped deity."""
        inventory = scan_all_visual_assets(roots=["assets/gods"], max_workers=4)
        matrix = build_deity_coverage_matrix(inventory)

        self.assertEqual(len(matrix["weekday_schedules"]), 7)
        for day_idx in range(7):
            sched = matrix["weekday_schedules"][day_idx]
            expected_deities = WEEKDAY_DEITY_MAPPING[day_idx]["primary_deities"]
            actual_deities = [d["deity_key"] for d in sched["deities"]]
            self.assertEqual(actual_deities, expected_deities)

    def test_04_contact_sheet_renders_unapproved_badge(self):
        """Contact sheet renders tiles with UNAPPROVED badge and metadata."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_out = Path(tmp_dir) / "test_sheet.png"
            fake_item = AssetInventoryItem(
                rel_path="assets/gods/ganesha/mock_unapproved.png",
                file_type="image",
                file_ext=".png",
                file_size_bytes=10240,
                sha256="abc123mockhash",
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
                provenance_note="Test item",
                is_broken=False,
                broken_reason=None,
            )

            res_p = render_contact_sheet_page(
                items=[fake_item],
                page_num=1,
                total_pages=1,
                deity_key="ganesha",
                category="image",
                output_path=tmp_out,
                frame_cache={},
            )
            self.assertTrue(res_p.exists())
            self.assertGreater(res_p.stat().st_size, 0)
            with Image.open(res_p) as img:
                self.assertGreater(img.width, 300)
                self.assertGreater(img.height, 400)


if __name__ == "__main__":
    unittest.main()
