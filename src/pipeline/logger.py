# src/pipeline/logger.py
# Phase 2I — Pipeline Logger

import sys
import time


def _safe_print(msg: str, file=None):
    if file is None:
        file = sys.stdout
    try:
        print(msg, file=file)
    except UnicodeEncodeError:
        safe_msg = msg.encode("ascii", errors="replace").decode("ascii")
        print(safe_msg, file=file)


class PipelineLogger:
    """Helper class to log formatted orchestration messages to stdout/stderr."""

    @staticmethod
    def info(msg: str):
        _safe_print(f"ℹ️  [INFO] {msg}")

    @staticmethod
    def success(msg: str):
        _safe_print(f"✅ [SUCCESS] {msg}")

    @staticmethod
    def warning(msg: str):
        _safe_print(f"⚠️  [WARNING] {msg}", file=sys.stderr)

    @staticmethod
    def error(msg: str):
        _safe_print(f"❌ [ERROR] {msg}", file=sys.stderr)

    @staticmethod
    def stage_banner(stage_name: str):
        _safe_print("\n" + "=" * 60)
        _safe_print(f"⚙️  STAGE: {stage_name}")
        _safe_print("=" * 60)
