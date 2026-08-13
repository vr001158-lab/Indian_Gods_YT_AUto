# src/research/report.py
# Hardened v0.2 — coordinates collection, scoring, dedup, gap analysis, and output.

import sys
import json
import time
from pathlib import Path

from src.research.collector import ResearchCollector
from src.research.scorer   import TopicScorer
from src.research.dedup    import deduplicate_topics

OUTPUT_DIR = Path("data/research")

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


# ── Pipeline ──────────────────────────────────────────────────────────────────

def run_research_pipeline(
    api_key: str = None,
    limit: int = None,
    max_search_calls: int = 10,
    cache_ttl_hours: int = 24,
) -> list:
    """
    Runs the full research pipeline: dedup → collect → score → gap → persist.

    Parameters
    ----------
    api_key           : YouTube Data API v3 key (None = offline/mock mode)
    limit             : cap number of topics scanned (None = all)
    max_search_calls  : quota budget for YouTube search.list this run
    cache_ttl_hours   : cache entry freshness window

    Returns
    -------
    Sorted list of candidate dicts, best score first.
    """
    collector = ResearchCollector(
        api_key=api_key,
        max_search_calls=max_search_calls,
        cache_ttl_hours=cache_ttl_hours,
    )

    # Deduplicate seed topics before scanning
    topics_to_scan = deduplicate_topics(SUGGESTED_TOPICS)
    if limit:
        topics_to_scan = topics_to_scan[:limit]

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
