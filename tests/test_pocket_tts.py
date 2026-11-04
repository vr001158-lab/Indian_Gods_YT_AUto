"""
tests/test_pocket_tts.py
Comprehensive unit tests for Pocket TTS Telugu female voice provider.
Tests:
- Telugu numeral & digit expansion into natural Telugu words
- Latin character detection, logging, and stripping
- Sentence-sized chunking & sequence preservation
- Provider initialization, configuration, and constraints
- Audio synthesis via mocked TTSModel and 24kHz mono PCM WAV generation
- Audio QA and ffprobe compliance
- Bidirectional fallback chain between Pocket TTS and Edge TTS
"""

import logging
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

from src.voice.providers.pocket_tts import (
    PocketTTSProvider,
    POCKET_TTS_CONFIG,
    POCKET_TTS_LANGUAGE_VOICE_CONFIG,
    normalize_telugu_text,
    number_to_telugu_words,
    split_into_sentences,
)
from src.voice.providers.base import VoiceProviderError
from src.voice.schemas import PRODUCTION_PROVIDERS, validate_audio_output
from src.voice.generator import (
    _get_fallback_candidates,
    _resolve_voice_config,
    generate_voice_mapping,
    get_default_provider_for_language,
)
from src.voice.qa import perform_audio_qa, validate_audio_file_with_ffprobe


class TestPocketTTSTextNormalization(unittest.TestCase):
    """Tests Telugu numerals, digits, and Latin character normalization."""

    def test_single_digits_to_words(self):
        self.assertEqual(number_to_telugu_words(0), "సున్నా")
        self.assertEqual(number_to_telugu_words(1), "ఒకటి")
        self.assertEqual(number_to_telugu_words(5), "ఐదు")
        self.assertEqual(number_to_telugu_words(9), "తొమ్మిది")

    def test_compound_numbers_to_words(self):
        self.assertEqual(number_to_telugu_words(10), "పది")
        self.assertEqual(number_to_telugu_words(15), "పదిహేను")
        self.assertEqual(number_to_telugu_words(20), "ఇరవై")
        self.assertEqual(number_to_telugu_words(25), "ఇరవై ఐదు")
        self.assertEqual(number_to_telugu_words(100), "వంద")
        self.assertEqual(number_to_telugu_words(1000), "వెయ్యి")

    def test_normalize_telugu_numerals(self):
        # ౧౦౮ should map to 108 -> నూట ఎనిమిది / వంద ఎనిమిది
        text = "శివునికి ౨౧ ప్రదక్షిణలు"
        normalized = normalize_telugu_text(text)
        self.assertIn("ఇరవై ఒకటి", normalized)
        self.assertNotIn("౨", normalized)
        self.assertNotIn("౨౧", normalized)

    def test_normalize_arabic_digits(self):
        text = "గణపతికి 5 మోదకాలు సమర్పించాలి"
        normalized = normalize_telugu_text(text)
        self.assertIn("ఐదు", normalized)
        self.assertNotIn("5", normalized)

    def test_latin_character_handling_warn_policy_default(self):
        """Default policy ('warn') preserves Latin words intact in text and emits a warning."""
        text = "ఓం నమః శివాయ Shiva Temple"
        with self.assertLogs("src.voice.providers.pocket_tts", level="WARNING") as cm:
            normalized = normalize_telugu_text(text)
            self.assertIn("unhandled Latin text", cm.output[0])
        # Latin words must be preserved by default, not silently stripped
        self.assertIn("Shiva", normalized)
        self.assertIn("Temple", normalized)
        self.assertIn("ఓం నమః శివాయ", normalized)

    def test_latin_character_handling_preserve_policy(self):
        """'preserve' policy keeps Latin text intact without emitting any warning."""
        text = "భక్తి ఛానల్ YouTube మరియు AI సాంకేతికత"
        # When preserve is set, no warning should be logged for Latin text
        logger = logging.getLogger("src.voice.providers.pocket_tts")
        with patch.object(logger, "warning") as mock_warn:
            normalized = normalize_telugu_text(text, latin_policy="preserve")
            mock_warn.assert_not_called()
        self.assertIn("YouTube", normalized)
        self.assertIn("AI", normalized)

    def test_latin_character_handling_strip_policy(self):
        """'strip' policy removes Latin words and logs a warning."""
        text = "ఓం నమః శివాయ Shiva Temple"
        with self.assertLogs("src.voice.providers.pocket_tts", level="WARNING") as cm:
            normalized = normalize_telugu_text(text, latin_policy="strip")
            self.assertIn("unhandled Latin text", cm.output[0])
        self.assertNotIn("Shiva", normalized)
        self.assertNotIn("Temple", normalized)
        self.assertIn("ఓం నమః శివాయ", normalized)

    def test_latin_policy_invalid_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            normalize_telugu_text("శివ", latin_policy="invalid_policy")
        self.assertIn("Invalid latin_policy", str(ctx.exception))

    def test_legacy_strip_latin_boolean_compatibility(self):
        text = "శివ Kailash"
        norm_strip = normalize_telugu_text(text, strip_latin=True)
        self.assertNotIn("Kailash", norm_strip)
        norm_keep = normalize_telugu_text(text, strip_latin=False)
        self.assertIn("Kailash", norm_keep)


class TestPocketTTSSentenceChunking(unittest.TestCase):
    """Tests chunking of long Telugu scripts into sentence-sized segments."""

    def test_split_by_standard_delimiters(self):
        text = "మొదటి వాక్యం. రెండవ వాక్యం! మూడవ వాక్యం? నాల్గవ వాక్యం।"
        chunks = split_into_sentences(text)
        self.assertEqual(len(chunks), 4)
        self.assertIn("మొదటి వాక్యం.", chunks[0])
        self.assertIn("రెండవ వాక్యం!", chunks[1])
        self.assertIn("మూడవ వాక్యం?", chunks[2])
        self.assertIn("నాల్గవ వాక్యం।", chunks[3])

    def test_split_preserves_order(self):
        text = "వాక్యం ఒకటి. వాక్యం రెండు. వాక్యం మూడు."
        chunks = split_into_sentences(text)
        self.assertEqual(chunks, ["వాక్యం ఒకటి.", "వాక్యం రెండు.", "వాక్యం మూడు."])

    def test_oversized_sentence_subsplit(self):
        # Construct a very long sentence with commas exceeding 150 chars
        long_sentence = "ఈ కథ పరమేశ్వరుని మహిమను చాటిచెబుతుంది, " * 6
        chunks = split_into_sentences(long_sentence, max_chars=100)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 110)


class TestPocketTTSProvider(unittest.TestCase):
    """Tests PocketTTSProvider class methods, metadata, synthesis, and safety gates."""

    def setUp(self):
        self.provider = PocketTTSProvider()

    def test_provider_attributes(self):
        self.assertEqual(self.provider.provider_name, "pocket_tts")
        self.assertEqual(self.provider.voice_id, "syspin_female")
        self.assertTrue(self.provider.real_tts)
        self.assertEqual(self.provider.mode, "production")

    def test_empty_text_raises_error(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = Path(f.name)
        try:
            with self.assertRaises(VoiceProviderError):
                self.provider.generate_speech("", temp_path, language_code="te-IN")
            with self.assertRaises(VoiceProviderError):
                self.provider.generate_speech("   ", temp_path, language_code="te-IN")
        finally:
            if temp_path.exists():
                temp_path.unlink()

    def test_unsupported_language_raises_error(self):
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = Path(f.name)
        try:
            with self.assertRaises(VoiceProviderError) as ctx:
                self.provider.generate_speech("నమస్కారం", temp_path, language_code="hi-IN")
            self.assertIn("Only 'te-IN' (Telugu) is supported", str(ctx.exception))
        finally:
            if temp_path.exists():
                temp_path.unlink()

    @unittest.skipUnless(HAS_TORCH, "torch is required for Pocket TTS neural synthesis testing")
    def test_generate_speech_mocked(self):
        """Test end-to-end synthesis with mocked neural weights producing valid audio."""
        import torch

        # Mock model that returns a 2-second 24kHz sine/silence tensor per chunk
        fake_model = MagicMock()
        fake_model.sample_rate = 24000
        # 24000 samples * 2 sec = 48000
        fake_model.generate_audio.side_effect = lambda state, text: torch.zeros(48000, dtype=torch.float32)

        with patch.object(PocketTTSProvider, "_get_model_and_state", return_value=(fake_model, {})):
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_wav = Path(f.name)
            try:
                duration = self.provider.generate_speech(
                    "నమస్కారం భక్తులారా. ఇది దివ్య దర్శనం.",
                    temp_wav,
                    language_code="te-IN",
                )
                self.assertGreater(duration, 0)
                self.assertTrue(temp_wav.exists())
                self.assertGreater(temp_wav.stat().st_size, 0)

                # Validate audio QA checks
                info = validate_audio_file_with_ffprobe(temp_wav, allow_mock=False)
                self.assertEqual(info["sample_rate"], 24000)
                self.assertEqual(info["channels"], 1)

                qa = perform_audio_qa(temp_wav, allow_mock=False)
                self.assertTrue(qa["valid"])
                self.assertEqual(qa["sample_rate"], 24000)
                self.assertEqual(qa["channels"], 1)
            finally:
                if temp_wav.exists():
                    temp_wav.unlink()


class TestPocketTTSFallbackIntegration(unittest.TestCase):
    """Tests registration, schema validation, and fallback candidates."""

    def test_registered_in_production_providers(self):
        self.assertIn("pocket_tts", PRODUCTION_PROVIDERS)

    def test_resolve_voice_config_for_telugu(self):
        cfg = _resolve_voice_config({}, "te-IN", "pocket_tts")
        self.assertEqual(cfg["provider"], "pocket_tts")
        self.assertEqual(cfg["voice_name"], "syspin_female")
        self.assertEqual(cfg["language_code"], "te-IN")
        self.assertEqual(cfg["sample_rate"], 24000)

    def test_fallback_candidates_when_pocket_tts_is_primary(self):
        candidates = _get_fallback_candidates("pocket_tts")
        self.assertTrue(len(candidates) > 0)
        # Edge TTS must be the first fallback candidate if pocket_tts fails
        self.assertEqual(candidates[0], "edge_neural_tts")
        self.assertEqual(candidates, ["edge_neural_tts", "kokoro", "piper"])

    def test_fallback_candidates_when_edge_is_primary(self):
        candidates = _get_fallback_candidates("edge_neural_tts")
        self.assertEqual(candidates, ["kokoro", "piper"])

    def test_schema_validates_pocket_tts_audio_mapping(self):
        valid_map = {
            "run_id": "test_pocket_run",
            "script_title": "శివుని లీలలు",
            "total_duration_seconds": 30,
            "provider": "pocket_tts",
            "real_tts": True,
            "mode": "production",
            "language_code": "te-IN",
            "voice_name": "syspin_female",
            "full_narration_audio_file": "data/audio/test/full.wav",
            "audio_scenes": [
                {
                    "scene": 1,
                    "voice_text": "మొదటి దృశ్యం",
                    "audio_file": "data/audio/test/scene_1.wav",
                    "duration_seconds": 15,
                },
                {
                    "scene": 2,
                    "voice_text": "రెండవ దృశ్యం",
                    "audio_file": "data/audio/test/scene_2.wav",
                    "duration_seconds": 15,
                },
            ],
        }
        ok, err = validate_audio_output(valid_map)
        self.assertTrue(ok, f"Validation failed: {err}")

    def test_pocket_and_edge_tts_failure_falls_back_to_kokoro(self):
        """Simulates both Pocket TTS and Edge TTS failing; verifies fallback cleanly proceeds to Kokoro without recursion."""
        from src.voice.generator import _make_silent_wav_bytes

        script = {
            "title": "శ్రీ వేంకటేశ్వర స్వామి దివ్య లీల",
            "duration_seconds": 30,
            "language_code": "te-IN",
            "narration": "నమస్కారం భక్తులారా. ఇది తిరుమల వేంకటేశ్వర స్వామి దివ్య దర్శనం.",
            "retention_hooks": ["తిరుమల రహస్యం"],
            "shorts_scripts": [
                {"title": "లఘు కథ 1", "hook": "మీకు తెలుసా?", "body": "తిరుమల స్వామి దివ్య కథ."}
            ],
            "scene_scripts": [
                {
                    "scene": 1,
                    "duration_seconds": 15,
                    "visual_reference": "Tirumala gopuram",
                    "voice_text": "నమస్కారం భక్తులారా. ఇది తిరుమల వేంకటేశ్వర స్వామి దివ్య దర్శనం.",
                    "emotion": "Devotional",
                },
                {
                    "scene": 2,
                    "duration_seconds": 15,
                    "visual_reference": "Balaji idol",
                    "voice_text": "స్వామివారి దివ్య రూపం దర్శించుకోండి.",
                    "emotion": "Devotional",
                },
            ],
            "approval_metadata": {
                "approved_for_generation": True,
                "data_source": "youtube_api",
                "confidence": "high",
                "selected_topic": "Tirumala Balaji Miracles",
                "language_code": "te-IN",
            },
        }

        call_order = []

        def pocket_fail(*args, **kwargs):
            call_order.append("pocket_tts")
            raise VoiceProviderError("Pocket inference error")

        def edge_fail(*args, **kwargs):
            call_order.append("edge_neural_tts")
            raise VoiceProviderError("Edge timeout")

        def kokoro_success(text, output_path, language_code="te-IN", voice_config=None):
            call_order.append("kokoro")
            output_path.write_bytes(_make_silent_wav_bytes(15))
            return 15

        with patch("src.voice.providers.pocket_tts.PocketTTSProvider.generate_speech", side_effect=pocket_fail):
            with patch("src.voice.providers.edge_tts.EdgeTTSProvider.generate_speech", side_effect=edge_fail):
                with patch("src.voice.providers.google_chirp.KokoroProvider.generate_speech", side_effect=kokoro_success):
                    with tempfile.TemporaryDirectory() as tmp_dir:
                        audio_map = generate_voice_mapping(
                            script=script,
                            provider_name="pocket_tts",
                            output_dir=Path(tmp_dir),
                            mode="production",
                        )
                        self.assertEqual(audio_map["provider"], "kokoro")
                        self.assertTrue(audio_map["fallback_used"])
                        self.assertEqual(audio_map["primary_provider_configured"], "pocket_tts")
                        # First attempt cycle for scene 1 must be strictly pocket -> edge -> kokoro
                        self.assertEqual(call_order[:3], ["pocket_tts", "edge_neural_tts", "kokoro"])

    def test_default_provider_resolution_by_language(self):
        """Verifies default production provider mapping: te-IN -> pocket_tts, hi-IN/ta-IN -> edge_neural_tts."""
        self.assertEqual(get_default_provider_for_language("te-IN", mode="production"), "pocket_tts")
        self.assertEqual(get_default_provider_for_language("hi-IN", mode="production"), "edge_neural_tts")
        self.assertEqual(get_default_provider_for_language("ta-IN", mode="production"), "edge_neural_tts")
        self.assertEqual(get_default_provider_for_language("te-IN", mode="test"), "mock")

    def test_generate_voice_mapping_defaults_to_pocket_tts_for_telugu(self):
        """When provider_name is omitted for Telugu script, generate_voice_mapping defaults to Pocket TTS."""
        from src.voice.generator import _make_silent_wav_bytes

        script = {
            "title": "శ్రీ వేంకటేశ్వర స్వామి దివ్య లీల",
            "duration_seconds": 30,
            "language_code": "te-IN",
            "narration": "నమస్కారం భక్తులారా. ఇది తిరుమల వేంకటేశ్వర స్వామి దివ్య దర్శనం.",
            "retention_hooks": ["తిరుమల రహస్యం"],
            "shorts_scripts": [
                {"title": "లఘు కథ 1", "hook": "మీకు తెలుసా?", "body": "తిరుమల స్వామి దివ్య కథ."}
            ],
            "scene_scripts": [
                {
                    "scene": 1,
                    "duration_seconds": 15,
                    "visual_reference": "Tirumala gopuram",
                    "voice_text": "నమస్కారం భక్తులారా. ఇది తిరుమల వేంకటేశ్వర స్వామి దివ్య దర్శనం.",
                    "emotion": "Devotional",
                },
                {
                    "scene": 2,
                    "duration_seconds": 15,
                    "visual_reference": "Balaji idol",
                    "voice_text": "స్వామివారి దివ్య రూపం దర్శించుకోండి.",
                    "emotion": "Devotional",
                },
            ],
            "approval_metadata": {
                "approved_for_generation": True,
                "data_source": "youtube_api",
                "confidence": "high",
                "selected_topic": "Tirumala Balaji Miracles",
                "language_code": "te-IN",
            },
        }

        def fake_pocket_speech(text, output_path, language_code="te-IN", voice_config=None):
            output_path.write_bytes(_make_silent_wav_bytes(15))
            return 15

        with patch("src.voice.providers.pocket_tts.PocketTTSProvider.generate_speech", side_effect=fake_pocket_speech) as mock_pocket:
            with tempfile.TemporaryDirectory() as tmp_dir:
                audio_map = generate_voice_mapping(
                    script=script,
                    provider_name=None,  # auto-default based on script language
                    output_dir=Path(tmp_dir),
                    mode="production",
                )
                self.assertEqual(audio_map["provider"], "pocket_tts")
                self.assertEqual(audio_map["primary_provider_configured"], "pocket_tts")
                self.assertFalse(audio_map["fallback_used"])
                self.assertTrue(mock_pocket.called)

    def test_telugu_default_pocket_tts_failure_falls_back_to_edge_tts(self):
        """When Telugu default Pocket TTS fails, pipeline automatically falls back to Edge TTS."""
        from src.voice.generator import _make_silent_wav_bytes

        script = {
            "title": "శ్రీ వేంకటేశ్వర స్వామి దివ్య లీల",
            "duration_seconds": 30,
            "language_code": "te-IN",
            "narration": "నమస్కారం భక్తులారా. ఇది తిరుమల వేంకటేశ్వర స్వామి దివ్య దర్శనం.",
            "retention_hooks": ["తిరుమల రహస్యం"],
            "shorts_scripts": [
                {"title": "లఘు కథ 1", "hook": "మీకు తెలుసా?", "body": "తిరుమల స్వామి దివ్య కథ."}
            ],
            "scene_scripts": [
                {
                    "scene": 1,
                    "duration_seconds": 15,
                    "visual_reference": "Tirumala gopuram",
                    "voice_text": "నమస్కారం భక్తులారా. ఇది తిరుమల వేంకటేశ్వర స్వామి దివ్య దర్శనం.",
                    "emotion": "Devotional",
                },
                {
                    "scene": 2,
                    "duration_seconds": 15,
                    "visual_reference": "Balaji idol",
                    "voice_text": "స్వామివారి దివ్య రూపం దర్శించుకోండి.",
                    "emotion": "Devotional",
                },
            ],
            "approval_metadata": {
                "approved_for_generation": True,
                "data_source": "youtube_api",
                "confidence": "high",
                "selected_topic": "Tirumala Balaji Miracles",
                "language_code": "te-IN",
            },
        }

        def fake_edge_speech(text, output_path, language_code="te-IN", voice_config=None):
            output_path.write_bytes(_make_silent_wav_bytes(15))
            return 15

        with patch("src.voice.providers.pocket_tts.PocketTTSProvider.generate_speech", side_effect=VoiceProviderError("Pocket inference failed")):
            with patch("src.voice.providers.edge_tts.EdgeTTSProvider.generate_speech", side_effect=fake_edge_speech) as mock_edge:
                with tempfile.TemporaryDirectory() as tmp_dir:
                    audio_map = generate_voice_mapping(
                        script=script,
                        provider_name=None,  # auto-default to pocket_tts
                        output_dir=Path(tmp_dir),
                        mode="production",
                    )
                    self.assertEqual(audio_map["provider"], "edge_neural_tts")
                    self.assertTrue(audio_map["fallback_used"])
                    self.assertEqual(audio_map["primary_provider_configured"], "pocket_tts")
                    self.assertTrue(mock_edge.called)

    def test_orchestrator_selects_pocket_tts_for_telugu(self):
        """PipelineRunner automatically selects pocket_tts for te-IN and edge_neural_tts for hi-IN."""
        from src.pipeline.state import PipelineState
        from src.pipeline.orchestrator import PipelineRunner

        fixture_path = Path(__file__).parent / "fixtures" / "sample_script.json"
        self.assertTrue(fixture_path.exists(), f"Fixture missing: {fixture_path}")

        runner_telugu = PipelineRunner(
            state=MagicMock(),
            dry_run=False,
            language_code="te-IN",
        )
        runner_hindi = PipelineRunner(
            state=MagicMock(),
            dry_run=False,
            language_code="hi-IN",
        )

        with patch.object(runner_telugu, "state") as mock_state, patch.object(runner_telugu, "_execute_cmd") as mock_cmd, patch.object(runner_telugu, "_find_latest_file", return_value=Path("data/audio/out.json")):
            mock_state.get_output.return_value = str(fixture_path)
            runner_telugu.run_voice()
            cmd = mock_cmd.call_args[0][0]
            self.assertIn("--provider", cmd)
            idx = cmd.index("--provider")
            self.assertEqual(cmd[idx + 1], "pocket_tts")

        with patch.object(runner_hindi, "state") as mock_state, patch.object(runner_hindi, "_execute_cmd") as mock_cmd, patch.object(runner_hindi, "_find_latest_file", return_value=Path("data/audio/out.json")):
            mock_state.get_output.return_value = str(fixture_path)
            runner_hindi.run_voice()
            cmd = mock_cmd.call_args[0][0]
            self.assertIn("--provider", cmd)
            idx = cmd.index("--provider")
            self.assertEqual(cmd[idx + 1], "edge_neural_tts")


if __name__ == "__main__":
    unittest.main()
