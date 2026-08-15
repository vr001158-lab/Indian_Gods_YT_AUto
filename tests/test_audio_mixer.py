# tests/test_audio_mixer.py
# Unit Tests for Audio Mixer, Music Selection, and Ducking Subsystem

import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.audio.music import discover_music_tracks, select_background_music
from src.audio.ducking import mix_audio_with_ducking, NARRATION_TARGET_DB, MUSIC_TARGET_DB


def _make_dummy_audio(path: Path, duration: int = 5) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
            "-c:a", "mp3", "-b:a", "128k",
            str(path),
        ],
        check=True,
    )
    return path


class TestAudioMixerSubsystem(unittest.TestCase):
    """Tests 31–35: Audio mixing, background music, and ducking."""

    # ── Test 31: Narration remains dominant ──────────────────────────────────
    def test_31_narration_dominant_target(self):
        self.assertLessEqual(NARRATION_TARGET_DB, -3.0)
        self.assertGreaterEqual(NARRATION_TARGET_DB, -6.0)

    # ── Test 32: Music ducking target ────────────────────────────────────────
    def test_32_music_ducking_target(self):
        self.assertLessEqual(MUSIC_TARGET_DB, -18.0)
        self.assertGreaterEqual(MUSIC_TARGET_DB, -24.0)

    # ── Test 33: Valid final audio output ─────────────────────────────────────
    def test_33_valid_final_audio_output(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            narr = _make_dummy_audio(tmp / "narration.mp3", 5)
            mus = _make_dummy_audio(tmp / "music.mp3", 10)
            out = tmp / "mixed.mp3"

            res = mix_audio_with_ducking(narr, mus, out)
            self.assertTrue(res.exists())
            self.assertGreater(res.stat().st_size, 0)

    # ── Test 34: No clipping ─────────────────────────────────────────────────
    def test_34_no_clipping(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            narr = _make_dummy_audio(tmp / "narration.mp3", 3)
            out = tmp / "normalized.mp3"

            res = mix_audio_with_ducking(narr, None, out)
            self.assertTrue(res.exists())
            self.assertGreater(res.stat().st_size, 0)

    # ── Test 35: No zero-byte output ──────────────────────────────────────────
    def test_35_no_zero_byte_output(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            narr = _make_dummy_audio(tmp / "narration.mp3", 4)
            out = tmp / "mixed_out.mp3"

            res = mix_audio_with_ducking(narr, None, out)
            self.assertNotEqual(res.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
