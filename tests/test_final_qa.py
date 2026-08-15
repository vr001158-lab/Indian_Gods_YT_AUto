# tests/test_final_qa.py
# Phase 2J — Final Pipeline QA Gate Tests
#
# 27 tests covering all required validation scenarios.
# Uses only in-memory / tempdir artifacts — no real media encoding required.

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# ── Ensure src/ is importable ─────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from qa.artifacts import PipelineArtifacts
from qa.checks import (
    check_audio_map,
    check_decision_approval,
    check_provenance_consistency,
    check_scene_sync,
    check_thumbnail_meta,
    check_topic_consistency,
    check_video_map,
    check_visual_map,
)
from qa.gate import FinalQAGate


# ─────────────────────────────────────────────────────────────────────────────
# Shared fixtures
# ─────────────────────────────────────────────────────────────────────────────

TOPIC = "Why Lord Shiva Wears a Snake Around His Neck"

APPROVAL_META = {
    "approved_for_generation": True,
    "selected_topic": TOPIC,
    "score": 66,
    "confidence": "high",
    "data_source": "youtube_api",
    "category": "Stories of deities",
}

VALID_DECISION = {
    "approved_for_generation": True,
    "selected_topic": TOPIC,
    "score": 66,
    "confidence": "high",
    "data_source": "youtube_api",
    "category": "Stories of deities",
    "deity": "shiva",
}

SCENE_SCRIPTS = [
    {"scene": i, "duration_seconds": 30, "visual_reference": f"v{i}", "voice_text": f"t{i}", "emotion": "reverent"}
    for i in range(1, 6)
]

VALID_SCRIPT = {
    "title": f"Secrets of Shiva's Snake: The Mastery Over Ego and Poison — {TOPIC}",
    "duration_seconds": 150,
    "narration": "Full narration text here.",
    "scene_scripts": SCENE_SCRIPTS,
    "approval_metadata": APPROVAL_META,
}

VALID_CONTENT_BRIEF = {
    "primary_title": f"Shiva Snake Why — {TOPIC}",
    "hook": "Hook text.",
    "approval_metadata": APPROVAL_META,
}


def _make_audio_scenes(tmp: Path, *, scenes=5, bad_scene_order=False, zero_byte=False):
    """Build audio_scenes list with real dummy MP3 files in tmp dir."""
    items = []
    for i in range(1, scenes + 1):
        scene_num = i if not bad_scene_order else (scenes + 1 - i)
        f = tmp / f"scene_{i}.mp3"
        if zero_byte:
            f.write_bytes(b"")
        else:
            f.write_bytes(b"\xff\xfb" + b"\x00" * 77)  # minimal MP3 header
        items.append({
            "scene": scene_num,
            "voice_text": f"narration {i}",
            "audio_file": str(f),
            "duration_seconds": 30,
        })
    return items


def _make_visual_scenes(tmp: Path, *, scenes=5, zero_byte=False, corrupt=False):
    """Build visual_scenes list with real dummy PNG files in tmp dir."""
    from PIL import Image
    items = []
    for i in range(1, scenes + 1):
        f = tmp / f"scene_{i}.png"
        if zero_byte:
            f.write_bytes(b"")
        elif corrupt:
            f.write_bytes(b"NOTAPNG")
        else:
            img = Image.new("RGB", (720, 1280), color=(i * 40, 50, 60))
            img.save(f, "PNG")
        items.append({
            "scene": i,
            "visual_prompt": f"prompt {i}",
            "image_file": str(f),
            "style": "cinematic",
            "duration_seconds": 30,
        })
    return items


def _make_thumbnail(tmp: Path, *, zero_byte=False, wrong_size=False, corrupt=False) -> Path:
    from PIL import Image
    f = tmp / "thumbnail.png"
    if zero_byte:
        f.write_bytes(b"")
    elif corrupt:
        f.write_bytes(b"NOTAPNG")
    elif wrong_size:
        img = Image.new("RGB", (640, 480), color=(100, 100, 100))
        img.save(f, "PNG")
    else:
        img = Image.new("RGB", (1280, 720), color=(80, 20, 120))
        img.save(f, "PNG")
    return f


def _make_video(tmp: Path, *, zero_byte=False) -> Path:
    f = tmp / "video.mp4"
    if zero_byte:
        f.write_bytes(b"")
    else:
        f.write_bytes(b"MOCK_MP4_VIDEO: resolution=720x1280, format=yuv420p, codec=h264\n")
    return f


def _build_artifacts(
    tmp: Path,
    *,
    decision: dict | None = None,
    content_brief: dict | None = None,
    script: dict | None = None,
    audio_scenes: list | None = None,
    audio_duration: int = 150,
    visual_scenes: list | None = None,
    visual_provider: str = "mock",
    video_scenes: int = 5,
    video_file: Path | None = None,
    thumbnail_file: Path | None = None,
    thumbnail_meta: dict | None = None,
    approval_meta_override: dict | None = None,
) -> PipelineArtifacts:
    """Build a complete in-memory PipelineArtifacts bundle for testing."""
    audio_tmp   = tmp / "audio"
    visual_tmp  = tmp / "visual"
    audio_tmp.mkdir(exist_ok=True)
    visual_tmp.mkdir(exist_ok=True)

    dec   = decision      if decision      is not None else VALID_DECISION.copy()
    cb    = content_brief if content_brief is not None else VALID_CONTENT_BRIEF.copy()
    sc    = script        if script        is not None else VALID_SCRIPT.copy()

    a_scenes = audio_scenes  if audio_scenes  is not None else _make_audio_scenes(audio_tmp)
    v_scenes = visual_scenes if visual_scenes is not None else _make_visual_scenes(visual_tmp)
    vf       = video_file    if video_file    is not None else _make_video(tmp)
    tf       = thumbnail_file if thumbnail_file is not None else _make_thumbnail(tmp)

    am_meta = approval_meta_override if approval_meta_override is not None else APPROVAL_META.copy()

    audio_map = {
        "script_title": sc.get("title", TOPIC),
        "total_duration_seconds": audio_duration,
        "provider": "kokoro",
        "audio_scenes": a_scenes,
        "full_narration_audio_file": str(audio_tmp / "full_narration.mp3"),
        "approval_metadata": am_meta,
    }
    # write full_narration stub
    (audio_tmp / "full_narration.mp3").write_bytes(b"\xff\xfb" + b"\x00" * 77)

    visual_map = {
        "script_title": sc.get("title", TOPIC),
        "total_scenes": len(v_scenes),
        "style_preset": "Devotional Cinematic Painting",
        "provider": visual_provider,
        "visual_scenes": v_scenes,
        "approval_metadata": am_meta,
    }

    video_scene_list = [
        {
            "scene": i,
            "image_file": v_scenes[i - 1]["image_file"] if v_scenes and i <= len(v_scenes) else "",
            "audio_file": a_scenes[i - 1]["audio_file"] if a_scenes and i <= len(a_scenes) else "",
            "duration_seconds": 30,
        }
        for i in range(1, video_scenes + 1)
    ]

    video_map = {
        "video_file": str(vf),
        "video_map_file": str(tmp / "video_map.json"),
        "total_duration": audio_duration,
        "resolution": "720x1280",
        "scenes": video_scene_list,
    }

    if thumbnail_meta is None:
        thumbnail_meta = {
            "title": TOPIC,
            "topic": TOPIC,
            "provider": "pil",
            "resolution": "1280x720",
            "format": "png",
            "approved_source": "youtube_api",
            "confidence": "high",
            "created_at": "20260813_120000",
            "approval_metadata": am_meta,
        }

    return PipelineArtifacts(
        decision        = dec,
        content_brief   = cb,
        script          = sc,
        audio_map       = audio_map,
        visual_map      = visual_map,
        video_map       = video_map,
        thumbnail_meta  = thumbnail_meta,
        decision_file       = str(tmp / "decision.json"),
        content_brief_file  = str(tmp / "content_brief.json"),
        script_file         = str(tmp / "script.json"),
        audio_map_file      = str(tmp / "audio_map.json"),
        visual_map_file     = str(tmp / "visual_map.json"),
        video_map_file      = str(tmp / "video_map.json"),
        thumbnail_meta_file = str(tmp / "thumbnail_meta.json"),
        video_file      = str(vf),
        thumbnail_file  = str(tf),
    )


def _write_artifacts_to_disk(arts: PipelineArtifacts, tmp: Path) -> None:
    """Write all JSON manifests to disk (needed for file-integrity checks)."""
    import dataclasses
    pairs = [
        (arts.decision_file,        arts.decision),
        (arts.content_brief_file,   arts.content_brief),
        (arts.script_file,          arts.script),
        (arts.audio_map_file,       arts.audio_map),
        (arts.visual_map_file,      arts.visual_map),
        (arts.video_map_file,       arts.video_map),
        (arts.thumbnail_meta_file,  arts.thumbnail_meta),
    ]
    for fpath, data in pairs:
        Path(fpath).write_text(json.dumps(data), encoding="utf-8")


def _run_gate(arts: PipelineArtifacts, tmp: Path) -> "QAResult":
    _write_artifacts_to_disk(arts, tmp)
    gate = FinalQAGate(allow_mock=True)
    return gate.run(artifacts=arts)


# ─────────────────────────────────────────────────────────────────────────────
# Test class
# ─────────────────────────────────────────────────────────────────────────────

class TestFinalQAGate(unittest.TestCase):

    # ── Test 1: Valid complete pipeline accepted ───────────────────────────
    def test_01_valid_complete_pipeline_accepted(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            arts = _build_artifacts(tmp)
            result = _run_gate(arts, tmp)
        self.assertTrue(result.approved_for_publishing, result.errors)
        self.assertTrue(result.all_passed(), result.errors)

    # ── Test 2: Rejected decision blocked ────────────────────────────────
    def test_02_rejected_decision_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            dec = {**VALID_DECISION, "approved_for_generation": False}
            arts = _build_artifacts(tmp, decision=dec)
            result = _run_gate(arts, tmp)
        self.assertFalse(result.approved_for_publishing)
        self.assertFalse(result.checks.get("decision_approval"))

    # ── Test 3: Mock source blocked ───────────────────────────────────────
    def test_03_mock_source_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            dec = {**VALID_DECISION, "data_source": "mock"}
            arts = _build_artifacts(tmp, decision=dec)
            result = _run_gate(arts, tmp)
        self.assertFalse(result.approved_for_publishing)
        self.assertFalse(result.checks.get("decision_approval"))

    # ── Test 4: Offline source blocked ────────────────────────────────────
    def test_04_offline_source_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            dec = {**VALID_DECISION, "data_source": "offline"}
            arts = _build_artifacts(tmp, decision=dec)
            result = _run_gate(arts, tmp)
        self.assertFalse(result.approved_for_publishing)
        self.assertFalse(result.checks.get("decision_approval"))

    # ── Test 5: Low confidence blocked ────────────────────────────────────
    def test_05_low_confidence_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            dec = {**VALID_DECISION, "confidence": "low"}
            arts = _build_artifacts(tmp, decision=dec)
            result = _run_gate(arts, tmp)
        self.assertFalse(result.approved_for_publishing)
        self.assertFalse(result.checks.get("decision_approval"))

    # ── Test 6: Missing decision file blocked ─────────────────────────────
    def test_06_missing_decision_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            arts = _build_artifacts(tmp)
            _write_artifacts_to_disk(arts, tmp)
            # Remove decision file from disk
            Path(arts.decision_file).unlink()
            gate = FinalQAGate()
            result = gate.run(artifacts=arts)
        self.assertFalse(result.approved_for_publishing)
        self.assertFalse(result.checks.get("file_integrity.decision_json"))

    # ── Test 7: Missing content brief blocked ────────────────────────────
    def test_07_missing_content_brief_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            arts = _build_artifacts(tmp)
            _write_artifacts_to_disk(arts, tmp)
            Path(arts.content_brief_file).unlink()
            gate = FinalQAGate()
            result = gate.run(artifacts=arts)
        self.assertFalse(result.approved_for_publishing)
        self.assertFalse(result.checks.get("file_integrity.content_brief_json"))

    # ── Test 8: Missing script blocked ────────────────────────────────────
    def test_08_missing_script_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            arts = _build_artifacts(tmp)
            _write_artifacts_to_disk(arts, tmp)
            Path(arts.script_file).unlink()
            gate = FinalQAGate()
            result = gate.run(artifacts=arts)
        self.assertFalse(result.approved_for_publishing)
        self.assertFalse(result.checks.get("file_integrity.script_json"))

    # ── Test 9: Missing audio map blocked ────────────────────────────────
    def test_09_missing_audio_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            arts = _build_artifacts(tmp)
            _write_artifacts_to_disk(arts, tmp)
            Path(arts.audio_map_file).unlink()
            gate = FinalQAGate()
            result = gate.run(artifacts=arts)
        self.assertFalse(result.approved_for_publishing)
        self.assertFalse(result.checks.get("file_integrity.audio_map_json"))

    # ── Test 10: Missing visual map blocked ───────────────────────────────
    def test_10_missing_visual_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            arts = _build_artifacts(tmp)
            _write_artifacts_to_disk(arts, tmp)
            Path(arts.visual_map_file).unlink()
            gate = FinalQAGate()
            result = gate.run(artifacts=arts)
        self.assertFalse(result.approved_for_publishing)
        self.assertFalse(result.checks.get("file_integrity.visual_map_json"))

    # ── Test 11: Missing video map blocked ────────────────────────────────
    def test_11_missing_video_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            arts = _build_artifacts(tmp)
            _write_artifacts_to_disk(arts, tmp)
            Path(arts.video_map_file).unlink()
            gate = FinalQAGate()
            result = gate.run(artifacts=arts)
        self.assertFalse(result.approved_for_publishing)
        self.assertFalse(result.checks.get("file_integrity.video_map_json"))

    # ── Test 12: Missing thumbnail meta blocked ───────────────────────────
    def test_12_missing_thumbnail_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            arts = _build_artifacts(tmp)
            _write_artifacts_to_disk(arts, tmp)
            Path(arts.thumbnail_meta_file).unlink()
            gate = FinalQAGate()
            result = gate.run(artifacts=arts)
        self.assertFalse(result.approved_for_publishing)
        self.assertFalse(result.checks.get("file_integrity.thumbnail_meta_json"))

    # ── Test 13: Topic mismatch blocked ───────────────────────────────────
    def test_13_topic_mismatch_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            # Completely different topic in thumbnail — triggers overlap failure
            tm = {
                "title": "Brahma Creates the Universe",
                "topic": "Brahma Creates the Universe",
                "provider": "pil",
                "resolution": "1280x720",
                "format": "png",
                "approved_source": "youtube_api",
                "confidence": "high",
                "created_at": "20260813_120000",
                "approval_metadata": APPROVAL_META,
            }
            arts = _build_artifacts(tmp, thumbnail_meta=tm)
            result = _run_gate(arts, tmp)
        self.assertFalse(result.approved_for_publishing)
        self.assertFalse(result.checks.get("topic_consistency"))

    # ── Test 14: Provenance mismatch blocked ──────────────────────────────
    def test_14_provenance_mismatch_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            bad_meta = {**APPROVAL_META, "selected_topic": "Brahma Creates the Universe"}
            # Inject bad meta only into audio_map (script still correct)
            arts = _build_artifacts(tmp, approval_meta_override=APPROVAL_META)
            arts.audio_map["approval_metadata"] = bad_meta
            result = _run_gate(arts, tmp)
        self.assertFalse(result.approved_for_publishing)
        self.assertFalse(result.checks.get("provenance"))

    # ── Test 15: Zero-byte artifact blocked ───────────────────────────────
    def test_15_zero_byte_artifact_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            vf = _make_video(tmp, zero_byte=True)
            arts = _build_artifacts(tmp, video_file=vf)
            result = _run_gate(arts, tmp)
        self.assertFalse(result.approved_for_publishing)
        self.assertFalse(result.checks.get("file_integrity.video_file"))

    # ── Test 16: Corrupted JSON blocked ───────────────────────────────────
    def test_16_corrupted_json_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            arts = _build_artifacts(tmp)
            _write_artifacts_to_disk(arts, tmp)
            # Corrupt the script JSON file
            Path(arts.script_file).write_text("{NOT VALID JSON", encoding="utf-8")
            gate = FinalQAGate()
            result = gate.run(artifacts=arts)
        self.assertFalse(result.approved_for_publishing)
        self.assertFalse(result.checks.get("file_integrity.script_json"))

    # ── Test 17: Corrupted media (thumbnail) blocked ──────────────────────
    def test_17_corrupted_media_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            # Use provider='pil' (non-mock) so PIL decode check fires
            tf = _make_thumbnail(tmp, corrupt=True)
            arts = _build_artifacts(tmp, thumbnail_file=tf)
            result = _run_gate(arts, tmp)
        self.assertFalse(result.approved_for_publishing)
        self.assertFalse(result.checks.get("thumbnail"))

    # ── Test 18: Scene count mismatch blocked ─────────────────────────────
    def test_18_scene_count_mismatch_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            audio_tmp = tmp / "audio"
            audio_tmp.mkdir()
            # Script has 5 scenes, audio has only 4 — mismatch must be caught
            a_scenes = _make_audio_scenes(audio_tmp, scenes=4)
            # video_scenes=4 prevents IndexError; script still has 5 → mismatch
            arts = _build_artifacts(
                tmp, audio_scenes=a_scenes, audio_duration=120, video_scenes=4
            )
            result = _run_gate(arts, tmp)
        self.assertFalse(result.approved_for_publishing)
        self.assertFalse(result.checks.get("scene_sync"))

    # ── Test 19: Scene ordering mismatch blocked ──────────────────────────
    def test_19_scene_ordering_mismatch_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            audio_tmp = tmp / "audio"
            audio_tmp.mkdir()
            a_scenes = _make_audio_scenes(audio_tmp, bad_scene_order=True)
            arts = _build_artifacts(tmp, audio_scenes=a_scenes)
            result = _run_gate(arts, tmp)
        self.assertFalse(result.approved_for_publishing)
        # Scene ordering failure shows up in audio check (scene 1 → 5) OR scene_sync
        scene_ok = result.checks.get("scene_sync", True) and result.checks.get("audio", True)
        self.assertFalse(scene_ok)

    # ── Test 20: Video validation failure blocked ─────────────────────────
    def test_20_video_validation_failure_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            vf = _make_video(tmp, zero_byte=True)
            arts = _build_artifacts(tmp, video_file=vf)
            result = _run_gate(arts, tmp)
        self.assertFalse(result.approved_for_publishing)

    # ── Test 21: Thumbnail validation failure blocked ─────────────────────
    def test_21_thumbnail_validation_failure_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            tf = _make_thumbnail(tmp, wrong_size=True)
            arts = _build_artifacts(tmp, thumbnail_file=tf)
            result = _run_gate(arts, tmp)
        self.assertFalse(result.approved_for_publishing)
        self.assertFalse(result.checks.get("thumbnail"))

    # ── Test 22: Audio validation failure blocked ─────────────────────────
    def test_22_audio_validation_failure_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            audio_tmp = tmp / "audio"
            audio_tmp.mkdir()
            a_scenes = _make_audio_scenes(audio_tmp, zero_byte=True)
            arts = _build_artifacts(tmp, audio_scenes=a_scenes)
            result = _run_gate(arts, tmp)
        self.assertFalse(result.approved_for_publishing)
        self.assertFalse(result.checks.get("audio"))

    # ── Test 23: Visual validation failure blocked ────────────────────────
    def test_23_visual_validation_failure_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            visual_tmp = tmp / "visual"
            visual_tmp.mkdir()
            # Use provider='pil' (non-mock) so PIL decode check runs
            v_scenes = _make_visual_scenes(visual_tmp, zero_byte=True)
            arts = _build_artifacts(tmp, visual_scenes=v_scenes, visual_provider="pil")
            result = _run_gate(arts, tmp)
        self.assertFalse(result.approved_for_publishing)
        self.assertFalse(result.checks.get("visual"))

    # ── Test 24: Metadata preservation ───────────────────────────────────
    def test_24_metadata_preservation(self):
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            arts = _build_artifacts(tmp)
            result = _run_gate(arts, tmp)
        meta = result.approval_metadata
        self.assertEqual(meta.get("approved_for_generation"), True)
        self.assertEqual(meta.get("selected_topic"), TOPIC)
        self.assertEqual(meta.get("score"), 66)
        self.assertEqual(meta.get("confidence"), "high")
        self.assertEqual(meta.get("data_source"), "youtube_api")
        self.assertTrue(result.approved_for_publishing)

    # ── Test 25: Deterministic output ─────────────────────────────────────
    def test_25_deterministic_output(self):
        """Two runs on identical inputs should both pass or both fail consistently."""
        results = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as td:
                tmp = Path(td)
                arts = _build_artifacts(tmp)
                results.append(_run_gate(arts, tmp))
        self.assertEqual(results[0].approved_for_publishing, results[1].approved_for_publishing)
        self.assertEqual(set(results[0].checks.keys()), set(results[1].checks.keys()))

    # ── Test 26: CLI execution ─────────────────────────────────────────────
    def test_26_cli_execution_works(self):
        """CLI exits 0 only on a fully approved run; structure must be valid."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            arts = _build_artifacts(tmp)
            _write_artifacts_to_disk(arts, tmp)

            cli = Path(__file__).parent.parent / "run_final_qa.py"
            env = os.environ.copy()
            env["PYTHONPATH"] = str(Path(__file__).parent.parent / "src")

            proc = subprocess.run(
                [
                    sys.executable, str(cli),
                    "--decision",       arts.decision_file,
                    "--content-brief",  arts.content_brief_file,
                    "--script",         arts.script_file,
                    "--audio-map",      arts.audio_map_file,
                    "--visual-map",     arts.visual_map_file,
                    "--video-map",      arts.video_map_file,
                    "--thumbnail-meta", arts.thumbnail_meta_file,
                    "--output-dir",     str(tmp / "qa"),
                    "--allow-mock",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                timeout=60,
            )
            output = proc.stdout + proc.stderr
            self.assertIn("FINAL PIPELINE QA GATE", output)
            self.assertIn("APPROVED FOR PUBLISHING", output)
            # Exit code 0 means approved_for_publishing = true
            self.assertEqual(proc.returncode, 0, msg=output)

    # ── Test 27: Fail-closed behaviour ────────────────────────────────────
    def test_27_fail_closed_behavior(self):
        """Any single failure must prevent approved_for_publishing."""
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            dec = {**VALID_DECISION, "approved_for_generation": False}
            arts = _build_artifacts(tmp, decision=dec)
            result = _run_gate(arts, tmp)
        # Fail-closed: even though the rest passes, decision failure kills approval
        self.assertFalse(result.approved_for_publishing)
        # Errors list must be populated
        self.assertTrue(len(result.errors) > 0)


# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    unittest.main(verbosity=2)
