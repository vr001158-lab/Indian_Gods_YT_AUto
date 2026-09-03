# src/voice/generator.py
# Phase 3 — Voice Generation Engine Module
#
# Primary production provider: edge_neural_tts (Microsoft Edge Neural TTS)
# Future premium provider:     google_chirp3_hd (Google Chirp 3 HD, billing-gated)
#
# Production fallback chain (fail-closed at each step — never silent):
#   edge_neural_tts → indic_tts → kokoro → piper
#
# Every generated audio file records:
#   provider, voice_name, language_code, real_tts, mode

import json
import time
from pathlib import Path

from src.voice.schemas import validate_script_input, validate_audio_output, PRODUCTION_PROVIDERS
from src.voice.qa import perform_audio_qa, AudioValidationError
from src.voice.providers import (
    AzureNeuralTTSProvider,
    EdgeTTSProvider,
    ElevenLabsProvider,
    GTTSSpeechProvider,
    GoogleChirpTTSProvider,
    KokoroProvider,
    MockVoiceProvider,
    PiperProvider,
    VoiceProviderError,
    LANGUAGE_VOICE_CONFIG,
    EDGE_LANGUAGE_VOICE_CONFIG,
)

# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

# Primary production provider for Phase 3
PRODUCTION_PROVIDER = "edge_neural_tts"

PROVIDERS = {
    "edge_neural_tts":   EdgeTTSProvider,       # PRIMARY — Microsoft Edge Neural TTS
    "google_chirp3_hd":  GoogleChirpTTSProvider, # FUTURE PREMIUM — Google Chirp 3 HD
    "azure_neural":      AzureNeuralTTSProvider,
    "elevenlabs":        ElevenLabsProvider,
    "gtts":              GTTSSpeechProvider,
    "kokoro":            KokoroProvider,
    "piper":             PiperProvider,
    "mock":              MockVoiceProvider,
}

# Production fallback chain (ordered — each tried only if the previous raises)
# All providers in this chain must be real_tts=True / mode=production.
PRODUCTION_FALLBACK_CHAIN = [
    "edge_neural_tts",
    "kokoro",
    "piper",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_silent_wav_bytes(duration_seconds: int, sample_rate: int = 24000) -> bytes:
    """
    Generate a valid WAV file containing pure silence, using only the Python
    standard library (no FFmpeg, no external packages required).

    Returns raw bytes that form a syntactically correct RIFF/PCM WAV container.
    FFmpeg and ffprobe recognise these bytes as a valid audio stream regardless
    of the filename extension.
    """
    import io
    import wave as _wave
    buf = io.BytesIO()
    with _wave.open(buf, "wb") as w:
        w.setnchannels(1)          # mono
        w.setsampwidth(2)          # 16-bit
        w.setframerate(sample_rate)
        # Write silence — sample_rate * bytes_per_sample * duration frames of zeros
        w.writeframes(b"\x00" * (sample_rate * 2 * max(1, duration_seconds)))
    return buf.getvalue()


def _resolve_language(script: dict) -> str:
    return script.get("language_code") or "hi-IN"


def _resolve_voice_config(script: dict, language_code: str, provider_name: str) -> dict:
    """
    Resolve the voice config for the active provider and language.
    Edge TTS always uses its own internal voice map (not the script's chirp config).
    """
    if provider_name == "edge_neural_tts":
        return EDGE_LANGUAGE_VOICE_CONFIG.get(
            language_code,
            EDGE_LANGUAGE_VOICE_CONFIG["hi-IN"],
        )
    if isinstance(script.get("voice_config"), dict):
        return script["voice_config"]
    return LANGUAGE_VOICE_CONFIG.get(language_code, LANGUAGE_VOICE_CONFIG["hi-IN"])


def _enforce_production_provider(provider_name: str, mode: str) -> None:
    """
    In production mode, only providers in PRODUCTION_PROVIDERS are allowed.
    Raises ValueError for fake/test providers.
    """
    if mode != "production":
        return
    if provider_name not in PRODUCTION_PROVIDERS:
        raise ValueError(
            f"Production mode requires a production provider "
            f"(got '{provider_name}', accepted: {sorted(PRODUCTION_PROVIDERS)})."
        )


def _enforce_provider_metadata(provider, mode: str) -> None:
    """Reject any provider that has real_tts=False in production mode."""
    if mode != "production":
        return
    if not provider.real_tts:
        raise ValueError(
            f"Production generation rejected: provider '{provider.provider_name}' "
            f"has real_tts=False (test-only placeholder)."
        )
    if provider.mode != "production":
        raise ValueError(
            f"Production generation rejected: provider '{provider.provider_name}' "
            f"has mode='{provider.mode}'."
        )


def _validate_production_audio(path: Path, *, allow_mock: bool) -> dict:
    try:
        return perform_audio_qa(path, allow_mock=allow_mock)
    except AudioValidationError as exc:
        raise VoiceProviderError(f"Generated audio failed validation: {exc}") from exc


def _try_fallback_chain(
    text: str,
    output_path: Path,
    language_code: str,
    voice_config: dict,
    primary_name: str,
) -> tuple[str, int]:
    """
    Attempt synthesis through the production fallback chain.
    Returns (provider_name_used, duration_seconds).
    Raises VoiceProviderError if ALL providers in the chain fail.
    Never silently produces mock/fake audio.
    """
    errors = []
    for name in PRODUCTION_FALLBACK_CHAIN:
        if name not in PROVIDERS:
            continue
        provider = PROVIDERS[name](voice_id="default")
        # Only attempt providers that are real_tts=True
        if not provider.real_tts:
            continue
        try:
            vc = EDGE_LANGUAGE_VOICE_CONFIG.get(language_code, EDGE_LANGUAGE_VOICE_CONFIG["hi-IN"]) \
                if name == "edge_neural_tts" else voice_config
            duration = provider.generate_speech(
                text, output_path,
                language_code=language_code,
                voice_config=vc,
            )
            return name, duration
        except Exception as exc:
            errors.append(f"{name}: {exc}")
            continue

    raise VoiceProviderError(
        f"All production providers in fallback chain failed for language '{language_code}'.\n"
        + "\n".join(errors)
    )


# ---------------------------------------------------------------------------
# Core generation function
# ---------------------------------------------------------------------------

def generate_voice_mapping(
    script: dict,
    provider_name: str | None = None,
    voice_id: str = "default",
    output_dir: Path = Path("data/audio"),
    mode: str = "production",
    content_type: str = "short",
    format: str = "narrated",
) -> dict:
    """
    Synthesizes speech for both full narration and individual scenes.
    Creates a synchronized mapping file of scenes to audio outputs.

    Production mode (default):
      - provider MUST be edge_neural_tts (or google_chirp3_hd for premium)
      - real_tts MUST be True
      - fails closed if provider unavailable or audio invalid
      - attempts fallback chain if primary fails

    Old format mode (format="old"):
      - Bypasses TTS voice generation completely (zero TTS calls)
      - Selects verified devotional music track and constructs music-only audio map
    """
    fmt = (format or script.get("format") or "narrated").lower()
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    run_audio_dir = output_dir / f"run_{timestamp}"
    run_audio_dir.mkdir(parents=True, exist_ok=True)

    if fmt == "old":
        from src.audio.music import (
            select_background_music_v2,
            validate_music_provenance,
            get_bgm_metadata_for_track,
        )
        music_track, sel_type = select_background_music_v2(category="devotional", script=script)
        bgm_meta = get_bgm_metadata_for_track(music_track, script=script)
        
        # Determine music file path and validate in production
        if mode == "production":
            if not music_track:
                raise ValueError("No approved devotional music track could be selected for old format.")
            is_ok, reason, track_info = validate_music_provenance(music_track)
            if not is_ok:
                raise ValueError(f"Selected music track failed provenance check: {reason}")
            if not music_track.exists() or music_track.stat().st_size == 0:
                raise ValueError(f"Selected music track file is missing or empty: {music_track}")
            try:
                perform_audio_qa(music_track, allow_mock=False)
            except Exception as exc:
                raise ValueError(f"Selected music track failed audio QA check: {exc}")
            full_audio_file = music_track
        else:
            if music_track and music_track.exists():
                is_ok, _, _ = validate_music_provenance(music_track)
                if is_ok:
                    full_audio_file = music_track
                else:
                    full_audio_file = run_audio_dir / "devotional_music_30s.wav"
                    if not full_audio_file.exists():
                        full_audio_file.write_bytes(_make_silent_wav_bytes(30))
            else:
                full_audio_file = run_audio_dir / "devotional_music_30s.wav"
                if not full_audio_file.exists():
                    full_audio_file.write_bytes(_make_silent_wav_bytes(30))

        topic = script.get("title") or script.get("approval_metadata", {}).get("selected_topic", "")
        from src.assets.selector import resolve_deity, build_deity_visual_timeline
        deity = resolve_deity(topic)

        content_type = (script.get("content_type") or "short").lower()
        target_total_dur = float(script.get("duration_seconds") or script.get("total_duration_seconds") or 45.0)
        if content_type == "short" and (target_total_dur < 35.0 or target_total_dur >= 60.0):
            target_total_dur = 45.0

        timeline_scenes = build_deity_visual_timeline(deity, target_duration=target_total_dur, content_type=content_type)

        allow_mock = mode == "test"
        audio_scenes = []
        total_duration = 0.0
        for i, sc in enumerate(timeline_scenes):
            scene_num = sc["scene"]
            dur = sc["duration_seconds"]
            total_duration += dur
            scene_file = run_audio_dir / f"scene_{scene_num}.wav"
            if not scene_file.exists():
                scene_file.write_bytes(_make_silent_wav_bytes(int(dur) or 1))

            if mode == "production":
                _validate_production_audio(scene_file, allow_mock=allow_mock)

            audio_scenes.append({
                "scene": scene_num,
                "voice_text": script.get("title") or "Devotional Dharshanam",
                "audio_file": str(scene_file.absolute()).replace("\\", "/"),
                "duration_seconds": int(round(dur)),
            })

        if mode == "production":
            _validate_production_audio(full_audio_file, allow_mock=allow_mock)

        run_id = script.get("run_id") or f"run_{timestamp}_OLD"
        audio_map = {
            "run_id": run_id,
            "format": "old",
            "audio_type": "music_only",
            "script_title": script.get("title", "Devotional Short"),
            "total_duration_seconds": int(round(total_duration)),
            "provider": "devotional_music",
            "voice_name": "none",
            "language_code": _resolve_language(script),
            "real_tts": True,
            "mode": mode,
            "audio_scenes": audio_scenes,
            "full_narration_audio_file": str(full_audio_file.absolute()).replace("\\", "/"),
            "bgm_title": bgm_meta.get("title", "Devotional Music"),
            "bgm_artist": bgm_meta.get("artist", "Traditional / Various Artists"),
            "bgm_deity": bgm_meta.get("deity", "devotional"),
            "approval_metadata": script.get("approval_metadata", {}),
        }

        ok_out, err_out = validate_audio_output(audio_map)
        if not ok_out:
            raise RuntimeError(f"❌ Internal Error: Generated old-format audio mapping fails schema: {err_out}")

        return audio_map

    ok, error_msg = validate_script_input(script, content_type=content_type)
    if not ok:
        raise ValueError(f"❌ Safety Gate Rejection: {error_msg}")

    if mode not in ("production", "test"):
        raise ValueError("mode must be 'production' or 'test'")

    provider_name = provider_name or (PRODUCTION_PROVIDER if mode == "production" else "mock")
    _enforce_production_provider(provider_name, mode)

    if provider_name not in PROVIDERS:
        raise ValueError(
            f"Unknown voice provider: {provider_name} "
            f"(must be one of {list(PROVIDERS.keys())})"
        )

    provider = PROVIDERS[provider_name](voice_id=voice_id)
    _enforce_provider_metadata(provider, mode)

    language_code = _resolve_language(script)
    voice_config = _resolve_voice_config(script, language_code, provider_name)
    voice_name = voice_config.get("voice_name", "")

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    run_audio_dir = output_dir / f"run_{timestamp}"
    run_audio_dir.mkdir(parents=True, exist_ok=True)

    allow_mock = mode == "test"
    audio_scenes = []
    total_duration = 0

    for item in script["scene_scripts"]:
        scene_num = item["scene"]
        text = item.get("voice_text") or item.get("narration_text") or item.get("narration", "")
        if not text or not str(text).strip():
            raise ValueError(f"Scene {scene_num} has empty narration text.")

        scene_file = run_audio_dir / f"scene_{scene_num}.mp3"

        if mode == "production":
            # Attempt primary provider with automatic fallback chain
            try:
                duration = provider.generate_speech(
                    text, scene_file,
                    language_code=language_code,
                    voice_config=voice_config,
                )
                used_provider = provider_name
            except VoiceProviderError as primary_exc:
                # Primary failed — try fallback chain (all real_tts=True only)
                if provider_name == PRODUCTION_FALLBACK_CHAIN[0]:
                    # Already starting from top of chain
                    used_provider, duration = _try_fallback_chain(
                        text, scene_file, language_code, voice_config, provider_name
                    )
                else:
                    raise
        else:
            duration = provider.generate_speech(
                text, scene_file,
                language_code=language_code,
                voice_config=voice_config,
            )
            used_provider = provider_name

        if mode == "production":
            _validate_production_audio(scene_file, allow_mock=allow_mock)

        total_duration += duration
        audio_scenes.append({
            "scene": scene_num,
            "voice_text": text,
            "audio_file": str(scene_file.absolute()).replace("\\", "/"),
            "duration_seconds": duration,
        })

    full_audio_file = run_audio_dir / "full_narration.mp3"
    if mode == "production":
        try:
            provider.generate_speech(
                script["narration"], full_audio_file,
                language_code=language_code,
                voice_config=voice_config,
            )
        except VoiceProviderError:
            if provider_name == PRODUCTION_FALLBACK_CHAIN[0]:
                _try_fallback_chain(
                    script["narration"], full_audio_file, language_code, voice_config, provider_name
                )
            else:
                raise
        full_audio_qa = _validate_production_audio(full_audio_file, allow_mock=allow_mock)
    else:
        provider.generate_speech(
            script["narration"], full_audio_file,
            language_code=language_code,
            voice_config=voice_config,
        )
        full_audio_qa = None

    run_id = script.get("run_id") or f"run_{timestamp}"
    audio_map = {
        "run_id": run_id,
        "script_title": script["title"],
        "total_duration_seconds": total_duration,
        "provider": provider.provider_name,
        "voice_name": voice_name,
        "language_code": language_code,
        "real_tts": provider.real_tts,
        "mode": mode,
        "audio_scenes": audio_scenes,
        "full_narration_audio_file": str(full_audio_file.absolute()).replace("\\", "/"),
        "approval_metadata": script["approval_metadata"],
    }
    if full_audio_qa:
        audio_map["audio_qa"] = full_audio_qa

    ok_out, err_out = validate_audio_output(audio_map)
    if not ok_out:
        raise RuntimeError(f"❌ Internal Error: Generated audio mapping fails schema: {err_out}")

    return audio_map


def process_script_file(
    script_path: Path,
    provider_name: str | None = None,
    voice_id: str = "default",
    output_dir: Path = Path("data/audio"),
    mode: str = "production",
    language_code: str | None = None,
    format: str = "narrated",
) -> Path:
    """Loads a script file, runs voice generation mapping, and saves the mapping JSON."""
    if not script_path.exists():
        raise FileNotFoundError(f"Script file not found: {script_path}")

    try:
        script = json.loads(script_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise ValueError(f"Failed to parse script JSON: {e}")

    if language_code:
        script["language_code"] = language_code

    audio_map = generate_voice_mapping(
        script=script,
        provider_name=provider_name,
        voice_id=voice_id,
        output_dir=output_dir,
        mode=mode,
        format=format,
    )

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_file = output_dir / f"audio_map_{timestamp}.json"
    out_file.write_text(
        json.dumps(audio_map, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return out_file
