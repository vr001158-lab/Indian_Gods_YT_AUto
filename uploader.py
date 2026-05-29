"""
uploader.py — God Channel: Generate → Save to Google Drive Only
----------------------------------------------------------------
Usage:
  python uploader.py --mode multi_image    # Short Type A
  python uploader.py --mode single_image   # Short Type B
  python uploader.py --mode long_video     # Long landscape video

Each run:
  1. Runs generate_short.py with the given mode
  2. Saves the video file to Google Drive
  3. Creates a readable metadata text file alongside it
"""

import json
import subprocess
import sys
import os
import shutil
from pathlib import Path
from datetime import datetime

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

# ─────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
]
TOKEN_PATH = "token.json"

# Google Drive folder ID where generated videos are saved
# To find: open the folder in Drive → copy the ID from the URL
# e.g. https://drive.google.com/drive/folders/1AbC...XyZ  → "1AbC...XyZ"
DRIVE_FOLDER_ID = os.environ.get("DRIVE_FOLDER_ID", "")   # set in GitHub secrets

# Local archive of uploaded videos (also committed to repo)
ARCHIVE_DIR = Path("uploaded_archive")
ARCHIVE_DIR.mkdir(exist_ok=True)
# ─────────────────────────────────────────────


# ── Credentials ──────────────────────────────────────────────────────────────

def refresh_credentials(token_path: str) -> Credentials:
    if not Path(token_path).exists():
        raise FileNotFoundError(f"Missing {token_path}. Add it as a GitHub secret.")
    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    return creds


# ── Generate Video ────────────────────────────────────────────────────────────

def run_generator(mode: str) -> dict:
    """Run generate_short.py and return the parsed JSON result."""
    print(f"🎬 Generating video: mode={mode}")

    process = subprocess.Popen(
        [sys.executable, "generate_short.py", "--mode", mode],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        env={**os.environ, "PYTHONUNBUFFERED": "1"}
    )

    last_line = ""
    for line in iter(process.stdout.readline, ""):
        print(line, end="")   # live log output in GitHub Actions
        if line.strip():
            last_line = line.strip()

    process.stdout.close()
    rc = process.wait()

    if rc != 0:
        print(f"❌ Generator failed with code {rc}")
        sys.exit(1)

    try:
        return json.loads(last_line)
    except Exception as e:
        print(f"❌ Failed to parse generator output: {e}\nLast line: {last_line!r}")
        sys.exit(1)


# ── Google Drive Upload ───────────────────────────────────────────────────────

def upload_to_drive(drive, item: dict):
    """Upload video + metadata text file to Google Drive folder."""
    if not DRIVE_FOLDER_ID:
        print("❌ DRIVE_FOLDER_ID not set. Set it in GitHub Actions secrets.")
        sys.exit(1)

    timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
    god_name   = item.get("god_name", "unknown")
    mode       = item.get("mode", "video")
    video_path = Path(item["video"])

    drive_filename = f"{timestamp}_{god_name}_{mode}.mp4"

    print(f"\n☁️  Uploading to Google Drive...")
    print(f"   Video: {drive_filename}")

    # ─── Upload video file ────────────────────────────────────────────────────
    file_metadata = {
        "name":    drive_filename,
        "parents": [DRIVE_FOLDER_ID],
    }
    media = MediaFileUpload(str(video_path), mimetype="video/mp4", resumable=True)
    uploaded = drive.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, name"
    ).execute()
    print(f"   ✅ Video uploaded: {uploaded['name']}")

    # ─── Create readable metadata text file ────────────────────────────────────
    meta_text = _build_metadata_text(item, timestamp)
    meta_filename = f"{timestamp}_{god_name}_{mode}_info.txt"
    meta_path = Path(f"/tmp/{meta_filename}")
    meta_path.write_text(meta_text, encoding="utf-8")

    drive.files().create(
        body={"name": meta_filename, "parents": [DRIVE_FOLDER_ID]},
        media_body=MediaFileUpload(str(meta_path), mimetype="text/plain"),
        fields="id"
    ).execute()
    print(f"   ✅ Metadata saved: {meta_filename}")

    # ─── Save locally for git commit ───────────────────────────────────────────
    local_meta = ARCHIVE_DIR / meta_filename
    shutil.copy(meta_path, local_meta)
    print(f"   📁 Local archive: {local_meta}")


def _build_metadata_text(item: dict, timestamp: str) -> str:
    """
    Build a human-readable metadata text file.
    """
    god_name = item.get("god_name", "unknown").replace("_", " ").title()
    mode = item.get("mode", "unknown").replace("_", " ").title()
    title = item.get("title", "No Title")
    description = item.get("description", "No description")
    tags = item.get("tags", [])

    dt = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
    date_str = dt.strftime("%B %d, %Y")
    time_str = dt.strftime("%I:%M %p")

    # Build readable text
    text = []
    text.append("=" * 70)
    text.append("GOD CHANNEL — VIDEO METADATA")
    text.append("=" * 70)
    text.append("")
    text.append(f"Generated: {date_str} at {time_str}")
    text.append("")
    text.append("-" * 70)
    text.append("VIDEO DETAILS")
    text.append("-" * 70)
    text.append("")
    text.append(f"God Name:     {god_name}")
    text.append(f"Video Type:   {mode}")
    text.append(f"File Name:    {timestamp}_{item.get('god_name')}_{item.get('mode')}.mp4")
    text.append("")
    text.append("-" * 70)
    text.append("YOUTUBE INFORMATION")
    text.append("-" * 70)
    text.append("")
    text.append(f"Title:")
    text.append(f"  {title}")
    text.append("")
    text.append("Description:")
    for line in description.split("\n"):
        text.append(f"  {line}")
    text.append("")
    text.append("Tags / Hashtags:")
    text.append("")
    for i, tag in enumerate(tags, 1):
        if i % 3 == 0:
            text.append(f"  #{tag}")
        else:
            text.append(f"  #{tag}  ", end="")
    text.append("")
    text.append("")
    text.append("-" * 70)
    text.append("NOTES FOR UPLOADING")
    text.append("-" * 70)
    text.append("")
    text.append("• Video is ready to upload to YouTube")
    text.append("• Add music/background music if desired")
    text.append("• Copy the Title above into YouTube title field")
    text.append("• Copy the Description above into YouTube description field")
    text.append("• Copy the Tags into YouTube tags field")
    if mode == "short type a" or mode == "short type b":
        text.append("• Add #Shorts to the title for YouTube Shorts")
    text.append("• Set to Public when uploading")
    text.append("")
    text.append("=" * 70)

    return "\n".join(text)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    mode = "multi_image"
    if "--mode" in sys.argv:
        idx = sys.argv.index("--mode")
        if idx + 1 < len(sys.argv):
            mode = sys.argv[idx + 1]

    valid_modes = {"multi_image", "single_image", "long_video"}
    if mode not in valid_modes:
        print(f"❌ Invalid mode '{mode}'. Choose from: {valid_modes}")
        sys.exit(1)

    # 1. Generate the video
    item = run_generator(mode)

    # 2. Auth
    creds = refresh_credentials(TOKEN_PATH)
    drive = build("drive", "v3", credentials=creds)

    # 3. Save to Google Drive (no YouTube upload)
    upload_to_drive(drive, item)

    print(f"\n🎉 Done! Saved to Google Drive")
    print(f"   Mode: {item.get('mode')}")
    print(f"   God: {item.get('god_name')}")


if __name__ == "__main__":
    main()
