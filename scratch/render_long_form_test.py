import os
import sys
import io
import json
import subprocess
from pathlib import Path

# Force UTF-8 stdout/stderr on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

sys.path.insert(0, os.getcwd())

from src.video.generator import (
    compose_video_pipeline,
    perform_video_qa,
    validate_video_file_with_ffprobe,
)
from src.qa.gate import FinalQAGate, QAResult
from src.publisher.safety import validate_qa_for_publishing
from src.publisher.metadata import build_video_metadata

AUDIO_MAP_FILE = Path("data/audio/audio_map_20260813_223645.json")
VISUAL_MAP_FILE = Path("data/visuals/visual_map_20260813_223645.json")
OUTPUT_DIR = Path("data/videos")
QA_DIR = Path("data/qa")


def main():
    print("==========================================================")
    print("🎬 STARTING CONTROLLED LONG-FORM (16:9 1920x1080) PIPELINE TEST")
    print("==========================================================")

    if not AUDIO_MAP_FILE.exists() or not VISUAL_MAP_FILE.exists():
        print(f"❌ Missing timing map inputs: {AUDIO_MAP_FILE} or {VISUAL_MAP_FILE}")
        sys.exit(1)

    audio_map = json.loads(AUDIO_MAP_FILE.read_text(encoding="utf-8"))
    visual_map = json.loads(VISUAL_MAP_FILE.read_text(encoding="utf-8"))

    # ── Step 1: Render 1920x1080 LONG video ─────────────────────────────────
    print("\n1️⃣ Rendering 1920x1080 landscape video (content_type='long')...")
    video_map = compose_video_pipeline(
        audio_map=audio_map,
        visual_map=visual_map,
        composer_type="ffmpeg",
        output_dir=OUTPUT_DIR,
        output_file_name="shiva_long_test_final.mp4",
        content_type="long",
    )

    video_file = Path(video_map["video_file"])
    vmap_file = Path(video_map["video_map_file"])
    vmap_file.write_text(json.dumps(video_map, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"✅ Rendered: {video_file.name}")
    print(f"   Resolution:   {video_map['resolution']}")
    print(f"   Aspect Ratio: {video_map['aspect_ratio']}")
    print(f"   Content Type: {video_map['content_type']}")

    # ── Step 2: ffprobe validation ──────────────────────────────────────────
    print("\n2️⃣ Running ffprobe and decode validation...")
    ok_probe, probe_detail = validate_video_file_with_ffprobe(
        video_file,
        content_type="long",
    )
    if not ok_probe:
        print(f"❌ ffprobe failed: {probe_detail}")
        sys.exit(1)
    print(f"✅ ffprobe validation passed: {probe_detail}")

    # ── Step 3: Resolution mismatch safety verification ───────────────────
    print("\n3️⃣ Testing Resolution Mismatch Gates (Fail-Closed)...")
    
    # 3a. Request short on 1920x1080 video -> MUST FAIL
    ok_mismatch_1, err_1, _ = check_mismatch_with_ffprobe(video_file, content_type="short")
    if not ok_mismatch_1:
        print(f"✅ PASS: short requested on 1920x1080 video correctly REJECTED: {err_1}")
    else:
        print("❌ FAIL: short requested on 1920x1080 video was unexpectedly accepted!")
        sys.exit(1)

    # ── Step 4: Final QA Gate ──────────────────────────────────────────────
    print("\n4️⃣ Generating Final QA Gate result for LONG video...")
    qa_result = perform_final_qa_for_long_video(video_map, video_file)
    qa_path = QA_DIR / "final_qa_shiva_long_test.json"
    qa_path.write_text(json.dumps(qa_result.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✅ Saved QA result: {qa_path}")
    print(f"   Approved for Publishing: {qa_result.approved_for_publishing}")
    print(f"   Content Type:            {qa_result.content_type}")

    if not qa_result.approved_for_publishing:
        print(f"❌ QA errors: {qa_result.errors}")
        sys.exit(1)

    # ── Step 5: Publisher Safety Gate ──────────────────────────────────────
    print("\n5️⃣ Validating Publisher Safety Gate...")
    try:
        validate_qa_for_publishing(qa_result.to_dict())
        print("✅ Publisher safety gate PASSED.")
    except Exception as e:
        print(f"❌ Publisher safety gate failed: {e}")
        sys.exit(1)

    # ── Step 6: Metadata Builder Verification ──────────────────────────────
    print("\n6️⃣ Verifying YouTube Metadata Builder for LONG format...")
    meta = build_video_metadata(qa_result.to_dict())
    print(f"   Title:       {meta['title']}")
    print(f"   Tags:        {meta['tags']}")
    print(f"   Shorts tag in tags?     {'Shorts' in meta['tags']}")
    print(f"   #Shorts in description? {'#Shorts' in meta['description']}")

    if "Shorts" in meta["tags"] or "#Shorts" in meta["description"]:
        print("❌ FAIL: Shorts tags found in long-form metadata!")
        sys.exit(1)
    print("✅ PASS: Long-form metadata contains NO Shorts tags/hashtags.")

    # ── Step 7: Publisher Dry-Run ──────────────────────────────────────────
    print("\n7️⃣ Executing Publisher Dry-Run...")
    res = subprocess.run(
        ["py", "run_publisher.py", "--qa", str(qa_path), "--dry-run"],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    print(res.stdout)
    if res.returncode != 0:
        print(f"❌ Publisher dry-run failed (exit {res.returncode}): {res.stderr}")
        sys.exit(1)

    print("==========================================================")
    print("🎉 LONG-FORM PRODUCTION PIPELINE TEST PASSED SUCCESSFULLY!")
    print("==========================================================")


def check_mismatch_with_ffprobe(video_file, content_type):
    from src.qa.checks import check_video_with_ffprobe
    return check_video_with_ffprobe(video_file, content_type=content_type)


def perform_final_qa_for_long_video(video_map, video_file):
    # Load base production artifacts
    script_file = Path("data/scripts/script_master_shiva.json")
    brief_file = Path("data/content_briefs/content_brief_20260813_194729.json")
    decision_file = Path("data/decision/decision_20260814_071510.json")
    audio_map_file = Path("data/audio/audio_map_20260813_223645.json")
    visual_map_file = Path("data/visuals/visual_map_20260813_223645.json")
    thumb_meta_file = Path("data/thumbnails/thumbnail_metadata_20260813_203805.json")

    gate = FinalQAGate(
        base_dir=".",
        content_type="long",
        decision_file=str(decision_file),
        content_brief_file=str(brief_file),
        script_file=str(script_file),
        audio_map_file=str(audio_map_file),
        visual_map_file=str(visual_map_file),
        video_map_file=str(video_map["video_map_file"]),
        thumbnail_meta_file=str(thumb_meta_file),
    )
    return gate.run()


if __name__ == "__main__":
    main()
