"""
generate_short.py — God Channel Video Generator (v2)
------------------------------------------------------
Generates one of four video types based on --mode argument. Sources are now
a MIXED pool of still-image clips and real short video clips (both produced
by prepare_assets.py into assets/gods_processed/<god>/vertical|horizontal),
so a single god's Short can freely combine photos and footage.

  --mode multi_image   → Short Type A: several clips (images and/or videos)
                          from one randomly chosen god, joined with gentle
                          crossfade transitions. Vertical, 25–50s.

  --mode single_image  → Short Type B: one still image, Ken Burns zoom +
                          fade. Vertical, 25–50s.

  --mode single_video   → Short Type B2: one real video clip, gentle
                          zoom/pan + fade (no zoompan-from-still artifacts).
                          Vertical, 25–50s.

  --mode long_video     → Long video: all clips (images and/or videos) from
                          one god's assets/long_video_source/<god>/ folder,
                          landscape 1920x1080, crossfade-joined, under 4 min.

No voiceover. No text overlays. Transitions are deliberately gentle/elegant
(crossfade family, slow zoom) — nothing flashy/strobing, aimed at holding
attention for an older (30+) devotional audience without feeling gimmicky.

Duration guidance (YouTube, 2026): Shorts can run up to 3 minutes, but
completion-rate data consistently shows 20–45s (up to ~60s) as the
best-performing range for Shorts feed distribution. This script defaults
Shorts to SHORT_MIN_S–SHORT_MAX_S (25–50s) accordingly — tune below if you
want to test longer/shorter. Long-form videos have no official minimum;
this pipeline caps at ~4 minutes to match the size of a typical single-god
image/clip set, but you can raise LONG_VIDEO_CAP_S once you have more
source material per god.

Output filenames: every finished video is renamed to
    <god_name>_<mode>_<YYYYMMDD_HHMMSS>_IST.mp4
using Indian Standard Time, so uploads sort naturally and are unambiguous
regardless of which timezone the GitHub Actions runner executes in.
A companion "<same-name>.json" sidecar with title/description/tags/god_name
is written next to the video for uploader.py to consume — the last stdout
line is still the same JSON for backward compatibility.
"""

import sys
import json
import random
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

# ─────────────────────────────────────────────
PROC_BASE         = Path("assets/gods_processed")
LONG_VIDEO_SOURCE = Path("assets/long_video_source")   # top-level folder for long-video clips
OUTPUT            = Path("output")
OUTPUT.mkdir(exist_ok=True)

MANIFEST   = Path("manifest.json")   # tracks folder rotation fairness

IST = ZoneInfo("Asia/Kolkata")

# Shorts: best-performing completion-rate band per 2026 platform data.
# YouTube's hard cap is 180s (3 min) but sweet-spot is much shorter.
SHORT_MIN_S      = 25
SHORT_MAX_S      = 50

# Long video: no official YouTube minimum; capped here to match typical
# per-god asset volume. Raise once you have more long_video_source clips.
LONG_VIDEO_CAP_S = 218   # 3 min 38s, leaves headroom under the 4-min target

# Crossfade transition duration between clips (kept short/subtle on Shorts,
# slightly longer on long-form for a calmer pace).
SHORT_TRANSITION_S = 0.45
LONG_TRANSITION_S  = 0.8

# Elegant, non-gimmicky transition set — avoids anything flashy/strobing.
TRANSITIONS = ["fade", "dissolve", "smoothleft", "smoothright", "circleopen"]
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


def get_meta(god_name: str) -> dict:
    """Fallback metadata for any god folder not listed above."""
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
    Each mode tracks its own rotation.
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
        used = set()
        remaining = available

    chosen = random.choice(remaining)
    used.add(chosen.name)
    manifest[key] = list(used)
    save_manifest(manifest)

    return chosen


# ── ffprobe / ffmpeg helpers ─────────────────────────────────────────────────

def get_duration(file: Path) -> float:
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "default=noprint_wrappers=1:nokey=1", str(file)]
    return float(subprocess.check_output(cmd).decode().strip())


def run_ffmpeg(cmd: list):
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg error:\n{e.stderr[-1200:]}", file=sys.stderr)
        raise


def random_short_duration() -> float:
    """Pick a random target duration inside the Shorts sweet-spot band."""
    return round(random.uniform(SHORT_MIN_S, SHORT_MAX_S), 2)


def is_video_origin(clip: Path) -> bool:
    return clip.stem.endswith("__vid")


def is_image_origin(clip: Path) -> bool:
    return clip.stem.endswith("__img")


# ─────────────────────────────────────────────────────────────────────────────
# Crossfade concat — used by every multi-clip build (Shorts + long video)
# ─────────────────────────────────────────────────────────────────────────────

def build_crossfade_video(selected: list, size: str, transition_s: float, out_file: Path,
                           end_fade: bool = True) -> float:
    """
    Join `selected` = [(clip_path, use_duration), ...] into out_file using
    ffmpeg's xfade filter for smooth crossfade-style transitions between
    clips (randomly varied, but from a curated 'calm' set — see TRANSITIONS).
    Returns the total output duration actually produced.
    """
    n = len(selected)
    cmd = ["ffmpeg", "-y"]
    for clip, _ in selected:
        cmd += ["-i", str(clip)]

    if n == 1:
        clip, dur = selected[0]
        vf = f"scale={size}:force_original_aspect_ratio=increase,crop={size.replace(':', ':')},setsar=1,fps=30"
        if end_fade:
            vf += f",fade=t=in:st=0:d=1,fade=t=out:st={max(dur - 1, 0):.2f}:d=1"
        cmd += [
            "-t", f"{dur:.2f}",
            "-vf", vf,
            "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p", "-r", "30",
            str(out_file)
        ]
        run_ffmpeg(cmd)
        return dur

    w, h = size.split(":")
    filters, labels = [], []
    for i, (clip, dur) in enumerate(selected):
        filters.append(
            f"[{i}:v]scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h},setsar=1,fps=30,trim=duration={dur:.2f},"
            f"setpts=PTS-STARTPTS[c{i}]"
        )
        labels.append(f"c{i}")

    chain = []
    cur = labels[0]
    offset = selected[0][1] - transition_s
    running_total = selected[0][1]
    for i in range(1, n):
        trans = random.choice(TRANSITIONS)
        out_label = f"x{i}"
        chain.append(
            f"[{cur}][{labels[i]}]xfade=transition={trans}:"
            f"duration={transition_s:.2f}:offset={max(offset, 0):.2f}[{out_label}]"
        )
        cur = out_label
        running_total += selected[i][1] - transition_s
        offset += selected[i][1] - transition_s

    fc = ";".join(filters) + ";" + ";".join(chain)
    final_label = cur
    total_duration = max(running_total, 1.0)

    if end_fade:
        fc += f";[{final_label}]fade=t=in:st=0:d=0.6,fade=t=out:st={max(total_duration - 0.8, 0):.2f}:d=0.8[vout]"
        map_label = "vout"
    else:
        map_label = final_label

    cmd += [
        "-filter_complex", fc,
        "-map", f"[{map_label}]",
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-r", "30",
        "-t", f"{total_duration:.2f}",
        str(out_file)
    ]
    run_ffmpeg(cmd)
    return total_duration


def _pick_clips_for_duration(clips: list, target_dur: float) -> list:
    """Greedily shuffle-pick clips (images and/or videos) to approx. fill target_dur."""
    selected = []
    total = 0.0
    shuffled = list(clips)
    random.shuffle(shuffled)

    for clip in shuffled:
        d = get_duration(clip)
        if total + d > target_dur:
            remaining = target_dur - total
            if remaining >= 1.2:
                selected.append((clip, remaining))
                total += remaining
            break
        selected.append((clip, d))
        total += d
        if total >= target_dur:
            break

    if not selected:
        clip = shuffled[0]
        d = min(get_duration(clip), target_dur)
        selected = [(clip, d)]

    return selected


# ─────────────────────────────────────────────────────────────────────────────
# VIDEO TYPE A — Multi-clip Short (vertical, ~25–50s, crossfade transitions)
# Mixes still-image clips and real video clips from the SAME god at random.
# ─────────────────────────────────────────────────────────────────────────────

def generate_multi_image_short() -> dict:
    god_dir = pick_god_folder("multi_image")
    vert_dir = god_dir / "vertical"
    clips = sorted(vert_dir.glob("*.mp4"))

    if not clips:
        print(f"❌ No vertical clips in {vert_dir}", file=sys.stderr)
        sys.exit(1)

    meta = get_meta(god_dir.name)
    title = random.choice(meta["titles_multi"])
    target_dur = random_short_duration()

    selected = _pick_clips_for_duration(clips, target_dur)
    n_img = sum(1 for c, _ in selected if is_image_origin(c))
    n_vid = sum(1 for c, _ in selected if is_video_origin(c))
    print(f"🙏 God: {meta['display']} | {len(selected)} clips ({n_img} img / {n_vid} vid) | target {target_dur:.1f}s",
          file=sys.stderr)

    out_file = OUTPUT / "short_multi.mp4"
    actual_dur = build_crossfade_video(selected, "720:1280", SHORT_TRANSITION_S, out_file)

    return {
        "video": str(out_file), "title": title[:95], "description": meta["description"],
        "tags": meta["tags"], "god_name": god_dir.name, "mode": "multi_image",
        "duration_s": round(actual_dur, 2),
    }


# ─────────────────────────────────────────────────────────────────────────────
# VIDEO TYPE B — Single-image Short (vertical, ~25–50s, Ken Burns, fade)
# ─────────────────────────────────────────────────────────────────────────────

def generate_single_image_short() -> dict:
    god_dir = pick_god_folder("single_image")
    vert_dir = god_dir / "vertical"
    all_clips = sorted(vert_dir.glob("*.mp4"))
    image_clips = [c for c in all_clips if is_image_origin(c)] or all_clips

    if not image_clips:
        print(f"❌ No clips in {vert_dir}", file=sys.stderr)
        sys.exit(1)

    chosen_clip = random.choice(image_clips)
    meta = get_meta(god_dir.name)
    title = random.choice(meta["titles_single"])
    target_dur = random_short_duration()

    print(f"🙏 God: {meta['display']} | Single image | {target_dur:.1f}s", file=sys.stderr)

    out_file = OUTPUT / "short_single.mp4"
    _build_single_image_vertical(chosen_clip, target_dur, out_file)

    return {
        "video": str(out_file), "title": title[:95], "description": meta["description"],
        "tags": meta["tags"], "god_name": god_dir.name, "mode": "single_image",
        "duration_s": target_dur,
    }


def _build_single_image_vertical(clip: Path, duration: float, out_file: Path):
    """Single still image with Ken Burns zoom + fade in/out. No audio, no text."""
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
        "-vf", vf, "-an",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-t", f"{duration:.2f}", "-r", "30",
        str(out_file)
    ]
    run_ffmpeg(cmd)


# ─────────────────────────────────────────────────────────────────────────────
# VIDEO TYPE B2 — Single-video Short (vertical, ~25–50s, gentle zoom+fade)
# For clips that already have real motion — avoids double-zoompan artifacts.
# ─────────────────────────────────────────────────────────────────────────────

def generate_single_video_short() -> dict:
    god_dir = pick_god_folder("single_video")
    vert_dir = god_dir / "vertical"
    all_clips = sorted(vert_dir.glob("*.mp4"))
    video_clips = [c for c in all_clips if is_video_origin(c)]

    if not video_clips:
        print(f"⚠️  No real video clips for {god_dir.name}, falling back to single_image.", file=sys.stderr)
        return generate_single_image_short()

    chosen_clip = random.choice(video_clips)
    meta = get_meta(god_dir.name)
    title = random.choice(meta["titles_single"])
    target_dur = random_short_duration()

    print(f"🙏 God: {meta['display']} | Single video | {target_dur:.1f}s", file=sys.stderr)

    out_file = OUTPUT / "short_single_video.mp4"
    vf = (
        "scale=1.06*720:-1,"                      # slight overscan for a subtle slow pan
        f"zoompan=z='min(zoom+0.0006,1.08)':d={int(target_dur*30)}:s=720x1280:fps=30,"
        "fade=t=in:st=0:d=1.2,"
        f"fade=t=out:st={target_dur - 1.2:.2f}:d=1.2"
    )
    cmd = [
        "ffmpeg", "-y", "-stream_loop", "-1", "-i", str(chosen_clip),
        "-vf", vf, "-an",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-t", f"{target_dur:.2f}", "-r", "30",
        str(out_file)
    ]
    run_ffmpeg(cmd)

    return {
        "video": str(out_file), "title": title[:95], "description": meta["description"],
        "tags": meta["tags"], "god_name": god_dir.name, "mode": "single_video",
        "duration_s": target_dur,
    }


# ─────────────────────────────────────────────────────────────────────────────
# VIDEO TYPE C — Long Landscape Video (<~4 min, 1920x1080, crossfade)
# Sources its clips from assets/long_video_source/<god_name>/*.mp4
# (images or real videos, already normalized by prepare_assets.py logic if
#  you point that script at this folder too, or pre-rendered separately.)
# ─────────────────────────────────────────────────────────────────────────────

def generate_long_video() -> dict:
    god_dir = pick_god_folder("long_video")
    long_dir = LONG_VIDEO_SOURCE / god_dir.name
    clips = sorted(long_dir.glob("*.mp4"))

    if not clips:
        print(f"❌ No long-video clips in {long_dir}. "
              f"Add clips to assets/long_video_source/{god_dir.name}/", file=sys.stderr)
        sys.exit(1)

    meta = get_meta(god_dir.name)
    title = random.choice(meta["titles_long"])

    selected = []
    total_dur = 0.0
    shuffled = list(clips)
    random.shuffle(shuffled)
    for clip in shuffled:
        d = get_duration(clip)
        if total_dur + d > LONG_VIDEO_CAP_S:
            break
        selected.append((clip, d))
        total_dur += d
    if not selected:
        clip = shuffled[0]
        d = min(get_duration(clip), LONG_VIDEO_CAP_S)
        selected = [(clip, d)]

    print(f"🙏 God: {meta['display']} | Long video | {len(selected)} clips | ~{total_dur:.1f}s", file=sys.stderr)

    out_file = OUTPUT / "long_video.mp4"
    actual_dur = build_crossfade_video(selected, "1920:1080", LONG_TRANSITION_S, out_file)

    return {
        "video": str(out_file), "title": title[:95], "description": meta["description"],
        "tags": meta["tags"], "god_name": god_dir.name, "mode": "long_video",
        "duration_s": round(actual_dur, 2),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Final naming: <god_name>_<mode>_<YYYYMMDD_HHMMSS>_IST.mp4  (+ .json sidecar)
# ─────────────────────────────────────────────────────────────────────────────

def rename_with_ist_timestamp(result: dict) -> dict:
    src = Path(result["video"])
    ist_now = datetime.now(IST)
    stamp = ist_now.strftime("%Y%m%d_%H%M%S")
    final_name = f"{result['god_name']}_{result['mode']}_{stamp}_IST.mp4"
    dest = OUTPUT / final_name
    src.rename(dest)

    result["video"] = str(dest)
    result["generated_at_ist"] = ist_now.isoformat()

    sidecar = dest.with_suffix(".json")
    sidecar.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    result["metadata_file"] = str(sidecar)
    return result


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
    elif mode == "single_video":
        result = generate_single_video_short()
    elif mode == "long_video":
        result = generate_long_video()
    else:
        print(f"❌ Unknown mode: {mode}. Use multi_image | single_image | single_video | long_video",
              file=sys.stderr)
        sys.exit(1)

    result = rename_with_ist_timestamp(result)

    # Print JSON result as last line (parsed by uploader.py)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
