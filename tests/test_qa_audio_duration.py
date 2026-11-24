import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.qa.checks import (
    AUDIO_DURATION_SHORTFALL_TOLERANCE_SECONDS,
    check_audio_stream_duration,
    check_video_with_ffprobe,
)


def _probe_result(duration: float) -> MagicMock:
    return MagicMock(
        returncode=0,
        stdout=json.dumps({
            "streams": [{"codec_type": "audio", "duration": str(duration)}],
            "format": {"duration": str(duration)},
        }),
        stderr="",
    )


class TestAudioStreamDurationQA(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmpdir.name)
        self.scene_audio = self.root / "scene.mp3"
        self.scene_audio.write_bytes(b"scene audio")

    def tearDown(self):
        self.tmpdir.cleanup()

    def _check(self, actual_duration: float, scene_duration: float = 10.0):
        audio_map = {
            "audio_scenes": [{"scene": 1, "audio_file": str(self.scene_audio)}],
            "full_narration_audio_file": str(self.root / "full_narration.mp3"),
        }
        video_validation = {"audio_duration_seconds": actual_duration}
        with patch(
            "src.qa.checks.subprocess.run",
            return_value=_probe_result(scene_duration),
        ) as probe:
            result = check_audio_stream_duration(video_validation, audio_map)
        return result, probe

    def test_correctly_muxed_audio_passes(self):
        (passed, detail), _ = self._check(actual_duration=10.0)
        self.assertTrue(passed, detail)
        self.assertIn("expected 10.000s", detail)
        self.assertIn("actual 10.000s", detail)
        self.assertIn("difference +0.000s", detail)

    def test_materially_short_audio_fails_with_duration_diagnostic(self):
        (passed, detail), _ = self._check(actual_duration=8.9)
        self.assertFalse(passed)
        self.assertIn("expected 10.000s", detail)
        self.assertIn("actual 8.900s", detail)
        self.assertIn("difference -1.100s", detail)

    def test_slight_shortfall_within_tolerance_passes(self):
        (passed, detail), _ = self._check(
            actual_duration=10.0 - AUDIO_DURATION_SHORTFALL_TOLERANCE_SECONDS + 0.01
        )
        self.assertTrue(passed, detail)

    def test_longer_audio_passes_for_concat_padding(self):
        (passed, detail), _ = self._check(actual_duration=11.0)
        self.assertTrue(passed, detail)
        self.assertIn("difference +1.000s", detail)
        self.assertIn("longer audio allowed for concat padding", detail)

    def test_missing_rendered_audio_stream_duration_fails(self):
        passed, detail = check_audio_stream_duration(
            {},
            {"audio_scenes": [{"scene": 1, "audio_file": str(self.scene_audio)}]},
        )
        self.assertFalse(passed)
        self.assertIn("no valid audio-stream duration", detail)

    def test_missing_scene_audio_file_fails_safely(self):
        missing_file = self.root / "missing.mp3"
        passed, detail = check_audio_stream_duration(
            {"audio_duration_seconds": 10.0},
            {"audio_scenes": [{"scene": 1, "audio_file": str(missing_file)}]},
        )
        self.assertFalse(passed)
        self.assertIn("audio file is missing", detail)

    def test_path_exists_oserror_fails_safely(self):
        with patch.object(Path, "exists", side_effect=OSError("Disk I/O error")):
            passed, detail = check_audio_stream_duration(
                {"audio_duration_seconds": 10.0},
                {"audio_scenes": [{"scene": 1, "audio_file": str(self.scene_audio)}]},
            )
        self.assertFalse(passed)
        self.assertIn("audio file access error", detail)
        self.assertIn("Disk I/O error", detail)

    def test_path_is_file_oserror_fails_safely(self):
        with patch.object(Path, "is_file", side_effect=OSError("Permission denied")):
            passed, detail = check_audio_stream_duration(
                {"audio_duration_seconds": 10.0},
                {"audio_scenes": [{"scene": 1, "audio_file": str(self.scene_audio)}]},
            )
        self.assertFalse(passed)
        self.assertIn("audio file access error", detail)
        self.assertIn("Permission denied", detail)

    def test_path_stat_oserror_fails_safely(self):
        with patch.object(Path, "stat", side_effect=PermissionError("Stat access denied")):
            passed, detail = check_audio_stream_duration(
                {"audio_duration_seconds": 10.0},
                {"audio_scenes": [{"scene": 1, "audio_file": str(self.scene_audio)}]},
            )
        self.assertFalse(passed)
        self.assertIn("audio file access error", detail)
        self.assertIn("Stat access denied", detail)

    def test_invalid_path_null_byte_fails_safely(self):
        passed, detail = check_audio_stream_duration(
            {"audio_duration_seconds": 10.0},
            {"audio_scenes": [{"scene": 1, "audio_file": "scene\x00_invalid.mp3"}]},
        )
        self.assertFalse(passed)
        self.assertIn("Scene 1 has invalid audio path", detail)
        self.assertIn("null byte", detail)

    def test_non_string_audio_file_fails_safely(self):
        for bad_val in (12345, ["scene.mp3"], {"path": "scene.mp3"}, True):
            with self.subTest(bad_val=bad_val):
                passed, detail = check_audio_stream_duration(
                    {"audio_duration_seconds": 10.0},
                    {"audio_scenes": [{"scene": 1, "audio_file": bad_val}]},
                )
                self.assertFalse(passed)
                self.assertIn("Scene 1 has invalid audio path", detail)

    def test_file_disappearing_between_exists_and_stat_fails_safely(self):
        with patch.object(Path, "exists", return_value=True), \
             patch.object(Path, "is_file", return_value=True), \
             patch.object(Path, "stat", side_effect=FileNotFoundError("Disappeared")):
            passed, detail = check_audio_stream_duration(
                {"audio_duration_seconds": 10.0},
                {"audio_scenes": [{"scene": 1, "audio_file": str(self.scene_audio)}]},
            )
        self.assertFalse(passed)
        self.assertIn("audio file access error", detail)
        self.assertIn("Disappeared", detail)

    def test_ffprobe_failure_fails_safely(self):
        with patch(
            "src.qa.checks.subprocess.run",
            return_value=MagicMock(returncode=1, stdout="", stderr="invalid media"),
        ):
            passed, detail = check_audio_stream_duration(
                {"audio_duration_seconds": 10.0},
                {"audio_scenes": [{"scene": 1, "audio_file": str(self.scene_audio)}]},
            )
        self.assertFalse(passed)
        self.assertIn("ffprobe failed", detail)

    def test_malformed_ffprobe_output_fails_safely(self):
        with patch(
            "src.qa.checks.subprocess.run",
            return_value=MagicMock(returncode=0, stdout="{bad json", stderr=""),
        ):
            passed, detail = check_audio_stream_duration(
                {"audio_duration_seconds": 10.0},
                {"audio_scenes": [{"scene": 1, "audio_file": str(self.scene_audio)}]},
            )
        self.assertFalse(passed)
        self.assertIn("unparseable JSON", detail)

    def test_expected_duration_uses_scene_audio_not_full_narration(self):
        full_narration = self.root / "full_narration.mp3"
        full_narration.write_bytes(b"separate narration")
        audio_map = {
            "audio_scenes": [{"scene": 1, "audio_file": str(self.scene_audio)}],
            "full_narration_audio_file": str(full_narration),
        }
        with patch(
            "src.qa.checks.subprocess.run",
            return_value=_probe_result(7.0),
        ) as probe:
            passed, detail = check_audio_stream_duration(
                {"audio_duration_seconds": 7.0},
                audio_map,
            )
        self.assertTrue(passed, detail)
        self.assertIn("expected 7.000s", detail)
        probed_path = probe.call_args.args[0][-1]
        self.assertEqual(probed_path, str(self.scene_audio))
        self.assertNotEqual(probed_path, str(full_narration))

    def test_video_ffprobe_requires_and_records_audio_stream_duration(self):
        video_file = self.root / "video.mp4"
        video_file.write_bytes(b"non-mock video")
        video_probe = {
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "pix_fmt": "yuv420p",
                    "width": 1080,
                    "height": 1920,
                    "duration": "35.0",
                },
                {
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "channels": 2,
                    "duration": "35.0",
                },
            ],
            "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2", "duration": "35.0"},
        }
        with patch(
            "src.qa.checks.subprocess.run",
            side_effect=[
                MagicMock(returncode=0, stdout=json.dumps(video_probe), stderr=""),
                MagicMock(returncode=0, stdout="", stderr=""),
            ],
        ):
            passed, detail, validation = check_video_with_ffprobe(video_file)
        self.assertTrue(passed, detail)
        self.assertEqual(validation["audio_duration_seconds"], 35.0)

    def test_video_ffprobe_missing_audio_stream_fails(self):
        video_file = self.root / "video_no_audio.mp4"
        video_file.write_bytes(b"non-mock video without audio")
        video_probe = {
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "pix_fmt": "yuv420p",
                    "width": 1080,
                    "height": 1920,
                    "duration": "35.0",
                },
            ],
            "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2", "duration": "35.0"},
        }
        with patch(
            "src.qa.checks.subprocess.run",
            return_value=MagicMock(returncode=0, stdout=json.dumps(video_probe), stderr=""),
        ):
            passed, detail, validation = check_video_with_ffprobe(video_file)
        self.assertFalse(passed)
        self.assertIn("No audio stream found", detail)
        self.assertEqual(validation["audio_duration_seconds"], 0.0)

    def test_video_ffprobe_invalid_audio_duration_fails(self):
        video_file = self.root / "video_bad_audio_dur.mp4"
        video_file.write_bytes(b"non-mock video with zero duration audio")
        video_probe = {
            "streams": [
                {
                    "codec_type": "video",
                    "codec_name": "h264",
                    "pix_fmt": "yuv420p",
                    "width": 1080,
                    "height": 1920,
                    "duration": "35.0",
                },
                {
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "channels": 2,
                    "duration": "0.0",
                },
            ],
            "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2", "duration": "35.0"},
        }
        with patch(
            "src.qa.checks.subprocess.run",
            return_value=MagicMock(returncode=0, stdout=json.dumps(video_probe), stderr=""),
        ):
            passed, detail, validation = check_video_with_ffprobe(video_file)
        self.assertFalse(passed)
        self.assertIn("Audio stream duration is missing or invalid", detail)

    def test_non_mock_qa_gate_executes_audio_duration_check_and_fails_on_truncation(self):
        from src.qa.gate import FinalQAGate
        from tests.test_final_qa import _build_artifacts

        arts = _build_artifacts(self.root)
        vval = {
            "container": "mp4",
            "video_codec": "h264",
            "pixel_format": "yuv420p",
            "width": 720,
            "height": 1280,
            "audio_codec": "aac",
            "audio_channels": 2,
            "audio_duration_seconds": 10.0,
            "duration_seconds": 30.0,
            "ffprobe_passed": True,
            "ffmpeg_decode_passed": True,
        }
        with patch("src.qa.gate.check_video_with_ffprobe", return_value=(True, "OK", vval)), \
             patch("src.qa.gate.check_audio_stream_duration", return_value=(False, "shortfall detected: expected 40.000s, actual 10.000s")):
            gate = FinalQAGate(allow_mock=False)
            result = gate.run(artifacts=arts)
            self.assertIn("audio_duration", result.checks)
            self.assertFalse(result.checks["audio_duration"])
            self.assertFalse(result.approved_for_publishing)
            self.assertIn("audio_duration: shortfall detected: expected 40.000s, actual 10.000s", result.errors)

    def test_non_mock_qa_gate_executes_audio_duration_check_and_passes_when_valid(self):
        from src.qa.gate import FinalQAGate
        from tests.test_final_qa import _build_artifacts

        arts = _build_artifacts(self.root)
        vval = {
            "container": "mp4",
            "video_codec": "h264",
            "pixel_format": "yuv420p",
            "width": 720,
            "height": 1280,
            "audio_codec": "aac",
            "audio_channels": 2,
            "audio_duration_seconds": 40.0,
            "duration_seconds": 40.0,
            "ffprobe_passed": True,
            "ffmpeg_decode_passed": True,
        }
        with patch("src.qa.gate.check_video_with_ffprobe", return_value=(True, "OK", vval)), \
             patch("src.qa.gate.check_audio_stream_duration", return_value=(True, "expected 40.000s; actual 40.000s")):
            gate = FinalQAGate(allow_mock=False)
            result = gate.run(artifacts=arts)
            self.assertIn("audio_duration", result.checks)
            self.assertTrue(result.checks["audio_duration"])
            self.assertEqual(result.details.get("audio_duration"), "expected 40.000s; actual 40.000s")

    def test_final_qa_gate_does_not_crash_on_audio_filesystem_error(self):
        import inspect
        from src.qa.gate import FinalQAGate
        from tests.test_final_qa import _build_artifacts

        arts = _build_artifacts(self.root)
        vval = {
            "container": "mp4",
            "video_codec": "h264",
            "pixel_format": "yuv420p",
            "width": 720,
            "height": 1280,
            "audio_codec": "aac",
            "audio_channels": 2,
            "audio_duration_seconds": 40.0,
            "duration_seconds": 40.0,
            "ffprobe_passed": True,
            "ffmpeg_decode_passed": True,
        }
        original_stat = Path.stat

        def _conditional_stat(path_self, *args, **kwargs):
            caller_names = {frame.function for frame in inspect.stack()}
            if "_probe_scene_audio_duration" in caller_names:
                raise OSError("Audio hardware read error")
            return original_stat(path_self, *args, **kwargs)

        with patch("src.qa.gate.check_video_with_ffprobe", return_value=(True, "OK", vval)), \
             patch.object(Path, "stat", side_effect=_conditional_stat, autospec=True):
            gate = FinalQAGate(allow_mock=False)
            result = gate.run(artifacts=arts)
            self.assertIn("audio_duration", result.checks)
            self.assertFalse(result.checks["audio_duration"])
            self.assertFalse(result.approved_for_publishing)
            self.assertTrue(any("audio_duration" in err for err in result.errors))


if __name__ == "__main__":
    unittest.main()
