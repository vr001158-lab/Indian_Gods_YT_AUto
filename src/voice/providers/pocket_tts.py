# src/voice/providers/pocket_tts.py
# Phase 3 — Pocket TTS Telugu Voice Provider
# Model: prasadvittaldev/pocket-tts-telugu-female-syspin
# Architecture: Kyutai Pocket TTS (~0.1B parameters)
# Training Dataset: IISc SPIRE Lab SYSPIN Telugu Female (CC-BY-4.0)
#
# Production voice provider for Telugu (te-IN) narration.
# Offline, CPU-executable, 24kHz mono PCM WAV output.
#
# Fail-Closed Policy:
#   Any synthesis failure raises VoiceProviderError immediately.
#   Never falls back silently to fake or mock audio.

from __future__ import annotations

import logging
from pathlib import Path
import re
import subprocess
from typing import Any

from src.voice.providers.base import VoiceProvider, VoiceProviderError, _get_audio_duration

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration & Voice Mapping
# ---------------------------------------------------------------------------

POCKET_TTS_CONFIG: dict[str, Any] = {
    "provider": "pocket_tts",
    "voice_name": "syspin_female",
    "language_code": "te-IN",
    "sample_rate": 24000,
    "channels": 1,
    "config_uri": "hf://prasadvittaldev/pocket-tts-telugu-female-syspin/config.yaml",
    "voice_prompt_uri": "hf://prasadvittaldev/pocket-tts-telugu-female-syspin/voice_prompt.wav",
    "style": "devotional_storytelling",
}

POCKET_TTS_LANGUAGE_VOICE_CONFIG: dict[str, dict[str, Any]] = {
    "te-IN": POCKET_TTS_CONFIG,
}

# ---------------------------------------------------------------------------
# Telugu Text Normalization Helpers
# ---------------------------------------------------------------------------

TELUGU_NUMERALS_MAP = {
    "౦": "0", "౧": "1", "౨": "2", "౩": "3", "౪": "4",
    "౫": "5", "౬": "6", "౭": "7", "౮": "8", "౯": "9",
}

TELUGU_WORDS_0_TO_19 = {
    0: "సున్నా", 1: "ఒకటి", 2: "రెండు", 3: "మూడు", 4: "నాలుగు",
    5: "ఐదు", 6: "ఆరు", 7: "ఏడు", 8: "ఎనిమిది", 9: "తొమ్మిది",
    10: "పది", 11: "పదకొండు", 12: "పన్నెండు", 13: "పదమూడు", 14: "పద్నాలుగు",
    15: "పదిహేను", 16: "పదహారు", 17: "పదిహేడు", 18: "పద్దెనిమిది", 19: "పందొమ్మిది",
}

TELUGU_TENS = {
    20: "ఇరవై", 30: "ముప్పై", 40: "నలభై", 50: "యాభై",
    60: "అరవై", 70: "డెబ్బై", 80: "ఎనభై", 90: "తొంభై",
}


def number_to_telugu_words(num: int) -> str:
    """Converts a non-negative integer into standard Telugu spoken words."""
    if num < 0:
        return "మైనస్ " + number_to_telugu_words(-num)
    if num in TELUGU_WORDS_0_TO_19:
        return TELUGU_WORDS_0_TO_19[num]
    if num < 100:
        tens = (num // 10) * 10
        rem = num % 10
        if rem == 0:
            return TELUGU_TENS[tens]
        return f"{TELUGU_TENS[tens]} {TELUGU_WORDS_0_TO_19[rem]}"
    if num < 1000:
        hundreds = num // 100
        rem = num % 100
        h_word = "వంద" if hundreds == 1 else f"{TELUGU_WORDS_0_TO_19.get(hundreds, str(hundreds))} వందలు"
        if rem == 0:
            return h_word
        return f"{h_word} {number_to_telugu_words(rem)}"
    if num < 100000:
        thousands = num // 1000
        rem = num % 1000
        t_word = "వెయ్యి" if thousands == 1 else f"{number_to_telugu_words(thousands)} వేలు"
        if rem == 0:
            return t_word
        return f"{t_word} {number_to_telugu_words(rem)}"
    if num < 10000000:
        lakhs = num // 100000
        rem = num % 100000
        l_word = "లక్ష" if lakhs == 1 else f"{number_to_telugu_words(lakhs)} లక్షలు"
        if rem == 0:
            return l_word
        return f"{l_word} {number_to_telugu_words(rem)}"
    crores = num // 10000000
    rem = num % 10000000
    c_word = "కోటి" if crores == 1 else f"{number_to_telugu_words(crores)} కోట్లు"
    if rem == 0:
        return c_word
    return f"{c_word} {number_to_telugu_words(rem)}"


def _replace_digit_match(match: re.Match) -> str:
    val = match.group(0)
    try:
        n = int(val)
        return number_to_telugu_words(n)
    except Exception:
        # Fallback to single digit conversion
        return " ".join(TELUGU_WORDS_0_TO_19.get(int(d), d) for d in val)


def normalize_telugu_text(
    text: str,
    latin_policy: str = "warn",
    strip_latin: bool | None = None,
) -> str:
    """
    Normalizes Telugu text for Pocket TTS inference:
      1. Translates Telugu numerals (౦-౯) to ASCII digits.
      2. Expands Arabic digits (0-9) into natural Telugu spoken words.
      3. Handles Latin / English characters according to latin_policy:
         - "warn" (default): Preserves Latin text intact in narration, logs a warning alerting that
           Latin words are out of the Telugu acoustic model vocabulary.
         - "preserve": Preserves Latin text intact without logging any warning.
         - "strip": Removes Latin words (replacing with single space) after logging a warning.
         (If legacy strip_latin boolean is passed, it takes precedence: True -> "strip", False -> "preserve").
      4. Normalizes whitespace and punctuation.
    """
    if not text:
        return ""

    if strip_latin is not None:
        policy = "strip" if strip_latin else "preserve"
    else:
        policy = (latin_policy or "warn").lower().strip()

    if policy not in ("warn", "preserve", "strip"):
        raise ValueError(
            f"Invalid latin_policy '{latin_policy}'. Must be 'warn', 'preserve', or 'strip'."
        )

    # 1. Map Telugu numerals to Arabic digits
    for t_char, d_char in TELUGU_NUMERALS_MAP.items():
        text = text.replace(t_char, d_char)

    # 2. Expand numbers to Telugu words
    text = re.sub(r"\d+", _replace_digit_match, text)

    # 3. Detect and handle Latin / English words
    latin_matches = re.findall(r"[A-Za-z]+", text)
    if latin_matches:
        if policy in ("warn", "strip"):
            logger.warning(
                "PocketTTS Telugu: unhandled Latin text encountered (%s): %s",
                policy,
                ", ".join(repr(m) for m in latin_matches[:5]),
            )
        if policy == "strip":
            text = re.sub(r"[A-Za-z]+", " ", text)

    # 4. Normalize whitespaces
    text = re.sub(r"[ \t]+", " ", text).strip()
    return text


def split_into_sentences(text: str, max_chars: int = 150) -> list[str]:
    """
    Splits Telugu narration text into sentence-sized chunks suitable for Pocket TTS.
    Prevents token truncation and ensures high acoustic quality.
    """
    if not text or not text.strip():
        return []

    # Split by standard sentence delimiters (periods, Danda, double Danda, exclamation, question mark, newline)
    raw_chunks = re.split(r"([।॥\.\?\!\n;]+)", text)
    sentences: list[str] = []
    current_sentence = ""

    for part in raw_chunks:
        if not part:
            continue
        if re.match(r"^[।॥\.\?\!\n;]+$", part):
            current_sentence += part
            cleaned = current_sentence.strip()
            if cleaned:
                sentences.append(cleaned)
            current_sentence = ""
        else:
            if current_sentence:
                current_sentence += " " + part
            else:
                current_sentence = part

    if current_sentence.strip():
        sentences.append(current_sentence.strip())

    # Ensure no individual sentence exceeds max_chars
    final_chunks: list[str] = []
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        if len(s) <= max_chars:
            final_chunks.append(s)
        else:
            # Sub-split on commas or conjunctions or whitespace
            sub_parts = re.split(r"([,،\s]+)", s)
            accum = ""
            for sp in sub_parts:
                if len(accum) + len(sp) > max_chars and accum.strip():
                    final_chunks.append(accum.strip())
                    accum = sp
                else:
                    accum += sp
            if accum.strip():
                final_chunks.append(accum.strip())

    return final_chunks


# ---------------------------------------------------------------------------
# PocketTTSProvider
# ---------------------------------------------------------------------------

class PocketTTSProvider(VoiceProvider):
    """
    Pocket TTS Telugu Voice Provider (Female, IISc SYSPIN).
    Model Checkpoint: prasadvittaldev/pocket-tts-telugu-female-syspin

    Attributes
    ----------
    real_tts : True   — Real neural acoustic generation
    mode     : "production"
    """

    _cached_model: Any = None
    _cached_state: Any = None
    _cached_config_uri: str = ""
    _cached_voice_prompt_uri: str = ""

    def __init__(self, voice_id: str = "syspin_female", mode: str = "production"):
        super().__init__(
            provider_name="pocket_tts",
            voice_id=voice_id or "syspin_female",
            real_tts=True,
            mode=mode,
        )

    @classmethod
    def _get_model_and_state(cls, config_uri: str, voice_prompt_uri: str) -> tuple[Any, Any]:
        """Loads and caches the TTSModel and voice prompt state in memory."""
        try:
            from pocket_tts import TTSModel
        except ImportError as exc:
            raise VoiceProviderError(
                "Pocket TTS is not installed. Run 'pip install pocket-tts' to enable this provider."
            ) from exc

        if cls._cached_model is None or cls._cached_config_uri != config_uri:
            try:
                cls._cached_model = TTSModel.load_model(config=config_uri)
                cls._cached_config_uri = config_uri
                cls._cached_state = None
            except Exception as exc:
                raise VoiceProviderError(
                    f"Failed to load Pocket TTS model checkpoint from '{config_uri}': {exc}"
                ) from exc

        if cls._cached_state is None or cls._cached_voice_prompt_uri != voice_prompt_uri:
            try:
                cls._cached_state = cls._cached_model.get_state_for_audio_prompt(voice_prompt_uri)
                cls._cached_voice_prompt_uri = voice_prompt_uri
            except Exception as exc:
                raise VoiceProviderError(
                    f"Failed to load Pocket TTS voice prompt from '{voice_prompt_uri}': {exc}"
                ) from exc

        return cls._cached_model, cls._cached_state

    def generate_speech(
        self,
        text: str,
        output_path: Path,
        language_code: str = "te-IN",
        voice_config: dict[str, Any] | None = None,
    ) -> int:
        """
        Synthesize Telugu *text* using Pocket TTS and save as 24kHz mono WAV to *output_path*.

        Returns
        -------
        int — audio duration in whole seconds.

        Raises
        ------
        VoiceProviderError — on empty text, unsupported language, or generation failure.
        """
        if not text or not str(text).strip():
            raise VoiceProviderError("Narration text is empty.")

        if language_code != "te-IN":
            raise VoiceProviderError(
                f"Unsupported language '{language_code}' for Pocket TTS. Only 'te-IN' (Telugu) is supported."
            )

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        config = dict(POCKET_TTS_CONFIG)
        if isinstance(voice_config, dict):
            config.update(voice_config)

        config_uri = config.get("config_uri", POCKET_TTS_CONFIG["config_uri"])
        voice_prompt_uri = config.get("voice_prompt_uri", POCKET_TTS_CONFIG["voice_prompt_uri"])
        latin_policy = config.get("latin_policy", "warn")

        # 1. Normalize text
        normalized = normalize_telugu_text(text, latin_policy=latin_policy)
        if not normalized:
            raise VoiceProviderError("Telugu text was empty after normalization.")

        # 2. Chunk text into sentence-sized pieces
        chunks = split_into_sentences(normalized)
        if not chunks:
            raise VoiceProviderError("Failed to extract sentence chunks from Telugu text.")

        # 3. Load model and voice prompt state
        model, voice_state = self._get_model_and_state(config_uri, voice_prompt_uri)
        sample_rate = getattr(model, "sample_rate", None) or config.get("sample_rate", 24000)

        # 4. Generate audio per chunk
        try:
            import torch
            audio_tensors: list[torch.Tensor] = []
            for chunk in chunks:
                chunk_tensor = model.generate_audio(voice_state, chunk)
                if chunk_tensor is not None and chunk_tensor.numel() > 0:
                    chunk_1d = chunk_tensor.detach().cpu().squeeze()
                    if chunk_1d.ndim == 0:
                        chunk_1d = chunk_1d.unsqueeze(0)
                    audio_tensors.append(chunk_1d)

            if not audio_tensors:
                raise VoiceProviderError("Pocket TTS generated empty audio tensors.")

            # Concatenate chunks sequentially along time dimension
            full_audio = torch.cat(audio_tensors, dim=0)
            audio_np = full_audio.numpy()
        except VoiceProviderError:
            raise
        except Exception as exc:
            raise VoiceProviderError(f"Pocket TTS inference failed: {exc}") from exc

        # 5. Write valid 24kHz mono 16-bit PCM WAV file
        try:
            self._write_audio_file(output_path, audio_np, sample_rate)
        except Exception as exc:
            raise VoiceProviderError(f"Failed to write audio output file '{output_path}': {exc}") from exc

        # 6. Measure audio duration via ffprobe
        duration = _get_audio_duration(output_path)
        return max(1, duration)

    @staticmethod
    def _write_audio_file(output_path: Path, audio_np: Any, sample_rate: int) -> None:
        """Writes audio samples to output_path. Supports WAV directly or converts if needed."""
        import numpy as np

        audio_np = np.asarray(audio_np, dtype=np.float32)
        if audio_np.ndim > 1:
            audio_np = audio_np.squeeze()

        # If output_path asks for mp3, write wav first then encode, or write directly
        target_suffix = output_path.suffix.lower()
        wav_target = output_path if target_suffix == ".wav" else output_path.with_suffix(".wav")

        try:
            import soundfile as sf
            sf.write(str(wav_target), audio_np, sample_rate, format="WAV", subtype="PCM_16")
        except Exception:
            # Fallback to standard library wave
            import wave
            audio_clamped = np.clip(audio_np, -1.0, 1.0)
            int16_data = (audio_clamped * 32767).astype(np.int16)
            with wave.open(str(wav_target), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(int16_data.tobytes())

        if target_suffix == ".mp3" and wav_target != output_path:
            try:
                subprocess.run(
                    [
                        "ffmpeg", "-y", "-v", "error",
                        "-i", str(wav_target),
                        "-c:a", "mp3", "-b:a", "128k",
                        str(output_path),
                    ],
                    check=True,
                )
                if wav_target.exists():
                    wav_target.unlink()
            except Exception:
                # If ffmpeg is not available, move wav_target to output_path (ffprobe accepts RIFF PCM regardless of extension)
                if wav_target.exists() and not output_path.exists():
                    wav_target.rename(output_path)
