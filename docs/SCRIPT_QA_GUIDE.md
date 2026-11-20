# SCRIPT QUALITY & FACTUALITY QA GUIDE
## Multi-Tier Validation Framework for Telugu Devotional Scripts

**Channel:** Divine Dharshanam Daily (`@Divine_Dharshan_om`)<br>
**Target Locale:** `te-IN` (Telugu, India)<br>
**Standard:** Shastric Authenticity, Linguistic Elegance, and High Retention<br>

---

## 1. Overview of QA Architecture

Before any voice synthesis (Pocket TTS) or video composition commences, all generated scripts must pass three deterministic automated QA gates:

```
                  Raw Script Generated (Gemini / Offline Template)
                                        |
                                        v
                 +-----------------------------------------------+
                 |  TIER 1: Shastric Factuality Validator        |
                 |  (src/script/script_factuality_validator.py)  |
                 +-----------------------------------------------+
                                        |  Pass: Valid attributes & shastra match
                                        v
                 +-----------------------------------------------+
                 |  TIER 2: Telugu Linguistic Quality Evaluator  |
                 |  (src/script/script_quality_evaluator.py)     |
                 +-----------------------------------------------+
                                        |  Pass: Indic ratio >= 60%, score >= 50
                                        v
                 +-----------------------------------------------+
                 |  TIER 3: Retention Optimizer                  |
                 |  (src/script/script_retention_optimizer.py)   |
                 +-----------------------------------------------+
                                        |  Pass: Score >= 70, Opening hook, CTA
                                        v
                       Approved for Production Synthesis
```

---

## 2. Tier 1: Shastric Factuality Validation

### 2.1 Cross-Deity Contradiction Checks
The validator checks that the deity established in the topic matches the deity and divine deeds in the script:
* **Attribute Canon:** Each deity has defined allowable weapons, vahanas, and consorts.
  - *Example Violation:* Sudarshana Chakra assigned to Lord Shiva $\rightarrow$ **REJECTED**.
  - *Example Violation:* Ganesha riding Garuda $\rightarrow$ **REJECTED**.
  - *Example Violation:* Parvati referred to as wife of Rama $\rightarrow$ **REJECTED**.

### 2.2 Chronological & Yuga Consistency
Avatars from different Yugas (Treta Yuga: Rama, Vamana, Parashurama; Dvapara Yuga: Krishna) cannot be portrayed as contemporary peers in a common timeline unless explicitly backed by canonical scripture (e.g., Parashurama encountering Rama in Balakanda).

### 2.3 Citation Fabrications
Any hallucinatory citations (e.g. "Bhagavata Purana Chapter 999") trigger an immediate factuality failure.

---

## 3. Tier 2: Telugu Linguistic Quality Evaluation

### 3.1 Metrics Evaluated
1. **Native Indic Ratio:** $\ge 60\%$ Telugu Unicode glyphs (`[\u0C00-\u0C7F]`). Pure English or corrupt characters trigger rejection.
2. **Devotional Reverence Score:** Analyzes presence of respectful prefixes and honorifics (శ్రీ, స్వామి, భగవాన్, పరమ, దివ్య).
3. **Disallowed Slang:** Automatic rejection upon encountering offensive, casual, or inappropriate terms (అబద్ధం, చెత్త, పిచ్చి, సోది, etc.).
4. **Duration & Pacing:** Assesses word count relative to duration. Target $\sim 115\text{ words/min}$.

---

## 4. Tier 3: Retention Optimization

### 4.1 Required Components
1. **Curiosity Hook in Scene 1:** Must pose an engaging question using curiosity triggers (e.g., "తెలుసా?", "ఎందుకు?", "రహస్యం").
2. **Retention Hooks:** Minimum 2 forward-looking hooks teasing mid-to-late story revelations.
3. **Closing Devotional Call-to-Action:** Respectful sign-off encouraging subscription and divine contemplation (e.g., "నిత్యం పవిత్ర దివ్య దర్శనం కోసం లైక్ చేసి సబ్‌స్క్రైబ్ చేయండి! ఓం నమః శివాయ / ఓం నమో నారాయణాయ").
4. **Three Shorts Variants:** Shorts scripts must include exactly 3 distinct vertical scripts with hook and body.

---
*Maintained under Divine Dharshanam Daily Script QA Protocols.*
