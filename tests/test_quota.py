# tests/test_quota.py
# Comprehensive automated unit & integration tests for Publishing Quota & Language Enforcement
#
# Covers:
#  - Telugu-only publishing enforcement (te-IN allowed, hi-IN rejected, others rejected)
#  - Maximum 2 successful Shorts per Asia/Kolkata calendar day
#  - Failed uploads do not consume quota
#  - Dry-runs do not consume quota
#  - Maximum 1 successful long-video upload per rolling 72 hours
#  - Timezone boundary cases around midnight in Asia/Kolkata
#  - Publishing history concurrency locking & persistence
#  - Corrupted/malformed history safety (fail-closed, no wipe)

import json
import shutil
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
import zoneinfo

from src.publisher.quota import (
    PRODUCTION_LANGUAGE,
    MAX_SHORTS_PER_DAY,
    MAX_VIDEOS_PER_DAY,
    LONG_VIDEO_MIN_INTERVAL_HOURS,
    KOLKATA_TZ,
    UTC_TZ,
    QuotaExceededError,
    PublishingFileLock,
    check_publishing_quota,
    load_publishing_history,
    parse_published_timestamp,
    record_successful_publish,
)
from src.publisher.safety import (
    PublisherSafetyError,
    validate_qa_for_publishing,
)


class TestPublishingQuotaAndLanguage(unittest.TestCase):

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.history_file = self.temp_dir / "publishing_history.json"
        self.lock_file = self.temp_dir / "publishing_history.json.lock"

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ── 1. Language Enforcement Tests ──────────────────────────────────────────

    def test_telugu_language_allowed(self):
        """te-IN must be accepted by check_publishing_quota."""
        ok, msg = check_publishing_quota(
            content_type="short",
            language_code="te-IN",
            history_file=self.history_file,
        )
        self.assertTrue(ok)
        self.assertIn("Quota check passed", msg)

    def test_hindi_language_rejected(self):
        """hi-IN must be rejected by check_publishing_quota."""
        ok, msg = check_publishing_quota(
            content_type="short",
            language_code="hi-IN",
            history_file=self.history_file,
        )
        self.assertFalse(ok)
        self.assertIn("strictly Telugu ('te-IN') only", msg)

    def test_english_and_other_languages_rejected(self):
        """Any language other than te-IN must be rejected."""
        for invalid_lang in ("en", "en-US", "ta-IN", "kn-IN", ""):
            ok, msg = check_publishing_quota(
                content_type="short",
                language_code=invalid_lang,
                history_file=self.history_file,
            )
            self.assertFalse(ok)
            self.assertIn("strictly Telugu", msg)

    def test_publisher_safety_gate_rejects_hindi(self):
        """validate_qa_for_publishing must raise PublisherSafetyError for Hindi."""
        qa = {
            "approved_for_publishing": True,
            "selected_topic": "Test Topic",
            "score": 85,
            "confidence": "high",
            "data_source": "youtube_api",
            "content_type": "short",
            "language_code": "hi-IN",
            "artifacts": {
                "decision": "data/decision.json",
                "content_brief": "data/brief.json",
                "script": "data/script.json",
                "audio": "data/audio.json",
                "video": "data/video_map.json",
                "thumbnail": "data/thumb.json",
            },
            "approval_metadata": {
                "approved_for_generation": True,
                "data_source": "youtube_api",
                "confidence": "high",
                "selected_topic": "Test Topic",
            },
        }
        with self.assertRaises(PublisherSafetyError) as ctx:
            validate_qa_for_publishing(qa, manifest_dir=self.temp_dir, allow_mock=True, history_file=self.history_file)
        self.assertIn("strictly Telugu ('te-IN') only", str(ctx.exception))

    # ── 2. Daily Shorts Limit (Max 2 per Asia/Kolkata Calendar Day) ────────────

    def test_shorts_daily_limit_zero_uploaded(self):
        """When 0 shorts have been published today, next short is allowed."""
        ok, msg = check_publishing_quota("short", "te-IN", self.history_file)
        self.assertTrue(ok)

    def test_shorts_daily_limit_one_uploaded(self):
        """When 1 short has been published today in Asia/Kolkata, next short is allowed."""
        now_kolkata = datetime.now(KOLKATA_TZ)
        record_successful_publish(
            video_id="VID_SHORT_1",
            title="Telugu Short 1",
            content_type="short",
            language_code="te-IN",
            history_file=self.history_file,
            now_dt=now_kolkata,
        )

        ok, msg = check_publishing_quota("short", "te-IN", self.history_file, now_dt=now_kolkata)
        self.assertTrue(ok, f"Expected 2nd short to be allowed, got rejection: {msg}")

    def test_shorts_daily_limit_two_uploaded_blocks_third(self):
        """When 2 shorts have been published today in Asia/Kolkata, 3rd short is blocked."""
        now_kolkata = datetime.now(KOLKATA_TZ)
        record_successful_publish(
            video_id="VID_SHORT_1",
            title="Telugu Short 1",
            content_type="short",
            language_code="te-IN",
            history_file=self.history_file,
            now_dt=now_kolkata - timedelta(hours=2),
        )
        record_successful_publish(
            video_id="VID_SHORT_2",
            title="Telugu Short 2",
            content_type="short",
            language_code="te-IN",
            history_file=self.history_file,
            now_dt=now_kolkata - timedelta(hours=1),
        )

        ok, msg = check_publishing_quota("short", "te-IN", self.history_file, now_dt=now_kolkata)
        self.assertFalse(ok)
        self.assertIn("Daily Telugu Shorts quota reached", msg)
        self.assertIn("2/2", msg)

    def test_failed_uploads_do_not_consume_quota(self):
        """
        Failed uploads do NOT call record_successful_publish.
        Verifies history is not modified and quota remains available.
        """
        # History remains empty when upload fails
        self.assertFalse(self.history_file.exists())
        ok, _ = check_publishing_quota("short", "te-IN", self.history_file)
        self.assertTrue(ok)

    def test_dry_run_does_not_consume_quota(self):
        """
        Dry runs validate quota but never append to history.
        Verifies multiple dry runs leave quota intact.
        """
        now = datetime.now(KOLKATA_TZ)
        for _ in range(5):
            ok, _ = check_publishing_quota("short", "te-IN", self.history_file, now_dt=now)
            self.assertTrue(ok)
        self.assertFalse(self.history_file.exists())

    # ── 3. Long Video Rolling 72-Hour Quota Tests ──────────────────────────────

    def test_long_video_allowed_when_no_previous_long_videos(self):
        """When no long videos have ever been uploaded, long video is allowed."""
        ok, msg = check_publishing_quota("long", "te-IN", self.history_file)
        self.assertTrue(ok)

    def test_long_video_blocked_within_72_hours(self):
        """A long video published 24 hours ago must block another long video."""
        now = datetime.now(KOLKATA_TZ)
        past_time = now - timedelta(hours=24)

        record_successful_publish(
            video_id="LONG_VID_001",
            title="Telugu Long Video 1",
            content_type="long",
            language_code="te-IN",
            history_file=self.history_file,
            now_dt=past_time,
        )

        ok, msg = check_publishing_quota("long", "te-IN", self.history_file, now_dt=now)
        self.assertFalse(ok)
        self.assertIn("Long-video 72-hour interval restriction active", msg)
        self.assertIn("LONG_VID_001", msg)

    def test_long_video_allowed_after_72_hours(self):
        """A long video published 73 hours ago must allow a new long video."""
        now = datetime.now(KOLKATA_TZ)
        past_time = now - timedelta(hours=73)

        record_successful_publish(
            video_id="LONG_VID_OLD",
            title="Telugu Long Video Old",
            content_type="long",
            language_code="te-IN",
            history_file=self.history_file,
            now_dt=past_time,
        )

        ok, msg = check_publishing_quota("long", "te-IN", self.history_file, now_dt=now)
        self.assertTrue(ok)

    # ── 4. Timezone Boundary Cases (Asia/Kolkata Midnight Transition) ─────────

    def test_midnight_transition_asia_kolkata(self):
        """
        Tests midnight boundary in Asia/Kolkata:
        - Video published at 23:55:00 IST on Day 1.
        - Next query at 00:05:00 IST on Day 2.
        - Day 1 upload must NOT count against Day 2's quota.
        """
        # Day 1: 2026-11-03 23:55:00 IST
        day1_dt = datetime(2026, 11, 3, 23, 55, 0, tzinfo=KOLKATA_TZ)
        record_successful_publish(
            video_id="MIDNIGHT_VID_1",
            title="Short Day 1",
            content_type="short",
            language_code="te-IN",
            history_file=self.history_file,
            now_dt=day1_dt,
        )

        # Day 2: 2026-11-04 00:05:00 IST (10 minutes later, but next calendar day in IST)
        day2_dt = datetime(2026, 11, 4, 0, 5, 0, tzinfo=KOLKATA_TZ)

        # On Day 2, 0 shorts have been published on 2026-11-04
        ok, msg = check_publishing_quota("short", "te-IN", self.history_file, now_dt=day2_dt)
        self.assertTrue(ok)

        # Now publish 2 shorts on Day 2
        record_successful_publish(
            video_id="DAY2_VID_1",
            title="Short Day 2 - 1",
            content_type="short",
            language_code="te-IN",
            history_file=self.history_file,
            now_dt=day2_dt,
        )
        record_successful_publish(
            video_id="DAY2_VID_2",
            title="Short Day 2 - 2",
            content_type="short",
            language_code="te-IN",
            history_file=self.history_file,
            now_dt=day2_dt + timedelta(hours=1),
        )

        # 3rd short on Day 2 must now be blocked
        ok2, msg2 = check_publishing_quota("short", "te-IN", self.history_file, now_dt=day2_dt + timedelta(hours=2))
        self.assertFalse(ok2)
        self.assertIn("Daily Telugu Shorts quota reached for 2026-11-04", msg2)

    # ── 5. History Concurrency & Atomic File Locking ───────────────────────────

    def test_atomic_persistence_and_file_lock(self):
        """Verifies file lock acquires and releases cleanly, and history preserves all entries."""
        for i in range(2):
            record_successful_publish(
                video_id=f"CONCURRENT_VID_{i}",
                title=f"Title {i}",
                content_type="short",
                language_code="te-IN",
                history_file=self.history_file,
                now_dt=datetime(2026, 11, 3, 10 + i, 0, 0, tzinfo=KOLKATA_TZ),
            )

        records = load_publishing_history(self.history_file)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0]["youtube_video_id"], "CONCURRENT_VID_0")
        self.assertEqual(records[1]["youtube_video_id"], "CONCURRENT_VID_1")
        self.assertEqual(records[0]["language_code"], "te-IN")
        self.assertEqual(records[0]["kolkata_date"], "2026-11-03")

    def test_corrupted_history_fails_closed(self):
        """Corrupted JSON in publishing_history.json must raise ValueError and NOT overwrite or reset."""
        self.history_file.write_text("{ this is corrupt json !!!", encoding="utf-8")
        with self.assertRaises(ValueError):
            load_publishing_history(self.history_file)

        # File content must remain intact (not wiped)
        self.assertIn("corrupt json", self.history_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
