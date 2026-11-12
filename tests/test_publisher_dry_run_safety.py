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

    # ── Test 5: Dry-run mode succeeds with missing credentials ──────────────
    def test_05_dry_run_mode_with_missing_credentials(self):
        """
        Dry-run mode (--dry-run) must succeed and exit 0 even if credentials
        are completely absent from the environment and disk.
        """
        test_args = ["run_publisher.py", "--qa", str(self.qa_file), "--dry-run"]
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(sys, "argv", test_args), \
             patch("google_auth_config.get_google_credentials") as mock_creds:
            exit_code = run_publisher.main()
            self.assertEqual(exit_code, 0)
            mock_creds.assert_not_called()

    # ── Test 6: Production mode with no credentials fails closed ─────────────
    def test_06_production_mode_with_no_credentials(self):
        """
        Production mode with explicit authorization but missing credentials
        (no TOKEN_JSON and no token.json) must fail closed with exit code 1.
        """
        test_args = ["run_publisher.py", "--qa", str(self.qa_file)]
        with patch.dict(os.environ, {"YOUTUBE_PUBLISH_AUTHORIZED": "true"}, clear=True), \
             patch("pathlib.Path.exists", return_value=False), \
             patch.object(sys, "argv", test_args):
            exit_code = run_publisher.main()
            self.assertEqual(exit_code, 1)

    # ── Test 7: Production mode with incomplete/malformed credentials ────────
    def test_07_production_mode_with_incomplete_credentials(self):
        """
        Production mode with malformed, empty, non-object, missing fields, or
        insufficient scopes in TOKEN_JSON must fail closed with exit code 1.
        """
        test_args = ["run_publisher.py", "--qa", str(self.qa_file)]
        invalid_tokens = [
            "not-valid-json",
            "{}",
            "[]",
            '""',
            "12345",
            "{unquoted: key}",
            '{"random_field": "123"}',
            '{"token": "123"}',
            '{"client_id": "123"}',
            # Access-token-only (missing refresh_token)
            '{"token": "123", "client_id": "cid", "client_secret": "sec", "scopes": ["https://www.googleapis.com/auth/youtube.upload"]}',
            # Missing client_secret
            '{"refresh_token": "rt", "client_id": "cid", "scopes": ["https://www.googleapis.com/auth/youtube.upload"]}',
            # Missing client_id
            '{"refresh_token": "rt", "client_secret": "sec", "scopes": ["https://www.googleapis.com/auth/youtube.upload"]}',
            # Missing scopes
            '{"refresh_token": "rt", "client_id": "cid", "client_secret": "sec"}',
            # Empty scopes
            '{"refresh_token": "rt", "client_id": "cid", "client_secret": "sec", "scopes": []}',
            # Read-only scope only
            '{"refresh_token": "rt", "client_id": "cid", "client_secret": "sec", "scopes": ["https://www.googleapis.com/auth/youtube.readonly"]}',
        ]
        for bad_token in invalid_tokens:
            with self.subTest(bad_token=bad_token):
                with patch.dict(os.environ, {
                    "YOUTUBE_PUBLISH_AUTHORIZED": "true",
                    "TOKEN_JSON": bad_token,
                }, clear=True), patch.object(sys, "argv", test_args):
                    exit_code = run_publisher.main()
                    self.assertEqual(exit_code, 1)

    # ── Test 8: Explicit authorization but empty token file on disk ─────────
    def test_08_production_mode_with_explicit_authorization_but_missing_token_file(self):
        """
        If TOKEN_JSON is absent and token.json on disk is 0 bytes or malformed,
        production execution must fail closed with exit code 1.
        """
        test_args = ["run_publisher.py", "--qa", str(self.qa_file)]
        with patch.dict(os.environ, {"YOUTUBE_PUBLISH_AUTHORIZED": "true"}, clear=True), \
             patch("publisher.safety.Path") as mock_path_cls, \
             patch.object(sys, "argv", test_args):

            # Create mock path object for token.json that reports exists=True, st_size=0
            mock_p = MagicMock()
            mock_p.exists.return_value = True
            mock_p.stat.return_value.st_size = 0
            mock_path_cls.return_value = mock_p

            exit_code = run_publisher.main()
            self.assertEqual(exit_code, 1)

    # ── Test 9: Production mode with complete valid configuration ────────────
    def test_09_production_mode_with_complete_valid_configuration(self):
        """
        When explicit authorization and valid credentials are provided,
        production execution completes successfully (mocked upload API).
        """
        valid_token_json = json.dumps({
            "token": "mock_access_token_123",
            "refresh_token": "mock_refresh_token_456",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "mock_client_id.apps.googleusercontent.com",
            "client_secret": "mock_secret",
            "scopes": ["https://www.googleapis.com/auth/youtube.upload"],
        })

        mock_creds = MagicMock()
        mock_creds.expired = False
        mock_creds.valid = True

        test_args = [
            "run_publisher.py",
            "--qa", str(self.qa_file),
            "--output-dir", str(self.tmp / "publishing"),
        ]

        with patch.dict(os.environ, {
            "YOUTUBE_PUBLISH_AUTHORIZED": "true",
            "TOKEN_JSON": valid_token_json,
        }, clear=True), \
             patch("google_auth_config.get_google_credentials", return_value=mock_creds), \
             patch("youtube_uploader.upload_to_youtube", return_value="PROD_TEST_VID_777"), \
             patch("src.publisher.uploader.upload_thumbnail", return_value=True), \
             patch.object(sys, "argv", test_args):

            exit_code = run_publisher.main()
            self.assertEqual(exit_code, 0)

            # Verify manifest was generated
            manifests = list((self.tmp / "publishing").glob("publish_*.json"))
            self.assertEqual(len(manifests), 1)
            mdata = json.loads(manifests[0].read_text(encoding="utf-8"))
            self.assertEqual(mdata["video_id"], "PROD_TEST_VID_777")
            self.assertTrue(mdata["success"])

    # ── Test 10: Invalid or empty production authorization values ───────────
    def test_10_invalid_or_empty_production_authorization_values(self):
        """
        Any authorization value other than 'true', '1', or 'yes'
        (e.g., 'false', '0', 'no', '', or random text) must fail closed with exit code 1.
        """
        test_args = ["run_publisher.py", "--qa", str(self.qa_file)]
        valid_token = json.dumps({
            "token": "mock_access_token",
            "refresh_token": "mock_refresh_token",
            "client_id": "mock_client_id.apps.googleusercontent.com",
            "client_secret": "mock_client_secret",
            "scopes": ["https://www.googleapis.com/auth/youtube.upload"],
        })

        invalid_auth_values = [
            "",
            "false",
            "0",
            "no",
            "off",
            "disabled",
            "invalid_token",
            "None",
        ]
        for auth_val in invalid_auth_values:
            with self.subTest(auth_val=auth_val):
                with patch.dict(os.environ, {
                    "YOUTUBE_PUBLISH_AUTHORIZED": auth_val,
                    "TOKEN_JSON": valid_token,
                }, clear=True), patch.object(sys, "argv", test_args):
                    exit_code = run_publisher.main()
                    self.assertEqual(exit_code, 1)

    # ── Test 11: Unexpected publisher exceptions cause fail-closed exit 1 ───
    def test_11_unexpected_publisher_exceptions_cause_fail_closed_exit_1(self):
        """
        Unexpected runtime exceptions during credential resolution or upload
        must propagate fail-closed exit code 1 without leaking secrets.
        """
        test_args = ["run_publisher.py", "--qa", str(self.qa_file)]
        valid_token = json.dumps({
            "token": "mock_access_token",
            "refresh_token": "mock_refresh_token",
            "client_id": "mock_client_id.apps.googleusercontent.com",
            "client_secret": "mock_client_secret",
            "scopes": ["https://www.googleapis.com/auth/youtube.upload"],
        })

        # Case A: Credential resolution failure
        with patch.dict(os.environ, {
            "YOUTUBE_PUBLISH_AUTHORIZED": "true",
            "TOKEN_JSON": valid_token,
        }, clear=True), \
             patch("google_auth_config.get_google_credentials", side_effect=RuntimeError("Auth backend timeout")), \
             patch.object(sys, "argv", test_args):
            exit_code = run_publisher.main()
            self.assertEqual(exit_code, 1)

        # Case B: Upload failure in publish_video
        mock_creds = MagicMock()
        mock_creds.expired = False
        with patch.dict(os.environ, {
            "YOUTUBE_PUBLISH_AUTHORIZED": "true",
            "TOKEN_JSON": valid_token,
        }, clear=True), \
             patch("google_auth_config.get_google_credentials", return_value=mock_creds), \
             patch("src.publisher.uploader.publish_video", side_effect=RuntimeError("Network broken pipe")), \
             patch.object(sys, "argv", test_args):
            exit_code = run_publisher.main()
            self.assertEqual(exit_code, 1)

    # ── Test 12: Environment isolation between tests ────────────────────────
    def test_12_environment_isolation_between_tests(self):
        """
        Verify that environment variable state remains strictly isolated across tests.
        """
        # Ensure that no prior test leaked production authorization into os.environ
        self.assertNotIn("YOUTUBE_PUBLISH_AUTHORIZED", os.environ)

        # Run with isolated un-authorized environment
        test_args = ["run_publisher.py", "--qa", str(self.qa_file)]
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(sys, "argv", test_args):
            exit_code = run_publisher.main()
            self.assertEqual(exit_code, 1)

    # ── Test 13: Reject access-token-only credentials ───────────────────────
    def test_13_production_mode_rejects_access_token_only_credentials(self):
        """
        Credentials possessing only an access token ('token') without 'refresh_token'
        cannot support automated token refresh and must fail closed with exit code 1.
        """
        test_args = ["run_publisher.py", "--qa", str(self.qa_file)]
        access_token_only = json.dumps({
            "token": "ya29.mock_access_token_without_refresh",
            "client_id": "mock_client_id.apps.googleusercontent.com",
            "client_secret": "mock_secret",
            "scopes": ["https://www.googleapis.com/auth/youtube.upload"],
        })
        with patch.dict(os.environ, {
            "YOUTUBE_PUBLISH_AUTHORIZED": "true",
            "TOKEN_JSON": access_token_only,
        }, clear=True), patch.object(sys, "argv", test_args):
            exit_code = run_publisher.main()
            self.assertEqual(exit_code, 1)

    # ── Test 14: Reject missing or empty scopes metadata ────────────────────
    def test_14_production_mode_rejects_missing_or_empty_scopes_metadata(self):
        """
        Credentials missing 'scopes' metadata entirely or providing an empty list
        must fail closed with exit code 1.
        """
        test_args = ["run_publisher.py", "--qa", str(self.qa_file)]
        tokens_without_valid_scopes = [
            # Missing scopes key entirely
            json.dumps({
                "refresh_token": "mock_refresh_token",
                "client_id": "mock_client_id",
                "client_secret": "mock_secret",
            }),
            # Empty scopes list
            json.dumps({
                "refresh_token": "mock_refresh_token",
                "client_id": "mock_client_id",
                "client_secret": "mock_secret",
                "scopes": [],
            }),
            # Scopes missing required upload scope
            json.dumps({
                "refresh_token": "mock_refresh_token",
                "client_id": "mock_client_id",
                "client_secret": "mock_secret",
                "scopes": ["https://www.googleapis.com/auth/youtube.readonly"],
            }),
        ]
        for bad_token in tokens_without_valid_scopes:
            with self.subTest(bad_token=bad_token):
                with patch.dict(os.environ, {
                    "YOUTUBE_PUBLISH_AUTHORIZED": "true",
                    "TOKEN_JSON": bad_token,
                }, clear=True), patch.object(sys, "argv", test_args):
                    exit_code = run_publisher.main()
                    self.assertEqual(exit_code, 1)

    # ── Test 15: Reject missing client_id or client_secret ──────────────────
    def test_15_production_mode_rejects_missing_client_credentials(self):
        """
        OAuth authorized user dictionaries missing 'client_id' or 'client_secret'
        must fail closed with exit code 1.
        """
        test_args = ["run_publisher.py", "--qa", str(self.qa_file)]
        incomplete_tokens = [
            # Missing client_id
            json.dumps({
                "refresh_token": "mock_refresh_token",
                "client_secret": "mock_secret",
                "scopes": ["https://www.googleapis.com/auth/youtube.upload"],
            }),
            # Missing client_secret
            json.dumps({
                "refresh_token": "mock_refresh_token",
                "client_id": "mock_client_id",
                "scopes": ["https://www.googleapis.com/auth/youtube.upload"],
            }),
        ]
        for bad_token in incomplete_tokens:
            with self.subTest(bad_token=bad_token):
                with patch.dict(os.environ, {
                    "YOUTUBE_PUBLISH_AUTHORIZED": "true",
                    "TOKEN_JSON": bad_token,
                }, clear=True), patch.object(sys, "argv", test_args):
                    exit_code = run_publisher.main()
                    self.assertEqual(exit_code, 1)

    # ── Test 16: Google auth config library validation ───────────────────────
    def test_16_google_auth_config_enforces_structure_and_scopes(self):
        """
        Direct test of google_auth_config.get_google_credentials():
        Asserts ValueError is raised on missing refresh_token, missing scopes,
        missing client info, or insufficient scopes.
        """
        import google_auth_config

        # Case 1: Missing refresh_token
        with patch.dict(os.environ, {
            "TOKEN_JSON": json.dumps({
                "token": "tok",
                "client_id": "cid",
                "client_secret": "sec",
                "scopes": ["https://www.googleapis.com/auth/youtube.upload"],
            })
        }, clear=True), patch("pathlib.Path.exists", return_value=False):
            with self.assertRaises(ValueError) as ctx:
                google_auth_config.get_google_credentials(token_file=Path("nonexistent.json"))
            self.assertIn("refresh_token", str(ctx.exception))

        # Case 2: Missing scopes
        with patch.dict(os.environ, {
            "TOKEN_JSON": json.dumps({
                "refresh_token": "rt",
                "client_id": "cid",
                "client_secret": "sec",
            })
        }, clear=True), patch("pathlib.Path.exists", return_value=False):
            with self.assertRaises(ValueError) as ctx:
                google_auth_config.get_google_credentials(token_file=Path("nonexistent.json"))
            self.assertIn("scopes", str(ctx.exception).lower())

        # Case 3: Insufficient scopes
        with patch.dict(os.environ, {
            "TOKEN_JSON": json.dumps({
                "refresh_token": "rt",
                "client_id": "cid",
                "client_secret": "sec",
                "scopes": ["https://www.googleapis.com/auth/youtube.readonly"],
            })
        }, clear=True), patch("pathlib.Path.exists", return_value=False):
            with self.assertRaises(ValueError) as ctx:
                google_auth_config.get_google_credentials(token_file=Path("nonexistent.json"))
            self.assertIn("OAUTH SCOPE ERROR", str(ctx.exception))

    # ── Test 17: Expired credentials handling in google_auth_config ──────────
    def test_17_google_auth_config_handles_expired_token_safely(self):
        """
        Verify that expired credentials raise ValueError when refresh fails,
        and never leak raw secret values in exceptions.
        """
        import google_auth_config

        valid_raw = json.dumps({
            "token": "expired_access_token_secret_123",
            "refresh_token": "refresh_token_secret_456",
            "client_id": "client_id_secret_789.apps.googleusercontent.com",
            "client_secret": "client_secret_secret_abc",
            "scopes": ["https://www.googleapis.com/auth/youtube.upload"],
        })

        mock_creds = MagicMock()
        mock_creds.expired = True
        mock_creds.refresh_token = "refresh_token_secret_456"
        mock_creds.refresh.side_effect = RuntimeError("Failed to resolve oauth2.googleapis.com")

        with patch.dict(os.environ, {"TOKEN_JSON": valid_raw}, clear=True), \
             patch("pathlib.Path.exists", return_value=False), \
             patch("google.oauth2.credentials.Credentials.from_authorized_user_info", return_value=mock_creds):
            with self.assertRaises(ValueError) as ctx:
                google_auth_config.get_google_credentials(token_file=Path("nonexistent.json"))
            err_msg = str(ctx.exception)
            self.assertIn("Failed to refresh expired token", err_msg)
            # Secrets must never appear in the error message
            self.assertNotIn("expired_access_token_secret_123", err_msg)
            self.assertNotIn("client_secret_secret_abc", err_msg)

    # ── Test 18: Expired credentials refresh failure causes fail-closed exit 1
    def test_18_production_mode_fails_closed_on_expired_token_refresh_error(self):
        """
        In production mode, if the token is expired and fails to refresh at upload time,
        run_publisher.py must fail closed with exit code 1.
        """
        test_args = ["run_publisher.py", "--qa", str(self.qa_file)]
        valid_token = json.dumps({
            "token": "mock_access_token",
            "refresh_token": "mock_refresh_token",
            "client_id": "mock_client_id.apps.googleusercontent.com",
            "client_secret": "mock_client_secret",
            "scopes": ["https://www.googleapis.com/auth/youtube.upload"],
        })

        with patch.dict(os.environ, {
            "YOUTUBE_PUBLISH_AUTHORIZED": "true",
            "TOKEN_JSON": valid_token,
        }, clear=True), \
             patch("google_auth_config.get_google_credentials", side_effect=ValueError("Failed to refresh expired token")), \
             patch.object(sys, "argv", test_args):
            exit_code = run_publisher.main()
            self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
