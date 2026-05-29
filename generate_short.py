"""
generate_short.py — God Channel Video Generator
------------------------------------------------
Generates one of three video types based on --mode argument:

  --mode multi_image   → Short Type A: multiple images from one randomly chosen
                         god folder, each clip 2–4s, total 30–55s. (vertical)

  --mode single_image  → Short Type B: one single image from a randomly chosen
                         god folder, duration 30–55s, with Ken Burns + effects.
                         (vertical)

  --mode long_video    → Long video: all images from one randomly chosen god folder,
                         landscape 1920x1080, under 4 minutes.

No voiceover. No text overlays. Random duration between 30–55 seconds (Shorts modes).

Output: prints a single JSON line on stdout with keys:
  video, title, description, tags, god_name, mode
"""

import sys
import json
import random
import subprocess
from pathlib import Path

# ─────────────────────────────────────────────
PROC_BASE  = Path("assets/gods_processed")
OUTPUT     = Path("output")
OUTPUT.mkdir(exist_ok=True)

# Manifest to track which folder was used last (to rotate fairly)
MANIFEST   = Path("manifest.json")
# ─────────────────────────────────────────────


# ── Metadata templates ───────────────────────────────────────────────────────

GOD_META = {
    "lord_vishnu": {
        "display": "Lord Vishnu",
        "titles_multi":  ["🙏 Beautiful Images of Lord Vishnu | Jai Vishnu", "🌸 Lord Vishnu Divine Darshan #Shorts"],
        "titles_single": ["🌺 Lord Vishnu Blessings | Rare Divine Image #Shorts", "💙 Jai Vishnu Ji | God Blessings #Shorts"],
        "titles_long":   ["🙏 Lord Vishnu Divine Gallery | Peaceful Darshan | Jai Vishnu"],
        "description": (
            "🙏 Jai Shri Vishnu! Relax and receive the blessings of Lord Vishnu.\n\n"
            "Watch these beautiful divine images and feel peace in your heart.\n\n"
            "✨ Share this with your family and loved ones.\n"
            "🔔 Subscribe for daily God blessings and devotional content.\n\n"
            "#LordVishnu #JaiVishnu #DivineImages #GodBlessings #Devotional #Shorts"
        ),
        "tags": ["lord vishnu", "vishnu blessings", "jai vishnu", "god images", "divine darshan",
                 "devotional shorts", "vishnu photos", "hindu god", "peace blessings"],
    },
    "shiva": {
        "display": "Lord Shiva",
        "titles_multi":  ["🙏 Beautiful Images of Lord Shiva | Har Har Mahadev", "🔱 Mahadev Divine Darshan #Shorts"],
        "titles_single": ["🔱 Lord Shiva Blessings | Rare Divine Image #Shorts", "🌙 Har Har Mahadev | God Blessings #Shorts"],
        "titles_long":   ["🙏 Lord Shiva Divine Gallery | Mahadev Darshan | Har Har Mahadev"],
        "description": (
            "🔱 Har Har Mahadev! Receive the divine blessings of Lord Shiva.\n\n"
            "These beautiful images of Mahadev will bring peace and strength to your life.\n\n"
            "✨ Share this blessings with your family.\n"
            "🔔 Subscribe for daily devotional content.\n\n"
            "#LordShiva #Mahadev #HarHarMahadev #ShivaBlessings #Devotional #Shorts"
        ),
        "tags": ["lord shiva", "mahadev", "har har mahadev", "shiva blessings", "divine images",
                 "devotional shorts", "shiva photos", "hindu god", "om namah shivaya"],
    },
    "hanuman": {
        "display": "Lord Hanuman",
        "titles_multi":  ["🙏 Beautiful Images of Lord Hanuman | Jai Bajrangbali", "🧡 Hanuman Ji Divine Darshan #Shorts"],
        "titles_single": ["🧡 Lord Hanuman Blessings | Rare Divine Image #Shorts", "🙏 Jai Bajrangbali | God Blessings #Shorts"],
        "titles_long":   ["🙏 Lord Hanuman Divine Gallery | Bajrangbali Darshan | Jai Hanuman"],
        "description": (
            "🙏 Jai Bajrangbali! May Lord Hanuman protect you and your family.\n\n"
            "These powerful divine images of Hanuman Ji will give you strength and courage.\n\n"
            "✨ Share this with your loved ones for blessings.\n"
            "🔔 Subscribe for daily devotional videos.\n\n"
            "#LordHanuman #Bajrangbali #JaiBajrangbali #HanumanBlessings #Devotional #Shorts"
        ),
        "tags": ["lord hanuman", "bajrangbali", "jai bajrangbali", "hanuman blessings", "divine images",
                 "devotional shorts", "hanuman photos", "hindu god", "jai hanuman"],
    },
    "kali_amma": {
        "display": "Maa Kali",
        "titles_multi":  ["🙏 Beautiful Images of Maa Kali | Jai Maa Kali", "⚡ Maa Kali Divine Darshan #Shorts"],
        "titles_single": ["⚡ Maa Kali Blessings | Rare Divine Image #Shorts", "🙏 Jai Maa Kali | Divine Blessings #Shorts"],
        "titles_long":   ["🙏 Maa Kali Divine Gallery | Devi Darshan | Jai Maa Kali"],
        "description": (
            "🙏 Jai Maa Kali! Receive the powerful blessings of Maa Kali Devi.\n\n"
            "These divine images of the Mother Goddess will protect you and your family.\n\n"
            "✨ Share this blessing with your loved ones.\n"
            "🔔 Subscribe for daily devotional content.\n\n"
            "#MaaKali #KaliMaa #JaiMaaKali #KaliBlessings #Devotional #Shorts"
        ),
        "tags": ["maa kali", "kali maa", "jai maa kali", "kali blessings", "divine images",
                 "devotional shorts", "devi photos", "hindu goddess", "shakti"],
    },
    "seetha": {
        "display": "Mata Sita",
        "titles_multi":  ["🙏 Beautiful Images of Mata Sita | Jai Siya Ram", "🌸 Sita Mata Divine Darshan #Shorts"],
        "titles_single": ["🌸 Mata Sita Blessings | Rare Divine Image #Shorts", "🙏 Jai Siya Ram | Divine Blessings #Shorts"],
        "titles_long":   ["🙏 Mata Sita Divine Gallery | Sita Devi Darshan | Jai Siya Ram"],
        "description": (
            "🙏 Jai Siya Ram! Receive the divine blessings of Mata Sita.\n\n"
            "These beautiful images of Sita Mata will bring peace and happiness to your home.\n\n"
            "✨ Share this with your family for blessings.\n"
            "🔔 Subscribe for daily devotional videos.\n\n"
            "#MataSita #SitaMata #JaiSiyaRam #SitaBlessings #Devotional #Shorts"
        ),
        "tags": ["mata sita", "sita mata", "jai siya ram", "sita blessings", "divine images",
                 "devotional shorts", "sita photos", "hindu goddess", "ramayan"],
    },
}

# Fallback metadata for any god folder not listed above
def get_meta(god_name: str) -> dict:
    if god_name in GOD_META:
        return GOD_META[god_name]
    display = god_name.replace("_", " ").title()
    return {
        "display": display,
        "titles_multi":  [f"🙏 Beautiful Images of {display} | Divine Darshan #Shorts"],
        "titles_single": [f"🙏 {display} Blessings | Divine Image #Shorts"],
        "titles_long":   [f"🙏 {display} Divine Gallery | Devotional Video"],
        "description": (
            f"🙏 Receive the divine blessings of {display}.\n\n"
            "These beautiful images will bring peace and happiness to your life.\n\n"
            "✨ Share with your family.\n"
            "🔔 Subscribe for daily devotional content.\n\n"
            f"#{display.replace(' ','')} #GodBlessings #Devotional"
        ),
        "tags": [god_name.replace("_", " "), "god blessings", "divine images", "devotional", "hindu god"],
    }


# ── Manifest helpers ─────────────────────────────────────────────────────────

def load_manifest() -> dict:
    if MANIFEST.exists():
        try:
            return json.loads(MANIFEST.read_text())
        except Exception:
            pass
    return {}


def save_manifest(data: dict):
    MANIFEST.write_text(json.dumps(data, indent=2))


def pick_god_folder(mode: str) -> Path:
    """
    Picks a god folder, rotating so no folder repeats until all have been used.
    Each mode (multi_image, single_image, long_video) tracks its own rotation.
    """
    available = [d for d in PROC_BASE.iterdir() if d.is_dir()]
    if not available:
        print("❌ No processed god folders found. Run prepare_assets.py first.", file=sys.stderr)
        sys.exit(1)

    manifest = load_manifest()
    key = f"used_{mode}"
    used = set(manifest.get(key, []))

    remaining = [d for d in available if d.name not in used]
    if not remaining:
        # Reset rotation
        used = set()
        remaining = available

    chosen = random.choice(remaining)
    used.add(chosen.name)
    manifest[key] = list(used)
    save_manifest(manifest)

    return chosen


# ── ffprobe ──────────────────────────────────────────────────────────────────

def get_duration(file: Path) -> float:
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1", str(file)]
    return float(subprocess.check_output(cmd).decode().strip())


# ── Random target duration for Shorts ────────────────────────────────────────

def random_short_duration() -> float:
    """Pick a random duration between 30 and 55 seconds."""
    return round(random.uniform(30.0, 55.0), 2)


# ─────────────────────────────────────────────────────────────────────────────
# VIDEO TYPE A — Multi-image Short (vertical, 30–55s, no voice, no text)
# ─────────────────────────────────────────────────────────────────────────────

def generate_multi_image_short() -> dict:
    """Pick one god folder, take multiple images as clips, concat → Short."""
    god_dir = pick_god_folder("multi_image")
    vert_dir = god_dir / "vertical"
    clips = sorted(vert_dir.glob("*.mp4"))

    if not clips:
        print(f"❌ No vertical clips in {vert_dir}", file=sys.stderr)
        sys.exit(1)

    meta = get_meta(god_dir.name)
    title = random.choice(meta["titles_multi"])
    target_dur = random_short_duration()

    # Select clips to fill target duration
    selected = []
    total_dur = 0.0
    shuffled = list(clips)
    random.shuffle(shuffled)

    for clip in shuffled:
        d = get_duration(clip)
        if total_dur + d > target_dur:
            # Add a trimmed version of this clip to exactly hit target_dur
            remaining = target_dur - total_dur
            if remaining >= 1.0:
                selected.append((clip, remaining))
                total_dur += remaining
            break
        selected.append((clip, d))
        total_dur += d
        if total_dur >= target_dur:
            break

    # Need at least 1 clip
    if not selected:
        clip = shuffled[0]
        selected = [(clip, min(get_duration(clip), target_dur))]
        total_dur = selected[0][1]

    print(f"🙏 God: {meta['display']} | {len(selected)} clips | {total_dur:.1f}s", file=sys.stderr)

    out_file = OUTPUT / "short_multi.mp4"
    _build_concat_vertical(selected, target_dur, out_file)

    return {
        "video":       str(out_file),
        "title":       title[:95],
        "description": meta["description"],
        "tags":        meta["tags"],
        "god_name":    god_dir.name,
        "mode":        "multi_image",
    }


def _build_concat_vertical(selected: list, duration: float, out_file: Path):
    """Concat clips, no audio, no text, output vertical Short."""
    n = len(selected)

    cmd = ["ffmpeg", "-y"]

    if n == 1:
        # Single clip, just trim it
        clip, dur = selected[0]
        cmd += [
            "-i", str(clip),
            "-t", f"{dur:.2f}",
            "-an",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
            "-r", "30",
            str(out_file)
        ]
        subprocess.run(cmd, check=True)
        return

    # Build filter for trim + concat
    for clip, dur in selected:
        cmd += ["-i", str(clip)]

    fc = ""
    for i, (clip, dur) in enumerate(selected):
        fc += f"[{i}:v]trim=duration={dur:.2f},setpts=PTS-STARTPTS[v{i}];"
    fc += "".join(f"[v{i}]" for i in range(n))
    fc += f"concat=n={n}:v=1:a=0[vout]"

    cmd += [
        "-filter_complex", fc,
        "-map", "[vout]",
        "-an",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
        "-t", f"{duration:.2f}",
        "-r", "30",
        str(out_file)
    ]
    subprocess.run(cmd, check=True)


# ─────────────────────────────────────────────────────────────────────────────
# VIDEO TYPE B — Single-image Short (vertical, 30–55s, Ken Burns, no voice, no text)
# ─────────────────────────────────────────────────────────────────────────────

def generate_single_image_short() -> dict:
    """Pick one god folder, pick one random clip, make 30–55s Short with Ken Burns."""
    god_dir = pick_god_folder("single_image")
    vert_dir = god_dir / "vertical"
    clips = sorted(vert_dir.glob("*.mp4"))

    if not clips:
        print(f"❌ No vertical clips in {vert_dir}", file=sys.stderr)
        sys.exit(1)

    chosen_clip = random.choice(clips)
    meta = get_meta(god_dir.name)
    title = random.choice(meta["titles_single"])
    target_dur = random_short_duration()

    print(f"🙏 God: {meta['display']} | Single image | {target_dur:.1f}s", file=sys.stderr)

    out_file = OUTPUT / "short_single.mp4"
    _build_single_image_vertical(chosen_clip, target_dur, out_file)

    return {
        "video":       str(out_file),
        "title":       title[:95],
        "description": meta["description"],
        "tags":        meta["tags"],
        "god_name":    god_dir.name,
        "mode":        "single_image",
    }


def _build_single_image_vertical(clip: Path, duration: float, out_file: Path):
    """Single image with Ken Burns zoom + fade in/out. No audio, no text."""
    # Ken Burns: slow zoom from 1.05x to 1.15x over full duration
    zoom_effect = (
        f"scale=8000:-1,zoompan="
        f"z='min(zoom+0.0003,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={int(duration * 30)}:s=720x1280:fps=30"
    )
    fade_in  = "fade=t=in:st=0:d=1.5"
    fade_out = f"fade=t=out:st={duration - 1.5:.2f}:d=1.5"

    vf = f"{zoom_effect},{fade_in},{fade_out}"

    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", str(clip),
        "-vf", vf,
        "-an",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
        "-t", f"{duration:.2f}",
        "-r", "30",
        str(out_file)
    ]
    subprocess.run(cmd, check=True)


# ─────────────────────────────────────────────────────────────────────────────
# VIDEO TYPE C — Long Landscape Video (<4 min, 1920x1080, no voice, no text)
# ─────────────────────────────────────────────────────────────────────────────

def generate_long_video() -> dict:
    """All images from one god folder → landscape video <4 min."""
    god_dir = pick_god_folder("long_video")
    horiz_dir = god_dir / "horizontal"
    clips = sorted(horiz_dir.glob("*.mp4"))

    if not clips:
        print(f"❌ No horizontal clips in {horiz_dir}", file=sys.stderr)
        sys.exit(1)

    meta = get_meta(god_dir.name)
    title = random.choice(meta["titles_long"])

    # Collect clips up to 3 min 40 sec
    selected = []
    total_dur = 0.0
    shuffled = list(clips)
    random.shuffle(shuffled)

    for clip in shuffled:
        d = get_duration(clip)
        if total_dur + d > 218:   # 3min 38s cap
            break
        selected.append((clip, d))
        total_dur += d

    if not selected:
        clip = shuffled[0]
        d = min(get_duration(clip), 218.0)
        selected = [(clip, d)]
        total_dur = d

    print(f"🙏 God: {meta['display']} | Long video | {len(selected)} clips | {total_dur:.1f}s", file=sys.stderr)

    out_file = OUTPUT / "long_video.mp4"
    _build_long_landscape(selected, total_dur, out_file)

    return {
        "video":       str(out_file),
        "title":       title[:95],
        "description": meta["description"],
        "tags":        meta["tags"],
        "god_name":    god_dir.name,
        "mode":        "long_video",
    }


def _build_long_landscape(selected: list, duration: float, out_file: Path):
    """Concat horizontal clips, fade in/out, no audio, no text."""
    n = len(selected)

    cmd = ["ffmpeg", "-y"]
    for clip, _ in selected:
        cmd += ["-i", str(clip)]

    if n == 1:
        clip, dur = selected[0]
        vf = f"fade=t=in:st=0:d=2,fade=t=out:st={dur - 2:.1f}:d=2"
        cmd += [
            "-vf", vf,
            "-an",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
            "-t", f"{dur:.2f}",
            "-r", "30",
            str(out_file)
        ]
        subprocess.run(cmd, check=True)
        return

    fc = ""
    for i, (clip, dur) in enumerate(selected):
        fc += f"[{i}:v]trim=duration={dur:.2f},setpts=PTS-STARTPTS[v{i}];"
    fc += "".join(f"[v{i}]" for i in range(n))
    fc += f"concat=n={n}:v=1:a=0[vraw];"
    fc += f"[vraw]fade=t=in:st=0:d=2,fade=t=out:st={duration - 2:.1f}:d=2[vout]"

    cmd += [
        "-filter_complex", fc,
        "-map", "[vout]",
        "-an",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
        "-t", f"{duration:.2f}",
        "-r", "30",
        str(out_file)
    ]
    subprocess.run(cmd, check=True)


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main():
    mode = "multi_image"
    if "--mode" in sys.argv:
        idx = sys.argv.index("--mode")
        if idx + 1 < len(sys.argv):
            mode = sys.argv[idx + 1]

    if mode == "multi_image":
        result = generate_multi_image_short()
    elif mode == "single_image":
        result = generate_single_image_short()
    elif mode == "long_video":
        result = generate_long_video()
    else:
        print(f"❌ Unknown mode: {mode}. Use multi_image | single_image | long_video", file=sys.stderr)
        sys.exit(1)

    # Print JSON result as last line (parsed by uploader.py)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
