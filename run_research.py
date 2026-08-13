"""
run_research.py — Devotional Research Engine Runner (v2.1)
Coordinates collection and scoring to report evidence-backed video topic candidates.
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

# Ensure imports can find src/
sys.path.insert(0, os.getcwd())
import google_auth_config
from src.research import report

def main():
    limit = None
    force_mock = False

    # CLI parsing
    if "--limit" in sys.argv:
        try:
            idx = sys.argv.index("--limit")
            if idx + 1 < len(sys.argv):
                limit = int(sys.argv[idx + 1])
        except ValueError:
            pass

    if "--no-api" in sys.argv:
        force_mock = True

    print("==================================================")
    print("🌅 Research Engine — Divine Dharshanam Daily")
    print("==================================================")

    # Resolve OAuth credentials (optional; skips API and falls back to mocks if missing)
    creds = None
    if not force_mock:
        token_path = Path("token.json")
        secret_path = Path("client_secret.json")
        if token_path.exists() and secret_path.exists():
            try:
                creds = google_auth_config.get_google_credentials()
                print("🔑 YouTube API Credentials loaded successfully.")
            except Exception as e:
                print(f"⚠️ Warning: Failed to load Google credentials: {e}. Falling back to offline/mock mode.", file=sys.stderr)
        else:
            print("ℹ️ token.json or client_secret.json not found on disk. Operating in offline/mock mode.")
    else:
        print("ℹ️ Offline mode forced via --no-api. Bypassing YouTube API.")

    # Execute pipeline
    candidates = report.run_research_pipeline(creds=creds, limit=limit)

    # Print report
    report.print_report(candidates)

if __name__ == "__main__":
    main()
