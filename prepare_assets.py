import subprocess
from pathlib import Path
import os

# Updated to match your new Horror Channel folder structure
BASE = Path("assets/horror_stories")
RAW_CLIPS = BASE / "clips_raw"
OUT_CLIPS = BASE / "clips"

RAW_MUSIC = BASE / "music_raw"
OUT_MUSIC = BASE / "music"

# Create output directories if they don't exist
OUT_CLIPS.mkdir(parents=True, exist_ok=True)
OUT_MUSIC.mkdir(parents=True, exist_ok=True)

def run(cmd):
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg Error: {e.stderr}")
        raise e

def process_clips():
    print(f"🎬 Processing clips from {RAW_CLIPS}...")
    clips = list(RAW_CLIPS.glob("*.mp4"))
    if not clips:
        print(f"⚠️ No .mp4 files found in {RAW_CLIPS}")
        return

    for clip in clips:
        out = OUT_CLIPS / clip.name
        if out.exists():
            continue

        print(f"🔨 Converting: {clip.name}")
        # Standardize to Vertical 720x1280 for Shorts
        cmd = [
            "ffmpeg", "-y",
            "-i", str(clip),
            "-t", "10", # Takes 10 seconds of background
            "-vf", "scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-pix_fmt", "yuv420p",
            "-an", # Remove original audio
            str(out)
        ]
        run(cmd)

def process_music():
    print(f"🎵 Processing music from {RAW_MUSIC}...")
    # Changed from .m4a to .mp3 to match your actual downloads
    music_files = list(RAW_MUSIC.glob("*.mp3"))
    if not music_files:
        print(f"⚠️ No .mp3 files found in {RAW_MUSIC}")
        return

    for music in music_files:
        # Save as .aac for better compatibility with the video editor
        out = OUT_MUSIC / (music.stem + ".aac")
        if out.exists():
            continue

        print(f"🔊 Converting: {music.name}")
        cmd = [
            "ffmpeg", "-y",
            "-i", str(music),
            "-t", "60", # Ensure audio is long enough for the Short
            "-c:a", "aac",
            "-b:a", "128k",
            str(out)
        ]
        run(cmd)

if __name__ == "__main__":
    if not RAW_CLIPS.exists() or not RAW_MUSIC.exists():
        print(f"❌ FATAL ERROR: Source folders not found in {BASE}")
        exit(1)
        
    process_clips()
    process_music()
    print("✅ Assets prepared successfully for @Horrorstories-mb2L")
