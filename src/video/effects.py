# src/video/effects.py
# Phase 2G/Phase 4 — FFmpeg Filtergraph Effects (Ken Burns, Fades, Scaling)


def get_ken_burns_filter(
    fps: int = 25,
    zoom_speed: float = 0.0005,
    max_zoom: float = 1.25,
    width: int = 1080,
    height: int = 1920,
    motion_type: str = "zoom_in",
    duration_seconds: float = 5.0,
) -> str:
    """
    Returns an FFmpeg zoompan filter string simulating a Ken Burns effect.
    Supports motion_type: 'zoom_in', 'zoom_out', 'pan_left', 'pan_right'.
    """
    total_frames = max(1, int(duration_seconds * fps))
    if motion_type == "zoom_out":
        return (
            f"zoompan=z='max({max_zoom}-{zoom_speed}*on,1.0)':"
            f"x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':"
            f"d=1:s={width}x{height}"
        )
    elif motion_type == "pan_left":
        return (
            f"zoompan=z='1.15':"
            f"x='(iw-iw/zoom)*(1-on/{total_frames})':"
            f"y='ih/2-(ih/zoom/2)':"
            f"d=1:s={width}x{height}"
        )
    elif motion_type == "pan_right":
        return (
            f"zoompan=z='1.15':"
            f"x='(iw-iw/zoom)*(on/{total_frames})':"
            f"y='ih/2-(ih/zoom/2)':"
            f"d=1:s={width}x{height}"
        )
    else:  # zoom_in (default)
        return (
            f"zoompan=z='min(zoom+{zoom_speed},{max_zoom})':"
            f"x='iw/2-(iw/zoom/2)':"
            f"y='ih/2-(ih/zoom/2)':"
            f"d=1:s={width}x{height}"
        )


def get_fade_in_out_filter(duration_seconds: int, fade_duration: float = 0.5) -> str:
    """
    Returns an FFmpeg filter string adding a fade-in at start and fade-out at end.
    """
    fade_in = f"fade=t=in:st=0:d={fade_duration}"
    fade_out = f"fade=t=out:st={duration_seconds - fade_duration}:d={fade_duration}"
    return f"{fade_in},{fade_out}"


def get_caption_filter(
    caption_text_file: str,
    font_path: str = "C:/Windows/Fonts/Nirmala.ttc",
    fontsize: int = 42,
    y_position_ratio: float = 0.72,
) -> str:
    """
    Returns an FFmpeg drawtext filter string for burning captions from a textfile into the video stream.
    Formats text inside YouTube Shorts safe area with a high-contrast dark background box.
    """
    escaped_font_path = font_path.replace("\\", "/").replace(":", "\\:")
    escaped_text_path = caption_text_file.replace("\\", "/").replace(":", "\\:")
    return (
        f"drawtext=fontfile='{escaped_font_path}':"
        f"textfile='{escaped_text_path}':"
        f"fontsize={fontsize}:"
        f"fontcolor=white:"
        f"box=1:boxcolor=black@0.65:boxborderw=12:"
        f"line_spacing=10:"
        f"x=(w-text_w)/2:y=h*{y_position_ratio}"
    )


def get_video_filtergraph_for_scene(
    duration_seconds: int,
    fps: int = 25,
    width: int = 1080,
    height: int = 1920,
    motion_type: str = "zoom_in",
    caption_text_file: str | None = None,
) -> str:
    """
    Combines scale, SAR normalization, Ken Burns, fades, and optional captions into a single FFmpeg filter chain for a scene.
    `setsar=1` ensures uniform square pixel sample aspect ratio across all input images for FFmpeg concat.
    """
    # 1. Scale input to widthxheight using force_original_aspect_ratio and pad with black borders
    scale_crop = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
        f"setsar=1"
    )
    # 2. Add Ken Burns
    kb = get_ken_burns_filter(fps=fps, zoom_speed=0.0005, max_zoom=1.25, width=width, height=height, motion_type=motion_type, duration_seconds=duration_seconds)
    # 3. Add fades
    fade = get_fade_in_out_filter(duration_seconds=duration_seconds)

    filter_chain = f"{scale_crop},{kb},{fade}"

    # 4. Add captions if provided
    if caption_text_file:
        caption_filter = get_caption_filter(caption_text_file)
        filter_chain += f",{caption_filter}"

    return filter_chain

