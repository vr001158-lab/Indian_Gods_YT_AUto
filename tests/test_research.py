"""
tests/test_research.py
Hardened v0.2 — 9 test scenarios for the research engine.
All tests run without any network or YouTube API access.
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure UTF-8 stdout
import io
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.getcwd())

import src.research.collector as collector_mod
import src.research.scorer   as scorer_mod
import src.research.dedup    as dedup_mod
import src.research.report   as report_mod
from src.research.collector import ResearchCollector, CACHE_VERSION
from src.research.scorer    import TopicScorer
from src.research.dedup     import deduplicate_topics


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_video(views=100_000, age_days=200):
    pub = (datetime.date.today() - datetime.timedelta(days=age_days)).isoformat() + "T00:00:00Z"
    return {"video_id": "v1", "title": "Test", "channel": "Ch", "published_at": pub,
            "views": views, "likes": 5000, "url": "https://example.com/v1"}

def _mock_festival(verified=True, days=30):
    return {
        "festival_name": "Test Festival",
        "days_remaining": days,
        "verified": verified,
        "calendar_basis": "test",
        "source": "test",
    }

def _make_collector(tmp_path, creds=None, max_calls=10, ttl=24):
    c = collector_mod.ResearchCollector(creds=creds, max_search_calls=max_calls, cache_ttl_hours=ttl)
    # Redirect cache file to temp dir
    c._cache_raw = {"_version": CACHE_VERSION}
    collector_mod.CACHE_FILE = tmp_path / "api_cache.json"
    return c


# ─────────────────────────────────────────────────────────────────────────────
class TestQuotaBudgeting(unittest.TestCase):
    """TEST 1 — Quota budget is enforced; engine never exceeds max_search_calls."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        collector_mod.CACHE_FILE = self.tmp / "cache.json"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        collector_mod.CACHE_FILE = Path("data/research/api_cache.json")

    def test_quota_exhausted_returns_offline(self):
        # Budget = 0 from the start; every call must return offline immediately
        c = ResearchCollector(creds=None, max_search_calls=0)
        c._cache_raw = {"_version": CACHE_VERSION}
        result = c.search_youtube_videos("Why Ganesha has broken tusk")
        self.assertEqual(result["data_source"], "offline",
                         "Should return offline when budget is 0")
        self.assertTrue(result["is_mock"])
        self.assertEqual(c._search_calls_used, 0, "No API calls should have been made")

    def test_quota_counter_increments_on_mock_api(self):
        """search_calls_used should NOT increment for mock/no-creds path."""
        c = ResearchCollector(creds=None, max_search_calls=5)
        c._cache_raw = {"_version": CACHE_VERSION}
        c.search_youtube_videos("test topic")
        self.assertEqual(c._search_calls_used, 0,
                         "Mock/offline path must not consume quota units")


# ─────────────────────────────────────────────────────────────────────────────
class TestCacheTTL(unittest.TestCase):
    """TEST 2 — Cache TTL: fresh entries are reused; stale entries are flagged."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.orig = collector_mod.CACHE_FILE
        collector_mod.CACHE_FILE = self.tmp / "cache.json"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        collector_mod.CACHE_FILE = self.orig

    def test_fresh_cache_hit(self):
        c = ResearchCollector(creds=None, max_search_calls=10, cache_ttl_hours=24)
        c._cache_raw = {"_version": CACHE_VERSION}
        query = "Shiva snake neck"
        r1 = c.search_youtube_videos(query)
        self.assertTrue((self.tmp / "cache.json").exists(), "Cache file must be written")

        # Second instance — should return from cache, not re-run mock generation
        c2 = ResearchCollector(creds=None, max_search_calls=10, cache_ttl_hours=24)
        r2 = c2.search_youtube_videos(query)
        self.assertIn(r2["data_source"], ("mock", "cached_youtube_api"),
                      "Cached result should be returned for same query within TTL")
        self.assertEqual(r1["videos"], r2["videos"], "Cached content must match original")

    def test_stale_cache_is_flagged(self):
        c = ResearchCollector(creds=None, max_search_calls=10, cache_ttl_hours=24)
        c._cache_raw = {"_version": CACHE_VERSION}
        query = "Hanuman sindoor"
        # Manually insert an expired entry (timestamp 48h ago)
        old_ts = (datetime.datetime.utcnow() - datetime.timedelta(hours=48)).isoformat()
        c._cache_raw[query] = {
            "query": query,
            "timestamp": old_ts,
            "cache_version": CACHE_VERSION,
            "source": "youtube_api",
            "api_method": "search.list",
            "is_mock": False,
            "stale": False,
            "result": [_make_video()],
        }
        entry = c._cache_get(query)
        self.assertIsNotNone(entry, "Should return stale entry rather than None")
        self.assertTrue(entry.get("stale"), "Expired entry must be marked stale=True")


# ─────────────────────────────────────────────────────────────────────────────
class TestMockVsRealLabeling(unittest.TestCase):
    """TEST 3 — data_source field correctly distinguishes mock from real data."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.orig = collector_mod.CACHE_FILE
        collector_mod.CACHE_FILE = self.tmp / "cache.json"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        collector_mod.CACHE_FILE = self.orig

    def test_no_creds_gives_mock_label(self):
        c = ResearchCollector(creds=None)
        c._cache_raw = {"_version": CACHE_VERSION}
        r = c.search_youtube_videos("Lakshmi Samudra Manthan")
        self.assertIn(r["data_source"], ("mock", "offline"))
        self.assertTrue(r["is_mock"])

    def test_mock_urls_are_not_real_youtube(self):
        c = ResearchCollector(creds=None)
        c._cache_raw = {"_version": CACHE_VERSION}
        r = c.search_youtube_videos("Narasimha avatar mystery")
        for v in r["videos"]:
            self.assertFalse(
                v["url"].startswith("https://www.youtube.com/"),
                "Mock URLs must NOT use real youtube.com domain"
            )

    def test_confidence_low_for_mock_data(self):
        score = TopicScorer.calculate_score(
            topic_meta={"topic": "Why Ganesha tusk broken"},
            youtube_videos=[_make_video()],
            festival_info=_mock_festival(),
            data_source="mock",
        )
        self.assertEqual(score["confidence"], "low",
                         "Mock data must yield low confidence regardless of video count")


# ─────────────────────────────────────────────────────────────────────────────
class TestUnverifiedFestivalDate(unittest.TestCase):
    """TEST 4 — Unverified festival date halves the relevance contribution."""

    def test_unverified_halves_relevance(self):
        videos = [_make_video(views=200_000)]
        topic  = {"topic": "Why Ganesha tusk broken"}

        score_verified   = TopicScorer.calculate_score(
            topic, videos, _mock_festival(verified=True,  days=10), "mock")
        score_unverified = TopicScorer.calculate_score(
            topic, videos, _mock_festival(verified=False, days=10), "mock")

        self.assertGreater(
            score_verified["relevance_score"],
            score_unverified["relevance_score"],
            "Verified festival should yield higher relevance than unverified"
        )
        # Verified: raw = max(50, 100-10)=90; Unverified: 90*0.5=45
        self.assertEqual(score_unverified["relevance_score"], 45)
        self.assertEqual(score_verified["relevance_score"],   90)

    def test_unverified_flag_propagates_to_candidate(self):
        candidates = report_mod.run_research_pipeline(creds=None, limit=1)
        c = candidates[0]
        # All built-in festivals have verified=False
        self.assertFalse(c["festival_verified"],
                         "Default festivals must carry verified=False")


# ─────────────────────────────────────────────────────────────────────────────
class TestDuplicateTopicGrouping(unittest.TestCase):
    """TEST 5 — Near-duplicate topics are collapsed to a single entry."""

    def test_snake_topic_variants_are_deduplicated(self):
        topics = [
            {"topic": "Why Shiva wears a snake around his neck", "category": "mythology", "deity": "shiva"},
            {"topic": "Why Lord Shiva has a snake", "category": "mythology", "deity": "shiva"},
            {"topic": "The reason Vasuki the snake lives on Shiva", "category": "mythology", "deity": "shiva"},
        ]
        unique = deduplicate_topics(topics)
        self.assertEqual(len(unique), 1,
                         "Three near-duplicate snake-Shiva topics must collapse to one")

    def test_distinct_topics_are_preserved(self):
        topics = [
            {"topic": "Why Ganesha has one broken tusk", "category": "myth", "deity": "ganesha"},
            {"topic": "Why Hanuman covered himself in sindoor", "category": "tradition", "deity": "hanuman"},
            {"topic": "Mysteries of Tirupati Balaji temple wealth", "category": "places", "deity": "vishnu"},
        ]
        unique = deduplicate_topics(topics)
        self.assertEqual(len(unique), 3,
                         "Three distinct topics must all be preserved")


# ─────────────────────────────────────────────────────────────────────────────
class TestContentGapLanguage(unittest.TestCase):
    """TEST 6 — Content gap claims are cautious; no unsupported 'high growth potential' language."""

    FORBIDDEN_PHRASES = [
        "high growth potential",
        "guaranteed",
        "will perform",
        "perfect opportunity",   # removed from v0.2
    ]

    def _scores_for(self, demand, competition, freshness, curiosity, dominant, data_source="mock"):
        return {
            "demand_score":      demand,
            "competition_score": competition,
            "freshness_score":   freshness,
            "curiosity_score":   curiosity,
            "stats":             {"dominant_count": dominant},
        }

    def test_no_guaranteed_language(self):
        for demand, comp, fresh, curio, dom in [
            (80, 85, 70, 75, 0),
            (78, 60, 20, 75, 2),
            (50, 70, 60, 92, 0),
        ]:
            gap = report_mod.analyze_content_gap(
                self._scores_for(demand, comp, fresh, curio, dom),
                data_source="mock"
            )
            for phrase in self.FORBIDDEN_PHRASES:
                self.assertNotIn(phrase.lower(), gap.lower(),
                                 f"Forbidden phrase '{phrase}' found in gap: {gap!r}")

    def test_gap_notes_mock_qualifier(self):
        gap = report_mod.analyze_content_gap(
            self._scores_for(80, 85, 70, 75, 0), data_source="mock"
        )
        self.assertIn("mock data", gap.lower(),
                      "Content gap for mock data must mention it is based on mock data")

    def test_insufficient_evidence_fallback(self):
        gap = report_mod.analyze_content_gap(
            self._scores_for(50, 60, 60, 70, 1), data_source="mock"
        )
        self.assertIn("insufficient evidence", gap.lower())


# ─────────────────────────────────────────────────────────────────────────────
class TestDeterministicScoring(unittest.TestCase):
    """TEST 7 — Identical inputs produce identical scores across multiple calls."""

    def test_score_is_deterministic(self):
        videos = [_make_video(views=250_000, age_days=400)]
        topic  = {"topic": "The Hidden Meaning of Shiva Trishul"}
        fest   = _mock_festival(verified=False, days=50)

        s1 = TopicScorer.calculate_score(topic, videos, fest, "mock")
        s2 = TopicScorer.calculate_score(topic, videos, fest, "mock")
        self.assertEqual(s1, s2, "Scoring must be fully deterministic")

    def test_score_components_all_present(self):
        s = TopicScorer.calculate_score(
            {"topic": "Why Lakshmi chose Vishnu"},
            [_make_video()], _mock_festival(), "mock"
        )
        for key in [
            "score_version", "overall_score", "demand_score", "relevance_score",
            "competition_score", "evergreen_score", "freshness_score",
            "curiosity_score", "long_form_potential", "shorts_potential",
            "confidence", "festival_verified", "stats",
        ]:
            self.assertIn(key, s, f"Score output missing required key: {key}")


# ─────────────────────────────────────────────────────────────────────────────
class TestConfidenceScoring(unittest.TestCase):
    """TEST 8 — Confidence reflects evidence quality, not expected views."""

    def test_mock_source_is_low_confidence(self):
        s = TopicScorer.calculate_score(
            {"topic": "Hanuman sindoor devotion"}, [_make_video()] * 5,
            _mock_festival(), "mock"
        )
        self.assertEqual(s["confidence"], "low")

    def test_real_sparse_is_medium_confidence(self):
        s = TopicScorer.calculate_score(
            {"topic": "Hanuman sindoor devotion"}, [_make_video(), _make_video()],
            _mock_festival(), "youtube_api"
        )
        self.assertEqual(s["confidence"], "medium")

    def test_real_sufficient_is_high_confidence(self):
        s = TopicScorer.calculate_score(
            {"topic": "Hanuman sindoor devotion"},
            [_make_video(), _make_video(), _make_video()],
            _mock_festival(), "youtube_api"
        )
        self.assertEqual(s["confidence"], "high")

    def test_cached_real_is_medium_confidence(self):
        s = TopicScorer.calculate_score(
            {"topic": "Hanuman sindoor devotion"}, [_make_video()],
            _mock_festival(), "cached_youtube_api"
        )
        self.assertEqual(s["confidence"], "medium")


# ─────────────────────────────────────────────────────────────────────────────
class TestCandidateSchemaAndPipeline(unittest.TestCase):
    """TEST 9 — Candidate model contains all required fields; pipeline runs offline."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.orig_cache = collector_mod.CACHE_FILE
        collector_mod.CACHE_FILE = self.tmp / "cache.json"
        self.orig_output = report_mod.OUTPUT_DIR
        report_mod.OUTPUT_DIR = self.tmp

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        collector_mod.CACHE_FILE = self.orig_cache
        report_mod.OUTPUT_DIR    = self.orig_output

    def test_full_pipeline_offline(self):
        candidates = report_mod.run_research_pipeline(creds=None, limit=2)
        self.assertGreater(len(candidates), 0)

        required = [
            "topic", "category", "deity", "suggested_angle",
            "data_source", "is_mock", "confidence",
            "closest_festival", "days_to_festival", "festival_verified", "festival_source",
            "score_version", "overall_score",
            "demand_score", "relevance_score", "competition_score",
            "evergreen_score", "freshness_score", "curiosity_score",
            "long_form_potential", "shorts_potential",
            "content_gap", "related_videos", "stats",
        ]
        for key in required:
            self.assertIn(key, candidates[0], f"Candidate missing required field: {key}")

    def test_pipeline_sorted_descending(self):
        candidates = report_mod.run_research_pipeline(creds=None, limit=3)
        scores = [c["overall_score"] for c in candidates]
        self.assertEqual(scores, sorted(scores, reverse=True),
                         "Candidates must be sorted by overall_score descending")

    def test_pipeline_output_file_created(self):
        report_mod.run_research_pipeline(creds=None, limit=1)
        files = list(self.tmp.glob("research_results_*.json"))
        self.assertTrue(len(files) >= 1, "Pipeline must write a results JSON file")


if __name__ == "__main__":
    unittest.main()
