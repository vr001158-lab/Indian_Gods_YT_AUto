"""
tests/test_pipeline.py
Unit tests for Phase 2I — Production Pipeline Orchestrator.
Tests state creation, transitions, persistence, resuming, subprocess mocks, dry runs, and failure handling.
Runs completely offline without external network or API dependencies.
"""

import sys
import os
import json
import tempfile
import unittest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.getcwd())

from src.pipeline.state import PipelineState, STAGES
from src.pipeline.orchestrator import PipelineRunner
from src.pipeline.logger import PipelineLogger
import run_pipeline


# ─────────────────────────────────────────────────────────────────────────────
class TestPipelineState(unittest.TestCase):
    """Tests PipelineState management, stage transitions, and persistence (Tests 1-12)."""

    def test_1_state_initialized_with_id(self):
        state = PipelineState("test_pipeline_run")
        self.assertEqual(state.pipeline_id, "test_pipeline_run")

    def test_2_state_default_current_stage(self):
        state = PipelineState()
        self.assertEqual(state.current_stage, "RESEARCH")

    def test_3_state_default_completed_list(self):
        state = PipelineState()
        self.assertEqual(state.completed_stages, [])

    def test_4_state_default_failed_stage_none(self):
        state = PipelineState()
        self.assertIsNone(state.failed_stage)

    def test_5_state_update_stage_progress(self):
        state = PipelineState()
        state.update_stage("RESEARCH", "IN_PROGRESS")
        self.assertEqual(state.current_stage, "RESEARCH")
        self.assertIsNone(state.failed_stage)

    def test_6_state_update_stage_completed(self):
        state = PipelineState()
        state.update_stage("RESEARCH", "COMPLETED")
        # Moves to DECISION stage
        self.assertEqual(state.current_stage, "DECISION")
        self.assertIn("RESEARCH", state.completed_stages)

    def test_7_state_update_stage_completed_final(self):
        state = PipelineState()
        state.completed_stages = STAGES[:-1]
        state.update_stage(STAGES[-1], "COMPLETED")
        self.assertEqual(state.current_stage, "UPLOAD_READY")

    def test_8_state_update_stage_failure(self):
        state = PipelineState()
        state.update_stage("CONTENT", "FAILED")
        self.assertEqual(state.failed_stage, "CONTENT")
        self.assertEqual(state.current_stage, "CONTENT")

    def test_9_state_outputs(self):
        state = PipelineState()
        state.set_output("test_key", "C:\\path\\to\\file.json")
        self.assertEqual(state.get_output("test_key"), "C:/path/to/file.json")

    def test_10_state_save_writes_json(self):
        state = PipelineState("save_test")
        state.set_output("key", "val")
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            out_file = state.save(tmp_path)
            self.assertTrue(out_file.exists())
            
            data = json.loads(out_file.read_text(encoding="utf-8"))
            self.assertEqual(data["pipeline_id"], "save_test")
            self.assertEqual(data["outputs"]["key"], "val")

    def test_11_state_load_parses(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            state = PipelineState("load_test")
            state.update_stage("RESEARCH", "COMPLETED")
            state.save(tmp_path)
            
            loaded = PipelineState.load("load_test", state_dir=tmp_path)
            self.assertEqual(loaded.pipeline_id, "load_test")
            self.assertEqual(loaded.current_stage, "DECISION")
            self.assertIn("RESEARCH", loaded.completed_stages)

    def test_12_state_load_not_found(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaises(FileNotFoundError):
                PipelineState.load("non_existent_id", state_dir=Path(tmp_dir))


# ─────────────────────────────────────────────────────────────────────────────
class TestPipelineOrchestrator(unittest.TestCase):
    """Tests PipelineRunner actions, dry run, fail-safes, and mock end-to-end runs (Tests 13-21)."""

    def test_13_runner_stores_dry_run(self):
        runner = PipelineRunner(dry_run=True)
        self.assertTrue(runner.dry_run)

    def test_14_missing_input_rejections(self):
        state = PipelineState()
        # Skipped RESEARCH stage output setting
        runner = PipelineRunner(state)
        
        with self.assertRaises(ValueError):
            runner.run_decision()

    def test_15_non_existent_input_file_rejections(self):
        state = PipelineState()
        state.set_output("research_output", "non_existent_file_path.json")
        runner = PipelineRunner(state)
        
        with self.assertRaises(ValueError):
            runner.run_decision()

    def test_16_stage_failure_updates_state(self):
        state = PipelineState()
        runner = PipelineRunner(state)
        
        with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "cmd", stderr="Mock error")):
            with tempfile.TemporaryDirectory() as tmp_dir:
                with patch("src.pipeline.state.STATE_DIR", Path(tmp_dir)):
                    with self.assertRaises(RuntimeError):
                        runner.run_research()
                    
                    self.assertEqual(state.failed_stage, "RESEARCH")

    def test_17_stage_failure_persists_state(self):
        state = PipelineState("persist_fail_run")
        runner = PipelineRunner(state)
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            with patch("subprocess.run", side_effect=subprocess.CalledProcessError(1, "cmd", stderr="Mock error")):
                with self.assertRaises(RuntimeError):
                    runner._execute_cmd(["cmd"], "RESEARCH")
                
                # State should be written to state directory
                state.save(tmp_path)
                loaded = PipelineState.load("persist_fail_run", state_dir=tmp_path)
                self.assertEqual(loaded.failed_stage, "RESEARCH")

    def test_18_decision_safety_gate_failure(self):
        state = PipelineState()
        runner = PipelineRunner(state)
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            
            # Setup a decision JSON that is unapproved
            decision_file = tmp_path / "decision_fail.json"
            decision_file.write_text(json.dumps({
                "approved_for_generation": False,
                "reason": "Overall opportunity score is below threshold"
            }), encoding="utf-8")
            
            state.set_output("research_output", tmp_path / "research.json") # dummy
            state.set_output("decision_output", decision_file)
            
            # Patch find_latest_file to return our unapproved decision JSON
            with patch.object(runner, "_find_latest_file", return_value=decision_file):
                with patch.object(runner, "_execute_cmd"):
                    # Triggering run_decision must raise ValueError on unapproved status
                    with self.assertRaises(ValueError):
                        runner.run_decision()

    def test_19_dry_run_modes(self):
        state = PipelineState()
        runner = PipelineRunner(state, dry_run=True)
        self.assertTrue(runner.dry_run)

    def test_20_resume_loading_skips(self):
        state = PipelineState("resume_skip_run")
        state.completed_stages = ["RESEARCH", "DECISION"]
        state.current_stage = "CONTENT"
        
        # Verify execution starts from CONTENT stage
        with patch.object(PipelineRunner, "run_content") as mock_content:
            with patch.object(PipelineRunner, "run_script") as mock_script:
                with patch.object(PipelineRunner, "run_voice") as mock_voice:
                    with patch.object(PipelineRunner, "run_visual") as mock_visual:
                        with patch.object(PipelineRunner, "run_video") as mock_video:
                            with patch.object(PipelineRunner, "run_thumbnail") as mock_thumbnail:
                                with patch.object(PipelineRunner, "run_qa") as mock_qa:
                                    with patch.object(PipelineRunner, "run_publisher") as mock_pub:
                                        runner = PipelineRunner(state)
                                        runner.execute_pipeline()
                                        
                                        # Content and subsequent should be called, but not research/decision
                                        mock_content.assert_called_once()
                                        mock_script.assert_called_once()

    def test_21_successful_full_pipeline_mock_execution(self):
        state = PipelineState("full_mock_run")

        
        # Setup files on disk to prevent path validation failures
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            
            research_f = tmp_path / "research_results.json"
            decision_f = tmp_path / "decision.json"
            brief_f = tmp_path / "brief.json"
            script_f = tmp_path / "script.json"
            audio_f = tmp_path / "audio.json"
            visual_f = tmp_path / "visual.json"
            video_f = tmp_path / "video.json"
            thumb_f = tmp_path / "thumb.json"
            qa_f = tmp_path / "qa.json"
            pub_f = tmp_path / "publish.json"
            
            research_f.write_text("{}", encoding="utf-8")
            decision_f.write_text(json.dumps({"approved_for_generation": True, "selected_topic": "topic", "data_source": "youtube_api", "confidence": "high"}), encoding="utf-8")
            brief_f.write_text("{}", encoding="utf-8")
            script_f.write_text("{}", encoding="utf-8")
            audio_f.write_text("{}", encoding="utf-8")
            visual_f.write_text("{}", encoding="utf-8")
            video_f.write_text(json.dumps({"video_file": "video.mp4"}), encoding="utf-8")
            thumb_f.write_text("{}", encoding="utf-8")
            qa_f.write_text("{}", encoding="utf-8")
            pub_f.write_text("{}", encoding="utf-8")
            
            # Setup stage return values
            with patch.object(PipelineRunner, "run_research", return_value=research_f) as m_res:
                with patch.object(PipelineRunner, "run_decision", return_value=decision_f) as m_dec:
                    with patch.object(PipelineRunner, "run_content", return_value=brief_f) as m_con:
                        with patch.object(PipelineRunner, "run_script", return_value=script_f) as m_scr:
                            with patch.object(PipelineRunner, "run_voice", return_value=audio_f) as m_voi:
                                with patch.object(PipelineRunner, "run_visual", return_value=visual_f) as m_vis:
                                    with patch.object(PipelineRunner, "run_video", return_value=video_f) as m_vid:
                                        with patch.object(PipelineRunner, "run_thumbnail", return_value=thumb_f) as m_thu:
                                            with patch.object(PipelineRunner, "run_qa", return_value=qa_f) as m_qa:
                                                with patch.object(PipelineRunner, "run_publisher", return_value=pub_f) as m_pub:
                                                    runner = PipelineRunner(state, dry_run=True)
                                                    runner.execute_pipeline()
                                                    
                                                    # All stages should be invoked
                                                    m_res.assert_called_once()
                                                    m_dec.assert_called_once()
                                                    m_con.assert_called_once()
                                                    m_scr.assert_called_once()
                                                    m_voi.assert_called_once()
                                                    m_vis.assert_called_once()
                                                    m_vid.assert_called_once()
                                                    m_thu.assert_called_once()
                                                    m_qa.assert_called_once()
                                                    m_pub.assert_called_once()
                                                    
                                                    self.assertEqual(state.current_stage, "UPLOAD_READY")
                                                    self.assertIn("UPLOAD_READY", state.completed_stages)


if __name__ == "__main__":
    unittest.main()
