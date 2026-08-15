# src/video/composer.py
# Phase 2G/Phase 4 — Video Composer Render Engine
# Supports Mock composition rendering for tests and full production FFmpeg rendering.

import subprocess
import sys
from pathlib import Path
from src.video.effects import get_video_filtergraph_for_scene


def _parse_resolution(resolution: str) -> tuple[int, int]:
    """Parse '1080x1920' or '720x1280' resolution string into (width, height)."""
    try:
        parts = resolution.lower().split("x")
        return int(parts[0]), int(parts[1])
    except Exception:
        return 1080, 1920


class VideoComposer:
    """Interface for video composition rendering."""

    def compose_video(
        self,
        scenes: list,
        output_file: Path,
        background_music: Path = None,
        bgm_volume: float = 0.15,
        resolution: str = "1080x1920",
    ) -> bool:
        """
        Synthesizes the scenes (images + audios) into an MP4 video.

        Returns
        -------
        bool — True if composition succeeded, False otherwise.
        """
        raise NotImplementedError("Subclasses must implement compose_video")


class MockVideoComposer(VideoComposer):
    """
    Mock Composer that writes dummy text to output_file to simulate video creation.
    Runs 100% offline and avoids launching subprocess processes in tests.
    """

    def compose_video(
        self,
        scenes: list,
        output_file: Path,
        background_music: Path = None,
        bgm_volume: float = 0.15,
        resolution: str = "1080x1920",
    ) -> bool:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        summary = (
            f"MOCK_MP4_VIDEO: resolution={resolution}, format=yuv420p, codec=h264\n"
            f"Scenes composed: {len(scenes)}\n"
            f"BGM: {background_music} (volume={bgm_volume})\n"
        )
        for s in scenes:
            summary += f" - Scene {s['scene']}: img={s['image_file']}, aud={s['audio_file']}, dur={s['duration_seconds']}s\n"

        output_file.write_text(summary, encoding="utf-8")
        return True


def format_caption_text(text: str, max_chars_per_line: int = 35) -> str:
    """Formats caption text into clean multi-line blocks that fit within mobile safe area."""
    if not text:
        return ""
    words = text.split()
    lines = []
    current_line = []
    current_len = 0
    for w in words:
        if current_len + len(w) + (1 if current_line else 0) <= max_chars_per_line:
            current_line.append(w)
            current_len += len(w) + (1 if current_len > 0 else 0)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [w]
            current_len = len(w)
    if current_line:
        lines.append(" ".join(current_line))
    return "\n".join(lines)


class FFmpegVideoComposer(VideoComposer):
    """
    Production Video Composer utilizing local FFmpeg binary execution.
    Formulates and executes clean, high-performance command line instructions.
    """

    def build_ffmpeg_command(
        self,
        scenes: list,
        output_file: Path,
        background_music: Path = None,
        bgm_volume: float = 0.15,
        bgm_db: float = -22.0,
        fps: int = 25,
        resolution: str = "1080x1920",
    ) -> list:
        """
        Constructs the exact FFmpeg command list.

        bgm_db: BGM attenuation in dBFS (e.g. -22.0 means music at -22 dBFS).
               Used instead of linear bgm_volume for accurate loudness targeting.
        """
        width, height = _parse_resolution(resolution)
        cmd = ["ffmpeg", "-y"]  # overwrite output files

        # ── 1. Register Inputs ────────────────────────────────────────────────
        # Inputs alternate: [loop image i], [scene audio i]
        for s in scenes:
            cmd.extend([
                "-loop", "1",
                "-t", str(s["duration_seconds"]),
                "-i", s["image_file"]
            ])
            cmd.extend([
                "-i", s["audio_file"]
            ])

        # Register optional background music input
        if background_music and background_music.exists():
            cmd.extend(["-i", str(background_music.absolute())])

        # ── 2. Construct Filtergraph ──────────────────────────────────────────
        filter_parts = []
        motions = ["zoom_in", "zoom_out", "pan_left", "pan_right", "zoom_in"]
        
        # Prepare caption text files directory
        caption_dir = output_file.parent / f"_captions_{output_file.stem}"
        caption_dir.mkdir(parents=True, exist_ok=True)

        # Pre-process each image input: scale, crop, Ken Burns, fade in/out, captions
        for i, s in enumerate(scenes):
            v_input_idx = 2 * i
            motion_type = motions[i % len(motions)]
            
            caption_file_path = None
            voice_text = s.get("voice_text", "")
            if voice_text:
                formatted_cap = format_caption_text(voice_text)
                txt_path = caption_dir / f"caption_scene_{i+1}.txt"
                txt_path.write_text(formatted_cap, encoding="utf-8")
                caption_file_path = str(txt_path.absolute())

            v_filter = get_video_filtergraph_for_scene(
                duration_seconds=s["duration_seconds"],
                fps=fps,
                width=width,
                height=height,
                motion_type=motion_type,
                caption_text_file=caption_file_path,
            )
            filter_parts.append(f"[{v_input_idx}:v]{v_filter}[v_scene_{i}]")

        # Concat video and audio streams
        concat_in = ""
        for i in range(len(scenes)):
            v_scene_tag = f"[v_scene_{i}]"
            a_scene_tag = f"[{2 * i + 1}:a]"
            concat_in += f"{v_scene_tag}{a_scene_tag}"

        filter_parts.append(
            f"{concat_in}concat=n={len(scenes)}:v=1:a=1[v_concat][a_concat]"
        )

        # Handle BGM mixing if applicable
        if background_music and background_music.exists():
            bgm_idx = 2 * len(scenes)
            # Use dB-scale attenuation so BGM level is predictable and audible.
            # normalize=0 prevents amix from halving both streams (default behaviour
            # would cut narration by -6 dB unnecessarily).
            filter_parts.append(
                f"[{bgm_idx}:a]volume={bgm_db:.1f}dB[a_bgm]"
            )
            filter_parts.append(
                f"[a_concat][a_bgm]amix=inputs=2:duration=first:"
                f"dropout_transition=2:normalize=0[a_final]"
            )
            audio_map_tag = "[a_final]"
        else:
            audio_map_tag = "[a_concat]"

        cmd.extend(["-filter_complex", ";".join(filter_parts)])

        # ── 3. Codec & Output Parameters ──────────────────────────────────────
        cmd.extend([
            "-map", "[v_concat]",
            "-map", audio_map_tag,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-r", str(fps),
            "-c:a", "aac",
            "-ar", "48000",
            "-ac", "2",
            "-shortest",
            str(output_file.absolute())
        ])

        return cmd

    def compose_video(
        self,
        scenes: list,
        output_file: Path,
        background_music: Path = None,
        bgm_volume: float = 0.15,
        bgm_db: float = -22.0,
        resolution: str = "1080x1920",
    ) -> bool:
        cmd = self.build_ffmpeg_command(
            scenes=scenes,
            output_file=output_file,
            background_music=background_music,
            bgm_volume=bgm_volume,
            bgm_db=bgm_db,
            resolution=resolution,
        )

        print(f"\n🚀 Launching FFmpeg composition render ({resolution})...", file=sys.stderr)
        print(f"   Command: {' '.join(cmd)}", file=sys.stderr)

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=True,
            )
            print("✅ FFmpeg render complete!", file=sys.stderr)
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ FFmpeg render FAILED: exit_code={e.returncode}", file=sys.stderr)
            print(f"   Error log:\n{e.stderr}", file=sys.stderr)
            return False
        except FileNotFoundError:
            print("❌ FFmpeg binary not found on this system path.", file=sys.stderr)
            return False
