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
    def test_06_fallback_to_generated_track(self):
        # Only fallback track registered in manifest
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
        self.assertIsNotNone(selected_path)
        self.assertEqual(stype, "fallback_generated")
        self.assertEqual(selected_path.name, "fallback_track.wav")

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

        self.assertTrue(out_path.exists())
        self.assertGreater(out_path.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
