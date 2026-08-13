"""
tests/test_decision.py
Unit tests for Phase 2B.1 — Topic Decision Engine.
Tests all validation gates, deterministic selection priority, JSON output schema, and CLI behavior.
All tests run offline without network access or live API dependencies.
"""

import sys
import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.getcwd())

from src.decision.validator import validate_candidate, validate_candidates
from src.decision.selector  import select_topic
from src.decision.report    import run_decision_pipeline
import run_decision


# ── Helper: generate mock candidate dicts ─────────────────────────────────────
def _make_candidate(
    topic: str = "Test Topic",
    overall_score: int = 70,
    confidence: str = "high",
    data_source: str = "youtube_api",
    category: str = "Hindu mythology",
    **kwargs
) -> dict:
    """Helper to build a structurally valid research candidate."""
    base = {
        "topic": topic,
        "category": category,
        "deity": "shiva",
        "suggested_angle": "Test suggested angle for topic.",
        "data_source": data_source,
        "is_mock": data_source in ("mock", "offline"),
        "confidence": confidence,
        "closest_festival": "Maha Shivratri",
        "days_to_festival": 100,
        "festival_verified": True,
        "festival_source": "test",
        "score_version": "v0.1",
        "overall_score": overall_score,
        "demand_score": 80,
        "relevance_score": 75,
        "competition_score": 70,
        "evergreen_score": 65,
        "freshness_score": 60,
        "curiosity_score": 92,
        "long_form_potential": 70,
        "shorts_potential": 80,
        "content_gap": "Possible gap — low saturation with moderate-to-high demand signals.",
        "related_videos": [],
        "stats": {}
    }
    base.update(kwargs)
    return base


# ─────────────────────────────────────────────────────────────────────────────
class TestDecisionValidator(unittest.TestCase):
    """Test candidate structural completeness and safety gates."""

    def test_valid_candidate_passes(self):
        c = _make_candidate()
        ok, reasons = validate_candidate(c)
        self.assertTrue(ok)
        self.assertEqual(reasons, [])

    def test_mock_topic_rejected(self):
        c = _make_candidate(data_source="mock")
        ok, reasons = validate_candidate(c)
        self.assertFalse(ok)
        self.assertTrue(any("data_source" in r for r in reasons))

    def test_offline_topic_rejected(self):
        c = _make_candidate(data_source="offline")
        ok, reasons = validate_candidate(c)
        self.assertFalse(ok)
        self.assertTrue(any("data_source" in r for r in reasons))

    def test_low_confidence_rejected(self):
        c = _make_candidate(confidence="low")
        ok, reasons = validate_candidate(c)
        self.assertFalse(ok)
        self.assertTrue(any("confidence" in r for r in reasons))

    def test_medium_confidence_rejected(self):
        c = _make_candidate(confidence="medium")
        ok, reasons = validate_candidate(c)
        self.assertFalse(ok)
        self.assertTrue(any("confidence" in r for r in reasons))

    def test_score_below_threshold_rejected(self):
        c = _make_candidate(overall_score=59)
        ok, reasons = validate_candidate(c, min_score=60)
        self.assertFalse(ok)
        self.assertTrue(any("overall_score" in r for r in reasons))

    def test_score_at_threshold_passes(self):
        c = _make_candidate(overall_score=60)
        ok, _ = validate_candidate(c, min_score=60)
        self.assertTrue(ok)

    def test_missing_required_field_rejected(self):
        c = _make_candidate()
        del c["suggested_angle"]
        ok, reasons = validate_candidate(c)
        self.assertFalse(ok)
        self.assertTrue(any("suggested_angle" in r for r in reasons))

    def test_null_required_field_rejected(self):
        c = _make_candidate()
        c["category"] = None
        ok, reasons = validate_candidate(c)
        self.assertFalse(ok)
        self.assertTrue(any("category" in r for r in reasons))


# ─────────────────────────────────────────────────────────────────────────────
class TestDecisionSelector(unittest.TestCase):
    """Test sorting priority, deterministic ranking, and deduplication."""

    def test_highest_valid_topic_selected(self):
        c1 = _make_candidate("Low score", overall_score=65)
        c2 = _make_candidate("High score", overall_score=85)
        c3 = _make_candidate("Mid score", overall_score=75)
        res = select_topic([c1, c2, c3])
        self.assertEqual(res["selected"]["topic"], "High score")

    def test_tie_breakers_evaluated_correctly(self):
        # Tie-breaker order:
        # 1. overall_score (equal)
        # 2. demand_score
        # 3. freshness_score
        # 4. content_gap strength ("possible gap" > "high saturation")
        # 5. relevance_score
        # 6. curiosity_score
        # 7. topic (alphabetical string tie-breaker)

        # Tie 1: demand score beats others
        c1 = _make_candidate("T1 A", overall_score=70, demand_score=80)
        c2 = _make_candidate("T1 B", overall_score=70, demand_score=85)
        res = select_topic([c1, c2])
        self.assertEqual(res["selected"]["topic"], "T1 B")

        # Tie 2: freshness beats relevance
        c3 = _make_candidate("T2 A", overall_score=70, demand_score=80, freshness_score=50)
        c4 = _make_candidate("T2 B", overall_score=70, demand_score=80, freshness_score=60)
        res = select_topic([c3, c4])
        self.assertEqual(res["selected"]["topic"], "T2 B")

        # Tie 3: gap strength beats relevance
        c5 = _make_candidate("T3 A", overall_score=70, demand_score=80, freshness_score=50, content_gap="high saturation")
        c6 = _make_candidate("T3 B", overall_score=70, demand_score=80, freshness_score=50, content_gap="possible gap")
        res = select_topic([c5, c6])
        self.assertEqual(res["selected"]["topic"], "T3 B")

        # Tie 4: alphabetical string fallback
        c7 = _make_candidate("Alpha Topic", overall_score=70, demand_score=80, freshness_score=50, curiosity_score=90)
        c8 = _make_candidate("Beta Topic", overall_score=70, demand_score=80, freshness_score=50, curiosity_score=90)
        res = select_topic([c7, c8])
        self.assertEqual(res["selected"]["topic"], "Alpha Topic")

    def test_duplicate_topics_deduplicated_safely(self):
        # Two topics sharing >= 2 non-stop-words are near-duplicates
        c1 = _make_candidate("Why Lord Ganesha Has One Broken Tusk", overall_score=80)
        c2 = _make_candidate("Story of Ganesha and His Broken Tusk", overall_score=75) # Near-duplicate
        c3 = _make_candidate("Why Lord Shiva Wears a Snake Around His Neck", overall_score=70) # Distinct

        res = select_topic([c1, c2, c3])
        self.assertEqual(res["selected"]["topic"], "Why Lord Ganesha Has One Broken Tusk")
        self.assertEqual(len(res["ranked"]), 3)
        # Verify c2 was dropped as duplicate
        deduped_topics = [x["topic"] for x in res["dedup_removed"]]
        self.assertIn("Story of Ganesha and His Broken Tusk", deduped_topics)
        
        # Verify c3 remains in unique rank candidates list implicitly via final select length
        # Unique list count can be derived from ranked minus dedup_removed
        self.assertEqual(len(res["ranked"]) - len(res["dedup_removed"]), 2)

    def test_deterministic_selection_order(self):
        # Shuffled order of identical lists must yield identical selection
        c1 = _make_candidate("A", overall_score=80, demand_score=90)
        c2 = _make_candidate("B", overall_score=80, demand_score=85)
        c3 = _make_candidate("C", overall_score=70, demand_score=95)

        res1 = select_topic([c1, c2, c3])
        res2 = select_topic([c3, c2, c1])
        self.assertEqual(res1["selected"]["topic"], res2["selected"]["topic"])
        self.assertEqual(res1["selected"]["topic"], "A")


# ─────────────────────────────────────────────────────────────────────────────
class TestDecisionPipeline(unittest.TestCase):
    """Test full decision pipeline output schema and edge cases."""

    def test_valid_decision_json_generated(self):
        c1 = _make_candidate("Valid", overall_score=75)
        c2 = _make_candidate("Mock", overall_score=85, data_source="mock")

        with tempfile.TemporaryDirectory() as tmp_dir:
            orig_output = run_decision.decision_report.OUTPUT_DIR
            run_decision.decision_report.OUTPUT_DIR = Path(tmp_dir)
            try:
                decision = run_decision_pipeline([c1, c2], min_score=60, save=True)
                
                # Check memory schema
                self.assertTrue(decision["approved_for_generation"])
                self.assertEqual(decision["selected_topic"], "Valid")
                self.assertEqual(decision["score"], 75)
                self.assertEqual(decision["confidence"], "high")
                self.assertEqual(decision["data_source"], "youtube_api")
                self.assertEqual(decision["category"], "Hindu mythology")
                self.assertIsNotNone(decision["selected_at"])
                self.assertEqual(len(decision["rejected_candidates"]), 1)
                self.assertEqual(decision["rejected_candidates"][0]["topic"], "Mock")

                # Check persistence
                saved_files = list(Path(tmp_dir).glob("decision_*.json"))
                self.assertEqual(len(saved_files), 1)
                saved_data = json.loads(saved_files[0].read_text(encoding="utf-8"))
                self.assertEqual(saved_data["selected_topic"], "Valid")
            finally:
                run_decision.decision_report.OUTPUT_DIR = orig_output

    def test_completely_unsafe_research_fails_closed(self):
        c1 = _make_candidate("Mock", overall_score=85, data_source="mock")
        c2 = _make_candidate("Low Conf", overall_score=90, confidence="low")
        c3 = _make_candidate("Offline", overall_score=95, data_source="offline")

        decision = run_decision_pipeline([c1, c2, c3], min_score=60, save=False)
        self.assertFalse(decision["approved_for_generation"])
        self.assertIsNone(decision["selected_topic"])
        self.assertIn("No research candidate passed", decision["reason"])

    def test_mixed_real_and_mock_selects_only_real(self):
        # Mock candidate has higher score, but must be bypassed for the valid candidate
        c_mock = _make_candidate("Mock Topic", overall_score=95, data_source="mock")
        c_real = _make_candidate("Real Topic", overall_score=65, data_source="youtube_api")

        decision = run_decision_pipeline([c_mock, c_real], min_score=60, save=False)
        self.assertTrue(decision["approved_for_generation"])
        self.assertEqual(decision["selected_topic"], "Real Topic")


# ─────────────────────────────────────────────────────────────────────────────
class TestDecisionCLI(unittest.TestCase):
    """Test run_decision.py CLI inputs, outputs, and auto-discovery."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.research_dir = Path(self.tmp_dir.name) / "research"
        self.decision_dir = Path(self.tmp_dir.name) / "decision"
        self.research_dir.mkdir()
        self.decision_dir.mkdir()

        # Patch paths in run_decision and report modules
        self.patch_research_dir = patch("run_decision.RESEARCH_DIR", self.research_dir)
        self.patch_decision_dir = patch("src.decision.report.OUTPUT_DIR", self.decision_dir)
        self.patch_research_dir.start()
        self.patch_decision_dir.start()

    def tearDown(self):
        self.patch_research_dir.stop()
        self.patch_decision_dir.stop()
        self.tmp_dir.cleanup()

    def test_cli_auto_locates_latest_research_file(self):
        # Write two mock research files with chronological names
        f1 = self.research_dir / "research_results_20260810_120000.json"
        f2 = self.research_dir / "research_results_20260812_120000.json"

        # f1 has a topic that passes; f2 has a different topic that passes.
        c1 = _make_candidate("Topic Old", overall_score=70)
        c2 = _make_candidate("Topic New", overall_score=80)

        f1.write_text(json.dumps([c1]), encoding="utf-8")
        f2.write_text(json.dumps([c2]), encoding="utf-8")

        # Mock sys.argv to run auto-locate (no arguments)
        with patch("sys.argv", ["run_decision.py", "--no-save"]):
            with patch("sys.exit") as mock_exit:
                run_decision.main()
                mock_exit.assert_called_once_with(0) # Approved exit code is 0

        # Verify new files were created in decision dir?
        # We passed --no-save in argv so no file should be written, but we can verify
        # what topic was selected by running without --no-save as well.
        with patch("sys.argv", ["run_decision.py"]):
            with patch("sys.exit") as mock_exit:
                run_decision.main()
                mock_exit.assert_called_once_with(0)

        decision_files = list(self.decision_dir.glob("decision_*.json"))
        self.assertEqual(len(decision_files), 1)
        data = json.loads(decision_files[0].read_text(encoding="utf-8"))
        # Must have loaded the newer file (f2 -> Topic New)
        self.assertEqual(data["selected_topic"], "Topic New")

    def test_custom_input_param_works(self):
        # Create a file outside the auto-locate pattern
        custom_file = Path(self.tmp_dir.name) / "custom_res.json"
        c = _make_candidate("Custom Input Topic", overall_score=85)
        custom_file.write_text(json.dumps([c]), encoding="utf-8")

        with patch("sys.argv", ["run_decision.py", "--input", str(custom_file)]):
            with patch("sys.exit") as mock_exit:
                run_decision.main()
                mock_exit.assert_called_once_with(0)

        decision_files = list(self.decision_dir.glob("decision_*.json"))
        self.assertEqual(len(decision_files), 1)
        data = json.loads(decision_files[0].read_text(encoding="utf-8"))
        self.assertEqual(data["selected_topic"], "Custom Input Topic")

    def test_custom_min_score_param_works(self):
        f = self.research_dir / "research_results_20260813_120000.json"
        c = _make_candidate("Topic with 65", overall_score=65)
        f.write_text(json.dumps([c]), encoding="utf-8")

        # Under default threshold (60), it should be approved (exit 0)
        with patch("sys.argv", ["run_decision.py", "--no-save"]):
            with patch("sys.exit") as mock_exit:
                run_decision.main()
                mock_exit.assert_called_once_with(0)

        # Under elevated threshold (70), it should be rejected (exit 2)
        with patch("sys.argv", ["run_decision.py", "--min-score", "70", "--no-save"]):
            with patch("sys.exit") as mock_exit:
                run_decision.main()
                mock_exit.assert_called_once_with(2)


if __name__ == "__main__":
    unittest.main()
