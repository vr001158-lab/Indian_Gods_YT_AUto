"""
run_pipeline.py — Divine Dharshanam Daily Pipeline Orchestrator CLI (Phase 2I)
Runs the entire creation cycle: Research -> Decision -> Content -> Script -> Voice -> Visuals -> Video -> Thumbnail.

Usage:
  python run_pipeline.py                                # run full pipeline
  python run_pipeline.py --dry-run                      # run pipeline in offline dry-run mode
  python run_pipeline.py --resume <pipeline_id>         # resume a failed pipeline run
  python run_pipeline.py --resume <id> --dry-run        # resume a failed run in dry-run mode
"""

import sys
import os
import io
from pathlib import Path

# Force UTF-8 stdout/stderr on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

sys.path.insert(0, os.getcwd())

from src.pipeline.state import PipelineState
from src.pipeline.orchestrator import PipelineRunner
from src.pipeline.logger import PipelineLogger


def main():
    resume_id = None
    dry_run = False
    content_type = "short"

    # ── CLI parsing ───────────────────────────────────────────────────────────
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--resume" and i + 1 < len(args):
            resume_id = args[i + 1]
            i += 2
        elif args[i] == "--dry-run":
            dry_run = True
            i += 1
        elif args[i] == "--content-type" and i + 1 < len(args):
            content_type = args[i + 1].lower().strip()
            if content_type not in ("short", "long"):
                print(f"❌ Invalid content-type: '{args[i+1]}'. Must be 'short' or 'long'", file=sys.stderr)
                sys.exit(1)
            i += 2
        else:
            print(f"❌ Unknown argument: {args[i]}", file=sys.stderr)
            print("Usage: python run_pipeline.py [--content-type short|long] [--resume PIPELINE_ID] [--dry-run]", file=sys.stderr)
            sys.exit(1)

    # ── Initialize State ──────────────────────────────────────────────────────
    try:
        if resume_id:
            PipelineLogger.info(f"Loading state file for resumption of: {resume_id}...")
            state = PipelineState.load(resume_id)
            PipelineLogger.info(f"Resuming from current stage: {state.current_stage}")
        else:
            state = PipelineState()
            PipelineLogger.info(f"Initialized new pipeline run: {state.pipeline_id} ({content_type.upper()})")
    except FileNotFoundError as e:
        PipelineLogger.error(str(e))
        sys.exit(1)

    # ── Execute Orchestrator ──────────────────────────────────────────────────
    try:
        runner = PipelineRunner(state=state, dry_run=dry_run, content_type=content_type)
        runner.execute_pipeline()
    except Exception as e:
        PipelineLogger.error(f"Pipeline run stopped with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
