# src/voice/providers/mock.py
# Offline Mock Voice Provider — FOR UNIT TESTS ONLY

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.voice.providers.base import VoiceProvider


class MockVoiceProvider(VoiceProvider):
    """
    Offline mock provider for isolated unit tests.
    
    Writes a plain-text stub beginning with MOCK_VOICE_AUDIO.
    Explicitly classified as real_tts = False, mode = "test".
    The production video pipeline MUST reject any file/provider with real_tts == False.
    """

    def __init__(self, voice_id: str = "default"):
        super().__init__(
            provider_name="mock",
            voice_id=voice_id,
            real_tts=False,
            mode="test",
        )

    def generate_speech(
        self,
        text: str,
        output_path: Path,
        language_code: str = "hi-IN",
        voice_config: dict[str, Any] | None = None,
    ) -> int:
        word_count = len(text.split())
        duration = max(5, round(word_count / 2.5))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            f"MOCK_VOICE_AUDIO: voice_id={self.voice_id}, lang={language_code}, "
            f"duration={duration}s, text='{text[:40]}...'",
            encoding="utf-8",
        )
        return duration
