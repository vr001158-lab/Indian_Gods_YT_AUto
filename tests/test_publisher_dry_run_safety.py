# tests/test_publisher_dry_run_safety.py
# Independent Publisher Safety & Dry-Run Isolation Test Suite
# Verifies that dry-run mode can NEVER call YouTube APIs, publish, or schedule videos,
# and that QA approval never bypasses dry-run safeguards.

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

import run_publisher
from src.pipeline.orchestrator import PipelineRunner
from tests.test_publisher import _make_qa


class TestPublisherDryRunSafety(unittest.TestCase):
    """Negative and safety isolation tests for YouTube publishing dry-run."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.tmp = Path(self.td.name)
        self.qa_file, self.mp4 = _make_qa(self.tmp, approved=True, data_source="youtube_api", confidence="high")

    def tearDown(self):
        self.td.cleanup()

    # ── Test 1: Negative Guard - Dry-Run fails if real upload API is called ──
    def test_01_negative_test_fails_if_real_upload_invoked_during_dry_run(self):
        """
        Negative test: If any real YouTube upload function is invoked during dry-run,
        an AssertionError is raised and the test fails immediately.
        """
        def forbidden_upload(*args, **kwargs):
            raise AssertionError("CRITICAL VIOLATION: Real YouTube upload API was invoked during dry-run!")

        def forbidden_creds(*args, **kwargs):
            raise AssertionError("CRITICAL VIOLATION: OAuth credentials were retrieved during dry-run!")

        with patch("youtube_uploader.upload_to_youtube", side_effect=forbidden_upload), \
             patch("src.publisher.uploader.publish_video", side_effect=forbidden_upload), \
             patch("google_auth_config.get_google_credentials", side_effect=forbidden_creds):

            # Call run_publisher with --dry-run
            test_args = ["run_publisher.py", "--qa", str(self.qa_file), "--dry-run"]
            with patch.object(sys, "argv", test_args):
                exit_code = run_publisher.main()

            self.assertEqual(exit_code, 0)

    # ── Test 2: QA approval does not bypass dry-run ──────────────────────────
    def test_02_final_qa_approval_does_not_bypass_dry_run_restriction(self):
        """
        Even with a 100% approved QA result with valid production tags,
        dry-run restriction must strictly prevent upload.
        """
        qa_data = json.loads(self.qa_file.read_text(encoding="utf-8"))
        self.assertTrue(qa_data["approved_for_publishing"])
        self.assertTrue(qa_data["approval_metadata"]["approved_for_generation"])

        upload_mock = MagicMock()
        with patch("youtube_uploader.upload_to_youtube", upload_mock), \
             patch("src.publisher.uploader.publish_video", upload_mock):

            test_args = ["run_publisher.py", "--qa", str(self.qa_file), "--dry-run"]
            with patch.object(sys, "argv", test_args):
                exit_code = run_publisher.main()

            self.assertEqual(exit_code, 0)
            upload_mock.assert_not_called()

    # ── Test 3: PipelineRunner dry-run guarantees --dry-run CLI flag ────────
    def test_03_pipeline_runner_dry_run_enforces_dry_run_flag(self):
        """
        PipelineRunner initialized with dry_run=True must append --dry-run
        to the publisher CLI command line and never allow live execution.
        """
        runner = PipelineRunner(dry_run=True, language_code="te-IN")
        self.assertTrue(runner.dry_run)

        # Mock state to return the qa_file
        runner.state.set_output("qa_output", self.qa_file)

        with patch.object(runner, "_execute_cmd") as mock_exec:
            out_file = runner.run_publisher()
            mock_exec.assert_called_once()
            cmd_args = mock_exec.call_args[0][0]
            self.assertIn("--dry-run", cmd_args)
            self.assertEqual(Path(out_file), Path(self.qa_file))

    # ── Test 4: Production upload requires explicit non-dry-run and credentials
    def test_04_production_upload_requires_explicit_production_controls(self):
        """
        Without --dry-run, execution fails closed if production OAuth credentials
        or required YouTube environment variables are absent.
        """
        test_args = ["run_publisher.py", "--qa", str(self.qa_file)]
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(sys, "argv", test_args):
            # Should fail closed with return code 1 because credentials cannot be loaded
            exit_code = run_publisher.main()
            self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
