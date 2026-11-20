# UPGRADE AUDIT REPORT — DIVINE DHARSHANAM DAILY
## Telugu-Only AI Devotional Content Intelligence & Automation Engine

**Target Repository:** `Indian_Gods_YT_AUto`<br>
**Current Channel:** Divine Dharshanam Daily (`@Divine_Dharshan_om`)<br>
**Production Language Policy:** Strictly Telugu (`te-IN`)<br>
**Date:** November 2026<br>
**Auditor:** Senior Systems Architect & Telugu Content Intelligence Specialist<br>

---

## 1. Executive Summary

This audit assesses the state of `Indian_Gods_YT_AUto` prior to implementing the **Telugu-Only AI Devotional Content Intelligence & Automation Engine**.

While the existing pipeline successfully enforces a daily publishing limit (maximum 2 uploads per day, 72-hour landscape long video pacing) and contains a functional multilingual fallback engine, significant architectural gaps exist in scriptural factuality, Telugu narrative depth, deity diversity, visual story matching, and audience retention intelligence.

### Core Objectives of Upgrade
1. **Scriptural Authenticity & Factuality:** Eliminate mythological hallucinations, cross-deity attribute bleeding, and chronological distortions through a structured Shastric Source Registry.
2. **Telugu Devotional Script Excellence:** Standardize high-retention Telugu storytelling across 45-second Shorts and 3-5 minute Landscape Long Videos using authentic Telugu devotional vocabulary, respectful honorifics, and narrative arcs.
3. **Deity Diversity & Anti-Fatigue Intelligence:** Dynamically prevent consecutive or repetitive deity content using feedback from `publishing_history.json`.
4. **Scene-Aware Visual Story Matching:** Upgrade asset selection to comprehend Telugu scene prompts and resolve semantic concepts rather than stripping non-ASCII characters.
5. **Multi-Gate Quality Assurance:** Establish strict automated gates for factuality, Telugu linguistic integrity, script retention, and local asset isolation before any asset or audio generation begins.

---

## 2. Baseline Architecture & Verification

The current system executes a 10-stage sequential pipeline:
$$\text{RESEARCH} \rightarrow \text{DECISION} \rightarrow \text{CONTENT} \rightarrow \text{SCRIPT} \rightarrow \text{VOICE} \rightarrow \text{VISUAL} \rightarrow \text{VIDEO} \rightarrow \text{THUMBNAIL} \rightarrow \text{QA} \rightarrow \text{PUBLISHER}$$

* **Full Test Suite Status:** 569 tests passing (1 test skipped for optional PyTorch).
* **Target YouTube Channel:** Authenticated via OAuth token (`token.json`), title `Divine Dharshanam Daily`, handle `@Divine_Dharshan_om`.
* **Current Quota:** 1/2 videos published today (unlisted verification Short); 1 upload slot available; 72h landscape cadence intact.
* **Production Language:** Locked to `te-IN` (Telugu, India).

---

## 3. Detailed Component Audit & Identified Vulnerabilities

### 3.1 Topic Decision Engine (`src/decision/`)
* **Current State:** `selector.py` ranks candidates purely by a deterministic tuple `(-overall_score, -demand_score, -freshness_score, -gap, -relevance, -curiosity, topic)`. `validator.py` enforces high confidence and non-duplicate topic strings.
* **Vulnerabilities:**
  1. *Deity Fatigue Blindness:* The selector does not inspect deity distribution in `publishing_history.json`. If 5 Shiva topics score highest, the system publishes Shiva on consecutive days, fatiguing the subscriber base.
  2. *Lack of Telugu Cultural & Calendar Proximity:* No dedicated scoring for Telugu festivals (e.g., Ugadi, Brahmotsavam, Sivaratri, Mukkoti Ekadasi, Hanuman Jayanti, Vinayaka Chavithi, Karthika Masam).
  3. *No Scriptural Reliability Weighting:* YouTube API search keywords receive equal weight regardless of whether the topic is rooted in authentic Puranas or speculative clickbait.

### 3.2 Content Brief & Story Blueprint Engine (`src/content/`)
* **Current State:** `_DEITY_BLUEPRINTS` in `src/content/brief_generator.py` only defines blueprints for `shiva` and `ganesha`. For all other deities (Vishnu, Krishna, Rama, Hanuman, Durga, Lakshmi, Venkateswara, Narasimha, Vamana, Kurma, etc.), the engine drops into a generic English boilerplate or an offline Telugu Shiva brief when Gemini is offline or rate-limited.
* **Vulnerabilities:**
  1. *Severe Avatar & Deity Coverage Gap:* No pre-structured story blueprints for Dashavatara episodes, Ramayana episodes, or South Indian Vaishnavite/Shaivite legends.
  2. *Offline Fallback Mismatch:* `src/content/gemini_provider.py` contains only Shiva in `_OFFLINE_BRIEFS["te-IN"]` and `_OFFLINE_SCRIPTS["te-IN"]`. A request for a Kurma or Rama brief falling back offline erroneously receives a Shiva script, triggering downstream semantic rejection.

### 3.3 Script Generation & Factuality QA Void (`src/script/`)
* **Current State:** `generator.py` has a basic title-topic semantic alignment check (`check_title_topic_semantic_alignment`) and Indic Unicode character ratio validation (`validate_script_language_integrity`).
* **Vulnerabilities:**
  1. *No Independent Factuality Validator:* Does not verify whether a deity is paired with the wrong weapon (e.g., Shiva with Sudarshana Chakra, Vishnu with Trishula), wrong vahana (e.g., Ganesha on Garuda), or wrong consort/family relationships (e.g., Sita with Shiva).
  2. *Chronological & Yuga Contradictions:* No check preventing anachronistic mashups (e.g., Parashurama taking orders from Krishna, or Treta Yuga characters fighting in Kurukshetra without scriptural basis).
  3. *No Telugu Script Quality Evaluator:* No check for colloquial Telugu slang, repetitive sentence structures, passive pacing, or inappropriate tone for sacred discourse.
  4. *No Retention Hook Optimizer:* Hooks are not validated for question-form curiosity loops or retention pacing.

### 3.4 Visual Scene Matching (`src/assets/selector.py`)
* **Current State:** Line 218 in `select_scene_assets()` uses regex:
  ```python
  keywords = [
      w for w in re.sub(r"[^a-zA-Z0-9\s]", "", f"{visual_ref} {script_text}").lower().split()
      if len(w) >= 4
  ]
  ```
* **Vulnerabilities:**
  1. *Telugu Glyph Stripping:* The regex completely deletes all Telugu characters. When `visual_ref` and `script_text` are in Telugu, `keywords` becomes empty, semantic score is always 0, and the engine falls back to cyclic index selection.
  2. *Lack of Telugu Transliteration Concept Mapping:* Sacred terms like `కైలాస` (Kailash), `సర్పం` / `వాసుకి` (Vasuki), `మథనం` (Churning), `ధనుస్సు` (Bow), `చక్రం` (Chakra) are not mapped to asset filenames or manifest tags.

### 3.5 Analytics & Performance Feedback Loop (`src/analytics/` / `src/decision/`)
* **Current State:** `publishing_history.json` records published metadata, but this data is purely used for deduplication in `validator.py`.
* **Vulnerabilities:**
  1. The decision engine does not analyze the frequency, recency, or distribution of past published deities to adjust topic demand scores dynamically.

---

## 4. Upgrade Architecture & Implementation Plan

```
+-----------------------------------------------------------------------------------+
|                            RESEARCH & DISCOVERY                                   |
|   src/research/collector.py  +  src/research/scriptural_source_registry.py        |
|   * Authentic Puranas & Itihasas Source Mapping (Valmiki, Vyasa, Puranic Corpus)  |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                        INTELLIGENT DECISION ENGINE                                |
|   src/decision/selector.py  +  validator.py  +  strategy.py  +  feedback.py       |
|   * Deity Fatigue Penalty (Exponential decay based on publishing_history.json)    |
|   * Telugu Cultural & Festival Calendar Proximity Scoring                         |
|   * Series Potential & Scriptural Reliability Weighting                           |
|   * Transparent & Explainable Decision Logging                                    |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                     DYNAMIC STORY BLUEPRINT GENERATOR                             |
|   src/content/brief_generator.py  +  gemini_provider.py                           |
|   * Comprehensive blueprints: Shiva, Vishnu, Krishna, Rama, Ganesha, Hanuman,     |
|     Durga, Lakshmi, Saraswati, Subrahmanya, Venkateswara, Narasimha, Vamana,      |
|     Kurma, Varaha, Matsya, Parashurama                                            |
|   * Universal Dynamic Composition for Unlisted Topics                             |
|   * 3-Act Structure, Scene Prompts & High-Conversion Telugu Hooks                 |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                   TELUGU SCRIPT GENERATOR & 3-TIER QA ENGINE                      |
|   src/script/generator.py                                                         |
|   |--> Tier 1: src/script/script_factuality_validator.py (Shastric Consistency)   |
|   |--> Tier 2: src/script/script_quality_evaluator.py (Telugu Linguistic Mastery) |
|   +--> Tier 3: src/script/script_retention_optimizer.py (Pacing, Hooks & CTAs)    |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                      VISUAL STORY INTELLIGENCE                                    |
|   src/assets/selector.py                                                          |
|   * Telugu Concept & Transliteration Narrative Matcher                            |
|   * Strict Local Deity Asset Priority & Validation Logging                        |
+-----------------------------------------------------------------------------------+
```

---

## 5. Risk Assessment & Safe Execution Constraints

1. **Non-Breaking Existing Suite:** All 569 existing unit tests must remain 100% green without modification to unrelated assertions.
2. **Telugu Pocket TTS Preservation:** The primary Telugu voice provider (`pocket_tts`) and its fallback sequence (`edge_neural_tts` -> `kokoro` -> `piper`) must remain completely undisturbed.
3. **No Unsanctioned Commits or Live Publishes:** Strict sandbox execution; dry-run validation only.
4. **Authenticity Guarantee:** No synthetic or fabricated scriptural references; all citations must map to canonical texts.

---
*Report generated and approved for Phase 2 implementation.*
