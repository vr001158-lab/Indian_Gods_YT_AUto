import sys
import io
import json
import time
import os
import subprocess
from pathlib import Path

# Force stdout/stderr to use UTF-8 to prevent console encoding crashes on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import google_auth_config
import youtube_uploader

# Config
GENERATE_SCRIPT = Path("generate_short.py")

# ─────────────────────────────────────────────────────────────────────────────
# Helper: Run the generator subprocess
# ─────────────────────────────────────────────────────────────────────────────
def run_generator(mode: str) -> dict:
    """Run generate_short.py as a subprocess and return its JSON result."""
    if not GENERATE_SCRIPT.exists():
        print(f"❌ CONFIGURATION FAILURE: {GENERATE_SCRIPT} not found.", file=sys.stderr)
        sys.exit(1)

    print(f"🎬 Launching generator (mode={mode})...", file=sys.stderr)

    try:
        proc = subprocess.run(
            [sys.executable, str(GENERATE_SCRIPT), "--mode", mode],
            capture_output=True,
            encoding="utf-8",
        )
    except Exception as e:
        print(f"❌ RENDER FAILURE: Failed to execute {GENERATE_SCRIPT}: {e}", file=sys.stderr)
        sys.exit(1)

    # Forward stderr (logs) to console
    if proc.stderr:
        print(proc.stderr.strip(), file=sys.stderr)

    if proc.returncode != 0:
        print(f"❌ RENDER FAILURE: generate_short.py failed with exit code {proc.returncode}", file=sys.stderr)
        sys.exit(1)

    # Parse JSON from stdout
    json_lines = [
        line for line in proc.stdout.splitlines()
        if line.strip().startswith("{")
    ]

    if not json_lines:
        print("❌ RENDER FAILURE: No JSON metadata returned by generator.", file=sys.stderr)
        print("   stdout was:", file=sys.stderr)
        print(proc.stdout, file=sys.stderr)
        sys.exit(1)

    try:
        return json.loads(json_lines[-1])
    except Exception as e:
        print(f"❌ RENDER FAILURE: Failed to parse generator JSON: {e}", file=sys.stderr)
        print(f"   Last line: {json_lines[-1]}", file=sys.stderr)
        sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# Helper: Validate video quality using ffprobe
# ─────────────────────────────────────────────────────────────────────────────
def validate_video_quality(video_path: Path, mode: str) -> float:
    """
    Checks if video file exists, is non-empty, readable by ffprobe,
    and has correct dimensions/codec. Returns duration.
    """
    print(f"🔍 Validating video quality for {video_path.name}...")
    if not video_path.exists():
        print(f"❌ RENDER FAILURE: Video file does not exist: {video_path}", file=sys.stderr)
        sys.exit(1)

    if video_path.stat().st_size == 0:
        print(f"❌ RENDER FAILURE: Assembled video file is empty (0 bytes).", file=sys.stderr)
        sys.exit(1)

    # Check via ffprobe
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=codec_name,pix_fmt,width,height,duration",
        "-of", "json",
        str(video_path)
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ RENDER FAILURE: FFprobe validation command failed: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ RENDER FAILURE: Failed to parse video metadata: {e}", file=sys.stderr)
        sys.exit(1)

    streams = data.get("streams", [])
    if not streams:
        print("❌ RENDER FAILURE: No video stream detected in conforming MP4.", file=sys.stderr)
        sys.exit(1)

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
            str(video_path)
        ]
        try:
            res_fmt = subprocess.run(cmd_fmt, capture_output=True, text=True, check=True)
            data_fmt = json.loads(res_fmt.stdout)
            duration = data_fmt.get("format", {}).get("duration")
        except Exception:
            pass

    if duration is not None:
        try:
            duration_val = float(duration)
        except ValueError:
            duration_val = 0.0
    else:
        duration_val = 0.0

    if duration_val <= 0:
        print(f"❌ RENDER FAILURE: Video has invalid duration: {duration}", file=sys.stderr)
        sys.exit(1)

    # Check specs
    if codec != "h264":
        print(f"❌ RENDER FAILURE: Video codec is '{codec}' (expected: 'h264').", file=sys.stderr)
        sys.exit(1)
    if pix_fmt not in ("yuv420p", "yuvj420p"):
        print(f"❌ RENDER FAILURE: Pixel format is '{pix_fmt}' (expected: 'yuv420p' or 'yuvj420p').", file=sys.stderr)
        sys.exit(1)

    # Dimension checks
    is_short = mode in ("multi_image", "single_image", "single_video")
    expected_w, expected_h = (720, 1280) if is_short else (1920, 1080)

    if width != expected_w or height != expected_h:
        print(
            f"❌ RENDER FAILURE: Unexpected resolution {width}x{height} (expected {expected_w}x{expected_h} for mode '{mode}').",
            file=sys.stderr
        )
        sys.exit(1)

    print(f"   ✅ Video conforms to YouTube guidelines ({width}x{height}, {codec}, {pix_fmt}, {duration_val:.2f}s)")
    return duration_val

# ─────────────────────────────────────────────────────────────────────────────
# Helper: Upload to Google Drive (optional)
# ─────────────────────────────────────────────────────────────────────────────
def upload_to_drive(creds, video_path: Path, filename: str, folder_id: str) -> str:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    try:
        service = build("drive", "v3", credentials=creds)
        file_metadata = {
            "name": filename,
            "parents": [folder_id],
        }
        media = MediaFileUpload(
            str(video_path),
            mimetype="video/mp4",
            resumable=True,
            chunksize=5 * 1024 * 1024,
        )

        print(f"☁️  Uploading to Google Drive: {filename}...")
        request = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, name, webViewLink",
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"   Drive progress: {int(status.progress() * 100)}%", end="\r")

        print(f"\n✅ Drive upload complete: {response['name']}")
        return response["id"]
    except Exception as e:
        print(f"❌ DRIVE FAILURE: Google Drive backup failed: {e}", file=sys.stderr)
        raise

# ─────────────────────────────────────────────────────────────────────────────
# Main Pipeline
# ─────────────────────────────────────────────────────────────────────────────
def main():
    # Simple manual argument parsing to match expected custom error formats
    mode = None
    privacy = "public"
    dry_run = False

    if "--mode" in sys.argv:
        try:
            idx = sys.argv.index("--mode")
            if idx + 1 < len(sys.argv):
                mode = sys.argv[idx + 1]
        except ValueError:
            pass

    if "--privacy" in sys.argv:
        try:
            idx = sys.argv.index("--privacy")
            if idx + 1 < len(sys.argv):
                privacy = sys.argv[idx + 1]
        except ValueError:
            pass

    if "--dry-run" in sys.argv:
        dry_run = True

    # Validate mode choice
    supported_modes = ["multi_image", "single_image", "single_video", "long_video"]
    if mode not in supported_modes:
        print(f"ERROR: Unsupported mode '{mode}'.", file=sys.stderr)
        print("Supported modes:", file=sys.stderr)
        for m in supported_modes:
            print(f"- {m}", file=sys.stderr)
        sys.exit(1)

    # Validate privacy choice
    if privacy not in ["private", "unlisted", "public"]:
        print(f"❌ CONFIGURATION FAILURE: Invalid privacy status '{privacy}'. Choose: private | unlisted | public", file=sys.stderr)
        sys.exit(1)

    print("==================================================")
    print("🌅 Divine Dharshanam Daily — Pipeline Execution")
    print(f"   Mode:    {mode.upper()}")
    print(f"   Privacy: {privacy.upper()}")
    print(f"   Dry Run: {dry_run}")
    print("==================================================")

    # 1. Config Validation
    # Google Drive integration is disabled/removed from the core production path.
    # This keeps OAuth scope minimal (youtube.upload only) and satisfies the ₹0 constraint.
    enable_drive = False
    if os.environ.get("ENABLE_GOOGLE_DRIVE", "").lower() == "true":
        print("ℹ️  Note: Google Drive backup is disabled/removed from the core production path. Skipping backup.", file=sys.stderr)


    # 2. Check Credentials (unless dry-run)
    creds = None
    if not dry_run:
        try:
            creds = google_auth_config.get_google_credentials()
        except Exception as e:
            print(f"❌ AUTH FAILURE: Google authentication credentials invalid or missing: {e}", file=sys.stderr)
            sys.exit(1)

    # 3. Generate Video
    result = run_generator(mode)
    video_path = Path(result["video"])
    god_name = result.get("god_name", "unknown")

    # 4. Conforming Quality Checks
    duration = validate_video_quality(video_path, mode)

    # 5. Publishing / Uploading
    youtube_id = None
    drive_file_id = None
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"{god_name}_{mode}_{timestamp}.mp4"

    if dry_run:
        print("🔬 [DRY RUN] Skipping YouTube and Google Drive publishing.")
    else:
        # YouTube Upload (Required in production)
        try:
            youtube_id = youtube_uploader.upload_to_youtube(
                creds=creds,
                video_path=video_path,
                title=result.get("title", "Divine Darshan"),
                description=result.get("description", ""),
                tags=result.get("tags", []),
                privacy_status=privacy
            )
        except Exception as e:
            print(f"❌ YOUTUBE FAILURE: YouTube upload failed: {e}", file=sys.stderr)
            sys.exit(1)

        # Google Drive Backup (Optional)
        if enable_drive:
            try:
                drive_file_id = upload_to_drive(creds, video_path, filename, drive_folder_id)
            except Exception as e:
                # Do NOT crash the pipeline if optional Drive backup fails
                print(f"⚠️ Drive backup failed: {e}. Skipping backup and continuing.", file=sys.stderr)
        else:
            print("ℹ️ Google Drive backup is disabled. Skipping backup.")

    # 6. Archive Metadata
    archive_dir = Path("uploaded_archive")
    archive_dir.mkdir(exist_ok=True)
    archive_filename = f"{timestamp}_{god_name}_{mode}_metadata.json"
    archive_path = archive_dir / archive_filename

    metadata = {
        "pipeline_version": "v2.1",
        "timestamp": timestamp,
        "video_file_name": filename,
        "deity": god_name,
        "mode": mode,
        "duration": round(duration, 2),
        "title": result.get("title", ""),
        "description": result.get("description", ""),
        "tags": result.get("tags", []),
        "youtube_id": youtube_id,
        "youtube_url": f"https://www.youtube.com/watch?v={youtube_id}" if youtube_id else None,
        "youtube_upload_status": "success" if youtube_id else ("skipped" if dry_run else "failed"),
        "drive_backup_status": "success" if drive_file_id else ("disabled" if not enable_drive else ("skipped" if dry_run else "failed")),
    }

    try:
        archive_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"📁 Metadata archived locally at: {archive_path}")
    except Exception as e:
        print(f"⚠️ Warning: Failed to write local archive log: {e}", file=sys.stderr)

    print("🎉 Pipeline executed successfully!")

if __name__ == "__main__":
    main()
