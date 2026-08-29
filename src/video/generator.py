# src/video/generator.py
# Phase 2G/Phase 4 — Video Composer Engine Pipeline
# Matches timing maps, invokes rendering engine, validates results with ffprobe & video QA.
#
# Phase 2G+ adds first-class content_type support (short / long).
# All resolution and duration constants are sourced from format_config — never
# hard-coded here.

import json
import subprocess
import time
from pathlib import Path

from src.video.format_config import (
    DEFAULT_CONTENT_TYPE,
    get_format_config,
    validate_content_type,
    validate_duration_for_content_type,
    validate_resolution_for_content_type,
)
from src.video.schemas import validate_input_maps, validate_output_video_map
from src.video.composer import MockVideoComposer, FFmpegVideoComposer

COMPOSERS = {
    "mock": MockVideoComposer,
    "ffmpeg": FFmpegVideoComposer,
}


def validate_video_file_with_ffprobe(
    video_path: Path,
    *,
    allow_mock: bool = False,
    expected_resolution: str | None = None,
    content_type: str = DEFAULT_CONTENT_TYPE,
) -> tuple:
    """
    Validates the generated video file using ffprobe and ffmpeg decode.

    Parameters
    ----------
    allow_mock : bool
        If True, files starting with MOCK_MP4_VIDEO pass immediately.
        ONLY unit tests may set this to True.
        Production callers MUST leave this False (default).
    content_type : str
        "short" or "long".  Determines which resolutions and duration
        bounds are considered valid.  Defaults to "short" for backwards
        compatibility with callers that predate format-awareness.
    expected_resolution : str | None
        If supplied, the actual resolution must match exactly (legacy
        override; content_type check is preferred).
    """
    if not video_path.exists():
        return False, f"Video file not found: {video_path}"

    if video_path.stat().st_size == 0:
        return False, "Video file is empty (zero-byte)"

    # Detect mock/text files
    try:
        header = video_path.read_bytes()[:64]
        if header.startswith(b"MOCK_MP4_VIDEO"):
            if allow_mock:
                return True, "mock video accepted (test mode)"
            return False, "Mock video artifact is not valid for production publishing"
    except Exception:
        pass

    # Validate content_type
    ok_ct, ct_err = validate_content_type(content_type)
    if not ok_ct:
        return False, f"Invalid content_type passed to ffprobe validator: {ct_err}"

    fmt_cfg = get_format_config(content_type)
    expected_res = expected_resolution or fmt_cfg["resolution"]

    # ── ffprobe: query streams ────────────────────────────────────────────
    cmd = [
        "ffprobe", "-v", "error",
        "-show_streams", "-show_format",
        "-of", "json",
        str(video_path.absolute())
    ]
    try:
        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=30, encoding="utf-8", errors="replace",
        )
        if result.returncode != 0:
            return False, f"ffprobe failed (exit {result.returncode}): {result.stderr[:200]}"

        probe = json.loads(result.stdout)
    except FileNotFoundError:
        return False, "ffprobe binary not found — cannot validate video for production"
    except json.JSONDecodeError as exc:
        return False, f"ffprobe returned unparseable JSON: {exc}"
    except Exception as exc:
        return False, f"ffprobe error: {exc}"

    streams = probe.get("streams", [])
    video_streams = [s for s in streams if s.get("codec_type") == "video"]
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

    if not video_streams:
        return False, "No video stream found"
    if not audio_streams:
        return False, "No audio stream found"

    vs = video_streams[0]
    codec   = vs.get("codec_name", "")
    pix_fmt = vs.get("pix_fmt", "")
    width   = vs.get("width", 0)
    height  = vs.get("height", 0)

    if codec != "h264":
        return False, f"Invalid codec: expected h264, got {codec}"
    if pix_fmt not in ("yuv420p", "yuvj420p"):
        return False, f"Invalid pixel format: expected yuv420p, got {pix_fmt}"

    # ── Format-aware resolution check ────────────────────────────────────
    actual_res = f"{width}x{height}"
    ok_res, res_err = validate_resolution_for_content_type(actual_res, content_type)
    if not ok_res:
        return False, res_err

    # Legacy explicit override (additional strictness, not relaxation)
    if expected_resolution and actual_res != expected_resolution:
        return False, f"Resolution mismatch: expected {expected_resolution}, got {actual_res}"

    # Audio checks (full strictness for production profile)
    as_stream = audio_streams[0]
    a_codec = as_stream.get("codec_name", "")
    a_rate = int(as_stream.get("sample_rate", 0) or 0)
    a_ch = int(as_stream.get("channels", 0) or 0)

    if fmt_cfg.get("audio_codec") and a_codec:
        if a_codec != fmt_cfg["audio_codec"]:
            return False, f"Invalid audio codec: expected {fmt_cfg['audio_codec']}, got {a_codec}"
    if fmt_cfg.get("audio_sample_rate") and a_rate > 0:
        if a_rate != fmt_cfg["audio_sample_rate"]:
            return False, f"Invalid audio sample rate: expected {fmt_cfg['audio_sample_rate']} Hz, got {a_rate} Hz"
    if fmt_cfg.get("audio_channels") and a_ch > 0:
        if a_ch != fmt_cfg["audio_channels"]:
            return False, f"Invalid audio channels: expected {fmt_cfg['audio_channels']} (stereo), got {a_ch}"

    # Duration
    duration = float(probe.get("format", {}).get("duration", 0) or 0)
    if duration <= 0:
        duration = float(vs.get("duration", 0) or 0)
    if duration <= 0:
        return False, f"Video duration is not positive: {duration}"

    # ── ffmpeg decode test ────────────────────────────────────────────────
    try:
        decode_result = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(video_path.absolute()), "-f", "null", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, timeout=120, encoding="utf-8", errors="replace",
        )
        if decode_result.returncode != 0:
            return False, f"FFmpeg decode test failed: {decode_result.stderr[:200]}"
    except FileNotFoundError:
        return False, "FFmpeg binary not found — cannot perform decode validation"
    except Exception as exc:
        return False, f"FFmpeg decode error: {exc}"

    return True, (
        f"OK (duration={duration:.1f}s, {width}x{height}, {codec}, "
        f"{pix_fmt}, audio={a_codec}/{a_rate}Hz/{a_ch}ch, "
        f"content_type={content_type})"
    )


def perform_video_qa(
    video_path: Path,
    expected_duration: float | None = None,
    *,
    allow_mock: bool = False,
    content_type: str = DEFAULT_CONTENT_TYPE,
) -> dict:
    """
    Performs comprehensive Video QA checks on the rendered video file.

    Validates:
      - file exists and is non-zero
      - valid MP4 container / H264 / yuv420p
      - video stream exists with the correct resolution for *content_type*
      - audio stream exists with the correct codec/rate/channels
      - duration > 0 and within bounds for *content_type*
      - duration matches audio narration (if expected_duration provided)
      - FFmpeg decode test (no corruption)

    Raises ValueError if any QA check fails.
    """
    ok, detail = validate_video_file_with_ffprobe(
        video_path,
        allow_mock=allow_mock,
        content_type=content_type,
    )
    if not ok:
        raise ValueError(f"❌ Video QA Rejection for {video_path.name}: {detail}")

    if allow_mock:
        return {
            "valid": True,
            "file_name": video_path.name,
            "detail": detail,
            "content_type": content_type,
            "mock": True,
        }

    cmd = [
        "ffprobe", "-v", "error",
        "-show_streams", "-show_format",
        "-of", "json",
        str(video_path.absolute())
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    probe = json.loads(res.stdout)

    fmt = probe.get("format", {})
    duration = float(fmt.get("duration", 0) or 0)
    size = int(fmt.get("size", 0) or video_path.stat().st_size)

    streams = probe.get("streams", [])
    vs = [s for s in streams if s.get("codec_type") == "video"][0]
    as_stream = [s for s in streams if s.get("codec_type") == "audio"][0]

    # ── Duration bounds check for content_type ────────────────────────────
    ok_dur, dur_err = validate_duration_for_content_type(duration, content_type)
    if not ok_dur:
        raise ValueError(f"❌ Video QA Duration Bounds: {dur_err}")

    duration_diff = 0.0
    if expected_duration is not None and expected_duration > 0:
        duration_diff = abs(duration - expected_duration)
        if duration_diff > 1.5:
            raise ValueError(
                f"❌ Video QA Duration Mismatch: video duration ({duration:.2f}s) "
                f"differs from audio narration ({expected_duration:.2f}s) by {duration_diff:.2f}s (>1.5s)"
            )

    fmt_cfg = get_format_config(content_type)

    return {
        "valid": True,
        "file_name": video_path.name,
        "file_size_bytes": size,
        "container": fmt.get("format_name", "mp4"),
        "duration_seconds": round(duration, 2),
        "expected_audio_duration": round(expected_duration, 2) if expected_duration else None,
        "duration_diff_seconds": round(duration_diff, 2),
        "video_codec": vs.get("codec_name", ""),
        "pixel_format": vs.get("pix_fmt", ""),
        "resolution": f"{vs.get('width')}x{vs.get('height')}",
        "audio_codec": as_stream.get("codec_name", ""),
        "audio_channels": as_stream.get("channels", 1),
        "audio_sample_rate": int(as_stream.get("sample_rate", 0) or 0),
        "no_corruption": True,
        "content_type": content_type,
        "aspect_ratio": fmt_cfg["aspect_ratio"],
    }


def create_visual_map_from_asset_plan(
    asset_plan_path: Path,
    audio_map: dict,
) -> dict:
    """
    Adapts the shared visual asset plan to a specific language audio map by
    recalculating scene durations to match the actual narration audio duration
    for each scene.

    The visual asset plan is the single source of truth for deity image identity.
    NO new asset plans are created. NO online fallbacks. NO random asset selections.
    """
    if not asset_plan_path.exists():
        raise FileNotFoundError(f"Shared asset plan file not found: {asset_plan_path}")

    asset_plan = json.loads(asset_plan_path.read_text(encoding="utf-8"))
    plan_scenes = asset_plan.get("scenes", [])
    audio_scenes = audio_map.get("audio_scenes", [])

    if not plan_scenes:
        raise ValueError(f"Asset plan {asset_plan_path.name} contains no scenes")
    if not audio_scenes:
        raise ValueError("audio_map contains no audio_scenes")

    if len(plan_scenes) != len(audio_scenes):
        raise ValueError(
            f"Scene count mismatch between asset plan ({len(plan_scenes)}) "
            f"and audio map ({len(audio_scenes)})"
        )

    visual_scenes = []
    for i, a_sc in enumerate(audio_scenes):
        p_sc = plan_scenes[i]
        asset_file = p_sc["asset"]
        asset_path = Path(asset_file)

        if not asset_path.exists():
            raise FileNotFoundError(
                f"Missing repository visual asset for scene {a_sc['scene']}: {asset_file}"
            )
        if asset_path.stat().st_size == 0:
            raise ValueError(
                f"Repository visual asset for scene {a_sc['scene']} is empty (0 bytes): {asset_file}"
            )

        asset_type = p_sc.get("asset_type", "image")
        source = p_sc.get("source", "repository")
        scene_duration = a_sc["duration_seconds"]

        visual_scenes.append({
            "scene": a_sc["scene"],
            "visual_prompt": f"Scene #{a_sc['scene']}: {asset_type} asset from {source}",
            "image_file": str(asset_path.absolute()).replace("\\", "/"),
            "asset_type": asset_type,
            "source": source,
            "style": "Devotional Cinematic Painting, 8k, divine golden glow",
            "duration_seconds": scene_duration,
        })

    run_id = audio_map.get("run_id", "run_shared_asset_plan")
    title = audio_map.get("script_title") or asset_plan.get("topic", "")

    visual_map = {
        "run_id": run_id,
        "script_title": title,
        "total_scenes": len(visual_scenes),
        "style_preset": "Devotional Cinematic Painting, 8k, divine golden glow",
        "provider": "repository",
        "asset_plan_path": str(asset_plan_path.absolute()).replace("\\", "/"),
        "visual_scenes": visual_scenes,
        "approval_metadata": audio_map.get("approval_metadata", asset_plan.get("approval_metadata", {})),
    }

    return visual_map


def compose_video_pipeline(
    audio_map: dict,
    visual_map: dict,
    composer_type: str = "ffmpeg",
    background_music: Path = None,
    bgm_volume: float = 0.15,
    output_dir: Path = Path("data/videos"),
    resolution: str | None = None,
    output_file_name: str | None = None,
    content_type: str = DEFAULT_CONTENT_TYPE,
) -> dict:
    """
    Executes the video composition orchestration pipeline.
    Combines input maps, resolves dependencies, matches paths, compiles video, and validates.

    Parameters
    ----------
    content_type : str
        "short" (default, 1080x1920) or "long" (1920x1080).
        Determines resolution, duration bounds, and output map metadata.
    resolution : str | None
        Override resolution string. If None, derived from *content_type*.
        Provided for backwards-compatibility; prefer content_type.

    Raises ValueError if inputs fail safety checks.
    """
    # Validate content_type first — fail fast
    ok_ct, ct_err = validate_content_type(content_type)
    if not ok_ct:
        raise ValueError(f"❌ Invalid content_type: {ct_err}")

    fmt_cfg = get_format_config(content_type)

    # Derive resolution from content_type unless explicitly overridden
    if resolution is None:
        resolution = fmt_cfg["resolution"]

    # Ensure explicit resolution matches declared content_type
    ok_res, res_err = validate_resolution_for_content_type(resolution, content_type)
    if not ok_res:
        raise ValueError(f"❌ Resolution/content_type mismatch: {res_err}")

    ok, error_msg = validate_input_maps(audio_map, visual_map)
    if not ok:
        raise ValueError(f"❌ Safety Gate Rejection: {error_msg}")

    if composer_type not in COMPOSERS:
        raise ValueError(f"Unknown video composer: {composer_type} (must be one of {list(COMPOSERS.keys())})")

    scenes = []
    total_duration = 0

    audio_scenes = audio_map["audio_scenes"]
    visual_scenes = visual_map["visual_scenes"]

    for i in range(len(audio_scenes)):
        a_sc = audio_scenes[i]
        v_sc = visual_scenes[i]

        if a_sc["scene"] != v_sc["scene"]:
            raise ValueError(f"Mismatched scenes at index {i}: audio is {a_sc['scene']}, visual is {v_sc['scene']}")

        img_path = Path(v_sc["image_file"])
        aud_path = Path(a_sc["audio_file"])

        if not img_path.exists():
            raise FileNotFoundError(f"Missing visual asset for scene {a_sc['scene']}: {img_path}")
        if not aud_path.exists():
            raise FileNotFoundError(f"Missing audio asset for scene {a_sc['scene']}: {aud_path}")

        if img_path.stat().st_size == 0:
            raise ValueError(f"Visual asset for scene {a_sc['scene']} is empty (zero-byte): {img_path}")
        if aud_path.stat().st_size == 0:
            raise ValueError(f"Audio asset for scene {a_sc['scene']} is empty (zero-byte): {aud_path}")

        duration = a_sc["duration_seconds"]
        total_duration += duration

        is_old_format = (audio_map.get("format") == "old" or audio_map.get("audio_type") == "music_only")
        scenes.append({
            "scene":            a_sc["scene"],
            "image_file":       str(img_path.absolute()).replace("\\", "/"),
            "audio_file":       str(aud_path.absolute()).replace("\\", "/"),
            "duration_seconds": duration,
            "voice_text":       "" if is_old_format else a_sc.get("voice_text", ""),
        })

    output_dir.mkdir(parents=True, exist_ok=True)
    if output_file_name:
        video_file = output_dir / output_file_name
        base_stem = video_file.stem
        video_map_file = output_dir / f"{base_stem}_map.json"
    else:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        video_file = output_dir / f"video_{content_type}_{timestamp}.mp4"
        video_map_file = output_dir / f"video_map_{content_type}_{timestamp}.json"

    composer = COMPOSERS[composer_type]()
    success = composer.compose_video(
        scenes=scenes,
        output_file=video_file,
        background_music=background_music,
        bgm_volume=bgm_volume,
        resolution=resolution,
    )

    if not success:
        raise RuntimeError("❌ Video rendering engine failed composition step")

    ok_probe, err_probe = validate_video_file_with_ffprobe(
        video_file,
        allow_mock=(composer_type == "mock"),
        content_type=content_type,
        expected_resolution=resolution,
    )
    if not ok_probe:
        raise RuntimeError(f"❌ Video validation check failed: {err_probe}")

    output_map = {
        "video_file":       str(video_file.absolute()).replace("\\", "/"),
        "video_map_file":   str(video_map_file.absolute()).replace("\\", "/"),
        "total_duration":   total_duration,
        "resolution":       resolution,
        "content_type":     content_type,
        "aspect_ratio":     fmt_cfg["aspect_ratio"],
        "scenes":           scenes,
        "approval_metadata": audio_map["approval_metadata"],
    }

    ok_out, err_out = validate_output_video_map(output_map)
    if not ok_out:
        raise RuntimeError(f"❌ Internal Error: Composed video mapping fails schema: {err_out}")

    return output_map


def render_multilingual_video(
    language_code: str,
    audio_map_path: Path,
    asset_plan_path: Path,
    output_video_path: Path,
    composer_type: str = "ffmpeg",
    background_music: Path = None,
    bgm_volume: float = 0.15,
    resolution: str = "1080x1920",
    content_type: str = DEFAULT_CONTENT_TYPE,
) -> dict:
    """
    Phase 4 Multilingual Video Renderer.

    Inputs:
      - language_code: hi-IN, te-IN, or ta-IN
      - audio_map_path: Path to the Edge Neural TTS audio map JSON for this language
      - asset_plan_path: Path to the shared visual asset plan
      - output_video_path: Output MP4 destination
      - content_type: "short" (default) or "long"

    Workflow:
      1. Read language audio_map.
      2. Adapt shared asset_plan into language visual_map.
      3. Compose MP4 at the resolution for content_type.
      4. Run strict Video QA validation.
      5. Return output video map dict with embedded `video_qa` details.
    """
    if not audio_map_path.exists():
        raise FileNotFoundError(f"Audio map file not found: {audio_map_path}")

    # Validate content_type early
    ok_ct, ct_err = validate_content_type(content_type)
    if not ok_ct:
        raise ValueError(f"Invalid content_type: {ct_err}")

    fmt_cfg = get_format_config(content_type)

    # If caller supplied an explicit resolution, verify it matches content_type
    ok_res, res_err = validate_resolution_for_content_type(resolution, content_type)
    if not ok_res:
        raise ValueError(res_err)

    audio_map = json.loads(audio_map_path.read_text(encoding="utf-8"))

    if audio_map.get("language_code") and audio_map["language_code"] != language_code:
        raise ValueError(
            f"Language code mismatch: expected '{language_code}', "
            f"audio map has '{audio_map['language_code']}'"
        )

    visual_map = create_visual_map_from_asset_plan(asset_plan_path, audio_map)

    output_dir = output_video_path.parent
    output_name = output_video_path.name

    video_map = compose_video_pipeline(
        audio_map=audio_map,
        visual_map=visual_map,
        composer_type=composer_type,
        background_music=background_music,
        bgm_volume=bgm_volume,
        output_dir=output_dir,
        resolution=resolution,
        output_file_name=output_name,
        content_type=content_type,
    )

    vmap_file = Path(video_map["video_map_file"])
    vmap_file.write_text(
        json.dumps(video_map, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # The expected duration for the composed video is the sum of audio scenes
    expected_dur = float(audio_map.get("total_duration_seconds", 0))

    video_qa = perform_video_qa(
        output_video_path,
        expected_duration=expected_dur,
        allow_mock=(composer_type == "mock"),
        content_type=content_type,
    )

    video_map["video_qa"] = video_qa
    video_map["language_code"] = language_code

    return video_map


def process_mapping_files(
    audio_map_path: Path,
    visual_map_path: Path,
    composer_type: str = "ffmpeg",
    background_music: Path = None,
    bgm_volume: float = 0.15,
    output_dir: Path = Path("data/videos"),
    resolution: str | None = None,
    content_type: str = DEFAULT_CONTENT_TYPE,
) -> Path:
    """
    Loads timing maps from paths, runs composition, and saves the output mapping JSON.

    *content_type* defaults to "short" for full backwards compatibility
    (old callers that don't pass content_type continue to produce Shorts).
    """
    if not audio_map_path.exists():
        raise FileNotFoundError(f"Audio map file not found: {audio_map_path}")
    if not visual_map_path.exists():
        raise FileNotFoundError(f"Visual map file not found: {visual_map_path}")

    try:
        audio_map = json.loads(audio_map_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise ValueError(f"Failed to parse audio map JSON: {e}")

    try:
        visual_map = json.loads(visual_map_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise ValueError(f"Failed to parse visual map JSON: {e}")

    output_map = compose_video_pipeline(
        audio_map=audio_map,
        visual_map=visual_map,
        composer_type=composer_type,
        background_music=background_music,
        bgm_volume=bgm_volume,
        output_dir=output_dir,
        resolution=resolution,
        content_type=content_type,
    )

    out_file = Path(output_map["video_map_file"])
    out_file.write_text(
        json.dumps(output_map, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )

    return out_file
