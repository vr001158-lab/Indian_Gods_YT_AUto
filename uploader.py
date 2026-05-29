"""
uploader.py — Google Drive Uploader for God Channel Videos
-----------------------------------------------------------
Reads the JSON output from generate_short.py and uploads the video
to a specified Google Drive folder.

Usage:
    python generate_short.py --mode multi_image | python uploader.py

Or with a saved JSON file:
    python uploader.py --json output/result.json

Requirements:
    pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib

Setup:
    1. Go to https://console.cloud.google.com/
    2. Create a project → Enable "Google Drive API"
    3. Create OAuth 2.0 credentials → Download as credentials.json
    4. Place credentials.json in the same folder as this script
    5. On first run, a browser window opens to authorize — token.json is saved for future runs.

Config:
    Set DRIVE_FOLDER_ID below to your target Google Drive folder ID.
    (Open the folder in Drive → copy the ID from the URL)
"""

import sys
import json
import os
from pathlib import Path

# ── Config ───────────────────────────────────────────────────────────────────

# Paste your Google Drive folder ID here (from the folder's URL)
# e.g. https://drive.google.com/drive/folders/1A2B3C4D5E6F  →  "1A2B3C4D5E6F"
DRIVE_FOLDER_ID = "YOUR_DRIVE_FOLDER_ID_HERE"

CREDENTIALS_FILE = Path("credentials.json")   # OAuth2 client secrets
TOKEN_FILE       = Path("token.json")          # Saved auth token (auto-created)
SCOPES           = ["https://www.googleapis.com/auth/drive.file"]

# ── Auth ─────────────────────────────────────────────────────────────────────

def get_drive_service():
    """Authenticate and return a Google Drive API service object."""
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
    """Upload a video file to Google Drive. Returns the file ID."""
    from googleapiclient.http import MediaFileUpload

    file_metadata = {
        "name": filename,
        "parents": [DRIVE_FOLDER_ID],
    }

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,        # resumable upload handles large files safely
        chunksize=5 * 1024 * 1024,  # 5 MB chunks
    )

    print(f"⬆️  Uploading: {filename} ({video_path.stat().st_size / 1024 / 1024:.1f} MB)", file=sys.stderr)

    request = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, name, webViewLink",
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"   Progress: {pct}%", file=sys.stderr, end="\r")

    print(f"\n✅ Uploaded: {response['name']}", file=sys.stderr)
    print(f"   Drive link: {response.get('webViewLink', 'N/A')}", file=sys.stderr)
    return response["id"]


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    # Read JSON from stdin (piped from generate_short.py) or --json flag
    if "--json" in sys.argv:
        idx = sys.argv.index("--json")
        result = json.loads(Path(sys.argv[idx + 1]).read_text())
    else:
        raw = sys.stdin.read().strip()
        # Take only the last line (generate_short.py may print status lines to stdout)
        last_line = [l for l in raw.splitlines() if l.strip().startswith("{")][-1]
        result = json.loads(last_line)

    video_path = Path(result["video"])
    god_name   = result.get("god_name", "unknown")
    mode       = result.get("mode", "video")
    title      = result.get("title", video_path.stem)

    if not video_path.exists():
        print(f"❌ Video file not found: {video_path}", file=sys.stderr)
        sys.exit(1)

    if DRIVE_FOLDER_ID == "YOUR_DRIVE_FOLDER_ID_HERE":
        print("❌ Please set DRIVE_FOLDER_ID in uploader.py before running.", file=sys.stderr)
        sys.exit(1)

    # Build a clean filename: god_mode_timestamp.mp4
    import time
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    safe_title = title[:50].replace(" ", "_").replace("/", "-").replace(":", "")
    filename = f"{god_name}_{mode}_{timestamp}.mp4"

    print(f"\n📁 Uploading to Google Drive...", file=sys.stderr)
    print(f"   God   : {god_name}", file=sys.stderr)
    print(f"   Mode  : {mode}", file=sys.stderr)
    print(f"   File  : {filename}", file=sys.stderr)

    service = get_drive_service()
    file_id = upload_to_drive(service, video_path, filename)

    # Output final result JSON (can be piped further if needed)
    output = {**result, "drive_file_id": file_id, "drive_filename": filename}
    print(json.dumps(output))


if __name__ == "__main__":
    main()
