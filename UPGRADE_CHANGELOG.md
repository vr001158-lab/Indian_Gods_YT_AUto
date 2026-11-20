# UPGRADE CHANGELOG — TELUGU CONTENT INTELLIGENCE
## Divine Dharshanam Daily Content & Automation Engine

**Repository:** `Indian_Gods_YT_AUto`<br>
**Date:** November 2026<br>
**Scope:** Core Intelligence, Shastric Registry, Story Blueprints, 3-Tier Script QA, Visual Narrative Matching<br>

---

## Added Modules & Files

1. **`UPGRADE_AUDIT_REPORT.md`**
   - Architectural analysis, component audit, identified vulnerabilities, and upgrade strategy.

2. **`src/research/scriptural_source_registry.py`**
   - 20 canonical scripture mappings across Ramayana, Mahabharata, Bhagavata, Shiva, Vishnu, Devi Bhagavata, Skanda, and Brahmanda Puranas.
   - Comprehensive deity attribute and relationship rules for 11 major deities.
   - Chronological Yuga era compatibility checker.
   - Claim verification and fake citation detection.

3. **`src/decision/feedback.py`**
   - Publishing history analyzer calculating deity frequency and exponential recency penalties.
   - Deity fatigue penalty (-25 for consecutive day).
   - Telugu devotional day-of-week cultural calendar bonus (+5).

4. **`src/content/telugu_blueprints.py`**
   - Deep, production-ready Telugu blueprints for 11 deities: Lord Shiva, Lord Ganesha, Lord Krishna, Lord Rama, Lord Hanuman, Goddess Durga, Lord Vamana, Lord Kurma, Lord Narasimha, Lord Venkateswara (7Kondala), Lord Vishnu.
   - Universal dynamic Telugu brief synthesizer for unlisted deities and topics.
   - Universal dynamic Telugu script synthesizer for unlisted deities.

5. **`src/script/script_factuality_validator.py`**
   - Automated Tier 1 QA: Validates attribute canon, weapon/vahana compatibility, family relationships, disallowed episodes, and chronology.

6. **`src/script/script_quality_evaluator.py`**
   - Automated Tier 2 QA: Validates native Telugu Unicode ratio ($\ge 60\%$), devotional honorifics, prohibited slang, word count, and pacing.

7. **`src/script/script_retention_optimizer.py`**
   - Automated Tier 3 QA: Validates opening curiosity hook in Scene 1, retention hook questions, and closing devotional Call-to-Action.

8. **`tests/test_content_intelligence.py`**
   - 20 comprehensive unit tests covering all required production scenarios.

9. **Documentation Suite:**
   - `TELUGU_CONTENT_INTELLIGENCE.md`
   - `SCRIPT_QA_GUIDE.md`
   - `SOURCE_VERIFICATION_GUIDE.md`
   - `UPGRADE_CHANGELOG.md`

---

## Enhanced Existing Modules

1. **`src/decision/strategy.py`**
   - Integrated `apply_content_intelligence_preferences`: Incorporates deity fatigue, cultural calendar bonus, series potential, and scriptural reliability.

2. **`src/decision/report.py`**
   - Connected `apply_content_intelligence_preferences` into decision pipeline when language code is specified or in narrated Telugu mode.
   - Enriched decision JSON with `intelligence_factors` and human-readable selection explanations.

3. **`src/content/gemini_provider.py`**
   - Replaced single-deity Shiva fallback with `src.content.telugu_blueprints` dynamic synthesis for all deities and unlisted topics.
   - Guaranteed full Telugu script synthesis for any topic when Gemini is rate-limited or offline.

4. **`src/assets/selector.py`**
   - Added `TELUGU_NARRATIVE_CONCEPTS` mapping Telugu devotional phrases to English keywords for asset search.
   - Implemented `extract_scene_semantic_keywords` supporting bilingual and transliterated prompt matching without stripping Telugu characters.

---
*Verified and documented for production release.*
