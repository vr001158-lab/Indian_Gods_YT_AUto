import os
import sys
import json
import time
from pathlib import Path

# Ensure UTF-8 stdout
import io
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add workspace to path
sys.path.insert(0, os.getcwd())
import google_auth_config
import youtube_uploader
import generate_short

def run_upload_test():
    print("🚀 Starting Controlled Private YouTube Upload Test...\n")

    # 1. Verification of credentials
    token_path = Path("token.json")
    secret_path = Path("client_secret.json")
    if not token_path.exists() or not secret_path.exists():
        print("❌ STOP: Required credential files (token.json or client_secret.json) are missing.", file=sys.stderr)
        print("   Please ensure TOKEN_JSON and CLIENT_SECRET_JSON GitHub secrets are mapped correctly.", file=sys.stderr)
        sys.exit(1)

    # 2. Get credentials
    try:
        creds = google_auth_config.get_google_credentials()
    except Exception as e:
        print(f"❌ AUTH FAILURE: Failed to load Google credentials: {e}", file=sys.stderr)
        sys.exit(1)

    # 3. Generate one small test video using multi_image mode
    print("🎬 Generating a small test video...")
    try:
        result = generate_short.generate_multi_image_short()
        video_path = Path(result["video"])
        god_name = result.get("god_name", "unknown")
        print(f"   Generated video: {video_path} for god {god_name} ({video_path.stat().st_size / 1024 / 1024:.2f} MB)")
    except Exception as e:
        print(f"❌ GENERATOR FAILURE: Failed to generate test video: {e}", file=sys.stderr)
        sys.exit(1)

    # 4. Set custom metadata (as requested)
    test_title = "[PRIVATE TEST] Divine Dharshanam Daily Pipeline"
    test_desc = "Private validation upload for the Divine Dharshanam Daily automated production pipeline."
    test_tags = ["test", "divine dharshanam daily", "automation"]
    
    # 5. Run YouTube upload (explicitly private!)
    video_id = None
    try:
        video_id = youtube_uploader.upload_to_youtube(
            creds=creds,
            video_path=video_path,
            title=test_title,
            description=test_desc,
            tags=test_tags,
            privacy_status="private"
        )
    except Exception as e:
        print(f"❌ YOUTUBE FAILURE: YouTube upload failed: {e}", file=sys.stderr)
        sys.exit(1)

    # 6. Archive Metadata
    archive_dir = Path("uploaded_archive")
    archive_dir.mkdir(exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    archive_filename = f"{timestamp}_{god_name}_youtube_test_metadata.json"
    archive_path = archive_dir / archive_filename

    metadata = {
        "pipeline_version": "v2.1-test",
        "timestamp": timestamp,
        "video_file_name": video_path.name,
        "deity": god_name,
        "mode": "multi_image",
        "duration": round(result.get("duration_s", 0), 2),
        "title": test_title,
        "description": test_desc,
        "tags": test_tags,
        "youtube_id": video_id,
        "youtube_url": f"https://www.youtube.com/watch?v={video_id}",
        "youtube_upload_status": "success",
        "privacy_status": "private",
        "drive_backup_status": "disabled"
    }

    try:
        archive_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"📁 Metadata archived locally at: {archive_path}")
    except Exception as e:
        print(f"⚠️ Warning: Failed to write local archive log: {e}", file=sys.stderr)

    print("\n🎉 Controlled Private YouTube Upload Test completed successfully!")
    print(f"   YouTube Video ID: {video_id}")
    print("   Privacy Status:   PRIVATE")

if __name__ == "__main__":
    run_upload_test()
