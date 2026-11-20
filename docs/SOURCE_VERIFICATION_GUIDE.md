# SOURCE VERIFICATION GUIDE
## Canonical Hindu Scriptures & Episode Verification Framework

**Repository:** `Indian_Gods_YT_AUto`<br>
**Module:** `src/research/scriptural_source_registry.py`<br>
**Standard:** Primary Canonical Shastras, Sthala Puranas, and Folklore Demarcation<br>

---

## 1. Hierarchy of Scriptural Sources

Divine Dharshanam Daily prioritizes authentic, canonical Hindu scriptures over popular folklore or modern fictional retellings:

```
TIER 1 (Mukhya Shastras - Primary Canonical Authorities)
├── Valmiki Ramayana (Bala, Ayodhya, Aranya, Kishkindha, Sundara, Yuddha Kandas)
├── Vyasa Mahabharata & Srimad Bhagavad Gita
├── Srimad Bhagavata Purana (Maha Purana)
├── Shiva Purana (Rudra, Kotirudra, Vidyeshvara Samhitas)
├── Vishnu Purana
├── Devi Bhagavata Purana & Markandeya Purana (Devi Mahatmyam / Durga Saptashati)
└── Brahmanda Purana (Lalita Sahasranama)

TIER 2 (Sthala Puranas & Regional Temple Chronicles)
├── Skanda Purana (Venkatachala Mahatmyam - Tirumala)
├── Bhavishyottara Purana (Srinivasa Kalyanam)
└── Arunachala Mahatmyam

TIER 3 (Folklore / Modern Fictionalization - FLAGGED / DISALLOWED)
└── Unverified internet rumors, sensationalized TV serial plots, and non-shastric claims
```

---

## 2. Canonical Episode Mapping Registry

| Deity | Canonical Episode | Primary Source | Division / Canto |
| :--- | :--- | :--- | :--- |
| **Lord Shiva** | Drinking Halahala & Vasuki Serpent | Shiva Purana & Bhagavata Purana | Rudra Samhita / Skandha 8, Adhyayas 6-12 |
| **Lord Ganesha** | Ekadanta & Writing Mahabharata | Vyasa Mahabharata | Adi Parva, Adhyayas 1-60 |
| **Lord Krishna** | Lifting Govardhan Hill | Srimad Bhagavata Purana | Skandha 10, Adhyayas 24-27 |
| **Lord Krishna** | Kaliya Mardanam | Srimad Bhagavata Purana | Skandha 10, Adhyayas 15-17 |
| **Lord Sri Rama** | Shabari Devotion & Berries | Valmiki Ramayana | Aranya Kanda, Sarga 74 |
| **Lord Sri Rama** | Building of Ram Setu | Valmiki Ramayana | Yuddha Kanda, Sargas 21-22 |
| **Lord Hanuman** | Sanjeevani Retrieval & Dronagiri | Valmiki Ramayana | Yuddha Kanda, Sarga 74 |
| **Goddess Durga** | Mahishasura Samharam | Markandeya Purana | Devi Mahatmyam, Adhyayas 81-93 |
| **Vamana Avatar** | Three Strides of Land & King Bali | Srimad Bhagavata Purana | Skandha 8, Adhyayas 18-23 |
| **Kurma Avatar** | Bearing Mount Mandara in Ocean | Srimad Bhagavata Purana | Skandha 8, Adhyayas 6-8 |
| **Narasimha Avatar**| Pillar Manifestation & Prahlada | Srimad Bhagavata Purana | Skandha 7, Adhyayas 8-10 |
| **Sri Venkateswara**| Srinivasa Kalyanam & Seven Hills | Skanda Purana | Venkatachala Mahatmyam |
| **Lord Vishnu** | Gajendra Moksham | Srimad Bhagavata Purana | Skandha 8, Adhyayas 2-4 |

---

## 3. Shastric Fact-Checking Protocols

When verifying any script or topic:
1. **Primary Reference Check:** Call `get_scripture_reference_for_topic(topic, deity)` to establish authentic shastra backing.
2. **Attribute Verification:** Confirm that divine weapons, mounts, and companions match `CANONICAL_DEITY_RULES`.
3. **Chronological Consistency:** Avatars from different Yugas (e.g. Rama and Krishna) cannot be conflated as contemporaries without canonical basis (`check_chronology_compatibility`).
4. **No Synthetic Verses:** Citations must strictly adhere to authenticated skandhas/sargas/adhyayas.

---
*Maintained under Divine Dharshanam Daily Scriptural Integrity Guidelines.*
