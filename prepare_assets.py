"""
prepare_assets.py — God Channel Asset Preparation
Converts raw images in each god subfolder into short MP4 clips:
  - Vertical (720x1280) for Shorts
  - Horizontal (1920x1080) for Long Videos
Each image becomes a 2–4 second clip (randomized).
No music processing — music is uploaded manually.
"""

import subprocess
import random
from pathlib import Path

# ─────────────────────────────────────────────
# FOLDER STRUCTURE:
# assets/gods/
#   lord_vishnu/      ← raw images (.jpg/.png/.webp)
#   shiva/
#   hanuman/
#   kali_amma/
#   seetha/
#   … (any new folder added here is auto-picked up)
#
# Output:
# assets/gods_processed/
#   lord_vishnu/
#     vertical/      ← 720x1280 clips for Shorts
#     horizontal/    ← 1920x1080 clips for Long Video
#   shiva/
#   …
# ─────────────────────────────────────────────

GODS_BASE   = Path("assets/gods")
PROC_BASE   = Path("assets/gods_processed")
IMAGE_EXTS  = {".jpg", ".jpeg", ".png", ".webp", ".JPG", ".JPEG", ".PNG"}
CLIP_MIN_S  = 2   # minimum seconds per image clip
CLIP_MAX_S  = 4   # maximum seconds per image clip


def run_ffmpeg(cmd: list):
    """Run an ffmpeg command, raise on failure."""
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"  ❌ FFmpeg error:\n{e.stderr[-800:]}")
        raise


def make_vertical_clip(img: Path, out: Path, duration: int):
    """720x1280 vertical clip — fills frame, no letterbox."""
    cmd = [
        "ffmpeg", "-y", "-loop", "1",
        "-i", str(img),
        "-t", str(duration),
        "-vf", (
            "scale=720:1280:force_original_aspect_ratio=increase,"
            "crop=720:1280,"
            "setsar=1"
        ),
        "-c:v", "libx264", "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        "-r", "30", "-an",
        str(out)
    ]
    run_ffmpeg(cmd)


def make_horizontal_clip(img: Path, out: Path, duration: int):
    """1920x1080 horizontal clip — fills frame, no letterbox."""
    cmd = [
        "ffmpeg", "-y", "-loop", "1",
        "-i", str(img),
        "-t", str(duration),
        "-vf", (
            "scale=1920:1080:force_original_aspect_ratio=increase,"
            "crop=1920:1080,"
            "setsar=1"
        ),
        "-c:v", "libx264", "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        "-r", "30", "-an",
        str(out)
    ]
    run_ffmpeg(cmd)


def process_god_folder(god_dir: Path):
    """Process all images in one god subfolder."""
    images = [f for f in god_dir.iterdir() if f.suffix in IMAGE_EXTS]
    if not images:
        print(f"  ⚠️  No images found in {god_dir.name}, skipping.")
        return

    vert_dir = PROC_BASE / god_dir.name / "vertical"
    horiz_dir = PROC_BASE / god_dir.name / "horizontal"
    vert_dir.mkdir(parents=True, exist_ok=True)
    horiz_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n📂 Processing: {god_dir.name} ({len(images)} images)")

    for img in sorted(images):
        duration = random.randint(CLIP_MIN_S, CLIP_MAX_S)
        stem = img.stem

        v_out = vert_dir  / f"{stem}.mp4"
        h_out = horiz_dir / f"{stem}.mp4"

        if not v_out.exists():
            print(f"  🔨 Vertical  {img.name} → {duration}s")
            make_vertical_clip(img, v_out, duration)
        else:
            print(f"  ✅ Vertical  {img.name} already processed.")

        if not h_out.exists():
            print(f"  🔨 Horizontal {img.name} → {duration}s")
            make_horizontal_clip(img, h_out, duration)
        else:
            print(f"  ✅ Horizontal {img.name} already processed.")


def main():
    if not GODS_BASE.exists():
        print(f"❌ FATAL: Source folder not found: {GODS_BASE}")
        print("   Please create it and add subfolders like: assets/gods/lord_vishnu/")
        exit(1)

    god_folders = [d for d in GODS_BASE.iterdir() if d.is_dir()]
    if not god_folders:
        print(f"❌ No god subfolders found inside {GODS_BASE}")
        exit(1)

    print(f"🙏 Found {len(god_folders)} god folder(s): {[d.name for d in god_folders]}")

    for gf in sorted(god_folders):
        process_god_folder(gf)

    print("\n✅ All assets prepared successfully!")


if __name__ == "__main__":
    main()
