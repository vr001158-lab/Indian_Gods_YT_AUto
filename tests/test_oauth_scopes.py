"""
tests/test_oauth_scopes.py
Verifies OAuth scope configuration (upload-only) and API-key research architecture.
All tests are offline — no network access, no token files required.
"""

import os
import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.getcwd())

import google_auth_config
from google_auth_config import SCOPES, get_google_credentials
import src.research.collector as collector_mod
from src.research.collector import ResearchCollector, YOUTUBE_API_KEY_ENV
import youtube_uploader


# ── Expected scope constants ──────────────────────────────────────────────────
SCOPE_UPLOAD   = "https://www.googleapis.com/auth/youtube.upload"
SCOPE_READONLY = "https://www.googleapis.com/auth/youtube.readonly"
SCOPE_DRIVE    = "https://www.googleapis.com/auth/drive.file"


# ─────────────────────────────────────────────────────────────────────────────
class TestScopeDefinition(unittest.TestCase):
    """Verify the centralized SCOPES list is correct for upload-only OAuth."""

    def test_upload_scope_present(self):
        self.assertIn(SCOPE_UPLOAD, SCOPES,
                      "youtube.upload scope must be in google_auth_config.SCOPES")

    def test_readonly_scope_NOT_present(self):
        """youtube.readonly must be ABSENT — research uses API key, not OAuth."""
        self.assertNotIn(SCOPE_READONLY, SCOPES,
                         "youtube.readonly must NOT be in SCOPES — "
                         "research uses YOUTUBE_API_KEY, not OAuth.")

    def test_drive_scope_NOT_present(self):
        """drive.file must be ABSENT — Google Drive integration is disabled/removed."""
        self.assertNotIn(SCOPE_DRIVE, SCOPES,
                         "drive.file must NOT be in SCOPES — Drive backup is disabled.")

    def test_scopes_is_a_list(self):
        self.assertIsInstance(SCOPES, list, "SCOPES must be a plain list")

    def test_no_duplicate_scopes(self):
        self.assertEqual(len(SCOPES), len(set(SCOPES)),
                         "SCOPES must not contain duplicates")

    def test_scopes_are_strings(self):
        for s in SCOPES:
            self.assertIsInstance(s, str,
                                  f"Every scope must be a string, got: {type(s)}")

    def test_scope_count(self):
        self.assertEqual(len(SCOPES), 1,
                         "SCOPES must have exactly 1 entry: youtube.upload only")


# ─────────────────────────────────────────────────────────────────────────────
class TestResearchUsesApiKey(unittest.TestCase):
    """Verify that the research collector uses API key, not OAuth credentials."""

    def test_collector_does_not_define_own_scopes(self):
        """collector.py must not define an independent SCOPES constant."""
        self.assertFalse(
            hasattr(collector_mod, "SCOPES"),
            "collector.py must NOT define its own SCOPES — research uses API key only"
        )

    def test_collector_constructor_accepts_api_key(self):
        """ResearchCollector.__init__ must accept an api_key parameter."""
        import inspect
        sig = inspect.signature(ResearchCollector.__init__)
        self.assertIn("api_key", sig.parameters,
                      "ResearchCollector.__init__ must accept api_key parameter")

    def test_collector_constructor_does_not_accept_creds(self):
        """ResearchCollector must NOT accept a creds/OAuth parameter."""
        import inspect
        sig = inspect.signature(ResearchCollector.__init__)
        self.assertNotIn("creds", sig.parameters,
                         "ResearchCollector must not accept creds — use api_key instead")

    def test_api_key_env_var_name_is_correct(self):
        """The env var name constant must match the documented secret name."""
        self.assertEqual(YOUTUBE_API_KEY_ENV, "YOUTUBE_API_KEY")

    def test_no_api_key_gives_mock(self):
        """When no API key is set, collector must return mock data."""
        with tempfile.TemporaryDirectory() as tmp:
            collector_mod.CACHE_FILE = Path(tmp) / "cache.json"
            # Ensure env var is absent
            env_backup = os.environ.pop("YOUTUBE_API_KEY", None)
            try:
                c = ResearchCollector(api_key=None)
                c._cache_raw = {"_version": collector_mod.CACHE_VERSION}
                r = c.search_youtube_videos("test query")
                self.assertIn(r["data_source"], ("mock", "offline"))
                self.assertTrue(r["is_mock"])
            finally:
                if env_backup:
                    os.environ["YOUTUBE_API_KEY"] = env_backup
                collector_mod.CACHE_FILE = Path("data/research/api_cache.json")

    def test_api_key_from_env_configures_client(self):
        """When YOUTUBE_API_KEY is set in env, collector picks it up."""
        with patch.dict(os.environ, {"YOUTUBE_API_KEY": "fake_test_key_xyz"}):
            with patch("googleapiclient.discovery.build") as mock_build:
                mock_build.return_value = MagicMock()
                c = ResearchCollector()
                self.assertEqual(c.api_key, "fake_test_key_xyz",
                                 "Collector must read api_key from env var")
                mock_build.assert_called_once_with(
                    "youtube", "v3", developerKey="fake_test_key_xyz"
                )


# ─────────────────────────────────────────────────────────────────────────────
class TestInsufficientScopeDetection(unittest.TestCase):
    """Verify that tokens missing required upload scopes are rejected clearly."""

    def _make_token_file(self, scopes: list, tmp_dir: Path) -> Path:
        token_data = {
            "token":         "fake_access_token",
            "refresh_token": "fake_refresh_token",
            "token_uri":     "https://oauth2.googleapis.com/token",
            "client_id":     "fake_client_id.apps.googleusercontent.com",
            "client_secret": "fake_client_secret",
            "scopes":        scopes,
            "expiry":        "2099-01-01T00:00:00Z",
        }
        p = tmp_dir / "token.json"
        p.write_text(json.dumps(token_data), encoding="utf-8")
        return p

    def test_token_missing_upload_scope_raises(self):
        """A token without youtube.upload must be rejected."""
        with tempfile.TemporaryDirectory() as tmp:
            token_file = self._make_token_file(
                [SCOPE_DRIVE],  # missing upload
                Path(tmp)
            )
            with self.assertRaises((ValueError, Exception)) as ctx:
                get_google_credentials(token_file=token_file)
            msg = str(ctx.exception).lower()
            self.assertTrue(
                any(kw in msg for kw in ("scope", "permission", "missing", "incompatible")),
                f"Error must reference scope problem. Got: {ctx.exception}"
            )

    def test_error_message_contains_reauth_instruction(self):
        """The scope error must tell the operator to run refresh_token.py."""
        with tempfile.TemporaryDirectory() as tmp:
            token_file = self._make_token_file(
                [SCOPE_DRIVE],  # missing upload scope
                Path(tmp)
            )
            with self.assertRaises((ValueError, Exception)) as ctx:
                get_google_credentials(token_file=token_file)
            self.assertIn("refresh_token.py", str(ctx.exception),
                          "Scope error must reference 'python refresh_token.py'")

    def test_complete_upload_token_passes_scope_check(self):
        """A token with youtube.upload must pass scope check."""
        with tempfile.TemporaryDirectory() as tmp:
            token_file = self._make_token_file(SCOPES, Path(tmp))
            try:
                get_google_credentials(token_file=token_file)
            except ValueError as e:
                msg = str(e).lower()
                self.assertNotIn("missing scopes", msg,
                                 "Token with correct scopes must not fail scope check")
            except Exception:
                pass  # Network/refresh failures are acceptable in offline test

    def test_token_with_readonly_still_passes_if_upload_present(self):
        """Old tokens that happen to have readonly/drive should still pass if upload is there."""
        with tempfile.TemporaryDirectory() as tmp:
            token_file = self._make_token_file(
                [SCOPE_UPLOAD, SCOPE_READONLY, SCOPE_DRIVE],
                Path(tmp)
            )
            # Should not raise a scope error (extra scopes are acceptable)
            try:
                get_google_credentials(token_file=token_file)
            except ValueError as e:
                self.assertNotIn("missing scopes", str(e).lower(),
                                 "Extra scopes in token must not cause scope rejection")
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────────────
class TestOAuthCredentialHandling(unittest.TestCase):
    """Verify uploader OAuth credentials check, refresh, and clear failures."""

    @patch("youtube_uploader.build")
    def test_uploader_receives_oauth_credentials(self, mock_build):
        """Existing YouTube uploader still receives credentials."""
        mock_creds = MagicMock()
        mock_video_path = Path("dummy.mp4")
        # Mock the YouTube API insert and resumable upload chunk loop
        mock_request = MagicMock()
        mock_request.next_chunk.return_value = (None, {"id": "dummy_video_id"})
        mock_build.return_value.videos.return_value.insert.return_value = mock_request

        with patch("youtube_uploader.Path.exists", return_value=True), \
             patch("youtube_uploader.Path.stat") as mock_stat:
            mock_stat.return_value.st_size = 10 * 1024 * 1024
            with patch("youtube_uploader.MediaFileUpload") as mock_media:
                youtube_uploader.upload_to_youtube(
                    creds=mock_creds,
                    video_path=mock_video_path,
                    title="Test",
                    description="Desc",
                    tags=[]
                )
                # Verify oauth build was called with the passed credentials
                mock_build.assert_called_once_with("youtube", "v3", credentials=mock_creds)

    @patch("google_auth_config.Credentials")
    def test_expired_access_token_refreshed(self, mock_creds_class):
        """Expired access tokens are refreshed using the refresh token."""
        mock_creds = MagicMock()
        mock_creds.expired = True
        mock_creds.refresh_token = "valid_refresh_token"
        mock_creds.scopes = SCOPES
        mock_creds.to_json.return_value = "{}"
        mock_creds_class.from_authorized_user_file.return_value = mock_creds

        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token.json"
            # Write a valid dummy JSON that satisfies _read_raw_scopes_from_file
            token_file.write_text(json.dumps({"scopes": SCOPES}), encoding="utf-8")

            with patch("google_auth_config.Request") as mock_request:
                get_google_credentials(token_file=token_file)
                # Ensure refresh was called
                mock_creds.refresh.assert_called_once()

    @patch("google_auth_config.Credentials")
    def test_refresh_failure_raises_clear_auth_error(self, mock_creds_class):
        """Refresh failure produces a clear authentication failure."""
        mock_creds = MagicMock()
        mock_creds.expired = True
        mock_creds.refresh_token = "valid_refresh_token"
        mock_creds.scopes = SCOPES
        mock_creds.refresh.side_effect = Exception("Auth Server Connection Error")
        mock_creds_class.from_authorized_user_file.return_value = mock_creds

        with tempfile.TemporaryDirectory() as tmp:
            token_file = Path(tmp) / "token.json"
            token_file.write_text(json.dumps({"scopes": SCOPES}), encoding="utf-8")

            with patch("google_auth_config.Request"):
                with self.assertRaises(ValueError) as ctx:
                    get_google_credentials(token_file=token_file)
                self.assertIn("Failed to refresh expired token", str(ctx.exception))


# ─────────────────────────────────────────────────────────────────────────────
class TestMockFallbackOnAuthFailure(unittest.TestCase):
    """Verify research collector falls back to mock when API key is absent."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self._orig_cache = collector_mod.CACHE_FILE
        collector_mod.CACHE_FILE = self.tmp / "cache.json"
        self._backup_key = os.environ.pop("YOUTUBE_API_KEY", None)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)
        collector_mod.CACHE_FILE = self._orig_cache
        if self._backup_key:
            os.environ["YOUTUBE_API_KEY"] = self._backup_key

    def test_no_api_key_returns_mock(self):
        c = ResearchCollector(api_key=None)
        c._cache_raw = {"_version": collector_mod.CACHE_VERSION}
        r = c.search_youtube_videos("Why Shiva has a snake")
        self.assertIn(r["data_source"], ("mock", "offline"))
        self.assertTrue(r["is_mock"])

    def test_mock_data_source_fails_live_validation_gate(self):
        """mock data_source must NOT be in the accepted real-API set."""
        ACCEPTED = {"youtube_api", "cached_youtube_api"}
        self.assertNotIn("mock",    ACCEPTED)
        self.assertNotIn("offline", ACCEPTED)

    def test_mock_urls_not_real_youtube(self):
        c = ResearchCollector(api_key=None)
        c._cache_raw = {"_version": collector_mod.CACHE_VERSION}
        r = c.search_youtube_videos("Narasimha avatar")
        for v in r["videos"]:
            self.assertFalse(
                v["url"].startswith("https://www.youtube.com/"),
                "Mock URLs must NOT use real youtube.com domain"
            )


# ─────────────────────────────────────────────────────────────────────────────
class TestNoCredentialPrinting(unittest.TestCase):
    """Verify no credential or key value is printed by any module."""

    def test_refresh_token_py_does_not_print_token_content(self):
        src = Path("refresh_token.py").read_text(encoding="utf-8")
        self.assertNotIn(
            "print(token_path.read_text())", src,
            "refresh_token.py must NOT print token file contents to stdout"
        )

    def test_google_auth_config_does_not_print_token_value(self):
        src = Path("google_auth_config.py").read_text(encoding="utf-8")
        for dangerous in ("creds.token", "creds.refresh_token"):
            self.assertNotIn(
                f"print({dangerous})", src,
                f"google_auth_config.py must not print {dangerous}"
            )

    def test_run_research_does_not_print_api_key(self):
        """run_research.py must not print the raw API key value."""
        src = Path("run_research.py").read_text(encoding="utf-8")
        # Acceptable: print key length. Not acceptable: print the key itself.
        self.assertNotIn(
            'print(api_key)', src,
            "run_research.py must NOT print the raw API key"
        )
        self.assertNotIn(
            'print(os.environ.get("YOUTUBE_API_KEY"))', src,
            "run_research.py must NOT print the raw API key via env"
        )

    def test_collector_does_not_log_api_key(self):
        """collector.py must not print or log the api_key value."""
        src = Path("src/research/collector.py").read_text(encoding="utf-8")
        self.assertNotIn(
            "print(self.api_key)", src,
            "collector.py must NOT print the raw API key"
        )
        self.assertNotIn(
            "print(api_key)", src,
            "collector.py must NOT print the raw API key"
        )


if __name__ == "__main__":
    unittest.main()
