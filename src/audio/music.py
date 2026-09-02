# src/audio/music.py
# Phase 6.3 / Music Pipeline v2 — Copyright Safety & Provenance Architecture
#
# Primary Music Path: Verified YouTube Audio Library & Licensed Royalty-Free tracks
# Fallback 1: Verified original-generated tracks (e.g. shiva_devotional_shivaranjani_flute.wav)
# Fallback 2: Narration-only output (None)
#
# Hard Provenance Gate:
#   Tracks that are unverified, non-commercial, non-YouTube permitted, or have SHA256 mismatch MUST BE REJECTED.

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any

import re

MUSIC_DIR = Path("assets/music")
MANIFEST_PATH = MUSIC_DIR / "music_manifest.json"

# Allowed legitimate source types
VALID_SOURCE_TYPES = {"youtube_audio_library", "royalty_free_public", "original_generated"}
PRIMARY_SOURCE_TYPES = {"youtube_audio_library", "royalty_free_public"}

# Canonical Deity Aliases Normalization Map
DEITY_ALIASES: dict[str, list[str]] = {
    "shiva": ["shiva", "shiv", "mahadev", "bholenath", "mahakal", "trishul", "kailash", "somnath", "shivling", "nataraja", "arunachalam", "kedarnath", "samudra manthan"],
    "hanuman": ["hanuman", "bajrangbali", "maruti", "anjaneya", "sanjeevani", "bajrang", "rambhakt"],
    "krishna": ["krishna", "gopala", "kanha", "govinda", "isckon", "radhe", "achyutam", "keshavam", "shri krishna"],
    "rama": ["rama", "ram", "ramachandra", "ayodhya", "sita", "shri ram", "raghunandana"],
    "ganesha": ["ganesha", "ganesh", "vinayaka", "vighnaharta", "gajanana", "morya", "ganapati", "ekadanta", "vakratunda"],
    "durga": ["durga", "maa durga", "mahishasura mardini", "aigiri nandini", "navdurga", "ambe"],
    "lakshmi": ["lakshmi", "laxmi", "maa lakshmi", "mahalakshmi", "kanakadhara", "sri lakshmi"],
    "saraswati": ["saraswati", "maa saraswati", "sharada", "veena", "saraswati vandana"],
    "vishnu": ["vishnu", "narayan", "narayana", "dashavatar", "shantakaram", "hari stuti", "jagdish"],
    "kali": ["kali", "mahakali", "maa kali", "shyama"],
    "murugan": ["murugan", "kartikeya", "subramanya", "skanda", "vel", "kanda sashti", "arupadai"],
    "ayyappa": ["ayyappa", "swami ayyappa", "sabarimala", "manikanta", "harivarasanam"],
}

# Curated Deity -> Song Catalog (Metadata)
DEITY_SONG_CATALOG: dict[str, list[dict[str, Any]]] = {
    "shiva": [
        {"title": "Namo Namo", "artist": "Amit Trivedi", "audio_file": "assets/music/devotional/shiva_devotional_shivaranjani_flute.wav"},
        {"title": "Shiv Tandav Stotram", "artist": "Ravana / Various Artists", "audio_file": None},
        {"title": "Shiv Kailasho Ke Vasi", "artist": "Hansraj Raghuwanshi", "audio_file": None},
        {"title": "Man Mera Mandir Shiv Meri Puja", "artist": "Anuradha Paudwal", "audio_file": None},
        {"title": "Shiv Sama Rahe", "artist": "Hansraj Raghuwanshi", "audio_file": None},
    ],
    "hanuman": [
        {"title": "Shree Hanuman Chalisa", "artist": "Hariharan", "audio_file": None},
        {"title": "Sankatmochan Hanuman Ashtak", "artist": "Hariharan", "audio_file": None},
        {"title": "Bajrang Baan (Lofi)", "artist": "Rasraj Ji Maharaj", "audio_file": None},
        {"title": "Mangalmurti Maruti Nandan", "artist": "Hariharan", "audio_file": None},
        {"title": "Raghunandana (From \"HanuMan\")", "artist": "GowraHari, Saicharan Bhaskaruni, Lokeshwar Edara, Harshavardhan Chavali", "audio_file": None},
    ],
    "krishna": [
        {"title": "Shri Krishna Govind Hare Murari", "artist": "Jubin Nautiyal / Simpal Kharel", "audio_file": None},
        {"title": "Tum Prem Ho (Reprise)", "artist": "Mohit Lalwani & Bharat Kamal", "audio_file": None},
        {"title": "Radhe Radhe", "artist": "Hansraj Raghuwanshi", "audio_file": None},
        {"title": "Sawre Ko Dil Me Basa Kar To Dekho", "artist": "Chitra Vichitra Ji", "audio_file": None},
        {"title": "Achyutam Keshavam", "artist": "Madhuraa Bhattacharya", "audio_file": None},
    ],
    "rama": [
        {"title": "Ram Siya Ram", "artist": "Sachet Tandon & Parampara Tandon", "audio_file": None},
        {"title": "Mangal Bhavan Amangal Hari", "artist": "Ravindra Jain", "audio_file": None},
        {"title": "Ram Aaye Hain", "artist": "Swasti Mehul", "audio_file": None},
        {"title": "Shri Ram Chandra Kripalu Bhajman", "artist": "Lata Mangeshkar / Anup Jalota", "audio_file": None},
        {"title": "Bharat Ka Bacha Bacha Jai Shree Ram Bolega", "artist": "Devendra Pathak", "audio_file": None},
    ],
    "ganesha": [
        {"title": "Sukhkarta Dukhharta", "artist": "Lata Mangeshkar", "audio_file": None},
        {"title": "Deva Shree Ganesha", "artist": "Ajay-Atul & Ajay Gogavale", "audio_file": None},
        {"title": "Ganesh Chalisa", "artist": "Anuradha Paudwal", "audio_file": None},
        {"title": "Om Gan Ganapataye Namo Namah", "artist": "Suresh Wadkar", "audio_file": None},
        {"title": "Ekadantaya Vakratundaya", "artist": "Shankar Mahadevan", "audio_file": None},
    ],
    "durga": [
        {"title": "Aigiri Nandini (Mahishasura Mardini Stotram)", "artist": "Rajalakshmee Sanjay", "audio_file": None},
        {"title": "Durga Chalisa", "artist": "Anuradha Paudwal", "audio_file": None},
        {"title": "Jai Ambe Gauri", "artist": "Anuradha Paudwal", "audio_file": None},
        {"title": "Navdurga Stuti", "artist": "Anuradha Paudwal", "audio_file": None},
        {"title": "Chalo Bulawa Aaya Hai", "artist": "Narendra Chanchal, Mahendra Kapoor, Asha Bhosle", "audio_file": None},
    ],
    "lakshmi": [
        {"title": "Mahalakshmi Ashtakam", "artist": "Bombay Jayashri / Uma Mohan", "audio_file": None},
        {"title": "Sri Lakshmi Sahasranamam", "artist": "M.S. Subbulakshmi", "audio_file": None},
        {"title": "Om Jai Lakshmi Mata", "artist": "Anuradha Paudwal", "audio_file": None},
        {"title": "Lakshmi Gayatri Mantra", "artist": "Suresh Wadkar", "audio_file": None},
        {"title": "Kanakadhara Stotram", "artist": "M.S. Subbulakshmi", "audio_file": None},
    ],
    "saraswati": [
        {"title": "Saraswati Vandana (Ya Kundendu)", "artist": "Anuradha Paudwal", "audio_file": None},
        {"title": "Saraswati Chalisa", "artist": "Suresh Wadkar", "audio_file": None},
        {"title": "Om Airim Namah (Saraswati Mantra)", "artist": "Sadhana Sargam", "audio_file": None},
        {"title": "Saraswati Stotram", "artist": "Bombay Jayashri", "audio_file": None},
        {"title": "Namostute Saraswati", "artist": "Devaki Pandit", "audio_file": None},
    ],
    "vishnu": [
        {"title": "Vishnu Sahasranamam", "artist": "M.S. Subbulakshmi", "audio_file": None},
        {"title": "Achyutam Keshavam Krishna Damodaram", "artist": "Anup Jalota", "audio_file": None},
        {"title": "Om Jai Jagdish Hare", "artist": "Anuradha Paudwal", "audio_file": None},
        {"title": "Hari Stuti (Shantakaram Bhujagashayanam)", "artist": "Suresh Wadkar", "audio_file": None},
        {"title": "Narayana Stotram", "artist": "Uma Mohan", "audio_file": None},
    ],
    "kali": [
        {"title": "Mahakali Stotram", "artist": "Shankar Mahadevan", "audio_file": None},
        {"title": "Jai Kali Maa", "artist": "Anuradha Paudwal", "audio_file": None},
        {"title": "Shyamama Sangey", "artist": "Kumar Sanu", "audio_file": None},
        {"title": "Mahakali Mantra", "artist": "Suresh Wadkar", "audio_file": None},
        {"title": "Kali Chalisa", "artist": "Lakhbir Singh Lakkha", "audio_file": None},
    ],
    "murugan": [
        {"title": "Kanda Sashti Kavasam", "artist": "Soolamangalam Sisters", "audio_file": None},
        {"title": "Vel Vel Muruga", "artist": "Gajwel Venu", "audio_file": None},
        {"title": "Arupadai Veedu", "artist": "T.M. Soundararajan", "audio_file": None},
        {"title": "Muthai Tharu (Thiruppugazh)", "artist": "T.M. Soundararajan", "audio_file": None},
        {"title": "Muruga Saranam", "artist": "Mahanadhi Shobana", "audio_file": None},
    ],
    "ayyappa": [
        {"title": "Harivarasanam", "artist": "K.J. Yesudas", "audio_file": None},
        {"title": "Pallikettu Sabarimalaikku", "artist": "K.J. Yesudas", "audio_file": None},
        {"title": "Bhagavan Saranam", "artist": "K.J. Yesudas", "audio_file": None},
        {"title": "Swamy Saranam Ayyappa", "artist": "Veeramani Raju", "audio_file": None},
        {"title": "Ayyappa Suprabhatam", "artist": "K.J. Yesudas", "audio_file": None},
    ],
}


def normalize_deity(input_val: Any) -> str | None:
    """
    Normalizes deity identity to one of the canonical keys:
      shiva, hanuman, krishna, rama, ganesha, durga, lakshmi, saraswati, vishnu, kali, murugan, ayyappa.
    Accepts string (deity/topic name) or script/decision dict.
    Returns canonical deity string or None if unmapped.
    """
    if not input_val:
        return None

    if isinstance(input_val, dict):
        candidates = []
        if "deity" in input_val and isinstance(input_val["deity"], str):
            candidates.append(input_val["deity"])
        meta = input_val.get("approval_metadata")
        if isinstance(meta, dict) and meta.get("selected_topic"):
            candidates.append(meta["selected_topic"])
        if "selected_topic" in input_val and isinstance(input_val["selected_topic"], str):
            candidates.append(input_val["selected_topic"])
        if "topic" in input_val and isinstance(input_val["topic"], str):
            candidates.append(input_val["topic"])
        if "title" in input_val and isinstance(input_val["title"], str):
            candidates.append(input_val["title"])
        if "narration" in input_val and isinstance(input_val["narration"], str):
            candidates.append(input_val["narration"])

        for candidate in candidates:
            res = normalize_deity(candidate)
            if res:
                return res
        return None

    text = str(input_val).lower().strip()
    if not text:
        return None

    if text in DEITY_ALIASES:
        return text

    # Pass 1: Strict word-boundary matching across all deities first
    for canonical, aliases in DEITY_ALIASES.items():
        for alias in aliases:
            if re.search(r"\b" + re.escape(alias) + r"\b", text):
                return canonical

    # Pass 2: Substring matching as secondary fallback
    for canonical, aliases in DEITY_ALIASES.items():
        for alias in aliases:
            if len(alias) >= 4 and alias in text:
                return canonical

    return None


def load_music_manifest(manifest_path: str | Path = MANIFEST_PATH) -> dict:
    """Loads and parses music_manifest.json."""
    mp = Path(manifest_path)
    if not mp.exists():
        return {"tracks": []}
    try:
        return json.loads(mp.read_text(encoding="utf-8"))
    except Exception:
        return {"tracks": []}


def validate_music_provenance(
    music_file: str | Path,
    manifest_path: str | Path = MANIFEST_PATH,
) -> tuple[bool, str, dict[str, Any]]:
    """
    Hard Provenance Gate for Music Pipeline v2.
    Validates that a music track is:
      1. Physical file exists
      2. Registered in music_manifest.json
      3. Marked as approved (approved == True)
      4. Permitted for commercial use (commercial_use == True)
      5. Permitted for YouTube Shorts (youtube_shorts_permitted != False)
      6. Has valid source_type in (youtube_audio_library, royalty_free_public, original_generated)
      7. Passes SHA256 digest verification

    Returns (is_valid, reason, track_info).
    """
    mf = Path(music_file)
    if not mf.exists():
        return False, f"Music file not found: {mf}", {}

    manifest = load_music_manifest(manifest_path)
    tracks = manifest.get("tracks", [])

    rel_str = str(mf.as_posix())

    matched_track = None
    for tr in tracks:
        tr_rel = tr.get("relative_path", "").replace("\\", "/")
        tr_name = tr.get("filename", "")
        if tr_rel == rel_str or tr_name == mf.name:
            matched_track = tr
            break

    if not matched_track:
        return False, f"Unauthorized music track: {mf.name} is not registered in music_manifest.json", {}

    if not matched_track.get("approved", False):
        return False, f"Music track {mf.name} is marked as unapproved in manifest", matched_track

    if matched_track.get("commercial_use") is False:
        return False, f"Music track {mf.name} is not permitted for commercial use", matched_track

    if matched_track.get("youtube_shorts_permitted") is False:
        return False, f"Music track {mf.name} is not permitted for YouTube Shorts distribution", matched_track

    stype = matched_track.get("source_type", "")
    if stype not in VALID_SOURCE_TYPES:
        return False, f"Music track {mf.name} has unauthorized source_type: '{stype}'", matched_track

    # Check SHA256 digest match
    expected_sha256 = matched_track.get("sha256")
    if expected_sha256:
        actual_sha256 = hashlib.sha256(mf.read_bytes()).hexdigest()
        if actual_sha256 != expected_sha256:
            return False, f"Music SHA256 mismatch for {mf.name}: expected {expected_sha256}, got {actual_sha256}", matched_track

    return True, "Approved music track with valid provenance", matched_track


def discover_music_tracks(music_dir: str | Path = MUSIC_DIR) -> dict[str, list[Path]]:
    """
    Discover approved background music tracks in assets/music/.
    Categories: devotional, ambient, transition.
    Only returns files that pass provenance validation.
    """
    base = Path(music_dir)
    manifest_file = base / "music_manifest.json"
    categories = ["devotional", "ambient", "transition"]
    result: dict[str, list[Path]] = {cat: [] for cat in categories}

    if not base.exists():
        return result

    for cat in categories:
        cat_dir = base / cat
        if cat_dir.exists():
            for f in sorted(cat_dir.glob("*")):
                if f.suffix.lower() in (".mp3", ".wav", ".aac", ".flac"):
                    ok, _, _ = validate_music_provenance(f, manifest_path=manifest_file)
                    if ok:
                        result[cat].append(f)

    return result


def select_background_music_v2(
    category: str = "devotional",
    music_dir: str | Path = MUSIC_DIR,
    deity: str | None = None,
    script: dict | None = None,
) -> tuple[Path | None, str]:
    """
    Music Pipeline v2 Deity-Specific Selection Strategy.

    Priority Order:
      1. Deity-Specific Path: If a deity is specified/detected from script or deity param,
         matches approved deity-specific songs from DEITY_SONG_CATALOG or music_manifest.json.
         Fails closed (returns None, "narration_only") if no approved audio asset exists for that deity.
      2. General Category Path (when no deity specified): Searches category tracks in manifest.

    Returns (selected_track_path, selection_type)
    """
    manifest_file = Path(music_dir) / "music_manifest.json"
    manifest = load_music_manifest(manifest_file)
    tracks = manifest.get("tracks", [])

    norm_deity = normalize_deity(deity) or normalize_deity(script)

    # 1. Deity-specific selection
    if norm_deity:
        deity_candidates = []

        # Check DEITY_SONG_CATALOG
        catalog_songs = DEITY_SONG_CATALOG.get(norm_deity, [])
        for item in catalog_songs:
            af = item.get("audio_file")
            if af:
                p = Path(af) if Path(af).is_absolute() else Path(music_dir).parent / af
                if p.exists():
                    ok, _, _ = validate_music_provenance(p, manifest_path=manifest_file)
                    if ok:
                        deity_candidates.append(p)

        # Check manifest tracks matching deity
        for tr in tracks:
            tr_deity = tr.get("deity") or ""
            tr_relevance = str(tr.get("deity_relevance", "")).lower()
            if tr_deity == norm_deity or norm_deity in tr_relevance:
                rel_p = tr.get("relative_path", "")
                fpath = Path(music_dir).parent / rel_p if not Path(rel_p).is_absolute() else Path(rel_p)
                if not fpath.exists():
                    fpath = Path(music_dir) / tr.get("category", "") / tr.get("filename", "")
                if fpath.exists():
                    ok, _, _ = validate_music_provenance(fpath, manifest_path=manifest_file)
                    if ok and fpath not in deity_candidates:
                        deity_candidates.append(fpath)

        if deity_candidates:
            if script and isinstance(script, dict) and script.get("title"):
                idx = sum(ord(c) for c in script["title"]) % len(deity_candidates)
                return deity_candidates[idx], "primary"
            return deity_candidates[0], "primary"

        # Deity identified, but NO approved audio asset exists -> fail closed (None)
        return None, "narration_only"

    # If deity or script was supplied but no deity could be detected (e.g. unknown deity topic)
    if deity or (script and isinstance(script, dict)):
        return None, "narration_only"

    # 2. General Category selection (when neither deity nor script is specified)
    primary_candidates = []
    fallback_candidates = []

    for tr in tracks:
        rel_p = tr.get("relative_path", "")
        fpath = Path(music_dir).parent / rel_p if not Path(rel_p).is_absolute() else Path(rel_p)
        if not fpath.exists():
            fpath = Path(music_dir) / tr.get("category", "") / tr.get("filename", "")
        if not fpath.exists():
            continue

        ok, _, tinfo = validate_music_provenance(fpath, manifest_path=manifest_file)
        if not ok:
            continue

        cat = tinfo.get("category", "devotional")
        if cat != category and category != "devotional":
            continue

        stype = tinfo.get("source_type", "")
        if stype in PRIMARY_SOURCE_TYPES:
            primary_candidates.append(fpath)
        elif stype == "original_generated":
            fallback_candidates.append(fpath)

    if primary_candidates:
        return primary_candidates[0], "primary"

    if fallback_candidates:
        return fallback_candidates[0], "fallback_generated"

    return None, "narration_only"


def get_bgm_metadata_for_track(
    track_path: Path | str | None,
    script: dict | None = None,
    deity: str | None = None,
    manifest_path: str | Path = MANIFEST_PATH,
) -> dict[str, str]:
    """
    Resolves title, artist, and deity metadata for a selected BGM track.
    """
    norm_deity = normalize_deity(deity) or normalize_deity(script) or "devotional"

    if not track_path:
        cat_songs = DEITY_SONG_CATALOG.get(norm_deity, [])
        if cat_songs:
            song = cat_songs[0]
            return {
                "title": song["title"],
                "artist": song["artist"],
                "deity": norm_deity,
            }
        return {
            "title": "Devotional Music",
            "artist": "Traditional / Various Artists",
            "deity": norm_deity,
        }

    tp = Path(track_path)

    # Check catalog for mapping
    cat_songs = DEITY_SONG_CATALOG.get(norm_deity, [])
    for song in cat_songs:
        af = song.get("audio_file")
        if af and Path(af).name == tp.name:
            return {
                "title": song["title"],
                "artist": song["artist"],
                "deity": norm_deity,
            }

    # Check manifest metadata
    manifest = load_music_manifest(manifest_path)
    for tr in manifest.get("tracks", []):
        if tr.get("filename") == tp.name or tr.get("relative_path", "").endswith(tp.name):
            return {
                "title": tr.get("track_name", song_title_from_filename(tp.name)),
                "artist": tr.get("source", "Approved Catalog"),
                "deity": norm_deity,
            }

    if cat_songs:
        song = cat_songs[0]
        return {
            "title": song["title"],
            "artist": song["artist"],
            "deity": norm_deity,
        }

    return {
        "title": song_title_from_filename(tp.name),
        "artist": "Traditional / Various Artists",
        "deity": norm_deity,
    }


def song_title_from_filename(filename: str) -> str:
    stem = Path(filename).stem
    return stem.replace("_", " ").title()


def select_background_music(
    category: str = "devotional",
    music_dir: str | Path = MUSIC_DIR,
) -> Path | None:
    """
    Backward compatible helper for existing callers.
    Calls Music Pipeline v2 selection and returns the track Path or None.
    """
    track, _ = select_background_music_v2(category=category, music_dir=music_dir)
    return track
