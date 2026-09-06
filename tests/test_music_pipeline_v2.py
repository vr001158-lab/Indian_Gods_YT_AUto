# tests/test_music_pipeline_v2.py
# Phase 6.3 — Unit Tests for Music Pipeline v2 Architecture

import json
import shutil
import tempfile
import unittest
import hashlib
import subprocess
from pathlib import Path

from src.audio.music import (
    load_music_manifest,
    validate_music_provenance,
    select_background_music_v2,
    select_background_music,
)
from src.audio.ducking import mix_audio_with_ducking


class TestMusicPipelineV2(unittest.TestCase):

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.tmp_dir.name)
        self.music_dir = self.base_dir / "assets" / "music"
        self.devotional_dir = self.music_dir / "devotional"
        self.devotional_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_file = self.music_dir / "music_manifest.json"

        # Create dummy audio file 1: Primary track (YouTube Audio Library)
        self.primary_file = self.devotional_dir / "primary_track.wav"
        self._write_dummy_wav(self.primary_file, freq=440)
        self.sha256_primary = hashlib.sha256(self.primary_file.read_bytes()).hexdigest()

        # Create dummy audio file 2: Fallback track (Original Generated)
        self.fallback_file = self.devotional_dir / "fallback_track.wav"
        self._write_dummy_wav(self.fallback_file, freq=220)
        self.sha256_fallback = hashlib.sha256(self.fallback_file.read_bytes()).hexdigest()

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _write_dummy_wav(self, path: Path, freq: int = 440):
        import wave, struct
        sample_rate = 48000
        duration = 2.0
        n_samples = int(sample_rate * duration)
        with wave.open(str(path), "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            frames = bytearray()
            for i in range(n_samples):
                val = int(16000 * (i % (sample_rate // freq) / (sample_rate // freq)))
                frames.extend(struct.pack("<hh", val, val))
            wf.writeframes(frames)

    def _write_manifest(self, tracks: list):
        data = {"tracks": tracks}
        self.manifest_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # -------------------------------------------------------------------------
    # 1. Primary Track Selection Test
    # -------------------------------------------------------------------------
    def test_01_primary_track_selection(self):
        tracks = [
            {
                "filename": "primary_track.wav",
                "relative_path": "assets/music/devotional/primary_track.wav",
                "track_name": "Primary Devotional",
                "category": "devotional",
                "source": "YouTube Audio Library",
                "source_type": "youtube_audio_library",
                "commercial_use": True,
                "youtube_shorts_permitted": True,
                "approved": True,
                "sha256": self.sha256_primary
            },
            {
                "filename": "fallback_track.wav",
                "relative_path": "assets/music/devotional/fallback_track.wav",
                "track_name": "Fallback Devotional",
                "category": "devotional",
                "source": "Synthesizer",
                "source_type": "original_generated",
                "commercial_use": True,
                "youtube_shorts_permitted": True,
                "approved": True,
                "sha256": self.sha256_fallback
            }
        ]
        self._write_manifest(tracks)

        selected_path, stype = select_background_music_v2(category="devotional", music_dir=self.music_dir)
        self.assertIsNotNone(selected_path)
        self.assertEqual(stype, "primary")
        self.assertEqual(selected_path.name, "primary_track.wav")

    # -------------------------------------------------------------------------
    # 2. Hard License Rejection Gate Tests
    # -------------------------------------------------------------------------
    def test_02_rejection_unapproved_track(self):
        tracks = [{
            "filename": "primary_track.wav",
            "relative_path": "assets/music/devotional/primary_track.wav",
            "source_type": "youtube_audio_library",
            "commercial_use": True,
            "youtube_shorts_permitted": True,
            "approved": False,
            "sha256": self.sha256_primary
        }]
        self._write_manifest(tracks)
        ok, msg, _ = validate_music_provenance(self.primary_file, manifest_path=self.manifest_file)
        self.assertFalse(ok)
        self.assertIn("unapproved", msg)

    def test_03_rejection_non_commercial_track(self):
        tracks = [{
            "filename": "primary_track.wav",
            "relative_path": "assets/music/devotional/primary_track.wav",
            "source_type": "youtube_audio_library",
            "commercial_use": False,
            "youtube_shorts_permitted": True,
            "approved": True,
            "sha256": self.sha256_primary
        }]
        self._write_manifest(tracks)
        ok, msg, _ = validate_music_provenance(self.primary_file, manifest_path=self.manifest_file)
        self.assertFalse(ok)
        self.assertIn("commercial use", msg)

    def test_04_rejection_sha256_mismatch(self):
        tracks = [{
            "filename": "primary_track.wav",
            "relative_path": "assets/music/devotional/primary_track.wav",
            "source_type": "youtube_audio_library",
            "commercial_use": True,
            "youtube_shorts_permitted": True,
            "approved": True,
            "sha256": "0000000000000000000000000000000000000000000000000000000000000000"
        }]
        self._write_manifest(tracks)
        ok, msg, _ = validate_music_provenance(self.primary_file, manifest_path=self.manifest_file)
        self.assertFalse(ok)
        self.assertIn("SHA256 mismatch", msg)

    def test_05_rejection_arbitrary_unauthorized_source(self):
        tracks = [{
            "filename": "primary_track.wav",
            "relative_path": "assets/music/devotional/primary_track.wav",
            "source_type": "arbitrary_youtube_rip",
            "commercial_use": True,
            "youtube_shorts_permitted": True,
            "approved": True,
            "sha256": self.sha256_primary
        }]
        self._write_manifest(tracks)
        ok, msg, _ = validate_music_provenance(self.primary_file, manifest_path=self.manifest_file)
        self.assertFalse(ok)
        self.assertIn("unauthorized source_type", msg)

    # -------------------------------------------------------------------------
    # 3. Fallback Selection Tests
    # -------------------------------------------------------------------------
    def test_06_synthetic_tracks_never_auto_selected(self):
        # Only fallback synthetic track registered in manifest -> must fail closed to None
        tracks = [{
            "filename": "fallback_track.wav",
            "relative_path": "assets/music/devotional/fallback_track.wav",
            "category": "devotional",
            "source_type": "original_generated",
            "commercial_use": True,
            "youtube_shorts_permitted": True,
            "approved": True,
            "sha256": self.sha256_fallback
        }]
        self._write_manifest(tracks)

        selected_path, stype = select_background_music_v2(category="devotional", music_dir=self.music_dir)
        self.assertIsNone(selected_path)
        self.assertEqual(stype, "narration_only")

    def test_07_fallback_to_narration_only(self):
        # Empty manifest
        self._write_manifest([])
        selected_path, stype = select_background_music_v2(category="devotional", music_dir=self.music_dir)
        self.assertIsNone(selected_path)
        self.assertEqual(stype, "narration_only")

    # -------------------------------------------------------------------------
    # 4. Ducking & Mixing Integrity Tests
    # -------------------------------------------------------------------------
    def test_08_ducking_audio_generation(self):
        narration_wav = self.base_dir / "narration.wav"
        self._write_dummy_wav(narration_wav, freq=800)
        output_mp3 = self.base_dir / "mixed_out.mp3"

        out_path = mix_audio_with_ducking(
            narration_path=narration_wav,
            music_path=self.primary_file,
            output_path=output_mp3,
            narration_volume_db=-4.0,
            music_volume_db=-16.0,
        )

        self.assertTrue(out_path.exists())
        self.assertGreater(out_path.stat().st_size, 1000)

    def test_09_narration_only_when_music_none(self):
        narration_wav = self.base_dir / "narration.wav"
        self._write_dummy_wav(narration_wav, freq=800)
        output_mp3 = self.base_dir / "narration_only.mp3"

        out_path = mix_audio_with_ducking(
            narration_path=narration_wav,
            music_path=None,
            output_path=output_mp3,
        )

    def test_10_all_12_deities_manifest_and_catalog_validation(self):
        """Verify all 12 deities have usable, approved physical assets matching SHA256 and provenance rules."""
        from src.audio.music import DEITY_SONG_CATALOG, MANIFEST_PATH, load_music_manifest, validate_music_provenance, select_background_music_v2

        canonical_deities = [
            "shiva", "hanuman", "krishna", "rama", "ganesha", "durga",
            "lakshmi", "saraswati", "vishnu", "kali", "murugan", "ayyappa"
        ]

        manifest = load_music_manifest(MANIFEST_PATH)
        tracks = manifest.get("tracks", [])
        self.assertGreaterEqual(len(tracks), 12, "Manifest must contain at least 12 registered tracks")

        # Verify physical existence and SHA-256 for all tracks in repository manifest
        for tr in tracks:
            rel_path = Path(tr["relative_path"])
            self.assertTrue(rel_path.exists(), f"Registered asset file does not exist: {rel_path}")

            # Check SHA256 matches physical file
            actual_sha256 = hashlib.sha256(rel_path.read_bytes()).hexdigest()
            self.assertEqual(tr["sha256"], actual_sha256, f"SHA256 mismatch for {rel_path}")

            # Validate provenance according to approval state
            ok, msg, _ = validate_music_provenance(rel_path, manifest_path=MANIFEST_PATH)
            if tr.get("approved", False):
                self.assertTrue(ok, f"Provenance validation failed for approved track {rel_path}: {msg}")
            else:
                self.assertFalse(ok, f"Unapproved track {rel_path} unexpectedly passed provenance")

            self.assertIn(tr["source_type"], {"original_generated", "youtube_audio_library", "royalty_free_public"})
            self.assertTrue(tr.get("commercial_use", False))
            self.assertNotEqual(tr.get("youtube_shorts_permitted"), False)

        # Verify every canonical deity has at least one approved usable asset in catalog
        for deity in canonical_deities:
            self.assertIn(deity, DEITY_SONG_CATALOG, f"Deity {deity} missing from catalog")
            script = {"selected_topic": deity}
            track, stype = select_background_music_v2(category="devotional", script=script)
            self.assertIsNotNone(track, f"No approved track selected for deity: {deity}")
            self.assertTrue(track.exists(), f"Selected track for {deity} does not exist: {track}")
            ok, msg, _ = validate_music_provenance(track, manifest_path=MANIFEST_PATH)
            self.assertTrue(ok, f"Selected track for {deity} failed provenance: {msg}")

    def test_11_youtube_audio_library_tracks_and_rama_mapping(self):
        """Verify YouTube Audio Library tracks integration, SHA-256 verification, and Rama -> Bhaj Le Ram mapping."""
        from src.audio.music import MANIFEST_PATH, load_music_manifest, validate_music_provenance, select_background_music_v2, get_bgm_metadata_for_track

        manifest = load_music_manifest(MANIFEST_PATH)
        tracks_by_fn = {tr["filename"]: tr for tr in manifest.get("tracks", [])}

        yt_files = [
            "Bhaj Le Ram - Bhajan (Voice, Sarangi, Tabla) - Sandeep Das,  Ujjwal Sahani,  Aneesh Mishra.mp3",
            "Calcutta Sunset - E's Jammy Jams.mp3",
            "Raag Charukeshi - Madhyalaya Teentaal (Sitar, Tabla) - Sandeep Das,  Amrendra Mishra.mp3"
        ]

        for fn in yt_files:
            self.assertIn(fn, tracks_by_fn, f"YouTube Audio Library file {fn} missing from manifest")
            tr = tracks_by_fn[fn]
            self.assertEqual(tr["source"], "YouTube Audio Library")
            self.assertEqual(tr["source_type"], "youtube_audio_library")
            self.assertEqual(tr["license"], "Attribution not required")
            self.assertTrue(tr["approved"])

            rel_path = Path(tr["relative_path"])
            self.assertTrue(rel_path.exists(), f"Physical audio file missing: {rel_path}")
            actual_sha = hashlib.sha256(rel_path.read_bytes()).hexdigest()
            self.assertEqual(tr["sha256"], actual_sha, f"SHA256 mismatch for {fn}")

            ok, reason, _ = validate_music_provenance(rel_path, manifest_path=MANIFEST_PATH)
            self.assertTrue(ok, f"Provenance failed for {fn}: {reason}")

        # Verify Rama script maps to an approved Rama track
        rama_script = {"title": "Shri Ram Ayodhya Dharshanam", "selected_topic": "Rama"}
        track, stype = select_background_music_v2(category="devotional", script=rama_script)
        self.assertIsNotNone(track)
        self.assertEqual(stype, "primary")
        self.assertTrue("Bhaj Le Ram" in track.name or "ram-bhajan" in track.name)

        bgm_meta = get_bgm_metadata_for_track(track, script=rama_script)
        self.assertEqual(bgm_meta["deity"], "rama")

        # Verify unmapped deity falls back to Calcutta Sunset
        unmapped_script = {"title": "Unknown Entity Mystery", "selected_topic": "Unknown Deity X"}
        unmapped_track, unmapped_stype = select_background_music_v2(category="devotional", script=unmapped_script)
        self.assertIsNotNone(unmapped_track)
        self.assertIn("Calcutta Sunset", unmapped_track.name)
        self.assertEqual(unmapped_stype, "primary")

    def test_12_production_music_fallback_priority(self):
        """Verify production music selection priority: Deity-specific trusted track -> Calcutta Sunset -> Fail Closed."""
        from src.audio.music import select_background_music_v2, validate_music_provenance, MANIFEST_PATH

        # A. Ganesha with approved deity-specific trusted Pixabay track -> elijah_k-ganesha-323827.mp3
        ganesha_script = {"title": "Sacrifice of Ganesha", "selected_topic": "ganesha"}
        ganesha_track, stype = select_background_music_v2(category="devotional", script=ganesha_script)
        self.assertIsNotNone(ganesha_track)
        self.assertIn("ganesha", ganesha_track.name.lower())
        self.assertEqual(stype, "primary")

        # B. Rama with approved Rama tracks available -> Bhaj Le Ram / kontraa-ram-bhajan
        rama_script = {"title": "Shri Ram Ayodhya Dharshanam", "selected_topic": "rama"}
        rama_track, r_stype = select_background_music_v2(category="devotional", script=rama_script)
        self.assertIsNotNone(rama_track)
        self.assertTrue("Bhaj Le Ram" in rama_track.name or "ram-bhajan" in rama_track.name)
        self.assertEqual(r_stype, "primary")

        # C. Unmapped deity (Surya) -> Calcutta Sunset fallback
        surya_script = {"title": "Secrets of Surya", "selected_topic": "surya"}
        surya_track, s_stype = select_background_music_v2(category="devotional", script=surya_script)
        self.assertIsNotNone(surya_track)
        self.assertIn("Calcutta Sunset", surya_track.name)
        self.assertEqual(s_stype, "primary")

        # D. Synthetic tracks are NEVER selected by normal production fallback
        self.assertNotIn("original", ganesha_track.name.lower())
        self.assertNotIn("flute", ganesha_track.name.lower())
        self.assertNotIn("original", surya_track.name.lower())

        # E. If Calcutta Sunset is unavailable or fails provenance validation, fail closed
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_music_dir = Path(tmp_dir) / "assets" / "music"
            tmp_music_dir.mkdir(parents=True, exist_ok=True)
            empty_manifest = tmp_music_dir / "music_manifest.json"
            empty_manifest.write_text(json.dumps({"tracks": [
                {
                    "filename": "synthetic_only.mp3",
                    "relative_path": "assets/music/devotional/synthetic_only.mp3",
                    "source_type": "original_generated",
                    "approved": True
                }
            ]}), encoding="utf-8")

            failed_track, failed_stype = select_background_music_v2(category="devotional", music_dir=tmp_music_dir, script=ganesha_script)
            self.assertIsNone(failed_track)
            self.assertEqual(failed_stype, "narration_only")

    def test_13_pixabay_approved_tracks_selection(self):
        """Verify Pixabay approved tracks can be selected for deity and fallback works."""
        from src.audio.music import select_background_music_v2

        # Ganesha -> Pixabay approved Ganesha track
        g_track, g_stype = select_background_music_v2(deity="ganesha")
        self.assertIsNotNone(g_track)
        self.assertIn("ganesha-323827", g_track.name)
        self.assertEqual(g_stype, "primary")

        # Krishna -> Pixabay approved Krishna track
        k_track, k_stype = select_background_music_v2(deity="krishna")
        self.assertIsNotNone(k_track)
        self.assertIn("krishna", k_track.name.lower())
        self.assertEqual(k_stype, "primary")

        # Unmapped deity -> Calcutta Sunset
        u_track, u_stype = select_background_music_v2(deity="unmapped_deity_test")
        self.assertIsNotNone(u_track)
        self.assertIn("Calcutta Sunset", u_track.name)
        self.assertEqual(u_stype, "primary")

    def test_14_pixabay_provenance_validation(self):
        """Verify all Pixabay approved tracks pass hard provenance gate."""
        from src.audio.music import validate_music_provenance, MANIFEST_PATH

        approved_files = [
            Path("assets/music/pixabay/elijah_k-ganesha-323827.mp3"),
            Path("assets/music/pixabay/photowhole22--231281.mp3"),
            Path("assets/music/pixabay/emand_edroff-om-namah-shivaya-475721.mp3")
        ]
        for af in approved_files:
            self.assertTrue(af.exists())
            ok, msg, track_info = validate_music_provenance(af, manifest_path=MANIFEST_PATH)
            self.assertTrue(ok, f"Provenance validation failed for {af}: {msg}")

    def test_15_pixabay_credits_generation(self):
        """Verify automated YouTube description credits formatting from manifest metadata."""
        from src.audio.music import get_bgm_credit_for_track

        # Cert-backed track with URL
        ganesha_track = Path("assets/music/pixabay/elijah_k-ganesha-323827.mp3")
        credit = get_bgm_credit_for_track(ganesha_track)
        self.assertIsNotNone(credit)
        self.assertIn("Music: Ganesha", credit)
        self.assertIn("Artist: elijah_k", credit)
        self.assertIn("Source: Pixabay", credit)
        self.assertIn("URL: https://pixabay.com/music/india-ganesha-323827/", credit)

        # Cert-less track with Hindi title (photowhole22)
        photowhole_track = Path("assets/music/pixabay/photowhole22--231281.mp3")
        pw_credit = get_bgm_credit_for_track(photowhole_track)
        self.assertIsNotNone(pw_credit)
        self.assertIn("Photowhole22", pw_credit)
        self.assertIn("Pixabay", pw_credit)


if __name__ == "__main__":
    unittest.main()
