"""
generate_short.py — God Channel Video Generator
------------------------------------------------
Generates one of three video types based on --mode argument:

  --mode multi_image   → Short Type A: multiple images from one randomly chosen
                         god folder, each clip 2–4s, total under 60s. (vertical)

  --mode single_image  → Short Type B: one single image from a randomly chosen
                         god folder, duration 30–55s, with Ken Burns + effects.
                         (vertical)

  --mode long_video    → Long video: all images from one randomly chosen god folder,
                         landscape 1920x1080, under 4 minutes.

Output: prints a single JSON line on stdout with keys:
  video, title, description, tags, god_name, mode
"""

import sys
import json
import random
import subprocess
import asyncio
from pathlib import Path

# ─────────────────────────────────────────────
PROC_BASE  = Path("assets/gods_processed")
OUTPUT     = Path("output")
OUTPUT.mkdir(exist_ok=True)

VOICE      = "en-IN-PrabhatNeural"   # warm Indian English voice for elderly audience
FONT_PATH  = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# Channel branding
CHANNEL_TAG = "@GodsBlessings"       # ← update to your actual channel handle

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


# ── TTS ──────────────────────────────────────────────────────────────────────

async def _tts(text: str, out_path: Path):
    import edge_tts
    comm = edge_tts.Communicate(text, VOICE)
    await comm.save(str(out_path))


def tts(text: str, out_path: Path):
    asyncio.run(_tts(text, out_path))


# ─────────────────────────────────────────────────────────────────────────────
# VIDEO TYPE A — Multi-image Short (vertical, <60s)
# ─────────────────────────────────────────────────────────────────────────────

def generate_multi_image_short() -> dict:
    """Pick one god folder, take multiple images as 2–4s clips, concat → Short."""
    god_dir = pick_god_folder("multi_image")
    vert_dir = god_dir / "vertical"
    clips = sorted(vert_dir.glob("*.mp4"))

    if not clips:
        print(f"❌ No vertical clips in {vert_dir}", file=sys.stderr)
        sys.exit(1)

    meta = get_meta(god_dir.name)
    title = random.choice(meta["titles_multi"])

    # Greet and describe
    vo_text = (
        f"Jai {meta['display']}! "
        
    )
    vo_path = OUTPUT / "vo_multi.mp3"
    tts(vo_text, vo_path)
    vo_duration = get_duration(vo_path)

    # How many clips fit under 58 seconds?
    selected = []
    total_dur = 0.0
    shuffled = list(clips)
    random.shuffle(shuffled)

    for clip in shuffled:
        d = get_duration(clip)
        if total_dur + d > 58:
            break
        selected.append((clip, d))
        total_dur += d
        if total_dur >= 50:
            break

    # Need at least 2 clips
    if len(selected) < 2:
        selected = [(c, get_duration(c)) for c in shuffled[:4]]

    print(f"🙏 God: {meta['display']} | {len(selected)} clips | {total_dur:.1f}s", file=sys.stderr)

    # Build ffmpeg command
    out_file = OUTPUT / "short_multi.mp4"
    _build_concat_vertical(selected, vo_path, vo_duration, title, out_file)

    return {
        "video":       str(out_file),
        "title":       title[:95],
        "description": meta["description"],
        "tags":        meta["tags"],
        "god_name":    god_dir.name,
        "mode":        "multi_image",
    }


def _build_concat_vertical(selected: list, vo_path: Path, vo_duration: float,
                            title: str, out_file: Path):
    """Concat clips, overlay TTS audio and on-screen text, output vertical Short."""
    n = len(selected)

    cmd = ["ffmpeg", "-y"]
    for clip, _ in selected:
        cmd += ["-i", str(clip)]
    cmd += ["-i", str(vo_path)]

    # Video filter: concat + text overlays
    fc = ""
    for i in range(n):
        fc += f"[{i}:v]setpts=PTS-STARTPTS[v{i}];"
    fc += "".join(f"[v{i}]" for i in range(n))
    fc += f"concat=n={n}:v=1:a=0[vraw];"

    clean_title = title.replace("'", "").replace(":", "").replace("#", "").upper()
    if len(clean_title) > 40:
        clean_title = clean_title[:40]

    sub_start = max(0, vo_duration - 4)

    overlays = (
        f"drawtext=fontfile='{FONT_PATH}':text='{clean_title}':fontsize=38:"
        f"fontcolor=yellow:borderw=4:bordercolor=black:"
        f"x=(w-text_w)/2:y=h*0.15:enable='between(t,0,3)',"
        f"drawtext=fontfile='{FONT_PATH}':text='🙏 JAI {clean_title[:20]}':fontsize=34:"
        f"fontcolor=white:borderw=3:bordercolor=black:"
        f"x=(w-text_w)/2:y=h*0.75:enable='between(t,3,{sub_start:.1f})',"
        f"drawtext=fontfile='{FONT_PATH}':text='SUBSCRIBE FOR DAILY BLESSINGS':fontsize=36:"
        f"fontcolor=red:borderw=4:bordercolor=white:"
        f"x=(w-text_w)/2:y=(h-text_h)/2:enable='gt(t,{sub_start:.1f})',"
        f"drawtext=fontfile='{FONT_PATH}':text='{CHANNEL_TAG}':fontsize=22:"
        f"fontcolor=white@0.5:x=w-tw-16:y=16"
    )

    fc += f"[vraw]{overlays}[vout];"

    # Audio: voiceover only (music added manually)
    fc += f"[{n}:a]volume=2.2[aout]"

    cmd += [
        "-filter_complex", fc,
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "22",
        "-c:a", "aac", "-b:a", "192k",
        "-t", f"{vo_duration:.2f}",
        "-r", "30",
        str(out_file)
    ]
    subprocess.run(cmd, check=True)


# ─────────────────────────────────────────────────────────────────────────────
# VIDEO TYPE B — Single-image Short (vertical, 30–55s, with effects)
# ─────────────────────────────────────────────────────────────────────────────

def generate_single_image_short() -> dict:
    """Pick one god folder, pick one random image, make 30–55s Short with effects."""
    god_dir = pick_god_folder("single_image")
    vert_dir = god_dir / "vertical"
    clips = sorted(vert_dir.glob("*.mp4"))

    if not clips:
        print(f"❌ No vertical clips in {vert_dir}", file=sys.stderr)
        sys.exit(1)

    chosen_clip = random.choice(clips)
    meta = get_meta(god_dir.name)
    title = random.choice(meta["titles_single"])

    # Longer, devotional voiceover for single-image format
    vo_text = (
        f"Jai {meta['display']}! "
        "Please take a moment to look at this beautiful divine image and offer your prayers. "
        "May the blessings of the Almighty always be with you, your family, and all your loved ones. "
        "This sacred image brings peace, happiness, and good health to all who see it. "
        "Please share this video with your parents, grandparents, and family members. "
        "Subscribe to our channel for daily divine darshan and blessings. "
        f"Jai {meta['display']}! God bless you all."
    )
    vo_path = OUTPUT / "vo_single.mp3"
    tts(vo_text, vo_path)
    vo_duration = get_duration(vo_path)
    target_dur = max(30.0, min(vo_duration + 2, 54.0))

    print(f"🙏 God: {meta['display']} | Single image | {target_dur:.1f}s", file=sys.stderr)

    out_file = OUTPUT / "short_single.mp4"
    _build_single_image_vertical(chosen_clip, vo_path, target_dur, title, out_file, meta)

    return {
        "video":       str(out_file),
        "title":       title[:95],
        "description": meta["description"],
        "tags":        meta["tags"],
        "god_name":    god_dir.name,
        "mode":        "single_image",
    }


def _build_single_image_vertical(clip: Path, vo_path: Path, duration: float,
                                  title: str, out_file: Path, meta: dict):
    """Single image with Ken Burns zoom + fade in/out + golden glow border."""
    sub_start = max(0, duration - 5)
    clean_title = title.replace("'", "").replace(":", "").replace("#", "").upper()[:40]
    god_display  = meta["display"].upper()

    # Ken Burns: slow zoom from 1.05x to 1.15x over the full duration
    zoom_effect = (
        f"scale=8000:-1,zoompan="
        f"z='min(zoom+0.0003,1.15)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={int(duration*30)}:s=720x1280:fps=30"
    )
    fade_in  = "fade=t=in:st=0:d=1.5"
    fade_out = f"fade=t=out:st={duration-1.5:.2f}:d=1.5"

    text_layers = (
        # God name — bottom third, always visible
        f"drawtext=fontfile='{FONT_PATH}':text='🙏 JAI {god_display}':fontsize=48:"
        f"fontcolor=gold:borderw=5:bordercolor=black:"
        f"x=(w-text_w)/2:y=h*0.78,"
        # Subtitle line
        f"drawtext=fontfile='{FONT_PATH}':text='DIVINE DARSHAN':fontsize=30:"
        f"fontcolor=white@0.85:borderw=3:bordercolor=black:"
        f"x=(w-text_w)/2:y=h*0.85,"
        # Subscribe CTA
        f"drawtext=fontfile='{FONT_PATH}':text='🔔 SUBSCRIBE FOR DAILY BLESSINGS':fontsize=32:"
        f"fontcolor=red:borderw=4:bordercolor=white:"
        f"x=(w-text_w)/2:y=(h-text_h)/2:enable='gt(t,{sub_start:.1f})',"
        # Channel watermark
        f"drawtext=fontfile='{FONT_PATH}':text='{CHANNEL_TAG}':fontsize=22:"
        f"fontcolor=white@0.5:x=w-tw-16:y=16"
    )

    vf = f"{zoom_effect},{fade_in},{fade_out},{text_layers}"

    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", str(clip),
        "-i", str(vo_path),
        "-filter_complex",
            f"[0:v]{vf}[vout];[1:a]volume=2.2[aout]",
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-t", f"{duration:.2f}",
        "-r", "30",
        str(out_file)
    ]
    subprocess.run(cmd, check=True)


# ─────────────────────────────────────────────────────────────────────────────
# VIDEO TYPE C — Long Landscape Video (<4 min, 1920x1080)
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

    # Collect clips up to 3 min 40 sec (leaving room for VO and credits)
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
        selected = [(shuffled[0], get_duration(shuffled[0]))]

    # TTS: full devotional narration
    vo_text = (
        f"Jai {meta['display']}! Welcome to our channel. "
        "We bring you this beautiful collection of divine images for your daily darshan. "
        "May looking at these sacred images bring peace, health, and happiness to you and your entire family. "
        "Our elders always taught us that starting the day with God's darshan brings good fortune. "
        "Take a moment, close your eyes, and offer your prayers with a pure heart. "
        f"May {meta['display']} always protect you and bless your family with long life and prosperity. "
        "Please like this video, share it with your parents and grandparents, "
        "and subscribe to our channel for daily devotional content. "
        f"Jai {meta['display']}! God bless you all."
    )
    vo_path = OUTPUT / "vo_long.mp3"
    tts(vo_text, vo_path)
    vo_duration = get_duration(vo_path)
    target_dur = max(total_dur, vo_duration + 2)

    print(f"🙏 God: {meta['display']} | Long video | {len(selected)} clips | {target_dur:.1f}s", file=sys.stderr)

    out_file = OUTPUT / "long_video.mp4"
    _build_long_landscape(selected, vo_path, target_dur, title, out_file, meta)

    return {
        "video":       str(out_file),
        "title":       title[:95],
        "description": meta["description"],
        "tags":        meta["tags"],
        "god_name":    god_dir.name,
        "mode":        "long_video",
    }


def _build_long_landscape(selected: list, vo_path: Path, duration: float,
                           title: str, out_file: Path, meta: dict):
    """Concat horizontal clips, TTS audio, elegant text overlays."""
    n = len(selected)
    sub_start = max(0, duration - 6)
    god_display = meta["display"].upper()

    cmd = ["ffmpeg", "-y"]
    for clip, _ in selected:
        cmd += ["-i", str(clip)]
    cmd += ["-i", str(vo_path)]

    fc = ""
    for i in range(n):
        fc += f"[{i}:v]setpts=PTS-STARTPTS[v{i}];"
    fc += "".join(f"[v{i}]" for i in range(n))
    fc += f"concat=n={n}:v=1:a=0[vraw];"

    # Landscape text overlays — title top, god name bottom-left, subscribe end
    clean_title = title.replace("'", "").replace(":", "").replace("#", "")[:60]
    overlays = (
        f"drawtext=fontfile='{FONT_PATH}':text='{clean_title}':fontsize=50:"
        f"fontcolor=gold:borderw=5:bordercolor=black:"
        f"x=(w-text_w)/2:y=60:enable='between(t,0,5)',"
        f"drawtext=fontfile='{FONT_PATH}':text='🙏 JAI {god_display}':fontsize=44:"
        f"fontcolor=white:borderw=4:bordercolor=black:"
        f"x=40:y=h-80,"
        f"drawtext=fontfile='{FONT_PATH}':text='SUBSCRIBE FOR DAILY DARSHAN 🔔':fontsize=48:"
        f"fontcolor=red:borderw=5:bordercolor=white:"
        f"x=(w-text_w)/2:y=(h-text_h)/2:enable='gt(t,{sub_start:.1f})',"
        f"drawtext=fontfile='{FONT_PATH}':text='{CHANNEL_TAG}':fontsize=26:"
        f"fontcolor=white@0.45:x=w-tw-20:y=20,"
        # Fade in/out
        f"fade=t=in:st=0:d=2,fade=t=out:st={duration-2:.1f}:d=2"
    )

    fc += f"[vraw]{overlays}[vout];"
    fc += f"[{n}:a]volume=2.2[aout]"

    cmd += [
        "-filter_complex", fc,
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
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
