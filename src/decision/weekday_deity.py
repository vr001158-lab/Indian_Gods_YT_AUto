# src/decision/weekday_deity.py
# Automatic Hindu Gods by Day of the Week & Deterministic Rotation System
#
# Reference Hindu Weekday Deity Mapping:
#   Sunday (Ravivar):    Lord Surya, Kaal Bhairav
#   Monday (Somvar):     Lord Shiva, Goddess Parvati, Chandra Deva
#   Tuesday (Mangalvar): Lord Hanuman, Lord Ganesha, Goddess Durga, Goddess Kali, Lord Kartikeya / Skanda
#   Wednesday (Budhvar): Budha, Lord Ganesha, Lord Krishna, Lord Vithal
#   Thursday (Guruvar):  Lord Vishnu, Brihaspati, Lord Krishna
#   Friday (Shukravar):  Goddess Mahalakshmi, Santoshi Ma, Annapurneshwari, Goddess Durga / Shakti
#   Saturday (Shaniwar): Lord Shani, Lord Hanuman
#
# Timezone: Asia/Kolkata (UTC+5:30)

from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

try:
    from zoneinfo import ZoneInfo
    KOLKATA_TZ = ZoneInfo("Asia/Kolkata")
except Exception:
    KOLKATA_TZ = timezone(timedelta(hours=5, minutes=30))


WEEKDAY_DEITY_MAPPING: dict[int, dict[str, Any]] = {
    # 0 = Monday (Somvar)
    0: {
        "english_day": "Monday",
        "sanskrit_day": "Somvar",
        "primary_deities": ["lord_shiva", "parvathi", "chandra"],
        "display_names": {
            "lord_shiva": "Lord Shiva",
            "parvathi": "Goddess Parvati",
            "chandra": "Chandra Deva",
        },
        "significance": [
            "Mental peace",
            "Purity",
            "Family prosperity",
            "Marital harmony",
        ],
        "visual_and_offering_context": {
            "attire": "White clothes",
            "flowers": "White flowers and Bilva leaves",
            "offerings": "Milk and holy water offered to Shiva Lingam",
            "motifs": "Trishula, Damaru, crescent moon, sacred ash (vibhuti)",
        },
    },
    # 1 = Tuesday (Mangalvar)
    1: {
        "english_day": "Tuesday",
        "sanskrit_day": "Mangalvar",
        "primary_deities": ["hanuman", "ganesha", "durga", "kali", "subramanya"],
        "display_names": {
            "hanuman": "Lord Hanuman",
            "ganesha": "Lord Ganesha",
            "durga": "Goddess Durga",
            "kali": "Goddess Kali",
            "subramanya": "Lord Kartikeya / Skanda",
        },
        "significance": [
            "Courage",
            "Strength",
            "Protection",
            "Removing obstacles",
        ],
        "visual_and_offering_context": {
            "attire": "Red clothes",
            "flowers": "Red hibiscus and bright red garlands",
            "offerings": "Sindoor, jaggery, and traditional sweets",
            "motifs": "Gada, Vel, Trishula, Modak, sacred fire",
        },
    },
    # 2 = Wednesday (Budhvar)
    2: {
        "english_day": "Wednesday",
        "sanskrit_day": "Budhvar",
        "primary_deities": ["budha", "ganesha", "krishna", "vithal"],
        "display_names": {
            "budha": "Budha",
            "ganesha": "Lord Ganesha",
            "krishna": "Lord Krishna",
            "vithal": "Lord Vithal",
        },
        "significance": [
            "Intellect",
            "Wisdom",
            "Communication",
            "Business and financial success",
        ],
        "visual_and_offering_context": {
            "attire": "Green clothes",
            "flowers": "Green moong dal offerings, Tulsi leaves",
            "offerings": "Durva grass for Ganesha, butter and sweets for Krishna",
            "motifs": "Durva blades, peacock feather, flute, sacred scrolls",
        },
    },
    # 3 = Thursday (Guruvar)
    3: {
        "english_day": "Thursday",
        "sanskrit_day": "Guruvar",
        "primary_deities": ["lord_vishnu", "brihaspati", "krishna"],
        "display_names": {
            "lord_vishnu": "Lord Vishnu",
            "brihaspati": "Brihaspati",
            "krishna": "Lord Krishna",
        },
        "significance": [
            "Wealth",
            "Happiness",
            "Spiritual growth",
            "Family prosperity",
        ],
        "visual_and_offering_context": {
            "attire": "Yellow clothes (Pitambara)",
            "flowers": "Yellow marigold and yellow flowers",
            "offerings": "Chana dal, pure ghee, and banana tree worship",
            "motifs": "Sudarshana chakra, Shankha, yellow halo, sacred scriptures",
        },
    },
    # 4 = Friday (Shukravar)
    4: {
        "english_day": "Friday",
        "sanskrit_day": "Shukravar",
        "primary_deities": ["lakshmi_devi", "santoshi_ma", "annapurneshwari", "durga"],
        "display_names": {
            "lakshmi_devi": "Goddess Mahalakshmi",
            "santoshi_ma": "Santoshi Ma",
            "annapurneshwari": "Annapurneshwari",
            "durga": "Goddess Durga",
        },
        "significance": [
            "Material wealth",
            "Beauty",
            "Prosperity",
            "Removing obstacles",
        ],
        "visual_and_offering_context": {
            "attire": "White or rich red attire with golden embroidery",
            "flowers": "Pink lotus flowers and fragrant jasmine",
            "offerings": "Kheer, milk-based payasam, and jaggery sweets",
            "motifs": "Golden Kalasha, overflowing coins, sacred lotus, divine aura",
        },
    },
    # 5 = Saturday (Shaniwar)
    5: {
        "english_day": "Saturday",
        "sanskrit_day": "Shaniwar",
        "primary_deities": ["shani", "hanuman"],
        "display_names": {
            "shani": "Lord Shani",
            "hanuman": "Lord Hanuman",
        },
        "significance": [
            "Discipline",
            "Reducing hardships",
            "Protection from adversities",
        ],
        "visual_and_offering_context": {
            "attire": "Black or deep dark blue clothes",
            "flowers": "Blue flowers and Aparajita blossoms",
            "offerings": "Mustard or sesame oil, black sesame seeds, and deepam",
            "motifs": "Iron lamp with sesame oil, crow motif, mountain-carrying stance",
        },
    },
    # 6 = Sunday (Ravivar)
    6: {
        "english_day": "Sunday",
        "sanskrit_day": "Ravivar",
        "primary_deities": ["surya", "kaal_bhairav"],
        "display_names": {
            "surya": "Lord Surya",
            "kaal_bhairav": "Kaal Bhairav",
        },
        "significance": [
            "Health",
            "Vitality",
            "Success",
            "Relief from skin ailments",
        ],
        "visual_and_offering_context": {
            "attire": "Crimson and bright orange attire",
            "flowers": "Red lotus and red hibiscus flowers",
            "offerings": "Red sandalwood tilak, offering water (Arghya) to rising Sun",
            "motifs": "Seven-horse solar chariot, bright solar disk, cosmic radiance",
        },
    },
}

# Mapping of minor/aspect deities to primary canonical repository asset folders.
# Distinct deity identities must NEVER be conflated with shared parent folders.
# Each deity has its own distinct identity; a shared folder never implies that every asset
# inside it depicts every deity.
DEITY_REPOSITORY_ALIAS: dict[str, str] = {
    "kaal_bhairav": "kaal_bhairav",
    "chandra": "chandra",
    "kali": "kali",
    "durga": "durga",
    "subramanya": "subramanya",
    "budha": "budha",
    "vithal": "vithal",
    "brihaspati": "brihaspati",
    "santoshi_ma": "santoshi_ma",
    "annapurneshwari": "annapurneshwari",
    "shani": "shani",
    "surya": "surya",
    "lord_shiva": "lord_shiva",
    "parvathi": "parvathi",
    "hanuman": "hanuman",
    "ganesha": "ganesha",
    "krishna": "krishna",
    "lord_vishnu": "lord_vishnu",
    "lakshmi_devi": "lakshmi_devi",
}

# Authoritative alias-to-canonical mapping for weekday deity identification
DEITY_CANONICAL_ALIASES: dict[str, str] = {
    # Lord Shiva
    "shiva": "lord_shiva",
    "lord_shiva": "lord_shiva",
    "mahadev": "lord_shiva",
    "bholenath": "lord_shiva",
    # Goddess Parvati
    "parvati": "parvathi",
    "parvathi": "parvathi",
    "goddess_parvati": "parvathi",
    # Chandra Deva
    "chandra": "chandra",
    "chandra_deva": "chandra",
    "chandradeva": "chandra",
    # Lord Hanuman
    "hanuman": "hanuman",
    "lord_hanuman": "hanuman",
    "bajrangbali": "hanuman",
    "anjaneya": "hanuman",
    # Lord Ganesha
    "ganesha": "ganesha",
    "ganesh": "ganesha",
    "vinayaka": "ganesha",
    "lord_ganesha": "ganesha",
    # Goddess Durga
    "durga": "durga",
    "goddess_durga": "durga",
    # Goddess Kali
    "kali": "kali",
    "goddess_kali": "kali",
    "mahakali": "kali",
    # Lord Kartikeya / Skanda
    "subramanya": "subramanya",
    "kartikeya": "subramanya",
    "skanda": "subramanya",
    "lord_kartikeya": "subramanya",
    "murugan": "subramanya",
    # Budha
    "budha": "budha",
    "budha_deva": "budha",
    # Lord Krishna
    "krishna": "krishna",
    "lord_krishna": "krishna",
    "gopala": "krishna",
    # Lord Vithal
    "vithal": "vithal",
    "vitthal": "vithal",
    "vithoba": "vithal",
    "lord_vithal": "vithal",
    # Lord Vishnu
    "vishnu": "lord_vishnu",
    "lord_vishnu": "lord_vishnu",
    "narayana": "lord_vishnu",
    # Brihaspati
    "brihaspati": "brihaspati",
    "guru_brihaspati": "brihaspati",
    # Goddess Mahalakshmi
    "lakshmi_devi": "lakshmi_devi",
    "mahalakshmi": "lakshmi_devi",
    "goddess_mahalakshmi": "lakshmi_devi",
    "lakshmi": "lakshmi_devi",
    # Santoshi Ma
    "santoshi_ma": "santoshi_ma",
    "santoshima": "santoshi_ma",
    # Annapurneshwari
    "annapurneshwari": "annapurneshwari",
    "annapurna": "annapurneshwari",
    # Lord Shani
    "shani": "shani",
    "lord_shani": "shani",
    # Lord Surya
    "surya": "surya",
    "lord_surya": "surya",
    "suryadeva": "surya",
    # Kaal Bhairav
    "kaal_bhairav": "kaal_bhairav",
    "bhairav": "kaal_bhairav",
    "kalabhairav": "kaal_bhairav",
    "kala_bhairava": "kaal_bhairav",
}


def is_deity_eligible_for_weekday(deity_name: str, dt: Optional[datetime] = None) -> bool:
    """
    Checks if a deity (or alias) belongs to the authoritative eligibility group for the day.
    """
    if not deity_name:
        return False
    info = get_weekday_info(dt)
    target = deity_name.strip().lower()
    canonical = DEITY_CANONICAL_ALIASES.get(target, target)
    eligible = [d.lower() for d in info["primary_deities"]]
    return target in eligible or canonical in eligible


def get_current_kolkata_datetime() -> datetime:
    """Returns the current datetime in the Asia/Kolkata timezone."""
    return datetime.now(KOLKATA_TZ)


def get_weekday_info(dt: Optional[datetime] = None) -> dict[str, Any]:
    """
    Returns the complete devotional weekday configuration for a given datetime
    (or current Asia/Kolkata time if None).
    """
    if dt is None:
        dt = get_current_kolkata_datetime()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=KOLKATA_TZ)
    else:
        dt = dt.astimezone(KOLKATA_TZ)

    weekday_idx = dt.weekday()
    return WEEKDAY_DEITY_MAPPING[weekday_idx]


def rotate_deity_for_day(
    dt: datetime,
    eligible_deities: list[str],
    history: Optional[list[dict[str, Any]]] = None,
) -> str:
    """
    Deterministically rotates through eligible deities for a weekday based on
    calendar week and day offset, avoiding random repetition while ensuring
    every deity is scheduled systematically over time.
    """
    if not eligible_deities:
        return "lord_shiva"
    if len(eligible_deities) == 1:
        return eligible_deities[0]

    iso_year, iso_week, _ = dt.isocalendar()
    day_in_month = dt.day

    # Deterministic rotation key based on year, ISO week, and month-day band
    rotation_seed = (iso_year * 53 + iso_week + (day_in_month // 7))
    selected_idx = rotation_seed % len(eligible_deities)
    candidate = eligible_deities[selected_idx]

    # If recent history is available, prevent immediate back-to-back repeats
    if history:
        recent_deities = []
        for rec in history[:3]:
            d = rec.get("deity") or rec.get("resolved_deity")
            if d:
                recent_deities.append(str(d).lower())
        if candidate in recent_deities:
            # Advance to the next eligible deity in the deterministic rotation
            selected_idx = (selected_idx + 1) % len(eligible_deities)
            candidate = eligible_deities[selected_idx]

    return candidate


def select_weekday_deity(
    dt: Optional[datetime] = None,
    history: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """
    Deterministically selects the day's scheduled deity and devotional context.

    Returns
    -------
    dict with keys:
      - weekday_index: int (0=Monday..6=Sunday)
      - english_day: str
      - sanskrit_day: str
      - scheduled_deity: str (canonical deity key)
      - display_name: str
      - repository_folder: str (canonical asset folder)
      - eligible_deities: list[str]
      - significance: list[str]
      - visual_and_offering_context: dict
      - kolkata_date: str (YYYY-MM-DD)
    """
    if dt is None:
        dt = get_current_kolkata_datetime()
    elif dt.tzinfo is None:
        dt = dt.replace(tzinfo=KOLKATA_TZ)
    else:
        dt = dt.astimezone(KOLKATA_TZ)

    day_info = get_weekday_info(dt)
    eligible = day_info["primary_deities"]
    chosen_deity = rotate_deity_for_day(dt, eligible, history=history)

    repo_folder = DEITY_REPOSITORY_ALIAS.get(chosen_deity, chosen_deity)
    display_name = day_info["display_names"].get(chosen_deity, chosen_deity.replace("_", " ").title())

    return {
        "weekday_index": dt.weekday(),
        "english_day": day_info["english_day"],
        "sanskrit_day": day_info["sanskrit_day"],
        "scheduled_deity": chosen_deity,
        "display_name": display_name,
        "repository_folder": repo_folder,
        "eligible_deities": list(eligible),
        "significance": list(day_info["significance"]),
        "visual_and_offering_context": dict(day_info["visual_and_offering_context"]),
        "kolkata_date": dt.strftime("%Y-%m-%d"),
    }


def get_day_of_week_deity_bonus(deity_key: Optional[str], now_dt: Optional[datetime] = None) -> float:
    """
    Calculates cultural calendar bonus (+15.0 for scheduled deity, +8.0 for eligible deities)
    using the Asia/Kolkata Hindu weekday calendar.

    Audited rule: A shared repository folder NEVER gives an unrelated deity the scheduled deity's +15 bonus.
    The +15.0 bonus is awarded strictly when the candidate deity matches the scheduled deity identity.
    """
    if not deity_key:
        return 0.0

    d_info = select_weekday_deity(now_dt)
    target = deity_key.strip().lower()
    canonical = DEITY_CANONICAL_ALIASES.get(target, target)
    scheduled = d_info["scheduled_deity"].lower()

    # Exact identity match for scheduled deity (+15.0)
    if target == scheduled or canonical == scheduled:
        return 15.0

    # Eligible deities of the weekday (+8.0)
    eligible = [d.lower() for d in d_info["eligible_deities"]]
    if target in eligible or canonical in eligible:
        return 8.0

    return 0.0
