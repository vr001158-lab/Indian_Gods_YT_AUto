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
from src.pipeline.render_validator import validate_render_only_output


class PipelineRunner:
    """End-to-end Pipeline Orchestrator executing stages from Research to Upload Prep."""

    def __init__(
        self,
        state: PipelineState = None,
        dry_run: bool = False,
        content_type: str = "short",
        format: str = "narrated",
        experiment_tag: str | None = None,
        language_code: str | None = None,
        render_only: bool = False,
    ):
        self.format = (format or getattr(state, "format", "narrated")).lower()
        self.experiment_tag = experiment_tag or getattr(state, "experiment_tag", None)
        self.language_code = (
            language_code
            or getattr(state, "language_code", None)
            or os.environ.get("LANGUAGE_CODE", "te-IN")
        )
        self.render_only = render_only or getattr(state, "render_only", False) or (os.environ.get("RENDER_ONLY", "").lower() in ("true", "1", "yes"))
        self.state = state or PipelineState(
            format=self.format,
            experiment_tag=self.experiment_tag,
            language_code=self.language_code,
            render_only=self.render_only,
        )
        if hasattr(self.state, "format"):
            self.state.format = self.format
        if hasattr(self.state, "experiment_tag") and self.experiment_tag:
            self.state.experiment_tag = self.experiment_tag
        if hasattr(self.state, "language_code"):
            self.state.language_code = self.language_code
        if hasattr(self.state, "render_only"):
            self.state.render_only = self.render_only
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
        cmd = [
            sys.executable, "run_decision.py",
            "--input", str(research_file),
            "--format", self.format,
            "--language", self.language_code,
        ]
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
        cmd = [
            sys.executable, "run_content_brief.py",
            "--input", str(decision_file),
            "--language", self.language_code,
        ]
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
        cmd = [
            sys.executable, "run_script_generator.py",
            "--input", str(brief_file),
            "--language", self.language_code,
        ]
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

        # ── Pre-Voice QA Verification Gate ────────────────────────────────────
        if self.format != "old":
            from src.script.script_qa_gate import run_pre_voice_script_qa
            script_data = json.loads(Path(script_file).read_text(encoding="utf-8"))
            meta = script_data.get("approval_metadata") or {}
            qa_ok, qa_report, qa_errors = run_pre_voice_script_qa(
                script_data=script_data,
                canonical_topic=meta.get("selected_topic") or script_data.get("title"),
                deity_hint=meta.get("deity", ""),
                language_code=self.language_code,
                content_type=self.content_type,
                fail_fast=False,
            )
            if not qa_ok:
                raise ValueError(
                    f"❌ Orchestrator Pre-Voice Gate Rejection: Script failed QA with {len(qa_errors)} error(s). "
                    f"Voice synthesis blocked.\nErrors: {qa_errors}"
                )
            PipelineLogger.info("Pre-Voice Script QA gate passed.")

        start_time = time.time()
        if self.dry_run:
            provider = "mock"
        else:
            provider = "pocket_tts" if self.language_code == "te-IN" else "edge_neural_tts"
        mode = "test" if self.dry_run else "production"
        cmd = [
            sys.executable, "run_voice_generator.py",
            "--input", str(script_file),
            "--provider", provider,
            "--mode", mode,
            "--format", self.format,
            "--content-type", self.content_type,
            "--language", self.language_code,
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
        cmd = [
            sys.executable, "run_visual_generator.py",
            "--input", str(script_file),
            "--provider", provider,
            "--format", self.format,
            "--content-type", self.content_type,
        ]
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
        if self.dry_run:
            provider = "mock"
        elif self.render_only or os.environ.get("THUMBNAIL_PROVIDER") == "reuse":
            provider = "reuse"
        else:
            provider = "pollinations"
        cmd = [
            sys.executable, "run_thumbnail_generator.py",
            "--input", str(decision_file),
            "--provider", provider,
            "--language", self.language_code,
        ]
        script_file = self.state.get_output("script_output")
        if script_file and Path(script_file).exists():
            cmd.extend(["--script", str(script_file)])
        visual_file = self.state.get_output("visual_map_output")
        if visual_file and Path(visual_file).exists():
            cmd.extend(["--visual-map", str(visual_file)])
        video_file = self.state.get_output("video_output")
        if video_file and Path(video_file).exists():
            cmd.extend(["--video", str(video_file)])
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

        allow_mock = False if self.render_only else self.dry_run
        gate = FinalQAGate(
            base_dir=".",
            allow_mock=allow_mock,
            content_type=self.content_type,
            language_code=self.language_code,
            format=self.format,
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
        if self.render_only or os.environ.get("RENDER_ONLY", "").lower() in ("true", "1", "yes"):
            err = "CRITICAL SAFETY VIOLATION: run_publisher() invoked in render-only mode! Upload and live publishing are strictly forbidden."
            PipelineLogger.error(err)
            raise RuntimeError(err)

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

    def package_and_validate_render_only(self) -> Path:
        """
        Executes the RENDER_PACKAGING stage for render-only mode:
        1. Copies all pipeline outputs into data/render_only/<pipeline_id>/
        2. Validates media files (MP4, audio, thumbnail, script, visuals)
        3. Generates render_summary.json
        4. Fails if validation fails; marks RENDER_PACKAGING and RENDER_COMPLETE if successful.
        """
        stage = "RENDER_PACKAGING"
        PipelineLogger.stage_banner(stage)
        self.state.update_stage(stage, "IN_PROGRESS")
        self.state.save()

        import shutil

        render_dir = Path("data/render_only") / self.state.pipeline_id
        render_dir.mkdir(parents=True, exist_ok=True)
        audio_dest_dir = render_dir / "audio"
        visuals_dest_dir = render_dir / "visuals"
        audio_dest_dir.mkdir(parents=True, exist_ok=True)
        visuals_dest_dir.mkdir(parents=True, exist_ok=True)

        # Source paths from pipeline state
        cb_src = Path(self.state.get_output("content_brief_output") or "")
        sc_src = Path(self.state.get_output("script_output") or "")
        am_src = Path(self.state.get_output("audio_map_output") or "")
        vm_src = Path(self.state.get_output("visual_map_output") or "")
        vid_src = Path(self.state.get_output("video_output") or "")
        thm_src = Path(self.state.get_output("thumbnail_output") or "")
        qa_src = Path(self.state.get_output("qa_output") or "")

        # Packaged destinations
        cb_dst = render_dir / "content_brief.json"
        sc_dst = render_dir / "script.json"
        am_dst = render_dir / "audio_map.json"
        vm_dst = render_dir / "visual_map.json"
        vid_dst = render_dir / "video_short.mp4"
        thm_dst = render_dir / "thumbnail.png"
        qa_dst = render_dir / "final_qa.json"

        if cb_src.exists():
            shutil.copy2(cb_src, cb_dst)
        if sc_src.exists():
            shutil.copy2(sc_src, sc_dst)
        if am_src.exists():
            shutil.copy2(am_src, am_dst)
        if vm_src.exists():
            shutil.copy2(vm_src, vm_dst)
        if vid_src.exists():
            shutil.copy2(vid_src, vid_dst)
            if vid_src.name != vid_dst.name:
                shutil.copy2(vid_src, render_dir / vid_src.name)
        if thm_src.exists():
            shutil.copy2(thm_src, thm_dst)
        if qa_src.exists():
            shutil.copy2(qa_src, qa_dst)

        # Copy audio files
        audio_files_packaged = []
        if am_src.exists():
            try:
                am_data = json.loads(am_src.read_text(encoding="utf-8"))
                full_narration = am_data.get("full_narration_audio_file")
                if full_narration and Path(full_narration).exists():
                    fn_dst = audio_dest_dir / Path(full_narration).name
                    shutil.copy2(full_narration, fn_dst)
                    audio_files_packaged.append(str(fn_dst))
                for s in am_data.get("audio_scenes", []):
                    af = s.get("audio_file")
                    if af and Path(af).exists():
                        af_dst = audio_dest_dir / Path(af).name
                        shutil.copy2(af, af_dst)
                        audio_files_packaged.append(str(af_dst))
            except Exception as e:
                PipelineLogger.warning(f"Error copying audio scene files: {e}")

        # Copy visual files
        visual_files_packaged = []
        if vm_src.exists():
            try:
                vm_data = json.loads(vm_src.read_text(encoding="utf-8"))
                for vs in vm_data.get("visual_scenes", []):
                    for k in ("image_file", "video_file"):
                        vf = vs.get(k)
                        if vf and Path(vf).exists():
                            vf_dst = visuals_dest_dir / Path(vf).name
                            shutil.copy2(vf, vf_dst)
                            visual_files_packaged.append(str(vf_dst))
            except Exception as e:
                PipelineLogger.warning(f"Error copying visual assets: {e}")

        # Validation
        artifacts_for_validation = {
            "video": vid_dst if vid_dst.exists() else vid_src,
            "audio": Path(audio_files_packaged[0]) if audio_files_packaged else (am_src),
            "thumbnail": thm_dst if thm_dst.exists() else thm_src,
            "script": sc_dst if sc_dst.exists() else sc_src,
            "visual_map": vm_dst if vm_dst.exists() else vm_src,
        }

        is_valid, details, errors = validate_render_only_output(
            render_dir=render_dir,
            artifacts=artifacts_for_validation,
            content_type=self.content_type,
            language_code=self.language_code,
        )

        from datetime import datetime, timezone
        summary_data = {
            "pipeline_id": self.state.pipeline_id,
            "execution_mode": "render_only",
            "status": "SUCCESS" if is_valid else "FAILED",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "language_code": self.language_code,
            "content_type": self.content_type,
            "format": self.format,
            "publishing_safety": {
                "publisher_stage_executed": False,
                "youtube_upload_attempted": False,
                "oauth_credentials_required": False,
                "publishing_history_modified": False,
                "quota_consumed": False,
                "youtube_publish_authorized": False,
            },
            "artifacts": {
                "render_directory": str(render_dir).replace("\\", "/"),
                "content_brief": str(cb_dst).replace("\\", "/") if cb_dst.exists() else None,
                "script": str(sc_dst).replace("\\", "/") if sc_dst.exists() else None,
                "audio_map": str(am_dst).replace("\\", "/") if am_dst.exists() else None,
                "visual_map": str(vm_dst).replace("\\", "/") if vm_dst.exists() else None,
                "video": str(vid_dst).replace("\\", "/") if vid_dst.exists() else None,
                "thumbnail": str(thm_dst).replace("\\", "/") if thm_dst.exists() else None,
                "final_qa": str(qa_dst).replace("\\", "/") if qa_dst.exists() else None,
                "audio_files_count": len(audio_files_packaged),
                "visual_files_count": len(visual_files_packaged),
            },
            "validation": {
                "passed": is_valid,
                "details": details,
                "errors": errors,
            },
        }

        summary_file = render_dir / "render_summary.json"
        summary_file.write_text(json.dumps(summary_data, indent=2, ensure_ascii=False), encoding="utf-8")

        if not is_valid:
            err_msg = f"❌ Render-Only Final Validation Failed with {len(errors)} error(s): {errors}"
            PipelineLogger.error(err_msg)
            self.state.update_stage(stage, "FAILED")
            self.state.save()
            raise ValueError(err_msg)

        self.state.set_output("render_only_dir", render_dir)
        self.state.set_output("render_only_summary", summary_file)
        self.state.update_stage(stage, "COMPLETED")
        self.state.save()
        PipelineLogger.success(f"RENDER_PACKAGING completed. Directory: {render_dir}")
        return render_dir

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

        if self.language_code != "te-IN":
            err = f"Production pipeline strictly supports Telugu ('te-IN') only. Attempted: '{self.language_code}'"
            PipelineLogger.error(err)
            raise ValueError(err)

        if self.render_only:
            if self.content_type != "short":
                raise ValueError(f"Render-only mode supports 'short' content-type only. Attempted: '{self.content_type}'")
            if self.format != "narrated":
                raise ValueError(f"Render-only mode supports 'narrated' format only. Attempted: '{self.format}'")
            PipelineLogger.info("🔒 [RENDER ONLY] Real media render mode active. Live publishing & quota consumption disabled.")
        else:
            from src.publisher.quota import check_publishing_quota
            ok_quota, quota_msg = check_publishing_quota(
                content_type=self.content_type,
                language_code=self.language_code,
            )
            if not ok_quota:
                if self.dry_run:
                    PipelineLogger.info(f"🌵 [DRY RUN QUOTA WARNING] {quota_msg}")
                else:
                    PipelineLogger.error(f"❌ Publishing Quota Rejection: {quota_msg}")
                    raise ValueError(f"Publishing quota rejection: {quota_msg}")

        schedule = "evening" if self.format == "old" else "morning"
        PipelineLogger.info(f"🚀 Executing pipeline CONTENT_TYPE={self.content_type.upper()} FORMAT={self.format.upper()} SCHEDULE={schedule}")
        PipelineLogger.info(f"Pipeline ID: {self.state.pipeline_id}")
        if self.dry_run:
            PipelineLogger.info("🌵 Dry Run Mode Enabled.")
        elif self.render_only:
            PipelineLogger.info("🎬 Render-Only Mode Enabled (Real media generation without live publication).")

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
        }
        if self.render_only:
            stages_map["RENDER_PACKAGING"] = self.package_and_validate_render_only
        else:
            stages_map["PUBLISHER"] = self.run_publisher

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
        if self.render_only:
            self.state.update_stage("RENDER_COMPLETE", "COMPLETED")
            self.state.save()
            PipelineLogger.success(f"🏆 Render-Only Pipeline Run {self.state.pipeline_id} fully complete! Output packaged and verified in: {self.state.get_output('render_only_dir')}")
        else:
            self.state.update_stage("UPLOAD_READY", "COMPLETED")
            self.state.save()
            PipelineLogger.success(f"🏆 Pipeline Run {self.state.pipeline_id} fully complete! Package is ready for upload.")
        return self.state.pipeline_id
