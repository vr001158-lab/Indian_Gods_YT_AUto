# src/research/scriptural_source_registry.py
# Scriptural Source Registry for Divine Dharshanam Daily
# Provides authentic, verifiable references from canonical Hindu scriptures.
# Distinguishes primary (Mukhya) shastras from secondary / sthala puranas and flags folklore.

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ScriptureReference:
    """Represents a canonical scriptural citation."""
    text_name: str           # e.g., "Srimad Bhagavata Purana", "Valmiki Ramayana"
    division: str            # e.g., "Skandha 8, Adhyaya 7", "Bala Kanda, Sarga 45"
    sanskrit_title: str      # e.g., "श्रीमद्भागवतपुराणम्"
    telugu_title: str        # e.g., "శ్రీమద్భాగవత పురాణము"
    source_tier: str         # "primary", "secondary", "sthala_purana"
    verified_episodes: list[str] = field(default_factory=list)


# ── Canonical Scriptures Registry ─────────────────────────────────────────────

CANONICAL_SCRIPTURES: dict[str, ScriptureReference] = {
    # ── Bhagavata Purana ──────────────────────────────────────────────────────
    "bhagavata_purana_samudra_manthan": ScriptureReference(
        text_name="Srimad Bhagavata Purana",
        division="Skandha 8, Adhyayas 6-12",
        sanskrit_title="श्रीमद्भागवतपुराणम्",
        telugu_title="శ్రీమద్భాగవత పురాణము (అష్టమ స్కంధము)",
        source_tier="primary",
        verified_episodes=["samudra_manthan", "kurma_avatar", "halahala_shiva", "mohini_avatar"],
    ),
    "bhagavata_purana_govardhan": ScriptureReference(
        text_name="Srimad Bhagavata Purana",
        division="Skandha 10, Adhyayas 24-27",
        sanskrit_title="श्रीमद्भागवतपुराणम्",
        telugu_title="శ్రీమద్భాగవత పురాణము (దశమ స్కంధము)",
        source_tier="primary",
        verified_episodes=["govardhan_hill", "krishna_indra_pride", "surabhi_cow"],
    ),
    "bhagavata_purana_kaliya_mardanam": ScriptureReference(
        text_name="Srimad Bhagavata Purana",
        division="Skandha 10, Adhyayas 15-17",
        sanskrit_title="श्रीमद्भागवतपुराणम्",
        telugu_title="శ్రీమద్భాగవత పురాణము (కాళీయ మర్దనము)",
        source_tier="primary",
        verified_episodes=["kaliya_mardanam", "yamuna_purification"],
    ),
    "bhagavata_purana_vamana": ScriptureReference(
        text_name="Srimad Bhagavata Purana",
        division="Skandha 8, Adhyayas 18-23",
        sanskrit_title="श्रीमद्भागवतपुराणम्",
        telugu_title="శ్రీమద్భాగవత పురాణము (వామన చరితము)",
        source_tier="primary",
        verified_episodes=["vamana_avatar", "mahabali_three_strides", "trivikrama"],
    ),
    "bhagavata_purana_narasimha": ScriptureReference(
        text_name="Srimad Bhagavata Purana",
        division="Skandha 7, Adhyayas 8-10",
        sanskrit_title="श्रीमद्भागवतपुराणम्",
        telugu_title="శ్రీమద్భాగవత పురాణము (నరసింహావతారము)",
        source_tier="primary",
        verified_episodes=["narasimha_avatar", "prahlada_bhakti", "hiranyakashipu_samharam"],
    ),
    "bhagavata_purana_gajendra_moksha": ScriptureReference(
        text_name="Srimad Bhagavata Purana",
        division="Skandha 8, Adhyayas 2-4",
        sanskrit_title="శ్రీమద్భాగవత పురాణము",
        telugu_title="శ్రీమద్భాగవత పురాణము (గజేంద్ర మోక్షము)",
        source_tier="primary",
        verified_episodes=["gajendra_moksham", "vishnu_surrender"],
    ),

    # ── Valmiki Ramayana ──────────────────────────────────────────────────────
    "valmiki_ramayana_bala_kanda": ScriptureReference(
        text_name="Valmiki Ramayana",
        division="Bala Kanda, Sargas 45-47",
        sanskrit_title="वाल्मीकि रामायणम्",
        telugu_title="వాల్మీకి రామాయణము (బాలకాండ)",
        source_tier="primary",
        verified_episodes=["samudra_manthan", "ganga_avataranam", "halahala"],
    ),
    "valmiki_ramayana_aranya_kanda": ScriptureReference(
        text_name="Valmiki Ramayana",
        division="Aranya Kanda, Sargas 42-44, 74",
        sanskrit_title="वाल्मीकि रामायणम्",
        telugu_title="వాల్మీకి రామాయణము (అరణ్యకాండ)",
        source_tier="primary",
        verified_episodes=["golden_deer_maricha", "jatayu_sacrifice", "shabari_bhakti"],
    ),
    "valmiki_ramayana_yuddha_kanda": ScriptureReference(
        text_name="Valmiki Ramayana",
        division="Yuddha Kanda, Sargas 21-22, 74",
        sanskrit_title="वाल्मीकि रामायणम्",
        telugu_title="వాల్మీకి రామాయణము (యుద్ధకాండ)",
        source_tier="primary",
        verified_episodes=["ram_setu", "sanjeevani_hanuman", "ravana_samharam"],
    ),
    "valmiki_ramayana_sundara_kanda": ScriptureReference(
        text_name="Valmiki Ramayana",
        division="Sundara Kanda, Sargas 1-68",
        sanskrit_title="वाल्मीकि रामायणम्",
        telugu_title="వాల్మీకి రామాయణము (సుందరకాండ)",
        source_tier="primary",
        verified_episodes=["hanuman_ocean_leap", "sita_dharshanam", "lanka_dahanam"],
    ),

    # ── Mahabharata ───────────────────────────────────────────────────────────
    "mahabharata_adi_parva": ScriptureReference(
        text_name="Vyasa Mahabharata",
        division="Adi Parva, Adhyayas 1-60",
        sanskrit_title="महाभारतम्",
        telugu_title="వ్యాస మహాభారతము (ఆది పర్వము)",
        source_tier="primary",
        verified_episodes=["ganesha_ekadanta_writing", "samudra_manthan", "garuda_amrita"],
    ),
    "mahabharata_bhishma_parva": ScriptureReference(
        text_name="Vyasa Mahabharata",
        division="Bhishma Parva, Adhyayas 23-40 (Srimad Bhagavad Gita)",
        sanskrit_title="श्रीमद्भगवद्गीता",
        telugu_title="శ్రీమద్భగవద్గీత",
        source_tier="primary",
        verified_episodes=["bhagavad_gita", "vishwaroopa_dharshanam", "karma_yoga"],
    ),

    # ── Shiva Purana ──────────────────────────────────────────────────────────
    "shiva_purana_rudra_samhita": ScriptureReference(
        text_name="Shiva Purana",
        division="Rudra Samhita, Sati Khanda & Parvati Khanda",
        sanskrit_title="शिवपुराणम्",
        telugu_title="శివ పురాణము (రుద్ర సంహిత)",
        source_tier="primary",
        verified_episodes=["shiva_parvati_kalyanam", "vasuki_snake_ornament", "halahala_drinking", "neelkanth"],
    ),
    "shiva_purana_kotirudra_samhita": ScriptureReference(
        text_name="Shiva Purana",
        division="Kotirudra Samhita",
        sanskrit_title="शिवपुराणम्",
        telugu_title="శివ పురాణము (కోటిరుద్ర సంహిత)",
        source_tier="primary",
        verified_episodes=["dwadasa_jyotirlingas", "somnath", "mahakaleshwar", "kedarnath"],
    ),

    # ── Devi Bhagavata & Markandeya Purana (Durga Saptashati) ────────────────
    "devi_bhagavata_purana": ScriptureReference(
        text_name="Devi Bhagavata Purana",
        division="Skandha 5",
        sanskrit_title="देवीभागवतपुराणम्",
        telugu_title="దేవీ భాగవత పురాణము",
        source_tier="primary",
        verified_episodes=["mahishasura_mardini", "shakti_tattvam", "navaratri_mahatmyam"],
    ),
    "markandeya_purana_devi_mahatmyam": ScriptureReference(
        text_name="Markandeya Purana (Devi Mahatmyam / Durga Saptashati)",
        division="Adhyayas 81-93",
        sanskrit_title="दुर्गासप्तशती",
        telugu_title="శ్రీ దుర్గా సప్తశతీ (దేవీ మాహాత్మ్యము)",
        source_tier="primary",
        verified_episodes=["mahishasura_mardini", "chanda_munda_samharam", "shumbha_nishumbha"],
    ),

    # ── Vishnu Purana ─────────────────────────────────────────────────────────
    "vishnu_purana": ScriptureReference(
        text_name="Vishnu Purana",
        division="Amsha 1 & 5",
        sanskrit_title="विष्णुपुराणम्",
        telugu_title="శ్రీ విష్ణు పురాణము",
        source_tier="primary",
        verified_episodes=["krishna_avatara", "samudra_manthan", "dhruva_charitra"],
    ),

    # ── South Indian & Sthala Puranas ─────────────────────────────────────────
    "skanda_purana_venkatachala": ScriptureReference(
        text_name="Skanda Purana (Venkatachala Mahatmyam)",
        division="Vaishnava Khanda",
        sanskrit_title="स्कन्दपुराणम्",
        telugu_title="స్కంద పురాణము (శ్రీ వేంకటాచల మాహాత్మ్యము)",
        source_tier="secondary",
        verified_episodes=["venkateswara_swami", "srinivasa_padmavathi", "tirupati_seven_hills"],
    ),
    "bhavishyottara_purana_srinivasa": ScriptureReference(
        text_name="Bhavishyottara Purana",
        division="Srinivasa Kalyana Khanda",
        sanskrit_title="भविष्योत्तरपुराणम्",
        telugu_title="భవిష్యోత్తర పురాణము",
        source_tier="secondary",
        verified_episodes=["srinivasa_kalyanam", "kubera_loan"],
    ),
    "brahmanda_purana_lalita": ScriptureReference(
        text_name="Brahmanda Purana",
        division="Uttara Khanda (Lalita Sahasranama & Trishati)",
        sanskrit_title="ब्रह्माण्डपुराणम्",
        telugu_title="బ్రహ్మాండ పురాణము (శ్రీ లలితా సహస్రనామ స్తోత్రము)",
        source_tier="primary",
        verified_episodes=["lalita_tripurasundari", "shri_yantra_mahatmyam"],
    ),
}


# ── Canonical Deity Attributes & Factuality Rules ─────────────────────────────

CANONICAL_DEITY_RULES: dict[str, dict[str, Any]] = {
    "lord_shiva": {
        "canonical_names": ["Shiva", "Mahadeva", "Neelkantha", "Nataraja", "Shankara", "Bholenath", "శివుడు", "మహాదేవుడు", "నీలకంఠుడు"],
        "weapons_and_items": ["Trishula", "Damaru", "Vasuki (serpent)", "Crescent Moon (Chandra)", "Ganga", "Rudraksha", "త్రిశూలం", "డమరుకం", "పాము", "వాసుకి"],
        "forbidden_weapons": ["Sudarshana Chakra", "Sharanga Bow", "Kaumodaki Gada", "సుదర్శన చక్రం"],
        "vahanas": ["Nandi (Bull)", "నంది"],
        "forbidden_vahanas": ["Garuda", "Mushika", "Lion", "Mayura", "గరుడ", "ఎలుక"],
        "consort": ["Parvati", "Gauri", "Shakti", "Sati", "పార్వతి", "గౌరి"],
        "forbidden_consorts": ["Lakshmi", "Saraswati", "Sita", "Radha", "లక్ష్మి", "సీత"],
        "key_episodes": ["samudra_manthan", "drinking_halahala", "wearing_vasuki", "ganga_descent", "nataraja_dance"],
        "disallowed_episodes": ["lifting_govardhan", "subduing_kaliya", "killing_mahishasura", "building_setu"],
    },
    "lord_vishnu": {
        "canonical_names": ["Vishnu", "Narayana", "Hari", "Madhava", "విష్ణువు", "నారాయణుడు"],
        "weapons_and_items": ["Sudarshana Chakra", "Panchajanya Shankha", "Kaumodaki Gada", "Padma (Lotus)", "సుదర్శన చక్రం", "శంఖం", "గద", "పద్మం"],
        "forbidden_weapons": ["Trishula", "Damaru", "Pinaka Bow", "త్రిశూలం", "డమరుకం"],
        "vahanas": ["Garuda", "Shesha Naga (Bed)", "గరుత్మంతుడు", "ఆదిశేషుడు"],
        "forbidden_vahanas": ["Nandi", "Mushika", "Tiger", "నంది"],
        "consort": ["Lakshmi", "Bhudevi", "లక్ష్మీదేవి", "భూదేవి"],
        "forbidden_consorts": ["Parvati", "Saraswati"],
        "key_episodes": ["samudra_manthan", "gajendra_moksha", "dashavatara", "mohini_avatar"],
        "disallowed_episodes": ["drinking_halahala", "holding_ganga_in_hair"],
    },
    "krishna": {
        "canonical_names": ["Krishna", "Govinda", "Gopala", "Vasudeva", "కృష్ణుడు", "గోవిందుడు", "గోపాలుడు"],
        "weapons_and_items": ["Flute (Murali)", "Sudarshana Chakra", "Peacock Feather", "మురళి", "సుదర్శన చక్రం", "నెమలి పించం"],
        "forbidden_weapons": ["Trishula", "Damaru", "త్రిశూలం"],
        "vahanas": ["Garuda (Divine)", "Chariot with 4 horses", "రథం"],
        "consort": ["Rukmini", "Satyabhama", "Radha (Eternal Companion)", "రుక్మిణి", "సత్యభామ", "రాధ"],
        "parents": ["Vasudeva", "Devaki", "Nanda Baba (Foster)", "Yashoda (Foster)", "వసుదేవుడు", "దేవకి", "యశోద"],
        "key_episodes": ["govardhan_hill", "kaliya_mardanam", "butter_stealing", "bhagavad_gita_upadesha", "raas_leela"],
        "yuga": "Dvapara Yuga",
        "disallowed_episodes": ["drinking_halahala", "killing_ravana_in_forest", "breaking_tusk_for_pen"],
    },
    "ram": {
        "canonical_names": ["Rama", "Ramachandra", "Raghava", "Sri Rama", "రాముడు", "శ్రీరామచంద్రుడు", "రాఘవుడు"],
        "weapons_and_items": ["Kodanda Bow", "Arrows", "కోదండం", "బాణాలు"],
        "forbidden_weapons": ["Trishula", "Sudarshana Chakra", "త్రిశూలం", "సుదర్శన చక్రం"],
        "consort": ["Sita", "Janaki", "సీతాదేవి", "జానకి"],
        "brothers": ["Lakshmana", "Bharata", "Shatrughna", "లక్ష్మణుడు", "భరతుడు", "శత్రుఘ్నుడు"],
        "parents": ["Dasharatha", "Kausalya", "దశరథుడు", "కౌసల్య"],
        "key_episodes": ["golden_deer_maricha", "jatayu_moksha", "shabari_bhakti", "ram_setu", "ravana_samharam"],
        "yuga": "Treta Yuga",
        "disallowed_episodes": ["lifting_govardhan", "gita_upadesha_to_arjuna", "drinking_halahala"],
    },
    "ganesha": {
        "canonical_names": ["Ganesha", "Vinayaka", "Ganapati", "Ekadanta", "Vighnaharta", "గణపతి", "వినాయకుడు", "ఏకదంతుడు"],
        "weapons_and_items": ["Broken Tusk", "Modaka", "Parashu (Axe)", "Pasha (Noose)", "ఏకదంతం", "మోదకం", "పాశం"],
        "forbidden_weapons": ["Sudarshana Chakra", "Kodanda Bow"],
        "vahanas": ["Mushika (Mouse)", "మూషిక వాహనం", "ఎలుక"],
        "forbidden_vahanas": ["Garuda", "Nandi", "Lion"],
        "parents": ["Shiva", "Parvati", "శివపార్వతులు"],
        "key_episodes": ["ekadanta_mahabharata_writing", "pradakshina_parents", "modaka_leela"],
        "disallowed_episodes": ["samudra_manthan_churning_rope", "lifting_govardhan"],
    },
    "hanuman": {
        "canonical_names": ["Hanuman", "Anjaneya", "Bajrangbali", "Maruti", "హనుమంతుడు", "ఆంజనేయుడు", "బజరంగబలి"],
        "weapons_and_items": ["Gada (Mace)", "Dronagiri Mountain", "Sanjeevani", "గద", "ద్రోణగిరి", "సంజీవని"],
        "deity_served": ["Sri Rama", "రాముడు"],
        "parents": ["Anjana", "Kesari", "Vayu (Spiritual Father)", "అంజనాదేవి", "కేసరి", "వాయుదేవుడు"],
        "key_episodes": ["leap_across_ocean", "sanjeevani_retrieval", "lanka_dahanam", "heart_opened_showing_sita_rama"],
        "disallowed_episodes": ["drinking_halahala", "killing_hiranyakashipu", "killing_mahishasura"],
    },
    "durga": {
        "canonical_names": ["Durga", "Mahishasura Mardini", "Chandika", "Bhavani", "దుర్గాదేవి", "మహిషాసుర మర్దిని"],
        "weapons_and_items": ["Trishula (from Shiva)", "Chakra (from Vishnu)", "Bow & Arrow", "Sword", "త్రిశూలం", "చక్రం", "ఖడ్గం"],
        "vahanas": ["Lion", "Tiger", "సింహ వాహనం", "సింహం", "పులి"],
        "forbidden_vahanas": ["Mouse", "Garuda", "Nandi"],
        "key_episodes": ["mahishasura_samharam", "chanda_munda_samharam", "navaratri_celebration"],
        "disallowed_episodes": ["drinking_halahala", "breaking_tusk"],
    },
    "vamana": {
        "canonical_names": ["Vamana", "Trivikrama", "Upendra", "వామనుడు", "త్రివిక్రముడు"],
        "weapons_and_items": ["Umbrella (Chhatra)", "Danda (Staff)", "Kamandalu", "గొడుగు", "కమండలం"],
        "antagonist_or_devotee": ["Mahabali", "Bali", "Sukracharya", "మహాబలి", "శుక్రాచార్యుడు"],
        "key_episodes": ["three_strides_of_land", "foot_on_mahabali_head", "trivikrama_cosmic_form"],
        "disallowed_episodes": ["drinking_halahala", "kurukshetra_war"],
    },
    "kurma": {
        "canonical_names": ["Kurma", "Tortoise Avatar", "కూర్మావతారము", "కూర్ముడు"],
        "key_episodes": ["samudra_manthan", "bearing_mount_mandara", "stabilizing_churning"],
        "weapons_and_items": ["Cosmic Shell", "Mount Mandara Base"],
        "disallowed_episodes": ["lifting_govardhan", "breaking_tusk"],
    },
    "narasimha": {
        "canonical_names": ["Narasimha", "Nrusimha", "Man-Lion", "నరసింహస్వామి", "నృసింహుడు"],
        "weapons_and_items": ["Divine Claws (Nakha)", "దివ్య నఖాలు"],
        "key_episodes": ["emergence_from_pillar", "hiranyakashipu_samharam", "protection_of_prahlada"],
        "consort": ["Chenchu Lakshmi", "Lakshmi Narasimha"],
        "disallowed_episodes": ["drinking_halahala", "writing_mahabharata"],
    },
    "7Kondala_Swami": {
        "canonical_names": ["Venkateswara", "Srinivasa", "Balaji", "Govinda", "వేంకటేశ్వరుడు", "శ్రీనివాసుడు", "ఏడుకొండలవాడు"],
        "weapons_and_items": ["Shankha", "Chakra", "Varada Hasta", "Kati Hasta", "శంఖం", "చక్రం"],
        "consort": ["Padmavathi", "Alamelu Manga", "Sri Devi", "పద్మావతి", "అలమేలు మంగ"],
        "location": ["Tirumala", "Seshachalam Hills", "తిరుమల", "ఏడుకొండలు"],
        "key_episodes": ["srinivasa_kalyanam", "kubera_debt", "vakula_devi_motherly_love"],
        "disallowed_episodes": ["drinking_halahala", "killing_ravana"],
    },
}


# ── Known Chronological Contradictions & Timeline Eras ────────────────────────

YUGA_ORDER = {
    "Satya Yuga (Krita Yuga)": 1,
    "Treta Yuga": 2,
    "Dvapara Yuga": 3,
    "Kali Yuga": 4,
}

AVATAR_YUGA_MAP = {
    "matsya": "Satya Yuga (Krita Yuga)",
    "kurma": "Satya Yuga (Krita Yuga)",
    "varaha": "Satya Yuga (Krita Yuga)",
    "narasimha": "Satya Yuga (Krita Yuga)",
    "vamana": "Treta Yuga",
    "parashurama": "Treta Yuga",
    "ram": "Treta Yuga",
    "krishna": "Dvapara Yuga",
    "7Kondala_Swami": "Kali Yuga",
}


# ── Public Verification Functions ─────────────────────────────────────────────

def get_scripture_reference_for_topic(topic: str, deity: str = "") -> ScriptureReference | None:
    """Finds the most specific primary scripture reference for a topic."""
    t_clean = topic.lower()
    d_clean = deity.lower()

    if any(k in t_clean for k in ["vasuki", "snake", "serpent", "halahala", "neelkanth"]):
        return CANONICAL_SCRIPTURES["shiva_purana_rudra_samhita"]
    if any(k in t_clean for k in ["govardhan", "mountain", "hill"]):
        return CANONICAL_SCRIPTURES["bhagavata_purana_govardhan"]
    if any(k in t_clean for k in ["kaliya", "snake dance", "yamuna"]):
        return CANONICAL_SCRIPTURES["bhagavata_purana_kaliya_mardanam"]
    if any(k in t_clean for k in ["vamana", "mahabali", "bali", "three strides"]):
        return CANONICAL_SCRIPTURES["bhagavata_purana_vamana"]
    if any(k in t_clean for k in ["narasimha", "prahlada", "hiranyakashipu"]):
        return CANONICAL_SCRIPTURES["bhagavata_purana_narasimha"]
    if any(k in t_clean for k in ["kurma", "tortoise", "mandara"]):
        return CANONICAL_SCRIPTURES["bhagavata_purana_samudra_manthan"]
    if any(k in t_clean for k in ["maricha", "golden deer", "deer", "shabari", "jatayu"]):
        return CANONICAL_SCRIPTURES["valmiki_ramayana_aranya_kanda"]
    if any(k in t_clean for k in ["ram setu", "setu", "bridge"]):
        return CANONICAL_SCRIPTURES["valmiki_ramayana_yuddha_kanda"]
    if any(k in t_clean for k in ["sanjeevani", "dronagiri", "lanka dahanam"]):
        return CANONICAL_SCRIPTURES["valmiki_ramayana_yuddha_kanda"]
    if any(k in t_clean for k in ["broken tusk", "ekadanta", "vyasa", "mahabharata writer"]):
        return CANONICAL_SCRIPTURES["mahabharata_adi_parva"]
    if any(k in t_clean for k in ["mahishasura", "durga", "chandi"]):
        return CANONICAL_SCRIPTURES["markandeya_purana_devi_mahatmyam"]
    if any(k in t_clean for k in ["venkateswara", "balaji", "srinivasa", "tirupati"]):
        return CANONICAL_SCRIPTURES["skanda_purana_venkatachala"]

    # Fallback to general deity references
    if "shiva" in d_clean:
        return CANONICAL_SCRIPTURES["shiva_purana_rudra_samhita"]
    if "krishna" in d_clean:
        return CANONICAL_SCRIPTURES["bhagavata_purana_govardhan"]
    if "ram" in d_clean:
        return CANONICAL_SCRIPTURES["valmiki_ramayana_bala_kanda"]
    if "ganesha" in d_clean:
        return CANONICAL_SCRIPTURES["mahabharata_adi_parva"]
    if "durga" in d_clean:
        return CANONICAL_SCRIPTURES["markandeya_purana_devi_mahatmyam"]

    return None


def verify_scriptural_claim(
    topic: str,
    deity_key: str,
    text_to_verify: str,
) -> tuple[bool, list[str]]:
    """
    Validates that a topic, script, or narration does not contain gross
    theological, genealogical, or attribute contradictions.

    Returns:
        (is_valid, list_of_violations)
    """
    violations = []
    text_lower = text_to_verify.lower()

    rules = CANONICAL_DEITY_RULES.get(deity_key)
    if not rules:
        # Unknown/unlisted deity - pass through gracefully without blocking
        return True, []

    # 1. Weapon & Item Check
    for forbidden_weapon in rules.get("forbidden_weapons", []):
        if forbidden_weapon.lower() in text_lower:
            violations.append(
                f"Deity '{deity_key}' is canonically associated with items {rules['weapons_and_items'][:2]}, "
                f"NOT '{forbidden_weapon}'."
            )

    # 2. Vahana Check
    for forbidden_vahana in rules.get("forbidden_vahanas", []):
        if forbidden_vahana.lower() in text_lower:
            violations.append(
                f"Deity '{deity_key}' ride/vehicle is canonically {rules['vahanas']}, "
                f"NOT '{forbidden_vahana}'."
            )

    # 3. Consort / Family Check
    for forbidden_consort in rules.get("forbidden_consorts", []):
        pattern = rf"\b{re.escape(forbidden_consort.lower())}\b"
        if re.search(pattern, text_lower):
            # Check if mentioned as consort/wife
            consort_indicators = ["wife", "consort", "bharya", "devi", "పతి", "భార్య", "సతీమణి"]
            if any(ind in text_lower for ind in consort_indicators):
                violations.append(
                    f"Consort contradiction: Deity '{deity_key}' consort is {rules.get('consort')}, "
                    f"NOT '{forbidden_consort}'."
                )

    # 4. Disallowed Episode Attribution
    for disallowed_ep in rules.get("disallowed_episodes", []):
        ep_words = disallowed_ep.split("_")
        if all(w in text_lower for w in ep_words):
            violations.append(
                f"Episode mismatch: '{disallowed_ep}' cannot be attributed to deity '{deity_key}'."
            )

    # 5. False chapter/citation checks (e.g. fabricated chapter references)
    fake_patterns = [
        r"bhagavata purana chapter 999",
        r"ramayana canto 450",
        r"shiva purana chapter 888",
    ]
    for pat in fake_patterns:
        if re.search(pat, text_lower):
            violations.append(f"Fabricated or non-existent scriptural citation detected: '{pat}'.")

    return len(violations) == 0, violations


def check_chronology_compatibility(deity_a: str, deity_b: str) -> tuple[bool, str]:
    """
    Checks if two avatars can co-exist as peers in the same timeline without scriptural precedent.
    Rama (Treta) and Krishna (Dvapara) are distinct Yuga avatars.
    """
    yuga_a = AVATAR_YUGA_MAP.get(deity_a)
    yuga_b = AVATAR_YUGA_MAP.get(deity_b)

    if yuga_a and yuga_b and yuga_a != yuga_b:
        # Known allowed exceptions in shastras: Parashurama (Chiranjeevi) meets Rama in Balakanda
        if {deity_a, deity_b} == {"parashurama", "ram"}:
            return True, "Scripturally permitted encounter (Valmiki Ramayana Bala Kanda)"
        # Hanuman (Chiranjeevi) in Mahabharata (Kalyana Saugandhika / Arjuna Chariot Flag)
        if deity_a == "hanuman" or deity_b == "hanuman":
            return True, "Scripturally permitted Chiranjeevi presence across Yugas"

        return False, (
            f"Chronological Yuga contradiction: '{deity_a}' belongs to {yuga_a}, "
            f"while '{deity_b}' belongs to {yuga_b}."
        )

    return True, "Chronologically compatible"
