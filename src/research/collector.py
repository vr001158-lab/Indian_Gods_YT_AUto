# src/research/collector.py
# Collector module — YouTube Data API v3 + Hindu festival calendar.
# Hardened v0.2: quota budgeting, TTL-aware cache, real/mock labeling, verified festival dates.

import json
import sys
import datetime
from pathlib import Path

# ── Configurable quota budget ─────────────────────────────────────────────────
# YouTube Data API v3 unit costs (as of 2024):
#   search.list  = 100 units per call
#   videos.list  = 1 unit per call
# Default project quota: 10,000 units/day
# Safe default: allow at most 10 search calls per research run (= 1,000 units)
RESEARCH_MAX_SEARCH_CALLS_PER_RUN: int = 10
SEARCH_CALL_COST: int = 100          # quota units per search.list call
VIDEOS_LIST_CALL_COST: int = 1       # quota units per videos.list call
DAILY_QUOTA_LIMIT: int = 10_000      # total project daily limit

# ── Cache settings ────────────────────────────────────────────────────────────
CACHE_VERSION: str = "2"
CACHE_TTL_HOURS: int = 24            # cached entries older than this are considered stale

# ── File paths ────────────────────────────────────────────────────────────────
CACHE_FILE = Path("data/research/api_cache.json")
FESTIVAL_FILE = Path("data/research/festivals.json")

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
    Collects YouTube competitor signals and Hindu festival proximity data.

    Quota management:
        A run is allocated at most RESEARCH_MAX_SEARCH_CALLS_PER_RUN search.list
        calls. Each call costs SEARCH_CALL_COST quota units. The run aborts
        gracefully (falls through to cached/mock data) once the budget is exhausted.
    """

    def __init__(
        self,
        creds=None,
        max_search_calls: int = RESEARCH_MAX_SEARCH_CALLS_PER_RUN,
        cache_ttl_hours: int = CACHE_TTL_HOURS,
    ):
        self.creds = creds
        self.youtube = None
        self.max_search_calls = max_search_calls
        self.cache_ttl_hours = cache_ttl_hours
        self._search_calls_used = 0            # track quota this run
        self._cache_raw: dict = self._load_cache_raw()
        self.festivals: list = self._load_festivals()

        if self.creds:
            try:
                from googleapiclient.discovery import build
                self.youtube = build("youtube", "v3", credentials=self.creds)
            except Exception as e:
                print(f"⚠️  Warning: Failed to build YouTube API client: {e}", file=sys.stderr)

    # ── Cache helpers ─────────────────────────────────────────────────────────

    def _load_cache_raw(self) -> dict:
        if CACHE_FILE.exists():
            try:
                data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
                # Accept only matching cache version
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
            # Stale — mark explicitly but still return so caller can decide
            entry["stale"] = True
            return entry
        except Exception:
            return None

    def _cache_put(self, key: str, results: list, data_source: str, api_method: str):
        """Store a cache entry with full metadata."""
        self._cache_raw[key] = {
            "query": key,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "cache_version": CACHE_VERSION,
            "source": data_source,
            "api_method": api_method,
            "is_mock": data_source in ("mock", "offline"),
            "stale": False,
            "result": results,
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
        Returns a dict with:
          festival_name, days_remaining, verified
        If no festival found returns a safe fallback with verified=False.
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
                "verified": f.get("verified", False),
                "calendar_basis": f.get("calendar_basis", "unknown"),
                "source": f.get("source", "built-in default"),
            })

        if upcoming:
            upcoming.sort(key=lambda x: x["days_remaining"])
            return upcoming[0]

        return {
            "festival_name": "Generic Devotional",
            "days_remaining": 365,
            "verified": False,
            "calendar_basis": "n/a",
            "source": "fallback",
        }

    # ── YouTube data collection ───────────────────────────────────────────────

    @property
    def quota_remaining(self) -> int:
        return self.max_search_calls - self._search_calls_used

    def search_youtube_videos(self, query: str) -> dict:
        """
        Returns a dict:
          {
            "videos": [...],
            "data_source": "youtube_api" | "cached_youtube_api" | "mock" | "offline" | "stale_offline",
            "is_mock": bool,
            "stale": bool,
          }
        Never raises; always returns a usable result with explicit data_source.
        """
        # 1. Check cache (fresh or stale)
        cached = self._cache_get(query)
        if cached:
            is_stale = cached.get("stale", False)
            if not is_stale:
                src = "cached_youtube_api" if not cached.get("is_mock") else "mock"
                return {
                    "videos": cached["result"],
                    "data_source": src,
                    "is_mock": cached.get("is_mock", False),
                    "stale": False,
                }
            # Stale — attempt refresh if we have budget
            # (fall through to live fetch below)

        # 2. Check quota budget
        if self._search_calls_used >= self.max_search_calls:
            print(
                f"⚠️  Research quota exhausted ({self.max_search_calls} search calls used). "
                f"Returning offline data for: {query!r}",
                file=sys.stderr
            )
            videos = self._generate_mock_results(query)
            self._cache_put(query, videos, "offline", "none")
            return {"videos": videos, "data_source": "offline", "is_mock": True, "stale": False}

        # 3. No YouTube client — offline/mock mode
        if not self.youtube:
            videos = self._generate_mock_results(query)
            self._cache_put(query, videos, "mock", "none")
            return {"videos": videos, "data_source": "mock", "is_mock": True, "stale": False}

        # 4. Live YouTube API call
        try:
            self._search_calls_used += 1
            search_res = self.youtube.search().list(
                q=query,
                part="snippet",
                type="video",
                maxResults=5,
                safeSearch="strict",
            ).execute()

            video_ids = [
                item["id"]["videoId"]
                for item in search_res.get("items", [])
                if "videoId" in item.get("id", {})
            ]

            videos = []
            if video_ids:
                # Batch videos.list — costs only 1 unit for the batch
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
                f"⚠️  YouTube API error for {query!r}: {e}. Falling back to mock.",
                file=sys.stderr
            )
            videos = self._generate_mock_results(query)
            self._cache_put(query, videos, "offline", "error_fallback")
            return {"videos": videos, "data_source": "offline", "is_mock": True, "stale": False}

    # ── Mock data generation ──────────────────────────────────────────────────

    def _generate_mock_results(self, query: str) -> list:
        """
        Generates deterministic mock video records seeded from the query string.
        These are explicitly labelled as mock — never presented as real YouTube data.
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
            vid_id   = f"mock_vid_{seed + i}"
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
