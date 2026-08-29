# src/research/collector.py
# Collector module — YouTube Data API v3 public-data + Hindu festival calendar.
# Hardened v0.3: API-key-based research (no OAuth), quota budgeting,
#                TTL-aware cache, real/mock labeling, verified festival dates.
#
# Architecture note:
#   Research reads (search.list, videos.list) use a PUBLIC-DATA API key
#   from the YOUTUBE_API_KEY environment variable. No OAuth token is needed.
#   OAuth (token.json) is used exclusively by youtube_uploader.py for upload.

import json
import os
import sys
import datetime
from pathlib import Path

# ── Configurable quota budget ─────────────────────────────────────────────────
# YouTube Data API v3 unit costs (as of 2024):
#   search.list  = 100 units per call
#   videos.list  = 1 unit per call  (batch of up to 50 IDs)
# Default project quota: 10,000 units/day
# Safe per-run default: 10 search calls = 1,000 units
RESEARCH_MAX_SEARCH_CALLS_PER_RUN: int = 10
SEARCH_CALL_COST: int = 100       # quota units per search.list call
VIDEOS_LIST_CALL_COST: int = 1    # quota units per videos.list batch
DAILY_QUOTA_LIMIT: int = 10_000   # total project daily limit

# ── Cache settings ────────────────────────────────────────────────────────────
CACHE_VERSION: str = "3"          # bump version when cache schema changes
CACHE_TTL_HOURS: int = 24

# ── File paths ────────────────────────────────────────────────────────────────
CACHE_FILE = Path("data/research/api_cache.json")
FESTIVAL_FILE = Path("data/research/festivals.json")

# ── Environment variable name for the API key ─────────────────────────────────
YOUTUBE_API_KEY_ENV: str = "YOUTUBE_API_KEY"

# ── Deity keyword map ─────────────────────────────────────────────────────────
DEITY_KEYWORDS: dict = {
    "ganesha":    ["ganesha", "ganpati", "vinayaka"],
    "shiva":      ["shiva", "mahadev", "bholenath", "kedarnath"],
    "vishnu":     ["vishnu", "narasimha", "jagannath"],
    "krishna":    ["krishna", "janmashtami", "gopal"],
    "hanuman":    ["hanuman", "bajrangbali"],
    "lakshmi":    ["lakshmi", "diwali"],
    "rama":       ["rama", "ramayan", "ayodhya"],
    "traditions": [],
}

# ── Default festival records ───────────────────────────────────────────────────
# Each record uses approximate Gregorian dates (lunisolar calendar drifts yearly).
# verified=False means the exact date has NOT been confirmed against a
# published Panchang/almanac for the current year.
# When verified=False the festival relevance contribution is halved in the scorer.
DEFAULT_FESTIVALS: list = [
    {
        "festival_name": "Maha Shivratri",
        "deity": "shiva",
        "month": 3, "approx_day": 8,
        "calendar_basis": "lunisolar — approx Gregorian estimate",
        "verified": False,
        "source": "built-in default"
    },
    {
        "festival_name": "Rama Navami",
        "deity": "rama",
        "month": 4, "approx_day": 17,
        "calendar_basis": "lunisolar — approx Gregorian estimate",
        "verified": False,
        "source": "built-in default"
    },
    {
        "festival_name": "Hanuman Jayanti",
        "deity": "hanuman",
        "month": 4, "approx_day": 23,
        "calendar_basis": "lunisolar — approx Gregorian estimate",
        "verified": False,
        "source": "built-in default"
    },
    {
        "festival_name": "Krishna Janmashtami",
        "deity": "krishna",
        "month": 9, "approx_day": 4,
        "calendar_basis": "lunisolar — approx Gregorian estimate",
        "verified": False,
        "source": "built-in default"
    },
    {
        "festival_name": "Ganesh Chaturthi",
        "deity": "ganesha",
        "month": 9, "approx_day": 7,
        "calendar_basis": "lunisolar — approx Gregorian estimate",
        "verified": False,
        "source": "built-in default"
    },
    {
        "festival_name": "Diwali / Lakshmi Puja",
        "deity": "lakshmi",
        "month": 11, "approx_day": 1,
        "calendar_basis": "lunisolar — approx Gregorian estimate",
        "verified": False,
        "source": "built-in default"
    },
]


class ResearchCollector:
    """
    Collects YouTube competitor signals using a public-data API key.

    Authentication:
        No OAuth is used. The YOUTUBE_API_KEY environment variable provides
        a simple API key sufficient for search.list and videos.list on public data.

    Quota management:
        A run is allocated at most RESEARCH_MAX_SEARCH_CALLS_PER_RUN search.list
        calls (100 units each). The run falls back to cached/mock data once
        the budget is exhausted.

    Modes (in priority order):
        1. Fresh cache hit              → data_source = "cached_youtube_api"
        2. Quota budget available + key → data_source = "youtube_api"
        3. Budget exhausted             → data_source = "offline"
        4. No API key                   → data_source = "mock"
        5. API error                    → data_source = "offline"
    """

    def __init__(
        self,
        api_key: str = None,
        max_search_calls: int = RESEARCH_MAX_SEARCH_CALLS_PER_RUN,
        cache_ttl_hours: int = CACHE_TTL_HOURS,
    ):
        """
        Parameters
        ----------
        api_key          : YouTube Data API v3 key. If None, reads from
                           YOUTUBE_API_KEY environment variable.
                           If still absent, falls back to mock mode.
        max_search_calls : maximum search.list calls this run
        cache_ttl_hours  : cache entry freshness window
        """
        # Resolve API key from argument → env var → None (offline)
        raw_key = api_key or os.environ.get(YOUTUBE_API_KEY_ENV) or None
        self.api_key: str = raw_key.strip("'\" \t\r\n") if raw_key else None
        self.youtube = None
        self.max_search_calls = max_search_calls
        self.cache_ttl_hours = cache_ttl_hours
        self._search_calls_used = 0
        self._cache_raw: dict = self._load_cache_raw()
        self.festivals: list = self._load_festivals()

        if self.api_key:
            try:
                from googleapiclient.discovery import build
                self.youtube = build("youtube", "v3", developerKey=self.api_key)
                print("🔑 YouTube API key loaded — research operating in live mode.", file=sys.stderr)
            except Exception as e:
                print(f"⚠️  Warning: Failed to build YouTube API client: {e}", file=sys.stderr)
                self.youtube = None
        else:
            print(
                "ℹ️  YOUTUBE_API_KEY not set — research operating in offline/mock mode.",
                file=sys.stderr
            )

    # ── Cache helpers ─────────────────────────────────────────────────────────

    def _load_cache_raw(self) -> dict:
        if CACHE_FILE.exists():
            try:
                data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data.get("_version") == CACHE_VERSION:
                    return data
            except Exception:
                pass
        return {"_version": CACHE_VERSION}

    def _save_cache(self):
        try:
            CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            CACHE_FILE.write_text(
                json.dumps(self._cache_raw, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception as e:
            print(f"⚠️  Warning: Failed to save API cache: {e}", file=sys.stderr)

    def _cache_get(self, key: str):
        """Return cached entry if present and not expired; else None."""
        entry = self._cache_raw.get(key)
        if not isinstance(entry, dict):
            return None
        ts_str = entry.get("timestamp")
        if not ts_str:
            return None
        try:
            cached_at = datetime.datetime.fromisoformat(ts_str)
            age_hours = (datetime.datetime.utcnow() - cached_at).total_seconds() / 3600
            if age_hours <= self.cache_ttl_hours:
                return entry
            entry["stale"] = True
            return entry
        except Exception:
            return None

    def _cache_put(self, key: str, results: list, data_source: str, api_method: str):
        """Store a cache entry with full metadata."""
        self._cache_raw[key] = {
            "query":         key,
            "timestamp":     datetime.datetime.utcnow().isoformat(),
            "cache_version": CACHE_VERSION,
            "source":        data_source,
            "api_method":    api_method,
            "is_mock":       data_source in ("mock", "offline"),
            "stale":         False,
            "result":        results,
        }
        self._save_cache()

    # ── Festival helpers ──────────────────────────────────────────────────────

    def _load_festivals(self) -> list:
        if FESTIVAL_FILE.exists():
            try:
                data = json.loads(FESTIVAL_FILE.read_text(encoding="utf-8"))
                if isinstance(data, list) and data:
                    return data
            except Exception:
                pass
        return DEFAULT_FESTIVALS

    def get_festival_info(self, deity: str) -> dict:
        """
        Returns next upcoming festival for the deity:
          { festival_name, days_remaining, verified, calendar_basis, source }
        Falls back to a safe generic record when no match found.
        """
        today = datetime.date.today()
        upcoming = []

        for f in self.festivals:
            if f.get("deity", "").lower() != deity.lower():
                continue
            try:
                f_date = datetime.date(today.year, f["month"], f["approx_day"])
            except (ValueError, KeyError):
                continue
            if f_date < today:
                try:
                    f_date = datetime.date(today.year + 1, f["month"], f["approx_day"])
                except ValueError:
                    continue
            days = (f_date - today).days
            upcoming.append({
                "festival_name": f.get("festival_name", f.get("name", "Unknown")),
                "days_remaining": days,
                "verified":       f.get("verified", False),
                "calendar_basis": f.get("calendar_basis", "unknown"),
                "source":         f.get("source", "built-in default"),
            })

        if upcoming:
            upcoming.sort(key=lambda x: x["days_remaining"])
            return upcoming[0]

        return {
            "festival_name":  "Generic Devotional",
            "days_remaining": 365,
            "verified":       False,
            "calendar_basis": "n/a",
            "source":         "fallback",
        }

    # ── YouTube data collection ───────────────────────────────────────────────

    @property
    def quota_remaining(self) -> int:
        return self.max_search_calls - self._search_calls_used

    def search_youtube_videos(self, query: str) -> dict:
        """
        Search YouTube for *query* and return video statistics.

        Returns
        -------
        {
          "videos":      list of video dicts,
          "data_source": "youtube_api" | "cached_youtube_api" | "mock" | "offline",
          "is_mock":     bool,
          "stale":       bool,
        }
        Never raises. Always returns a usable result with explicit data_source.
        """
        # 1. Fresh cache hit
        cached = self._cache_get(query)
        if cached and not cached.get("stale", False):
            is_cached_mock = cached.get("is_mock", False)
            # If live API client is available, bypass unexpired mock cache entries
            if not (is_cached_mock and self.youtube is not None):
                src = "cached_youtube_api" if not is_cached_mock else "mock"
                return {
                    "videos":      cached["result"],
                    "data_source": src,
                    "is_mock":     is_cached_mock,
                    "stale":       False,
                }

        # 2. Quota budget exhausted
        if self._search_calls_used >= self.max_search_calls:
            print(
                f"⚠️  Research quota exhausted ({self.max_search_calls} search calls used). "
                f"Returning offline data for: {query!r}",
                file=sys.stderr
            )
            videos = self._generate_mock_results(query)
            self._cache_put(query, videos, "offline", "none")
            return {"videos": videos, "data_source": "offline", "is_mock": True, "stale": False}

        # 3. No API key → offline/mock mode
        if not self.youtube:
            videos = self._generate_mock_results(query)
            self._cache_put(query, videos, "mock", "none")
            return {"videos": videos, "data_source": "mock", "is_mock": True, "stale": False}

        # 4. Live API call using API key (public data — no OAuth required)
        try:
            self._search_calls_used += 1
            search_res = self.youtube.search().list(
                q=query,
                part="snippet",
                type="video",
                maxResults=5,
                safeSearch="strict",
                regionCode="IN",
            ).execute()

            video_ids = [
                item["id"]["videoId"]
                for item in search_res.get("items", [])
                if "videoId" in item.get("id", {})
            ]

            videos = []
            if video_ids:
                # Batch videos.list — costs 1 quota unit for the whole batch
                vid_res = self.youtube.videos().list(
                    id=",".join(video_ids),
                    part="statistics,snippet",
                ).execute()

                for item in vid_res.get("items", []):
                    snippet = item.get("snippet", {})
                    stats   = item.get("statistics", {})
                    try:
                        views = int(stats.get("viewCount", 0))
                        likes = int(stats.get("likeCount", 0))
                    except (ValueError, TypeError):
                        views = 0
                        likes = 0
                    videos.append({
                        "video_id":     item.get("id"),
                        "title":        snippet.get("title", ""),
                        "channel":      snippet.get("channelTitle", ""),
                        "published_at": snippet.get("publishedAt", ""),
                        "views":        views,
                        "likes":        likes,
                        "url":          f"https://www.youtube.com/watch?v={item.get('id')}",
                    })

            self._cache_put(query, videos, "youtube_api", "search.list + videos.list")
            return {"videos": videos, "data_source": "youtube_api", "is_mock": False, "stale": False}

        except Exception as e:
            print(
                f"⚠️  YouTube API error for {query!r}: {e}. Falling back to offline.",
                file=sys.stderr
            )
            videos = self._generate_mock_results(query)
            self._cache_put(query, videos, "offline", "error_fallback")
            return {"videos": videos, "data_source": "offline", "is_mock": True, "stale": False}

    # ── Mock data generation ──────────────────────────────────────────────────

    def _generate_mock_results(self, query: str) -> list:
        """
        Deterministic mock video records seeded from the query string.
        Explicitly labelled as mock — never presented as real YouTube data.
        URLs use mock.example.invalid — never youtube.com.
        """
        import random
        seed = sum(ord(c) for c in query)
        random.seed(seed)
        mock_channels = [
            "Divine Grace", "Spiritual Stories", "Hindu Symbolism",
            "Sacred Temple Tales", "Vedanta Wisdom",
        ]
        results = []
        for i in range(5):
            views    = random.randint(5_000, 750_000)
            likes    = int(views * random.uniform(0.02, 0.08))
            age_days = random.randint(10, 1_000)
            pub_date = (
                datetime.date.today() - datetime.timedelta(days=age_days)
            ).isoformat() + "T00:00:00Z"
            vid_id = f"mock_vid_{seed + i}"
            results.append({
                "video_id":     vid_id,
                "title":        f"[MOCK] Story of {query} — Part {i + 1}",
                "channel":      random.choice(mock_channels),
                "published_at": pub_date,
                "views":        views,
                "likes":        likes,
                "url":          f"https://mock.example.invalid/watch?v={vid_id}",
            })
        return results
