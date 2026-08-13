import os
import shutil
import sys
import io
import time
from pathlib import Path

# Force UTF-8 stdout
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Ensure we import prepare_assets correctly from the root workspace
sys.path.insert(0, os.getcwd())
import prepare_assets

TEST_GOD_SRC = Path("assets/gods/test_god")
TEST_GOD_PROC = Path("assets/gods_processed/test_god")

def clean_test_dirs():
    if TEST_GOD_SRC.exists():
        shutil.rmtree(TEST_GOD_SRC)
    if TEST_GOD_PROC.exists():
        shutil.rmtree(TEST_GOD_PROC)
    # Remove from manifest
    manifest = prepare_assets.load_asset_manifest()
    keys_to_del = [k for k in manifest if k.startswith("test_god/")]
    for k in keys_to_del:
        del manifest[k]
    prepare_assets.save_asset_manifest(manifest)

def get_ffmpeg_count_from_output(output: str) -> int:
    return output.count("[ASSET] CONVERT")

def run_test():
    print("🧪 Starting Incremental Asset Conform tests...\n")
    clean_test_dirs()

    # Find a real image to copy for realistic test
    real_images = list(Path("assets/gods/").glob("*/*.jpg")) + list(Path("assets/gods/").glob("*/*.jpeg")) + list(Path("assets/gods/").glob("*/*.png"))
    if not real_images:
        # If no real images are in the repo (e.g. sparse checkout in CI), create a mock image using ffmpeg!
        print("ℹ️ No real images found in assets/gods. Creating mock image using FFmpeg...")
        TEST_GOD_SRC.mkdir(parents=True, exist_ok=True)
        mock_img = TEST_GOD_SRC / "test_image.jpg"
        # Generate a solid color 1280x720 JPEG using FFmpeg
        cmd = [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=blue:s=1280x720",
            "-vframes", "1", str(mock_img)
        ]
        import subprocess
        subprocess.run(cmd, check=True, capture_output=True)
    else:
        real_image = real_images[0]
        print(f"📋 Using sample image: {real_image.name} for testing.")
        TEST_GOD_SRC.mkdir(parents=True, exist_ok=True)
        shutil.copy(real_image, TEST_GOD_SRC / "test_image.jpg")

    # Capture outputs by redirecting stdout
    def capture_prepare():
        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()
        try:
            prepare_assets.prepare_deity_assets("test_god")
        finally:
            sys.stdout = old_stdout
        return buffer.getvalue()

    # ─────────────────────────────────────────────────────────────────────────
    # Test 1: First Run (New Asset)
    # ─────────────────────────────────────────────────────────────────────────
    print("▶️ TEST 1: First run (asset does not exist in conformed cache)")
    t0 = time.time()
    out1 = capture_prepare()
    t1 = time.time()
    print(out1.strip())
    ffmpeg_count_1 = get_ffmpeg_count_from_output(out1)
    print(f"   Time taken: {t1 - t0:.2f}s | FFmpeg invocations: {ffmpeg_count_1}")
    
    # Assert conformed vertical and horizontal exists
    v_clip = TEST_GOD_PROC / "vertical/test_image__img.mp4"
    h_clip = TEST_GOD_PROC / "horizontal/test_image__img.mp4"
    assert v_clip.exists() and v_clip.stat().st_size > 0, "Vertical clip missing or empty"
    assert h_clip.exists() and h_clip.stat().st_size > 0, "Horizontal clip missing or empty"
    
    # Validate resolution using ffprobe
    assert prepare_assets.validate_conformed_clip(v_clip, 720, 1280), "Vertical clip invalid specs"
    assert prepare_assets.validate_conformed_clip(h_clip, 1920, 1080), "Horizontal clip invalid specs"
    print("   ✅ Test 1 Passed: Clips conformed and validated with correct dimensions (720x1280, 1920x1080).")

    # ─────────────────────────────────────────────────────────────────────────
    # Test 2: Second Run (Unchanged Cache)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n▶️ TEST 2: Second run (assets already valid and unchanged)")
    t0 = time.time()
    out2 = capture_prepare()
    t1 = time.time()
    print(out2.strip())
    ffmpeg_count_2 = get_ffmpeg_count_from_output(out2)
    print(f"   Time taken: {t1 - t0:.2f}s | FFmpeg invocations: {ffmpeg_count_2}")
    assert ffmpeg_count_2 == 0, "FFmpeg should not run for unchanged assets"
    print("   ✅ Test 2 Passed: FFmpeg calls skipped and conformed assets reused.")

    # ─────────────────────────────────────────────────────────────────────────
    # Test 3: Corrupted Output Rebuild
    # ─────────────────────────────────────────────────────────────────────────
    print("\n▶️ TEST 3: Corrupted output detection (truncate conformed vertical clip to 0 bytes)")
    # Corrupt vertical by writing 0 bytes
    v_clip.write_text("")
    t0 = time.time()
    out3 = capture_prepare()
    t1 = time.time()
    print(out3.strip())
    ffmpeg_count_3 = get_ffmpeg_count_from_output(out3)
    print(f"   Time taken: {t1 - t0:.2f}s | FFmpeg invocations: {ffmpeg_count_3}")
    assert ffmpeg_count_3 == 1, "FFmpeg should run exactly once to repair vertical clip"
    assert "[ASSET] CONVERT  test_image.jpg → vertical (corrupt)" in out3, "Logs must indicate corrupt rebuild"
    assert "[ASSET] SKIP     test_image.jpg → horizontal (cached)" in out3, "Horizontal should still be skipped"
    print("   ✅ Test 3 Passed: Corrupt clip detected and rebuilt; intact clip skipped.")

    # ─────────────────────────────────────────────────────────────────────────
    # Test 4: Changed Source Rebuild
    # ─────────────────────────────────────────────────────────────────────────
    print("\n▶️ TEST 4: Changed source detection (modifying modification timestamp/size)")
    # Let's modify the source image size slightly by appending bytes
    test_img = TEST_GOD_SRC / "test_image.jpg"
    with open(test_img, "ab") as f:
        f.write(b"EXTRABYTES")
    
    t0 = time.time()
    out4 = capture_prepare()
    t1 = time.time()
    print(out4.strip())
    ffmpeg_count_4 = get_ffmpeg_count_from_output(out4)
    print(f"   Time taken: {t1 - t0:.2f}s | FFmpeg invocations: {ffmpeg_count_4}")
    assert ffmpeg_count_4 == 2, "FFmpeg should run twice (both vertical and horizontal) for changed source"
    assert "[ASSET] CONVERT  test_image.jpg → vertical (changed)" in out4
    assert "[ASSET] CONVERT  test_image.jpg → horizontal (changed)" in out4
    print("   ✅ Test 4 Passed: Changed source detected; both formats rebuilt.")

    # ─────────────────────────────────────────────────────────────────────────
    # Test 5: Fresh environment simulation
    # ─────────────────────────────────────────────────────────────────────────
    print("\n▶️ TEST 5: Fresh environment bootstrap (deleting processed folder but keeping manifest)")
    if TEST_GOD_PROC.exists():
        shutil.rmtree(TEST_GOD_PROC)
    
    t0 = time.time()
    out5 = capture_prepare()
    t1 = time.time()
    print(out5.strip())
    ffmpeg_count_5 = get_ffmpeg_count_from_output(out5)
    print(f"   Time taken: {t1 - t0:.2f}s | FFmpeg invocations: {ffmpeg_count_5}")
    assert ffmpeg_count_5 == 2, "FFmpeg should rebuild both vertical and horizontal in fresh env"
    print("   ✅ Test 5 Passed: System rebuilt missing conformed outputs successfully.")

    # Clean up test directories
    clean_test_dirs()
    print("\n🎉 All 5 incremental conforming tests completed successfully!")

if __name__ == "__main__":
    run_test()
