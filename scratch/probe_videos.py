import subprocess, json
from pathlib import Path

videos = [
    ("hi-IN", Path("data/videos/shiva_hi_final.mp4")),
    ("te-IN", Path("data/videos/shiva_te_final.mp4")),
    ("ta-IN", Path("data/videos/shiva_ta_final.mp4")),
]

for lang, v in videos:
    if not v.exists():
        print(f"MISSING: {v}")
        continue
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", "-show_format", str(v)],
        capture_output=True, text=True
    )
    d = json.loads(r.stdout)
    fmt = d.get("format", {})
    streams = d.get("streams", [])
    for s in streams:
        ct = s.get("codec_type", "")
        if ct == "video":
            w = s["width"]
            h = s["height"]
            codec = s["codec_name"]
            pix = s["pix_fmt"]
            print(f"{lang} VIDEO: {w}x{h} {codec} {pix}")
        elif ct == "audio":
            acodec = s["codec_name"]
            sr = s["sample_rate"]
            ch = s["channels"]
            print(f"{lang} AUDIO: {acodec} {sr}Hz ch={ch}")
    dur = float(fmt.get("duration", 0))
    size = int(fmt.get("size", 0))
    print(f"{lang} DURATION={dur:.1f}s SIZE={size:,}B")
    print()
