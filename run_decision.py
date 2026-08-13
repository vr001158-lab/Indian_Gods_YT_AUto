"""
run_decision.py — Divine Dharshanam Daily: Topic Decision Engine CLI (Phase 2B.1)

Usage:
  python run_decision.py                        # auto-picks latest research JSON
  python run_decision.py --input <file>         # explicit research file
  python run_decision.py --min-score 65         # override minimum score threshold
  python run_decision.py --no-save              # skip writing decision JSON to disk

Security rules enforced:
  - Never prints API keys, OAuth tokens, or credentials.
  - Never triggers YouTube uploads.
  - Never makes publishing decisions automatically.
"""

import sys
import os
import io
import json
from pathlib import Path

# Force UTF-8 stdout/stderr on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

sys.path.insert(0, os.getcwd())

from src.decision import report as decision_report

RESEARCH_DIR = Path("data/research")
DEFAULT_MIN_SCORE = 60


def _find_latest_research_file() -> Path:
    """Returns the most recently created research_results_*.json file."""
    files = sorted(RESEARCH_DIR.glob("research_results_*.json"))
    if not files:
        raise FileNotFoundError(
            f"❌ No research_results_*.json files found in {RESEARCH_DIR}.\n"
            "   Run: python run_research.py   to generate research data first."
        )
    return files[-1]  # lexicographic sort on timestamp filenames is chronological


def main():
    input_file  = None
    min_score   = DEFAULT_MIN_SCORE
    save_output = True

    # ── CLI parsing ───────────────────────────────────────────────────────────
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--input" and i + 1 < len(args):
            input_file = Path(args[i + 1])
            i += 2
        elif args[i] == "--min-score" and i + 1 < len(args):
            try:
                min_score = int(args[i + 1])
            except ValueError:
                print(f"❌ --min-score must be an integer, got: {args[i+1]}", file=sys.stderr)
                sys.exit(1)
            i += 2
        elif args[i] == "--no-save":
            save_output = False
            i += 1
        else:
            print(f"❌ Unknown argument: {args[i]}", file=sys.stderr)
            print("Usage: python run_decision.py [--input FILE] [--min-score N] [--no-save]", file=sys.stderr)
            sys.exit(1)

    # ── Locate research file ──────────────────────────────────────────────────
    if input_file is None:
        try:
            input_file = _find_latest_research_file()
        except FileNotFoundError as e:
            print(str(e), file=sys.stderr)
            sys.exit(1)
    elif not input_file.exists():
        print(f"❌ Specified input file not found: {input_file}", file=sys.stderr)
        sys.exit(1)

    print(f"\n📄 Research file: {input_file}")
    print(f"🎯 Minimum score threshold: {min_score}")

    # ── Load research JSON ────────────────────────────────────────────────────
    try:
        candidates = json.loads(input_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"❌ Failed to read research file: {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(candidates, list):
        print("❌ Research file does not contain a JSON array.", file=sys.stderr)
        sys.exit(1)

    # ── Run decision pipeline ─────────────────────────────────────────────────
    decision = decision_report.run_decision_pipeline(
        candidates=candidates,
        min_score=min_score,
        save=save_output,
    )

    # ── Print report ──────────────────────────────────────────────────────────
    decision_report.print_decision(decision)

    # ── Exit code ─────────────────────────────────────────────────────────────
    # Exit 0 if approved, 2 if no topic passed (non-1 to distinguish from error)
    sys.exit(0 if decision["approved_for_generation"] else 2)


if __name__ == "__main__":
    main()
