# src/voice/providers/__init__.py
# Voice Provider Package Exports

from src.voice.providers.base import VoiceProvider, VoiceProviderError, _get_audio_duration, _synthesize_speech
from src.voice.providers.google_chirp import (
    GoogleChirpTTSProvider,
    GTTSSpeechProvider,
    ElevenLabsProvider,
    KokoroProvider,
    PiperProvider,
    LANGUAGE_VOICE_CONFIG,
)
from src.voice.providers.azure_neural import AzureNeuralTTSProvider
from src.voice.providers.edge_tts import EdgeTTSProvider, EDGE_LANGUAGE_VOICE_CONFIG
from src.voice.providers.mock import MockVoiceProvider

__all__ = [
    "VoiceProvider",
    "VoiceProviderError",
    "GoogleChirpTTSProvider",
    "AzureNeuralTTSProvider",
    "EdgeTTSProvider",
    "MockVoiceProvider",
    "ElevenLabsProvider",
    "GTTSSpeechProvider",
    "KokoroProvider",
    "PiperProvider",
    "LANGUAGE_VOICE_CONFIG",
    "EDGE_LANGUAGE_VOICE_CONFIG",
    "_get_audio_duration",
    "_synthesize_speech",
]
