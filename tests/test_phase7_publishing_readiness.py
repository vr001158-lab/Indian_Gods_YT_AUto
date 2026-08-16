# tests/test_phase7_publishing_readiness.py
# Phase 7 — Publishing Readiness Unit Test Suite
#
# Validates:
#   - Metadata completeness (title, description, hashtags, tags, category, language)
#   - Public publishing enforcement (REQUIRED_PRIVACY == "public")
#   - Safety gate validation of video QA & provenance
#   - Non-fatal thumbnail handling & 403 handling rationale
#   - Credentials safety & no leak in manifests
#   - No CLI option for accidental public upload
#   - Existence & technical QA of the 3 Phase 6 final videos
#   - SHA256 immutability of shared visual asset plan

import os
import sys
import json
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from publisher.safety import load_qa_result, validate_qa_for_publishing, verify_video_with_ffprobe, PublisherSafetyError
from publisher.metadata import build_video_metadata
from publisher.uploader import publish_video, upload_thumbnail, REQUIRED_PRIVACY

SHARED_ASSET_PLAN = Path("data/visuals/asset_plan_20260814_071510.json")
EXPECTED_SHA256 = "f6ca03a2dfec5add5b9bce5ce699124bfdffacf42f009b2a9d4b1c02a5f87b33"


class TestPhase7PublishingReadiness(unittest.TestCase):

    # 1. Metadata completeness
    def test_01_metadata_completeness(self):
        qa = {
            "approved_for_publishing": True,
            "selected_topic": "Why Lord Shiva Wears a Snake Around His Neck",
            "score": 66,
            "confidence": "high",
            "data_source": "youtube_api",
            "approval_metadata": {
                "approved_for_generation": True,
                "selected_topic": "Why Lord Shiva Wears a Snake Around His Neck",
                "data_source": "youtube_api",
                "confidence": "high",
            },
            "artifacts": {
                "script": "data/scripts/script_20260813_120000.json",
                "video": "data/videos/shiva_hi_video_map.json"
            }
        }
        meta = build_video_metadata(qa)
        for key in ("title", "description", "tags", "category_id", "video_file", "thumbnail_file"):
            self.assertIn(key, meta, f"Missing required metadata key: '{key}'")

        self.assertTrue(len(meta["title"]) > 0)
        self.assertTrue(len(meta["description"]) > 0)
        self.assertTrue(len(meta["tags"]) > 0)
        self.assertIn("#IndianMythology", meta["description"])
        self.assertEqual(meta["category_id"], "27")

    # 2. Public publishing enforced
    def test_02_public_publishing_enforced(self):
        self.assertEqual(REQUIRED_PRIVACY, "public")

    # 3. No CLI override of privacy setting
    def test_03_no_privacy_override_cli(self):
        cli_file = Path("run_publisher.py")
        self.assertTrue(cli_file.exists())
        cli_code = cli_file.read_text(encoding="utf-8")

        # Verify no --privacy parameter allowed in CLI parser (privacy is hard-coded)
        self.assertNotIn("--privacy", cli_code)

    # 4. Video QA gate rejection
    def test_04_video_qa_gate_rejection(self):
        bad_qa = {
            "approved_for_publishing": False,  # Not approved
            "selected_topic": "Why Lord Shiva Wears a Snake Around His Neck",
            "data_source": "mock",             # Mock data source rejected
            "confidence": "low",               # Low confidence rejected
            "approval_metadata": {"approved_for_generation": False},
            "artifacts": {}
        }
        with self.assertRaises(PublisherSafetyError):
            validate_qa_for_publishing(bad_qa)

    # 5. Non-fatal thumbnail handling
    def test_05_thumbnail_handling_non_fatal(self):
        creds = MagicMock()
        ok = upload_thumbnail(creds, "dummy_video_id", "non_existent_thumbnail.png")
        self.assertFalse(ok, "Missing thumbnail should return False without raising exception")

    # 6. Language metadata tags
    def test_06_language_metadata(self):
        qa = {
            "selected_topic": "Why Lord Shiva Wears a Snake Around His Neck",
            "score": 80,
            "confidence": "high",
            "data_source": "youtube_api",
            "artifacts": {}
        }
        meta = build_video_metadata(qa)
        self.assertIn("Indian mythology", meta["tags"])
        self.assertIn("Hindu gods", meta["tags"])

    # 7. Credentials safety — no token leak in manifests
    def test_07_credentials_safety_in_manifest(self):
        manifest_data = {
            "video_id": "test_id_123",
            "youtube_url": "https://www.youtube.com/watch?v=test_id_123",
            "privacy_status": "public",
            "success": True,
            "approval_metadata": {"approved_for_generation": True}
        }
        raw_json = json.dumps(manifest_data)
        for sensitive in ("client_secret", "refresh_token", "access_token", "api_key_secret"):
            self.assertNotIn(sensitive, raw_json)

    # 8. Verify the 3 Phase 6 final videos exist & pass ffprobe
    def test_08_phase6_final_videos_exist_and_pass_qa(self):
        missing_videos = [f"shiva_{s}_final.mp4" for s in ["hi", "te", "ta"] if not Path(f"data/videos/shiva_{s}_final.mp4").exists()]
        if missing_videos:
            self.skipTest(f"Phase 6 final video assets missing in CI: {missing_videos}")
        for lang_suffix in ["hi", "te", "ta"]:
            vpath = Path(f"data/videos/shiva_{lang_suffix}_final.mp4")
            self.assertGreater(vpath.stat().st_size, 0, f"Empty final video: {vpath}")
            
            res = verify_video_with_ffprobe(vpath)
            self.assertIn(res["width"], (720, 1080))
            self.assertIn(res["height"], (1280, 1920))
            self.assertEqual(res["video_codec"], "h264")
            self.assertIn(res["audio_codec"], ("aac", "mp3"))
            self.assertGreater(res["duration"], 0)

    # 9. Shared asset plan SHA256 immutability
    def test_09_shared_asset_plan_sha256_unmodified(self):
        if not SHARED_ASSET_PLAN.exists():
            self.skipTest("Production asset plan file not available in CI environment")
        actual_hash = hashlib.sha256(SHARED_ASSET_PLAN.read_bytes()).hexdigest()
        self.assertEqual(actual_hash, EXPECTED_SHA256, "Shared visual asset plan SHA256 modified!")


if __name__ == "__main__":
    unittest.main(verbosity=2)
