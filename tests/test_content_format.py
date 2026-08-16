# tests/test_content_format.py
# Phase 12 — End-to-End Content Format Architecture Tests (SHORT vs LONG)

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.script.schemas import validate_script_output
from src.video.generator import (
    compose_video_pipeline,
    perform_video_qa,
    validate_video_file_with_ffprobe,
)
from src.qa.checks import check_video_map, check_video_with_ffprobe
from src.qa.gate import FinalQAGate
from src.publisher.safety import validate_qa_for_publishing, PublisherSafetyError, verify_video_with_ffprobe
from src.publisher.metadata import build_video_metadata
from src.publisher.uploader import publish_video


def _make_mock_script(content_type="short"):
    s = {
        "title": "Test Title",
        "duration_seconds": 60 if content_type == "short" else 300,
        "narration": "Test narration text.",
        "retention_hooks": ["Hook 1"],
        "scene_scripts": [
            {
                "scene": 1,
                "duration_seconds": 60 if content_type == "short" else 300,
                "visual_reference": "Ref",
                "voice_text": "Text",
                "emotion": "Serene",
            }
        ],
    }
    if content_type == "short":
        s["shorts_scripts"] = [{"title": "S1", "hook": "H1", "body": "B1"}]
    else:
        s["long_form_metadata"] = {"chapters": ["Intro", "Main", "Outro"]}
    return s


def _make_mock_maps(tmpdir: Path, content_type="short", duration=60):
    res = "1080x1920" if content_type == "short" else "1920x1080"
    
    # Create dummy audio and image files
    aud_file = tmpdir / "audio.mp3"
    aud_file.write_bytes(b"MOCK_AUDIO_CONTENT_12345")
    img_file = tmpdir / "image.jpg"
    img_file.write_bytes(b"MOCK_IMAGE_CONTENT_12345")

    meta = {
        "approved_for_generation": True,
        "data_source": "youtube_api",
        "confidence": "high",
        "selected_topic": "Lord Shiva Story",
    }

    audio_map = {
        "run_id": "run_test_001",
        "script_title": "Lord Shiva Story",
        "total_duration_seconds": duration,
        "language_code": "hi-IN",
        "approval_metadata": meta,
        "audio_scenes": [
            {
                "scene": 1,
                "audio_file": str(aud_file.absolute()).replace("\\", "/"),
                "duration_seconds": duration,
                "voice_text": "Test narration",
            }
        ],
    }

    visual_map = {
        "run_id": "run_test_001",
        "script_title": "Lord Shiva Story",
        "provider": "mock",
        "approval_metadata": meta,
        "visual_scenes": [
            {
                "scene": 1,
                "image_file": str(img_file.absolute()).replace("\\", "/"),
                "duration_seconds": duration,
            }
        ],
    }

    return audio_map, visual_map


class TestScriptSchemaFormat(unittest.TestCase):

    def test_01_short_script_valid(self):
        s = _make_mock_script("short")
        ok, err = validate_script_output(s, content_type="short")
        self.assertTrue(ok, f"Expected short script to pass, got: {err}")

    def test_02_short_script_missing_shorts_scripts_fails(self):
        s = _make_mock_script("long")  # no shorts_scripts
        ok, err = validate_script_output(s, content_type="short")
        self.assertFalse(ok)
        self.assertIn("shorts_scripts", err)

    def test_03_long_script_without_shorts_scripts_valid(self):
        s = _make_mock_script("long")
        ok, err = validate_script_output(s, content_type="long")
        self.assertTrue(ok, f"Expected long script to pass without shorts_scripts, got: {err}")

    def test_04_invalid_content_type_rejected(self):
        s = _make_mock_script("short")
        ok, err = validate_script_output(s, content_type="invalid_format")
        self.assertFalse(ok)
        self.assertIn("content_type", err)


class TestVideoGeneratorFormat(unittest.TestCase):

    def setUp(self):
        self.tmpdir_obj = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmpdir_obj.name)

    def tearDown(self):
        self.tmpdir_obj.cleanup()

    def test_05_short_video_composition_output_map(self):
        a_map, v_map = _make_mock_maps(self.tmpdir, content_type="short", duration=60)
        vmap = compose_video_pipeline(
            audio_map=a_map,
            visual_map=v_map,
            composer_type="mock",
            output_dir=self.tmpdir,
            content_type="short",
        )
        self.assertEqual(vmap["content_type"], "short")
        self.assertEqual(vmap["aspect_ratio"], "9:16")
        self.assertEqual(vmap["resolution"], "1080x1920")

    def test_06_long_video_composition_output_map(self):
        a_map, v_map = _make_mock_maps(self.tmpdir, content_type="long", duration=300)
        vmap = compose_video_pipeline(
            audio_map=a_map,
            visual_map=v_map,
            composer_type="mock",
            output_dir=self.tmpdir,
            content_type="long",
        )
        self.assertEqual(vmap["content_type"], "long")
        self.assertEqual(vmap["aspect_ratio"], "16:9")
        self.assertEqual(vmap["resolution"], "1920x1080")

    def test_07_short_rejects_1920x1080_resolution_mismatch(self):
        a_map, v_map = _make_mock_maps(self.tmpdir, content_type="short", duration=60)
        with self.assertRaises(ValueError) as ctx:
            compose_video_pipeline(
                audio_map=a_map,
                visual_map=v_map,
                composer_type="mock",
                output_dir=self.tmpdir,
                resolution="1920x1080",
                content_type="short",
            )
        self.assertIn("mismatch", str(ctx.exception).lower())

    def test_08_long_rejects_1080x1920_resolution_mismatch(self):
        a_map, v_map = _make_mock_maps(self.tmpdir, content_type="long", duration=300)
        with self.assertRaises(ValueError) as ctx:
            compose_video_pipeline(
                audio_map=a_map,
                visual_map=v_map,
                composer_type="mock",
                output_dir=self.tmpdir,
                resolution="1080x1920",
                content_type="long",
            )
        self.assertIn("mismatch", str(ctx.exception).lower())


class TestVideoQAFortmat(unittest.TestCase):

    def setUp(self):
        self.tmpdir_obj = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmpdir_obj.name)

    def tearDown(self):
        self.tmpdir_obj.cleanup()

    def test_09_check_video_map_format_matching(self):
        vmap_short = {
            "video_file": str((self.tmpdir / "test.mp4").absolute()),
            "video_map_file": str((self.tmpdir / "test_map.json").absolute()),
            "total_duration": 60,
            "resolution": "1080x1920",
            "content_type": "short",
            "aspect_ratio": "9:16",
            "scenes": [{"scene": 1, "image_file": "img.jpg", "audio_file": "aud.mp3", "duration_seconds": 60}],
        }
        (self.tmpdir / "test.mp4").write_bytes(b"MOCK_MP4_VIDEO")

        ok, err = check_video_map(vmap_short, content_type="short")
        self.assertTrue(ok, f"Expected short map to pass, got: {err}")

        # Check format mismatch rejection
        ok, err = check_video_map(vmap_short, content_type="long")
        self.assertFalse(ok)
        self.assertIn("mismatch", err)

    def test_10_missing_file_rejected(self):
        vmap = {
            "video_file": str((self.tmpdir / "nonexistent.mp4").absolute()),
            "video_map_file": "map.json",
            "total_duration": 60,
            "resolution": "1080x1920",
            "content_type": "short",
            "aspect_ratio": "9:16",
            "scenes": [{"scene": 1, "image_file": "img.jpg", "audio_file": "aud.mp3", "duration_seconds": 60}],
        }
        ok, err = check_video_map(vmap, content_type="short")
        self.assertFalse(ok)
        self.assertIn("not found", err)


class TestPublisherRoutingAndMetadata(unittest.TestCase):

    def test_11_metadata_short_includes_shorts_tag(self):
        qa = {
            "selected_topic": "Test Topic",
            "content_type": "short",
            "artifacts": {},
        }
        meta = build_video_metadata(qa)
        self.assertIn("Shorts", meta["tags"])
        self.assertIn("#Shorts", meta["description"])
        self.assertEqual(meta["content_type"], "short")

    def test_12_metadata_long_omits_shorts_tag(self):
        qa = {
            "selected_topic": "Test Topic",
            "content_type": "long",
            "artifacts": {},
        }
        meta = build_video_metadata(qa)
        self.assertNotIn("Shorts", meta["tags"])
        self.assertNotIn("#Shorts", meta["description"])
        self.assertEqual(meta["content_type"], "long")

    def test_13_missing_content_type_blocks_publishing(self):
        qa = {
            "approved_for_publishing": True,
            "approval_metadata": {
                "approved_for_generation": True,
            },
            "data_source": "youtube_api",
            "confidence": "high",
            "selected_topic": "Test Topic",
            "artifacts": {"video": "nonexistent_map.json"},
            # content_type IS MISSING
        }
        with self.assertRaises(PublisherSafetyError) as ctx:
            validate_qa_for_publishing(qa)
        self.assertIn("content_type is missing", str(ctx.exception))

    def test_14_invalid_content_type_blocks_publishing(self):
        qa = {
            "approved_for_publishing": True,
            "approval_metadata": {
                "approved_for_generation": True,
            },
            "data_source": "youtube_api",
            "confidence": "high",
            "selected_topic": "Test Topic",
            "content_type": "invalid_format",
            "artifacts": {"video": "map.json"},
        }
        with self.assertRaises(PublisherSafetyError) as ctx:
            validate_qa_for_publishing(qa)
        self.assertIn("Invalid content_type", str(ctx.exception))


class TestPublisherManifestAndThumbnail(unittest.TestCase):

    def setUp(self):
        self.tmpdir_obj = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmpdir_obj.name)

    def tearDown(self):
        self.tmpdir_obj.cleanup()

    @patch("youtube_uploader.upload_to_youtube", return_value="MOCK_VIDEO_ID_123")
    @patch("src.publisher.uploader.upload_thumbnail", return_value=True)
    @patch("src.publisher.safety.verify_video_with_ffprobe")
    def test_15_publish_video_records_format_metadata_in_manifest(self, mock_ffprobe, mock_thumb, mock_yt):
        video_file = self.tmpdir / "test_long.mp4"
        video_file.write_bytes(b"MOCK_REAL_MP4_CONTENT")
        thumb_file = self.tmpdir / "thumb.png"
        thumb_file.write_bytes(b"MOCK_THUMB_CONTENT")

        qa = {
            "selected_topic": "Test Topic",
            "content_type": "long",
            "aspect_ratio": "16:9",
            "resolution": "1920x1080",
            "video_validation": {"duration_seconds": 300.0},
            "artifacts": {},
            "approval_metadata": {},
        }

        manifest = publish_video(
            creds=MagicMock(),
            video_file=video_file,
            title="Test Long Title",
            description="Description",
            tags=["tag1"],
            category_id="27",
            thumbnail_file=thumb_file,
            qa=qa,
            output_dir=self.tmpdir,
        )

        self.assertEqual(manifest["video_id"], "MOCK_VIDEO_ID_123")
        self.assertEqual(manifest["content_type"], "long")
        self.assertEqual(manifest["aspect_ratio"], "16:9")
        self.assertEqual(manifest["resolution"], "1920x1080")
        self.assertEqual(manifest["duration_seconds"], 300.0)
        self.assertTrue(manifest["thumbnail_uploaded"])
        self.assertEqual(manifest["privacy_status"], "public")

        manifest_path = Path(manifest["_manifest_path"])
        self.assertTrue(manifest_path.exists())
        saved_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(saved_data["content_type"], "long")

    def test_16_multilingual_long_support(self):
        """Verify that long-form script and video composition supports hi-IN, te-IN, and ta-IN language codes."""
        for lang_code in ("hi-IN", "te-IN", "ta-IN"):
            a_map, v_map = _make_mock_maps(self.tmpdir, content_type="long", duration=120)
            a_map["language_code"] = lang_code
            vmap_out = compose_video_pipeline(
                audio_map=a_map,
                visual_map=v_map,
                composer_type="mock",
                output_dir=self.tmpdir,
                content_type="long",
            )
            self.assertEqual(vmap_out["content_type"], "long")
            self.assertEqual(vmap_out["resolution"], "1920x1080")
            self.assertEqual(vmap_out["aspect_ratio"], "16:9")

    def test_17_duplicate_publishing_protection(self):
        """Verify that attempts to publish a video already recorded in publish_manifest are blocked."""
        from src.publisher.safety import check_duplicate_publishing, PublisherSafetyError

        mp4_file = self.tmpdir / "dup_test.mp4"
        mp4_file.write_bytes(b"\x00\x00\x00\x20ftyp" + b"\x00" * 1200)

        vmap_file = self.tmpdir / "dup_video_map.json"
        vmap_file.write_text(json.dumps({"video_file": str(mp4_file.absolute())}), encoding="utf-8")

        qa = {
            "approved_for_publishing": True,
            "selected_topic": "Test Topic",
            "confidence": "high",
            "data_source": "youtube_api",
            "content_type": "long",
            "artifacts": {"video": str(vmap_file.absolute())},
            "approval_metadata": {"approved_for_generation": True},
        }

        # First check: no manifests exist yet -> not duplicate
        is_dup, _ = check_duplicate_publishing(qa, manifest_dir=self.tmpdir)
        self.assertFalse(is_dup)

        # Create a mock existing publishing manifest for this video file
        manifest_data = {
            "video_id": "MOCK_EXISTING_ID_999",
            "success": True,
            "video_file": str(mp4_file.absolute()),
            "source_artifacts": {"video": str(vmap_file.absolute())},
        }
        (self.tmpdir / "publish_manifest_20260815_120000.json").write_text(
            json.dumps(manifest_data), encoding="utf-8"
        )

        # Second check: manifest exists -> duplicate detected!
        is_dup, dup_msg = check_duplicate_publishing(qa, manifest_dir=self.tmpdir)
        self.assertTrue(is_dup)
        self.assertIn("Duplicate upload blocked", dup_msg)

        # validate_qa_for_publishing must raise PublisherSafetyError
        with self.assertRaises(PublisherSafetyError) as ctx:
            validate_qa_for_publishing(qa, manifest_dir=self.tmpdir)
        self.assertIn("Duplicate upload blocked", str(ctx.exception))

    def test_18_duplicate_history_file_protection(self):
        """Verify that check_duplicate_publishing checks history_file across runs when manifest_dir is empty."""
        from src.publisher.safety import check_duplicate_publishing, PublisherSafetyError

        empty_manifest_dir = self.tmpdir / "empty_manifests"
        empty_manifest_dir.mkdir()

        hist_file = self.tmpdir / "publishing_history.json"
        hist_records = [
            {
                "youtube_video_id": "PREV_YT_ID_100",
                "topic": "Why Lord Shiva Wears a Snake Around His Neck",
                "title": "Secrets of Shiva's Snake",
                "video_file_name": "shiva_long_production_final.mp4"
            }
        ]
        hist_file.write_text(json.dumps(hist_records), encoding="utf-8")

        qa = {
            "approved_for_publishing": True,
            "selected_topic": "Why Lord Shiva Wears a Snake Around His Neck",
            "title": "Secrets of Shiva's Snake",
            "confidence": "high",
            "data_source": "youtube_api",
            "content_type": "long",
            "artifacts": {},
            "approval_metadata": {"approved_for_generation": True},
        }

        is_dup, dup_msg = check_duplicate_publishing(qa, manifest_dir=empty_manifest_dir, history_file=hist_file)
        self.assertTrue(is_dup)
        self.assertIn("Duplicate upload blocked", dup_msg)
        self.assertIn("Why Lord Shiva Wears a Snake Around His Neck", dup_msg)


if __name__ == "__main__":
    unittest.main()
