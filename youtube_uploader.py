"""
youtube_uploader.py — Isolated YouTube Upload Module
Provides functions to publish videos/Shorts using the YouTube Data API v3.
"""

import sys
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

def upload_to_youtube(
    creds: Credentials,
    video_path: Path,
    title: str,
    description: str,
    tags: list,
    privacy_status: str = "private",
    category_id: str = "22"  # "22" represents "People & Blogs"
) -> str:
    """
    Uploads a video to YouTube using the official YouTube Data API v3.
    Returns the generated YouTube Video ID on success.
    Raises exception on failure.
    """
    if not video_path.exists():
        raise FileNotFoundError(f"❌ Video file not found: {video_path}")

    # YouTube Data API constraints
    sanitized_title = title[:95]
    
    # Initialize Service
    try:
        youtube = build("youtube", "v3", credentials=creds)
    except Exception as e:
        raise RuntimeError(f"❌ Failed to build YouTube API service client: {e}")

    print(f"📤 Uploading video to YouTube...")
    print(f"   File:     {video_path.name} ({video_path.stat().st_size / 1024 / 1024:.2f} MB)")
    print(f"   Title:    {sanitized_title}")
    print(f"   Privacy:  {privacy_status.upper()}")
    print(f"   Category: {category_id}")

    try:
        body = {
            "snippet": {
                "title": sanitized_title,
                "description": description,
                "tags": tags,
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
                "selfDeclaredMadeForKids": False,
            }
        }

        # Resumable media upload
        media = MediaFileUpload(
            str(video_path),
            mimetype="video/mp4",
            chunksize=-1,
            resumable=True
        )

        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                print(f"   Upload progress: {int(status.progress() * 100)}%", end="\r")

        video_id = response.get("id")
        if not video_id:
            raise RuntimeError(f"❌ No video ID returned in YouTube response: {response}")

        print(f"\n✅ YouTube upload SUCCESS! ID: {video_id}")
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        print(f"   🔗 Video URL: {video_url}")
        return video_id

    except Exception as e:
        print(f"\n❌ YouTube upload API execution failed: {e}", file=sys.stderr)
        raise
