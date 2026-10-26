# tests/test_multilingual_gemini.py
# Comprehensive Unit & Regression Tests for:
# 1. Google Gemini API Integration & Redaction Security
# 2. Voice Provider Fallback Chain (Edge TTS -> Kokoro -> Piper)
# 3. Indic Font Resolver & Safe Fallback
# 4. Fail-Closed Language QA & Format Consistency (Old vs Narrated)
# 5. YouTube Metadata Localized Generation

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

from src.content.gemini_provider import (
    GeminiAuthError,
    GeminiModelNotFoundError,
    GeminiProviderError,
    GeminiRateLimitError,
    _build_generation_config,
    _clean_json_markdown,
    _redact_key,
    call_gemini_api,
    generate_brief_with_gemini,
    generate_script_with_gemini,
    validate_indic_script,
)
from src.content.brief_generator import generate_content_brief
from src.publisher.metadata import build_video_metadata
from src.qa.checks import check_format_consistency, check_language_consistency
from src.script.generator import generate_script
from src.video.effects import resolve_caption_font
from src.voice.generator import (
    PRODUCTION_FALLBACK_CHAIN,
    _get_fallback_candidates,
    _resolve_language,
    _resolve_voice_config,
    _try_fallback_chain,
    generate_voice_mapping,
)
from src.voice.providers import (
    EDGE_LANGUAGE_VOICE_CONFIG,
    KOKORO_LANGUAGE_VOICE_CONFIG,
    PIPER_LANGUAGE_VOICE_CONFIG,
    EdgeTTSProvider,
    KokoroProvider,
    PiperProvider,
    VoiceProviderError,
)


# =============================================================================
# 1. Google Gemini Provider & Redaction Security Tests
# =============================================================================

class TestGeminiProviderAndSecurity(unittest.TestCase):
    """Verifies Gemini REST client, model configs, redaction, and error distinction."""

    def test_clean_json_markdown(self):
        self.assertEqual(_clean_json_markdown('{"a": 1}'), '{"a": 1}')
        self.assertEqual(_clean_json_markdown('```json\n{"a": 1}\n```'), '{"a": 1}')
        self.assertEqual(_clean_json_markdown('```\n{"a": 1}\n```'), '{"a": 1}')

    def test_redact_key(self):
        secret = "AIzaSyDummySecretKey1234567890abcdef"
        msg = f"Failed to connect using key {secret} at https://api.google.com?key={secret}"
        redacted = _redact_key(msg, secret)
        self.assertNotIn(secret, redacted)
        self.assertIn("[REDACTED_API_KEY]", redacted)

    def test_build_generation_config_model_aware(self):
        # Gemini 3.x / 4.x must omit temperature
        cfg_3 = _build_generation_config("gemini-3.5-flash-lite")
        self.assertNotIn("temperature", cfg_3)
        self.assertEqual(cfg_3["responseMimeType"], "application/json")

        cfg_4 = _build_generation_config("gemini-4-flash")
        self.assertNotIn("temperature", cfg_4)

        # Older Gemini 2.x models retain temperature
        cfg_2 = _build_generation_config("gemini-2.5-flash-lite")
        self.assertIn("temperature", cfg_2)
        self.assertEqual(cfg_2["responseMimeType"], "application/json")

    def test_validate_indic_script(self):
        self.assertTrue(validate_indic_script("भगवान शिव की कथा", "hi-IN"))
        self.assertFalse(validate_indic_script("Pure English Title", "hi-IN"))
        self.assertTrue(validate_indic_script("పరమశివుని దివ్య లీలలు", "te-IN"))
        self.assertFalse(validate_indic_script("Pure English Title", "te-IN"))
        self.assertFalse(validate_indic_script("", "hi-IN"))

    @patch("src.content.gemini_provider.requests.post")
    def test_call_gemini_api_uses_header_auth(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": '{"result": "ok"}'}]}}]
        }
        mock_post.return_value = mock_resp

        secret_key = "AIzaSyTestSecretKeyXYZ1234567890"
        result = call_gemini_api("Test prompt", api_key=secret_key, model="gemini-2.5-flash-lite")
        self.assertEqual(result, '{"result": "ok"}')

        # Check call arguments: key must be in headers, NOT in URL query string
        args, kwargs = mock_post.call_args
        call_url = args[0]
        call_headers = kwargs["headers"]
        self.assertNotIn(secret_key, call_url)
        self.assertEqual(call_headers["x-goog-api-key"], secret_key)

    @patch("src.content.gemini_provider.requests.post")
    def test_call_gemini_api_auth_error_redacted(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        secret_key = "AIzaSySecretAuthFailureKey1234"
        mock_resp.text = f"Invalid API key {secret_key}"
        mock_post.return_value = mock_resp

        with self.assertRaises(GeminiAuthError) as ctx:
            call_gemini_api("Test prompt", api_key=secret_key)
        # Verify secret key is never present in exception string
        self.assertNotIn(secret_key, str(ctx.exception))
        self.assertIn("[REDACTED_API_KEY]", str(ctx.exception))

    @patch("src.content.gemini_provider.requests.post")
    def test_call_gemini_api_rate_limit(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.text = "Quota exceeded"
        mock_post.return_value = mock_resp

        with self.assertRaises(GeminiRateLimitError):
            call_gemini_api("Test prompt", api_key="dummy_key")

    @patch("src.content.gemini_provider.requests.post")
    def test_call_gemini_api_model_not_found(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.text = "Model not found"
        mock_post.return_value = mock_resp

        with self.assertRaises(GeminiProviderError):
            call_gemini_api("Test prompt", api_key="dummy_key")

    @patch("src.content.gemini_provider.requests.post")
    def test_call_gemini_api_malformed_response(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"candidates": []}
        mock_post.return_value = mock_resp

        with self.assertRaises(GeminiProviderError) as ctx:
            call_gemini_api("Test prompt", api_key="dummy_key")
        self.assertIn("no candidates", str(ctx.exception))

    @patch("src.content.gemini_provider.requests.post")
    def test_call_gemini_api_handles_empty_env_model_gracefully(self, mock_post):
        """Verifies that an empty GEMINI_MODEL env var falls back to default and avoids empty URL."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": '{"result": "ok"}'}]}}]
        }
        mock_post.return_value = mock_resp

        with patch.dict("os.environ", {"GEMINI_MODEL": "", "GEMINI_API_KEY": "test_key"}):
            result = call_gemini_api("Test prompt")
            self.assertEqual(result, '{"result": "ok"}')
            args, _ = mock_post.call_args
            call_url = args[0]
            # Ensure the model in URL is never empty (not ".../models/:generateContent")
            self.assertNotIn("/models/:generateContent", call_url)
            self.assertIn("/models/gemini-", call_url)

    @patch("src.content.gemini_provider.requests.post")
    def test_call_gemini_api_fallback_ordering_on_404(self, mock_post):
        """Verifies fallback ordering: 404 on gemini-2.5-flash-lite transitions cleanly to gemini-3.5-flash-lite."""
        resp_404 = MagicMock()
        resp_404.status_code = 404
        resp_404.text = "Model gemini-2.5-flash-lite not found or not enabled for project"

        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": '{"fallback": "success"}'}]}}]
        }

        mock_post.side_effect = [resp_404, resp_200]

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test_key", "GEMINI_MODEL": "gemini-2.5-flash-lite"}):
            result = call_gemini_api("Test prompt")
            self.assertEqual(result, '{"fallback": "success"}')
            self.assertEqual(mock_post.call_count, 2)
            first_url = mock_post.call_args_list[0][0][0]
            second_url = mock_post.call_args_list[1][0][0]
            self.assertIn("models/gemini-2.5-flash-lite:", first_url)
            self.assertIn("models/gemini-3.5-flash-lite:", second_url)

    @patch("src.content.gemini_provider.requests.post")
    def test_call_gemini_api_auth_error_fails_closed_without_candidate_cycling(self, mock_post):
        """Verifies HTTP 401/403 fails immediately with GeminiAuthError without cycling fallback models."""
        resp_401 = MagicMock()
        resp_401.status_code = 401
        resp_401.text = "API_KEY_INVALID"
        mock_post.return_value = resp_401

        with patch.dict("os.environ", {"GEMINI_API_KEY": "invalid_key"}):
            with self.assertRaises(GeminiAuthError) as ctx:
                call_gemini_api("Test prompt")
            self.assertIn("authentication failed", str(ctx.exception))
            # Must not cycle through candidate models when authentication is invalid
            self.assertEqual(mock_post.call_count, 1)

    @patch("src.content.gemini_provider.requests.post")
    def test_call_gemini_api_full_candidate_sequence_on_404(self, mock_post):
        """Verifies full sequence: 404 on each candidate exhausts the list in order without using 2.0-flash."""
        resp_404 = MagicMock()
        resp_404.status_code = 404
        resp_404.text = "Model not found or access restricted"
        mock_post.return_value = resp_404

        with patch.dict("os.environ", {"GEMINI_API_KEY": "test_key", "GEMINI_MODEL": "gemini-2.5-flash-lite"}):
            with self.assertRaises(GeminiProviderError) as ctx:
                call_gemini_api("Test prompt")
            self.assertIn("HTTP 404", str(ctx.exception))
            self.assertEqual(mock_post.call_count, 3)
            urls = [call[0][0] for call in mock_post.call_args_list]
            self.assertIn("models/gemini-2.5-flash-lite:", urls[0])
            self.assertIn("models/gemini-3.5-flash-lite:", urls[1])
            self.assertIn("models/gemini-3.5-flash:", urls[2])
            for u in urls:
                self.assertNotIn("gemini-2.0-flash", u)

    def test_call_gemini_api_no_key_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(GeminiProviderError) as ctx:
                call_gemini_api("Test", api_key="")
            self.assertIn("GEMINI_API_KEY is not set or empty", str(ctx.exception))

    def test_unsupported_language_fails_closed(self):
        with self.assertRaises(GeminiProviderError):
            generate_brief_with_gemini({}, language_code="en-US", allow_fallback=False)
        with self.assertRaises(GeminiProviderError):
            generate_script_with_gemini({}, language_code="fr-FR", allow_fallback=False)

    def test_offline_brief_and_script_attribution(self):
        decision = {
            "selected_topic": "శివుడు",
            "deity": "Lord Shiva",
            "approved_for_generation": True,
            "score": 85,
            "confidence": "high",
            "data_source": "youtube_api",
            "category": "mythology",
            "suggested_angle": "wisdom",
            "content_gap": "gap",
        }
        with patch.dict("os.environ", {"GEMINI_API_KEY": ""}):
            brief = generate_brief_with_gemini(decision, language_code="te-IN", allow_fallback=True)
            self.assertEqual(brief["language_code"], "te-IN")
            self.assertEqual(brief["generation_source"], "template_fallback")

            script = generate_script_with_gemini(brief, language_code="te-IN", allow_fallback=True)
            self.assertEqual(script["language_code"], "te-IN")
            self.assertEqual(script["generation_source"], "template_fallback")


# =============================================================================
# 2. Voice Provider Fallback Chain Tests
# =============================================================================

class TestVoiceProviderFallbackChain(unittest.TestCase):
    """Verifies Edge TTS -> Kokoro -> Piper fallback without recursive loops."""

    def test_fallback_candidates_order(self):
        self.assertEqual(_get_fallback_candidates("edge_neural_tts"), ["kokoro", "piper"])
        self.assertEqual(_get_fallback_candidates("kokoro"), ["piper"])
        self.assertEqual(_get_fallback_candidates("piper"), [])
        self.assertEqual(
            _get_fallback_candidates("google_chirp3_hd"),
            ["edge_neural_tts", "kokoro", "piper"],
        )

    def test_voice_configs_for_hindi_and_telugu(self):
        cfg_edge_hi = _resolve_voice_config({}, "hi-IN", "edge_neural_tts")
        self.assertEqual(cfg_edge_hi["voice_name"], "hi-IN-SwaraNeural")

        cfg_edge_te = _resolve_voice_config({}, "te-IN", "edge_neural_tts")
        self.assertEqual(cfg_edge_te["voice_name"], "te-IN-ShrutiNeural")

        cfg_kokoro_hi = _resolve_voice_config({}, "hi-IN", "kokoro")
        self.assertEqual(cfg_kokoro_hi["voice_name"], "hf_indic_hindi")

        cfg_piper_te = _resolve_voice_config({}, "te-IN", "piper")
        self.assertEqual(cfg_piper_te["voice_name"], "te_IN-indic-medium")

    def test_voice_generator_rejects_english_language(self):
        with self.assertRaises(ValueError):
            _resolve_language({"language_code": "en-US"})
        with self.assertRaises(ValueError):
            _resolve_language({"language_code": "en-IN"})

    @patch("src.voice.providers.edge_tts.EdgeTTSProvider.generate_speech")
    def test_edge_tts_primary_success(self, mock_edge):
        mock_edge.return_value = 10
        with tempfile.TemporaryDirectory() as td:
            out_file = Path(td) / "test.mp3"
            provider = EdgeTTSProvider()
            dur = provider.generate_speech("शिव कथा", out_file, language_code="hi-IN")
            self.assertEqual(dur, 10)

    @patch("src.voice.providers.edge_tts.EdgeTTSProvider.generate_speech")
    @patch("src.voice.providers.google_chirp.KokoroProvider.generate_speech")
    def test_edge_tts_fails_kokoro_succeeds(self, mock_kokoro, mock_edge):
        mock_edge.side_effect = VoiceProviderError("Edge network unavailable")
        mock_kokoro.return_value = 12

        with tempfile.TemporaryDirectory() as td:
            out_file = Path(td) / "test.mp3"
            used_provider, dur = _try_fallback_chain(
                "నమః శివాయ",
                out_file,
                language_code="te-IN",
                voice_config={},
                primary_name="edge_neural_tts",
                primary_error="Edge network timeout",
                mode="test",
            )
            self.assertEqual(used_provider, "kokoro")
            self.assertEqual(dur, 12)

    @patch("src.voice.providers.edge_tts.EdgeTTSProvider.generate_speech")
    @patch("src.voice.providers.google_chirp.KokoroProvider.generate_speech")
    @patch("src.voice.providers.google_chirp.PiperProvider.generate_speech")
    def test_edge_and_kokoro_fail_piper_succeeds(self, mock_piper, mock_kokoro, mock_edge):
        mock_edge.side_effect = VoiceProviderError("Edge down")
        mock_kokoro.side_effect = VoiceProviderError("Kokoro model not found")
        mock_piper.return_value = 15

        with tempfile.TemporaryDirectory() as td:
            out_file = Path(td) / "test.mp3"
            used_provider, dur = _try_fallback_chain(
                "शिव शम्भू",
                out_file,
                language_code="hi-IN",
                voice_config={},
                primary_name="edge_neural_tts",
                primary_error="Edge down",
                mode="test",
            )
            self.assertEqual(used_provider, "piper")
            self.assertEqual(dur, 15)

    def test_piper_primary_fails_no_further_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            out_file = Path(td) / "test.mp3"
            with self.assertRaises(VoiceProviderError) as ctx:
                _try_fallback_chain(
                    "నమః శివాయ",
                    out_file,
                    language_code="te-IN",
                    voice_config={},
                    primary_name="piper",
                    primary_error="Piper binary crashed",
                    mode="production",
                )
            self.assertIn("no further fallback providers", str(ctx.exception))

    @patch("src.voice.providers.google_chirp.KokoroProvider.generate_speech")
    @patch("src.voice.providers.google_chirp.PiperProvider.generate_speech")
    def test_kokoro_primary_fails_piper_succeeds(self, mock_piper, mock_kokoro):
        mock_kokoro.side_effect = VoiceProviderError("Kokoro failed")
        mock_piper.return_value = 8

        with tempfile.TemporaryDirectory() as td:
            out_file = Path(td) / "test.mp3"
            used_provider, dur = _try_fallback_chain(
                "ఓం నమః శివాయ",
                out_file,
                language_code="te-IN",
                voice_config={},
                primary_name="kokoro",
                primary_error="Kokoro failed",
                mode="test",
            )
            self.assertEqual(used_provider, "piper")
            self.assertEqual(dur, 8)


# =============================================================================
# 3. Indic Font Resolver Tests
# =============================================================================

class TestIndicFontResolver(unittest.TestCase):
    """Verifies platform Indic font resolution, existence checks, and overrides."""

    def test_unsupported_language_raises_value_error(self):
        with self.assertRaises(ValueError):
            resolve_caption_font("fr-FR")

    def test_explicit_font_path_existing(self):
        with tempfile.NamedTemporaryFile(suffix=".ttf") as tmp:
            font_path = resolve_caption_font("hi-IN", explicit_font_path=tmp.name)
            self.assertTrue(Path(font_path).exists())

    def test_explicit_font_path_nonexistent_raises(self):
        with self.assertRaises(FileNotFoundError):
            resolve_caption_font("hi-IN", explicit_font_path="C:/nonexistent/font.ttf")

    def test_env_var_override(self):
        with tempfile.NamedTemporaryFile(suffix=".ttf") as tmp:
            with patch.dict("os.environ", {"HINDI_FONT_PATH": tmp.name}):
                font_path = resolve_caption_font("hi-IN")
                self.assertEqual(Path(font_path).resolve(), Path(tmp.name).resolve())

    def test_missing_font_behavior_raise_on_missing(self):
        # When no candidate font exists and raise_on_missing is True
        with patch("pathlib.Path.exists", return_value=False):
            with self.assertRaises(RuntimeError) as ctx:
                resolve_caption_font("te-IN", raise_on_missing=True)
            self.assertIn("No suitable Indic font found", str(ctx.exception))


# =============================================================================
# 4. QA Checks: Language & Format Consistency Tests
# =============================================================================

class TestLanguageAndFormatQAChecks(unittest.TestCase):
    """Verifies fail-closed language validation and old vs narrated format rules."""

    def test_missing_language_code_fails_qa(self):
        manifests = {
            "script": {"title": "शिव"},
            "audio_map": {"language_code": "hi-IN"},
        }
        ok, err = check_language_consistency(manifests, expected_language="hi-IN")
        self.assertFalse(ok)
        self.assertIn("Missing language_code", err)

    def test_unsupported_language_code_fails_qa(self):
        manifests = {
            "script": {"language_code": "en-US"},
            "audio_map": {"language_code": "en-US"},
        }
        ok, err = check_language_consistency(manifests)
        self.assertFalse(ok)
        self.assertIn("Unsupported language", err)

    def test_language_mismatch_fails_qa(self):
        manifests = {
            "script": {"language_code": "hi-IN"},
            "audio_map": {"language_code": "te-IN"},
        }
        ok, err = check_language_consistency(manifests, expected_language="hi-IN")
        self.assertFalse(ok)
        self.assertIn("Language mismatch", err)

    def test_pure_english_script_fails_indic_qa(self):
        manifests = {
            "script": {
                "language_code": "hi-IN",
                "title": "Lord Shiva Story",
                "narration": "This is completely in English without Devanagari script.",
            },
            "audio_map": {"language_code": "hi-IN"},
        }
        ok, err = check_language_consistency(manifests, expected_language="hi-IN")
        self.assertFalse(ok)
        self.assertIn("lacks Devanagari", err)

    def test_old_format_passes_music_only_no_captions(self):
        manifests = {
            "audio_map": {
                "format": "old",
                "audio_type": "music_only",
                "voice_name": "none",
                "bgm_title": "Divine Flute",
                "bgm_deity": "krishna",
            },
            "video_map": {
                "has_captions": False,
                "caption_text_file": None,
            },
        }
        ok, detail = check_format_consistency(manifests, expected_format="old")
        self.assertTrue(ok)
        self.assertIn("old format", detail)

    def test_old_format_fails_if_voice_or_captions_present(self):
        # Case 1: Voice is present
        manifests_voice = {
            "audio_map": {
                "format": "old",
                "audio_type": "music_only",
                "voice_name": "hi-IN-SwaraNeural",
                "bgm_title": "Flute",
            },
            "video_map": {},
        }
        ok1, err1 = check_format_consistency(manifests_voice, expected_format="old")
        self.assertFalse(ok1)
        self.assertIn("must not contain voice narration", err1)

        # Case 2: Captions are present
        manifests_captions = {
            "audio_map": {
                "format": "old",
                "audio_type": "music_only",
                "voice_name": "none",
                "bgm_title": "Flute",
            },
            "video_map": {
                "caption_text_file": "captions.txt",
            },
        }
        ok2, err2 = check_format_consistency(manifests_captions, expected_format="old")
        self.assertFalse(ok2)
        self.assertIn("must not contain subtitles, captions", err2)

    def test_narrated_format_fails_if_music_only(self):
        manifests = {
            "audio_map": {
                "audio_type": "music_only",
                "voice_name": "none",
            },
        }
        ok, err = check_format_consistency(manifests, expected_format="narrated")
        self.assertFalse(ok)
        self.assertIn("cannot use audio_type='music_only'", err)


# =============================================================================
# 5. YouTube Localized Metadata Tests
# =============================================================================

class TestYouTubeMetadataLocalization(unittest.TestCase):
    """Verifies that generated YouTube metadata is genuinely Hindi or Telugu."""

    def test_hindi_metadata_generation(self):
        qa = {
            "selected_topic": "भगवान शिव और नाग वासुकि",
            "language_code": "hi-IN",
            "content_type": "short",
            "artifacts": {},
        }
        meta = build_video_metadata(qa)
        self.assertEqual(meta["language_code"], "hi-IN")
        self.assertEqual(meta["default_language"], "hi")
        self.assertEqual(meta["default_audio_language"], "hi")
        self.assertIn("दिव्य दर्शनम्", meta["description"])
        self.assertIn("#सनातनधर्म", meta["description"])
        self.assertIn("सनातन धर्म", meta["tags"])

    def test_telugu_metadata_generation(self):
        qa = {
            "selected_topic": "వినాయకుని ఏకదంత రహస్యం",
            "language_code": "te-IN",
            "content_type": "short",
            "artifacts": {},
        }
        meta = build_video_metadata(qa)
        self.assertEqual(meta["language_code"], "te-IN")
        self.assertEqual(meta["default_language"], "te")
        self.assertEqual(meta["default_audio_language"], "te")
        self.assertIn("దివ్య దర్శనం", meta["description"])
        self.assertIn("#భారతీయపురాణాలు", meta["description"])
        self.assertIn("తెలుగు భక్తి", meta["tags"])


if __name__ == "__main__":
    unittest.main()
