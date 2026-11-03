# Pocket TTS Telugu Voice Provider Integration Guide

## 1. Overview
The `pocket_tts` voice provider integrates the lightweight neural text-to-speech model **`prasadvittaldev/pocket-tts-telugu-female-syspin`** into the Divine Dharshanam automated YouTube production pipeline. It enables high-quality, fully offline Telugu narration on CPU infrastructure without reliance on cloud API keys or external billing.

- **Provider Identifier:** `pocket_tts`
- **Language Code:** `te-IN` (Telugu)
- **Voice Identifier:** `syspin_female`
- **Sampling Rate:** 24,000 Hz (24 kHz, 16-bit PCM mono WAV)
- **Model Architecture:** Kyutai Pocket TTS (~0.1B parameters)
- **Checkpoint Location:** `hf://prasadvittaldev/pocket-tts-telugu-female-syspin/config.yaml`
- **Voice Prompt Reference:** `hf://prasadvittaldev/pocket-tts-telugu-female-syspin/voice_prompt.wav`

---

## 2. Architecture & Design Principles

### Fail-Closed Production Standard
`PocketTTSProvider` enforces `real_tts = True` and `mode = "production"`. It is registered in `PRODUCTION_PROVIDERS`. If model weights cannot be loaded or inference fails, it raises `VoiceProviderError` to cleanly activate the production fallback chain. It never falls back silently to mock, sine-wave, or placeholder audio.

### Default Primary & Fallback Policy
1. **Telugu Primary Default:** Pocket TTS (`pocket_tts`) is the default primary production voice provider for Telugu (`te-IN`) narration across the CLI (`run_voice_generator.py`), pipeline orchestrator (`src/pipeline/orchestrator.py`), and GitHub Actions production workflows.
2. **Edge TTS Fallback for Telugu:** If `pocket_tts` encounters missing dependencies or inference errors on a Telugu run, the pipeline automatically falls back to Microsoft Edge Neural TTS (`edge_neural_tts`).
3. **Hindi & Tamil Defaults:** Microsoft Edge Neural TTS (`edge_neural_tts`) remains the default primary production provider for Hindi (`hi-IN`) and Tamil (`ta-IN`).
4. **Fallback Chain:** If both Pocket TTS and Edge TTS fail on Telugu, the pipeline cleanly falls back to Kokoro followed by Piper.

---

## 3. Telugu Text Normalization & Sentence Chunking

### Normalization Pipeline (`normalize_telugu_text`)
1. **Telugu Numerals:** Converts Telugu script numerals (`౦`, `౧`, `౨`, `౩`, `౪`, `౫`, `౬`, `౭`, `౮`, `౯`) to ASCII digits.
2. **Spoken Word Expansion:** Converts numbers to natural Telugu words:
   - Single digits: `0` → `సున్నా`, `1` → `ఒకటి`, `5` → `ఐదు`, `9` → `తొమ్మిది`
   - Multi-digit numbers: `10` → `పది`, `25` → `ఇరవై ఐదు`, `100` → `వంద`, `1000` → `వెయ్యి`, `100000` → `లక్ష`, `10000000` → `కోటి`
3. **Latin Character Protection:** Detects unhandled ASCII/Latin letters (`[A-Za-z]+`), emits a logger warning, and strips them when `strip_latin=True` to prevent SentencePiece tokenizer errors or phonetic corruption.
4. **Whitespace Sanitization:** Cleans multiple spaces and non-standard whitespace.

### Sentence Chunking (`split_into_sentences`)
1. Splits raw narrative text along punctuation boundaries: `.`, `?`, `!`, `।` (Danda), `॥` (Double Danda), and newlines.
2. Caps individual sentence chunks at `max_chars=150` characters (sub-splitting on commas or clause boundaries if needed) to ensure inputs stay within SentencePiece token capacity.
3. Preserves strict sequential order during audio concatenation.

---

## 4. Audio Specifications & QA Validation
- **Container / Codec:** RIFF/PCM WAV (`pcm_s16le`), 16-bit mono.
- **Sample Rate:** 24,000 Hz.
- **QA Compatibility:** Fully compatible with `ffprobe` format inspection and `src/voice/qa.py` (`perform_audio_qa`).

---

## 5. GitHub Actions & CI Configuration
1. **CPU Execution:** Inference runs entirely on CPU without GPU or CUDA drivers.
2. **PyTorch Wheel Optimization:** Installed using `--index-url https://download.pytorch.org/whl/cpu` to avoid downloading ~850MB of CUDA binaries in CI runners.
3. **Model Weight Caching:** Checkpoints (~209 MB) are cached under `~/.cache/huggingface` via `actions/cache@v4` in `.github/workflows/divine-dharshanam-daily.yml`.

---

## 6. Model Limitations
- **Single Fixed Voice:** The model is fine-tuned on a single female speaker (`syspin_female`, fundamental frequency $F_0 \approx 208\text{ Hz}$). Zero-shot multi-speaker voice cloning is not supported with this checkpoint.
- **Language Scope:** Restricted strictly to `te-IN` (Telugu). Any attempt to invoke it with `hi-IN` or `ta-IN` raises `VoiceProviderError`.

---

## 7. Licensing & Monetization Compliance

### Model Weights License
- **License:** MIT License (`prasadvittaldev/pocket-tts-telugu-female-syspin`).
- **Commercial Use:** Permitted under standard MIT terms.

### Dataset License & Attribution (Important for YouTube Monetization)
- **Dataset:** SYSPIN (Synthesizing Speech in Indian Languages) Telugu Female corpus.
- **Institution:** SPIRE Lab, Indian Institute of Science (IISc), Bengaluru & Bhashini project.
- **Dataset License:** **Creative Commons Attribution 4.0 International (CC-BY-4.0)**.
- **Monetization Implication:** CC-BY-4.0 permits commercial and monetized content generation provided appropriate attribution is given.
- **Recommended YouTube Video Description Credit:**
  ```text
  Voice synthesized using Pocket TTS trained on the SYSPIN Telugu speech dataset
  (SPIRE Lab, Indian Institute of Science, Bengaluru / Bhashini), licensed under CC-BY-4.0.
  ```
