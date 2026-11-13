# src/thumbnail/composer.py
# Phase 2H / Phase 4 — High-Quality Devotional Thumbnail PIL Composer
#
# Composes production 1280x720 thumbnails from any source aspect ratio:
#   - Landscape (16:9): Intelligent framing with subject center-right.
#   - Vertical (9:16) or Square (1:1): Blurred devotional background extension with crisp,
#     unstretched deity foreground centered-right.
#   - Strict left 35–40% typography confinement with zero overlap on the deity.
#   - Noto Sans Telugu typography (Gold main title, white subtitle).
#   - Channel branding badge: 'దైవ దర్శనం'.
#   - Devotional gold border and clean YouTube duration-badge safe margins.

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Any
from PIL import Image, ImageDraw, ImageFont, ImageFilter

from src.thumbnail.templates import get_thumbnail_theme


def _load_indic_font(size: int, language_code: str = "te-IN") -> ImageFont.FreeTypeFont:
    """Helper to safely load Telugu/Indic fonts across repository and system paths."""
    from src.video.effects import resolve_caption_font

    try:
        resolved = resolve_caption_font(language_code, raise_on_missing=False)
        if resolved and Path(resolved).exists():
            return ImageFont.truetype(resolved, size)
    except Exception:
        pass

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


def _apply_left_gradient_overlay(base_img: Image.Image, max_x: int = 490, max_alpha: int = 180) -> Image.Image:
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


def prepare_background_canvas(source_image: Image.Image, target_width: int = 1280, target_height: int = 720) -> Image.Image:
    """
    Intelligently adapts any source image (landscape, portrait 9:16, or square) to a 1280x720 canvas:
      - 16:9 source: Cropped/scaled with subject kept slightly center-right to leave text room on left.
      - 9:16 portrait source: Extends background using a rich blurred version of the image, placing the
        un-stretched foreground deity in the center-right (width: 480-1280), keeping faces sharp.
    """
    src = source_image.convert("RGB")
    src_w, src_h = src.size
    aspect = src_w / float(src_h)
    target_aspect = target_width / float(target_height)  # 1.777

    # 1. Near 16:9 landscape (1.6 to 1.9)
    if 1.60 <= aspect <= 1.90:
        # Scale to fill target dimensions
        scale = max(target_width / src_w, target_height / src_h)
        new_w = int(src_w * scale)
        new_h = int(src_h * scale)
        scaled = src.resize((new_w, new_h), Image.Resampling.LANCZOS)
        # Center-crop
        left = max(0, (new_w - target_width) // 2)
        top = max(0, (new_h - target_height) // 2)
        return scaled.crop((left, top, left + target_width, top + target_height))

    # 2. Vertical 9:16 or non-16:9 source (Aspect ratio extension)
    # Create blurred devotional background
    bg_blurred = src.resize((target_width, target_height), Image.Resampling.BILINEAR)
    bg_blurred = bg_blurred.filter(ImageFilter.GaussianBlur(radius=28))
    # Darken blurred background slightly
    darkener = Image.new("RGBA", (target_width, target_height), (10, 8, 14, 110))
    bg_composite = Image.alpha_composite(bg_blurred.convert("RGBA"), darkener).convert("RGB")

    # Fit foreground image maintaining aspect ratio
    fg_scale = (target_height - 20) / float(src_h)
    fg_w = int(src_w * fg_scale)
    fg_h = int(src_h * fg_scale)
    fg_scaled = src.resize((fg_w, fg_h), Image.Resampling.LANCZOS)

    # Position foreground toward center-right (leaving left 35-40% clear for typography)
    pos_x = min(target_width - fg_w - 20, max(460, target_width - fg_w - 40))
    pos_y = (target_height - fg_h) // 2

    # Paste foreground onto blurred backdrop
    bg_composite.paste(fg_scaled, (pos_x, pos_y))
    return bg_composite


def compose_reused_thumbnail(
    background_path: Path,
    title: str,
    subtitle: str,
    output_path: Path,
    language_code: str = "te-IN",
    theme: Optional[dict] = None,
) -> Path:
    """
    Renders complete production thumbnail from an indexed artwork or video frame:
      - 1280x720 PNG
      - Intelligent composition & safe margins
      - Telugu typography & branding badge
      - Devotional gold border
    """
    out_p = Path(output_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    active_theme = theme or get_thumbnail_theme(language_code=language_code)

    # 1. Load and prepare background canvas
    with Image.open(background_path) as raw_img:
        bg = prepare_background_canvas(raw_img, 1280, 720)

    # 2. Apply left-side atmospheric gradient overlay
    img = _apply_left_gradient_overlay(bg, max_x=510, max_alpha=180)
    draw = ImageDraw.Draw(img)

    # 3. Channel Branding Badge
    branding_text = active_theme.get("branding_text", "దైవ దర్శనం")
    brand_font = _load_indic_font(active_theme.get("branding_size", 24), language_code=language_code)
    b_box = brand_font.getbbox(branding_text)
    b_w = (b_box[2] - b_box[0]) + 32
    b_h = (b_box[3] - b_box[1]) + 16
    badge_x, badge_y = 55, 42
    badge_rect = [badge_x, badge_y, badge_x + b_w, badge_y + b_h]
    badge_bg = active_theme.get("badge_bg", (24, 12, 16))
    badge_border = active_theme.get("badge_border", (255, 185, 35))

    draw.rounded_rectangle(badge_rect, radius=6, fill=badge_bg, outline=badge_border, width=2)
    draw.text((badge_x + 16, badge_y + 8), branding_text, fill=badge_border, font=brand_font)

    # 4. Telugu Title Layout & Typography
    main_title = title.strip()
    supporting_title = (subtitle or "").strip()

    if (":" in main_title or " - " in main_title or "\n" in main_title) and (not supporting_title or supporting_title == branding_text):
        if ":" in main_title:
            parts = main_title.split(":", 1)
        elif " - " in main_title:
            parts = main_title.split(" - ", 1)
        else:
            parts = main_title.split("\n", 1)
        main_title = parts[0].strip()
        supporting_title = parts[1].strip()

    # Main Title (Sacred Gold with black outline)
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
        draw.text((59, y_cursor + 4), line, fill=shadow_color, font=main_font)
        draw.text(
            (55, y_cursor),
            line,
            fill=gold_color,
            font=main_font,
            stroke_width=3,
            stroke_fill=(0, 0, 0),
        )
        y_cursor += line_height_main

    # 5. Supporting Subtitle (Clean White with black outline)
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

    # 6. Bottom-Right Duration Badge Clean Margin
    corner_overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    c_draw = ImageDraw.Draw(corner_overlay)
    for step in range(35):
        alpha = int(255 * (step / 35.0))
        c_draw.rectangle([(1075 + step, 670), (1280, 720)], fill=(12, 12, 16, alpha))
    img = Image.alpha_composite(img.convert("RGBA"), corner_overlay).convert("RGB")
    draw = ImageDraw.Draw(img)

    # 7. Subtle Devotional Gold Border
    border_color = active_theme.get("border_color", (212, 175, 55))
    draw.rectangle([(16, 16), (1264, 704)], outline=border_color, width=2)

    # Save output
    img.save(out_p, format="PNG")
    return out_p
