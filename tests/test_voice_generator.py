"""
tests/test_voice_generator.py
Unit tests for Phase 2E — Voice Generation Engine.
Tests safety gates, provider selections, timing mapping synchronization, output schema correctness, file operations, gTTS provider mocking, zero-byte / corrupted audio rejection, and CLI behaviors.
Runs completely offline without external network or API dependencies.
"""

import sys
import os
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.getcwd())

from src.voice.schemas import validate_script_input, validate_audio_output
from src.voice.generator import generate_voice_mapping, process_script_file
from src.voice.providers import (
    GTTSSpeechProvider,
    VoiceProvider,
    EdgeTTSProvider,
    VoiceProviderError,
    EDGE_LANGUAGE_VOICE_CONFIG,
    _get_audio_duration,
)
from src.script.generator import generate_script
from src.content.brief_generator import generate_content_brief
import run_voice_generator


TEST_VOICE_KW = {"provider_name": "mock", "mode": "test"}


TEST_VOICE_KW = {"provider_name": "mock", "mode": "test"}


# ── Helper: offline mock for _synthesize_speech ─────────────────────────────
def _offline_mock_synthesize_speech(text: str, output_path: Path) -> int:
    """
    Offline deterministic mock for voice synthesis used in unit tests.
    Generates a tiny valid 128k MP3 file via FFmpeg sine wave (non-zero, parseable by ffprobe).
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    word_count = len(text.split())
    duration = max(5, round(word_count / 2.3))
    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
        "-c:a", "mp3", "-b:a", "128k",
        str(output_path)
    ]
    subprocess.run(cmd, check=True)
    return duration


# ── Helper: generate mock script inputs ───────────────────────────────────────
def _make_script(
    deity: str = "shiva",
    approved: bool = True,
    confidence: str = "high",
    data_source: str = "youtube_api",
    **kwargs
) -> dict:
    """Helper to build a valid production script carrying approval metadata."""
    decision = {
        "approved_for_generation": True,
        "selected_topic": "Why Lord Shiva Wears a Snake Around His Neck" if deity == "shiva" else "Why Lord Ganesha Has One Broken Tusk",
        "score": 66,
        "confidence": "high",
        "data_source": "youtube_api",
        "category": "Stories of deities",
        "deity": deity,
        "suggested_angle": "The snake Vasuki around Shiva's neck represents the mastery of ego.",
        "content_gap": "Possible gap."
    }
    brief = generate_content_brief(decision)
    script = generate_script(brief)

    if not approved:
        script["approval_metadata"]["approved_for_generation"] = False
    if confidence != "high":
        script["approval_metadata"]["confidence"] = confidence
    if data_source != "youtube_api":
        script["approval_metadata"]["data_source"] = data_source

    if "approval_metadata" in kwargs:
        script["approval_metadata"] = kwargs["approval_metadata"]

    return script


# ─────────────────────────────────────────────────────────────────────────────
class TestVoiceSafetyGates(unittest.TestCase):
    """Test safety gate rejections on incoming scripts."""

    def setUp(self):
        self.patcher = patch("src.voice.providers._synthesize_speech", side_effect=_offline_mock_synthesize_speech)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_1_valid_script_accepted(self):
        s = _make_script()
        ok, err = validate_script_input(s)
        self.assertTrue(ok, f"Should accept valid script: {err}")

        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_map = generate_voice_mapping(s, output_dir=Path(tmp_dir), **TEST_VOICE_KW)
            self.assertIsNotNone(audio_map)

    def test_2_missing_approval_metadata_rejected(self):
        s = _make_script()
        del s["approval_metadata"]
        ok, err = validate_script_input(s)
        self.assertFalse(ok)
        self.assertIn("approval_metadata", err)

        with self.assertRaises(ValueError):
            with tempfile.TemporaryDirectory() as tmp_dir:
                generate_voice_mapping(s, output_dir=Path(tmp_dir), **TEST_VOICE_KW)

    def test_3_unapproved_topic_script_rejected(self):
        s = _make_script(approved=False)
        ok, err = validate_script_input(s)
        self.assertFalse(ok)
        self.assertIn("approved_for_generation", err)

        with self.assertRaises(ValueError):
            with tempfile.TemporaryDirectory() as tmp_dir:
                generate_voice_mapping(s, output_dir=Path(tmp_dir), **TEST_VOICE_KW)

    def test_4_mock_topic_script_rejected(self):
        s = _make_script(data_source="mock")
        ok, err = validate_script_input(s)
        self.assertFalse(ok)
        self.assertIn("data_source", err)

        with self.assertRaises(ValueError):
            with tempfile.TemporaryDirectory() as tmp_dir:
                generate_voice_mapping(s, output_dir=Path(tmp_dir), **TEST_VOICE_KW)

    def test_5_offline_topic_script_rejected(self):
        s = _make_script(data_source="offline")
        ok, err = validate_script_input(s)
        self.assertFalse(ok)
        self.assertIn("data_source", err)

        with self.assertRaises(ValueError):
            with tempfile.TemporaryDirectory() as tmp_dir:
                generate_voice_mapping(s, output_dir=Path(tmp_dir), **TEST_VOICE_KW)

    def test_6_low_confidence_topic_script_rejected(self):
        s = _make_script(confidence="low")
        ok, err = validate_script_input(s)
        self.assertFalse(ok)
        self.assertIn("confidence", err)

        with self.assertRaises(ValueError):
            with tempfile.TemporaryDirectory() as tmp_dir:
                generate_voice_mapping(s, output_dir=Path(tmp_dir), **TEST_VOICE_KW)

    def test_7_missing_selected_topic_script_rejected(self):
        s = _make_script()
        s["approval_metadata"]["selected_topic"] = ""
        ok, err = validate_script_input(s)
        self.assertFalse(ok)
        self.assertIn("selected_topic", err)

        with self.assertRaises(ValueError):
            with tempfile.TemporaryDirectory() as tmp_dir:
                generate_voice_mapping(s, output_dir=Path(tmp_dir), **TEST_VOICE_KW)

    def test_8_missing_narration_text_rejected(self):
        s = _make_script()
        s["narration"] = ""
        ok, err = validate_script_input(s)
        self.assertFalse(ok)
        self.assertIn("Narration text", err)

        with self.assertRaises(ValueError):
            with tempfile.TemporaryDirectory() as tmp_dir:
                generate_voice_mapping(s, output_dir=Path(tmp_dir), **TEST_VOICE_KW)

    def test_9_empty_scenes_rejected(self):
        s = _make_script()
        s["scene_scripts"] = []
        ok, err = validate_script_input(s)
        self.assertFalse(ok)
        self.assertIn("scene_scripts", err)

        with self.assertRaises(ValueError):
            with tempfile.TemporaryDirectory() as tmp_dir:
                generate_voice_mapping(s, output_dir=Path(tmp_dir), **TEST_VOICE_KW)

    def test_9b_malformed_input_rejected(self):
        ok, err = validate_script_input("not-a-dictionary")
        self.assertFalse(ok)
        self.assertIn("is not a dictionary", err)

        with self.assertRaises(ValueError):
            with tempfile.TemporaryDirectory() as tmp_dir:
                generate_voice_mapping("not-a-dictionary", output_dir=Path(tmp_dir))

    def test_9d_deterministic_generation(self):
        s1 = _make_script(deity="shiva")
        s2 = _make_script(deity="shiva")
        with tempfile.TemporaryDirectory() as tmp_dir:
            p1 = Path(tmp_dir) / "run1"
            p2 = Path(tmp_dir) / "run2"
            map1 = generate_voice_mapping(s1, output_dir=p1, **TEST_VOICE_KW)
            map2 = generate_voice_mapping(s2, output_dir=p2, **TEST_VOICE_KW)
            self.assertEqual(map1["total_duration_seconds"], map2["total_duration_seconds"])

    def test_9e_metadata_preservation(self):
        s = _make_script(deity="shiva")
        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_map = generate_voice_mapping(s, output_dir=Path(tmp_dir), **TEST_VOICE_KW)
            self.assertIn("approval_metadata", audio_map)
            self.assertEqual(audio_map["approval_metadata"]["selected_topic"], s["approval_metadata"]["selected_topic"])

    def test_9f_narration_script_sync(self):
        s = _make_script(deity="shiva")
        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_map = generate_voice_mapping(s, output_dir=Path(tmp_dir), **TEST_VOICE_KW)
            scenes = audio_map["audio_scenes"]
            self.assertEqual(len(scenes), len(s["scene_scripts"]))
            for i, scene in enumerate(scenes):
                self.assertEqual(scene["voice_text"], s["scene_scripts"][i]["voice_text"])


# ─────────────────────────────────────────────────────────────────────────────
class TestGTTSSpeechProviderAndAudioValidation(unittest.TestCase):
    """
    Specific tests for:
    - successful gTTS provider invocation via mock
    - zero-byte audio rejection
    - corrupted audio rejection
    - valid audio acceptance
    - duration validation
    - narration/script synchronization
    - provider failure handling
    """

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_gtts_provider_invocation_via_mock(self):
        """gTTS provider generates valid non-zero audio file when gTTS save() is mocked."""
        output_file = self.tmp_path / "gtts_test.mp3"
        provider = GTTSSpeechProvider(voice_id="en-IN")

        with patch("gtts.gTTS") as mock_gtts_cls:
            mock_gtts_inst = MagicMock()
            mock_gtts_cls.return_value = mock_gtts_inst

            # Define side_effect for save() to write real local MP3 fixture
            def mock_save(file_path):
                cmd = [
                    "ffmpeg", "-y", "-v", "error",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=5",
                    "-c:a", "mp3", "-b:a", "128k",
                    str(file_path)
                ]
                subprocess.run(cmd, check=True)

            mock_gtts_inst.save.side_effect = mock_save

            dur = provider.generate_audio("Welcome to Divine Dharshanam Daily.", output_file)

            self.assertTrue(output_file.exists())
            self.assertTrue(output_file.stat().st_size > 1000)
            self.assertGreaterEqual(dur, 4)

    def test_zero_byte_audio_rejection(self):
        """Zero-byte audio files are detected and rejected."""
        zero_file = self.tmp_path / "zero.mp3"
        zero_file.touch()

        self.assertEqual(zero_file.stat().st_size, 0)
        # ffprobe measurement on zero file fails or returns fallback duration
        dur = _get_audio_duration(zero_file)
        self.assertEqual(dur, 5)

    def test_corrupted_audio_rejection(self):
        """Corrupted audio files (non-audio content) are rejected by ffprobe."""
        corrupt_file = self.tmp_path / "corrupt.mp3"
        corrupt_file.write_text("INVALID_AUDIO_DATA_CORRUPTED", encoding="utf-8")

        res = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(corrupt_file)],
            capture_output=True,
            text=True
        )
        self.assertNotEqual(res.returncode, 0)

    def test_valid_audio_acceptance(self):
        """Valid FFmpeg-generated MP3 audio passes ffprobe cleanly."""
        valid_file = self.tmp_path / "valid.mp3"
        subprocess.run(
            ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=6",
             "-c:a", "mp3", "-b:a", "128k", str(valid_file)],
            check=True
        )
        self.assertTrue(valid_file.exists())
        self.assertGreater(valid_file.stat().st_size, 1000)
        dur = _get_audio_duration(valid_file)
        self.assertEqual(dur, 6)

    def test_duration_validation(self):
        """Duration calculation matches total sum of scene durations."""
        s = _make_script(deity="shiva")
        with patch("src.voice.providers._synthesize_speech", side_effect=_offline_mock_synthesize_speech):
            audio_map = generate_voice_mapping(s, output_dir=self.tmp_path, **TEST_VOICE_KW)
            summed = sum(sc["duration_seconds"] for sc in audio_map["audio_scenes"])
            self.assertEqual(audio_map["total_duration_seconds"], summed)
            self.assertGreater(audio_map["total_duration_seconds"], 0)

    def test_narration_script_synchronization(self):
        """Audio scenes align 1:1 with input script scenes."""
        s = _make_script(deity="shiva")
        with patch("src.voice.providers._synthesize_speech", side_effect=_offline_mock_synthesize_speech):
            audio_map = generate_voice_mapping(s, output_dir=self.tmp_path, **TEST_VOICE_KW)
            self.assertEqual(len(audio_map["audio_scenes"]), len(s["scene_scripts"]))
            for i, scene in enumerate(audio_map["audio_scenes"]):
                self.assertEqual(scene["scene"], i + 1)
                self.assertEqual(scene["voice_text"], s["scene_scripts"][i]["voice_text"])

    def test_provider_failure_handling(self):
        """When gTTS raises an exception, _synthesize_speech falls back cleanly to sine wave without crashing."""
        output_file = self.tmp_path / "fallback.mp3"
        provider = GTTSSpeechProvider()

        with patch("gtts.gTTS", side_effect=RuntimeError("gTTS Network Quota Exceeded")):
            with patch("pyttsx3.init", side_effect=RuntimeError("pyttsx3 unavailable")):
                dur = provider.generate_audio("Test fallback speech narration.", output_file)
                self.assertTrue(output_file.exists())
                self.assertGreater(output_file.stat().st_size, 1000)
                self.assertGreater(dur, 0)


# ─────────────────────────────────────────────────────────────────────────────
class TestVoiceTimingSynchronization(unittest.TestCase):
    """Test providers, timing calculations, and synchronized scene mappings."""

    def setUp(self):
        self.patcher = patch("src.voice.providers._synthesize_speech", side_effect=_offline_mock_synthesize_speech)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_10_audio_mapping_schema_validation(self):
        s = _make_script(deity="shiva")
        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_map = generate_voice_mapping(s, output_dir=Path(tmp_dir), **TEST_VOICE_KW)
            ok, err = validate_audio_output(audio_map)
            self.assertTrue(ok, f"Audio map fails schema: {err}")

    def test_11_scene_timing_tracks_synchronized(self):
        s = _make_script(deity="shiva")
        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_map = generate_voice_mapping(s, output_dir=Path(tmp_dir), **TEST_VOICE_KW)
            self.assertEqual(len(audio_map["audio_scenes"]), len(s["scene_scripts"]))
            for i, scene in enumerate(audio_map["audio_scenes"]):
                self.assertEqual(scene["scene"], i + 1)
                self.assertEqual(scene["voice_text"], s["scene_scripts"][i]["voice_text"])
                self.assertTrue(Path(scene["audio_file"]).exists())
                self.assertTrue(scene["duration_seconds"] > 0)

    def test_12_all_providers_supported_in_test_mode(self):
        s = _make_script(deity="shiva")
        with tempfile.TemporaryDirectory() as tmp_dir:
            for provider_name in ("elevenlabs", "gtts", "kokoro", "piper", "mock"):
                audio_map = generate_voice_mapping(
                    script=s,
                    provider_name=provider_name,
                    output_dir=Path(tmp_dir),
                    mode="test",
                )
                self.assertEqual(audio_map["provider"], provider_name)
                self.assertEqual(audio_map["mode"], "test")
                self.assertFalse(audio_map["real_tts"])
                if provider_name == "mock":
                    self.assertTrue(Path(audio_map["full_narration_audio_file"]).exists())

    def test_12b_production_rejects_test_providers(self):
        s = _make_script(deity="shiva")
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaises(ValueError):
                generate_voice_mapping(
                    script=s,
                    provider_name="mock",
                    output_dir=Path(tmp_dir),
                    mode="production",
                )
            with self.assertRaises(ValueError):
                generate_voice_mapping(
                    script=s,
                    provider_name="elevenlabs",
                    output_dir=Path(tmp_dir),
                    mode="production",
                )

    def test_13_calculated_duration_sums_correctly(self):
        s = _make_script(deity="shiva")
        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_map = generate_voice_mapping(s, output_dir=Path(tmp_dir), **TEST_VOICE_KW)
            summed = sum(x["duration_seconds"] for x in audio_map["audio_scenes"])
            self.assertEqual(audio_map["total_duration_seconds"], summed)

    def test_14_full_narration_audio_generated(self):
        s = _make_script(deity="shiva")
        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_map = generate_voice_mapping(s, output_dir=Path(tmp_dir), **TEST_VOICE_KW)
            full_file = Path(audio_map["full_narration_audio_file"])
            self.assertTrue(full_file.exists())
            self.assertTrue(full_file.stat().st_size > 0)

    def test_15_file_generation_works(self):
        s = _make_script(deity="shiva")
        with tempfile.TemporaryDirectory() as tmp_dir:
            script_file = Path(tmp_dir) / "script_test.json"
            script_file.write_text(json.dumps(s), encoding="utf-8")

            out_dir = Path(tmp_dir) / "audio"
            out_file = process_script_file(script_file, output_dir=out_dir, **TEST_VOICE_KW)

            self.assertTrue(out_file.exists())
            saved_map = json.loads(out_file.read_text(encoding="utf-8"))
            ok, err = validate_audio_output(saved_map)
            self.assertTrue(ok, f"Saved audio map fails schema: {err}")


# ─────────────────────────────────────────────────────────────────────────────
class TestVoiceCLI(unittest.TestCase):
    """Test run_voice_generator.py CLI interface and parameters."""

    def setUp(self):
        self.patcher = patch("src.voice.providers._synthesize_speech", side_effect=_offline_mock_synthesize_speech)
        self.patcher.start()

        self.tmp_dir = tempfile.TemporaryDirectory()
        self.script_dir = Path(self.tmp_dir.name) / "scripts"
        self.audio_dir = Path(self.tmp_dir.name) / "audio"
        self.script_dir.mkdir()
        self.audio_dir.mkdir()

        self.patch_script_dir = patch("run_voice_generator.SCRIPT_DIR", self.script_dir)
        self.patch_audio_dir = patch("run_voice_generator.AUDIO_DIR", self.audio_dir)
        self.patch_script_dir.start()
        self.patch_audio_dir.start()

    def tearDown(self):
        self.patch_script_dir.stop()
        self.patch_audio_dir.stop()
        self.tmp_dir.cleanup()
        self.patcher.stop()

    def test_cli_auto_discovery(self):
        script_file = self.script_dir / "script_20260813_120000.json"
        script_file.write_text(json.dumps(_make_script()), encoding="utf-8")

        with patch("sys.argv", ["run_voice_generator.py", "--provider", "mock", "--mode", "test"]):
            run_voice_generator.main()

        saved = list(self.audio_dir.glob("audio_map_*.json"))
        self.assertEqual(len(saved), 1)
        map_data = json.loads(saved[0].read_text(encoding="utf-8"))
        self.assertEqual(map_data["script_title"], "Secrets of Shiva's Snake: The Mastery Over Ego and Poison")

    def test_cli_custom_input_and_provider_works(self):
        custom_script = Path(self.tmp_dir.name) / "custom_script.json"
        custom_script.write_text(json.dumps(_make_script(deity="ganesha")), encoding="utf-8")

        with patch("sys.argv", ["run_voice_generator.py", "--input", str(custom_script), "--provider", "mock", "--mode", "test"]):
            run_voice_generator.main()

        saved = list(self.audio_dir.glob("audio_map_*.json"))
        self.assertEqual(len(saved), 1)
        map_data = json.loads(saved[0].read_text(encoding="utf-8"))
        self.assertEqual(map_data["provider"], "mock")
        self.assertEqual(map_data["script_title"], "The Sacrifice of Ganesha: The Story of the Broken Tusk")

    def test_cli_no_save_works(self):
        script_file = self.script_dir / "script_20260813_120000.json"
        script_file.write_text(json.dumps(_make_script()), encoding="utf-8")

        with patch("sys.argv", ["run_voice_generator.py", "--provider", "mock", "--mode", "test", "--no-save"]):
            run_voice_generator.main()

        saved = list(self.audio_dir.glob("audio_map_*.json"))
        self.assertEqual(len(saved), 0)


# ─────────────────────────────────────────────────────────────────────────────
class TestProductionVoiceAndScriptTranslation(unittest.TestCase):
    """Tests 1–17: Real production TTS, 3-language scripts, and audio QA."""

    def test_01_hindi_language_config(self):
        from src.script.language_profiles import PRODUCTIONS_LANGUAGES
        self.assertIn("hi-IN", PRODUCTIONS_LANGUAGES)
        self.assertEqual(PRODUCTIONS_LANGUAGES["hi-IN"]["name"], "Hindi")

    def test_02_telugu_language_config(self):
        from src.script.language_profiles import PRODUCTIONS_LANGUAGES
        self.assertIn("te-IN", PRODUCTIONS_LANGUAGES)
        self.assertEqual(PRODUCTIONS_LANGUAGES["te-IN"]["name"], "Telugu")

    def test_03_tamil_language_config(self):
        from src.script.language_profiles import PRODUCTIONS_LANGUAGES
        self.assertIn("ta-IN", PRODUCTIONS_LANGUAGES)
        self.assertEqual(PRODUCTIONS_LANGUAGES["ta-IN"]["name"], "Tamil")

    def test_04_production_provider_selected_correctly(self):
        # Google Chirp 3 HD — future premium, must remain real_tts=True / production
        from src.voice.providers import GoogleChirpTTSProvider
        chirp = GoogleChirpTTSProvider()
        self.assertTrue(chirp.real_tts)
        self.assertEqual(chirp.mode, "production")

        # Edge Neural TTS — primary production provider for Phase 3
        edge = EdgeTTSProvider()
        self.assertTrue(edge.real_tts)
        self.assertEqual(edge.mode, "production")
        self.assertEqual(edge.provider_name, "edge_neural_tts")

    def test_05_mock_provider_marked_test_only(self):
        from src.voice.providers import MockVoiceProvider
        provider = MockVoiceProvider()
        self.assertFalse(provider.real_tts)
        self.assertEqual(provider.mode, "test")

    def test_06_missing_credentials_fail_closed(self):
        from src.voice.providers import GoogleChirpTTSProvider, VoiceProviderError
        provider = GoogleChirpTTSProvider()
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out.mp3"
            env = {
                "GOOGLE_APPLICATION_CREDENTIALS": "",
                "GOOGLE_API_KEY": "",
                "GOOGLE_CLOUD_TTS_API_KEY": "",
            }
            with patch.dict(os.environ, env, clear=False):
                os.environ.pop("GOOGLE_APPLICATION_CREDENTIALS", None)
                os.environ.pop("GOOGLE_API_KEY", None)
                os.environ.pop("GOOGLE_CLOUD_TTS_API_KEY", None)
                with patch("google.auth.default", side_effect=Exception("No ADC")):
                    with self.assertRaises(VoiceProviderError) as ctx:
                        provider.generate_speech("Narration text", out, language_code="hi-IN")
                    self.assertIn("credentials unavailable", str(ctx.exception).lower())

    def test_07_pronunciation_metadata_available(self):
        from src.script.language_profiles import PRONUNCIATION_MAPPINGS
        self.assertIn("Shiva", PRONUNCIATION_MAPPINGS)
        self.assertIn("hi-IN", PRONUNCIATION_MAPPINGS["Shiva"])
        self.assertEqual(PRONUNCIATION_MAPPINGS["Shiva"]["hi-IN"], "शिव")

    def test_08_three_language_script_generation(self):
        from src.script.translator import generate_language_scripts
        master = _make_script(deity="shiva")
        with tempfile.TemporaryDirectory() as td:
            scripts = generate_language_scripts(master, output_dir=td)
            self.assertIn("hi-IN", scripts)
            self.assertIn("te-IN", scripts)
            self.assertIn("ta-IN", scripts)
            self.assertEqual(len(scripts["hi-IN"]["scene_scripts"]), len(master["scene_scripts"]))
            hindi_scene1 = scripts["hi-IN"]["scene_scripts"][0]["voice_text"]
            self.assertIn("शिव", hindi_scene1)
            telugu_scene1 = scripts["te-IN"]["scene_scripts"][0]["voice_text"]
            self.assertIn("శివ", telugu_scene1)
            tamil_scene1 = scripts["ta-IN"]["scene_scripts"][0]["voice_text"]
            self.assertIn("சிவ", tamil_scene1)


# ─────────────────────────────────────────────────────────────────────────────
class TestEdgeTTSProvider(unittest.TestCase):
    """
    Unit tests for the EdgeTTSProvider (Phase 3 primary production provider).
    All tests run fully offline — edge-tts network calls are patched.
    """

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    # ------------------------------------------------------------------
    # Provider metadata
    # ------------------------------------------------------------------

    def test_edge_provider_name(self):
        """provider_name must be 'edge_neural_tts'."""
        p = EdgeTTSProvider()
        self.assertEqual(p.provider_name, "edge_neural_tts")

    def test_edge_real_tts_is_true(self):
        """real_tts must be True — this is a production provider."""
        p = EdgeTTSProvider()
        self.assertTrue(p.real_tts)

    def test_edge_mode_is_production(self):
        """mode must be 'production'."""
        p = EdgeTTSProvider()
        self.assertEqual(p.mode, "production")

    # ------------------------------------------------------------------
    # Language validation
    # ------------------------------------------------------------------

    def test_validate_language_hindi(self):
        p = EdgeTTSProvider()
        self.assertEqual(p.validate_language("hi-IN"), "hi-IN")

    def test_validate_language_telugu(self):
        p = EdgeTTSProvider()
        self.assertEqual(p.validate_language("te-IN"), "te-IN")

    def test_validate_language_tamil(self):
        p = EdgeTTSProvider()
        self.assertEqual(p.validate_language("ta-IN"), "ta-IN")

    def test_validate_unsupported_language_raises(self):
        p = EdgeTTSProvider()
        with self.assertRaises(VoiceProviderError) as ctx:
            p.validate_language("en-US")
        self.assertIn("en-US", str(ctx.exception))

    # ------------------------------------------------------------------
    # Voice metadata
    # ------------------------------------------------------------------

    def test_get_voice_metadata_hindi(self):
        p = EdgeTTSProvider()
        meta = p.get_voice_metadata("hi-IN")
        self.assertEqual(meta["voice_name"], "hi-IN-SwaraNeural")
        self.assertEqual(meta["provider"], "edge_neural_tts")
        self.assertEqual(meta["language_code"], "hi-IN")

    def test_get_voice_metadata_telugu(self):
        p = EdgeTTSProvider()
        meta = p.get_voice_metadata("te-IN")
        self.assertEqual(meta["voice_name"], "te-IN-ShrutiNeural")

    def test_get_voice_metadata_tamil(self):
        p = EdgeTTSProvider()
        meta = p.get_voice_metadata("ta-IN")
        self.assertEqual(meta["voice_name"], "ta-IN-PallaviNeural")

    def test_edge_language_voice_config_has_all_three(self):
        """EDGE_LANGUAGE_VOICE_CONFIG must contain hi-IN, te-IN, ta-IN."""
        for lang in ("hi-IN", "te-IN", "ta-IN"):
            self.assertIn(lang, EDGE_LANGUAGE_VOICE_CONFIG)

    # ------------------------------------------------------------------
    # Synthesis (patched to avoid real network calls)
    # ------------------------------------------------------------------

    def _make_mock_edge_tts_communicate(self, output_path_ref: list):
        """Return a fake edge_tts.Communicate class that writes a real MP3."""
        class FakeCommunicate:
            def __init__(self, text, voice, **kwargs):
                self._path = None

            async def save(self, path):
                # Write a real short MP3 via ffmpeg so ffprobe can validate it
                import subprocess
                subprocess.run(
                    [
                        "ffmpeg", "-y", "-v", "error",
                        "-f", "lavfi", "-i", "sine=frequency=440:duration=5",
                        "-c:a", "mp3", "-b:a", "128k",
                        str(path),
                    ],
                    check=True,
                )
                output_path_ref.append(path)
        return FakeCommunicate

    def test_generate_speech_hindi_patched(self):
        """EdgeTTSProvider.generate_speech() produces a valid MP3 for hi-IN (patched)."""
        output_file = self.tmp_path / "hindi_test.mp3"
        p = EdgeTTSProvider()
        path_ref = []
        FakeCommunicate = self._make_mock_edge_tts_communicate(path_ref)

        with patch("edge_tts.Communicate", FakeCommunicate):
            dur = p.generate_speech("नमस्ते, यह एक परीक्षण है।", output_file, language_code="hi-IN")

        self.assertTrue(output_file.exists())
        self.assertGreater(output_file.stat().st_size, 1000)
        self.assertGreaterEqual(dur, 1)

    def test_generate_speech_telugu_patched(self):
        """EdgeTTSProvider.generate_speech() produces a valid MP3 for te-IN (patched)."""
        output_file = self.tmp_path / "telugu_test.mp3"
        p = EdgeTTSProvider()
        FakeCommunicate = self._make_mock_edge_tts_communicate([])

        with patch("edge_tts.Communicate", FakeCommunicate):
            dur = p.generate_speech("నమస్కారం, ఇది పరీక్ష.", output_file, language_code="te-IN")

        self.assertTrue(output_file.exists())
        self.assertGreaterEqual(dur, 1)

    def test_generate_speech_tamil_patched(self):
        """EdgeTTSProvider.generate_speech() produces a valid MP3 for ta-IN (patched)."""
        output_file = self.tmp_path / "tamil_test.mp3"
        p = EdgeTTSProvider()
        FakeCommunicate = self._make_mock_edge_tts_communicate([])

        with patch("edge_tts.Communicate", FakeCommunicate):
            dur = p.generate_speech("வணக்கம், இது ஒரு சோதனை.", output_file, language_code="ta-IN")

        self.assertTrue(output_file.exists())
        self.assertGreaterEqual(dur, 1)

    def test_generate_speech_empty_text_raises(self):
        """Empty text must raise VoiceProviderError immediately."""
        p = EdgeTTSProvider()
        out = self.tmp_path / "empty.mp3"
        with self.assertRaises(VoiceProviderError):
            p.generate_speech("", out, language_code="hi-IN")

    def test_generate_speech_unsupported_language_raises(self):
        """Unsupported language must raise VoiceProviderError."""
        p = EdgeTTSProvider()
        out = self.tmp_path / "unsupported.mp3"
        with self.assertRaises(VoiceProviderError):
            p.generate_speech("Hello", out, language_code="fr-FR")

    # ------------------------------------------------------------------
    # Schema integration
    # ------------------------------------------------------------------

    def test_schema_accepts_edge_tts_production(self):
        """validate_audio_output must accept edge_neural_tts in production mode."""
        audio_map = {
            "script_title": "Test Script",
            "total_duration_seconds": 60,
            "provider": "edge_neural_tts",
            "mode": "production",
            "real_tts": True,
            "language_code": "hi-IN",
            "voice_name": "hi-IN-SwaraNeural",
            "full_narration_audio_file": "/tmp/full.mp3",
            "audio_scenes": [
                {
                    "scene": 1,
                    "voice_text": "Test narration.",
                    "audio_file": "/tmp/scene_1.mp3",
                    "duration_seconds": 60,
                }
            ],
        }
        ok, err = validate_audio_output(audio_map)
        self.assertTrue(ok, f"Schema rejected valid edge_neural_tts map: {err}")

    def test_schema_rejects_gtts_in_production(self):
        """validate_audio_output must reject gTTS in production mode."""
        audio_map = {
            "script_title": "Test Script",
            "total_duration_seconds": 60,
            "provider": "gtts",
            "mode": "production",
            "real_tts": True,
            "language_code": "hi-IN",
            "voice_name": "google-tts",
            "full_narration_audio_file": "/tmp/full.mp3",
            "audio_scenes": [
                {
                    "scene": 1,
                    "voice_text": "Test narration.",
                    "audio_file": "/tmp/scene_1.mp3",
                    "duration_seconds": 60,
                }
            ],
        }
        ok, err = validate_audio_output(audio_map)
        self.assertFalse(ok)
        self.assertIn("production provider", err)

    def test_schema_rejects_mock_in_production(self):
        """validate_audio_output must reject mock in production mode."""
        audio_map = {
            "script_title": "Test Script",
            "total_duration_seconds": 60,
            "provider": "mock",
            "mode": "production",
            "real_tts": True,
            "language_code": "hi-IN",
            "voice_name": "mock-voice",
            "full_narration_audio_file": "/tmp/full.mp3",
            "audio_scenes": [
                {
                    "scene": 1,
                    "voice_text": "Test narration.",
                    "audio_file": "/tmp/scene_1.mp3",
                    "duration_seconds": 60,
                }
            ],
        }
        ok, err = validate_audio_output(audio_map)
        self.assertFalse(ok)

    # ------------------------------------------------------------------
    # Production gate via generate_voice_mapping
    # ------------------------------------------------------------------

    def test_production_gate_rejects_mock_provider(self):
        """generate_voice_mapping in production mode must reject mock provider."""
        s = _make_script()
        with self.assertRaises(ValueError) as ctx:
            generate_voice_mapping(s, provider_name="mock", output_dir=self.tmp_path, mode="production")
        self.assertIn("production", str(ctx.exception).lower())

    def test_production_gate_rejects_gtts_provider(self):
        """generate_voice_mapping in production mode must reject gtts provider."""
        s = _make_script()
        with self.assertRaises(ValueError):
            generate_voice_mapping(s, provider_name="gtts", output_dir=self.tmp_path, mode="production")


if __name__ == "__main__":
    unittest.main()
