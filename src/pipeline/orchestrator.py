# src/pipeline/orchestrator.py
# Phase 2I — Pipeline Production Orchestrator

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from src.pipeline.state import PipelineState
from src.pipeline.logger import PipelineLogger


class PipelineRunner:
    """End-to-end Pipeline Orchestrator executing stages from Research to Upload Prep."""

    def __init__(self, state: PipelineState = None, dry_run: bool = False, content_type: str = "short", format: str = "narrated"):
        self.format = (format or getattr(state, "format", "narrated")).lower()
        self.state = state or PipelineState(format=self.format)
        if hasattr(self.state, "format"):
            self.state.format = self.format
        self.dry_run = dry_run
        self.content_type = content_type

    def _execute_cmd(self, cmd: list, stage_name: str) -> str:
        """Executes a CLI command as a subprocess, returning stdout."""
        PipelineLogger.info(f"Running command: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            err_output = []
            if e.stdout and e.stdout.strip():
                err_output.append(f"STDOUT:\n{e.stdout.strip()}")
            if e.stderr and e.stderr.strip():
                err_output.append(f"STDERR:\n{e.stderr.strip()}")
            combined = "\n".join(err_output) if err_output else str(e)
            PipelineLogger.error(f"Command failed in stage {stage_name}:\n{combined}")
            self.state.update_stage(stage_name, "FAILED")
            self.state.save()
            raise RuntimeError(f"Stage {stage_name} execution failed:\n{combined}")
        except Exception as e:
            PipelineLogger.error(f"Unexpected error in stage {stage_name}: {e}")
            self.state.update_stage(stage_name, "FAILED")
            self.state.save()
            raise

    def _find_latest_file(self, directory: Path, pattern: str, min_mtime: float | None = None) -> Path:
        """Helper to find the latest file in a directory matching a pattern by mtime."""
        files = sorted(directory.glob(pattern), key=lambda p: p.stat().st_mtime)
        if min_mtime is not None:
            files = [p for p in files if p.stat().st_mtime >= min_mtime]
        if not files:
            raise FileNotFoundError(f"No files matching {pattern} created since stage start found in {directory}")
        return files[-1]

    def run_research(self) -> Path:
        """Executes the RESEARCH stage."""
        stage = "RESEARCH"
        PipelineLogger.stage_banner(stage)
        self.state.update_stage(stage, "IN_PROGRESS")
        self.state.save()

        start_time = time.time()
        research_limit = os.environ.get("RESEARCH_LIMIT", "10")
        cmd = [sys.executable, "run_research.py", "--limit", str(research_limit)]
        self._execute_cmd(cmd, stage)

        # Auto-discover output path
        out_file = self._find_latest_file(Path("data/research"), "research_results_*.json", min_mtime=start_time - 2)
        self.state.set_output("research_output", out_file)
        self.state.update_stage(stage, "COMPLETED")
        self.state.save()
        PipelineLogger.success(f"RESEARCH completed. Output: {out_file}")
        return out_file

    def run_decision(self) -> Path:
        """Executes the DECISION stage."""
        stage = "DECISION"
        PipelineLogger.stage_banner(stage)
        self.state.update_stage(stage, "IN_PROGRESS")
        self.state.save()

        research_file = self.state.get_output("research_output")
        if not research_file or not Path(research_file).exists():
            raise ValueError(f"Missing or invalid research input file: {research_file}")

        start_time = time.time()
        cmd = [sys.executable, "run_decision.py", "--input", str(research_file), "--format", self.format]
        self._execute_cmd(cmd, stage)
        out_file = self._find_latest_file(Path("data/decision"), "decision_*.json", min_mtime=start_time - 2)
        decision_data = json.loads(out_file.read_text(encoding="utf-8"))
        if not decision_data.get("approved_for_generation"):
            self.state.update_stage(stage, "FAILED")
            self.state.save()
            raise ValueError(
                "Stage DECISION execution failed: no research candidate passed "
                "production safety gates"
            )

        self.state.set_output("decision_output", out_file)
        self.state.update_stage(stage, "COMPLETED")
        self.state.save()
        PipelineLogger.success(f"DECISION completed. Output: {out_file}")
        return out_file

    def run_content(self) -> Path:
        """Executes the CONTENT (Brief) stage."""
        stage = "CONTENT"
        PipelineLogger.stage_banner(stage)
        self.state.update_stage(stage, "IN_PROGRESS")
        self.state.save()

        decision_file = self.state.get_output("decision_output")
        if not decision_file or not Path(decision_file).exists():
            raise ValueError(f"Missing or invalid decision input file: {decision_file}")

        start_time = time.time()
        cmd = [sys.executable, "run_content_brief.py", "--input", str(decision_file)]
        self._execute_cmd(cmd, stage)

        out_file = self._find_latest_file(Path("data/content_briefs"), "content_brief_*.json", min_mtime=start_time - 2)
        self.state.set_output("content_brief_output", out_file)
        self.state.update_stage(stage, "COMPLETED")
        self.state.save()
        PipelineLogger.success(f"CONTENT completed. Output: {out_file}")
        return out_file

    def run_script(self) -> Path:
        """Executes the SCRIPT stage."""
        stage = "SCRIPT"
        PipelineLogger.stage_banner(stage)
        self.state.update_stage(stage, "IN_PROGRESS")
        self.state.save()

        brief_file = self.state.get_output("content_brief_output")
        if not brief_file or not Path(brief_file).exists():
            raise ValueError(f"Missing or invalid brief input file: {brief_file}")

        start_time = time.time()
        cmd = [sys.executable, "run_script_generator.py", "--input", str(brief_file)]
        self._execute_cmd(cmd, stage)

        out_file = self._find_latest_file(Path("data/scripts"), "script_*.json", min_mtime=start_time - 2)
        self.state.set_output("script_output", out_file)
        self.state.update_stage(stage, "COMPLETED")
        self.state.save()
        PipelineLogger.success(f"SCRIPT completed. Output: {out_file}")
        return out_file

    def run_voice(self) -> Path:
        """Executes the VOICE stage."""
        stage = "VOICE"
        PipelineLogger.stage_banner(stage)
        self.state.update_stage(stage, "IN_PROGRESS")
        self.state.save()

        script_file = self.state.get_output("script_output")
        if not script_file or not Path(script_file).exists():
            raise ValueError(f"Missing or invalid script input file: {script_file}")

        start_time = time.time()
        provider = "mock" if self.dry_run else "edge_neural_tts"
        mode = "test" if self.dry_run else "production"
        cmd = [
            sys.executable, "run_voice_generator.py",
            "--input", str(script_file),
            "--provider", provider,
            "--mode", mode,
            "--format", self.format,
        ]
        self._execute_cmd(cmd, stage)

        out_file = self._find_latest_file(Path("data/audio"), "audio_map_*.json", min_mtime=start_time - 2)
        self.state.set_output("audio_map_output", out_file)
        self.state.update_stage(stage, "COMPLETED")
        self.state.save()
        PipelineLogger.success(f"VOICE completed. Output: {out_file}")
        return out_file

    def run_visual(self) -> Path:
        """Executes the VISUAL stage."""
        stage = "VISUAL"
        PipelineLogger.stage_banner(stage)
        self.state.update_stage(stage, "IN_PROGRESS")
        self.state.save()

        script_file = self.state.get_output("script_output")
        if not script_file or not Path(script_file).exists():
            raise ValueError(f"Missing or invalid script input file: {script_file}")

        start_time = time.time()
        provider = "mock" if self.dry_run else "flux"
        cmd = [sys.executable, "run_visual_generator.py", "--input", str(script_file), "--provider", provider]
        self._execute_cmd(cmd, stage)

        out_file = self._find_latest_file(Path("data/visuals"), "visual_map_*.json", min_mtime=start_time - 2)
        self.state.set_output("visual_map_output", out_file)
        self.state.update_stage(stage, "COMPLETED")
        self.state.save()
        PipelineLogger.success(f"VISUAL completed. Output: {out_file}")
        return out_file

    def run_video(self) -> Path:
        """Executes the VIDEO stage."""
        stage = "VIDEO"
        PipelineLogger.stage_banner(stage)
        self.state.update_stage(stage, "IN_PROGRESS")
        self.state.save()

        audio_file = self.state.get_output("audio_map_output")
        visual_file = self.state.get_output("visual_map_output")
        if not audio_file or not Path(audio_file).exists():
            raise ValueError(f"Missing or invalid audio map input file: {audio_file}")
        if not visual_file or not Path(visual_file).exists():
            raise ValueError(f"Missing or invalid visual map input file: {visual_file}")

        start_time = time.time()
        # Always run mock composition in dry_run to prevent heavy render
        composer = "mock" if self.dry_run else "ffmpeg"
        cmd = [
            sys.executable, "run_video_generator.py",
            "--audio-map", str(audio_file),
            "--visual-map", str(visual_file),
            "--composer", composer,
            "--content-type", self.content_type,
        ]
        self._execute_cmd(cmd, stage)

        out_file = self._find_latest_file(Path("data/videos"), "video_map_*.json", min_mtime=start_time - 2)
        
        # Pull video file path from video map file
        video_map_data = json.loads(out_file.read_text(encoding="utf-8"))
        video_file = video_map_data["video_file"]

        self.state.set_output("video_map_output", out_file)
        self.state.set_output("video_output", video_file)
        self.state.update_stage(stage, "COMPLETED")
        self.state.save()
        PipelineLogger.success(f"VIDEO completed. Video file: {video_file}")
        return out_file

    def test_run_thumbnail(self) -> Path:
        """Executes the THUMBNAIL stage (using the mock keyword helper to stay safe)."""
        return self.run_thumbnail()

    def run_thumbnail(self) -> Path:
        """Executes the THUMBNAIL stage."""
        stage = "THUMBNAIL"
        PipelineLogger.stage_banner(stage)
        self.state.update_stage(stage, "IN_PROGRESS")
        self.state.save()

        decision_file = self.state.get_output("decision_output")
        if not decision_file or not Path(decision_file).exists():
            raise ValueError(f"Missing or invalid decision input file: {decision_file}")

        start_time = time.time()
        provider = "mock" if self.dry_run else "pil"
        cmd = [sys.executable, "run_thumbnail_generator.py", "--input", str(decision_file), "--provider", provider]
        self._execute_cmd(cmd, stage)

        out_file = self._find_latest_file(Path("data/thumbnails"), "thumbnail_metadata_*.json", min_mtime=start_time - 2)
        thumbnail_png = self._find_latest_file(Path("data/thumbnails"), "thumbnail_*.png", min_mtime=start_time - 2)

        self.state.set_output("thumbnail_metadata_output", out_file)
        self.state.set_output("thumbnail_output", thumbnail_png)
        self.state.update_stage(stage, "COMPLETED")
        self.state.save()
        PipelineLogger.success(f"THUMBNAIL completed. Thumbnail file: {thumbnail_png}")
        return out_file

    def run_qa(self) -> Path:
        """Executes the FINAL QA stage."""
        stage = "QA"
        PipelineLogger.stage_banner(stage)
        self.state.update_stage(stage, "IN_PROGRESS")
        self.state.save()

        decision_file = self.state.get_output("decision_output")
        brief_file = self.state.get_output("content_brief_output")
        script_file = self.state.get_output("script_output")
        audio_file = self.state.get_output("audio_map_output")
        visual_file = self.state.get_output("visual_map_output")
        video_map_file = self.state.get_output("video_map_output")
        thumb_meta_file = self.state.get_output("thumbnail_metadata_output")

        from datetime import datetime, timezone
        from src.qa.gate import FinalQAGate

        gate = FinalQAGate(
            base_dir=".",
            allow_mock=self.dry_run,
            content_type=self.content_type,
            decision_file=str(decision_file),
            content_brief_file=str(brief_file),
            script_file=str(script_file),
            audio_map_file=str(audio_file),
            visual_map_file=str(visual_file),
            video_map_file=str(video_map_file),
            thumbnail_meta_file=str(thumb_meta_file),
        )
        qa_result = gate.run()
        out_dir = Path("data/qa")
        out_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        qa_path = out_dir / f"final_qa_{ts}.json"
        qa_path.write_text(json.dumps(qa_result.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

        if not qa_result.approved_for_publishing:
            err_msg = f"❌ Final QA Gate Rejected: {qa_result.errors}"
            PipelineLogger.error(err_msg)
            self.state.update_stage(stage, "FAILED")
            self.state.save()
            raise ValueError(err_msg)

        self.state.set_output("qa_output", qa_path)
        self.state.update_stage(stage, "COMPLETED")
        self.state.save()
        PipelineLogger.success(f"QA completed. QA file: {qa_path}")
        return qa_path

    def run_publisher(self) -> Path:
        """Executes the PUBLISHER stage (or dry-run)."""
        stage = "PUBLISHER"
        PipelineLogger.stage_banner(stage)
        self.state.update_stage(stage, "IN_PROGRESS")
        self.state.save()

        qa_file = self.state.get_output("qa_output")
        if not qa_file or not Path(qa_file).exists():
            raise ValueError(f"Missing QA input file: {qa_file}")

        cmd = [sys.executable, "run_publisher.py", "--qa", str(qa_file)]
        if self.dry_run:
            cmd.append("--dry-run")

        self._execute_cmd(cmd, stage)

        manifest_file = self._find_latest_file(Path("data/publishing"), "publish_*.json") if not self.dry_run else qa_file
        self.state.set_output("publishing_output", manifest_file)
        self.state.update_stage(stage, "COMPLETED")
        self.state.save()
        PipelineLogger.success(f"PUBLISHER completed. Output: {manifest_file}")
        return manifest_file

    def execute_pipeline(self) -> str:
        """
        Orchestrates pipeline execution starting from the current_stage.
        Allows resuming from previous execution states.
        """
        if self.format == "old":
            enabled = os.environ.get("OLD_FORMAT_ENABLED", "true").lower()
            if enabled == "false":
                PipelineLogger.info("⚠️ OLD_FORMAT_ENABLED is set to 'false'. Exiting evening old-format pipeline safely without upload.")
                return self.state.pipeline_id

        schedule = "evening" if self.format == "old" else "morning"
        PipelineLogger.info(f"🚀 Executing pipeline CONTENT_TYPE={self.content_type.upper()} FORMAT={self.format.upper()} SCHEDULE={schedule}")
        PipelineLogger.info(f"Pipeline ID: {self.state.pipeline_id}")
        if self.dry_run:
            PipelineLogger.info("🌵 Dry Run Mode Enabled.")

        stages_map = {
            "RESEARCH":     self.run_research,
            "DECISION":     self.run_decision,
            "CONTENT":      self.run_content,
            "SCRIPT":       self.run_script,
            "VOICE":        self.run_voice,
            "VISUAL":       self.run_visual,
            "VIDEO":        self.run_video,
            "THUMBNAIL":    self.run_thumbnail,
            "QA":           self.run_qa,
            "PUBLISHER":    self.run_publisher,
        }

        # Identify which stages need execution based on current_stage index
        all_stages = list(stages_map.keys())
        start_idx = all_stages.index(self.state.current_stage) if self.state.current_stage in all_stages else 0

        for stage_name in all_stages[start_idx:]:
            try:
                # Call stage runner method
                stages_map[stage_name]()
            except Exception as e:
                PipelineLogger.error(f"Pipeline execution halted at stage {stage_name}: {e}")
                raise

        # Complete final state update
        self.state.update_stage("UPLOAD_READY", "COMPLETED")
        self.state.save()
        PipelineLogger.success(f"🏆 Pipeline Run {self.state.pipeline_id} fully complete! Package is ready for upload.")
        return self.state.pipeline_id
