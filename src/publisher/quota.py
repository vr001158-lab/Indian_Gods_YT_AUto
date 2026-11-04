# src/publisher/quota.py
# Quota enforcement and concurrency locking for Divine Dharshanam Daily publishing
#
# Enforces:
#  - Telugu ('te-IN') only publishing.
#  - Maximum 2 Telugu Shorts per calendar day in Asia/Kolkata.
#  - Maximum 2 total videos per calendar day in Asia/Kolkata.
#  - Maximum 1 long video per rolling 72-hour period.
#  - Cross-platform file locking for atomic state persistence.
#  - Dry runs and failed uploads do NOT consume quota.

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import zoneinfo

PRODUCTION_LANGUAGE = "te-IN"
MAX_SHORTS_PER_DAY = 2
MAX_VIDEOS_PER_DAY = 2
LONG_VIDEO_MIN_INTERVAL_HOURS = 72.0

KOLKATA_TZ = zoneinfo.ZoneInfo("Asia/Kolkata")
UTC_TZ = timezone.utc


class QuotaExceededError(ValueError):
    """Raised when an upload attempt exceeds the publishing quota."""


class PublishingLockError(RuntimeError):
    """Raised when the publishing lock cannot be acquired."""


class PublishingFileLock:
    """
    Cross-platform file lock for synchronizing publishing history updates.
    Works on Windows (msvcrt) and Unix / Linux (fcntl).
    """

    def __init__(self, lock_file: str | Path, timeout: float = 15.0, poll_interval: float = 0.1):
        self.lock_file = Path(lock_file)
        self.timeout = timeout
        self.poll_interval = poll_interval
        self._fd: Any = None

    def __enter__(self):
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()

    def acquire(self) -> None:
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        start_time = time.time()

        while True:
            try:
                # Open or create file for read/write
                self._fd = open(self.lock_file, "a+")
                if os.name == "nt":
                    import msvcrt
                    # Lock first byte non-blocking
                    self._fd.seek(0)
                    msvcrt.locking(self._fd.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self._fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return
            except (IOError, OSError):
                if self._fd:
                    try:
                        self._fd.close()
                    except Exception:
                        pass
                    self._fd = None
                if time.time() - start_time >= self.timeout:
                    raise PublishingLockError(
                        f"Could not acquire publishing lock on {self.lock_file} within {self.timeout}s"
                    )
                time.sleep(self.poll_interval)

    def release(self) -> None:
        if self._fd is not None:
            try:
                if os.name == "nt":
                    import msvcrt
                    self._fd.seek(0)
                    msvcrt.locking(self._fd.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self._fd.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
            finally:
                try:
                    self._fd.close()
                except Exception:
                    pass
                self._fd = None


def parse_published_timestamp(raw_ts: Any) -> datetime | None:
    """
    Parses various timestamp formats into a timezone-aware UTC datetime.
    Supports:
      - 'YYYYMMDD_HHMMSS'
      - ISO-8601 strings ('2026-11-03T18:02:35' / '2026-11-03T18:02:35Z' / with offset)
      - numeric timestamps (epoch seconds)
    """
    if not raw_ts:
        return None

    if isinstance(raw_ts, (int, float)):
        return datetime.fromtimestamp(raw_ts, tz=UTC_TZ)

    s = str(raw_ts).strip()
    # Try ISO formats
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC_TZ)
        return dt.astimezone(UTC_TZ)
    except Exception:
        pass

    # Try YYYYMMDD_HHMMSS
    for fmt in ("%Y%m%d_%H%M%S", "%Y%m%d%H%M%S", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(s, fmt)
            # Existing historical records saved YYYYMMDD_HHMMSS in UTC
            dt = dt.replace(tzinfo=UTC_TZ)
            return dt
        except Exception:
            continue

    return None


def get_kolkata_date(dt: datetime | None = None) -> str:
    """Returns YYYY-MM-DD for the given datetime in Asia/Kolkata timezone."""
    if dt is None:
        dt = datetime.now(KOLKATA_TZ)
    else:
        dt = dt.astimezone(KOLKATA_TZ)
    return dt.strftime("%Y-%m-%d")


def load_publishing_history(history_file: str | Path = "data/publishing_history.json") -> list[dict]:
    """
    Loads publishing history records.
    Returns empty list if file does not exist.
    Raises ValueError if file exists but contains invalid/corrupt JSON (fail-closed).
    """
    p = Path(history_file)
    if not p.exists():
        return []
    try:
        content = p.read_text(encoding="utf-8").strip()
        if not content:
            return []
        data = json.loads(content)
        if not isinstance(data, list):
            raise ValueError(f"Publishing history file {p} does not contain a JSON array (got {type(data).__name__})")
        return data
    except json.JSONDecodeError as exc:
        raise ValueError(f"Publishing history file {p} is corrupted: {exc}") from exc


def check_publishing_quota(
    content_type: str,
    language_code: str = PRODUCTION_LANGUAGE,
    history_file: str | Path = "data/publishing_history.json",
    now_dt: datetime | None = None,
) -> tuple[bool, str]:
    """
    Enforces production publishing quotas:
      1. Language must be 'te-IN' (Telugu). All other languages are rejected.
      2. Maximum 2 Telugu Shorts per calendar day in Asia/Kolkata.
      3. Maximum 2 total videos per calendar day in Asia/Kolkata.
      4. Maximum 1 long video per rolling 72-hour window.

    Parameters
    ----------
    content_type: 'short' or 'long'
    language_code: target language ('te-IN' required)
    history_file: path to publishing_history.json
    now_dt: reference datetime (defaults to current time in Asia/Kolkata)

    Returns
    -------
    (allowed: bool, detail_message: str)
    """
    ct = (content_type or "short").lower().strip()
    lang = (language_code or "").strip()

    # Rule 1: Telugu-only publishing
    if lang != PRODUCTION_LANGUAGE:
        return (
            False,
            f"Production publishing is strictly Telugu ('{PRODUCTION_LANGUAGE}') only. "
            f"Attempted language: '{lang}'."
        )

    if ct not in ("short", "long"):
        return False, f"Unknown content_type '{content_type}'. Must be 'short' or 'long'."

    ref_now = now_dt.astimezone(KOLKATA_TZ) if now_dt else datetime.now(KOLKATA_TZ)
    today_kolkata_str = ref_now.strftime("%Y-%m-%d")

    records = load_publishing_history(history_file)

    # Filter successful records
    successful_records = [
        r for r in records
        if r.get("youtube_video_id") or r.get("video_id")
    ]

    # Calculate today's uploads in Asia/Kolkata
    today_shorts = 0
    today_total = 0
    latest_long_dt: datetime | None = None
    latest_long_record: dict | None = None

    for rec in successful_records:
        rec_ct = (rec.get("content_type") or "short").lower().strip()
        pub_ts = rec.get("published_at_kolkata") or rec.get("published_at")
        dt_utc = parse_published_timestamp(pub_ts)

        if dt_utc:
            dt_kolkata = dt_utc.astimezone(KOLKATA_TZ)
            rec_kolkata_date = dt_kolkata.strftime("%Y-%m-%d")

            if rec_kolkata_date == today_kolkata_str:
                today_total += 1
                if rec_ct == "short":
                    today_shorts += 1

            if rec_ct == "long":
                if latest_long_dt is None or dt_utc > latest_long_dt:
                    latest_long_dt = dt_utc
                    latest_long_record = rec

    # Rule 2 & 3: Daily Limits
    if ct == "short":
        if today_shorts >= MAX_SHORTS_PER_DAY:
            return (
                False,
                f"Daily Telugu Shorts quota reached for {today_kolkata_str} (Asia/Kolkata): "
                f"{today_shorts}/{MAX_SHORTS_PER_DAY} shorts already uploaded today."
            )
        if today_total >= MAX_VIDEOS_PER_DAY:
            return (
                False,
                f"Daily total video publishing limit reached for {today_kolkata_str} (Asia/Kolkata): "
                f"{today_total}/{MAX_VIDEOS_PER_DAY} videos already uploaded today."
            )

    elif ct == "long":
        # Rule 4: Rolling 72-hour window for long video
        if latest_long_dt is not None:
            ref_now_utc = ref_now.astimezone(UTC_TZ)
            elapsed_seconds = (ref_now_utc - latest_long_dt).total_seconds()
            required_seconds = LONG_VIDEO_MIN_INTERVAL_HOURS * 3600.0

            if elapsed_seconds < required_seconds:
                elapsed_hours = elapsed_seconds / 3600.0
                remaining_hours = (required_seconds - elapsed_seconds) / 3600.0
                last_published_str = latest_long_dt.astimezone(KOLKATA_TZ).strftime("%Y-%m-%d %H:%M:%S IST")
                yt_id = latest_long_record.get("youtube_video_id") or latest_long_record.get("video_id", "")
                return (
                    False,
                    f"Long-video 72-hour interval restriction active: last long video was published at "
                    f"{last_published_str} ({elapsed_hours:.1f}h ago, Video ID: {yt_id}). "
                    f"Must wait at least {remaining_hours:.1f} more hours before publishing another long video."
                )

        if today_total >= MAX_VIDEOS_PER_DAY:
            return (
                False,
                f"Daily total video publishing limit reached for {today_kolkata_str} (Asia/Kolkata): "
                f"{today_total}/{MAX_VIDEOS_PER_DAY} videos already uploaded today."
            )

    return True, "Quota check passed."


def record_successful_publish(
    video_id: str,
    title: str,
    content_type: str,
    language_code: str = PRODUCTION_LANGUAGE,
    topic: str = "",
    aspect_ratio: str = "",
    resolution: str = "",
    duration_seconds: float | None = None,
    video_file_name: str = "",
    experiment_tag: str = "",
    history_file: str | Path = "data/publishing_history.json",
    now_dt: datetime | None = None,
) -> dict:
    """
    Safely records a successful upload into publishing_history.json under a process lock.
    Re-validates quota under the lock to prevent concurrent race conditions.
    Never called for dry-run or failed uploads.
    """
    h_path = Path(history_file)
    lock_path = h_path.parent / f"{h_path.name}.lock"

    ref_now_utc = now_dt.astimezone(UTC_TZ) if now_dt else datetime.now(UTC_TZ)
    ref_now_kolkata = ref_now_utc.astimezone(KOLKATA_TZ)

    entry = {
        "youtube_video_id":       video_id,
        "topic":                  topic,
        "title":                  title,
        "content_type":           content_type,
        "language_code":          language_code,
        "experiment_tag":         experiment_tag,
        "aspect_ratio":           aspect_ratio,
        "resolution":             resolution,
        "duration_seconds":       duration_seconds,
        "published_at":           ref_now_utc.strftime("%Y%m%d_%H%M%S"),
        "published_at_utc":       ref_now_utc.isoformat(),
        "published_at_kolkata":   ref_now_kolkata.strftime("%Y-%m-%d %H:%M:%S %z"),
        "kolkata_date":           ref_now_kolkata.strftime("%Y-%m-%d"),
        "video_file_name":        video_file_name,
        "success":                True,
    }

    with PublishingFileLock(lock_path):
        # Re-check quota under lock to ensure no race condition
        allowed, reason = check_publishing_quota(
            content_type=content_type,
            language_code=language_code,
            history_file=h_path,
            now_dt=ref_now_kolkata,
        )
        if not allowed:
            raise QuotaExceededError(f"Publishing rejected under lock: {reason}")

        records = load_publishing_history(h_path)
        records.append(entry)

        # Atomic write: write to temp file then replace
        h_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = h_path.parent / f"{h_path.name}.tmp_{os.getpid()}_{int(time.time()*1000)}"
        tmp_path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
        if os.name == "nt" and h_path.exists():
            # On Windows, replace requires target removal or os.replace
            os.replace(tmp_path, h_path)
        else:
            os.replace(tmp_path, h_path)

    return entry
