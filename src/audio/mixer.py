# src/audio/mixer.py
# Production Audio Mixer Module

from __future__ import annotations

from pathlib import Path
from src.audio.ducking import mix_audio_with_ducking
from src.audio.music import discover_music_tracks, select_background_music

__all__ = [
    "mix_audio_with_ducking",
    "discover_music_tracks",
    "select_background_music",
]
