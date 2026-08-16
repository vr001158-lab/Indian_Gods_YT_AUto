"""
run_research.py — Devotional Research Engine Runner (v2.2)
Coordinates collection and scoring to report evidence-backed video topic candidates.

Architecture:
  Research uses a YouTube Data API v3 PUBLIC-DATA API key.
  No OAuth token is required for search.list or videos.list on public data.
  Set YOUTUBE_API_KEY in the environment (or GitHub Secrets) to enable live mode.
"""

import sys
import io
import os
from pathlib import Path

# Force UTF-8 stdout/stderr to prevent encoding crashes on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, os.getcwd())
from src.research import report


def main():
    limit      = None
    force_mock = False

    if "--limit" in sys.argv:
        try:
            idx = sys.argv.index("--limit")
            if idx + 1 < len(sys.argv):
                limit = int(sys.argv[idx + 1])
        except ValueError:
            pass
    elif "RESEARCH_LIMIT" in os.environ:
        try:
            limit = int(os.environ["RESEARCH_LIMIT"])
        except ValueError:
            pass

    if "--no-api" in sys.argv:
        force_mock = True

    print("=" * 50)
    print("🌅 Research Engine — Divine Dharshanam Daily")
    print("=" * 50)

    # Resolve API key from environment
    api_key = None
    if force_mock:
        print("ℹ️  Offline mode forced via --no-api. Bypassing YouTube API.")
    else:
        api_key = os.environ.get("YOUTUBE_API_KEY")
        if api_key:
            # Confirm key is loaded without printing its value
            print(f"🔑 YOUTUBE_API_KEY found in environment ({len(api_key)} chars). Live mode.")
        else:
            print(
                "ℹ️  YOUTUBE_API_KEY not found in environment. "
                "Operating in offline/mock mode.",
                file=sys.stderr
            )

    # Execute pipeline
    candidates = report.run_research_pipeline(api_key=api_key, limit=limit)

    # Print report
    report.print_report(candidates)


if __name__ == "__main__":
    main()
