# src/research/dedup.py
# Deterministic topic deduplication using normalised keyword fingerprinting.

import re

# Core deity/concept keywords used to build a topic fingerprint.
# Topics that share the same normalised fingerprint are treated as duplicates.
_STOP_WORDS = {
    "the", "a", "an", "of", "in", "on", "at", "and", "or", "is", "was",
    "are", "were", "why", "how", "what", "who", "when", "lord", "goddess",
    "god", "story", "stories", "tale", "legend", "reason", "secret",
    "hidden", "untold", "meaning", "mystery", "mysteries",
}


def _fingerprint(topic: str) -> frozenset:
    """
    Lowercases, strips punctuation, removes stop words, and returns a frozenset
    of the remaining content words. Two topics with the same fingerprint are
    considered duplicates regardless of phrasing.
    """
    words = re.sub(r"[^a-z0-9\s]", "", topic.lower()).split()
    return frozenset(w for w in words if w not in _STOP_WORDS)


def deduplicate_topics(topics: list) -> list:
    """
    Removes near-duplicate topic entries from *topics* (a list of topic dicts).
    Preserves the first occurrence; subsequent entries with an overlapping
    fingerprint are dropped.

    Two topics are considered duplicates when their fingerprints share
    at least 2 content words (configurable via MIN_OVERLAP).

    Returns a new list; the original is not modified.
    """
    MIN_OVERLAP: int = 2
    seen_prints: list = []   # list of frozensets already emitted
    unique: list = []

    for item in topics:
        fp = _fingerprint(item["topic"])
        is_dup = any(
            len(fp & existing) >= MIN_OVERLAP
            for existing in seen_prints
        )
        if not is_dup:
            seen_prints.append(fp)
            unique.append(item)

    return unique
