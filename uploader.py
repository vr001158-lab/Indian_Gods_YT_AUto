"""
uploader.py — God Channel Video Generator + Google Drive Uploader
-----------------------------------------------------------------
Generates a video and uploads it directly to Google Drive.

Usage:
    python uploader.py --mode multi_image
    python uploader.py --mode single_image
    python uploader.py --mode long_video

Requirements:
    pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib

Setup:
    1. Go to https://console.cloud.google.com/
    2. Create a project → Enable "Google Drive API"
    3. Create OAuth 2.0 credentials → Download as credentials.json
    4. Place credentials.json in the same folder as this script
    5. On first run, a browser window opens to authorize — token.json saved for future runs.
"""

import sys
import json
import time
import subprocess
from pathlib import Path

# ── Config ───────────────────────────────────────────────────────────────────

DRIVE_FOLDER_ID  = "1wV6atZCtcrTQk4QMlTg1DV1vI7nYr-Ki"   # ← paste your Drive folder ID here
CREDENTIALS_FILE = Path("credentials.json")
TOKEN_FILE       = Path("token.json")
SCOPES           = ["https://www.googleapis.com/auth/drive.file"]

GENERATE_SCRIPT  = Path("generate_short.py")      # must be in same folder

# ── Auth ─────────────────────────────────────────────────────────────────────

def get_drive_service():
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                print("❌ credentials.json not found.", file=sys.stderr)
                print("   Download it from Google Cloud Console → APIs & Services → Credentials", file=sys.stderr)
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())

    return build("drive", "v3", credentials=creds)


# ── Upload ───────────────────────────────────────────────────────────────────

def upload_to_drive(service, video_path: Path, filename: str) -> str:
    from googleapiclient.http import MediaFileUpload

    file_metadata = {
        "name": filename,
        "parents": [DRIVE_FOLDER_ID],
    }
    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=5 * 1024 * 1024,
    )

    size_mb = video_path.stat().st_size / 1024 / 1024
    print(f"⬆️  Uploading: {filename} ({size_mb:.1f} MB)", file=sys.stderr)

    request = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, name, webViewLink",
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"   Progress: {int(status.progress() * 100)}%", file=sys.stderr, end="\r")

    print(f"\n✅ Upload complete: {response['name']}", file=sys.stderr)
    print(f"   Drive link: {response.get('webViewLink', 'N/A')}", file=sys.stderr)
    return response["id"]


# ── Generate video ────────────────────────────────────────────────────────────

def run_generator(mode: str) -> dict:
    """Run generate_short.py and return its JSON result."""
    if not GENERATE_SCRIPT.exists():
        print(f"❌ {GENERATE_SCRIPT} not found. Place it in the same folder.", file=sys.stderr)
        sys.exit(1)

    print(f"🎬 Generating video (mode={mode})...", file=sys.stderr)

    proc = subprocess.run(
        [sys.executable, str(GENERATE_SCRIPT), "--mode", mode],
        capture_output=True,
        text=True,
    )

    # Forward generator's stderr (progress messages) to our stderr
    if proc.stderr:
        print(proc.stderr.strip(), file=sys.stderr)

    if proc.returncode != 0:
        print(f"❌ generate_short.py failed (exit {proc.returncode})", file=sys.stderr)
        sys.exit(1)

    # Find the JSON line in stdout
    json_lines = [
        line for line in proc.stdout.splitlines()
        if line.strip().startswith("{")
    ]

    if not json_lines:
        print("❌ No JSON output from generate_short.py", file=sys.stderr)
        print("   stdout was:", file=sys.stderr)
        print(proc.stdout, file=sys.stderr)
        sys.exit(1)

    return json.loads(json_lines[-1])


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    # Parse --mode argument
    mode = "multi_image"
    if "--mode" in sys.argv:
        idx = sys.argv.index("--mode")
        if idx + 1 < len(sys.argv):
            mode = sys.argv[idx + 1]
        else:
            print("❌ --mode requires a value: multi_image | single_image | long_video", file=sys.stderr)
            sys.exit(1)

    valid_modes = {"multi_image", "single_image", "long_video"}
    if mode not in valid_modes:
        print(f"❌ Unknown mode '{mode}'. Choose: {' | '.join(valid_modes)}", file=sys.stderr)
        sys.exit(1)

    if DRIVE_FOLDER_ID == "YOUR_DRIVE_FOLDER_ID_HERE":
        print("❌ Please set DRIVE_FOLDER_ID in uploader.py before running.", file=sys.stderr)
        sys.exit(1)

    # Step 1: Generate the video
    result = run_generator(mode)

    video_path = Path(result["video"])
    god_name   = result.get("god_name", "unknown")

    if not video_path.exists():
        print(f"❌ Video file not found: {video_path}", file=sys.stderr)
        sys.exit(1)

    # Step 2: Build filename
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename  = f"{god_name}_{mode}_{timestamp}.mp4"

    print(f"\n📁 Uploading to Google Drive...", file=sys.stderr)
    print(f"   God  : {god_name}", file=sys.stderr)
    print(f"   Mode : {mode}", file=sys.stderr)
    print(f"   File : {filename}", file=sys.stderr)

    # Step 3: Upload
    service = get_drive_service()
    file_id = upload_to_drive(service, video_path, filename)

    # Output final JSON
    output = {**result, "drive_file_id": file_id, "drive_filename": filename}
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
