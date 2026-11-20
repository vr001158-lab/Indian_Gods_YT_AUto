# REMEDIATION REPORT — DIVINE DHARSHANAM DAILY
## Resolution of DEF-01, DEF-03, DEF-02, and DEF-04

**Channel:** Divine Dharshanam Daily (`@Divine_Dharshan_om`)<br>
**Production Language:** STRICTLY Telugu (`te-IN`)<br>
**Date:** November 11, 2026<br>
**Status:** ALL 4 DEFECTS REMEDIATED & VERIFIED<br>
**Full Test Suite:** 601 Tests Passed (0 Failures, 0 Errors, 1 Skipped for optional Torch neural test)

---

## 1. Executive Summary

An independent adversarial audit (`INDEPENDENT_PRODUCTION_READINESS_AUDIT.md`) uncovered four defects in the Telugu Content Intelligence system. All four defects have been remediated in priority order without breaking architectural integrity or altering publishing policies.

| Defect ID | Priority | Description | Remediation Summary | Status |
|:---|:---:|:---|:---|:---:|
| **DEF-01** | CRITICAL | Pre-Voice Script QA gate not connected into generation/voice pipeline | Created `src/script/script_qa_gate.py` with `run_pre_voice_script_qa()`, wired into `generator.py`, `voice/generator.py`, and `orchestrator.py` (`run_voice`). Fail-closed with SHA-256 content hashing. | **VERIFIED** |
| **DEF-03** | HIGH | Spoken narration leaked prompt directions and meta instructions | Implemented `clean_spoken_narration()` and `validate_spoken_narration()` in `src/content/telugu_blueprints.py`. Handcrafted pristine Telugu devotional voice text for all 11 blueprints. Preserved visual descriptions for video generation. | **VERIFIED** |
| **DEF-02** | HIGH | Semantic mismatch & unmonitored fallbacks in scene asset selection | Expanded Dashavatara keywords & deity aliases in `src/assets/selector.py`. Enriched `data/assets/asset_manifest.json` with keyword tags. Added explicit tracking for `semantic_confidence` and `missing_semantic_match`. | **VERIFIED** |
| **DEF-04** | MEDIUM | Script retention evaluator lacked structural narrative rigor | Redesigned `evaluate_script_retention()` in `src/script/script_retention_optimizer.py` with deterministic multi-dimensional checks (hook relevance, curiosity gap, progression, climax, payoff, lexical diversity). | **VERIFIED** |

---

## 2. Defect Remediation Details

### DEF-01 — Connect Pre-Voice Script QA (CRITICAL)

#### Root Cause
Although `src/script/script_factuality_validator.py`, `src/script/script_quality_evaluator.py`, and `src/script/script_retention_optimizer.py` existed, they were not invoked between script generation and voice synthesis. Unvalidated or factually flawed scripts could proceed straight to TTS.

#### Remediation
1. **Created Central QA Gate (`src/script/script_qa_gate.py`):**
   - Implemented `run_pre_voice_script_qa()` orchestrating 6 sequential checks:
     1. Script structure and schema completeness (`validate_script_output`)
     2. Title-topic semantic alignment (`check_title_topic_semantic_alignment`)
     3. Telugu/Indic script integrity (`validate_script_language_integrity`)
     4. Scriptural factuality verification (`validate_script_factuality`)
     5. Telugu linguistic quality & devotional reverence (`evaluate_script_quality`)
     6. Retention structure evaluation (`evaluate_script_retention`)
   - Implemented deterministic SHA-256 fingerprinting via `compute_script_content_hash(script_data)`. If an approved report with a matching hash already exists, duplicate validation is avoided.
   - Built fail-closed exception hierarchy: `ScriptQAError`, `ScriptFactualityError`, `ScriptQualityError`, `ScriptStructureError`.

2. **Wired into Pipeline Stages:**
   - `src/script/generator.py` (`generate_script`): Validates script before returning and attaches `qa_report` directly to script output.
   - `src/voice/generator.py` (`generate_voice_mapping`): Validates `qa_report` before audio synthesis begins. Rejects unapproved or tampered scripts immediately.
   - `src/pipeline/orchestrator.py` (`run_voice`): Verifies script QA before launching voice synthesis command.
   - `src/qa/gate.py` (`FinalQAGate.run`): Validates pre-voice QA status during end-of-pipeline verification.

---

### DEF-03 — Eliminate Narration Prompt Leakage (HIGH)

#### Root Cause
Spoken narration strings in several deity blueprints and dynamic fallback routines contained visual stage directions or descriptive labels (e.g., `దృశ్యం 1:`, `వర్ణన:`, `చిత్రం:`), which would be read aloud by TTS.

#### Remediation
1. **Sanitization & Validation Functions (`src/content/telugu_blueprints.py`):**
   - `clean_spoken_narration(text)`: Strips bracketed cues (`[ACT 1]`, `(Scene 1)`), meta-prefixes (`దృశ్యం 1:`, `వర్ణన:`, `Scene 1:`), and stray formatting characters.
   - `validate_spoken_narration(text)`: Validates that zero stage directions or leaked keywords (`దృశ్యం`, `వర్ణన`, `చిత్రం`, `scene`, `prompt`, `visual`, `camera`) appear in spoken text.

2. **Handcrafted Devotional Voice Text for All 11 Blueprints:**
   - Every deity blueprint in `src/content/telugu_blueprints.py` (`lord_shiva`, `ganesha`, `krishna`, `ram`, `hanuman`, `durga`, `vamana`, `kurma`, `narasimha`, `7Kondala_Swami`, `lord_vishnu`) now contains distinct, reverent, spoken-ready Telugu text per scene.
   - Visual references (`visual_reference`) remain detailed and descriptive, dedicated exclusively to image/video generation.

3. **Fixed Fallback Script Generator (`src/content/gemini_provider.py`):**
   - Corrected routing order so Telugu offline fallback scripts synthesize pure spoken narration for `voice_text` and clean prompt descriptions for `visual_reference`.

---

### DEF-02 — Fix Visual Semantic Matching & Fallbacks (HIGH)

#### Root Cause
`src/assets/selector.py` relied primarily on raw folder name matching and exact string containment in image filenames. When Dashavatara concepts occurred (e.g., Kurma, Vamana under `lord_vishnu`), the selector could fall back to generic deity portraits without flagging the low confidence.

#### Remediation
1. **Deity Aliases & Concept Mapping (`src/assets/selector.py`):**
   - Added Dashavatara concepts to `DEITY_ALIASES["lord_vishnu"]` (`kurma`, `vamana`, `trivikrama`, `matsya`, `varaha`, `parashurama`, `kalki`, `gajendra`).
   - Expanded `TELUGU_NARRATIVE_CONCEPTS` with Telugu-to-English translations for cosmic churning (`కూర్మ`, `మందర`, `క్షీరసాగర`), Vamana/Bali (`వామన`, `బలి`, `త్రివిక్రమ`), Govardhan, Trishul, and Sudarshana Chakra.
   - Prevented cross-deity borrowing: avatars and deities cannot silently substitute unrelated deities.

2. **Asset Manifest Tagging (`data/assets/asset_manifest.json`):**
   - Enriched 226 deity images with descriptive semantic tags extracted from filenames, removing hex hashes and unhelpful strings.
   - Updated `_score_semantic_match` to search both candidate file paths and asset tags.

3. **Explicit Confidence & Missing Match Tracking:**
   - Both `select_scene_assets` and `select_landscape_scene_assets` now track:
     - `semantic_match_found: bool`
     - `semantic_confidence: "HIGH" | "MEDIUM" | "NONE"`
     - `missing_semantic_match: bool` (set to `True` when confidence is `NONE` and fallback asset is used)
   - Allows QA gates and logs to detect when specific story-scene assets are missing.

---

### DEF-04 — Improve Script Retention Evaluator (MEDIUM)

#### Root Cause
`evaluate_script_retention()` in `src/script/script_retention_optimizer.py` used crude length heuristics that awarded high scores to repetitive scripts lacking genuine narrative structure or emotional hooks.

#### Remediation
1. **Multi-Dimensional Structural Checks:**
   - **Opening Hook Relevance (20 pts):** Verifies that Scene 1 explicitly connects to the script's deity and topic within the first 15 seconds.
   - **Curiosity Gap Detection (20 pts):** Scans for Telugu inquiry markers (`ఎందుకు`, `రహస్యం`, `ఎలా`, `ఆశ్చర్యం`, `కారణం`).
   - **Narrative Progression (20 pts):** Detects sequential transition markers (`అనంతరం`, `తరువాత`, `అయితే`, `చివరికి`, `వెంటనే`).
   - **Emotional Development & Climax (20 pts):** Scans for climax and emotional intensity markers (`సంహారం`, `విజయం`, `రక్షణ`, `కరుణ`, `విశ్వరూపం`).
   - **Resolution & Devotional Payoff (20 pts):** Scans for spiritual blessings and takeaway terms (`అనుగ్రహం`, `భక్తి`, `మోక్షం`, `ఆశీస్సులు`, `ప్రార్థన`).

2. **Repetition & Lexical Overlap Penalty:**
   - Computes consecutive scene word overlap. Identical or near-identical consecutive narrations trigger up to a 20-point penalty and advisory warnings.
   - Retention warnings are structured and returned without blocking valid scripts when advisory thresholds are met.

---

## 3. Production Pipeline Safety & Safeguards Verification

- **Telugu-Only Enforcement:**
  - `src/publisher/quota.py`: `PRODUCTION_LANGUAGE = "te-IN"`
  - `src/publisher/safety.py`: Rejects any non-Telugu publishing candidate.
  - `src/pipeline/orchestrator.py`: Pipeline execution fails closed if `language_code != "te-IN"`.
  - `run_pipeline.py`: CLI strictly rejects any language argument other than `te-IN`.

- **Pocket TTS Fallback Chain:**
  - Primary for Telugu: `pocket_tts`
  - Fallback order: `pocket_tts` → `edge_neural_tts` → `kokoro` → `piper`
  - Verified by `tests/test_pocket_tts.py` and `tests/test_remediation_defects.py`.

- **Daily Quotas:**
  - Maximum 2 uploads per calendar day (Asia/Kolkata timezone).
  - Maximum 2 Shorts per day.
  - 1 landscape long video per 72-hour rolling window.

---

## 4. Verification Test Results

### Full Repository Test Suite
```bash
python -m unittest discover -s tests -p "test_*.py"
```
**Outcome:**
- **Tests run:** 601
- **Failures:** 0
- **Errors:** 0
- **Skipped:** 1 (`test_generate_speech_mocked` requiring optional neural PyTorch runtime)
- **Result:** `OK (skipped=1)`

### Focused Verification Suites
- `tests.test_remediation_defects`: 12/12 PASSED
- `tests.test_content_intelligence`: 20/20 PASSED
- `tests.test_script_generator`: 43/43 PASSED
- `tests.test_voice_generator`: 52/52 PASSED
- `tests.test_final_qa`: 28/28 PASSED
- `tests.test_pocket_tts`: 26/26 PASSED (1 skipped)

### Code Formatting & Working Tree Integrity
- `git diff --check`: Completely clean (0 trailing whitespace or formatting errors).
- All untracked user scripts, assets, manifests, and documentation preserved.
- No files committed, pushed, or uploaded.
