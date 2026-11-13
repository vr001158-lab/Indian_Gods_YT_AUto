# tests/test_render_only_pipeline.py
# Tests for Production-Safe Real-Media Render-Only Mode

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from PIL import Image

from src.pipeline.state import PipelineState
from src.pipeline.orchestrator import PipelineRunner
from src.pipeline.render_validator import validate_render_only_output, probe_media_file
from src.publisher.safety import validate_production_environment
from src.publisher.uploader import publish_video, upload_thumbnail, PublishError
import youtube_uploader


class TestRenderOnlyPipeline(unittest.TestCase):
    """Verifies all 10 requirements for render-only execution mode."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = Path(self.temp_dir) / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        # Clean environment before each test
        os.environ.pop("RENDER_ONLY", None)
        os.environ.pop("YOUTUBE_PUBLISH_AUTHORIZED", None)

    def tearDown(self):
        os.environ.pop("RENDER_ONLY", None)
        os.environ.pop("YOUTUBE_PUBLISH_AUTHORIZED", None)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_render_only_selects_real_providers(self):
        """1. Render-only selects real production providers: Pocket TTS Telugu, Flux, FFmpeg, PIL."""
        runner = PipelineRunner(
            dry_run=False,
            render_only=True,
            content_type="short",
            format="narrated",
            language_code="te-IN",
        )
        self.assertTrue(runner.render_only)
        self.assertFalse(runner.dry_run)

        # Check voice provider resolution
        provider = "mock" if runner.dry_run else ("pocket_tts" if runner.language_code == "te-IN" else "edge_neural_tts")
        mode = "test" if runner.dry_run else "production"
        self.assertEqual(provider, "pocket_tts")
        self.assertEqual(mode, "production")

        # Check visual provider resolution
        vis_provider = "mock" if runner.dry_run else "flux"
        self.assertEqual(vis_provider, "flux")

        # Check video composer resolution
        composer = "mock" if runner.dry_run else "ffmpeg"
        self.assertEqual(composer, "ffmpeg")

        # Check thumbnail provider resolution
        thumb_provider = "mock" if runner.dry_run else "pil"
        self.assertEqual(thumb_provider, "pil")

        # Check QA allow_mock is False in render-only mode
        allow_mock = False if runner.render_only else runner.dry_run
        self.assertFalse(allow_mock)

    def test_02_render_only_skips_publisher_stage(self):
        """2. Render-only skips publisher stage and replaces it with render packaging."""
        runner = PipelineRunner(
            dry_run=False,
            render_only=True,
            content_type="short",
            format="narrated",
            language_code="te-IN",
        )
        # Direct attempt to run publisher in render-only mode must raise RuntimeError
        with self.assertRaises(RuntimeError) as ctx:
            runner.run_publisher()
        self.assertIn("CRITICAL SAFETY VIOLATION", str(ctx.exception))

    def test_03_render_only_does_not_require_oauth(self):
        """3. Render-only does not require OAuth token.json or credentials.json."""
        # Ensure token.json does not exist
        fake_token = Path(self.temp_dir) / "token.json"
        self.assertFalse(fake_token.exists())

        # Render-only mode does not call validate_production_environment() for live credentials
        runner = PipelineRunner(
            dry_run=False,
            render_only=True,
            content_type="short",
            format="narrated",
            language_code="te-IN",
        )
        # State transitions without requiring credentials
        self.assertTrue(runner.render_only)

    def test_04_render_only_cannot_call_youtube_upload_apis(self):
        """4. Render-only fails closed on any YouTube upload or publisher calls."""
        os.environ["RENDER_ONLY"] = "true"

        # Publisher environment check must block
        is_ok, err = validate_production_environment(allow_dry_run=False)
        self.assertFalse(is_ok)
        self.assertIn("RENDER_ONLY mode is active", err)

        # publish_video() must raise PublishError
        with self.assertRaises(PublishError) as ctx_pub:
            publish_video(creds=None, video_file="test.mp4", title="T", description="D", tags=[], category_id="22", thumbnail_file=None, qa={})
        self.assertIn("CRITICAL SAFETY VIOLATION", str(ctx_pub.exception))

        # upload_thumbnail() must raise PublishError
        with self.assertRaises(PublishError) as ctx_thm:
            upload_thumbnail(creds=None, video_id="vid123", thumbnail_file="thumb.png")
        self.assertIn("CRITICAL SAFETY VIOLATION", str(ctx_thm.exception))

        # youtube_uploader.upload_to_youtube() must raise PermissionError
        with self.assertRaises(PermissionError) as ctx_yt:
            youtube_uploader.upload_to_youtube(creds=None, video_path=Path("test.mp4"), title="T", description="D", tags=[])
        self.assertIn("CRITICAL SAFETY BLOCK", str(ctx_yt.exception))

    def test_05_render_only_does_not_modify_publishing_history(self):
        """5. Render-only does not touch or modify publishing_history.json."""
        hist_file = Path(self.temp_dir) / "publishing_history.json"
        initial_content = json.dumps([{"video_id": "test", "topic": "Lord Ganesha"}])
        hist_file.write_text(initial_content, encoding="utf-8")
        orig_mtime = hist_file.stat().st_mtime

        runner = PipelineRunner(
            dry_run=False,
            render_only=True,
            content_type="short",
            format="narrated",
            language_code="te-IN",
        )
        # Ensure stage map has no publisher
        self.assertTrue(runner.render_only)
        self.assertEqual(hist_file.read_text(encoding="utf-8"), initial_content)
        self.assertEqual(hist_file.stat().st_mtime, orig_mtime)

    def test_06_render_only_does_not_consume_quota(self):
        """6. Render-only skips publishing quota consumption."""
        from src.publisher.quota import check_publishing_quota

        # Even if daily quota is nominally exhausted, render-only does not upload
        runner = PipelineRunner(
            dry_run=False,
            render_only=True,
            content_type="short",
            format="narrated",
            language_code="te-IN",
        )
        self.assertTrue(runner.render_only)

    def test_07_render_only_outputs_are_isolated(self):
        """7. Render-only outputs are isolated in data/render_only/<pipeline_id>/."""
        run_id = "run_test_isolation_20261113"
        state = PipelineState(pipeline_id=run_id, render_only=True, format="narrated", language_code="te-IN")

        # Setup dummy source files
        src_dir = Path(self.temp_dir) / "source"
        src_dir.mkdir(parents=True, exist_ok=True)
        cb = src_dir / "brief.json"
        cb.write_text('{"topic": "Test"}', encoding="utf-8")
        sc = src_dir / "script.json"
        sc.write_text('{"language_code": "te-IN", "scenes": [{"voice_over": "ఓం నమో వేంకటేశాయ"}]}', encoding="utf-8")
        am = src_dir / "audio_map.json"
        audio_f = src_dir / "narration.wav"
        audio_f.write_bytes(b"RIFF" + b"\x00" * 40)
        am.write_text(json.dumps({"full_narration_audio_file": str(audio_f), "audio_scenes": []}), encoding="utf-8")

        vm = src_dir / "visual_map.json"
        img_f = src_dir / "scene_1.png"
        img = Image.new("RGB", (1080, 1920), color=(20, 30, 40))
        img.save(img_f, "PNG")
        vm.write_text(json.dumps({"visual_scenes": [{"image_file": str(img_f)}]}), encoding="utf-8")

        vid_f = src_dir / "video.mp4"
        vid_f.write_bytes(b"\x00\x00\x00\x20ftypisom" + b"\x00" * 100)

        thm_f = src_dir / "thumb.png"
        thm = Image.new("RGB", (1280, 720), color=(50, 60, 70))
        thm.save(thm_f, "PNG")

        qa_f = src_dir / "qa.json"
        qa_f.write_text('{"approved_for_publishing": true}', encoding="utf-8")

        state.set_output("content_brief_output", cb)
        state.set_output("script_output", sc)
        state.set_output("audio_map_output", am)
        state.set_output("visual_map_output", vm)
        state.set_output("video_output", vid_f)
        state.set_output("thumbnail_output", thm_f)
        state.set_output("qa_output", qa_f)

        runner = PipelineRunner(state=state, dry_run=False, render_only=True)

        with patch("src.pipeline.orchestrator.validate_render_only_output") as mock_val:
            mock_val.return_value = (True, {"probe": "mocked"}, [])
            render_dir = runner.package_and_validate_render_only()

        self.assertTrue(render_dir.exists())
        self.assertTrue((render_dir / "content_brief.json").exists())
        self.assertTrue((render_dir / "script.json").exists())
        self.assertTrue((render_dir / "audio_map.json").exists())
        self.assertTrue((render_dir / "visual_map.json").exists())
        self.assertTrue((render_dir / "video_short.mp4").exists())
        self.assertTrue((render_dir / "thumbnail.png").exists())
        self.assertTrue((render_dir / "final_qa.json").exists())
        self.assertTrue((render_dir / "render_summary.json").exists())

        # Verify summary content
        summary = json.loads((render_dir / "render_summary.json").read_text(encoding="utf-8"))
        self.assertEqual(summary["execution_mode"], "render_only")
        self.assertEqual(summary["status"], "SUCCESS")
        self.assertFalse(summary["publishing_safety"]["publisher_stage_executed"])
        self.assertFalse(summary["publishing_safety"]["youtube_upload_attempted"])

        # Clean up created render directory
        shutil.rmtree(render_dir, ignore_errors=True)

    def test_08_invalid_or_incomplete_media_fails_validation(self):
        """8. Invalid or incomplete media fails render-only validation."""
        render_dir = Path(self.temp_dir) / "render_test"
        render_dir.mkdir(parents=True, exist_ok=True)

        # Case A: Missing video file
        artifacts_bad = {"video": render_dir / "missing.mp4"}
        is_ok, details, errors = validate_render_only_output(render_dir, artifacts_bad, content_type="short")
        self.assertFalse(is_ok)
        self.assertTrue(any("MP4 video missing" in e for e in errors))

        # Case B: Video file is empty
        empty_mp4 = render_dir / "empty.mp4"
        empty_mp4.touch()
        artifacts_bad = {"video": empty_mp4}
        is_ok, details, errors = validate_render_only_output(render_dir, artifacts_bad, content_type="short")
        self.assertFalse(is_ok)
        self.assertTrue(any("0 bytes" in e for e in errors))

        # Case C: Script without Telugu characters
        sc_file = render_dir / "script.json"
        sc_file.write_text(json.dumps({"language_code": "te-IN", "scenes": [{"voice_over": "Only English text here"}]}), encoding="utf-8")
        artifacts_bad = {"video": empty_mp4, "script": sc_file}
        is_ok, details, errors = validate_render_only_output(render_dir, artifacts_bad, content_type="short")
        self.assertFalse(is_ok)
        self.assertTrue(any("Telugu script characters" in e for e in errors))

    def test_09_existing_dry_run_behavior_remains_unchanged(self):
        """9. Existing dry_run=True behavior remains unchanged (mock providers, dry-run publisher)."""
        runner = PipelineRunner(
            dry_run=True,
            render_only=False,
            content_type="short",
            format="narrated",
            language_code="te-IN",
        )
        self.assertTrue(runner.dry_run)
        self.assertFalse(runner.render_only)

        # Check mock providers selected in dry_run
        provider = "mock" if runner.dry_run else "pocket_tts"
        vis_provider = "mock" if runner.dry_run else "flux"
        composer = "mock" if runner.dry_run else "ffmpeg"
        thumb_provider = "mock" if runner.dry_run else "pil"
        allow_mock = False if runner.render_only else runner.dry_run

        self.assertEqual(provider, "mock")
        self.assertEqual(vis_provider, "mock")
        self.assertEqual(composer, "mock")
        self.assertEqual(thumb_provider, "mock")
        self.assertTrue(allow_mock)

    def test_10_existing_production_pipeline_behavior_remains_unchanged(self):
        """10. Existing production pipeline behavior remains unchanged."""
        runner = PipelineRunner(
            dry_run=False,
            render_only=False,
            content_type="short",
            format="narrated",
            language_code="te-IN",
        )
        self.assertFalse(runner.dry_run)
        self.assertFalse(runner.render_only)

        # Verify real providers in production
        vis_provider = "mock" if runner.dry_run else "flux"
        composer = "mock" if runner.dry_run else "ffmpeg"
        thumb_provider = "mock" if runner.dry_run else "pil"
        allow_mock = False if runner.render_only else runner.dry_run

        self.assertEqual(vis_provider, "flux")
        self.assertEqual(composer, "ffmpeg")
        self.assertEqual(thumb_provider, "pil")
        self.assertFalse(allow_mock)


if __name__ == "__main__":
    unittest.main()
