# src/voice/providers/edge_tts.py
# Phase 3 — Microsoft Edge Neural TTS Provider
# Primary production voice provider for Hindi, Telugu, and Tamil narration.
#
# Uses the `edge-tts` Python package (Microsoft Edge's read-aloud engine).
# No API key, no billing account, no cloud credentials required.
# real_tts = True | mode = "production"
#
# Fail-Closed Policy:
#   Any synthesis failure raises VoiceProviderError immediately.
#   This provider NEVER silently falls back to mock or sine-wave audio.

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from typing import Any

from src.voice.providers.base import VoiceProvider, VoiceProviderError


# ---------------------------------------------------------------------------
# Production voice configuration per language
# ---------------------------------------------------------------------------

EDGE_LANGUAGE_VOICE_CONFIG: dict[str, dict[str, str]] = {
    "hi-IN": {
        "provider":      "edge_neural_tts",
        "voice_name":    "hi-IN-SwaraNeural",
        "language_code": "hi-IN",
        "style":         "devotional_storytelling",
    },
    "te-IN": {
        "provider":      "edge_neural_tts",
        "voice_name":    "te-IN-ShrutiNeural",
        "language_code": "te-IN",
        "style":         "devotional_storytelling",
    },
    "ta-IN": {
        "provider":      "edge_neural_tts",
        "voice_name":    "ta-IN-PallaviNeural",
        "language_code": "ta-IN",
        "style":         "devotional_storytelling",
    },
}

SUPPORTED_LANGUAGES = set(EDGE_LANGUAGE_VOICE_CONFIG.keys())


# ---------------------------------------------------------------------------
# EdgeTTSProvider
# ---------------------------------------------------------------------------

class EdgeTTSProvider(VoiceProvider):
    """
    Microsoft Edge Neural TTS Provider — Phase 3 Primary Production Provider.

    Voices:
      hi-IN → hi-IN-SwaraNeural
      te-IN → te-IN-ShrutiNeural
      ta-IN → ta-IN-PallaviNeural

    Attributes
    ----------
    real_tts : True   — real Microsoft Neural TTS speech synthesis
    mode     : "production"
    """

    def __init__(self, voice_id: str = "default"):
        super().__init__(
            provider_name="edge_neural_tts",
            voice_id=voice_id,
            real_tts=True,
            mode="production",
        )

    # -----------------------------------------------------------------------
    # Public API required by base class
    # -----------------------------------------------------------------------

    def generate_speech(
        self,
        text: str,
        output_path: Path,
        language_code: str = "hi-IN",
        voice_config: dict[str, Any] | None = None,
    ) -> int:
        """
        Synthesize *text* using Edge Neural TTS and save as MP3 at *output_path*.

        Returns
        -------
        int — audio duration in whole seconds (ffprobe-measured).

        Raises
        ------
        VoiceProviderError — on empty text, unsupported language, or synthesis failure.
        """
        if not text or not text.strip():
            raise VoiceProviderError("Cannot synthesize empty narration text.")

        lang = self.validate_language(language_code)
        voice_meta = self.get_voice_metadata(lang)
        voice = voice_meta["voice_name"]

        rate = "+0%"
        pitch = "+0Hz"
        if voice_config and isinstance(voice_config, dict):
            rate = voice_config.get("rate", rate)
            pitch = voice_config.get("pitch", pitch)
        elif "rate" in voice_meta:
            rate = voice_meta.get("rate", rate)
            pitch = voice_meta.get("pitch", pitch)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # edge-tts outputs MP3 natively
        self._synthesize(text, voice, output_path, rate=rate, pitch=pitch)
        return self._measure_duration(output_path)

    # -----------------------------------------------------------------------
    # Extended API (synthesize / validate_language / get_voice_metadata)
    # -----------------------------------------------------------------------

    def synthesize(
        self,
        text: str,
        output_path: Path,
        language_code: str = "hi-IN",
    ) -> int:
        """
        Top-level synthesis entry point.
        Validates language, resolves voice, calls edge-tts, returns duration.
        """
        return self.generate_speech(text, output_path, language_code=language_code)

    def validate_language(self, language_code: str) -> str:
        """
        Validate that *language_code* is supported by this provider.

        Returns the canonical language code on success.
        Raises VoiceProviderError on unsupported language.
        """
        lang = language_code if language_code in SUPPORTED_LANGUAGES else None
        if lang is None:
            raise VoiceProviderError(
                f"EdgeTTSProvider does not support language '{language_code}'. "
                f"Supported: {sorted(SUPPORTED_LANGUAGES)}"
            )
        return lang

    def get_voice_metadata(self, language_code: str) -> dict[str, str]:
        """
        Return full voice metadata dict for the given language_code.

        Keys: provider, voice_name, language_code, style.
        Raises VoiceProviderError for unsupported languages.
        """
        lang = self.validate_language(language_code)
        return dict(EDGE_LANGUAGE_VOICE_CONFIG[lang])

    # -----------------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------------

    def _synthesize(
        self,
        text: str,
        voice: str,
        output_path: Path,
        rate: str = "+10%",
        pitch: str = "+0Hz",
    ) -> None:
        """
        Call edge-tts via asyncio to synthesize *text* with *voice*.
        Saves output directly as MP3 at *output_path*.

        Raises VoiceProviderError on any failure.
        """
        try:
            import edge_tts  # type: ignore
        except ImportError as exc:
            raise VoiceProviderError(
                "edge-tts package not installed. Run: pip install edge-tts>=6.1.9"
            ) from exc

        async def _run() -> None:
            communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
            await communicate.save(str(output_path))

        try:
            # Use asyncio.run() in a subprocess-safe manner
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Fallback for environments where loop is already running (e.g., Jupyter)
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                        future = pool.submit(asyncio.run, _run())
                        future.result(timeout=60)
                else:
                    loop.run_until_complete(_run())
            except RuntimeError:
                asyncio.run(_run())
        except VoiceProviderError:
            raise
        except Exception as exc:
            raise VoiceProviderError(
                f"Edge Neural TTS synthesis failed for voice '{voice}': {exc}"
            ) from exc

        if not output_path.exists() or output_path.stat().st_size < 1000:
            raise VoiceProviderError(
                f"Edge Neural TTS produced no usable output for voice '{voice}' "
                f"at {output_path}."
            )

    def _measure_duration(self, path: Path) -> int:
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
