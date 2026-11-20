# TELUGU CONTENT INTELLIGENCE & AUTOMATION ENGINE
## Architectural & Production Reference Guide for Divine Dharshanam Daily (దివ్య దర్శనం)

**Channel:** Divine Dharshanam Daily (`@Divine_Dharshan_om`)<br>
**Production Language:** Strictly Telugu (`te-IN`, Andhra Pradesh & Telangana audience)<br>
**Publishing Cadence:** Max 2 Shorts/day, 1 Landscape Long Video (16:9, 180-360s) every 3 days<br>
**Core Voice Provider:** Pocket TTS (Telugu) with Edge Neural TTS fallback chain<br>

---

## 1. Engine Architecture Overview

The Telugu Content Intelligence Engine transforms raw YouTube research signals into scripture-grounded, culturally resonant Telugu devotional content.

```
+-----------------------------------------------------------------------------------+
|                        1. SHASTRA SOURCE REGISTRY                                 |
|   src/research/scriptural_source_registry.py                                      |
|   - Primary sources: Valmiki Ramayana, Vyasa Mahabharata, Bhagavata, Shiva,       |
|     Vishnu, Devi Bhagavata, Skanda, Brahmanda Puranas                             |
|   - Canon rules: Deities, weapons, vahanas, consorts, and Yuga chronological eras|
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                   2. INTELLIGENT DECISION & DIVERSITY ENGINE                      |
|   src/decision/selector.py | validator.py | strategy.py | feedback.py             |
|   - Deity Fatigue Penalty: -25 points for immediately preceding published deity   |
|   - Cultural Calendar Proximity: +5 points for day-of-week deity alignment        |
|   - Series Potential: +5 to +8 points for Dashavatara, Ramayana, Jyotirlinga arcs |
|   - Scriptural Reliability: +6 points for primary canonical backing               |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                   3. DYNAMIC STORY BLUEPRINT ENGINE                               |
|   src/content/telugu_blueprints.py | brief_generator.py | gemini_provider.py      |
|   - Deep blueprints: Shiva, Ganesha, Krishna, Rama, Hanuman, Durga, Vamana,       |
|     Kurma, Narasimha, Venkateswara (7Kondala), Vishnu                             |
|   - Universal Dynamic Synthesis: Any unlisted Hindu devotional topic/deity        |
|   - 3-Act Structure, 5-Scene Visual Plan, High-Retention Telugu Hooks             |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                   4. THREE-TIER TELUGU SCRIPT QA GATE                             |
|   src/script/generator.py                                                         |
|   [Tier 1] Factuality Validator: Attribute, weapon, vahana, chronology integrity |
|   [Tier 2] Quality Evaluator: Native Indic glyph ratio, devotional honorifics, wpm|
|   [Tier 3] Retention Optimizer: Opening curiosity hook, mid-video bridges, CTA    |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                   5. VISUAL STORY INTELLIGENCE                                    |
|   src/assets/selector.py                                                          |
|   - Telugu concept semantic translation (కైలాస->kailash, పాము->snake, etc.)     |
|   - Strict local repository priority and deity folder isolation                   |
+-----------------------------------------------------------------------------------+
```

---

## 2. Topic Selection & Diversity Strategy

### 2.1 Deity Fatigue Penalty
To prevent audience saturation and content monotony, `src/decision/feedback.py` analyzes the most recent entries in `data/publishing_history.json`:
* **Immediately preceding video deity:** $-25.0$ penalty points.
* **Two videos ago:** $-15.0$ penalty points.
* **Three videos ago:** $-8.0$ penalty points.

### 2.2 Day-of-the-Week Cultural Affinity
Traditional Telugu devotional schedules award a $+5.0$ bonus:
* **Monday (సోమవారం):** Lord Shiva (`lord_shiva`)
* **Tuesday (మంగళవారం):** Lord Hanuman (`hanuman`), Lord Subrahmanya (`subramanya`)
* **Wednesday (బుధవారం):** Lord Ganesha (`ganesha`), Lord Krishna (`krishna`)
* **Thursday (గురువారం):** Lord Vishnu (`lord_vishnu`), Guru Dattatreya
* **Friday (శుక్రవారం):** Goddess Lakshmi (`lakshmi_devi`), Goddess Parvati / Durga (`parvathi`)
* **Saturday (శనివారం):** Lord Venkateswara / Balaji (`7Kondala_Swami`), Lord Hanuman
* **Sunday (ఆదివారం):** Surya Bhagavan

---

## 3. Telugu Linguistic & Devotional Standards

### 3.1 Reverential Honorifics
Every generated script must incorporate respectful devotional terms:
* **Deity prefixes:** శ్రీ (Sri), స్వామి (Swami), భగవాన్ (Bhagavan), పరమేశ్వరుడు (Parameshwarudu).
* **Attribute descriptors:** దివ్య (Divya), పవిత్ర (Pavitra), అనుగ్రహం (Anugraham), లీల (Leela).

### 3.2 Prohibited Colloquialisms
Sacred scripts must never use street slang or disrespectful terminology (e.g., అబద్ధం, మోసగాడు, చెత్త, పిచ్చి, సోది, టైంపాస్).

### 3.3 Audio Pacing Targets
* **Shorts (35-55s):** 80–130 Telugu words ($\sim 115\text{ wpm}$ optimal for Pocket TTS).
* **Landscape Long Videos (180-360s):** 350–650 Telugu words.

---

## 4. Visual Narrative Matching

`src/assets/selector.py` employs `TELUGU_NARRATIVE_CONCEPTS` to bridge native Telugu scene descriptions with asset filenames and metadata tags:
* Example: `కైలాస పర్వతముపై ధ్యానంలో ఉన్న పరమశివుడు` automatically resolves concepts `["kailash", "mountain", "meditation", "shiva"]`, prioritizing local repository image `assets/gods/lord_shiva/kailash_meditation.png`.
* Strict repository isolation guarantees that assets from other deity folders are never mixed.

---
*Maintained under Divine Dharshanam Daily Telugu Content Intelligence Standards.*
