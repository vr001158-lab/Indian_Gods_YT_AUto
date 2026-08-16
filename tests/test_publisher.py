# tests/test_publisher.py
# Phase 2K — YouTube Publisher Tests
#
# 16 tests covering all required scenarios.
# NO real uploads. All YouTube API calls are mocked.
# NO credential values are used or asserted on.

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

from publisher.safety   import (
    PublisherSafetyError,
    load_qa_result,
    validate_qa_for_publishing,
)
from publisher.metadata import build_video_metadata
from publisher.uploader import publish_video, upload_thumbnail, REQUIRED_PRIVACY


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

TOPIC = "Why Lord Shiva Wears a Snake Around His Neck"

APPROVAL_META = {
    "approved_for_generation": True,
    "selected_topic": TOPIC,
    "score": 66,
    "confidence": "high",
    "data_source": "youtube_api",
}


def _make_mp4(path: Path, *, empty: bool = False) -> Path:
    """Create a minimal stub MP4 file."""
    path.write_bytes(b"" if empty else (b"\x00\x00\x00\x20ftyp" + b"\x00" * 1279))
    return path


def _make_thumbnail_png(path: Path) -> Path:
    from PIL import Image
    img = Image.new("RGB", (1280, 720), color=(80, 20, 120))
    img.save(path, "PNG")
    return path


def _make_video_map(tmp: Path, mp4: Path) -> Path:
    vm_file = tmp / "video_map.json"
    vm_file.write_text(json.dumps({
        "video_file": str(mp4),
        "video_map_file": str(vm_file),
        "total_duration": 148,
        "resolution": "720x1280",
        "scenes": [{"scene": i, "image_file": "", "audio_file": "", "duration_seconds": 30}
                   for i in range(1, 6)],
    }), encoding="utf-8")
    return vm_file


def _make_script(tmp: Path) -> Path:
    sc = tmp / "script.json"
    sc.write_text(json.dumps({
        "title": f"Secrets of Shiva's Snake — {TOPIC}",
        "duration_seconds": 148,
        "narration": "Full narration text here.",
        "scene_scripts": [],
        "approval_metadata": APPROVAL_META,
    }), encoding="utf-8")
    return sc


def _make_brief(tmp: Path) -> Path:
    cb = tmp / "content_brief.json"
    cb.write_text(json.dumps({
        "primary_title": f"Shiva Snake Mystery — {TOPIC}",
        "hook": "A devotional hook line about Shiva.",
        "seo_keywords": ["shiva", "snake", "vasuki"],
        "approval_metadata": APPROVAL_META,
    }), encoding="utf-8")
    return cb


def _make_thumbnail_meta(tmp: Path, thumb_png: Path) -> Path:
    ts = "20260813_120000"
    meta_file = tmp / f"thumbnail_metadata_{ts}.json"
    meta_file.write_text(json.dumps({
        "title": TOPIC,
        "topic": TOPIC,
        "provider": "pil",
        "resolution": "1280x720",
        "format": "png",
        "approved_source": "youtube_api",
        "confidence": "high",
        "created_at": ts,
        "approval_metadata": APPROVAL_META,
    }), encoding="utf-8")
    # Also create the thumbnail file with matching name
    thumb_png.rename(tmp / f"thumbnail_{ts}.png")
    return meta_file


def _make_qa(
    tmp: Path,
    *,
    approved: bool = True,
    data_source: str = "youtube_api",
    confidence: str = "high",
    gen_approved: bool = True,
    topic: str = TOPIC,
    missing_video: bool = False,
    empty_mp4: bool = False,
) -> tuple[Path, Path]:
    """
    Build a complete QA JSON and supporting artifacts.
    Returns (qa_path, video_path).
    """
    mp4 = tmp / "video.mp4"
    _make_mp4(mp4, empty=empty_mp4)

    vm_file = _make_video_map(tmp, mp4)
    sc_file = _make_script(tmp)
    cb_file = _make_brief(tmp)

    from PIL import Image
    thumb_png = tmp / "thumbnail_raw.png"
    _make_thumbnail_png(thumb_png)
    tm_file = _make_thumbnail_meta(tmp, thumb_png)

    qa = {
        "approved_for_publishing": approved,
        "selected_topic": topic,
        "score": 66,
        "confidence": confidence,
        "data_source": data_source,
        "content_type": "short",
        "artifacts": {
            "decision":      str(tmp / "decision.json"),
            "content_brief": str(cb_file),
            "script":        str(sc_file),
            "audio":         str(tmp / "audio_map.json"),
            "visual":        str(tmp / "visual_map.json"),
            "video":         "" if missing_video else str(vm_file),
            "thumbnail":     str(tm_file),
        },
        "checks": {k: True for k in [
            "decision_approval", "provenance", "topic_consistency",
            "audio", "visual", "video", "thumbnail", "scene_sync",
        ]},
        "errors": [],
        "approval_metadata": {
            "approved_for_generation": gen_approved,
            "selected_topic": topic,
            "score": 66,
            "confidence": confidence,
            "data_source": data_source,
        },
        "approved_at": "2026-08-13T15:28:25Z",
    }

    # Write stub files needed for manifest
    (tmp / "decision.json").write_text("{}", encoding="utf-8")
    (tmp / "audio_map.json").write_text("{}", encoding="utf-8")
    (tmp / "visual_map.json").write_text("{}", encoding="utf-8")

    qa_file = tmp / "final_qa.json"
    qa_file.write_text(json.dumps(qa), encoding="utf-8")

    return qa_file, mp4


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestPublisherSafetyGate(unittest.TestCase):
    """Tests 1–8: Safety gate validation."""

    # ── Test 1: Approved QA accepted ──────────────────────────────────────
    def test_01_approved_qa_accepted(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            qa_file, _ = _make_qa(tmp)
            qa = load_qa_result(qa_file)
            # Should not raise
            validate_qa_for_publishing(qa)

    # ── Test 2: Failed QA rejected ────────────────────────────────────────
    def test_02_failed_qa_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            qa_file, _ = _make_qa(tmp, approved=False)
            qa = load_qa_result(qa_file)
            with self.assertRaises(PublisherSafetyError) as ctx:
                validate_qa_for_publishing(qa)
            self.assertIn("approved_for_publishing", str(ctx.exception))

    # ── Test 3: Mock research rejected ────────────────────────────────────
    def test_03_mock_source_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            qa_file, _ = _make_qa(tmp, data_source="mock")
            qa = load_qa_result(qa_file)
            with self.assertRaises(PublisherSafetyError) as ctx:
                validate_qa_for_publishing(qa)
            self.assertIn("data_source", str(ctx.exception))

    # ── Test 4: Offline research rejected ─────────────────────────────────
    def test_04_offline_source_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            qa_file, _ = _make_qa(tmp, data_source="offline")
            qa = load_qa_result(qa_file)
            with self.assertRaises(PublisherSafetyError):
                validate_qa_for_publishing(qa)

    # ── Test 5: Low confidence rejected ───────────────────────────────────
    def test_05_low_confidence_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            qa_file, _ = _make_qa(tmp, confidence="low")
            qa = load_qa_result(qa_file)
            with self.assertRaises(PublisherSafetyError) as ctx:
                validate_qa_for_publishing(qa)
            self.assertIn("confidence", str(ctx.exception))

    # ── Test 6: Missing video rejected ────────────────────────────────────
    def test_06_missing_video_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            qa_file, _ = _make_qa(tmp, missing_video=True)
            qa = load_qa_result(qa_file)
            with self.assertRaises(PublisherSafetyError):
                validate_qa_for_publishing(qa)

    # ── Test 7: Invalid (empty) video rejected ────────────────────────────
    def test_07_invalid_video_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            qa_file, _ = _make_qa(tmp, empty_mp4=True)
            qa = load_qa_result(qa_file)
            with self.assertRaises(PublisherSafetyError) as ctx:
                validate_qa_for_publishing(qa)
            self.assertIn("zero bytes", str(ctx.exception))

    # ── Test 7b: Corrupted / mock text video rejected ─────────────────────
    def test_07b_corrupted_video_stub_rejected(self):
        """Mock text files or corrupt stubs (e.g. video_20260813_194729.mp4) must be rejected."""
        from publisher.safety import verify_video_with_ffprobe
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            corrupt_file = tmp / "video_20260813_194729.mp4"
            corrupt_file.write_text("MOCK_MP4_VIDEO: resolution=720x1280, format=yuv420p", encoding="utf-8")
            with self.assertRaises(PublisherSafetyError) as ctx:
                verify_video_with_ffprobe(corrupt_file)
            self.assertIn("Mock video text file is not valid", str(ctx.exception))

    # ── Test 8: PUBLIC privacy enforced ───────────────────────────────────
    def test_08_public_privacy_enforced(self):
        """REQUIRED_PRIVACY must always be 'public' — the authorized production status."""
        self.assertEqual(REQUIRED_PRIVACY, "public")


class TestPublisherUpload(unittest.TestCase):
    """Tests 9–14: Upload mechanics, mocked."""

    def _mock_creds(self):
        return MagicMock()

    # ── Test 9: Credentials never logged ─────────────────────────────────
    def test_09_credentials_never_logged(self):
        """uploader.py source must not print/log token/credential values."""
        src = (
            Path(__file__).parent.parent / "src" / "publisher" / "uploader.py"
        ).read_text(encoding="utf-8")
        for forbidden in (
            "print(creds",
            "print(token",
            "print(refresh_token",
            "print(client_secret",
            "log(creds",
        ):
            self.assertNotIn(forbidden, src,
                             f"uploader.py must not log: {forbidden}")

    # ── Test 10: Successful upload mocked ────────────────────────────────
    def test_10_successful_upload_mocked(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            qa_file, mp4 = _make_qa(tmp)
            qa = json.loads(qa_file.read_text(encoding="utf-8"))
            meta = build_video_metadata(qa)

            mock_creds = self._mock_creds()
            with patch("youtube_uploader.build") as mock_build, \
                 patch("youtube_uploader.MediaFileUpload"):
                mock_req = MagicMock()
                mock_req.next_chunk.return_value = (None, {"id": "FAKE_VIDEO_ID_001"})
                mock_build.return_value.videos.return_value.insert.return_value = mock_req

                # Also mock thumbnail upload
                with patch("publisher.uploader.upload_thumbnail", return_value=True):
                    manifest = publish_video(
                        creds          = mock_creds,
                        video_file     = mp4,
                        title          = meta["title"],
                        description    = meta["description"],
                        tags           = meta["tags"],
                        category_id    = meta["category_id"],
                        thumbnail_file = meta.get("thumbnail_file") or None,
                        qa             = qa,
                        output_dir     = str(tmp / "publishing"),
                    )

            self.assertTrue(manifest["success"])
            self.assertEqual(manifest["video_id"], "FAKE_VIDEO_ID_001")
            self.assertIn("FAKE_VIDEO_ID_001", manifest["youtube_url"])

    # ── Test 11: Failed upload handled ───────────────────────────────────
    def test_11_failed_upload_handled(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            qa_file, mp4 = _make_qa(tmp)
            qa = json.loads(qa_file.read_text(encoding="utf-8"))
            meta = build_video_metadata(qa)

            mock_creds = self._mock_creds()
            with patch("youtube_uploader.build") as mock_build, \
                 patch("youtube_uploader.MediaFileUpload"):
                mock_build.return_value.videos.return_value.insert.side_effect = \
                    RuntimeError("API quota exceeded")

                from publisher.uploader import PublishError
                with self.assertRaises(PublishError) as ctx:
                    publish_video(
                        creds          = mock_creds,
                        video_file     = mp4,
                        title          = meta["title"],
                        description    = meta["description"],
                        tags           = meta["tags"],
                        category_id    = meta["category_id"],
                        thumbnail_file = None,
                        qa             = qa,
                        output_dir     = str(tmp / "publishing"),
                    )
                self.assertIn("upload failed", str(ctx.exception).lower())

    # ── Test 12: Video ID captured ────────────────────────────────────────
    def test_12_video_id_captured(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            qa_file, mp4 = _make_qa(tmp)
            qa = json.loads(qa_file.read_text(encoding="utf-8"))
            meta = build_video_metadata(qa)

            with patch("youtube_uploader.build") as mock_build, \
                 patch("youtube_uploader.MediaFileUpload"):
                mock_req = MagicMock()
                mock_req.next_chunk.return_value = (None, {"id": "SHIVA_VID_XYZ"})
                mock_build.return_value.videos.return_value.insert.return_value = mock_req

                with patch("publisher.uploader.upload_thumbnail", return_value=False):
                    manifest = publish_video(
                        creds          = self._mock_creds(),
                        video_file     = mp4,
                        title          = meta["title"],
                        description    = meta["description"],
                        tags           = meta["tags"],
                        category_id    = meta["category_id"],
                        thumbnail_file = None,
                        qa             = qa,
                        output_dir     = str(tmp / "publishing"),
                    )
            self.assertEqual(manifest["video_id"], "SHIVA_VID_XYZ")
            self.assertEqual(
                manifest["youtube_url"],
                "https://www.youtube.com/watch?v=SHIVA_VID_XYZ",
            )

    # ── Test 13: Thumbnail failure handled safely ─────────────────────────
    def test_13_thumbnail_failure_handled_safely(self):
        """Thumbnail upload failure must NOT abort the pipeline."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            qa_file, mp4 = _make_qa(tmp)
            qa = json.loads(qa_file.read_text(encoding="utf-8"))
            meta = build_video_metadata(qa)

            from publisher.uploader import PublishError
            with patch("youtube_uploader.build") as mock_build, \
                 patch("youtube_uploader.MediaFileUpload"):
                mock_req = MagicMock()
                mock_req.next_chunk.return_value = (None, {"id": "SAFE_VID_001"})
                mock_build.return_value.videos.return_value.insert.return_value = mock_req

                # Thumbnail upload raises — must be caught, not propagated
                with patch("publisher.uploader.upload_thumbnail",
                           side_effect=PublishError("Thumbnail API error")):
                    manifest = publish_video(
                        creds          = self._mock_creds(),
                        video_file     = mp4,
                        title          = meta["title"],
                        description    = meta["description"],
                        tags           = meta["tags"],
                        category_id    = meta["category_id"],
                        thumbnail_file = "/nonexistent/thumb.png",
                        qa             = qa,
                        output_dir     = str(tmp / "publishing"),
                    )
            # Video still succeeded despite thumbnail failure
            self.assertTrue(manifest["success"])
            self.assertEqual(manifest["video_id"], "SAFE_VID_001")
            self.assertFalse(manifest["thumbnail_uploaded"])
            self.assertIn("Thumbnail API error", manifest["thumbnail_error"])

    # ── Test 14: Publishing manifest schema ───────────────────────────────
    def test_14_publishing_manifest_schema(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            qa_file, mp4 = _make_qa(tmp)
            qa = json.loads(qa_file.read_text(encoding="utf-8"))
            meta = build_video_metadata(qa)

            with patch("youtube_uploader.build") as mock_build, \
                 patch("youtube_uploader.MediaFileUpload"):
                mock_req = MagicMock()
                mock_req.next_chunk.return_value = (None, {"id": "SCHEMA_TEST_001"})
                mock_build.return_value.videos.return_value.insert.return_value = mock_req

                with patch("publisher.uploader.upload_thumbnail", return_value=True):
                    manifest = publish_video(
                        creds          = self._mock_creds(),
                        video_file     = mp4,
                        title          = meta["title"],
                        description    = meta["description"],
                        tags           = meta["tags"],
                        category_id    = meta["category_id"],
                        thumbnail_file = None,
                        qa             = qa,
                        output_dir     = str(tmp / "publishing"),
                    )

        required_keys = [
            "video_id", "youtube_url", "selected_topic", "privacy_status",
            "upload_timestamp", "thumbnail_uploaded", "approval_metadata",
            "source_artifacts", "success", "video_file",
        ]
        for key in required_keys:
            self.assertIn(key, manifest, f"Manifest missing key: {key}")

        # Privacy must be "public"
        self.assertEqual(manifest["privacy_status"], "public")

        # No credential keys in manifest
        manifest_json = json.dumps(manifest)
        for forbidden in ("refresh_token", "client_secret", "access_token", "token_uri"):
            self.assertNotIn(forbidden, manifest_json,
                             f"Manifest must not contain: {forbidden}")

        # approval_metadata preserved
        am = manifest["approval_metadata"]
        self.assertTrue(am.get("approved_for_generation"))
        self.assertEqual(am.get("data_source"), "youtube_api")


class TestPublisherMetadata(unittest.TestCase):
    """Tests 15–16: Metadata and CLI."""

    # ── Test 15: Deterministic metadata ───────────────────────────────────
    def test_15_deterministic_metadata(self):
        """Same QA input produces the same metadata on two calls."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            qa_file, _ = _make_qa(tmp)
            qa = json.loads(qa_file.read_text(encoding="utf-8"))
            m1 = build_video_metadata(qa)
            m2 = build_video_metadata(qa)
        self.assertEqual(m1["title"], m2["title"])
        self.assertEqual(m1["tags"],  m2["tags"])
        self.assertEqual(m1["category_id"], m2["category_id"])

    # ── Test 16: CLI execution (dry-run) ──────────────────────────────────
    def test_16_cli_execution_dry_run(self):
        """CLI dry-run validates inputs and exits 0 without uploading."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            qa_file, _ = _make_qa(tmp)

            cli = Path(__file__).parent.parent / "run_publisher.py"
            env = os.environ.copy()
            env["PYTHONPATH"] = (
                str(Path(__file__).parent.parent / "src")
                + os.pathsep
                + str(Path(__file__).parent.parent)
            )
            proc = subprocess.run(
                [
                    sys.executable, str(cli),
                    "--qa",        str(qa_file),
                    "--output-dir", str(tmp / "publishing"),
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                timeout=30,
            )
            output = proc.stdout + proc.stderr
            self.assertIn("YOUTUBE PUBLISHER", output)
            self.assertIn("DRY RUN", output)
            self.assertEqual(proc.returncode, 0, msg=output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
