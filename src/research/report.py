# src/research/report.py
# Hardened v0.2 — coordinates collection, scoring, dedup, gap analysis, and output.

import sys
import json
import time
from pathlib import Path

from src.research.collector import ResearchCollector
from src.research.scorer   import TopicScorer
from src.research.dedup    import deduplicate_topics, _fingerprint
from src.decision.validator import _load_published_topics

OUTPUT_DIR = Path("data/research")
HISTORY_FILE = Path("data/publishing_history.json")

# ── Topic seed list ───────────────────────────────────────────────────────────
SUGGESTED_TOPICS = [
    {
        "topic":           "Why Lord Ganesha Has One Broken Tusk",
        "category":        "Hindu mythology",
        "deity":           "ganesha",
        "suggested_angle": (
            "The story behind Ganesha's broken tusk teaches deeper lessons on "
            "sacrifice than the popular version most people know."
        ),
    },
    {
        "topic":           "Why Lord Shiva Wears a Snake Around His Neck",
        "category":        "Stories of deities",
        "deity":           "shiva",
        "suggested_angle": (
            "The snake Vasuki around Shiva's neck represents the mastery of ego and "
            "poison — we explore the lesser-known cosmic context that placed him there."
        ),
    },
    {
        "topic":           "The Mystery of Narasimha Avatar",
        "category":        "Hindu mythology",
        "deity":           "vishnu",
        "suggested_angle": (
            "Why Vishnu had to manifest as a half-man, half-lion, and the unique "
            "grammatical loopholes in Hiranyakashipu's death conditions."
        ),
    },
    {
        "topic":           "Why Hanuman Covered Himself in Sindoor",
        "category":        "Traditions",
        "deity":           "hanuman",
        "suggested_angle": (
            "Hanuman's absolute devotion to Rama led him to paint his entire body "
            "orange — we unpack the literal and symbolic dimensions of this act."
        ),
    },
    {
        "topic":           "The Story of Krishna Lifting Govardhan Hill",
        "category":        "Stories of deities",
        "deity":           "krishna",
        "suggested_angle": (
            "More than a display of strength, this story represents the shift of "
            "devotion from nature worship (Indra) to direct spiritual connection."
        ),
    },
    {
        "topic":           "How Goddess Lakshmi Emerged from Samudra Manthan",
        "category":        "Spiritual history",
        "deity":           "lakshmi",
        "suggested_angle": (
            "The churning of the cosmic ocean yields spiritual gems — we detail why "
            "Lakshmi chose Vishnu as her eternal consort over other gods."
        ),
    },
    {
        "topic":           "Why We Perform Aarti and Ring Bells in Temples",
        "category":        "Traditions",
        "deity":           "traditions",
        "suggested_angle": (
            "The acoustic symbolism and historical roots of temple rituals explained "
            "clearly for a modern devotional audience."
        ),
    },
    {
        "topic":           "The Hidden Meaning of Lord Shiva's Trishul",
        "category":        "Symbolism",
        "deity":           "shiva",
        "suggested_angle": (
            "Shiva's trident governs the three gunas (Sattva, Rajas, Tamas) and the "
            "states of waking, dreaming, and deep sleep."
        ),
    },
    {
        "topic":           "Mysteries of Tirupati Balaji Temple Wealth",
        "category":        "Historical/religious places",
        "deity":           "vishnu",
        "suggested_angle": (
            "Why Lord Venkateswara took a massive loan from Kubera, and why devotees "
            "donate their hair to repay the cosmic interest."
        ),
    },
    {
        "topic":           "Why Ganesha's Mouse Is His Vehicle",
        "category":        "Hindu mythology",
        "deity":           "ganesha",
        "suggested_angle": (
            "The tiny mouse as Ganesha's vahana is not comic relief — it represents "
            "mastery over desire that gnaws invisibly at the mind."
        ),
    },
    {
        "topic":           "Why Shiva Drank Cosmic Poison",
        "category":        "Stories of deities",
        "deity":           "shiva",
        "suggested_angle": (
            "Neelkanth is more than a blue throat: Halahala shows why the cosmos "
            "needed a god willing to hold poison without becoming poison."
        ),
    },
    {
        "topic":           "Why Nandi Guards Kailash",
        "category":        "Symbolism",
        "deity":           "shiva",
        "suggested_angle": (
            "Nandi is not merely a bull statue — waiting in stillness before Shiva "
            "is the discipline that turns devotion into dharma."
        ),
    },
    {
        "topic":           "Why Vishnu Rests on Shesha",
        "category":        "Stories of deities",
        "deity":           "vishnu",
        "suggested_angle": (
            "Ananta Shesha is the remaining that never ends — we unpack why "
            "preservation is portrayed as rest, not as endless labour."
        ),
    },
    {
        "topic":           "Why Krishna Plays the Flute",
        "category":        "Stories of deities",
        "deity":           "krishna",
        "suggested_angle": (
            "The hollow flute is the devotee's emptied ego — we explore why "
            "Krishna's music calls without commanding."
        ),
    },
    {
        "topic":           "Why Hanuman Crossed the Ocean",
        "category":        "Hindu mythology",
        "deity":           "hanuman",
        "suggested_angle": (
            "The leap to Lanka is not only strength — it is the moment Hanuman "
            "remembered who he was after forgetting his own power."
        ),
    },
    {
        "topic":           "Why Rama Drew His Bow",
        "category":        "Stories of deities",
        "deity":           "rama",
        "suggested_angle": (
            "Kodanda is dharma under pressure — we look at when Rama chose the "
            "bow and what that choice costs a righteous king."
        ),
    },
    {
        "topic":           "Why Lakshmi Chooses the Lotus",
        "category":        "Symbolism",
        "deity":           "lakshmi",
        "suggested_angle": (
            "Prosperity that stays unstained in muddy water — the lotus seat "
            "explains why abundance and purity are taught together."
        ),
    },
    {
        "topic":           "Why Temple Lamps Stay Lit Overnight",
        "category":        "Traditions",
        "deity":           "traditions",
        "suggested_angle": (
            "Akhanda deepam is not decoration — continuous flame marks a vow "
            "that the sacred presence is never left in darkness."
        ),
    },
    {
        "topic":           "Why Tulsi Is Planted in Courtyards",
        "category":        "Traditions",
        "deity":           "traditions",
        "suggested_angle": (
            "The household tulsi vrindavan is a living shrine — we explain the "
            "devotional and seasonal logic behind planting it at home."
        ),
    },
    {
        "topic":           "Why Rudraksha Beads Are Worn",
        "category":        "Traditions",
        "deity":           "shiva",
        "suggested_angle": (
            "Rudraksha is described as Shiva's tear — we separate folklore from "
            "the practice of wearing mala as a reminder of inner stillness."
        ),
    },
    {
        "topic":           "Why Conch Shells Are Blown at Dawn",
        "category":        "Traditions",
        "deity":           "traditions",
        "suggested_angle": (
            "Shankha nada is treated as an auspicious opening of the day — we "
            "unpack acoustic, ritual, and symbolic reasons for the dawn conch."
        ),
    },
    {
        "topic":           "Why Ganga Flows from Shiva's Hair",
        "category":        "Hindu mythology",
        "deity":           "shiva",
        "suggested_angle": (
            "Catching Ganga in jata is not a special effect — it is the story of "
            "force tamed so a celestial river can nourish the earth."
        ),
    },
    {
        "topic":           "Why Sudarshana Chakra Never Misses",
        "category":        "Symbolism",
        "deity":           "vishnu",
        "suggested_angle": (
            "The discus is time and precise justice — we explore why Vishnu's "
            "weapon is said to return only after dharma is restored."
        ),
    },
    {
        "topic":           "Why Ayodhya Is Called Rama's Birthplace",
        "category":        "Historical/religious places",
        "deity":           "rama",
        "suggested_angle": (
            "Janmabhoomi is more than geography — we look at why Ayodhya is "
            "remembered as the city where maryada took human form."
        ),
    },
    {
        "topic":           "Why Goddess Durga Has Ten Arms",
        "category":        "Hindu mythology",
        "deity":           "durga",
        "suggested_angle": (
            "Each weapon in Durga's ten hands represents a divine potency combined "
            "to conquer Mahishasura — we detail the symbolic power behind each emblem."
        ),
    },
    {
        "topic":           "Why Saraswati Holds the Veena and Sacred Book",
        "category":        "Symbolism",
        "deity":           "saraswati",
        "suggested_angle": (
            "Saraswati represents pure knowledge and cosmic harmony — the veena "
            "tunes the intellect while the sacred manuscript embodies eternal truth."
        ),
    },
    {
        "topic":           "Why Lord Brahma Is Rarely Worshipped in Temples",
        "category":        "Stories of deities",
        "deity":           "brahma",
        "suggested_angle": (
            "The curse of Bhrigu and the pillar of light — we unpack why creation's "
            "architect lacks active temple worship across India."
        ),
    },
    {
        "topic":           "Why Kartikeya Rides a Peacock",
        "category":        "Hindu mythology",
        "deity":           "kartikeya",
        "suggested_angle": (
            "Murugan's peacock vahana represents the conquest of pride and vanity, "
            "turning ego into a loyal vessel for spiritual warfare."
        ),
    },
    {
        "topic":           "Why Lord Jagannath Has Large Round Eyes and Wooden Form",
        "category":        "Historical/religious places",
        "deity":           "vishnu",
        "suggested_angle": (
            "The sacred wooden daru form of Puri Jagannath hides ancient tribal and "
            "Vedic origins — we detail the divine unfulfilled craft of Vishwakarma."
        ),
    },
    {
        "topic":           "Why Parvati Performed Severe Tapas for Shiva",
        "category":        "Stories of deities",
        "deity":           "parvati",
        "suggested_angle": (
            "Aparna's intense penance demonstrates that true union requires equal "
            "spiritual stature — transforming devotion into unshakeable power."
        ),
    },
    {
        "topic":           "Why Surya Dev Rides a Chariot of Seven Horses",
        "category":        "Symbolism",
        "deity":           "surya",
        "suggested_angle": (
            "The seven horses of Surya represent the seven colors of light, the seven "
            "days of the week, and the vital rays that sustain terrestrial life."
        ),
    },
    {
        "topic":           "Why Yamraj Rides a Buffalo and Holds the Noose",
        "category":        "Hindu mythology",
        "deity":           "yama",
        "suggested_angle": (
            "Yama is the lord of cosmic justice (Dharmaraja) — his buffalo represents "
            "unyielding momentum, while the pasha binds only the karma of the soul."
        ),
    },
    {
        "topic":           "Why Lord Dhanvantari Emerged with Amrita in Samudra Manthan",
        "category":        "Spiritual history",
        "deity":           "dhanvantari",
        "suggested_angle": (
            "Dhanvantari bringing the pot of nectar marks the birth of Ayurveda — "
            "we explore the spiritual link between cosmic health and immortal wisdom."
        ),
    },
    {
        "topic":           "Why Kubera Is the Treasurer of the Devas",
        "category":        "Hindu mythology",
        "deity":           "kubera",
        "suggested_angle": (
            "Once a humble seeker, Kubera's austerity earned him the custodianship "
            "of wealth — teaching that material resources are held as a cosmic trust."
        ),
    },
    {
        "topic":           "Why Garuda Is Vishnu's Eternal Vahana",
        "category":        "Symbolism",
        "deity":           "garuda",
        "suggested_angle": (
            "Garuda embodies the swiftness of Vedic mantras — soaring high above "
            "earthly illusions while guarding sacred order against hidden corruption."
        ),
    },
    {
        "topic":           "Why Kalabhairava Guards the Sacred City of Kashi",
        "category":        "Historical/religious places",
        "deity":           "shiva",
        "suggested_angle": (
            "Kotwal of Kashi — Bhairava absolves the lingering karmic debts of "
            "seekers entering Varanasi, ensuring spiritual liberation at life's end."
        ),
    },
    {
        "topic":           "Why Lord Dattatreya Has Three Heads and Four Dogs",
        "category":        "Symbolism",
        "deity":           "dattatreya",
        "suggested_angle": (
            "The synthesis of Brahma, Vishnu, and Shiva — Dattatreya's four dogs "
            "represent the four Vedas following the supreme unattached guru."
        ),
    },
    {
        "topic":           "Why Hanuman Ate the Sun Thinking It Was a Fruit",
        "category":        "Hindu mythology",
        "deity":           "hanuman",
        "suggested_angle": (
            "Bal Hanuman's cosmic leap to catch the sun reveals unlimited innocence "
            "and the divine powers that were subsequently veiled until needed."
        ),
    },
    {
        "topic":           "Why Goddess Kali Stepped on Lord Shiva's Chest",
        "category":        "Stories of deities",
        "deity":           "kali",
        "suggested_angle": (
            "Shiva placing himself under Kali's foot calms the uncontrollable cosmic "
            "fury — symbolizing unmanifest consciousness restraining pure active power."
        ),
    },
]


# ── Content gap analysis ──────────────────────────────────────────────────────

def analyze_content_gap(scores: dict, data_source: str) -> str:
    """
    Returns a cautious, evidence-qualified content-gap label.
    Claims are weakened when based on mock/offline data.
    """
    is_real = data_source in ("youtube_api", "cached_youtube_api")
    demand       = scores["demand_score"]
    competition  = scores["competition_score"]
    freshness    = scores["freshness_score"]
    curiosity    = scores["curiosity_score"]
    dominant     = scores["stats"]["dominant_count"]

    qualifier = "" if is_real else " (based on mock data — requires real validation)"

    if dominant >= 4:
        return f"High Saturation: Many channels dominate this topic with high-view videos. A highly distinctive angle is needed to compete{qualifier}."
    if demand >= 70 and competition >= 80:
        return (
            f"Possible gap — low saturation with moderate-to-high demand signals. "
            f"Potential opportunity based on available signals{qualifier}."
        )
    if demand >= 75 and freshness <= 40:
        return (
            f"Possible evergreen refresh opportunity — older high-view content exists "
            f"but few recent uploads detected. Requires further validation{qualifier}."
        )
    if curiosity >= 90 and demand <= 55:
        return (
            f"Curiosity-hook topic with modest search demand — may suit a short, "
            f"high-hook Shorts format. Insufficient evidence to claim a gap{qualifier}."
        )
    return f"Insufficient evidence to identify a specific content gap{qualifier}."


def select_topics_to_scan(
    seeds: list | None = None,
    limit: int | None = None,
    history_file: str | Path = HISTORY_FILE,
) -> list:
    """
    Filter published topics/titles and near-duplicate fingerprints against publishing_history,
    deduplicate among seeds, then apply limit.
    """
    raw_seeds = seeds if seeds is not None else SUGGESTED_TOPICS
    published_strings = _load_published_topics(history_file)
    published_prints = [_fingerprint(p) for p in published_strings if p]

    fresh_seeds = []
    for item in raw_seeds:
        top_str = (item.get("topic") or "").strip().lower()
        if top_str in published_strings:
            continue
        fp = _fingerprint(top_str)
        if any(len(fp & pub_fp) >= 2 for pub_fp in published_prints):
            continue
        fresh_seeds.append(item)

    unique = deduplicate_topics(fresh_seeds)
    skipped = len(raw_seeds) - len(unique)
    if skipped:
        print(
            f"ℹ️  Skipping {skipped} seed topic(s) already published or near-duplicate in publishing_history.json "
            f"({len(unique)} fresh unpublished remaining).",
            file=sys.stderr,
        )
    if limit is not None:
        unique = unique[:limit]
    print(
        f"ℹ️  Research will scan {len(unique)} unpublished seed topic(s).",
        file=sys.stderr,
    )
    return unique


# ── Pipeline ──────────────────────────────────────────────────────────────────

def run_research_pipeline(
    api_key: str = None,
    limit: int = None,
    max_search_calls: int = 10,
    cache_ttl_hours: int = 24,
    history_file: str | Path = HISTORY_FILE,
) -> list:
    """
    Runs the full research pipeline: dedup → exclude published → collect → score → persist.

    Parameters
    ----------
    api_key           : YouTube Data API v3 key (None = offline/mock mode)
    limit             : cap number of unpublished topics scanned (None = all unpublished)
    max_search_calls  : quota budget for YouTube search.list this run
    cache_ttl_hours   : cache entry freshness window
    history_file      : publishing history used only to skip already-published seeds

    Returns
    -------
    Sorted list of candidate dicts, best score first.
    """
    collector = ResearchCollector(
        api_key=api_key,
        max_search_calls=max_search_calls,
        cache_ttl_hours=cache_ttl_hours,
    )

    topics_to_scan = select_topics_to_scan(
        SUGGESTED_TOPICS,
        limit=limit,
        history_file=history_file,
    )

    results = []
    any_mock = False

    for item in topics_to_scan:
        topic_text  = item["topic"]
        deity       = item["deity"]

        # Collect
        search_result = collector.search_youtube_videos(topic_text)
        videos        = search_result["videos"]
        data_source   = search_result["data_source"]
        is_mock       = search_result["is_mock"]
        if is_mock:
            any_mock = True

        # Festival proximity
        festival_info = collector.get_festival_info(deity)

        # Score
        scores = TopicScorer.calculate_score(
            topic_meta    = item,
            youtube_videos= videos,
            festival_info  = festival_info,
            data_source   = data_source,
        )

        # Content gap
        gap = analyze_content_gap(scores, data_source)

        # Assemble candidate
        candidate = {
            # Identity
            "topic":           topic_text,
            "category":        item["category"],
            "deity":           deity,
            "suggested_angle": item["suggested_angle"],

            # Data provenance
            "data_source":     data_source,
            "is_mock":         is_mock,
            "confidence":      scores["confidence"],

            # Festival
            "closest_festival":  festival_info["festival_name"],
            "days_to_festival":  festival_info["days_remaining"],
            "festival_verified": festival_info["verified"],
            "festival_source":   festival_info["source"],

            # Score
            "score_version":      scores["score_version"],
            "overall_score":      scores["overall_score"],
            "demand_score":       scores["demand_score"],
            "relevance_score":    scores["relevance_score"],
            "competition_score":  scores["competition_score"],
            "evergreen_score":    scores["evergreen_score"],
            "freshness_score":    scores["freshness_score"],
            "curiosity_score":    scores["curiosity_score"],
            "long_form_potential":scores["long_form_potential"],
            "shorts_potential":   scores["shorts_potential"],

            # Evidence
            "content_gap":   gap,
            "related_videos": [
                {
                    "title":        v["title"],
                    "views":        v["views"],
                    "url":          v["url"],
                    "published_at": v["published_at"],
                }
                for v in videos[:3]
            ],
            "stats": scores["stats"],
        }
        results.append(candidate)

    # Sort best-first
    results.sort(key=lambda x: x["overall_score"], reverse=True)

    # Persist
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_file = OUTPUT_DIR / f"research_results_{timestamp}.json"
    try:
        out_file.write_text(
            json.dumps(results, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        print(f"\n📂 Research candidates saved → {out_file}", file=sys.stderr)
    except Exception as e:
        print(f"⚠️  Warning: Failed to save research results: {e}", file=sys.stderr)

    if any_mock:
        print(
            "\n⚠️  WARNING: One or more topic scores are based on OFFLINE / MOCK data.\n"
            "   Results should NOT be used for production scheduling decisions\n"
            "   without re-running with a valid YouTube API connection.",
            file=sys.stderr
        )

    return results


# ── Console report ────────────────────────────────────────────────────────────

def print_report(candidates: list):
    """Outputs the formatted report to stdout."""
    any_mock = any(c.get("is_mock") for c in candidates)

    print("\n" + "=" * 54)
    print("🌅  DIVINE DHARSHANAM DAILY — TOPIC RESEARCH REPORT")
    print(f"    Scoring: Topic Opportunity Score {candidates[0]['score_version'] if candidates else 'v0.1'}")
    if any_mock:
        print("    ⚠️  MODE: OFFLINE / MOCK RESEARCH — not real YouTube data")
    print("=" * 54)

    for idx, c in enumerate(candidates, 1):
        src_label = f"[{c['data_source'].upper()}]"
        conf_label = f"confidence={c['confidence']}"
        fest_note = "" if c["festival_verified"] else " (unverified date)"

        print(f"\n{idx}. {c['topic']}")
        print(f"   Category:    {c['category']}  {src_label}  {conf_label}")
        print(f"   Festival:    {c['closest_festival']} in {c['days_to_festival']} days{fest_note}")
        print(f"\n   Score:       {c['overall_score']}/100")
        print(
            f"   Demand:{c['demand_score']:>4}  Relevance:{c['relevance_score']:>4}  "
            f"Competition:{c['competition_score']:>4}  Evergreen:{c['evergreen_score']:>4}"
        )
        print(f"   Curiosity:{c['curiosity_score']:>4}  Freshness:{c['freshness_score']:>4}  "
              f"Long-form:{c['long_form_potential']:>4}  Shorts:{c['shorts_potential']:>4}")
        print(f"\n   Suggested Angle:")
        print(f"   \"{c['suggested_angle']}\"")
        print(f"\n   Content Gap:")
        print(f"   {c['content_gap']}")
        print(f"\n   Evidence ({c['data_source']}):")
        for v in c["related_videos"]:
            print(f"   • {v['title']} — {v['views']:,} views — {v['url']}")
        print("\n" + "-" * 54)
