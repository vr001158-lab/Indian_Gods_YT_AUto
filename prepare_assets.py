"""
prepare_assets.py — God Channel Asset Preparation (v2.2)
Converts raw images and videos in each god subfolder into conformed MP4 clips.
Supports incremental preparation using an asset manifest to skip existing valid clips.
"""

import sys
import io
import json
import random
import subprocess
from pathlib import Path

# Force stdout/stderr to use UTF-8 to prevent console encoding crashes on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# ─────────────────────────────────────────────
# FOLDER STRUCTURE:
# assets/gods/
#   lord_vishnu/      ← raw images (.jpg/.png/.webp) and videos (.mp4)
#
# Output:
# assets/gods_processed/
#   lord_vishnu/
#     vertical/      ← 720x1280 clips
#     horizontal/    ← 1920x1080 clips
# ─────────────────────────────────────────────

GODS_BASE   = Path("assets/gods")
PROC_BASE   = Path("assets/gods_processed")
MANIFEST_FILE = Path("assets/asset_manifest.json")

IMAGE_EXTS  = {".jpg", ".jpeg", ".png", ".webp", ".JPG", ".JPEG", ".PNG"}
VIDEO_EXTS  = {".mp4", ".avi", ".mov", ".mkv", ".MP4", ".AVI", ".MOV", ".MKV"}

CLIP_MIN_S  = 2   # minimum seconds per image clip
CLIP_MAX_S  = 4   # maximum seconds per image clip


# ── Manifest Helpers ─────────────────────────────────────────────────────────

def load_asset_manifest() -> dict:
    if MANIFEST_FILE.exists():
        try:
            return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_asset_manifest(manifest: dict):
    try:
        MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST_FILE.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"⚠️ Error saving asset manifest: {e}", file=sys.stderr)


# ── Quality Validation Helper ────────────────────────────────────────────────

def validate_conformed_clip(clip_path: Path, expected_w: int, expected_h: int) -> bool:
    """
    Checks if video file exists, is non-empty, readable by ffprobe,
    and has correct dimensions/codec.
    """
    if not clip_path.exists():
        return False
    if clip_path.stat().st_size == 0:
        return False

    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,pix_fmt,width,height,duration",
        "-of", "json",
        str(clip_path)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        streams = data.get("streams", [])
        if not streams:
            return False

        stream = streams[0]
        codec = stream.get("codec_name")
        pix_fmt = stream.get("pix_fmt")
        width = stream.get("width")
        height = stream.get("height")

        # Resolve duration
        duration = stream.get("duration")
        if duration is None:
            # Fallback check duration using format
            cmd_fmt = [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json",
                str(clip_path)
            ]
            res_fmt = subprocess.run(cmd_fmt, capture_output=True, text=True, check=True)
            data_fmt = json.loads(res_fmt.stdout)
            duration = data_fmt.get("format", {}).get("duration")

        if duration is not None:
            try:
                duration_val = float(duration)
            except ValueError:
                duration_val = 0.0
        else:
            duration_val = 0.0

        if duration_val <= 0:
            return False

        # Validate specs
        if codec != "h264":
            return False
        if pix_fmt not in ("yuv420p", "yuvj420p"):
            return False
        if width != expected_w or height != expected_h:
            return False

        return True
    except Exception:
        return False


# ── FFmpeg Conforming ────────────────────────────────────────────────────────

def run_ffmpeg(cmd: list, src: Path = None, out: Path = None):
    """Run an ffmpeg command with -nostdin and a 60-second timeout."""
    if cmd and cmd[0] == "ffmpeg" and "-nostdin" not in cmd:
        cmd.insert(1, "-nostdin")

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired as e:
        err_msg = f"❌ FFMPEG TIMEOUT: FFmpeg process timed out after 60 seconds."
        if src:
            err_msg += f"\n   Input file:  {src}"
        if out:
            err_msg += f"\n   Output file: {out}"
        err_msg += f"\n   Command:     {' '.join(cmd)}"
        print(err_msg, file=sys.stderr)
        raise e
    except subprocess.CalledProcessError as e:
        print(f"  ❌ FFmpeg error:\n{e.stderr[-800:]}", file=sys.stderr)
        raise


def make_vertical_clip(src: Path, out: Path, duration: int, is_video: bool):
    """720x1280 vertical clip — fills frame, no letterbox."""
    if is_video:
        cmd = [
            "ffmpeg", "-y", "-i", str(src),
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
    else:
        cmd = [
            "ffmpeg", "-y", "-loop", "1",
            "-i", str(src),
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
    run_ffmpeg(cmd, src=src, out=out)


def make_horizontal_clip(src: Path, out: Path, duration: int, is_video: bool):
    """1920x1080 horizontal clip — fills frame, no letterbox."""
    if is_video:
        cmd = [
            "ffmpeg", "-y", "-i", str(src),
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
    else:
        cmd = [
            "ffmpeg", "-y", "-loop", "1",
            "-i", str(src),
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
    run_ffmpeg(cmd, src=src, out=out)


# ── Conforming Sourcing ──────────────────────────────────────────────────────

def process_god_folder(god_dir: Path, manifest: dict) -> bool:
    """Process raw files in one god subfolder incrementally."""
    items = [f for f in god_dir.iterdir() if f.suffix in IMAGE_EXTS or f.suffix in VIDEO_EXTS]
    if not items:
        print(f"  ⚠️  No raw media found in {god_dir.name}, skipping.")
        return False

    vert_dir = PROC_BASE / god_dir.name / "vertical"
    horiz_dir = PROC_BASE / god_dir.name / "horizontal"
    vert_dir.mkdir(parents=True, exist_ok=True)
    horiz_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n📂 Processing: {god_dir.name} ({len(items)} items)")

    manifest_changed = False

    for item in sorted(items):
        is_video = item.suffix in VIDEO_EXTS
        suffix = "__vid" if is_video else "__img"
        duration = random.randint(CLIP_MIN_S, CLIP_MAX_S)
        stem = item.stem

        v_out = vert_dir  / f"{stem}{suffix}.mp4"
        h_out = horiz_dir / f"{stem}{suffix}.mp4"

        # Unique key and fingerprint
        src_key = f"{god_dir.name}/{item.name}"
        stat_item = item.stat()
        src_fingerprint = f"{stat_item.st_size}_{stat_item.st_mtime}"

        # Load cached metadata
        cached = manifest.get(src_key, {})
        cached_fingerprint = cached.get("fingerprint")

        # ─── Process Vertical ─────────────────────────────────────────────────
        need_vertical = True
        if cached_fingerprint == src_fingerprint and v_out.exists():
            vert_cache = cached.get("vertical", {})
            v_stat = v_out.stat()
            # Fast check
            if vert_cache.get("size") == v_stat.st_size and vert_cache.get("mtime") == v_stat.st_mtime:
                need_vertical = False
                print(f"  [ASSET] SKIP     {item.name} → vertical (cached)")
            else:
                # Fallback check
                if validate_conformed_clip(v_out, 720, 1280):
                    need_vertical = False
                    vert_cache["size"] = v_stat.st_size
                    vert_cache["mtime"] = v_stat.st_mtime
                    manifest_changed = True
                    print(f"  [ASSET] SKIP     {item.name} → vertical (re-validated)")

        if need_vertical:
            if not v_out.exists():
                reason = "new"
            elif cached_fingerprint != src_fingerprint:
                reason = "changed"
            else:
                reason = "corrupt"
            print(f"  [ASSET] CONVERT  {item.name} → vertical ({reason})")

            v_tmp = vert_dir / f"{stem}{suffix}_tmp.mp4"
            try:
                make_vertical_clip(item, v_tmp, duration, is_video)
                if v_tmp.exists():
                    if v_out.exists():
                        v_out.unlink()
                    v_tmp.rename(v_out)

                    # Validate output and save metadata
                    if validate_conformed_clip(v_out, 720, 1280):
                        v_stat = v_out.stat()
                        if src_key not in manifest:
                            manifest[src_key] = {}
                        manifest[src_key]["fingerprint"] = src_fingerprint
                        manifest[src_key]["vertical"] = {
                            "path": str(v_out),
                            "size": v_stat.st_size,
                            "mtime": v_stat.st_mtime
                        }
                        manifest_changed = True
                    else:
                        print(f"  ❌ Error: Vertical conformed clip for {item.name} failed verification.", file=sys.stderr)
            except Exception as e:
                if v_tmp.exists():
                    v_tmp.unlink()
                raise e

        # ─── Process Horizontal ───────────────────────────────────────────────
        need_horizontal = True
        if cached_fingerprint == src_fingerprint and h_out.exists():
            horiz_cache = cached.get("horizontal", {})
            h_stat = h_out.stat()
            if horiz_cache.get("size") == h_stat.st_size and horiz_cache.get("mtime") == h_stat.st_mtime:
                need_horizontal = False
                print(f"  [ASSET] SKIP     {item.name} → horizontal (cached)")
            else:
                if validate_conformed_clip(h_out, 1920, 1080):
                    need_horizontal = False
                    horiz_cache["size"] = h_stat.st_size
                    horiz_cache["mtime"] = h_stat.st_mtime
                    manifest_changed = True
                    print(f"  [ASSET] SKIP     {item.name} → horizontal (re-validated)")

        if need_horizontal:
            if not h_out.exists():
                reason = "new"
            elif cached_fingerprint != src_fingerprint:
                reason = "changed"
            else:
                reason = "corrupt"
            print(f"  [ASSET] CONVERT  {item.name} → horizontal ({reason})")

            h_tmp = horiz_dir / f"{stem}{suffix}_tmp.mp4"
            try:
                make_horizontal_clip(item, h_tmp, duration, is_video)
                if h_tmp.exists():
                    if h_out.exists():
                        h_out.unlink()
                    h_tmp.rename(h_out)

                    # Validate output and save metadata
                    if validate_conformed_clip(h_out, 1920, 1080):
                        h_stat = h_out.stat()
                        if src_key not in manifest:
                            manifest[src_key] = {}
                        manifest[src_key]["fingerprint"] = src_fingerprint
                        manifest[src_key]["horizontal"] = {
                            "path": str(h_out),
                            "size": h_stat.st_size,
                            "mtime": h_stat.st_mtime
                        }
                        manifest_changed = True
                    else:
                        print(f"  ❌ Error: Horizontal conformed clip for {item.name} failed verification.", file=sys.stderr)
            except Exception as e:
                if h_tmp.exists():
                    h_tmp.unlink()
                raise e

    return manifest_changed


# ── Deity-Specific Conforming Interface ──────────────────────────────────────

def prepare_deity_assets(god_name: str):
    """Conforms assets only for the requested deity, using manifest caching."""
    god_dir = GODS_BASE / god_name
    if not god_dir.exists() or not god_dir.is_dir():
        print(f"⚠️ Deity folder {god_dir} does not exist. Skipping conforming.", file=sys.stderr)
        return

    manifest = load_asset_manifest()
    changed = process_god_folder(god_dir, manifest)
    if changed:
        save_asset_manifest(manifest)


# ── Main Entry Point ─────────────────────────────────────────────────────────

def main():
    if not GODS_BASE.exists():
        print(f"❌ FATAL: Source folder not found: {GODS_BASE}")
        exit(1)

    god_folders = [d for d in GODS_BASE.iterdir() if d.is_dir()]
    if not god_folders:
        print(f"❌ No god subfolders found inside {GODS_BASE}")
        exit(1)

    print(f"🙏 Found {len(god_folders)} god folder(s): {[d.name for d in god_folders]}")

    manifest = load_asset_manifest()
    manifest_changed = False

    for gf in sorted(god_folders):
        changed = process_god_folder(gf, manifest)
        if changed:
            manifest_changed = True

    if manifest_changed:
        save_asset_manifest(manifest)

    print("\n✅ All assets prepared successfully!")


if __name__ == "__main__":
    main()
