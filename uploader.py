import json
import subprocess
import sys
import time
import os
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
BASE_TAGS = ["horror stories", "scary stories", "creepypasta", "shorts", "scaryshorts"]

def build_description(hook: str, body: str) -> str:
    return (
        f"👁️ {hook}\n\n{body}\n\n"
        "Follow @Horrorstories-mb2L for daily doses of the unexplained.\n\n"
        "#horror #scarystories #creepypasta #shorts #mb2L"
    )

def refresh_credentials(token_path: str) -> Credentials:
    if not Path(token_path).exists():
        raise FileNotFoundError(f"Missing {token_path}.")
    creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    return creds

def main():
    print("🎬 Starting video generation...")
    
    # NEW LOGGING LOGIC: 
    # This allows logs to flow to the screen while still catching the final JSON
    process = subprocess.Popen(
        [sys.executable, "generate_short.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, # Merge error logs into standard logs
        text=True,
        bufsize=1
    )

    last_line = ""
    for line in iter(process.stdout.readline, ""):
        print(line, end="") # THIS PRINTS LIVE LOGS TO GITHUB
        if line.strip():
            last_line = line.strip()
    
    process.stdout.close()
    return_code = process.wait()

    if return_code != 0:
        print(f"❌ Generation failed with code {return_code}")
        sys.exit(1)

    # Parse the final JSON line
    try:
        item = json.loads(last_line)
    except Exception as e:
        print(f"❌ Failed to parse video data: {e}")
        sys.exit(1)

    video_path = item["video"]
    hook = item["title"]
    body = item.get("body", "")

    # Authenticate and Upload
    creds = refresh_credentials("token.json")
    youtube = build("youtube", "v3", credentials=creds)

    print(f"📤 Uploading: {hook}")
    
    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": hook[:95],
                "description": build_description(hook, body),
                "tags": BASE_TAGS,
                "categoryId": "24"
            },
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
        },
        media_body=MediaFileUpload(video_path, chunksize=-1, resumable=True)
    )

    response = request.execute()
    print(f"✅ SUCCESS! ID: {response['id']}")

if __name__ == "__main__":
    main()
