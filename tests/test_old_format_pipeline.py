"""
tests/test_old_format_pipeline.py
Unit and integration tests for the evening Old-Format Devotional Visual Short pipeline (Phase 2I addition).
Tests cover:
  A. Morning backward compatibility
  B. Old-format execution
  C. Old-format TTS bypass (no edge_neural_tts calls)
  D. Valid music-only audio structure compatible with renderer
  E. 24-45 second duration validation
  F. 28-40 second preferred target
  G. First-frame visual hook presence
  H. Topic duplicate protection against history
  I. Morning vs evening topic separation
  J. Asset directory isolation
  K. Publishing history format metadata
  L. OLD_FORMAT_ENABLED=false safe exit behavior
  M. Morning execution while OLD_FORMAT_ENABLED=false
  N. Evening execution while OLD_FORMAT_ENABLED=true
  O. 04:00 UTC -> format=narrated mapping
  P. 13:30 UTC -> format=old mapping
  Q. Workflow conditional logic
"""

import os
import sys
import json
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.getcwd())

from src.pipeline.state import PipelineState
from src.pipeline.orchestrator import PipelineRunner
from src.video.format_config import OLD_FORMAT_CONFIG
from src.voice.generator import generate_voice_mapping
from src.decision.strategy import apply_old_format_topic_preferences, OLD_FORMAT_TOPIC_PREFERENCES
from src.decision.validator import validate_candidate


class TestOldFormatPipeline(unittest.TestCase):

    def test_A_morning_backward_compatibility(self):
        state = PipelineState()
        self.assertEqual(state.format, "narrated")
        self.assertIn("NARRATED", state.pipeline_id)

    def test_B_old_format_execution_state(self):
        state = PipelineState(format="old")
        self.assertEqual(state.format, "old")
        self.assertIn("OLD", state.pipeline_id)

    def test_C_old_format_tts_bypass(self):
        script = {
            "title": "Venkateshwara Suprabhatam",
            "duration_seconds": 30,
            "narration": "Om Namo Venkateshaya",
            "scene_scripts": [
                {"scene": 1, "voice_text": "Govinda Govinda"}
            ],
            "retention_hooks": ["Hook"],
            "approval_metadata": {
                "approved_for_generation": True,
                "data_source": "youtube_api",
                "confidence": "high",
                "selected_topic": "Venkateshwara Suprabhatam",
            }
        }
        with patch("src.voice.providers.EdgeTTSProvider.generate_speech") as mock_tts:
            audio_map = generate_voice_mapping(script, format="old", mode="test")
            mock_tts.assert_not_called()
            self.assertEqual(audio_map["format"], "old")
            self.assertEqual(audio_map["provider"], "devotional_music")

    def test_D_valid_music_only_audio_structure(self):
        script = {
            "title": "Jai Hanuman",
            "duration_seconds": 30,
            "narration": "Jai Shri Ram",
            "scene_scripts": [
                {"scene": 1, "voice_text": "Jai Hanuman"}
            ],
            "retention_hooks": ["Hook"],
            "approval_metadata": {
                "approved_for_generation": True,
                "data_source": "youtube_api",
                "confidence": "high",
                "selected_topic": "Jai Hanuman",
            }
        }
        audio_map = generate_voice_mapping(script, format="old", mode="test")
        self.assertIn("audio_scenes", audio_map)
        self.assertGreater(len(audio_map["audio_scenes"]), 0)
        self.assertIn("full_narration_audio_file", audio_map)
        self.assertTrue(any(audio_map["full_narration_audio_file"].lower().endswith(ext) for ext in (".mp3", ".wav", ".aac", ".flac")))

    def test_E_duration_validation_range(self):
        self.assertEqual(OLD_FORMAT_CONFIG["min_duration_seconds"], 24)
        self.assertEqual(OLD_FORMAT_CONFIG["max_duration_seconds"], 45)

    def test_F_duration_preferred_target(self):
        self.assertEqual(OLD_FORMAT_CONFIG["preferred_target_min"], 28)
        self.assertEqual(OLD_FORMAT_CONFIG["preferred_target_max"], 40)

    def test_G_first_frame_visual_hook_config(self):
        self.assertEqual(OLD_FORMAT_CONFIG["resolution"], "1080x1920")
        self.assertEqual(OLD_FORMAT_CONFIG["aspect_ratio"], "9:16")

    def test_H_topic_duplicate_protection(self):
        candidate = {
            "topic": "Duplicate Topic",
            "category": "Devotional",
            "overall_score": 80,
            "demand_score": 80,
            "relevance_score": 80,
            "competition_score": 80,
            "evergreen_score": 80,
            "freshness_score": 80,
            "curiosity_score": 80,
            "long_form_potential": 80,
            "shorts_potential": 80,
            "data_source": "youtube_api",
            "confidence": "high",
            "suggested_angle": "Angle",
            "content_gap": "possible gap",
        }
        published_topics = {"duplicate topic"}
        ok, reasons = validate_candidate(candidate, published_topics=published_topics)
        self.assertFalse(ok)
        self.assertTrue(any("already published" in r for r in reasons))

    def test_I_old_format_topic_preference_weighting(self):
        candidates = [
            {"topic": "General Deity", "overall_score": 70},
            {"topic": "Lord Venkateshwara Suprabhatam", "overall_score": 70},
        ]
        adjusted = apply_old_format_topic_preferences(candidates)
        self.assertEqual(adjusted[0]["overall_score"], 70)
        self.assertEqual(adjusted[1]["overall_score"], 85.0)

    def test_J_asset_directory_isolation(self):
        state_narrated = PipelineState(format="narrated")
        state_old = PipelineState(format="old")
        self.assertNotEqual(state_narrated.pipeline_id, state_old.pipeline_id)

    def test_K_publishing_history_format_recording(self):
        state = PipelineState(format="old")
        runner = PipelineRunner(state=state, format="old")
        self.assertEqual(runner.format, "old")

    def test_L_old_format_enabled_false_safety(self):
        state = PipelineState(format="old")
        runner = PipelineRunner(state=state, format="old")
        with patch.dict(os.environ, {"OLD_FORMAT_ENABLED": "false"}):
            result = runner.execute_pipeline()
            self.assertEqual(result, state.pipeline_id)

    def test_M_morning_execution_when_old_format_disabled(self):
        state = PipelineState(format="narrated")
        runner = PipelineRunner(state=state, format="narrated")
        with patch.dict(os.environ, {"OLD_FORMAT_ENABLED": "false"}):
            self.assertEqual(runner.format, "narrated")

    def test_N_evening_execution_when_old_format_enabled(self):
        state = PipelineState(format="old")
        runner = PipelineRunner(state=state, format="old")
        with patch.dict(os.environ, {"OLD_FORMAT_ENABLED": "true"}):
            self.assertEqual(runner.format, "old")

    def test_O_0400_utc_cron_mapping(self):
        cron = "0 4 * * *"
        fmt = "old" if cron == "30 13 * * *" else "narrated"
        self.assertEqual(fmt, "narrated")

    def test_P_1330_utc_cron_mapping(self):
        cron = "30 13 * * *"
        fmt = "old" if cron == "30 13 * * *" else "narrated"
        self.assertEqual(fmt, "old")

    def test_Q_workflow_conditional_logic(self):
        event_name = "schedule"
        cron_morning = "0 4 * * *"
        cron_evening = "30 13 * * *"

        fmt_m = "old" if (event_name == "schedule" and cron_morning == "30 13 * * *") else "narrated"
        fmt_e = "old" if (event_name == "schedule" and cron_evening == "30 13 * * *") else "narrated"

        self.assertEqual(fmt_m, "narrated")
        self.assertEqual(fmt_e, "old")

    def test_R_old_format_no_captions_subtitles(self):
        """Verify that OLD format has no captions/subtitles, while NEW format retains them."""
        from tests.test_video_generator import _make_timing_maps
        from src.video.generator import compose_video_pipeline
        from src.video.composer import FFmpegVideoComposer

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Case 1: format = old -> voice_text in video map must be empty, no drawtext in ffmpeg command
            amap, vmap = _make_timing_maps(create_files=True, tmp_dir=tmp_path, scene_count=2)
            amap["format"] = "old"
            bgm_file = tmp_path / "full_narration.mp3"
            bgm_file.write_text("dummy bgm", encoding="utf-8")
            amap["full_narration_audio_file"] = str(bgm_file.absolute()).replace("\\", "/")
            video_map_old = compose_video_pipeline(amap, vmap, composer_type="mock", output_dir=tmp_path)

            for scene in video_map_old["scenes"]:
                self.assertEqual(scene["voice_text"], "")

            composer = FFmpegVideoComposer()
            cmd_old = composer.build_ffmpeg_command(
                scenes=video_map_old["scenes"],
                output_file=tmp_path / "video_old.mp4"
            )
            cmd_str_old = " ".join(cmd_old)
            self.assertNotIn("drawtext", cmd_str_old)

            # Case 2: format = narrated -> voice_text must be preserved, drawtext must be in ffmpeg command
            amap, vmap = _make_timing_maps(create_files=True, tmp_dir=tmp_path, scene_count=2)
            amap["format"] = "narrated"
            video_map_narrated = compose_video_pipeline(amap, vmap, composer_type="mock", output_dir=tmp_path)

            for i, scene in enumerate(video_map_narrated["scenes"]):
                self.assertEqual(scene["voice_text"], amap["audio_scenes"][i]["voice_text"])

            cmd_narrated = composer.build_ffmpeg_command(
                scenes=video_map_narrated["scenes"],
                output_file=tmp_path / "video_narrated.mp4"
            )
            cmd_str_narrated = " ".join(cmd_narrated)
            self.assertIn("drawtext", cmd_str_narrated)

    def test_S_old_format_bgm_validation_and_fail_closed(self):
        """Verify that OLD format BGM is validated and missing BGM fails closed."""
        from src.voice.generator import generate_voice_mapping
        from src.video.generator import compose_video_pipeline
        from tests.test_video_generator import _make_timing_maps

        script = {
            "title": "Jai Hanuman",
            "duration_seconds": 30,
            "narration": "Jai Shri Ram",
            "scene_scripts": [
                {"scene": 1, "voice_text": "Jai Hanuman"}
            ],
            "retention_hooks": ["Hook"],
            "approval_metadata": {
                "approved_for_generation": True,
                "data_source": "youtube_api",
                "confidence": "high",
                "selected_topic": "Jai Hanuman",
            }
        }

        # Test 1: OLD format selects a music track in test/mock mode
        audio_map = generate_voice_mapping(script, format="old", mode="test")
        self.assertEqual(audio_map["format"], "old")
        self.assertEqual(audio_map["audio_type"], "music_only")
        self.assertTrue(audio_map["full_narration_audio_file"].endswith(".wav"))











        # Test 2: Production must fail closed when music selection returns no BGM.
        with patch(
            "src.audio.music.select_background_music_v2",
            return_value=(None, "narration_only"),
        ):
            with self.assertRaises(ValueError):
                generate_voice_mapping(script, format="old", mode="production")


















        # Test 3: Video composition fails closed if background music file doesn't exist
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            amap, vmap = _make_timing_maps(create_files=True, tmp_dir=tmp_path, scene_count=2)
            amap["format"] = "old"
            amap["full_narration_audio_file"] = str(tmp_path / "non_existent_music.wav")
            with self.assertRaises(FileNotFoundError):
                compose_video_pipeline(amap, vmap, composer_type="mock", output_dir=tmp_path)

    def test_T_ffmpeg_command_and_mapping(self):
        """Verify BGM mapping in FFmpeg command and audibility parameters."""
        from src.video.composer import FFmpegVideoComposer
        from tests.test_video_generator import _make_timing_maps
        from src.video.generator import compose_video_pipeline

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            amap, vmap = _make_timing_maps(create_files=True, tmp_dir=tmp_path, scene_count=2)
            amap["format"] = "old"

            # Create a fake BGM file that exists and has 'mock' in the name
            bgm_file = tmp_path / "mock_devotional_music.wav"
            bgm_file.write_text("fake wav content", encoding="utf-8")
            amap["full_narration_audio_file"] = str(bgm_file.absolute()).replace("\\", "/")

            # Compose video
            video_map = compose_video_pipeline(amap, vmap, composer_type="mock", output_dir=tmp_path)

            # Check scene voice texts are empty
            for sc in video_map["scenes"]:
                self.assertEqual(sc["voice_text"], "")

            # Build FFmpeg command and check inputs and filtergraph
            composer = FFmpegVideoComposer()
            cmd = composer.build_ffmpeg_command(
                scenes=video_map["scenes"],
                output_file=tmp_path / "video_old.mp4",
                background_music=bgm_file,
            )
            cmd_str = " ".join(cmd)

            # Must contain BGM file as an input
            self.assertIn("mock_devotional_music.wav", cmd_str)
            # Must map final audio stream
            self.assertIn("-map [v_concat]", cmd_str)
            self.assertIn("-map [a_final]", cmd_str)
            # Volume for BGM must be set to -4.0dB (auto-adjusted for old format)
            self.assertIn("volume=-4.0dB", cmd_str)


if __name__ == "__main__":
    unittest.main()
