"""
prepare_assets.py — God Channel Asset Preparation (v2)
--------------------------------------------------------
Converts RAW images *and* raw short video clips found in each god subfolder
into normalized MP4 clips, ready to be mixed freely downstream:

  - Vertical   (720x1280)  for Shorts
  - Horizontal (1920x1080) for Long Videos

Images  -> become a CLIP_MIN_S–CLIP_MAX_S second still clip (randomized).
Videos  -> re-encoded to the same spec (30fps, yuv420p, no audio). If a
           source clip is shorter than VIDEO_MIN_S it is looped up to a
           random target inside [VIDEO_MIN_S, VIDEO_MAX_S]; if longer than
           VIDEO_MAX_S it is trimmed down to VIDEO_MAX_S.

Both outputs land in the SAME vertical/ and horizontal/ folders per god, so
generate_short.py can pick from a single pool that mixes photos and clips.
Output filenames are tagged with their origin (__img / __vid) so downstream
logic can tell a still image apart from real footage when it matters (e.g.
Ken Burns should only ever be applied to a still).

No music/audio processing — music is uploaded manually, all clips are muted
at this stage (-an) to keep downstream concatenation/crossfade simple.
"""

import subprocess
import random
from pathlib import Path

# ─────────────────────────────────────────────
# FOLDER STRUCTURE:
# assets/gods/
#   lord_vishnu/      ← raw images (.jpg/.png/.webp) AND/OR raw short clips (.mp4/.mov/...)
#   shiva/
#   hanuman/
#   kali_amma/
#   seetha/
#   … (any new folder added here is auto-picked up)
#
# Output:
# assets/gods_processed/
#   lord_vishnu/
#     vertical/      ← 720x1280 clips for Shorts   (stem__img.mp4 / stem__vid.mp4)
#     horizontal/    ← 1920x1080 clips for Long Video
#   shiva/
#   …
# ─────────────────────────────────────────────

GODS_BASE   = Path("assets/gods")
PROC_BASE   = Path("assets/gods_processed")

IMAGE_EXTS  = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTS  = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}

CLIP_MIN_S   = 2   # image: minimum seconds per still clip
CLIP_MAX_S   = 4   # image: maximum seconds per still clip

VIDEO_MIN_S  = 2   # video: loop up to this if the source clip is shorter
VIDEO_MAX_S  = 6   # video: trim down to this if the source clip is longer


# ── ffmpeg / ffprobe helpers ──────────────────────────────────────────────

def run_ffmpeg(cmd: list):
    """Run an ffmpeg command, raise on failure."""
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"  ❌ FFmpeg error:\n{e.stderr[-800:]}")
        raise


def get_duration(path: Path) -> float:
    """Return duration in seconds of a media file via ffprobe. 0.0 on failure."""
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1", str(path)]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
        return float(out) if out else 0.0
    except Exception:
        return 0.0


# ── Image → still clip ────────────────────────────────────────────────────

def make_vertical_image_clip(img: Path, out: Path, duration: int):
    """720x1280 vertical clip from a still image — fills frame, no letterbox."""
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


def make_horizontal_image_clip(img: Path, out: Path, duration: int):
    """1920x1080 horizontal clip from a still image — fills frame, no letterbox."""
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


# ── Video → normalized clip ───────────────────────────────────────────────

def _resolve_video_target(src: Path, min_s: int, max_s: int):
    """Decide the output duration + whether looping is required."""
    src_dur = get_duration(src)
    if src_dur <= 0:
        # Unreadable duration — fall back to a safe fixed length, no loop.
        return float(max_s), False
    if src_dur > max_s:
        return float(max_s), False
    if src_dur < min_s:
        return round(random.uniform(min_s, max_s), 2), True
    return round(src_dur, 2), False


def make_vertical_video_clip(vid: Path, out: Path, min_s: int = VIDEO_MIN_S, max_s: int = VIDEO_MAX_S):
    """720x1280 vertical clip from a short raw video clip."""
    target, needs_loop = _resolve_video_target(vid, min_s, max_s)
    cmd = ["ffmpeg", "-y"]
    if needs_loop:
        cmd += ["-stream_loop", "-1"]
    cmd += [
        "-i", str(vid),
        "-t", f"{target:.2f}",
        "-vf", (
            "scale=720:1280:force_original_aspect_ratio=increase,"
            "crop=720:1280,"
            "setsar=1,fps=30"
        ),
        "-c:v", "libx264", "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        "-an",
        str(out)
    ]
    run_ffmpeg(cmd)


def make_horizontal_video_clip(vid: Path, out: Path, min_s: int = VIDEO_MIN_S, max_s: int = VIDEO_MAX_S):
    """1920x1080 horizontal clip from a short raw video clip."""
    target, needs_loop = _resolve_video_target(vid, min_s, max_s)
    cmd = ["ffmpeg", "-y"]
    if needs_loop:
        cmd += ["-stream_loop", "-1"]
    cmd += [
        "-i", str(vid),
        "-t", f"{target:.2f}",
        "-vf", (
            "scale=1920:1080:force_original_aspect_ratio=increase,"
            "crop=1920:1080,"
            "setsar=1,fps=30"
        ),
        "-c:v", "libx264", "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        "-an",
        str(out)
    ]
    run_ffmpeg(cmd)


# ── Per-god processing ────────────────────────────────────────────────────

def process_god_folder(god_dir: Path):
    """Process all images AND video clips in one god subfolder."""
    files = sorted(
        f for f in god_dir.iterdir()
        if f.suffix.lower() in IMAGE_EXTS or f.suffix.lower() in VIDEO_EXTS
    )
    if not files:
        print(f"  ⚠️  No images or video clips found in {god_dir.name}, skipping.")
        return

    vert_dir = PROC_BASE / god_dir.name / "vertical"
    horiz_dir = PROC_BASE / god_dir.name / "horizontal"
    vert_dir.mkdir(parents=True, exist_ok=True)
    horiz_dir.mkdir(parents=True, exist_ok=True)

    n_img = sum(1 for f in files if f.suffix.lower() in IMAGE_EXTS)
    n_vid = sum(1 for f in files if f.suffix.lower() in VIDEO_EXTS)
    print(f"\n📂 Processing: {god_dir.name} ({n_img} images, {n_vid} video clips)")

    for f in files:
        is_video = f.suffix.lower() in VIDEO_EXTS
        stem = f.stem
        tag = "vid" if is_video else "img"

        v_out = vert_dir  / f"{stem}__{tag}.mp4"
        h_out = horiz_dir / f"{stem}__{tag}.mp4"

        if v_out.exists() and h_out.exists():
            print(f"  ✅ {f.name} already processed.")
            continue

        if is_video:
            if not v_out.exists():
                print(f"  🔨 Vertical (video)   {f.name}")
                make_vertical_video_clip(f, v_out)
            if not h_out.exists():
                print(f"  🔨 Horizontal (video) {f.name}")
                make_horizontal_video_clip(f, h_out)
        else:
            duration = random.randint(CLIP_MIN_S, CLIP_MAX_S)
            if not v_out.exists():
                print(f"  🔨 Vertical (image)   {f.name} → {duration}s")
                make_vertical_image_clip(f, v_out, duration)
            if not h_out.exists():
                print(f"  🔨 Horizontal (image) {f.name} → {duration}s")
                make_horizontal_image_clip(f, h_out, duration)


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
