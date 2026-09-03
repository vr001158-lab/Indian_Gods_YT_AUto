# src/pipeline/state.py
# Phase 2I — Pipeline State Manager

import json
import time
from pathlib import Path

STATE_DIR = Path("data/pipeline")

STAGES = [
    "RESEARCH",
    "DECISION",
    "CONTENT",
    "SCRIPT",
    "VOICE",
    "VISUAL",
    "VIDEO",
    "THUMBNAIL",
    "QA",
    "PUBLISHER",
    "UPLOAD_READY",
]


class PipelineState:
    """Manages tracking, persistence, and loading of pipeline state."""

    def __init__(self, pipeline_id: str = None, format: str = "narrated", experiment_tag: str | None = None):
        fmt_suffix = "OLD" if (format or "").lower() == "old" else "NARRATED"
        self.format = (format or "narrated").lower()
        self.experiment_tag = experiment_tag
        self.pipeline_id = pipeline_id or f"run_{time.strftime('%Y%m%d_%H%M%S')}_{fmt_suffix}"
        self.current_stage = "RESEARCH"
        self.completed_stages = []
        self.failed_stage = None
        self.outputs = {}
        self.timestamp = time.time()

    def update_stage(self, stage: str, status: str = "IN_PROGRESS"):
        """Updates current_stage parameters."""
        if stage not in STAGES:
            raise ValueError(f"Invalid stage name: {stage}")

        if status == "COMPLETED":
            if stage not in self.completed_stages:
                self.completed_stages.append(stage)
            self.failed_stage = None
            # Move to next stage if available
            idx = STAGES.index(stage)
            if idx + 1 < len(STAGES):
                self.current_stage = STAGES[idx + 1]
            else:
                self.current_stage = "UPLOAD_READY"
        elif status == "FAILED":
            self.failed_stage = stage
            self.current_stage = stage
        else:
            self.current_stage = stage
            self.failed_stage = None

        self.timestamp = time.time()

    def set_output(self, key: str, value: str):
        """Saves dynamic outputs from run phases."""
        self.outputs[key] = str(value).replace("\\", "/")

    def get_output(self, key: str) -> str:
        """Retrieves output values."""
        return self.outputs.get(key)

    def save(self, state_dir: Path = STATE_DIR) -> Path:
        """Saves current state tracking JSON on disk."""
        state_dir.mkdir(parents=True, exist_ok=True)
        file_path = state_dir / f"pipeline_{self.pipeline_id}.json"
        
        data = {
            "pipeline_id":      self.pipeline_id,
            "format":           self.format,
            "experiment_tag":   self.experiment_tag,
            "current_stage":     self.current_stage,
            "completed_stages":  self.completed_stages,
            "failed_stage":      self.failed_stage,
            "outputs":           self.outputs,
            "timestamp":         self.timestamp,
        }
        
        file_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return file_path

    @classmethod
    def load(cls, pipeline_id: str, state_dir: Path = STATE_DIR) -> "PipelineState":
        """Loads execution state file from run directory."""
        file_path = state_dir / f"pipeline_{pipeline_id}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"State file not found for pipeline ID: {pipeline_id}")

        data = json.loads(file_path.read_text(encoding="utf-8"))
        
        state = cls(pipeline_id=data["pipeline_id"], format=data.get("format", "narrated"), experiment_tag=data.get("experiment_tag"))
        state.current_stage = data["current_stage"]
        state.completed_stages = data["completed_stages"]
        state.failed_stage = data.get("failed_stage")
        state.outputs = data.get("outputs", {})
        state.timestamp = data.get("timestamp", time.time())
        return state
