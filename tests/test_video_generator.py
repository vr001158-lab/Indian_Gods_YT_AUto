"""
tests/test_video_generator.py
Unit tests for Phase 2G — Video Composer Engine.
Tests safety gates, input map alignment, missing file check rejections, composer type matching, FFmpeg command generation, output validation, and CLI behaviors.
Runs completely offline without external network or binary process dependencies.
"""

import sys
import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.getcwd())

from src.video.schemas import validate_input_maps, validate_output_video_map
from src.video.generator import compose_video_pipeline, process_mapping_files
from src.video.composer import FFmpegVideoComposer
import run_video_generator


# ── Helper: generate mock timing maps ─────────────────────────────────────────
def _make_timing_maps(
    deity: str = "shiva",
    approved: bool = True,
    confidence: str = "high",
    data_source: str = "youtube_api",
    title: str = "Secrets of Shiva's Snake",
    scene_count: int = 2,
    create_files: bool = False,
    tmp_dir: Path = None,
) -> tuple:
    """Helper to build audio and visual maps matching safety requirements."""
    meta = {
        "approved_for_generation": approved,
        "data_source":             data_source,
        "confidence":              confidence,
        "selected_topic":          "Why Lord Shiva Wears a Snake Around His Neck"
    }

    audio_scenes = []
    visual_scenes = []

    for i in range(1, scene_count + 1):
        # Setup paths
        img_p = f"scene_{i}.png"
        aud_p = f"scene_{i}.mp3"

        if create_files and tmp_dir:
            img_file = tmp_dir / img_p
            aud_file = tmp_dir / aud_p
            img_file.write_text("dummy image content", encoding="utf-8")
            aud_file.write_text("dummy audio content", encoding="utf-8")
            img_p = str(img_file.absolute()).replace("\\", "/")
            aud_p = str(aud_file.absolute()).replace("\\", "/")

        audio_scenes.append({
            "scene":            i,
            "voice_text":       f"Voice text for scene {i}",
            "audio_file":       aud_p,
            "duration_seconds": 10 * i
        })

        visual_scenes.append({
            "scene":            i,
            "visual_prompt":    f"Visual prompt for scene {i}",
            "image_file":       img_p,
            "style":            "Devotional Cinematic Painting",
            "duration_seconds": 10 * i
        })

    audio_map = {
        "script_title":              title,
        "total_duration_seconds":    sum(x["duration_seconds"] for x in audio_scenes),
        "provider":                  "elevenlabs",
        "audio_scenes":              audio_scenes,
        "full_narration_audio_file": "full_narration.mp3",
        "approval_metadata":         meta
    }

    visual_map = {
        "script_title":       title,
        "total_scenes":       len(visual_scenes),
        "style_preset":       "Devotional Cinematic Painting",
        "provider":           "mock",
        "visual_scenes":      visual_scenes,
        "approval_metadata":  meta
    }

    return audio_map, visual_map


# ─────────────────────────────────────────────────────────────────────────────
class TestVideoSafetyGates(unittest.TestCase):
    """Test safety gate rejections on incoming timing maps."""

    def test_1_valid_timing_maps_accepted(self):
        amap, vmap = _make_timing_maps()
        ok, err = validate_input_maps(amap, vmap)
        self.assertTrue(ok, f"Should accept valid timing maps: {err}")

    def test_2_missing_approval_metadata_rejected(self):
        amap, vmap = _make_timing_maps()
        del amap["approval_metadata"]
        ok, err = validate_input_maps(amap, vmap)
        self.assertFalse(ok)
        self.assertIn("approval_metadata is missing", err)

    def test_3_unapproved_topic_timing_map_rejected(self):
        amap, vmap = _make_timing_maps(approved=False)
        ok, err = validate_input_maps(amap, vmap)
        self.assertFalse(ok)
        self.assertIn("not approved for generation", err)

    def test_4_mock_evidence_source_rejected(self):
        amap, vmap = _make_timing_maps(data_source="mock")
        ok, err = validate_input_maps(amap, vmap)
        self.assertFalse(ok)
        self.assertIn("data_source", err)

    def test_5_offline_evidence_source_rejected(self):
        amap, vmap = _make_timing_maps(data_source="offline")
        ok, err = validate_input_maps(amap, vmap)
        self.assertFalse(ok)
        self.assertIn("data_source", err)

    def test_6_low_confidence_topic_rejected(self):
        amap, vmap = _make_timing_maps(confidence="low")
        ok, err = validate_input_maps(amap, vmap)
        self.assertFalse(ok)
        self.assertIn("confidence", err)

    def test_7_mismatched_titles_rejected(self):
        amap, vmap = _make_timing_maps(title="Title A")
        vmap["script_title"] = "Title B"
        ok, err = validate_input_maps(amap, vmap)
        self.assertFalse(ok)
        self.assertIn("Mismatched script titles", err)

    def test_8_mismatched_scene_counts_rejected(self):
        amap, vmap = _make_timing_maps(scene_count=2)
        # Drop a scene from visual map
        vmap["visual_scenes"].pop()
        ok, err = validate_input_maps(amap, vmap)
        self.assertFalse(ok)
        self.assertIn("Mismatched scene counts", err)

    def test_8b_malformed_input_rejected(self):
        ok, err = validate_input_maps("not-a-dict", {})
        self.assertFalse(ok)
        self.assertIn("must be dictionaries", err)

    def test_8c_missing_metadata_fields_rejected(self):
        amap, vmap = _make_timing_maps()
        del amap["approval_metadata"]["data_source"]
        ok, err = validate_input_maps(amap, vmap)
        self.assertFalse(ok)
        self.assertIn("Missing approval metadata key", err)

    def test_8d_missing_topic_rejected(self):
        amap, vmap = _make_timing_maps()
        amap["approval_metadata"]["selected_topic"] = ""
        ok, err = validate_input_maps(amap, vmap)
        self.assertFalse(ok)
        self.assertIn("selected_topic is missing", err)

    def test_8e_metadata_preservation(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            amap, vmap = _make_timing_maps(create_files=True, tmp_dir=tmp_path, scene_count=2)
            out_map = compose_video_pipeline(amap, vmap, composer_type="mock", output_dir=tmp_path)
            self.assertIn("approval_metadata", out_map)
            self.assertEqual(out_map["approval_metadata"]["selected_topic"], amap["approval_metadata"]["selected_topic"])

    def test_8f_zero_byte_asset_rejected(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            amap, vmap = _make_timing_maps(create_files=True, tmp_dir=tmp_path, scene_count=2)
            
            # Make an image asset zero-byte
            img = Path(vmap["visual_scenes"][0]["image_file"])
            img.write_bytes(b"") # zero-byte file
            
            with self.assertRaises(ValueError):
                compose_video_pipeline(amap, vmap, composer_type="mock", output_dir=tmp_path)

    def test_8g_corrupted_empty_mp4_detection(self):
        # QA check should detect empty or non-existent MP4 files
        from src.video.generator import validate_video_file_with_ffprobe
        with tempfile.TemporaryDirectory() as tmp_dir:
            bad_file = Path(tmp_dir) / "corrupted.mp4"
            bad_file.write_bytes(b"corrupted header data")
            
            # A mock file checks pass, but non-mock files go through ffprobe checks.
            # We can assert that non-mock corrupted files raise RuntimeError.
            ok, err = validate_video_file_with_ffprobe(bad_file)
            self.assertFalse(ok)
            self.assertIn("ffprobe failed", err)

    def test_8h_resolution_codec_aspect_ratio_checks(self):
        vmap_out = {
            "video_file":       "video_123.mp4",
            "video_map_file":   "video_map_123.json",
            "total_duration":   30,
            "resolution":       "720x1280",
            "content_type":     "short",
            "aspect_ratio":     "9:16",
            "scenes": [
                {
                    "scene":            1,
                    "image_file":       "scene_1.png",
                    "audio_file":       "scene_1.mp3",
                    "duration_seconds": 30
                }
            ]
        }
        ok, err = validate_output_video_map(vmap_out)
        self.assertTrue(ok, f"Output map fails validation: {err}")
        self.assertEqual(vmap_out["resolution"], "720x1280")
        
        # Test incorrect resolution gets blocked
        vmap_out["resolution"] = "1920x1080"
        ok2, err2 = validate_output_video_map(vmap_out)
        self.assertFalse(ok2)
        self.assertIn("resolution", err2.lower())


# ─────────────────────────────────────────────────────────────────────────────
class TestVideoCompositionLogic(unittest.TestCase):

    """Test composition mapping, FFmpeg command formulation, and asset validation."""

    def test_9_missing_image_file_on_disk_rejected(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            amap, vmap = _make_timing_maps(create_files=True, tmp_dir=tmp_path)
            
            # Delete one image file on disk to simulate missing asset
            missing_img = Path(vmap["visual_scenes"][0]["image_file"])
            missing_img.unlink()

            with self.assertRaises(FileNotFoundError):
                compose_video_pipeline(amap, vmap, composer_type="mock", output_dir=tmp_path)

    def test_10_missing_audio_file_on_disk_rejected(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            amap, vmap = _make_timing_maps(create_files=True, tmp_dir=tmp_path)
            
            # Delete one audio file on disk to simulate missing asset
            missing_aud = Path(amap["audio_scenes"][0]["audio_file"])
            missing_aud.unlink()

            with self.assertRaises(FileNotFoundError):
                compose_video_pipeline(amap, vmap, composer_type="mock", output_dir=tmp_path)

    def test_11_output_validation_schema(self):
        vmap_out = {
            "video_file":       "video_123.mp4",
            "video_map_file":   "video_map_123.json",
            "total_duration":   30,
            "resolution":       "720x1280",
            "content_type":     "short",
            "aspect_ratio":     "9:16",
            "scenes": [
                {
                    "scene":            1,
                    "image_file":       "scene_1.png",
                    "audio_file":       "scene_1.mp3",
                    "duration_seconds": 30
                }
            ]
        }
        ok, err = validate_output_video_map(vmap_out)
        self.assertTrue(ok, f"Output map fails schema check: {err}")

    def test_12_composed_scene_duration_sums(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            amap, vmap = _make_timing_maps(create_files=True, tmp_dir=tmp_path, scene_count=3)
            
            out_map = compose_video_pipeline(amap, vmap, composer_type="mock", output_dir=tmp_path)
            
            self.assertEqual(out_map["total_duration"], 10 + 20 + 30)
            self.assertEqual(len(out_map["scenes"]), 3)

    def test_13_ffmpeg_command_generation_correct(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            amap, vmap = _make_timing_maps(create_files=True, tmp_dir=tmp_path, scene_count=2)
            
            composer = FFmpegVideoComposer()
            scenes_list = [
                {
                    "scene":            1,
                    "image_file":       vmap["visual_scenes"][0]["image_file"],
                    "audio_file":       amap["audio_scenes"][0]["audio_file"],
                    "duration_seconds": 10
                },
                {
                    "scene":            2,
                    "image_file":       vmap["visual_scenes"][1]["image_file"],
                    "audio_file":       amap["audio_scenes"][1]["audio_file"],
                    "duration_seconds": 20
                }
            ]
            
            output_file = tmp_path / "video.mp4"
            cmd = composer.build_ffmpeg_command(scenes_list, output_file)
            
            # Command should alternate inputs
            self.assertEqual(cmd[0], "ffmpeg")
            self.assertIn("-loop", cmd)
            self.assertIn("-t", cmd)
            self.assertIn("10", cmd)
            self.assertIn("20", cmd)
            
            # Video codec and yuv420p should be present
            self.assertIn("libx264", cmd)
            self.assertIn("yuv420p", cmd)
            self.assertIn("-shortest", cmd)

    def test_14_ffmpeg_command_includes_bgm(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            amap, vmap = _make_timing_maps(create_files=True, tmp_dir=tmp_path, scene_count=1)
            
            bgm_file = tmp_path / "music.mp3"
            bgm_file.write_text("dummy BGM content", encoding="utf-8")
            
            composer = FFmpegVideoComposer()
            scenes_list = [
                {
                    "scene":            1,
                    "image_file":       vmap["visual_scenes"][0]["image_file"],
                    "audio_file":       amap["audio_scenes"][0]["audio_file"],
                    "duration_seconds": 10
                }
            ]
            
            output_file = tmp_path / "video.mp4"
            cmd = composer.build_ffmpeg_command(scenes_list, output_file, background_music=bgm_file, bgm_volume=0.25)
            
            # Check BGM mix tag in filter_complex
            self.assertIn("volume=", "".join(cmd))
            self.assertIn("amix=", "".join(cmd))


# ─────────────────────────────────────────────────────────────────────────────
class TestVideoCLI(unittest.TestCase):
    """Test run_video_generator.py CLI interface and parameters."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.audio_dir = Path(self.tmp_dir.name) / "audio"
        self.visual_dir = Path(self.tmp_dir.name) / "visuals"
        self.video_dir = Path(self.tmp_dir.name) / "videos"
        
        self.audio_dir.mkdir()
        self.visual_dir.mkdir()
        self.video_dir.mkdir()

        # Patch CLI folder paths
        self.patch_audio_dir = patch("run_video_generator.AUDIO_DIR", self.audio_dir)
        self.patch_visual_dir = patch("run_video_generator.VISUAL_DIR", self.visual_dir)
        self.patch_video_dir = patch("run_video_generator.VIDEO_DIR", self.video_dir)
        
        self.patch_audio_dir.start()
        self.patch_visual_dir.start()
        self.patch_video_dir.start()

    def tearDown(self):
        self.patch_audio_dir.stop()
        self.patch_visual_dir.stop()
        self.patch_video_dir.stop()
        self.tmp_dir.cleanup()

    def test_15_cli_auto_discovery(self):
        amap, vmap = _make_timing_maps(create_files=True, tmp_dir=Path(self.tmp_dir.name))
        
        # Write maps into auto-discovery locations
        audio_file = self.audio_dir / "audio_map_20260813_120000.json"
        visual_file = self.visual_dir / "visual_map_20260813_120000.json"
        
        audio_file.write_text(json.dumps(amap), encoding="utf-8")
        visual_file.write_text(json.dumps(vmap), encoding="utf-8")

        with patch("sys.argv", ["run_video_generator.py", "--composer", "mock"]):
            run_video_generator.main()

        saved = list(self.video_dir.glob("video_map_*.json"))
        self.assertEqual(len(saved), 1)
        map_data = json.loads(saved[0].read_text(encoding="utf-8"))
        self.assertEqual(map_data["total_duration"], 30)

    def test_16_cli_no_save_works(self):
        amap, vmap = _make_timing_maps(create_files=True, tmp_dir=Path(self.tmp_dir.name))
        
        audio_file = self.audio_dir / "audio_map_20260813_120000.json"
        visual_file = self.visual_dir / "visual_map_20260813_120000.json"
        
        audio_file.write_text(json.dumps(amap), encoding="utf-8")
        visual_file.write_text(json.dumps(vmap), encoding="utf-8")

        with patch("sys.argv", ["run_video_generator.py", "--composer", "mock", "--no-save"]):
            run_video_generator.main()

        # Should not write final video map to directory
        saved = list(self.video_dir.glob("video_map_*.json"))
        self.assertEqual(len(saved), 0)


if __name__ == "__main__":
    unittest.main()

# ─────────────────────────────────────────────────────────────────────────────
class TestProductionVideoValidation(unittest.TestCase):
    """Regression tests for Phase 2G production safety fix."""

    def test_R01_mock_mp4_rejected_by_production_validation(self):
        """Files starting with MOCK_MP4_VIDEO must fail production validation."""
        from src.video.generator import validate_video_file_with_ffprobe
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "mock.mp4"
            f.write_text("MOCK_MP4_VIDEO: resolution=720x1280\n", encoding="utf-8")
            ok, err = validate_video_file_with_ffprobe(f)
            self.assertFalse(ok)
            self.assertIn("Mock video artifact", err)

    def test_R02_zero_byte_mp4_rejected(self):
        from src.video.generator import validate_video_file_with_ffprobe
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "empty.mp4"
            f.write_bytes(b"")
            ok, err = validate_video_file_with_ffprobe(f)
            self.assertFalse(ok)
            self.assertIn("zero-byte", err)

    def test_R03_corrupt_mp4_rejected(self):
        from src.video.generator import validate_video_file_with_ffprobe
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "corrupt.mp4"
            f.write_bytes(b"\x00\x00\x00\x20ftyp" + b"\xDE\xAD" * 100)
            with patch("src.video.generator.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="moov atom not found")
                ok, err = validate_video_file_with_ffprobe(f)
            self.assertFalse(ok)

    def test_R04_text_file_with_mp4_extension_rejected(self):
        from src.video.generator import validate_video_file_with_ffprobe
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "fake.mp4"
            f.write_text("This is just a plain text file pretending.\n", encoding="utf-8")
            with patch("src.video.generator.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="invalid")
                ok, err = validate_video_file_with_ffprobe(f)
            self.assertFalse(ok)

    def test_R05_ffprobe_failure_rejected(self):
        """When ffprobe subprocess returns non-zero, must fail."""
        from src.video.generator import validate_video_file_with_ffprobe
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "bad.mp4"
            f.write_bytes(b"\x00" * 100)
            with patch("src.video.generator.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=1, stdout="", stderr="moov atom not found"
                )
                ok, err = validate_video_file_with_ffprobe(f)
            self.assertFalse(ok)
            self.assertIn("ffprobe failed", err)

    def test_R06_missing_video_stream_rejected(self):
        from src.video.generator import validate_video_file_with_ffprobe
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "nostream.mp4"
            f.write_bytes(b"\x00" * 100)
            probe_json = json.dumps({"streams": [{"codec_type": "audio", "codec_name": "aac"}], "format": {"duration": "10"}})
            with patch("src.video.generator.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout=probe_json, stderr="")
                ok, err = validate_video_file_with_ffprobe(f)
            self.assertFalse(ok)
            self.assertIn("No video stream", err)

    def test_R07_missing_audio_stream_rejected(self):
        from src.video.generator import validate_video_file_with_ffprobe
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "noaudio.mp4"
            f.write_bytes(b"\x00" * 100)
            probe_json = json.dumps({"streams": [{"codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p", "width": 720, "height": 1280}], "format": {"duration": "10"}})
            with patch("src.video.generator.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout=probe_json, stderr="")
                ok, err = validate_video_file_with_ffprobe(f)
            self.assertFalse(ok)
            self.assertIn("No audio stream", err)

    def test_R08_invalid_codec_rejected(self):
        from src.video.generator import validate_video_file_with_ffprobe
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "vp9.mp4"
            f.write_bytes(b"\x00" * 100)
            probe_json = json.dumps({"streams": [
                {"codec_type": "video", "codec_name": "vp9", "pix_fmt": "yuv420p", "width": 720, "height": 1280},
                {"codec_type": "audio", "codec_name": "aac"}
            ], "format": {"duration": "10"}})
            with patch("src.video.generator.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout=probe_json, stderr="")
                ok, err = validate_video_file_with_ffprobe(f)
            self.assertFalse(ok)
            self.assertIn("Invalid codec", err)

    def test_R09_invalid_pix_fmt_rejected(self):
        from src.video.generator import validate_video_file_with_ffprobe
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "rgb.mp4"
            f.write_bytes(b"\x00" * 100)
            probe_json = json.dumps({"streams": [
                {"codec_type": "video", "codec_name": "h264", "pix_fmt": "rgb24", "width": 720, "height": 1280},
                {"codec_type": "audio", "codec_name": "aac"}
            ], "format": {"duration": "10"}})
            with patch("src.video.generator.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout=probe_json, stderr="")
                ok, err = validate_video_file_with_ffprobe(f)
            self.assertFalse(ok)
            self.assertIn("Invalid pixel format", err)

    def test_R10_invalid_resolution_rejected(self):
        from src.video.generator import validate_video_file_with_ffprobe
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "landscape.mp4"
            f.write_bytes(b"\x00" * 100)
            probe_json = json.dumps({"streams": [
                {"codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p", "width": 1920, "height": 1080},
                {"codec_type": "audio", "codec_name": "aac"}
            ], "format": {"duration": "10"}})
            with patch("src.video.generator.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout=probe_json, stderr="")
                ok, err = validate_video_file_with_ffprobe(f)
            self.assertFalse(ok)
            self.assertIn("Invalid resolution", err)

    def test_R11_zero_duration_rejected(self):
        from src.video.generator import validate_video_file_with_ffprobe
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "nodur.mp4"
            f.write_bytes(b"\x00" * 100)
            probe_json = json.dumps({"streams": [
                {"codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p", "width": 720, "height": 1280, "duration": "0"},
                {"codec_type": "audio", "codec_name": "aac"}
            ], "format": {"duration": "0"}})
            with patch("src.video.generator.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout=probe_json, stderr="")
                ok, err = validate_video_file_with_ffprobe(f)
            self.assertFalse(ok)
            self.assertIn("not positive", err)

    def test_R12_valid_real_mp4_accepted(self):
        """A well-formed video passing all ffprobe + ffmpeg checks must succeed."""
        from src.video.generator import validate_video_file_with_ffprobe
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "good.mp4"
            f.write_bytes(b"\x00" * 100)
            probe_json = json.dumps({"streams": [
                {"codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p", "width": 720, "height": 1280, "duration": "148.5"},
                {"codec_type": "audio", "codec_name": "aac", "channels": 2}
            ], "format": {"duration": "148.5"}})
            with patch("src.video.generator.subprocess.run") as mock_run:
                # First call = ffprobe, second call = ffmpeg decode
                mock_run.side_effect = [
                    MagicMock(returncode=0, stdout=probe_json, stderr=""),
                    MagicMock(returncode=0, stdout="", stderr=""),
                ]
                ok, err = validate_video_file_with_ffprobe(f)
            self.assertTrue(ok, f"Should accept valid video: {err}")

    def test_R13_ffmpeg_decode_failure_rejected(self):
        from src.video.generator import validate_video_file_with_ffprobe
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "undecodable.mp4"
            f.write_bytes(b"\x00" * 100)
            probe_json = json.dumps({"streams": [
                {"codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p", "width": 720, "height": 1280},
                {"codec_type": "audio", "codec_name": "aac"}
            ], "format": {"duration": "148.5"}})
            with patch("src.video.generator.subprocess.run") as mock_run:
                mock_run.side_effect = [
                    MagicMock(returncode=0, stdout=probe_json, stderr=""),
                    MagicMock(returncode=1, stdout="", stderr="Invalid data found"),
                ]
                ok, err = validate_video_file_with_ffprobe(f)
            self.assertFalse(ok)
            self.assertIn("decode test failed", err)

    def test_R14_ffmpeg_decode_success_accepted(self):
        """Same as R12 but explicitly verifying the decode step is invoked."""
        from src.video.generator import validate_video_file_with_ffprobe
        with tempfile.TemporaryDirectory() as td:
            f = Path(td) / "decodeable.mp4"
            f.write_bytes(b"\x00" * 100)
            probe_json = json.dumps({"streams": [
                {"codec_type": "video", "codec_name": "h264", "pix_fmt": "yuv420p", "width": 720, "height": 1280},
                {"codec_type": "audio", "codec_name": "aac", "channels": 2}
            ], "format": {"duration": "60.0"}})
            with patch("src.video.generator.subprocess.run") as mock_run:
                mock_run.side_effect = [
                    MagicMock(returncode=0, stdout=probe_json, stderr=""),
                    MagicMock(returncode=0, stdout="", stderr=""),  # decode OK
                ]
                ok, err = validate_video_file_with_ffprobe(f)
            self.assertTrue(ok)
            # Verify decode was actually called (2 subprocess calls)
            self.assertEqual(mock_run.call_count, 2)

    def test_R15_production_cli_defaults_to_ffmpeg(self):
        """CLI main() must default to composer_type='ffmpeg'."""
        import inspect
        source = inspect.getsource(run_video_generator.main)
        self.assertIn('composer_type = "ffmpeg"', source)

    def test_R16_explicit_mock_still_works_for_tests(self):
        """--composer mock must still be accepted for unit tests."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            amap, vmap = _make_timing_maps(create_files=True, tmp_dir=tmp, scene_count=2)
            out_map = compose_video_pipeline(amap, vmap, composer_type="mock", output_dir=tmp)
            self.assertIn("video_file", out_map)
            self.assertIn(out_map["resolution"], ("720x1280", "1080x1920"))

    def test_R17_deterministic_output(self):
        """Two mock runs on identical inputs produce identical maps (except timestamps/paths)."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            amap, vmap = _make_timing_maps(create_files=True, tmp_dir=tmp, scene_count=2)
            m1 = compose_video_pipeline(amap, vmap, composer_type="mock", output_dir=tmp)
            m2 = compose_video_pipeline(amap, vmap, composer_type="mock", output_dir=tmp)
            self.assertEqual(m1["total_duration"], m2["total_duration"])
            self.assertEqual(m1["resolution"], m2["resolution"])
            self.assertEqual(len(m1["scenes"]), len(m2["scenes"]))


# ─────────────────────────────────────────────────────────────────────────────
class TestRunIDAndMockMediaRegression(unittest.TestCase):
    """
    Regression tests ensuring:
    - Mismatched run_id between audio and visual maps is rejected.
    - Mismatched selected_topic is rejected.
    - Mock-provider-only maps cannot reach production video composition.
    - Auto-discovery prefers production maps over mock-only maps.
    - Auto-discovery matches by run_id, then script_title.
    """

    def _prod_meta(self):
        return {
            "approved_for_generation": True,
            "data_source": "youtube_api",
            "confidence": "high",
            "selected_topic": "Why Lord Shiva Wears a Snake Around His Neck",
        }

    def _make_maps_with_run_id(self, audio_run_id, visual_run_id,
                                title="Secrets of Shiva's Snake",
                                audio_topic=None, visual_topic=None):
        meta_a = self._prod_meta()
        meta_v = self._prod_meta()
        if audio_topic:
            meta_a["selected_topic"] = audio_topic
        if visual_topic:
            meta_v["selected_topic"] = visual_topic

        amap = {
            "run_id": audio_run_id,
            "script_title": title,
            "total_duration_seconds": 30,
            "provider": "gtts",
            "audio_scenes": [
                {"scene": 1, "voice_text": "t", "audio_file": "a.mp3", "duration_seconds": 30}
            ],
            "full_narration_audio_file": "full.mp3",
            "approval_metadata": meta_a,
        }
        vmap = {
            "run_id": visual_run_id,
            "script_title": title,
            "total_scenes": 1,
            "style_preset": "Devotional Cinematic",
            "provider": "pollinations",
            "visual_scenes": [
                {"scene": 1, "visual_prompt": "p", "image_file": "s.png",
                 "style": "Devotional", "duration_seconds": 30}
            ],
            "approval_metadata": meta_v,
        }
        return amap, vmap

    # ── run_id mismatch ──────────────────────────────────────────────────────

    def test_R18_matching_run_ids_accepted(self):
        """Audio + visual maps with the same run_id must be accepted."""
        amap, vmap = self._make_maps_with_run_id("run_20260813_120000", "run_20260813_120000")
        ok, err = validate_input_maps(amap, vmap)
        self.assertTrue(ok, f"Same run_id should be accepted: {err}")

    def test_R19_mismatched_run_ids_rejected(self):
        """Audio + visual maps with different run_ids must be rejected."""
        amap, vmap = self._make_maps_with_run_id("run_20260813_100000", "run_20260813_190000")
        ok, err = validate_input_maps(amap, vmap)
        self.assertFalse(ok, "Mismatched run_ids should be rejected")
        self.assertIn("run_id", err)

    def test_R20_missing_run_id_not_blocked(self):
        """Maps without run_id at all should not be blocked by the run_id check."""
        amap, vmap = self._make_maps_with_run_id("run_X", "run_X")
        del amap["run_id"]
        del vmap["run_id"]
        ok, err = validate_input_maps(amap, vmap)
        self.assertTrue(ok, f"Maps without run_id should pass (no check): {err}")

    def test_R21_one_sided_run_id_not_blocked(self):
        """If only one map has run_id, the check is skipped (not a mismatch)."""
        amap, vmap = self._make_maps_with_run_id("run_20260813_100000", "run_20260813_100000")
        del vmap["run_id"]  # visual has no run_id
        ok, err = validate_input_maps(amap, vmap)
        self.assertTrue(ok, f"One-sided run_id should not trigger mismatch: {err}")

    # ── selected_topic mismatch ──────────────────────────────────────────────

    def test_R22_mismatched_selected_topic_rejected(self):
        """Audio and visual maps with different selected_topic must be rejected."""
        amap, vmap = self._make_maps_with_run_id(
            "run_X", "run_X",
            audio_topic="Shiva's Snake",
            visual_topic="Ganesha's Trunk",
        )
        ok, err = validate_input_maps(amap, vmap)
        self.assertFalse(ok, "Mismatched selected_topic should be rejected")
        self.assertIn("selected_topic", err)

    # ── mock-media production gate ───────────────────────────────────────────

    def test_R23_is_mock_only_true_for_mock_no_real_approval(self):
        """_is_mock_only returns True for provider='mock' with no real approval."""
        data = {"provider": "mock", "approval_metadata": {"data_source": "mock"}}
        self.assertTrue(run_video_generator._is_mock_only(data))

    def test_R24_is_mock_only_false_for_real_provider(self):
        """_is_mock_only returns False when provider is 'gtts' (production)."""
        data = {"provider": "gtts", "approval_metadata": {"data_source": "youtube_api"}}
        self.assertFalse(run_video_generator._is_mock_only(data))

    def test_R25_is_mock_only_false_for_mock_with_real_approval(self):
        """_is_mock_only returns False when provider='mock' BUT has real youtube_api source."""
        data = {"provider": "mock", "approval_metadata": {"data_source": "youtube_api"}}
        self.assertFalse(run_video_generator._is_mock_only(data))

    def test_R26_is_mock_only_false_for_missing_provider(self):
        """_is_mock_only returns False for maps with no provider key."""
        data = {"approval_metadata": {"data_source": "youtube_api"}}
        self.assertFalse(run_video_generator._is_mock_only(data))

    # ── _find_paired_maps discovery ──────────────────────────────────────────

    def test_R27_find_paired_maps_prefers_production_over_mock(self):
        """
        _find_paired_maps must return the production map even when a mock-only
        map has a later timestamp (simulating the original 148s vs 159s bug).
        """
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            audio_dir  = tmp / "audio"
            visual_dir = tmp / "visuals"
            audio_dir.mkdir(); visual_dir.mkdir()

            prod_meta = {
                "approved_for_generation": True,
                "data_source": "youtube_api",
                "confidence": "high",
                "selected_topic": "Shiva Topic",
            }

            # Older production audio map
            prod_audio = {
                "run_id": "run_20260813_100000",
                "script_title": "Shiva Script",
                "provider": "gtts",
                "audio_scenes": [],
                "approval_metadata": prod_meta,
            }
            # Newer mock-only audio map (should be deprioritised)
            mock_audio = {
                "run_id": "run_20260813_200000",
                "script_title": "Shiva Script",
                "provider": "mock",
                "audio_scenes": [],
                "approval_metadata": {"data_source": "mock"},
            }

            prod_visual = {
                "run_id": "run_20260813_100000",
                "script_title": "Shiva Script",
                "provider": "pollinations",
                "visual_scenes": [],
                "approval_metadata": prod_meta,
            }
            mock_visual = {
                "run_id": "run_20260813_200000",
                "script_title": "Shiva Script",
                "provider": "mock",
                "visual_scenes": [],
                "approval_metadata": {"data_source": "mock"},
            }

            (audio_dir  / "audio_map_20260813_100000.json").write_text(json.dumps(prod_audio))
            (audio_dir  / "audio_map_20260813_200000.json").write_text(json.dumps(mock_audio))
            (visual_dir / "visual_map_20260813_100000.json").write_text(json.dumps(prod_visual))
            (visual_dir / "visual_map_20260813_200000.json").write_text(json.dumps(mock_visual))

            a_path, v_path = run_video_generator._find_paired_maps(audio_dir, visual_dir)

            self.assertIn("100000", a_path.name,
                          f"Expected production (100000) audio map, got {a_path.name}")
            self.assertIn("100000", v_path.name,
                          f"Expected production (100000) visual map, got {v_path.name}")

    def test_R28_find_paired_maps_matches_by_run_id(self):
        """_find_paired_maps returns the pair sharing the same run_id."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            audio_dir  = tmp / "audio"
            visual_dir = tmp / "visuals"
            audio_dir.mkdir(); visual_dir.mkdir()

            prod_meta = {
                "approved_for_generation": True,
                "data_source": "youtube_api",
                "confidence": "high",
                "selected_topic": "Shiva Topic",
            }

            a1 = {"run_id": "run_A", "script_title": "T", "provider": "gtts",
                  "audio_scenes": [], "approval_metadata": prod_meta}
            a2 = {"run_id": "run_B", "script_title": "T", "provider": "gtts",
                  "audio_scenes": [], "approval_metadata": prod_meta}
            v_b = {"run_id": "run_B", "script_title": "T", "provider": "pollinations",
                   "visual_scenes": [], "approval_metadata": prod_meta}

            (audio_dir  / "audio_map_A.json").write_text(json.dumps(a1))
            (audio_dir  / "audio_map_B.json").write_text(json.dumps(a2))
            (visual_dir / "visual_map_B.json").write_text(json.dumps(v_b))

            a_path, v_path = run_video_generator._find_paired_maps(audio_dir, visual_dir)

            self.assertIn("audio_map_B", a_path.name,
                          f"Expected run_B audio map, got {a_path.name}")

    def test_R29_find_paired_maps_falls_back_to_script_title(self):
        """_find_paired_maps falls back to script_title matching when run_id absent."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            audio_dir  = tmp / "audio"
            visual_dir = tmp / "visuals"
            audio_dir.mkdir(); visual_dir.mkdir()

            prod_meta = {
                "approved_for_generation": True,
                "data_source": "youtube_api",
                "confidence": "high",
                "selected_topic": "Shiva Topic",
            }

            # No run_id, but matching script_title
            amap = {"script_title": "ShivaTitle", "provider": "gtts",
                    "audio_scenes": [], "approval_metadata": prod_meta}
            vmap = {"script_title": "ShivaTitle", "provider": "pollinations",
                    "visual_scenes": [], "approval_metadata": prod_meta}

            (audio_dir  / "audio_map_T.json").write_text(json.dumps(amap))
            (visual_dir / "visual_map_T.json").write_text(json.dumps(vmap))

            a_path, v_path = run_video_generator._find_paired_maps(audio_dir, visual_dir)
            self.assertIn("audio_map_T", a_path.name)
            self.assertIn("visual_map_T", v_path.name)

