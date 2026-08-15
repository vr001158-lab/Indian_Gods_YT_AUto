# src/voice/providers/google_chirp.py
# Real Production TTS Engine: Google Cloud Text-to-Speech Chirp 3 HD / Neural2

from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from pathlib import Path
from typing import Any

from src.voice.providers.base import VoiceProvider, VoiceProviderError, _synthesize_speech

# Production voice mapping per language
LANGUAGE_VOICE_CONFIG: dict[str, dict[str, str]] = {
    "hi-IN": {
        "provider": "google_chirp3_hd",
        "voice_name": "hi-IN-Chirp3-HD-D",
        "ssml_gender": "MALE",
        "style": "devotional_storytelling",
    },
    "te-IN": {
        "provider": "google_chirp3_hd",
        "voice_name": "te-IN-Chirp3-HD-A",
        "ssml_gender": "MALE",
        "style": "devotional_storytelling",
    },
    "ta-IN": {
        "provider": "google_chirp3_hd",
        "voice_name": "ta-IN-Chirp3-HD-A",
        "ssml_gender": "MALE",
        "style": "devotional_storytelling",
    },
}


class GoogleChirpTTSProvider(VoiceProvider):
    """
    Production Google Cloud Text-to-Speech Provider (Chirp 3 HD).
    
    Supports:
      - hi-IN (Hindi)
      - te-IN (Telugu)
      - ta-IN (Tamil)
      
    Fail-Closed Policy:
      If Google Cloud credentials are missing or invalid, raises VoiceProviderError.
      NEVER falls back silently to mock audio.
    """

    def __init__(self, voice_id: str = "default"):
        super().__init__(
            provider_name="google_chirp3_hd",
            voice_id=voice_id,
            real_tts=True,
            mode="production",
        )

    def _get_access_token(self) -> str:
        """
        Obtain OAuth access token from environment or Google Credentials.
        Raises VoiceProviderError if credentials are not available.
        """
        api_key = os.environ.get("GOOGLE_CLOUD_TTS_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
        if api_key:
            return f"API_KEY:{api_key}"

        cred_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
        if cred_path and Path(cred_path).exists():
            try:
                import google.auth
                import google.auth.transport.requests
                creds, _ = google.auth.load_credentials_from_file(
                    cred_path,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )
                req = google.auth.transport.requests.Request()
                creds.refresh(req)
                if creds.token:
                    return creds.token
            except Exception as e:
                raise VoiceProviderError(f"Google Cloud credentials load failed: {e}") from e

        try:
            import google.auth
            import google.auth.transport.requests
            creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
            req = google.auth.transport.requests.Request()
            creds.refresh(req)
            if creds.token:
                return creds.token
        except Exception:
            pass

        raise VoiceProviderError("Google Cloud TTS credentials unavailable.")

    def generate_speech(
        self,
        text: str,
        output_path: Path,
        language_code: str = "hi-IN",
        voice_config: dict[str, Any] | None = None,
    ) -> int:
        if not text or not text.strip():
            raise VoiceProviderError("Cannot synthesize empty narration text.")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        lang = language_code if language_code in LANGUAGE_VOICE_CONFIG else "hi-IN"
        config = voice_config or LANGUAGE_VOICE_CONFIG[lang]
        voice_name = config.get("voice_name", "hi-IN-Chirp3-HD-D")

        token = self._get_access_token()

        payload = {
            "input": {"text": text},
            "voice": {
                "languageCode": lang,
                "name": voice_name,
                "ssmlGender": config.get("ssml_gender", "MALE"),
            },
            "audioConfig": {
                "audioEncoding": "MP3",
                "speakingRate": 0.95,
                "pitch": -1.0,
            },
        }

        data_bytes = json.dumps(payload).encode("utf-8")

        if token.startswith("API_KEY:"):
            key_val = token.split(":", 1)[1]
            url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={key_val}"
            req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json"})
        else:
            url = "https://texttospeech.googleapis.com/v1/text:synthesize"
            req = urllib.request.Request(
                url,
                data=data_bytes,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
            )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            
            audio_b64 = result.get("audioContent", "")
            if not audio_b64:
                raise VoiceProviderError("Google Cloud TTS returned empty audio content.")

            import base64
            audio_data = base64.b64decode(audio_b64)
            output_path.write_bytes(audio_data)
        except VoiceProviderError:
            raise
        except Exception as exc:
            raise VoiceProviderError(f"Google Cloud TTS API execution failed: {exc}") from exc

        return self._measure_duration(output_path)

    def _measure_duration(self, path: Path) -> int:
        try:
            res = subprocess.run(
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
            return max(1, round(float(res.stdout.strip())))
        except Exception:
            return 5


class GTTSSpeechProvider(VoiceProvider):
    """gTTS placeholder — TEST ONLY. Not acceptable for production narration."""
    def __init__(self, voice_id: str = "default"):
        super().__init__(provider_name="gtts", voice_id=voice_id, real_tts=False, mode="test")

    def generate_speech(self, text: str, output_path: Path, language_code: str = "hi-IN", voice_config: dict[str, Any] | None = None) -> int:
        return _synthesize_speech(text, output_path)


class ElevenLabsProvider(VoiceProvider):
    """ElevenLabs placeholder — TEST ONLY. Routes to offline sine-wave stub."""
    def __init__(self, voice_id: str = "default"):
        super().__init__(provider_name="elevenlabs", voice_id=voice_id, real_tts=False, mode="test")

    def generate_speech(self, text: str, output_path: Path, language_code: str = "hi-IN", voice_config: dict[str, Any] | None = None) -> int:
        return _synthesize_speech(text, output_path)


class KokoroProvider(VoiceProvider):
    """Kokoro placeholder — TEST ONLY. Routes to offline sine-wave stub."""
    def __init__(self, voice_id: str = "default"):
        super().__init__(provider_name="kokoro", voice_id=voice_id, real_tts=False, mode="test")

    def generate_speech(self, text: str, output_path: Path, language_code: str = "hi-IN", voice_config: dict[str, Any] | None = None) -> int:
        return _synthesize_speech(text, output_path)


class PiperProvider(VoiceProvider):
    """Piper placeholder — TEST ONLY. Routes to offline sine-wave stub."""
    def __init__(self, voice_id: str = "default"):
        super().__init__(provider_name="piper", voice_id=voice_id, real_tts=False, mode="test")

    def generate_speech(self, text: str, output_path: Path, language_code: str = "hi-IN", voice_config: dict[str, Any] | None = None) -> int:
        return _synthesize_speech(text, output_path)
