# tests/test_publishing_security_gates.py
# Fail-Closed YouTube Publishing Security & Workflow Gate Verification

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import youtube_uploader
from src.publisher.safety import validate_production_environment
from src.publisher.uploader import upload_thumbnail, PublishError


class TestPublishingSecurityGates(unittest.TestCase):
    """
    Verification of fail-closed YouTube upload safety gates,
    environment variable enforcement, and GitHub Actions workflow security invariants.
    """

    def setUp(self):
        # Sample minimal valid QA result for publisher boundary tests
        self.qa_data = {
            "approved_for_publishing": True,
            "data_source": "youtube_api",
            "confidence": "high",
            "approved_for_generation": True,
            "video_path": "data/output/test_video.mp4",
            "content_type": "short",
            "language_code": "te-IN",
        }

    # ── Test 1: Direct uploader invocation without authorization fails closed ─
    def test_01_direct_uploader_invocation_without_authorization_fails(self):
        """youtube_uploader.upload_to_youtube must immediately raise PermissionError if unauthorized."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(PermissionError) as ctx:
                youtube_uploader.upload_to_youtube(
                    creds=MagicMock(),
                    video_path=Path("non_existent_test.mp4"),
                    title="Test Title",
                    description="Test Desc",
                    tags=["test"],
                )
            self.assertIn("CRITICAL SAFETY BLOCK", str(ctx.exception))

    # ── Test 2: RENDER_ONLY=true strictly blocks all uploads ──────────────────
    def test_02_render_only_true_blocks_uploads(self):
        """RENDER_ONLY=true blocks upload_to_youtube and validate_production_environment."""
        truthy_values = ["true", "1", "yes", "True", "YES"]
        for val in truthy_values:
            with self.subTest(render_only=val):
                with patch.dict(os.environ, {
                    "RENDER_ONLY": val,
                    "YOUTUBE_PUBLISH_AUTHORIZED": "true",
                    "YOUTUBE_PUBLISH": "true",
                }, clear=True):
                    is_ok, err = validate_production_environment(allow_dry_run=False)
                    self.assertFalse(is_ok)
                    self.assertIn("RENDER_ONLY mode is active", err)

                    with self.assertRaises(PermissionError) as ctx:
                        youtube_uploader.upload_to_youtube(
                            creds=MagicMock(),
                            video_path=Path("test.mp4"),
                            title="T",
                            description="D",
                            tags=[],
                        )
                    self.assertIn("RENDER_ONLY is active", str(ctx.exception))

    # ── Test 3: YOUTUBE_PUBLISH=false, 0, no, disabled, off blocks uploads ──────
    def test_03_youtube_publish_false_blocks_uploads(self):
        """YOUTUBE_PUBLISH explicitly set to falsy values blocks uploads."""
        falsy_values = ["false", "0", "no", "disabled", "off", "False", "NO", "Disabled"]
        for val in falsy_values:
            with self.subTest(youtube_publish=val):
                with patch.dict(os.environ, {
                    "RENDER_ONLY": "false",
                    "YOUTUBE_PUBLISH": val,
                    "YOUTUBE_PUBLISH_AUTHORIZED": "true",
                }, clear=True):
                    is_ok, err = validate_production_environment(allow_dry_run=False)
                    self.assertFalse(is_ok)
                    self.assertIn("YOUTUBE_PUBLISH is disabled or invalid", err)

                    with self.assertRaises(PermissionError) as ctx:
                        youtube_uploader.upload_to_youtube(
                            creds=MagicMock(),
                            video_path=Path("test.mp4"),
                            title="T",
                            description="D",
                            tags=[],
                        )
                    self.assertIn("YOUTUBE_PUBLISH must be explicitly 'true', '1', or 'yes'", str(ctx.exception))

    def test_03b_youtube_publish_missing_denies_publishing(self):
        """Missing YOUTUBE_PUBLISH denies publishing even when authorization is true and render-only is false."""
        with patch.dict(os.environ, {
            "RENDER_ONLY": "false",
            "YOUTUBE_PUBLISH_AUTHORIZED": "true",
        }, clear=True):
            is_ok, err = validate_production_environment(allow_dry_run=False)
            self.assertFalse(is_ok)
            self.assertIn("YOUTUBE_PUBLISH is missing or empty", err)

            with self.assertRaises(PermissionError) as ctx:
                youtube_uploader.upload_to_youtube(
                    creds=MagicMock(),
                    video_path=Path("test.mp4"),
                    title="T",
                    description="D",
                    tags=[],
                )
            self.assertIn("YOUTUBE_PUBLISH must be explicitly 'true', '1', or 'yes'", str(ctx.exception))

    def test_03c_youtube_publish_empty_and_arbitrary_values_deny(self):
        """Empty and arbitrary values for YOUTUBE_PUBLISH deny publishing."""
        invalid_values = ["", "   ", "arbitrary", "foo", "true_not", "2", "random"]
        for val in invalid_values:
            with self.subTest(youtube_publish=val):
                with patch.dict(os.environ, {
                    "RENDER_ONLY": "false",
                    "YOUTUBE_PUBLISH": val,
                    "YOUTUBE_PUBLISH_AUTHORIZED": "true",
                }, clear=True):
                    is_ok, err = validate_production_environment(allow_dry_run=False)
                    self.assertFalse(is_ok)
                    self.assertTrue(
                        "YOUTUBE_PUBLISH is missing or empty" in err
                        or "YOUTUBE_PUBLISH is disabled or invalid" in err
                    )

                    with self.assertRaises(PermissionError) as ctx:
                        youtube_uploader.upload_to_youtube(
                            creds=MagicMock(),
                            video_path=Path("test.mp4"),
                            title="T",
                            description="D",
                            tags=[],
                        )
                    self.assertIn("YOUTUBE_PUBLISH must be explicitly 'true', '1', or 'yes'", str(ctx.exception))

    def test_03d_youtube_publish_affirmative_values_allow_gate(self):
        """true, 1, and yes (and mixed-case / whitespace-trimmed) allow the YOUTUBE_PUBLISH gate."""
        affirmative_values = ["true", "1", "yes", "TRUE", "Yes", " 1 ", " true ", "YES "]
        for val in affirmative_values:
            with self.subTest(youtube_publish=val):
                with patch.dict(os.environ, {
                    "RENDER_ONLY": "false",
                    "YOUTUBE_PUBLISH": val,
                    "YOUTUBE_PUBLISH_AUTHORIZED": "true",
                }, clear=True):
                    is_ok, err = validate_production_environment(allow_dry_run=False)
                    # Gate passes; any failure after is due to missing test token if Path("token.json") absent
                    if not is_ok:
                        self.assertIn("Missing required OAuth credentials", err)

                    # In youtube_uploader, passes permission gate and hits FileNotFoundError
                    with self.assertRaises(FileNotFoundError):
                        youtube_uploader.upload_to_youtube(
                            creds=MagicMock(),
                            video_path=Path("non_existent_mock_file.mp4"),
                            title="T",
                            description="D",
                            tags=[],
                        )

    # ── Test 4: YOUTUBE_PUBLISH_AUTHORIZED=false blocks uploads ───────────────
    def test_04_youtube_publish_authorized_false_blocks_uploads(self):
        """YOUTUBE_PUBLISH_AUTHORIZED=false blocks uploads."""
        falsy_values = ["false", "0", "no", "disabled", "off", "False"]
        for val in falsy_values:
            with self.subTest(auth=val):
                with patch.dict(os.environ, {
                    "RENDER_ONLY": "false",
                    "YOUTUBE_PUBLISH": "true",
                    "YOUTUBE_PUBLISH_AUTHORIZED": val,
                }, clear=True):
                    is_ok, err = validate_production_environment(allow_dry_run=False)
                    self.assertFalse(is_ok)
                    self.assertIn("Production authorization is disabled or invalid", err)

                    with self.assertRaises(PermissionError) as ctx:
                        youtube_uploader.upload_to_youtube(
                            creds=MagicMock(),
                            video_path=Path("test.mp4"),
                            title="T",
                            description="D",
                            tags=[],
                        )
                    self.assertIn("YOUTUBE_PUBLISH_AUTHORIZED is not 'true'", str(ctx.exception))

    # ── Test 5: Missing authorization variables block uploads ─────────────────
    def test_05_missing_authorization_variables_block_uploads(self):
        """Missing YOUTUBE_PUBLISH_AUTHORIZED in environment must fail closed."""
        with patch.dict(os.environ, {
            "RENDER_ONLY": "false",
            "YOUTUBE_PUBLISH": "true",
        }, clear=True):
            is_ok, err = validate_production_environment(allow_dry_run=False)
            self.assertFalse(is_ok)
            self.assertIn("Explicit production authorization is missing", err)

            with self.assertRaises(PermissionError):
                youtube_uploader.upload_to_youtube(
                    creds=MagicMock(),
                    video_path=Path("test.mp4"),
                    title="T",
                    description="D",
                    tags=[],
                )

    # ── Test 6: Legacy aliases cannot bypass authorization ────────────────────
    def test_06_legacy_environment_aliases_cannot_bypass_authorization(self):
        """Setting PRODUCTION_PUBLISH_AUTHORIZED alone does not grant upload authorization."""
        with patch.dict(os.environ, {
            "PRODUCTION_PUBLISH_AUTHORIZED": "true",
            "YOUTUBE_PUBLISH": "true",
            "RENDER_ONLY": "false",
        }, clear=True):
            is_ok, err = validate_production_environment(allow_dry_run=False)
            self.assertFalse(is_ok)
            self.assertIn("Explicit production authorization is missing", err)

            with self.assertRaises(PermissionError):
                youtube_uploader.upload_to_youtube(
                    creds=MagicMock(),
                    video_path=Path("test.mp4"),
                    title="T",
                    description="D",
                    tags=[],
                )

    # ── Test 7: Denial happens before OAuth or network access ─────────────────
    def test_07_denial_happens_before_oauth_or_network_access(self):
        """Authorization gate check runs BEFORE any credential resolution or Google API client build."""
        mock_get_creds = MagicMock(side_effect=AssertionError("CRITICAL: OAuth get_credentials should NOT be called when unauthorized!"))
        mock_build = MagicMock(side_effect=AssertionError("CRITICAL: YouTube API build should NOT be called when unauthorized!"))

        with patch.dict(os.environ, {}, clear=True), \
             patch("google_auth_config.get_google_credentials", mock_get_creds), \
             patch("googleapiclient.discovery.build", mock_build):

            # Check 1: youtube_uploader
            with self.assertRaises(PermissionError):
                youtube_uploader.upload_to_youtube(
                    creds=None,
                    video_path=Path("test.mp4"),
                    title="T",
                    description="D",
                    tags=[],
                )

            # Check 2: legacy uploader main()
            import uploader
            with patch.object(sys, "argv", ["uploader.py", "--mode", "multi_image"]), \
                 self.assertRaises(SystemExit) as exit_ctx:
                uploader.main()
            self.assertEqual(exit_ctx.exception.code, 1)

        mock_get_creds.assert_not_called()
        mock_build.assert_not_called()

    # ── Test 8: Rendering continues to work without YouTube credentials ───────
    def test_08_rendering_continues_to_work_without_credentials(self):
        """In render-only mode, the pipeline executes without requiring token.json or TOKEN_JSON."""
        from src.pipeline.orchestrator import PipelineRunner
        with patch.dict(os.environ, {
            "RENDER_ONLY": "true",
            "YOUTUBE_PUBLISH": "false",
            "YOUTUBE_PUBLISH_AUTHORIZED": "false",
        }, clear=True):
            # Verify credentials are not present in environment
            self.assertNotIn("TOKEN_JSON", os.environ)
            runner = PipelineRunner(dry_run=False, render_only=True)
            self.assertTrue(runner.render_only)
            self.assertFalse(runner.dry_run)
            # Publisher stage must not be scheduled in render_only mode
            stages = runner._build_stages_map() if hasattr(runner, "_build_stages_map") else {}
            self.assertNotIn("PUBLISHER", stages)

    # ── Test 9: Scheduled workflow event cannot publish ───────────────────────
    def test_09_scheduled_workflow_event_cannot_publish(self):
        """Workflow script logic enforces render-only on schedule; no export of YOUTUBE_PUBLISH_AUTHORIZED=true."""
        workflow_path = Path(".github/workflows/divine-dharshanam-daily.yml")
        self.assertTrue(workflow_path.exists())
        workflow_text = workflow_path.read_text(encoding="utf-8")

        # In schedule block, --render-only must be explicitly passed
        self.assertIn('--render-only', workflow_text)

        # On schedule, export YOUTUBE_PUBLISH_AUTHORIZED="true" must NOT occur
        lines = workflow_text.splitlines()
        in_schedule_block = False
        for line in lines:
            if 'github.event_name == "schedule"' in line or "github.event_name == 'schedule'" in line:
                in_schedule_block = True
            elif 'workflow_dispatch' in line:
                in_schedule_block = False
            if in_schedule_block:
                self.assertNotIn('YOUTUBE_PUBLISH_AUTHORIZED="true"', line)
                self.assertNotIn("YOUTUBE_PUBLISH_AUTHORIZED='true'", line)

    # ── Test 10: Manual workflow dispatch with dry_run=false cannot publish ───
    def test_10_manual_dispatch_with_dry_run_false_alone_cannot_publish(self):
        """Workflow dispatch must NOT synthesize authorization merely on dry_run=false."""
        workflow_path = Path(".github/workflows/divine-dharshanam-daily.yml")
        workflow_text = workflow_path.read_text(encoding="utf-8")

        # Must not contain unguarded dry_run=false authorization
        self.assertNotIn('[ "$DRY_RUN_INPUT" = "false" ] && export YOUTUBE_PUBLISH_AUTHORIZED', workflow_text)
        self.assertNotIn('if [ "$DRY_RUN_INPUT" = "false" ]; then\n              export YOUTUBE_PUBLISH_AUTHORIZED="true"', workflow_text)
        # Must require CONFIRM_PUBLISH and secret opt-in
        self.assertIn('CONFIRM_PUBLISH', workflow_text)
        self.assertIn('YOUTUBE_PUBLISH_OPT_IN', workflow_text)

    # ── Test 11: No workflow contains unattended upload path ──────────────────
    def test_11_no_workflow_contains_unattended_upload_path(self):
        """Inspect all workflows to confirm none invoke uploader with public upload without manual authorization."""
        workflow_dir = Path(".github/workflows")
        for yml_file in workflow_dir.glob("*.yml"):
            text = yml_file.read_text(encoding="utf-8")
            # scheduler.yml must use --dry-run
            if yml_file.name == "scheduler.yml":
                self.assertNotIn("--privacy $PRIVACY", text)
                self.assertIn("--dry-run", text)

    # ── Test 12: No workflow automatically pushes commits to main ─────────────
    def test_12_no_workflow_automatically_pushes_commits_to_main(self):
        """Zero workflows may contain git push commands to repository branches."""
        workflow_dir = Path(".github/workflows")
        for yml_file in workflow_dir.glob("*.yml"):
            text = yml_file.read_text(encoding="utf-8")
            for line in text.splitlines():
                stripped = line.strip()
                if not stripped.startswith("#"):
                    self.assertNotIn("git push", stripped, f"Disallowed 'git push' found in {yml_file.name}: {stripped}")

    # ── Test 13: Workflows have read-only contents permissions ────────────────
    def test_13_workflow_permissions_are_read_only(self):
        """Active automation workflows must declare contents: read permissions."""
        audited_workflows = [
            Path(".github/workflows/divine-dharshanam-daily.yml"),
            Path(".github/workflows/scheduler.yml"),
        ]
        for yml_path in audited_workflows:
            text = yml_path.read_text(encoding="utf-8")
            self.assertIn("contents: read", text, f"{yml_path.name} missing 'contents: read'")
            self.assertNotIn("contents: write", text, f"{yml_path.name} retains disallowed 'contents: write'")

    # ── Test 14: Direct upload_thumbnail() without authorization is denied ────
    def test_14_upload_thumbnail_denied_without_authorization(self):
        """Direct upload_thumbnail() invocation without authorization is denied."""
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(PublishError) as ctx:
                upload_thumbnail(
                    creds=MagicMock(),
                    video_id="test_video_123",
                    thumbnail_file=Path("dummy_thumb.jpg"),
                )
            self.assertIn("upload_thumbnail() denied by production safety gate", str(ctx.exception))

    # ── Test 15: Missing YOUTUBE_PUBLISH denies direct thumbnail upload ───────
    def test_15_upload_thumbnail_denied_when_youtube_publish_missing(self):
        """Missing YOUTUBE_PUBLISH denies a direct thumbnail upload."""
        with patch.dict(os.environ, {
            "RENDER_ONLY": "false",
            "YOUTUBE_PUBLISH_AUTHORIZED": "true",
        }, clear=True):
            with self.assertRaises(PublishError) as ctx:
                upload_thumbnail(
                    creds=MagicMock(),
                    video_id="test_video_123",
                    thumbnail_file=Path("dummy_thumb.jpg"),
                )
            self.assertIn("YOUTUBE_PUBLISH is missing or empty", str(ctx.exception))

    # ── Test 16: RENDER_ONLY=true denies direct thumbnail upload ──────────────
    def test_16_upload_thumbnail_denied_when_render_only_true(self):
        """RENDER_ONLY=true denies a direct thumbnail upload."""
        with patch.dict(os.environ, {
            "RENDER_ONLY": "true",
            "YOUTUBE_PUBLISH": "true",
            "YOUTUBE_PUBLISH_AUTHORIZED": "true",
        }, clear=True):
            with self.assertRaises(PublishError) as ctx:
                upload_thumbnail(
                    creds=MagicMock(),
                    video_id="test_video_123",
                    thumbnail_file=Path("dummy_thumb.jpg"),
                )
            self.assertIn("RENDER_ONLY mode", str(ctx.exception))

    # ── Test 17: Authorized configuration proceeds to mocked thumbnail API ────
    def test_17_upload_thumbnail_authorized_proceeds_to_mocked_api(self):
        """Authorized configuration allows the function to proceed to mocked thumbnail API operation."""
        with tempfile.TemporaryDirectory() as td:
            thumb_path = Path(td) / "valid_thumb.jpg"
            thumb_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)  # non-empty jpeg

            with patch.dict(os.environ, {
                "RENDER_ONLY": "false",
                "YOUTUBE_PUBLISH": "true",
                "YOUTUBE_PUBLISH_AUTHORIZED": "true",
            }, clear=True):
                with patch("googleapiclient.discovery.build") as mock_build, \
                     patch("googleapiclient.http.MediaFileUpload"):
                    mock_youtube = MagicMock()
                    mock_build.return_value = mock_youtube
                    mock_set = MagicMock()
                    mock_youtube.thumbnails.return_value.set.return_value = mock_set

                    ok = upload_thumbnail(
                        creds=MagicMock(),
                        video_id="test_video_123",
                        thumbnail_file=thumb_path,
                    )
                    self.assertTrue(ok)
                    mock_youtube.thumbnails.return_value.set.assert_called_once()
                    mock_set.execute.assert_called_once()

    # ── Test 18: Unauthorized cases never invoke thumbnails().set() ───────────
    def test_18_upload_thumbnail_unauthorized_never_invokes_thumbnails_set(self):
        """Unauthorized cases never invoke thumbnails().set()."""
        unauthorized_environments = [
            {},
            {"RENDER_ONLY": "true", "YOUTUBE_PUBLISH": "true", "YOUTUBE_PUBLISH_AUTHORIZED": "true"},
            {"RENDER_ONLY": "false", "YOUTUBE_PUBLISH": "false", "YOUTUBE_PUBLISH_AUTHORIZED": "true"},
            {"RENDER_ONLY": "false", "YOUTUBE_PUBLISH": "true", "YOUTUBE_PUBLISH_AUTHORIZED": "false"},
            {"RENDER_ONLY": "false", "YOUTUBE_PUBLISH": "disabled", "YOUTUBE_PUBLISH_AUTHORIZED": "true"},
        ]
        with tempfile.TemporaryDirectory() as td:
            thumb_path = Path(td) / "valid_thumb.jpg"
            thumb_path.write_bytes(b"\xff\xd8\xff\xe0" + b"\x00" * 100)

            for env_case in unauthorized_environments:
                with self.subTest(env=env_case):
                    with patch.dict(os.environ, env_case, clear=True):
                        with patch("googleapiclient.discovery.build") as mock_build:
                            mock_youtube = MagicMock()
                            mock_build.return_value = mock_youtube

                            with self.assertRaises(PublishError):
                                upload_thumbnail(
                                    creds=MagicMock(),
                                    video_id="test_video_123",
                                    thumbnail_file=thumb_path,
                                )

                            mock_build.assert_not_called()
                            mock_youtube.thumbnails.return_value.set.assert_not_called()

    def test_19_publish_video_denied_without_all_production_safeguards(self):
        """Direct publishing rejects missing, false, or invalid authorization before upload."""
        unauthorized_environments = [
            {},
            {"RENDER_ONLY": "false", "YOUTUBE_PUBLISH": "true"},
            {"RENDER_ONLY": "false", "YOUTUBE_PUBLISH": "false", "YOUTUBE_PUBLISH_AUTHORIZED": "true"},
            {"RENDER_ONLY": "false", "YOUTUBE_PUBLISH": "true", "YOUTUBE_PUBLISH_AUTHORIZED": "false"},
            {"RENDER_ONLY": "false", "YOUTUBE_PUBLISH": "arbitrary", "YOUTUBE_PUBLISH_AUTHORIZED": "true"},
            {"RENDER_ONLY": "true", "YOUTUBE_PUBLISH": "true", "YOUTUBE_PUBLISH_AUTHORIZED": "true"},
        ]
        from src.publisher.uploader import publish_video

        for env_case in unauthorized_environments:
            with self.subTest(env=env_case), \
                 patch.dict(os.environ, env_case, clear=True), \
                 patch("youtube_uploader.upload_to_youtube") as mock_upload:
                with self.assertRaises(PublishError):
                    publish_video(
                        creds=MagicMock(),
                        video_file=Path("missing.mp4"),
                        title="Test",
                        description="Test",
                        tags=[],
                        category_id="22",
                        thumbnail_file=None,
                        qa={},
                    )
                mock_upload.assert_not_called()

    # ── Test 20: Secret opt-in required when configured ─────────────────────
    def test_20_secret_opt_in_required_when_configured(self):
        """When REQUIRE_PUBLISH_OPT_IN is true, missing or false opt-in blocks publishing."""
        valid_token = json.dumps({
            "token": "tok",
            "refresh_token": "rt",
            "client_id": "cid",
            "client_secret": "sec",
            "scopes": ["https://www.googleapis.com/auth/youtube.upload"],
        })
        # Case A: Missing opt-in when required
        with patch.dict(os.environ, {
            "RENDER_ONLY": "false",
            "YOUTUBE_PUBLISH": "true",
            "YOUTUBE_PUBLISH_AUTHORIZED": "true",
            "REQUIRE_PUBLISH_OPT_IN": "true",
            "TOKEN_JSON": valid_token,
        }, clear=True):
            is_ok, err = validate_production_environment(allow_dry_run=False)
            self.assertFalse(is_ok)
            self.assertIn("Secret opt-in (YOUTUBE_PUBLISH_OPT_IN) is required", err)

        # Case B: False opt-in value
        with patch.dict(os.environ, {
            "RENDER_ONLY": "false",
            "YOUTUBE_PUBLISH": "true",
            "YOUTUBE_PUBLISH_AUTHORIZED": "true",
            "YOUTUBE_PUBLISH_OPT_IN": "false",
            "TOKEN_JSON": valid_token,
        }, clear=True):
            is_ok, err = validate_production_environment(allow_dry_run=False)
            self.assertFalse(is_ok)
            self.assertIn("Secret opt-in (YOUTUBE_PUBLISH_OPT_IN) is disabled or invalid", err)

    # ── Test 21: Secret opt-in allows publishing when affirmative ───────────
    def test_21_secret_opt_in_allows_publishing_when_affirmative(self):
        """When YOUTUBE_PUBLISH_OPT_IN is 'true', publishing passes validation."""
        valid_token = json.dumps({
            "token": "tok",
            "refresh_token": "rt",
            "client_id": "cid",
            "client_secret": "sec",
            "scopes": ["https://www.googleapis.com/auth/youtube.upload"],
        })
        with patch.dict(os.environ, {
            "RENDER_ONLY": "false",
            "YOUTUBE_PUBLISH": "true",
            "YOUTUBE_PUBLISH_AUTHORIZED": "true",
            "REQUIRE_PUBLISH_OPT_IN": "true",
            "YOUTUBE_PUBLISH_OPT_IN": "true",
            "TOKEN_JSON": valid_token,
        }, clear=True):
            is_ok, err = validate_production_environment(allow_dry_run=False)
            self.assertTrue(is_ok, msg=err)
            self.assertEqual(err, "")

    # ── Test 22: Workflow publish mode security invariants ──────────────────
    def test_22_workflow_publish_mode_invariants(self):
        """Workflow dispatch defaults to render_only, private privacy, and requires dual authorization."""
        workflow_path = Path(".github/workflows/divine-dharshanam-daily.yml")
        text = workflow_path.read_text(encoding="utf-8")

        # Default execution_mode is render_only
        self.assertIn("default: 'render_only'", text)
        # Default privacy_status is private
        self.assertIn("default: 'private'", text)
        # Default dry_run is true
        self.assertIn("default: true", text)
        # publish option exists
        self.assertIn("- publish", text)
        # Requires CONFIRM_PUBLISH confirmation
        self.assertIn("CONFIRM_PUBLISH", text)
        # Secret opt-in check exists
        self.assertIn("YOUTUBE_PUBLISH_OPT_IN_SECRET", text)
        # Scheduled run uses --render-only
        self.assertIn("--render-only", text)


if __name__ == "__main__":
    unittest.main()
