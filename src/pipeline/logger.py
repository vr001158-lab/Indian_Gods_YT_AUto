# src/pipeline/logger.py
# Phase 2I — Pipeline Logger

import sys
import time


class PipelineLogger:
    """Helper class to log formatted orchestration messages to stdout/stderr."""

    @staticmethod
    def info(msg: str):
        print(f"ℹ️  [INFO] {msg}")

    @staticmethod
    def success(msg: str):
        print(f"✅ [SUCCESS] {msg}")

    @staticmethod
    def warning(msg: str):
        print(f"⚠️  [WARNING] {msg}", file=sys.stderr)

    @staticmethod
    def error(msg: str):
        print(f"❌ [ERROR] {msg}", file=sys.stderr)

    @staticmethod
    def stage_banner(stage_name: str):
        print("\n" + "=" * 60)
        print(f"⚙️  STAGE: {stage_name}")
        print("=" * 60)
