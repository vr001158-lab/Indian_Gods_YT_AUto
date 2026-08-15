# src/voice/providers/base.py
# Base Interface for All Voice Generation Providers

from __future__ import annotations

from pathlib import Path
import subprocess
from typing import Any


def _get_audio_duration(path: Path) -> int:
    """Return ffprobe-measured duration in whole seconds; fallback to 5."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return max(1, round(float(result.stdout.strip())))
    except Exception:
        return 5


def _synthesize_speech(text: str, output_path: Path) -> int:
    """Offline test fallback speech synthesis helper."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    word_count = len(text.split())
    duration = max(5, round(word_count / 2.3))
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error",
            "-f", "lavfi", "-i", f"sine=frequency=440:duration={duration}",
            "-c:a", "mp3", "-b:a", "128k",
            str(output_path),
        ],
        check=True,
    )
    return _get_audio_duration(output_path)


class VoiceProviderError(RuntimeError):
    """Raised when voice synthesis fails or credentials are missing."""


class VoiceProvider:
    """
    Abstract Base Class for Voice Providers.
    
    Attributes
    ----------
    provider_name : str
    voice_id : str
    real_tts : bool — MUST be True for production providers, False for mock stubs.
    mode : str     — "production" or "test"
    """

    def __init__(
        self,
        provider_name: str = "base",
        voice_id: str = "default",
        real_tts: bool = False,
        mode: str = "test",
    ):
        self.provider_name = provider_name
        self.voice_id = voice_id
        self.real_tts = real_tts
        self.mode = mode

    def generate_speech(
        self,
        text: str,
        output_path: Path,
        language_code: str = "hi-IN",
        voice_config: dict[str, Any] | None = None,
    ) -> int:
        """
        Synthesize *text* to speech and save to *output_path*.

        Returns
        -------
        int — duration in whole seconds.
        """
        raise NotImplementedError("Subclasses must implement generate_speech")

    def generate_audio(self, text: str, output_path: Path) -> int:
        """Legacy compatibility wrapper."""
        return self.generate_speech(text, output_path)
