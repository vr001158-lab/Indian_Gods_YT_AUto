"""
uploader.py — God Channel: Generate → Upload to YouTube → Save to Google Drive
-------------------------------------------------------------------------------
Usage:
  python uploader.py --mode multi_image    # Short Type A
  python uploader.py --mode single_image   # Short Type B
  python uploader.py --mode long_video     # Long landscape video

Each run:
  1. Runs generate_short.py with the given mode
  2. Uploads the video to YouTube
  3. Saves a copy + metadata JSON to Google Drive folder
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
from googleapiclient.errors import HttpError

# ─────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
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


# ── YouTube Upload ────────────────────────────────────────────────────────────

def upload_to_youtube(youtube, item: dict) -> str:
    """Upload video to YouTube. Returns the video ID."""
    video_path = item["video"]
    title       = item["title"]
    description = item["description"]
    tags        = item["tags"]
    mode        = item["mode"]

    # Shorts: categoryId 22 (People & Blogs) works well; 24 is Entertainment
    # Long videos: 22
    category_id = "22"

    # YouTube requires #Shorts in title/description for shorts detection
    is_short = mode in ("multi_image", "single_image")
    if is_short and "#Shorts" not in title and "#shorts" not in title:
        title = title + " #Shorts"

    print(f"📤 Uploading to YouTube: {title[:60]}")

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title":       title[:95],
                "description": description,
                "tags":        tags,
                "categoryId":  category_id,
            },
            "status": {
                "privacyStatus":          "public",
                "selfDeclaredMadeForKids": False,
            }
        },
        media_body=MediaFileUpload(video_path, chunksize=-1, resumable=True)
    )

    response = request.execute()
    video_id = response["id"]
    print(f"✅ YouTube upload SUCCESS! ID: {video_id}")
    print(f"   🔗 https://www.youtube.com/shorts/{video_id}" if is_short
          else f"   🔗 https://www.youtube.com/watch?v={video_id}")
    return video_id


# ── Google Drive Upload ───────────────────────────────────────────────────────

def upload_to_drive(drive, item: dict, youtube_id: str):
    """Upload video + metadata JSON to Google Drive folder."""
    if not DRIVE_FOLDER_ID:
        print("⚠️  DRIVE_FOLDER_ID not set. Skipping Drive upload.")
        return

    timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
    god_name   = item.get("god_name", "unknown")
    mode       = item.get("mode", "video")
    video_path = Path(item["video"])

    drive_filename = f"{timestamp}_{god_name}_{mode}.mp4"

    print(f"☁️  Uploading to Google Drive: {drive_filename}")

    # Upload video file
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
    print(f"✅ Drive video uploaded: {uploaded['name']} (id={uploaded['id']})")

    # Upload metadata JSON alongside the video
    meta_content = {
        "youtube_id":   youtube_id,
        "youtube_url":  (f"https://www.youtube.com/shorts/{youtube_id}"
                         if mode in ("multi_image", "single_image")
                         else f"https://www.youtube.com/watch?v={youtube_id}"),
        "title":        item["title"],
        "description":  item["description"],
        "tags":         item["tags"],
        "god_name":     god_name,
        "mode":         mode,
        "generated_at": timestamp,
        "drive_file":   drive_filename,
    }

    meta_filename = f"{timestamp}_{god_name}_{mode}_metadata.json"
    meta_path = Path(f"/tmp/{meta_filename}")
    meta_path.write_text(json.dumps(meta_content, indent=2, ensure_ascii=False))

    drive.files().create(
        body={"name": meta_filename, "parents": [DRIVE_FOLDER_ID]},
        media_body=MediaFileUpload(str(meta_path), mimetype="application/json"),
        fields="id"
    ).execute()
    print(f"✅ Drive metadata uploaded: {meta_filename}")

    # Also save metadata locally for git commit
    local_meta = ARCHIVE_DIR / meta_filename
    shutil.copy(meta_path, local_meta)
    print(f"📁 Local archive: {local_meta}")


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
    creds   = refresh_credentials(TOKEN_PATH)
    youtube = build("youtube", "v3", credentials=creds)
    drive   = build("drive",   "v3", credentials=creds)

    # 3. Upload to YouTube
    video_id = upload_to_youtube(youtube, item)

    # 4. Save to Google Drive
    upload_to_drive(drive, item, video_id)

    print(f"\n🎉 All done! Mode={mode}, God={item.get('god_name')}, YT={video_id}")


if __name__ == "__main__":
    main()
