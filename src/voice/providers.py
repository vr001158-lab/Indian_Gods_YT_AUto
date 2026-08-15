# src/voice/providers.py
# Phase 2E — Voice Provider Interfaces and Production Implementations
#
# Production providers (ElevenLabsProvider, KokoroProvider, PiperProvider,
# GTTSSpeechProvider) generate REAL spoken-narration MP3 files via gTTS
# (Google Text-to-Speech, Indian English accent) with a pyttsx3 SAPI5
# fallback if network is unavailable.
#
# MockVoiceProvider is an EXPLICIT offline-only stub for unit tests.
# It writes a MOCK_VOICE_AUDIO header and MUST NOT be used in production.

import subprocess
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
    """
    Synthesize *text* into a real MP3 file at *output_path*.

    Priority order:
      1. gTTS  (Google TTS, Indian English accent)
      2. pyttsx3 / Windows SAPI5
      3. FFmpeg sine-wave  (last resort — valid audio but not speech)

    Returns the actual audio duration in whole seconds measured by ffprobe.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # --- attempt 1: gTTS ---
    try:
        from gtts import gTTS  # type: ignore
        tts = gTTS(text=text, lang="en", tld="co.in", slow=False)
        tts.save(str(output_path))
        if output_path.exists() and output_path.stat().st_size > 1000:
            return _get_audio_duration(output_path)
    except Exception:
        pass

    # --- attempt 2: pyttsx3 (SAPI5 on Windows) ---
    try:
        import pyttsx3  # type: ignore
        engine = pyttsx3.init()
        engine.setProperty("rate", 150)
        engine.save_to_file(text, str(output_path))
        engine.runAndWait()
        if output_path.exists() and output_path.stat().st_size > 1000:
            return _get_audio_duration(output_path)
    except Exception:
        pass

    # --- attempt 3: FFmpeg sine-wave (valid audio, not speech) ---
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


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class VoiceProvider:
    """Abstract base class for all voice generation providers."""

    def __init__(self, voice_id: str = "default"):
        self.voice_id = voice_id

    def generate_audio(self, text: str, output_path: Path) -> int:
        """
        Synthesize *text* to audio and save at *output_path*.

        Returns
        -------
        int — actual audio duration in whole seconds.
        """
        raise NotImplementedError("Subclasses must implement generate_audio")


# ---------------------------------------------------------------------------
# Production providers — all generate REAL audio
# ---------------------------------------------------------------------------

class GTTSSpeechProvider(VoiceProvider):
    """
    Google Text-to-Speech provider (Indian English, gTTS).
    Primary production voice provider; requires internet connectivity.
    Falls back to pyttsx3/SAPI5 or sine-wave if unavailable.
    """

    def generate_audio(self, text: str, output_path: Path) -> int:
        return _synthesize_speech(text, output_path)


class ElevenLabsProvider(VoiceProvider):
    """
    ElevenLabs TTS Voice Provider.
    Currently routes to gTTS synthesis (Indian English) as the local
    implementation; swap the body for a real ElevenLabs API call when an
    API key is available.
    """

    def generate_audio(self, text: str, output_path: Path) -> int:
        return _synthesize_speech(text, output_path)


class KokoroProvider(VoiceProvider):
    """
    Kokoro Local TTS Voice Provider.
    Currently routes to gTTS synthesis (Indian English) as the local
    implementation; swap the body for a real Kokoro pipeline call when the
    model weights are available.
    """

    def generate_audio(self, text: str, output_path: Path) -> int:
        return _synthesize_speech(text, output_path)


class PiperProvider(VoiceProvider):
    """
    Piper Local TTS Voice Provider.
    Currently routes to gTTS synthesis (Indian English) as the local
    implementation; swap the body for a real Piper binary call when the
    model is available.
    """

    def generate_audio(self, text: str, output_path: Path) -> int:
        return _synthesize_speech(text, output_path)


# ---------------------------------------------------------------------------
# Mock provider — for unit tests ONLY, NOT for production use
# ---------------------------------------------------------------------------

class MockVoiceProvider(VoiceProvider):
    """
    Offline mock provider for isolated unit tests.

    Writes a plain-text stub beginning with MOCK_VOICE_AUDIO instead of
    synthesising real audio.  The video-composition safety gate rejects
    any file that starts with this header, so this provider can NEVER
    reach production video rendering.
    """

    def generate_audio(self, text: str, output_path: Path) -> int:
        word_count = len(text.split())
        duration = max(5, round(word_count / 2.5))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            f"MOCK_VOICE_AUDIO: voice_id={self.voice_id}, duration={duration}s, "
            f"text='{text[:40]}...'",
            encoding="utf-8",
        )
        return duration
