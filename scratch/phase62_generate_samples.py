"""
Phase 6.2 — Audio Sample Generator
Generates short TTS samples for Hindi (Devanagari), Telugu (Telugu script), Tamil (Tamil script).
Also generates a mixed sample (narration + BGM) to verify music audibility.

DO NOT render full videos. Samples only.
"""
import sys
sys.stdout.reconfigure(encoding="utf-8")

import os
import re
import json
import subprocess
import hashlib
from pathlib import Path

sys.path.insert(0, os.getcwd())

SAMPLE_DIR = Path("data/audio/phase62_samples")
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

BGM_FILE = Path("assets/music/devotional/shiva_devotional_mystic_flute.wav")

# ---------------------------------------------------------------------------
# Native-script narration samples (one representative scene per language)
# Short enough to evaluate in <30 seconds of audio
# ---------------------------------------------------------------------------

SAMPLES = {
    "hi-IN": {
        "voice": "hi-IN-SwaraNeural",
        "rate": "+0%",       # Slightly slower than before — more devotional/contemplative
        "pitch": "+0Hz",
        "text": (
            "भगवान शिव अपने गले में विषैले नाग को क्यों धारण करते हैं? "
            "यह कोई सामान्य आभूषण नहीं है। "
            "जब समुद्र मंथन में हलाहल विष प्रकट हुआ, "
            "तब महादेव ने उसे स्वयं पी लिया और सृष्टि की रक्षा की।"
        ),
        "description": "Hindi hook + story intro (Devanagari)",
    },
    "te-IN": {
        "voice": "te-IN-ShrutiNeural",
        "rate": "+0%",
        "pitch": "+0Hz",
        "text": (
            "మహాదేవుడు తన మెడలో విషపూరితమైన నాగును ఎందుకు ధరించారు? "
            "ఇది సాధారణ ఆభరణం కాదు. "
            "క్షీరసాగర మథనంలో హాలాహలం వెలువడినప్పుడు, "
            "శివుడు దానిని స్వయంగా మింగి సమస్త సృష్టిని రక్షించారు."
        ),
        "description": "Telugu hook + story intro (Telugu script)",
    },
    "ta-IN": {
        "voice": "ta-IN-PallaviNeural",
        "rate": "+0%",
        "pitch": "+0Hz",
        "text": (
            "சிவபெருமான் தமது கழுத்தில் விஷமுள்ள நாகத்தை ஏன் அணிந்திருக்கிறார்? "
            "இது சாதாரண ஆபரணமல்ல. "
            "திருப்பாற்கடல் கடைந்தபோது ஆலகால விஷம் வெளிவந்தது. "
            "சிவபெருமான் அதை அருந்தி அனைத்து உலகையும் காத்தார்."
        ),
        "description": "Tamil hook + story intro (Tamil script)",
    },
}

# ---------------------------------------------------------------------------
# Sentence-level segmentation helper
# ---------------------------------------------------------------------------

def segment_sentences(text: str) -> list[str]:
    """Split text at sentence boundaries (।, ., !, ?) with trailing space."""
    # Split on Devanagari danda (।), Telugu/Tamil full stop (.), !, ?
    parts = re.split(r'(?<=[।.!?])\s+', text.strip())
    return [p.strip() for p in parts if p.strip()]


def synthesize_with_pauses(
    text: str,
    voice: str,
    rate: str,
    pitch: str,
    output_path: Path,
    pause_ms: int = 400,
) -> None:
    """
    Synthesize text sentence-by-sentence, insert silence between sentences,
    then concatenate into one MP3.
    """
    import edge_tts
    import asyncio

    sentences = segment_sentences(text)
    parts = []
    silence_file = SAMPLE_DIR / "_silence.mp3"

    # Generate silence file (400ms) for inter-sentence pauses
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "lavfi", "-i", f"anullsrc=r=24000:cl=mono",
        "-t", f"{pause_ms/1000:.3f}",
        "-c:a", "mp3", "-b:a", "128k",
        str(silence_file)
    ], check=True)

    async def synth_one(idx: int, sentence: str) -> Path:
        part_file = SAMPLE_DIR / f"_part_{idx}.mp3"
        communicate = edge_tts.Communicate(
            text=sentence, voice=voice, rate=rate, pitch=pitch
        )
        await communicate.save(str(part_file))
        return part_file

    async def synth_all():
        for i, s in enumerate(sentences):
            await synth_one(i, s)

    asyncio.run(synth_all())

    # Collect parts with silence between them
    concat_list = SAMPLE_DIR / "_concat_list.txt"
    lines = []
    for i in range(len(sentences)):
        part = SAMPLE_DIR / f"_part_{i}.mp3"
        if part.exists() and part.stat().st_size > 500:
            lines.append(f"file '{part.absolute()}'\n")
            if i < len(sentences) - 1:
                lines.append(f"file '{silence_file.absolute()}'\n")
    concat_list.write_text("".join(lines), encoding="utf-8")

    # Concatenate
    subprocess.run([
        "ffmpeg", "-y", "-v", "error",
        "-f", "concat", "-safe", "0",
        "-i", str(concat_list),
        "-c", "copy",
        str(output_path)
    ], check=True)


# ---------------------------------------------------------------------------
# Probe audio file
# ---------------------------------------------------------------------------

def probe_audio(path: Path) -> dict:
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_streams", "-show_format", str(path)],
        capture_output=True, text=True
    )
    d = json.loads(r.stdout)
    fmt = d.get("format", {})
    streams = d.get("streams", [])
    audio = next((s for s in streams if s["codec_type"] == "audio"), {})

    # Loudness
    r2 = subprocess.run(
        ["ffmpeg", "-i", str(path), "-af", "volumedetect", "-vn", "-f", "null", "-"],
        capture_output=True, text=True
    )
    import re
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


# ---------------------------------------------------------------------------
# Main: generate samples
# ---------------------------------------------------------------------------

results = {}

print("=" * 64)
print("  PHASE 6.2 — AUDIO SAMPLES (native script, sentence-segmented)")
print("=" * 64)

for lang, cfg in SAMPLES.items():
    out_file = SAMPLE_DIR / f"sample_{lang.replace('-','_')}.mp3"
    print(f"\n[{lang}] Synthesizing: {cfg['voice']} rate={cfg['rate']} pitch={cfg['pitch']}")
    print(f"  Text: {cfg['text'][:80]}...")

    try:
        synthesize_with_pauses(
            text=cfg["text"],
            voice=cfg["voice"],
            rate=cfg["rate"],
            pitch=cfg["pitch"],
            output_path=out_file,
            pause_ms=400,
        )
        probe = probe_audio(out_file)
        results[lang] = {
            "status": "OK",
            "file": str(out_file),
            "text": cfg["text"],
            "voice": cfg["voice"],
            "rate": cfg["rate"],
            "pitch": cfg["pitch"],
            **probe,
        }
        print(f"  [OK] {out_file.name}: {probe['duration_seconds']}s | "
              f"{probe['codec']} {probe['sample_rate']}Hz | "
              f"mean={probe['mean_volume_dbfs']} dBFS max={probe['max_volume_dbfs']} dBFS")
    except Exception as e:
        results[lang] = {"status": f"ERROR: {e}", "file": str(out_file)}
        print(f"  [ERROR] {lang}: {e}")


# ---------------------------------------------------------------------------
# Mixed sample: narration + BGM
# ---------------------------------------------------------------------------
print("\n" + "=" * 64)
print("  MIXED SAMPLE: Hindi narration + BGM (-22 dBFS)")
print("=" * 64)

mixed_out = SAMPLE_DIR / "sample_mixed_hi_bgm.mp3"
narration_file = SAMPLE_DIR / "sample_hi_IN.mp3"

if narration_file.exists() and BGM_FILE.exists():
    try:
        # Mix using dB-scale attenuation + amix normalize=0
        subprocess.run([
            "ffmpeg", "-y", "-v", "error",
            "-i", str(narration_file),
            "-i", str(BGM_FILE),
            "-filter_complex",
            "[1:a]volume=-22.0dB[a_bgm];"
            "[0:a][a_bgm]amix=inputs=2:duration=first:dropout_transition=1:normalize=0[a_out]",
            "-map", "[a_out]",
            "-c:a", "aac", "-ar", "48000", "-ac", "2",
            str(mixed_out)
        ], check=True)

        mixed_probe = probe_audio(mixed_out)
        narr_probe = probe_audio(narration_file)
        results["mixed"] = {
            "status": "OK",
            "file": str(mixed_out),
            "narration_mean_dbfs": narr_probe["mean_volume_dbfs"],
            "mixed_mean_dbfs": mixed_probe["mean_volume_dbfs"],
            "mixed_max_dbfs": mixed_probe["max_volume_dbfs"],
            **mixed_probe,
        }
        print(f"  [OK] Narration mean: {narr_probe['mean_volume_dbfs']} dBFS")
        print(f"  [OK] Mixed output mean: {mixed_probe['mean_volume_dbfs']} dBFS  "
              f"max: {mixed_probe['max_volume_dbfs']} dBFS")
        print(f"  BGM target was -22 dBFS; narration dominant = "
              f"{'YES' if float(narr_probe['mean_volume_dbfs']) > float(mixed_probe['mean_volume_dbfs']) - 10 else 'CHECK'}")
    except Exception as e:
        results["mixed"] = {"status": f"ERROR: {e}"}
        print(f"  [ERROR] mixed sample: {e}")
else:
    print(f"  SKIP: narration={narration_file.exists()}, bgm={BGM_FILE.exists()}")


# ---------------------------------------------------------------------------
# Summary report
# ---------------------------------------------------------------------------
print("\n" + "=" * 64)
print("  PHASE 6.2 SAMPLE REPORT")
print("=" * 64)

for key, r in results.items():
    print(f"\n  [{key}]")
    for k, v in r.items():
        if k != "text":
            print(f"    {k}: {v}")
    if "text" in r:
        print(f"    text_preview: {r['text'][:120]}")

# Save report JSON
report_path = SAMPLE_DIR / "phase62_sample_report.json"
report_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"\n  Full report saved: {report_path}")
print("\n[DONE] Samples generated. Review audio before proceeding to full render.")
