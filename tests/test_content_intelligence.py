# tests/test_content_intelligence.py
# Comprehensive Test Suite for Telugu-Only Devotional Content Intelligence Engine
# Tests all 20 required production scenarios across research, decision, script, QA, visual, voice, and pipeline.

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.getcwd())

from src.research.scriptural_source_registry import (
    CANONICAL_SCRIPTURES,
    CANONICAL_DEITY_RULES,
    get_scripture_reference_for_topic,
    verify_scriptural_claim,
    check_chronology_compatibility,
)
from src.decision.strategy import (
    apply_content_intelligence_preferences,
)
from src.decision.feedback import (
    calculate_deity_fatigue_penalty,
    get_day_of_week_deity_bonus,
)
from src.decision.validator import validate_candidate
from src.decision.selector import select_topic
from src.content.telugu_blueprints import (
    TELUGU_DEITY_BRIEFS,
    synthesize_telugu_brief,
    synthesize_telugu_script_from_brief,
)
from src.content.brief_generator import generate_content_brief
from src.content.schemas import validate_brief_output
from src.script.generator import generate_script
from src.script.schemas import validate_script_output
from src.script.script_factuality_validator import validate_script_factuality
from src.script.script_quality_evaluator import evaluate_script_quality
from src.script.script_retention_optimizer import evaluate_script_retention
from src.assets.selector import (
    resolve_deity,
    select_scene_assets,
    extract_scene_semantic_keywords,
)
from src.voice.generator import _get_fallback_candidates


def _make_test_decision(topic: str, deity: str = "lord_shiva", score: int = 80) -> dict:
    return {
        "approved_for_generation": True,
        "selected_topic": topic,
        "score": score,
        "confidence": "high",
        "data_source": "youtube_api",
        "category": "Hindu mythology",
        "deity": deity,
        "suggested_angle": "Spiritual wisdom and life lessons",
        "content_gap": "Possible gap — high demand",
        "format": "narrated",
        "content_type": "short",
        "language_code": "te-IN",
    }


class TestTeluguContentIntelligenceScenarios(unittest.TestCase):
    """Verifies all 20 required content intelligence and QA scenarios."""

    @classmethod
    def setUpClass(cls):
        cls.patch_gemini = patch(
            "src.content.gemini_provider.call_gemini_api",
            side_effect=Exception("Offline test environment - fallback expected"),
        )
        cls.patch_gemini.start()

    @classmethod
    def tearDownClass(cls):
        cls.patch_gemini.stop()

    # ── Scenario 1: Shiva topic (Samudra Manthan / Vasuki / Neelkanth) ────────
    def test_01_shiva_story_blueprint_and_factuality(self):
        decision = _make_test_decision("Why Lord Shiva Wears a Snake Around His Neck", deity="lord_shiva")
        brief = generate_content_brief(decision, language_code="te-IN")
        ok_b, err_b = validate_brief_output(brief)
        self.assertTrue(ok_b, f"Shiva brief failed validation: {err_b}")

        script = generate_script(brief, language_code="te-IN")
        ok_s, err_s = validate_script_output(script, content_type="short")
        self.assertTrue(ok_s, f"Shiva script failed validation: {err_s}")
        self.assertIn("వాసుకి", script["narration"])
        self.assertEqual(resolve_deity(script["title"]), "lord_shiva")

    # ── Scenario 2: Ganesha topic (Ekadanta / Vyasa / Mahabharata) ────────────
    def test_02_ganesha_story_blueprint_and_factuality(self):
        decision = _make_test_decision("The Sacrifice of Ganesha Broken Tusk", deity="ganesha")
        brief = generate_content_brief(decision, language_code="te-IN")
        ok_b, err_b = validate_brief_output(brief)
        self.assertTrue(ok_b, f"Ganesha brief failed validation: {err_b}")

        script = generate_script(brief, language_code="te-IN")
        ok_s, err_s = validate_script_output(script, content_type="short")
        self.assertTrue(ok_s, f"Ganesha script failed validation: {err_s}")
        self.assertIn("మహాభారత", script["narration"])
        self.assertEqual(resolve_deity(script["title"]), "ganesha")

    # ── Scenario 3: Krishna topic (Govardhan Hill / Kaliya Mardanam) ──────────
    def test_03_krishna_story_blueprint_and_factuality(self):
        decision = _make_test_decision("The Story of Krishna Lifting Govardhan Hill", deity="krishna")
        brief = generate_content_brief(decision, language_code="te-IN")
        ok_b, err_b = validate_brief_output(brief)
        self.assertTrue(ok_b, f"Krishna brief failed validation: {err_b}")

        script = generate_script(brief, language_code="te-IN")
        ok_s, err_s = validate_script_output(script, content_type="short")
        self.assertTrue(ok_s, f"Krishna script failed validation: {err_s}")
        self.assertIn("గోవర్ధన", script["narration"])
        self.assertEqual(resolve_deity(script["title"]), "krishna")

    # ── Scenario 4: Rama topic (Shabari / Maricha / Ram Setu) ─────────────────
    def test_04_rama_story_blueprint_and_factuality(self):
        decision = _make_test_decision("Shabari Devotion and Lord Rama Grace", deity="ram")
        brief = generate_content_brief(decision, language_code="te-IN")
        ok_b, err_b = validate_brief_output(brief)
        self.assertTrue(ok_b, f"Rama brief failed validation: {err_b}")

        script = generate_script(brief, language_code="te-IN")
        ok_s, err_s = validate_script_output(script, content_type="short")
        self.assertTrue(ok_s, f"Rama script failed validation: {err_s}")
        self.assertIn("శబరి", script["narration"])
        self.assertEqual(resolve_deity(script["title"]), "ram")

    # ── Scenario 5: Hanuman topic (Sanjeevani / Dronagiri) ────────────────────
    def test_05_hanuman_story_blueprint_and_factuality(self):
        decision = _make_test_decision("How Hanuman Carried Dronagiri Mountain for Sanjeevani Herb", deity="hanuman")
        brief = generate_content_brief(decision, language_code="te-IN")
        ok_b, err_b = validate_brief_output(brief)
        self.assertTrue(ok_b, f"Hanuman brief failed validation: {err_b}")

        script = generate_script(brief, language_code="te-IN")
        ok_s, err_s = validate_script_output(script, content_type="short")
        self.assertTrue(ok_s, f"Hanuman script failed validation: {err_s}")
        self.assertIn("ద్రోణగిరి", script["narration"])
        self.assertEqual(resolve_deity(script["title"]), "hanuman")

    # ── Scenario 6: Durga topic (Mahishasura Mardini) ─────────────────────────
    def test_06_durga_story_blueprint_and_factuality(self):
        decision = _make_test_decision("Goddess Durga Mahishasura Mardini Victory", deity="durga")
        brief = generate_content_brief(decision, language_code="te-IN")
        ok_b, err_b = validate_brief_output(brief)
        self.assertTrue(ok_b, f"Durga brief failed validation: {err_b}")

        script = generate_script(brief, language_code="te-IN")
        ok_s, err_s = validate_script_output(script, content_type="short")
        self.assertTrue(ok_s, f"Durga script failed validation: {err_s}")
        self.assertIn("మహిషాసుర", script["narration"])
        self.assertEqual(resolve_deity(script["title"]), "parvathi")

    # ── Scenario 7: Vamana topic (Mahabali / 3 strides / Trivikrama) ──────────
    def test_07_vamana_story_blueprint_and_factuality(self):
        decision = _make_test_decision("The Legend of Vamana Avatar and King Bali", deity="vamana")
        brief = generate_content_brief(decision, language_code="te-IN")
        ok_b, err_b = validate_brief_output(brief)
        self.assertTrue(ok_b, f"Vamana brief failed validation: {err_b}")

        script = generate_script(brief, language_code="te-IN")
        ok_s, err_s = validate_script_output(script, content_type="short")
        self.assertTrue(ok_s, f"Vamana script failed validation: {err_s}")
        self.assertIn("బలి", script["narration"])

    # ── Scenario 8: Kurma topic (Samudra Manthan cosmic churning base) ────────
    def test_08_kurma_story_blueprint_and_factuality(self):
        decision = _make_test_decision("Kurma Avatar and the Churning of the Cosmic Milk Ocean", deity="kurma")
        brief = generate_content_brief(decision, language_code="te-IN")
        ok_b, err_b = validate_brief_output(brief)
        self.assertTrue(ok_b, f"Kurma brief failed validation: {err_b}")

        script = generate_script(brief, language_code="te-IN")
        ok_s, err_s = validate_script_output(script, content_type="short")
        self.assertTrue(ok_s, f"Kurma script failed validation: {err_s}")
        self.assertIn("మందర", script["narration"])

    # ── Scenario 9: Unlisted deity handling (Dynamic Telugu Synthesis) ─────────
    def test_09_unlisted_deity_dynamic_synthesis(self):
        decision = _make_test_decision("The Glory of Lord Dattatreya Divine Miracles", deity="dattatreya")
        brief = generate_content_brief(decision, language_code="te-IN")
        ok_b, err_b = validate_brief_output(brief)
        self.assertTrue(ok_b, f"Unlisted deity brief failed validation: {err_b}")

        script = generate_script(brief, language_code="te-IN")
        ok_s, err_s = validate_script_output(script, content_type="short")
        self.assertTrue(ok_s, f"Unlisted deity script failed validation: {err_s}")
        self.assertIn("దత్తాత్రేయ", script["title"] + script["narration"])

    # ── Scenario 10: Duplicate / fatigue penalty rejection ────────────────────
    def test_10_fatigue_penalty_against_publishing_history(self):
        # Mock recent history with Hanuman as the most recently published video
        mock_history = [
            {"topic": "How Hanuman Carried Dronagiri Mountain", "published_at": "20261110_100000"},
            {"topic": "Why Lord Shiva Wears a Snake", "published_at": "20261109_100000"},
        ]
        penalty_hanuman = calculate_deity_fatigue_penalty("hanuman", history=mock_history)
        penalty_krishna = calculate_deity_fatigue_penalty("krishna", history=mock_history)
        self.assertEqual(penalty_hanuman, 25.0, "Immediately preceding deity should receive 25.0 max penalty")
        self.assertEqual(penalty_krishna, 0.0, "Unpublished deity should receive 0.0 penalty")

        # Test in candidate adjustment
        c_hanuman = {
            "topic": "Hanuman Leap to Sun", "overall_score": 80.0, "deity": "hanuman",
            "category": "mythology", "data_source": "youtube_api", "confidence": "high"
        }
        c_krishna = {
            "topic": "Krishna Flute Wisdom", "overall_score": 70.0, "deity": "krishna",
            "category": "mythology", "data_source": "youtube_api", "confidence": "high"
        }
        adjusted = apply_content_intelligence_preferences([c_hanuman, c_krishna], history=mock_history)
        # Hanuman base 80 - 25 fatigue = 55 (plus potential day bonus). Krishna base 70 - 0 = 70+
        self.assertLess(adjusted[0]["overall_score"], adjusted[1]["overall_score"])

    # ── Scenario 11: False scripture claim rejection ──────────────────────────
    def test_11_false_scripture_claim_rejected(self):
        fake_text = "As explicitly recorded in Bhagavata Purana Chapter 999 verse 45..."
        valid, violations = verify_scriptural_claim("Test", "lord_shiva", fake_text)
        self.assertFalse(valid)
        self.assertTrue(any("Fabricated" in v for v in violations))

    # ── Scenario 12: Wrong deity attribution rejection ────────────────────────
    def test_12_wrong_deity_attribution_rejected(self):
        # Attributing Sudarshana Chakra to Shiva
        bad_shiva_text = "పరమశివుడు సుదర్శన చక్రం (Sudarshana Chakra) చేతబూని సంహరించాడు."
        valid, violations = verify_scriptural_claim("Shiva", "lord_shiva", bad_shiva_text)
        self.assertFalse(valid)
        self.assertTrue(any("canonically associated" in v for v in violations))

    # ── Scenario 13: Wrong deity relationship / genealogy rejection ───────────
    def test_13_wrong_deity_relationship_rejected(self):
        # Claiming Lakshmi is wife of Shiva
        bad_relation_text = "Lord Shiva consort Lakshmi wife Devi appeared in Kailash."
        valid, violations = verify_scriptural_claim("Shiva", "lord_shiva", bad_relation_text)
        self.assertFalse(valid)
        self.assertTrue(any("Consort contradiction" in v for v in violations))

    # ── Scenario 14: Chronology / avatar timeline contradiction rejection ─────
    def test_14_chronology_contradiction_rejected(self):
        compat, reason = check_chronology_compatibility("ram", "krishna")
        self.assertFalse(compat)
        self.assertIn("Chronological Yuga contradiction", reason)

        # But Parashurama and Rama meeting is canonically valid
        compat_valid, _ = check_chronology_compatibility("parashurama", "ram")
        self.assertTrue(compat_valid)

    # ── Scenario 15: Invalid / broken Telugu rejection ────────────────────────
    def test_15_invalid_broken_telugu_rejected(self):
        bad_script = {
            "title": "English Title With Zero Telugu Glyphs",
            "duration_seconds": 45,
            "narration": "This script is entirely in English and should be rejected immediately for te-IN.",
            "scene_scripts": [{"scene": 1, "duration_seconds": 45, "voice_text": "English voice text", "emotion": "calm", "visual_reference": "English"}]
        }
        valid, score, metrics, recs = evaluate_script_quality(bad_script, language_code="te-IN")
        self.assertFalse(valid)
        self.assertIn("flaws", metrics)

    # ── Scenario 16: Empty / truncated script output rejection ─────────────────
    def test_16_empty_or_truncated_script_rejected(self):
        empty_script = {
            "title": "",
            "duration_seconds": 0,
            "narration": "",
            "scene_scripts": [],
        }
        ok, err = validate_script_output(empty_script, content_type="short")
        self.assertFalse(ok)
        self.assertTrue("cannot be null" in err or "Missing" in err or "must be a" in err)

    # ── Scenario 17: Missing scriptural sources / citation lookup ─────────────
    def test_17_scriptural_source_registry_lookup(self):
        ref_shiva = get_scripture_reference_for_topic("Why Shiva wears a snake Vasuki around neck")
        self.assertIsNotNone(ref_shiva)
        self.assertIn("Shiva Purana", ref_shiva.text_name)

        ref_govardhan = get_scripture_reference_for_topic("Krishna lifting Govardhan Hill")
        self.assertIsNotNone(ref_govardhan)
        self.assertIn("Bhagavata Purana", ref_govardhan.text_name)

    # ── Scenario 18: Scene asset selector with Telugu narrative keywords ──────
    def test_18_scene_asset_selector_telugu_keywords(self):
        keywords = extract_scene_semantic_keywords({
            "visual_reference": "కైలాస పర్వతంపై ధ్యానముద్రలో ఉన్న పరమశివుడు మరియు మెడలోని వాసుకి సర్పం",
            "voice_text": "వాసుకి నాగరాజు శివుని మెడను ఆశ్రయించాడు"
        })
        self.assertIn("kailash", keywords)
        self.assertIn("vasuki", keywords)
        self.assertIn("snake", keywords)

    # ── Scenario 19: Telugu Pocket TTS fallback chain preservation ────────────
    def test_19_pocket_tts_fallback_chain_preserved(self):
        candidates = _get_fallback_candidates("pocket_tts")
        self.assertEqual(candidates, ["edge_neural_tts", "kokoro", "piper"])

        edge_candidates = _get_fallback_candidates("edge_neural_tts")
        self.assertEqual(edge_candidates, ["kokoro", "piper"])

    # ── Scenario 20: Strict Telugu-only production channel assertion ──────────
    def test_20_strict_telugu_only_production_assertion(self):
        from src.pipeline.orchestrator import PipelineRunner
        # Pipeline runner default should be te-IN
        runner = PipelineRunner(dry_run=True)
        self.assertEqual(runner.language_code, "te-IN")

        # Telugu brief generation must explicitly reject unsupported language codes
        with self.assertRaises(Exception):
            generate_content_brief(_make_test_decision("Test"), language_code="fr-FR")


if __name__ == "__main__":
    unittest.main()
