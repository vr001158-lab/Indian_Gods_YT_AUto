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


def resolve_caption_font(
    language_code: str = "hi-IN",
    explicit_font_path: str | None = None,
    raise_on_missing: bool = True,
) -> str:
    """
    Finds and verifies an appropriate Indic-compatible font across Windows, Linux, and macOS.
    Supports Hindi (Devanagari) and Telugu glyphs with clean verification and explicit overrides.

    Resolution order:
      1. explicit_font_path argument (if provided)
      2. Environment variable overrides (INDIC_FONT_PATH, HINDI_FONT_PATH, TELUGU_FONT_PATH)
      3. Operating system font locations (Windows, Linux, macOS)
      4. Safe Unicode fallback (DejaVuSans, FreeSans)

    Raises
    ------
    FileNotFoundError: If an explicitly configured font path does not exist.
    ValueError: If an unsupported language code is provided.
    RuntimeError: If no suitable font file exists on the system and raise_on_missing is True.
    """
    import os
    from pathlib import Path

    lang = (language_code or "hi-IN").strip()
    if lang not in ("hi-IN", "te-IN", "en", "en-US", "en-IN"):
        raise ValueError(f"Unsupported language code '{language_code}' for Indic font resolution.")

    # 1. Explicit font path parameter
    if explicit_font_path:
        p = Path(explicit_font_path)
        if p.exists() and p.is_file():
            return str(p.resolve()).replace("\\", "/")
        raise FileNotFoundError(f"Explicitly specified font path does not exist: {explicit_font_path}")

    # 2. Environment variable overrides
    env_override = os.environ.get("INDIC_FONT_PATH")
    if not env_override:
        if lang == "hi-IN":
            env_override = os.environ.get("HINDI_FONT_PATH")
        elif lang == "te-IN":
            env_override = os.environ.get("TELUGU_FONT_PATH")

    if env_override:
        p = Path(env_override)
        if p.exists() and p.is_file():
            return str(p.resolve()).replace("\\", "/")
        raise FileNotFoundError(f"Configured font environment variable path does not exist: {env_override}")

    # 3. System font candidates (platform-specific)
    candidates: list[str] = []

    # Windows standard fonts
    if os.name == "nt":
        candidates.extend([
            "C:/Windows/Fonts/Nirmala.ttc",
            "C:/Windows/Fonts/nirmala.ttf",
            "C:/Windows/Fonts/NirmalaB.ttf",
        ])
        if lang == "te-IN":
            candidates.extend([
                "C:/Windows/Fonts/gautami.ttf",
                "C:/Windows/Fonts/gautamib.ttf",
            ])
        elif lang == "hi-IN":
            candidates.extend([
                "C:/Windows/Fonts/mangal.ttf",
                "C:/Windows/Fonts/mangalb.ttf",
                "C:/Windows/Fonts/aparaj.ttf",
            ])
        candidates.extend([
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
        ])

    # Linux (GitHub Actions / Ubuntu) font candidates
    if lang == "te-IN":
        candidates.extend([
            "/usr/share/fonts/truetype/noto/NotoSansTelugu-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansTelugu-Bold.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansTelugu-Regular.otf",
            "/usr/share/fonts/truetype/lohit-telugu/Lohit-Telugu.ttf",
            "/usr/share/fonts/truetype/fonts-telu/Pothana2000.ttf",
            "/usr/share/fonts/truetype/Gidugu.ttf",
        ])
    elif lang == "hi-IN":
        candidates.extend([
            "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansDevanagari-Regular.otf",
            "/usr/share/fonts/truetype/lohit-devanagari/Lohit-Devanagari.ttf",
            "/usr/share/fonts/truetype/Gargi.ttf",
            "/usr/share/fonts/truetype/nakula/nakula.ttf",
        ])

    # Generic Linux fallbacks
    candidates.extend([
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ])

    # macOS candidates
    candidates.extend([
        "/System/Library/Fonts/KohinoorBangla.ttc",
        "/System/Library/Fonts/Supplemental/Nirmala.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
    ])

    for cf in candidates:
        candidate_path = Path(cf)
        if candidate_path.exists() and candidate_path.is_file():
            return str(candidate_path.resolve()).replace("\\", "/")

    if raise_on_missing:
        raise RuntimeError(
            f"No suitable Indic font found on system for '{lang}'. "
            f"Please install fonts-noto-core / fonts-deva / fonts-telu or set HINDI_FONT_PATH / TELUGU_FONT_PATH."
        )

    # Safe return only if raise_on_missing is False
    return "C:/Windows/Fonts/Nirmala.ttc" if os.name == "nt" else "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"


def get_caption_filter(
    caption_text_file: str,
    font_path: str | None = None,
    language_code: str = "hi-IN",
    fontsize: int = 42,
    y_position_ratio: float = 0.72,
) -> str:
    """
    Returns an FFmpeg drawtext filter string for burning captions from a textfile into the video stream.
    Formats text inside YouTube Shorts safe area with a high-contrast dark background box.
    """
    target_font = resolve_caption_font(language_code=language_code, explicit_font_path=font_path)
    escaped_font_path = target_font.replace("\\", "/").replace(":", "\\:")
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
    language_code: str = "hi-IN",
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
        caption_filter = get_caption_filter(caption_text_file, language_code=language_code)
        filter_chain += f",{caption_filter}"

    return filter_chain

