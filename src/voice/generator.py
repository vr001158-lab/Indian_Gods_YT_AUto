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
) -> dict:
    """
    Synthesizes speech for both full narration and individual scenes.
    Creates a synchronized mapping file of scenes to audio outputs.

    Production mode (default):
      - provider MUST be edge_neural_tts (or google_chirp3_hd for premium)
      - real_tts MUST be True
      - fails closed if provider unavailable or audio invalid
      - attempts fallback chain if primary fails

    Test mode:
      - allows mock/test providers for unit tests only
    """
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
    )

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_file = output_dir / f"audio_map_{timestamp}.json"
    out_file.write_text(
        json.dumps(audio_map, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return out_file
