"""
Phase 6.2 — Retry Tamil sample + fix mixed audio sample
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

import os
import re
import json
import time
import subprocess
from pathlib import Path

sys.path.insert(0, os.getcwd())

SAMPLE_DIR = Path("data/audio/phase62_samples")
BGM_FILE = Path("assets/music/devotional/shiva_devotional_mystic_flute.wav")

# ---------------------------------------------------------------------------
# Tamil retry
# ---------------------------------------------------------------------------
def synthesize_with_pauses(text, voice, rate, pitch, output_path, pause_ms=400):
    import edge_tts, asyncio

    parts_re = re.split(r'(?<=[。।.!?])\s+', text.strip())
    sentences = [p.strip() for p in parts_re if p.strip()]

    silence_file = SAMPLE_DIR / "_silence_retry.wav"
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"anullsrc=r=24000:cl=mono",
        "-t", f"{pause_ms/1000:.3f}",
        "-c:a", "pcm_s16le",
        str(silence_file)
    ], check=True)

    part_files = []

    async def synth_all():
        for i, s in enumerate(sentences):
            part_file = SAMPLE_DIR / f"_ta_part_{i}.mp3"
            communicate = edge_tts.Communicate(text=s, voice=voice, rate=rate, pitch=pitch)
            await communicate.save(str(part_file))
            part_files.append(part_file)

    asyncio.run(synth_all())

    concat_list = SAMPLE_DIR / "_ta_concat.txt"
    lines = []
    for i, pf in enumerate(part_files):
        if pf.exists() and pf.stat().st_size > 500:
            lines.append(f"file '{pf.absolute()}'\n")
            if i < len(part_files) - 1:
                lines.append(f"file '{silence_file.absolute()}'\n")
    concat_list.write_text("".join(lines), encoding="utf-8")

    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c:a", "libmp3lame", "-b:a", "128k", "-ar", "24000",
        str(output_path)
    ], check=True)


def probe_audio(path):
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_streams", "-show_format", str(path)],
        capture_output=True, text=True
    )
    d = json.loads(r.stdout)
    fmt = d.get("format", {})
    audio = next((s for s in d.get("streams", []) if s["codec_type"] == "audio"), {})
    r2 = subprocess.run(
        ["ffmpeg", "-i", str(path), "-af", "volumedetect", "-vn", "-f", "null", "-"],
        capture_output=True, text=True
    )
    mean = re.search(r"mean_volume:\s*([\-\d\.]+)", r2.stderr)
    mx   = re.search(r"max_volume:\s*([\-\d\.]+)", r2.stderr)
    return {
        "duration_seconds": round(float(fmt.get("duration", 0)), 2),
        "codec": audio.get("codec_name", "?"),
        "sample_rate": audio.get("sample_rate", "?"),
        "channels": audio.get("channels", "?"),
        "mean_volume_dbfs": mean.group(1) if mean else "N/A",
        "max_volume_dbfs": mx.group(1) if mx else "N/A",
    }


# --- Tamil retry ---
ta_out = SAMPLE_DIR / "sample_ta_IN.mp3"
ta_text = (
    "சிவபெருமான் தமது கழுத்தில் விஷமுள்ள நாகத்தை ஏன் அணிந்திருக்கிறார்? "
    "இது சாதாரண ஆபரணமல்ல. "
    "திருப்பாற்கடல் கடைந்தபோது ஆலகால விஷம் வெளிவந்தது. "
    "சிவபெருமான் அதை அருந்தி அனைத்து உலகையும் காத்தார்."
)

print("[ta-IN] Retrying Tamil synthesis...")
for attempt in range(1, 4):
    try:
        synthesize_with_pauses(ta_text, "ta-IN-PallaviNeural", "+0%", "+0Hz", ta_out)
        probe = probe_audio(ta_out)
        print(f"  [OK] sample_ta_IN.mp3: {probe['duration_seconds']}s | "
              f"{probe['codec']} {probe['sample_rate']}Hz | "
              f"mean={probe['mean_volume_dbfs']} dBFS max={probe['max_volume_dbfs']} dBFS")
        break
    except Exception as e:
        print(f"  Attempt {attempt} failed: {e}")
        if attempt < 3:
            time.sleep(5)

# ---------------------------------------------------------------------------
# Mixed sample (AAC output, narration + BGM at -22 dBFS)
# Use two-step: convert narration to WAV first, then amix cleanly
# ---------------------------------------------------------------------------
print("\n[mixed] Generating narration + BGM mixed sample...")
hi_mp3 = SAMPLE_DIR / "sample_hi_IN.mp3"
hi_wav = SAMPLE_DIR / "_hi_IN_for_mix.wav"
mixed_out = SAMPLE_DIR / "sample_mixed_hi_bgm.aac"

# Convert narration MP3 → WAV so amix avoids MP3 muxer issues
subprocess.run([
    "ffmpeg", "-y", "-v", "error",
    "-i", str(hi_mp3),
    "-ar", "48000", "-ac", "2",
    str(hi_wav)
], check=True)

# Mix: narration (full level) + BGM at -22 dBFS, amix normalize=0
subprocess.run([
    "ffmpeg", "-y", "-v", "error",
    "-i", str(hi_wav),
    "-i", str(BGM_FILE),
    "-filter_complex",
    "[1:a]volume=-22.0dB[a_bgm];"
    "[0:a][a_bgm]amix=inputs=2:duration=first:dropout_transition=1:normalize=0[a_out]",
    "-map", "[a_out]",
    "-c:a", "aac", "-ar", "48000", "-ac", "2",
    str(mixed_out)
], check=True)

narr_p = probe_audio(hi_wav)
mix_p  = probe_audio(mixed_out)
print(f"  Narration mean:    {narr_p['mean_volume_dbfs']} dBFS  max: {narr_p['max_volume_dbfs']} dBFS")
print(f"  Mixed output mean: {mix_p['mean_volume_dbfs']} dBFS  max: {mix_p['max_volume_dbfs']} dBFS")
print(f"  Duration: {mix_p['duration_seconds']}s | {mix_p['codec']} {mix_p['sample_rate']}Hz")
diff = float(narr_p['mean_volume_dbfs']) - float(mix_p['mean_volume_dbfs'])
print(f"  BGM contribution estimate: +{diff:.1f} dBFS lift in mix")
print(f"  Music audible: {'YES — BGM raised mix level' if diff < -0.5 else 'MARGINAL'}")
print(f"  File: {mixed_out}")
