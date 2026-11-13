# src/thumbnail/generator.py
# Phase 2H / Phase 4 — Thumbnail Generation Engine Providers
#
# Implements:
#   - PollinationsThumbnailGenerator: Production provider fetching 16:9 backgrounds
#     exclusively from Pollinations and composing Telugu typography and branding via PIL.
#   - PILThumbnailGenerator: Direct PIL composition engine using local or fetched backgrounds.
#   - MockThumbnailGenerator: Fast deterministic generator for offline unit tests and dry runs.
#   - FluxThumbnailGenerator: Strict stub enforcing that Flux is forbidden for thumbnails.

import sys
import time
from pathlib import Path
from typing import Optional
from PIL import Image, ImageDraw, ImageFont

from src.thumbnail.templates import get_thumbnail_theme, DEVOTIONAL_GOLD_THEME
from src.thumbnail.providers.pollinations import (
    PollinationsProvider,
    build_thumbnail_background_prompt,
)


def _load_indic_font(size: int, language_code: str = "te-IN") -> ImageFont.FreeTypeFont:
    """Helper to safely load Telugu/Indic fonts across repository and system paths."""
    from src.video.effects import resolve_caption_font

    try:
        resolved = resolve_caption_font(language_code, raise_on_missing=False)
        if resolved and Path(resolved).exists():
            return ImageFont.truetype(resolved, size)
    except Exception:
        pass

    # Direct check for bundled repository fonts
    for bf in (
        "assets/fonts/NotoSansTelugu-Variable.ttf",
        "assets/fonts/NotoSansTelugu-Bold.ttf",
        "assets/fonts/NotoSansTelugu-Regular.ttf",
    ):
        p = Path(bf)
        if p.exists() and p.is_file():
            try:
                return ImageFont.truetype(str(p.resolve()), size)
            except Exception:
                pass

    # Windows system font fallbacks
    if sys.platform == "win32":
        for wf in ("C:/Windows/Fonts/Nirmala.ttc", "C:/Windows/Fonts/nirmala.ttf", "arial.ttf"):
            if Path(wf).exists() or wf == "arial.ttf":
                try:
                    return ImageFont.truetype(wf, size)
                except Exception:
                    continue

    return ImageFont.load_default()


def _wrap_text_to_width(text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    """Wraps text into lines that do not exceed max_width in pixels."""
    words = text.strip().split()
    if not words:
        return []
    lines = []
    current_words = []
    for word in words:
        trial = " ".join(current_words + [word])
        bbox = font.getbbox(trial)
        w = bbox[2] - bbox[0]
        if w <= max_width or not current_words:
            current_words.append(word)
        else:
            lines.append(" ".join(current_words))
            current_words = [word]
    if current_words:
        lines.append(" ".join(current_words))
    return lines


def _apply_left_gradient_overlay(base_img: Image.Image, max_x: int = 490, max_alpha: int = 175) -> Image.Image:
    """Applies a smooth dark gradient on the left 35-40% to ensure high text contrast while keeping deity bright."""
    overlay = Image.new("RGBA", base_img.size, (0, 0, 0, 0))
    grad = Image.new("L", (base_img.width, 1))
    grad_bytes = bytearray(base_img.width)
    for x in range(base_img.width):
        if x < max_x:
            alpha = int(max_alpha * ((1.0 - (x / max_x)) ** 1.3))
            grad_bytes[x] = max(0, min(255, alpha))
        else:
            grad_bytes[x] = 0
    grad.frombytes(bytes(grad_bytes))
    mask = grad.resize(base_img.size)
    black_layer = Image.new("RGBA", base_img.size, (12, 10, 16, 255))
    overlay.paste(black_layer, (0, 0), mask=mask)
    return Image.alpha_composite(base_img.convert("RGBA"), overlay).convert("RGB")


class ThumbnailGenerator:
    """Base interface for all thumbnail generator engines."""

    def generate_thumbnail(
        self,
        title: str,
        subtitle: str,
        output_path: Path,
        background_image_path: Optional[Path] = None,
        theme: Optional[dict] = None,
        language_code: str = "te-IN",
        **kwargs,
    ) -> Path:
        raise NotImplementedError("Subclasses must implement generate_thumbnail")


class MockThumbnailGenerator(ThumbnailGenerator):
    """
    Mock Generator creating deterministic 1280x720 thumbnail images for unit testing and dry runs.
    """

    def generate_thumbnail(
        self,
        title: str,
        subtitle: str,
        output_path: Path,
        background_image_path: Optional[Path] = None,
        theme: Optional[dict] = None,
        language_code: str = "te-IN",
        **kwargs,
    ) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (1280, 720), color=(20, 18, 30))
        draw = ImageDraw.Draw(img)
        draw.text((60, 40), "MOCK THUMBNAIL (OFFLINE DRY-RUN)", fill=(255, 215, 0))
        draw.text((60, 80), f"Title: {title}", fill=(255, 255, 255))
        if subtitle:
            draw.text((60, 120), f"Subtitle: {subtitle}", fill=(255, 185, 35))
        img.save(output_path, format="PNG")
        return output_path


class PollinationsThumbnailGenerator(ThumbnailGenerator):
    """
    Production Thumbnail Generator.
    Uses Pollinations as the exclusive AI image generation provider for 16:9 backgrounds.
    Composes Telugu typography, channel branding, and devotional borders using PIL.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
    ):
        self.provider = PollinationsProvider(
            model=model,
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
            max_retries=max_retries,
        )

    def generate_thumbnail(
        self,
        title: str,
        subtitle: str,
        output_path: Path,
        background_image_path: Optional[Path] = None,
        theme: Optional[dict] = None,
        language_code: str = "te-IN",
        **kwargs,
    ) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        active_theme = theme or get_thumbnail_theme(language_code=language_code)

        # ── 1. Background Image Acquisition (Pollinations Exclusive) ───────────
        bg_path = background_image_path
        if bg_path is None or not Path(bg_path).exists():
            deity = kwargs.get("deity", "Divine Deity")
            main_event = kwargs.get("main_event") or title
            emotional_theme = kwargs.get("emotional_theme")
            visual_setting = kwargs.get("visual_setting")

            prompt = build_thumbnail_background_prompt(
                topic=title,
                deity=deity,
                main_event=main_event,
                emotional_theme=emotional_theme,
                visual_setting=visual_setting,
                thumbnail_title=title,
            )

            bg_dir = Path("data/thumbnails/backgrounds")
            bg_dir.mkdir(parents=True, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            bg_path = bg_dir / f"bg_{ts}.png"

            self.provider.generate_background(
                prompt=prompt,
                output_path=bg_path,
                seed=kwargs.get("seed"),
                width=1280,
                height=720,
            )

        # Open and ensure 1280x720 canvas
        try:
            with Image.open(bg_path) as raw_bg:
                bg = raw_bg.convert("RGB")
                if bg.size != (1280, 720):
                    bg = bg.resize((1280, 720), Image.Resampling.LANCZOS)
        except Exception:
            bg = Image.new("RGB", (1280, 720), color=active_theme["bg_color"])

        # ── 2. Atmospheric Left-Side Vignette ──────────────────────────────────
        img = _apply_left_gradient_overlay(bg, max_x=640, max_alpha=190)
        draw = ImageDraw.Draw(img)

        # ── 3. Channel Branding Badge ──────────────────────────────────────────
        branding_text = active_theme.get("branding_text", "దైవ దర్శనం")
        brand_font = _load_indic_font(active_theme.get("branding_size", 24), language_code=language_code)
        
        # Calculate badge pill size
        b_box = brand_font.getbbox(branding_text)
        b_w = (b_box[2] - b_box[0]) + 32
        b_h = (b_box[3] - b_box[1]) + 16

        badge_x, badge_y = 55, 42
        badge_rect = [badge_x, badge_y, badge_x + b_w, badge_y + b_h]
        badge_bg = active_theme.get("badge_bg", (24, 12, 16))
        badge_border = active_theme.get("badge_border", (255, 185, 35))

        draw.rounded_rectangle(badge_rect, radius=6, fill=badge_bg, outline=badge_border, width=2)
        draw.text((badge_x + 16, badge_y + 8), branding_text, fill=badge_border, font=brand_font)

        # ── 4. Telugu Title Layout & Hierarchy ─────────────────────────────────
        branding_text = active_theme.get("branding_text", "దైవ దర్శనం")
        main_title = title.strip()
        supporting_title = (subtitle or "").strip()

        # If title contains separator and supporting title is empty or branding, split cleanly
        if (":" in main_title or " - " in main_title or "\n" in main_title) and (not supporting_title or supporting_title == branding_text):
            if ":" in main_title:
                parts = main_title.split(":", 1)
            elif " - " in main_title:
                parts = main_title.split(" - ", 1)
            else:
                parts = main_title.split("\n", 1)
            main_title = parts[0].strip()
            supporting_title = parts[1].strip()

        # Render Main Title (Bold Sacred Gold)
        main_font_size = active_theme.get("title_size", 54)
        main_font = _load_indic_font(main_font_size, language_code=language_code)
        main_lines = _wrap_text_to_width(main_title, main_font, max_width=450)
        if len(main_lines) > 2:
            main_font_size = 48
            main_font = _load_indic_font(main_font_size, language_code=language_code)
            main_lines = _wrap_text_to_width(main_title, main_font, max_width=460)
        main_lines = main_lines[:3]

        y_cursor = 145
        line_height_main = int(main_font_size * 1.32)
        gold_color = active_theme.get("accent_color", (255, 215, 0))
        white_color = active_theme.get("text_color", (255, 255, 255))
        shadow_color = active_theme.get("shadow_color", (0, 0, 0))

        for line in main_lines:
            # Draw deep drop shadow
            draw.text((59, y_cursor + 4), line, fill=shadow_color, font=main_font)
            # Draw gold main title with thick black stroke outline for mobile readability
            draw.text(
                (55, y_cursor),
                line,
                fill=gold_color,
                font=main_font,
                stroke_width=3,
                stroke_fill=(0, 0, 0),
            )
            y_cursor += line_height_main

        # ── 5. Supporting Title Overlay (Crisp Clean White) ────────────────────
        if supporting_title and supporting_title != branding_text:
            sub_font_size = active_theme.get("subtitle_size", 34)
            sub_font = _load_indic_font(sub_font_size, language_code=language_code)
            sub_lines = _wrap_text_to_width(supporting_title, sub_font, max_width=450)
            y_cursor += 15
            line_height_sub = int(sub_font_size * 1.35)

            for s_line in sub_lines[:3]:
                draw.text((58, y_cursor + 3), s_line, fill=shadow_color, font=sub_font)
                draw.text(
                    (55, y_cursor),
                    s_line,
                    fill=white_color,
                    font=sub_font,
                    stroke_width=2,
                    stroke_fill=(0, 0, 0),
                )
                y_cursor += line_height_sub

        # ── 5.5 Clean Bottom-Right Corner (Duration Safe-Zone & Watermark Clean) ──
        corner_overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        c_draw = ImageDraw.Draw(corner_overlay)
        # Deep vignette falloff over bottom-right margin (matches YouTube badge zone)
        for step in range(35):
            alpha = int(255 * (step / 35.0))
            c_draw.rectangle([(1075 + step, 670), (1280, 720)], fill=(12, 12, 16, alpha))
        img = Image.alpha_composite(img.convert("RGBA"), corner_overlay).convert("RGB")
        draw = ImageDraw.Draw(img)

        # ── 6. Subtle Devotional Border ────────────────────────────────────────
        border_color = active_theme.get("border_color", (212, 175, 55))
        draw.rectangle([(16, 16), (1264, 704)], outline=border_color, width=2)

        # Save resulting composite thumbnail
        img.save(output_path, format="PNG")
        return output_path


class PILThumbnailGenerator(ThumbnailGenerator):
    """
    Backwards-compatible PIL Thumbnail Generator.
    If background_image_path is not supplied, delegates to PollinationsThumbnailGenerator.
    """

    def __init__(self):
        self._pollinations_generator = None

    def _get_pollinations_generator(self) -> PollinationsThumbnailGenerator:
        if self._pollinations_generator is None:
            self._pollinations_generator = PollinationsThumbnailGenerator()
        return self._pollinations_generator

    def generate_thumbnail(
        self,
        title: str,
        subtitle: str,
        output_path: Path,
        background_image_path: Optional[Path] = None,
        theme: Optional[dict] = None,
        language_code: str = "te-IN",
        **kwargs,
    ) -> Path:
        # If no background image provided, synthesize it via Pollinations
        if background_image_path is None or not Path(background_image_path).exists():
            gen = self._get_pollinations_generator()
            return gen.generate_thumbnail(
                title=title,
                subtitle=subtitle,
                output_path=output_path,
                background_image_path=background_image_path,
                theme=theme,
                language_code=language_code,
                **kwargs,
            )

        # If background image is already provided, use Pollinations composition engine
        gen = self._get_pollinations_generator()
        return gen.generate_thumbnail(
            title=title,
            subtitle=subtitle,
            output_path=output_path,
            background_image_path=background_image_path,
            theme=theme,
            language_code=language_code,
            **kwargs,
        )


class FluxThumbnailGenerator(ThumbnailGenerator):
    """
    Strict architectural prohibition:
    Flux is exclusively reserved for video scene generation.
    Thumbnails must exclusively use Pollinations for backgrounds.
    """

    def generate_thumbnail(
        self,
        title: str,
        subtitle: str,
        output_path: Path,
        background_image_path: Optional[Path] = None,
        theme: Optional[dict] = None,
        language_code: str = "te-IN",
        **kwargs,
    ) -> Path:
        raise NotImplementedError(
            "Flux AI image generation is reserved exclusively for video scenes and is strictly "
            "prohibited for YouTube thumbnails. Pollinations is the exclusive thumbnail image provider."
        )


class ThumbnailReuseGenerator(ThumbnailGenerator):
    """
    Zero-Cost Thumbnail Generation Engine prioritizing verified local artwork and video frames.
    Follows strict 4-priority selection chain and falls back to Pollinations anonymous generation.
    """

    def __init__(self):
        from src.thumbnail.reuse_engine import ThumbnailReuseEngine
        self.engine = ThumbnailReuseEngine()

    def generate_thumbnail(
        self,
        title: str,
        subtitle: str,
        output_path: Path,
        background_image_path: Optional[Path] = None,
        theme: Optional[dict] = None,
        language_code: str = "te-IN",
        **kwargs,
    ) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # If an explicit background path is already passed, compose directly
        if background_image_path and Path(background_image_path).exists():
            from src.thumbnail.composer import compose_reused_thumbnail
            return compose_reused_thumbnail(
                background_path=Path(background_image_path),
                title=title,
                subtitle=subtitle,
                output_path=output_path,
                language_code=language_code,
                theme=theme,
            )

        visual_map = kwargs.get("visual_map_path")
        video_p = kwargs.get("video_path")
        if not visual_map:
            for candidate in [Path("data/render_only"), Path("data/visuals")]:
                if candidate.exists():
                    found = list(candidate.glob("**/visual_map_*.json")) or list(candidate.glob("**/visual_map.json"))
                    if found:
                        found.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                        visual_map = found[0]
                        break
        if not video_p:
            for candidate in [Path("data/render_only"), Path("data/videos")]:
                if candidate.exists():
                    found = list(candidate.glob("**/video_*.mp4")) or list(candidate.glob("**/video.mp4"))
                    if found:
                        found.sort(key=lambda p: p.stat().st_mtime, reverse=True)
                        video_p = found[0]
                        break

        res = self.engine.generate(
            topic=kwargs.get("main_event") or title,
            script_title=title,
            subtitle=subtitle,
            deity=kwargs.get("deity"),
            avatar=kwargs.get("avatar"),
            visual_map_path=visual_map,
            video_path=video_p,
            output_image_path=output_path,
            language_code=language_code,
            allow_pollinations_fallback=kwargs.get("allow_pollinations_fallback", True),
        )
        return output_path

