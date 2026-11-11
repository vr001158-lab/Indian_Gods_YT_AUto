# tests/test_remediation_defects.py
# Verification and Regression Test Suite for Remediation of DEF-01, DEF-03, DEF-02, and DEF-04
# Mandatory production validation tests for Divine Dharshanam Daily.

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.getcwd())

from src.assets.manifest import load_asset_manifest
from src.assets.selector import (
    resolve_deity,
    select_scene_assets,
    extract_scene_semantic_keywords,
)
from src.content.telugu_blueprints import (
    TELUGU_DEITY_BRIEFS,
    clean_spoken_narration,
    synthesize_telugu_brief,
    synthesize_telugu_script_from_brief,
    validate_spoken_narration,
)
from src.script.generator import generate_script
from src.script.script_qa_gate import (
    ScriptQAError,
    compute_script_content_hash,
    run_pre_voice_script_qa,
)
from src.script.script_retention_optimizer import evaluate_script_retention
from src.voice.generator import _get_fallback_candidates, generate_voice_mapping


class TestRemediationDefects(unittest.TestCase):
    """Verifies all remediation fixes for DEF-01, DEF-02, DEF-03, and DEF-04."""

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

    def _get_valid_shiva_script(self) -> dict:
        brief = TELUGU_DEITY_BRIEFS["lord_shiva"]
        script = synthesize_telugu_script_from_brief(brief)
        script["approval_metadata"] = {
            "approved_for_generation": True,
            "selected_topic": "Why Lord Shiva Wears a Snake Around His Neck",
            "score": 85,
            "confidence": "high",
            "data_source": "youtube_api",
            "category": "Hindu mythology",
            "deity": "lord_shiva",
            "suggested_angle": "Spiritual wisdom",
            "content_gap": "Possible gap",
            "format": "narrated",
            "content_type": "short",
            "language_code": "te-IN",
        }
        return script

    # ── Test 1: Invalid factuality blocks voice generation ───────────────────
    def test_01_invalid_factuality_blocks_voice_generation(self):
        script = self._get_valid_shiva_script()
        # Corrupt factuality: Shiva using Sudarshana Chakra
        script["narration"] = "పరమశివుడు సుదర్శన చక్రం చేతబట్టి సంహరించాడు."
        script["scene_scripts"][0]["voice_text"] = "పరమశివుడు సుదర్శన చక్రం చేతబట్టి సంహరించాడు."
        if "qa_report" in script:
            del script["qa_report"]

        with self.assertRaises(ValueError) as ctx:
            generate_voice_mapping(script, provider_name="mock", mode="test")
        self.assertIn("Pre-Voice QA Gate Rejection", str(ctx.exception))
        self.assertIn("canonically associated", str(ctx.exception))

    # ── Test 2: Invalid Telugu blocks voice generation ───────────────────────
    def test_02_invalid_telugu_blocks_voice_generation(self):
        script = self._get_valid_shiva_script()
        # Corrupt language: entirely English narration
        script["narration"] = "This is entirely English narration without any Telugu characters."
        script["scene_scripts"][0]["voice_text"] = "This is entirely English narration."
        if "qa_report" in script:
            del script["qa_report"]

        with self.assertRaises(ValueError) as ctx:
            generate_voice_mapping(script, provider_name="mock", mode="test")
        self.assertIn("Pre-Voice QA Gate Rejection", str(ctx.exception))

    # ── Test 3: Valid Telugu narration reaches voice generation ───────────────
    def test_03_valid_telugu_narration_reaches_voice_generation(self):
        script = self._get_valid_shiva_script()
        audio_map = generate_voice_mapping(script, provider_name="mock", mode="test")
        self.assertIsNotNone(audio_map)
        self.assertGreater(audio_map["total_duration_seconds"], 0)
        self.assertEqual(len(audio_map["audio_scenes"]), 5)
        # Check that QA report was approved and cached
        self.assertTrue(script.get("qa_report", {}).get("approved"))

    # ── Test 4: Prompt metadata never reaches TTS ────────────────────────────
    def test_04_prompt_metadata_never_reaches_tts(self):
        for deity, brief in TELUGU_DEITY_BRIEFS.items():
            script = synthesize_telugu_script_from_brief(brief)
            for sc in script["scene_scripts"]:
                voice_text = sc["voice_text"]
                ok, leak_reasons = validate_spoken_narration(voice_text)
                self.assertTrue(
                    ok,
                    f"Deity '{deity}' scene #{sc['scene']} contains leaked prompt text: {leak_reasons}. Text: '{voice_text}'",
                )
                # Confirm Telugu stage instruction words are not present
                self.assertNotIn("దృశ్యం", voice_text)
                self.assertNotIn("వర్ణన", voice_text)
                self.assertNotIn("చిత్రం", voice_text)

    # ── Test 5: Scene descriptions remain available to visual generation ──────
    def test_05_scene_descriptions_remain_available_to_visual_generation(self):
        for deity, brief in TELUGU_DEITY_BRIEFS.items():
            script = synthesize_telugu_script_from_brief(brief)
            for sc in script["scene_scripts"]:
                self.assertIn("visual_reference", sc)
                self.assertTrue(len(sc["visual_reference"].strip()) > 5)
                # Description should still contain visual detail
                self.assertNotEqual(sc["visual_reference"], sc["voice_text"])

    # ── Test 6: Missing visual matches are explicitly reported ───────────────
    def test_06_missing_visual_matches_are_explicitly_reported(self):
        manifest = load_asset_manifest()
        scenes = [{"scene": 1, "voice_text": "అపూర్వమైన దివ్య సంఘటన"}]
        # Kurma has no direct named images in lord_vishnu, so it should report missing semantic match
        plan = select_scene_assets("lord_vishnu", scenes, manifest)
        self.assertEqual(len(plan), 1)
        sc = plan[0]
        self.assertIn("semantic_confidence", sc)
        self.assertIn("semantic_match_found", sc)
        self.assertIn("missing_semantic_match", sc)
        self.assertEqual(sc["semantic_confidence"], "NONE")
        self.assertFalse(sc["semantic_match_found"])
        self.assertTrue(sc["missing_semantic_match"])
        self.assertIn("Missing specific semantic asset", sc["reason_for_selection"])

    # ── Test 7: Unrelated deity assets are not silently substituted ──────────
    def test_07_unrelated_deity_assets_not_silently_substituted(self):
        manifest = load_asset_manifest()
        scenes = [{"scene": 1, "voice_text": "వామన త్రివిక్రమ లీల"}]
        plan = select_scene_assets("lord_vishnu", scenes, manifest)
        for sc in plan:
            self.assertEqual(sc["deity"], "lord_vishnu")
            self.assertIn("lord_vishnu", sc["asset"])
            # Prohibit borrowing from unrelated deity
            self.assertNotIn("lord_shiva", sc["asset"])
            self.assertNotIn("ganesha", sc["asset"])

    # ── Test 8: Retention warnings recorded correctly ────────────────────────
    def test_08_retention_warnings_recorded_correctly(self):
        script = self._get_valid_shiva_script()
        is_opt, score, suggestions = evaluate_script_retention(script)
        self.assertIsInstance(score, float)
        self.assertGreaterEqual(score, 70.0)
        self.assertIsInstance(suggestions, list)

        # In run_pre_voice_script_qa, verify retention suggestions are recorded as warnings
        approved, qa_rep, crit = run_pre_voice_script_qa(script)
        self.assertTrue(approved)
        self.assertEqual(len(crit), 0)
        self.assertGreater(len(qa_rep["warnings"]), 0)

    # ── Test 9: QA failure cannot be bypassed by dry-run or production mode ───
    def test_09_qa_failure_cannot_be_bypassed_by_dryrun_or_production(self):
        script = self._get_valid_shiva_script()
        # Introduce factuality error
        script["scene_scripts"][0]["voice_text"] = "శివుడు సుదర్శన చక్రం ధరించాడు."
        if "qa_report" in script:
            del script["qa_report"]

        # Fails in test mode (dry-run style)
        with self.assertRaises(ValueError):
            generate_voice_mapping(script, provider_name="mock", mode="test")

        # Fails in production mode
        with self.assertRaises(ValueError):
            generate_voice_mapping(script, provider_name="mock", mode="production")

    # ── Test 10: Telugu-only production enforcement remains intact ───────────
    def test_10_telugu_only_production_enforcement_remains_intact(self):
        from src.pipeline.orchestrator import PipelineRunner
        runner = PipelineRunner(dry_run=True, language_code="te-IN")
        self.assertEqual(runner.language_code, "te-IN")

        hindi_runner = PipelineRunner(dry_run=True, language_code="hi-IN")
        with self.assertRaises(ValueError):
            # Hindi production pipeline execution must fail closed
            hindi_runner.execute_pipeline()

    # ── Test 11: Existing Pocket TTS fallback behavior remains intact ────────
    def test_11_pocket_tts_fallback_chain_remains_intact(self):
        pocket_fallbacks = _get_fallback_candidates("pocket_tts")
        self.assertEqual(pocket_fallbacks, ["edge_neural_tts", "kokoro", "piper"])

        edge_fallbacks = _get_fallback_candidates("edge_neural_tts")
        self.assertEqual(edge_fallbacks, ["kokoro", "piper"])

    # ── Test 12: Existing publishing safeguards remain intact ────────────────
    def test_12_existing_publishing_safeguards_remain_intact(self):
        from src.publisher.quota import PRODUCTION_LANGUAGE, check_publishing_quota, MAX_VIDEOS_PER_DAY
        from src.publisher.safety import PRODUCTION_LANGUAGE as SAFETY_PROD_LANG, PublisherSafetyError, validate_qa_for_publishing
        self.assertEqual(PRODUCTION_LANGUAGE, "te-IN")
        self.assertEqual(SAFETY_PROD_LANG, "te-IN")
        self.assertEqual(MAX_VIDEOS_PER_DAY, 2)

        # Non-Telugu QA result must raise PublisherSafetyError
        bad_qa_result = {
            "approved_for_publishing": True,
            "language_code": "hi-IN",
            "content_type": "short",
            "selected_topic": "Test",
            "data_source": "youtube_api",
            "resolution": "1080x1920",
            "score": 85,
        }
        with self.assertRaises(PublisherSafetyError):
            validate_qa_for_publishing(bad_qa_result)


if __name__ == "__main__":
    unittest.main()
