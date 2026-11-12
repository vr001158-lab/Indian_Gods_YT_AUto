# tests/test_telugu_script_fallback.py
# Comprehensive Unit Tests for Telugu Script Generation Fallback & Deity Consistency
# Validates offline fallbacks, HTTP 503 resilience, deity isolation, and QA gate enforcement.

import unittest
from unittest.mock import MagicMock, patch

from src.content.brief_generator import generate_content_brief
from src.content.gemini_provider import GeminiProviderError, generate_brief_with_gemini, generate_script_with_gemini
from src.content.schemas import validate_brief_output
from src.content.telugu_blueprints import (
    TELUGU_DEITY_BRIEFS,
    synthesize_telugu_brief,
    synthesize_telugu_script_from_brief,
)
from src.script.generator import generate_script
from src.script.schemas import validate_script_output
from src.script.script_factuality_validator import validate_script_factuality
from src.script.script_qa_gate import run_pre_voice_script_qa
from tests.test_content_intelligence import _make_test_decision


class TestTeluguScriptFallbackDeityConsistency(unittest.TestCase):
    """
    Verifies that Telugu script generation fallback strictly preserves deity identity
    and does not cross-diverge under offline execution or upstream Gemini failures.
    """

    def setUp(self):
        # Default: simulate offline / unavailable Gemini API for deterministic fast tests
        self.patch_call_api = patch(
            "src.content.gemini_provider.call_gemini_api",
            side_effect=GeminiProviderError("Offline test environment - fallback expected"),
        )
        self.mock_call_api = self.patch_call_api.start()

    def tearDown(self):
        self.patch_call_api.stop()

    def test_01_7kondala_swami_fallback_contains_no_krishna_content(self):
        """
        Scenario 1: 7Kondala_Swami fallback must produce Venkateswara content,
        never include Krishna-specific content, and cleanly pass Pre-Voice QA.
        """
        decision = _make_test_decision(
            "Tirumala Venkateswara Swamy Miracles and Seven Hills",
            deity="7Kondala_Swami"
        )
        brief = generate_content_brief(decision, language_code="te-IN")
        ok_b, err_b = validate_brief_output(brief)
        self.assertTrue(ok_b, f"7Kondala Swami brief failed schema validation: {err_b}")
        self.assertIn("తిరుమల", brief["primary_title"])

        script = generate_script(brief, language_code="te-IN")
        ok_s, err_s = validate_script_output(script, content_type="short")
        self.assertTrue(ok_s, f"7Kondala Swami script failed schema validation: {err_s}")

        full_text = script["title"] + " " + script["narration"]

        # Must contain Venkateswara / Tirumala / Srinivasa identity markers
        self.assertTrue(
            any(kw in full_text for kw in ["తిరుమల", "ఏడుకొండల", "శ్రీనివాస", "శ్రీవారు", "వేంకటేశ్వర"]),
            f"Expected Venkateswara markers in script, got: {full_text}"
        )

        # Must NOT contain Krishna-specific narrative markers
        krishna_specific_markers = ["గోవర్ధన", "చిటికెన వేలు", "యశోద", "వెన్న దొంగ"]
        for marker in krishna_specific_markers:
            self.assertNotIn(
                marker, full_text,
                f"Deity leak: Krishna marker '{marker}' found in 7Kondala Swami fallback script!"
            )

        # Pre-Voice QA gate verification: must approve with 0 errors
        approved, qa_rep, qa_errors = run_pre_voice_script_qa(
            script_data=script,
            canonical_topic="Tirumala Venkateswara Swamy Miracles and Seven Hills",
            deity_hint="7Kondala_Swami",
            language_code="te-IN",
            content_type="short",
            fail_fast=False,
        )
        self.assertTrue(approved, f"Pre-Voice QA rejected 7Kondala Swami script: {qa_errors}")
        self.assertEqual(len(qa_errors), 0)

    def test_02_krishna_fallback_remains_krishna_specific(self):
        """
        Scenario 2: Krishna fallback must remain strictly Krishna-specific
        and not leak 7Kondala Swami or other deity attributes.
        """
        decision = _make_test_decision(
            "The Story of Krishna Lifting Govardhan Hill",
            deity="krishna"
        )
        brief = generate_content_brief(decision, language_code="te-IN")
        ok_b, err_b = validate_brief_output(brief)
        self.assertTrue(ok_b, f"Krishna brief failed schema validation: {err_b}")

        script = generate_script(brief, language_code="te-IN")
        ok_s, err_s = validate_script_output(script, content_type="short")
        self.assertTrue(ok_s, f"Krishna script failed schema validation: {err_s}")

        full_text = script["title"] + " " + script["narration"]
        self.assertIn("గోవర్ధన", full_text)
        self.assertIn("కృష్ణ", full_text)

        # Must NOT contain Tirumala-specific markers
        tirumala_markers = ["ఆనంద నిలయం", "వకుళమాత", "శేషాచల"]
        for marker in tirumala_markers:
            self.assertNotIn(
                marker, full_text,
                f"Deity leak: Tirumala marker '{marker}' found in Krishna fallback script!"
            )

        approved, qa_rep, qa_errors = run_pre_voice_script_qa(
            script_data=script,
            canonical_topic="The Story of Krishna Lifting Govardhan Hill",
            deity_hint="krishna",
            language_code="te-IN",
            content_type="short",
            fail_fast=False,
        )
        self.assertTrue(approved, f"Pre-Voice QA rejected Krishna script: {qa_errors}")

    def test_03_hanuman_fallback_remains_hanuman_specific(self):
        """
        Scenario 3: Hanuman fallback must remain strictly Hanuman-specific
        and contain Dronagiri and Sanjeevani narrative.
        """
        decision = _make_test_decision(
            "How Hanuman Carried Dronagiri Mountain for Sanjeevani Herb",
            deity="hanuman"
        )
        brief = generate_content_brief(decision, language_code="te-IN")
        script = generate_script(brief, language_code="te-IN")

        full_text = script["title"] + " " + script["narration"]
        self.assertIn("ద్రోణగిరి", full_text)
        self.assertIn("సంజీవని", full_text)

        approved, qa_rep, qa_errors = run_pre_voice_script_qa(
            script_data=script,
            canonical_topic="How Hanuman Carried Dronagiri Mountain for Sanjeevani Herb",
            deity_hint="hanuman",
            language_code="te-IN",
            content_type="short",
            fail_fast=False,
        )
        self.assertTrue(approved, f"Pre-Voice QA rejected Hanuman script: {qa_errors}")

    def test_04_gemini_http_503_invokes_correct_deity_fallback(self):
        """
        Scenario 4: When Gemini API returns HTTP 503 (service unavailable / high load),
        the system catches the error across all candidate models, invokes the correct
        deity-specific fallback, and passes Pre-Voice QA with zero deity divergence.
        """
        # Stop default call_gemini_api patch to test actual call_gemini_api retry loop
        self.patch_call_api.stop()

        mock_503_response = MagicMock()
        mock_503_response.status_code = 503
        mock_503_response.text = '{"error": {"code": 503, "message": "The model is overloaded. Please try again later."}}'

        decision = _make_test_decision(
            "Tirumala Venkateswara Swamy Miracles",
            deity="7Kondala_Swami"
        )

        with patch("requests.post", return_value=mock_503_response) as mock_post, \
             patch("time.sleep", return_value=None), \
             patch.dict("os.environ", {"GEMINI_API_KEY": "test-key-503"}):

            brief = generate_content_brief(decision, language_code="te-IN")
            self.assertEqual(brief.get("generation_source"), "template_fallback")
            self.assertIn("తిరుమల", brief["primary_title"])

            script = generate_script(brief, language_code="te-IN")
            self.assertEqual(script.get("generation_source"), "template_fallback")

            # Verify that requests.post was indeed called (and hit 503)
            self.assertTrue(mock_post.called)

        approved, qa_rep, qa_errors = run_pre_voice_script_qa(
            script_data=script,
            canonical_topic="Tirumala Venkateswara Swamy Miracles",
            deity_hint="7Kondala_Swami",
            language_code="te-IN",
            content_type="short",
            fail_fast=False,
        )
        self.assertTrue(approved, f"503 fallback script failed QA: {qa_errors}")
        self.assertEqual(len(qa_errors), 0)

        # Restart patch for tearDown
        self.patch_call_api.start()

    def test_05_missing_deity_fallback_fails_closed(self):
        """
        Scenario 5: When fallback is explicitly disabled, or when synthesizing
        with missing topic and deity metadata, the system fails closed.
        """
        decision = _make_test_decision("Unknown Topic", deity="unknown_deity")

        # When fallback is disabled and API call fails, must fail closed
        with self.assertRaises(GeminiProviderError):
            generate_brief_with_gemini(decision, language_code="te-IN", allow_fallback=False)

        # Empty topic and deity in synthesize_telugu_brief fails closed
        with self.assertRaises(ValueError):
            synthesize_telugu_brief("", "")

    def test_06_factuality_qa_continues_rejecting_deliberately_mismatched_scripts(self):
        """
        Scenario 6: Pre-Voice Factuality QA gate must continue to catch and reject
        any deliberately cross-diverged script (e.g. topic is Rama, but script is Shiva).
        """
        # Shiva script data
        shiva_blueprint = TELUGU_DEITY_BRIEFS["lord_shiva"]
        mismatched_script = synthesize_telugu_script_from_brief(shiva_blueprint, content_type="short")

        # Check factuality against Rama canonical topic
        valid, violations, report = validate_script_factuality(
            script_data=mismatched_script,
            canonical_topic="Lord Sri Rama and Shabari Devotion",
            deity_hint="ram",
        )
        self.assertFalse(valid, "Factuality QA should reject Shiva script paired with Rama topic")
        self.assertTrue(
            any("Deity divergence detected" in v for v in violations),
            f"Expected 'Deity divergence detected' violation, got: {violations}"
        )

        # Run through full Pre-Voice QA gate
        approved, qa_rep, qa_errors = run_pre_voice_script_qa(
            script_data=mismatched_script,
            canonical_topic="Lord Sri Rama and Shabari Devotion",
            deity_hint="ram",
            language_code="te-IN",
            content_type="short",
            fail_fast=False,
        )
        self.assertFalse(approved, "Pre-Voice QA must reject cross-diverged script")
        self.assertTrue(any("Deity divergence detected" in e for e in qa_errors))


if __name__ == "__main__":
    unittest.main()
