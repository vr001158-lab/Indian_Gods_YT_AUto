# src/audio/ducking.py
# Automatic Audio Ducking Engine using FFmpeg (Music Pipeline v2)

from __future__ import annotations

import subprocess
from pathlib import Path

NARRATION_TARGET_DB = -4.0
MUSIC_TARGET_DB = -18.0


def mix_audio_with_ducking(
    narration_path: str | Path,
    music_path: str | Path | None,
    output_path: str | Path,
    narration_volume_db: float = NARRATION_TARGET_DB,
    music_volume_db: float = MUSIC_TARGET_DB,
) -> Path:
    """
    Mix narration audio track with ducked background music using FFmpeg.
    Narration is kept dominant (-4.0 dB target), background music is ducked (-16.0 dB target).
    
    If music_path is None or missing, normalizes and copies narration track directly.
    """
    np = Path(narration_path)
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    if not np.exists():
        raise FileNotFoundError(f"Narration file not found: {np}")

    if not music_path or not Path(music_path).exists():
        # Copy / normalize narration directly
        cmd = [
            "ffmpeg", "-y", "-v", "error",
            "-i", str(np),
            "-filter:a", f"volume={10**(narration_volume_db/20):.2f}",
            "-c:a", "mp3", "-b:a", "192k",
            str(out_p),
        ]
        subprocess.run(cmd, check=True)
        return out_p

    mp = Path(music_path)
    # FFmpeg filter complex: loop music seamlessly, fade in, apply dB volume, mix with normalize=0
    filter_complex = (
        f"[1:a]aloop=loop=-1:size=2e+09,afade=t=in:st=0:d=1.0,volume={music_volume_db:.1f}dB[bg];"
        f"[0:a]volume=0.0dB[fg];"
        f"[fg][bg]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[out]"
    )

    cmd = [
        "ffmpeg", "-y", "-v", "error",
        "-i", str(np),
        "-i", str(mp),
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-c:a", "mp3", "-b:a", "192k",
        str(out_p),
    ]
    subprocess.run(cmd, check=True)
    return out_p
