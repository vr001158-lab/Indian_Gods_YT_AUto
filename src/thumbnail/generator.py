# src/thumbnail/generator.py
# Phase 2H — Thumbnail Generation Engine Providers
# Implements PILThumbnailGenerator, MockThumbnailGenerator, and FluxThumbnailGenerator.

import sys
import time
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from src.thumbnail.templates import DEVOTIONAL_GOLD_THEME


class ThumbnailGenerator:
    """Base interface for all thumbnail generator engines."""

    def generate_thumbnail(
        self,
        title: str,
        subtitle: str,
        output_path: Path,
        background_image_path: Path = None,
        theme: dict = DEVOTIONAL_GOLD_THEME,
    ) -> Path:
        """
        Synthesizes a 1280x720 YouTube thumbnail and returns its path.
        """
        raise NotImplementedError("Subclasses must implement generate_thumbnail")


class MockThumbnailGenerator(ThumbnailGenerator):
    """
    Mock Generator creating small deterministic thumbnail images for unit testing.
    """

    def generate_thumbnail(
        self,
        title: str,
        subtitle: str,
        output_path: Path,
        background_image_path: Path = None,
        theme: dict = DEVOTIONAL_GOLD_THEME,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Create a simple 1280x720 solid-color image
        img = Image.new("RGB", (1280, 720), color=(10, 20, 30))
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "MOCK THUMBNAIL", fill=(255, 255, 255))
        draw.text((10, 50), f"Title: {title}", fill=(255, 255, 255))
        img.save(output_path, format="PNG")
        return output_path


class PILThumbnailGenerator(ThumbnailGenerator):
    """
    Production Generator using PIL (Pillow) to design 1280x720 thumbnails.
    Draws backgrounds, renders multi-line titles with shadows, overlays branding tags.
    """

    def _get_font(self, font_name: str, size: int) -> ImageFont:
        """Helper to safely load system fonts or fall back cleanly."""
        try:
            # Try popular fonts depending on OS
            if sys.platform == "win32":
                return ImageFont.truetype("arial.ttf", size)
            else:
                return ImageFont.truetype("LiberationSans-Bold.ttf", size)
        except Exception:
            return ImageFont.load_default()

    def generate_thumbnail(
        self,
        title: str,
        subtitle: str,
        output_path: Path,
        background_image_path: Path = None,
        theme: dict = DEVOTIONAL_GOLD_THEME,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # ── 1. Background Setup ───────────────────────────────────────────────
        if background_image_path and background_image_path.exists():
            try:
                bg = Image.open(background_image_path).convert("RGB")
                # Resize and crop to fill 1280x720 exactly (maintain aspect ratio)
                bg.thumbnail((1280, 1280))
                # Crop center 1280x720
                width, height = bg.size
                left = (width - 1280) / 2
                top = (height - 720) / 2
                right = (width + 1280) / 2
                bottom = (height + 720) / 2
                img = bg.crop((left, top, right, bottom))
            except Exception:
                img = Image.new("RGB", (1280, 720), color=theme["bg_color"])
        else:
            # Create dark gradient fallback background
            img = Image.new("RGB", (1280, 720), color=theme["bg_color"])

        draw = ImageDraw.Draw(img)

        # ── 2. Branding Header Overlay ────────────────────────────────────────
        brand_font = self._get_font("arial.ttf", theme["branding_size"])
        brand_text = theme["branding_text"]
        # Draw branding background block
        draw.rectangle([(50, 40), (450, 80)], fill=(0, 0, 0, 128))
        draw.text((60, 48), brand_text, fill=theme["accent_color"], font=brand_font)

        # ── 3. Multi-line Title Placement ─────────────────────────────────────
        title_font = self._get_font("arial.ttf", theme["title_size"])
        
        # Simple word wrap logic
        words = title.split()
        lines = []
        current_line = []
        for word in words:
            current_line.append(word)
            # Rough check: keep lines to 3-4 words max
            if len(current_line) >= 4:
                lines.append(" ".join(current_line))
                current_line = []
        if current_line:
            lines.append(" ".join(current_line))

        # Render Title text with offset drop-shadow
        y_cursor = 180
        for line in lines[:3]:  # Max 3 lines of title text
            # Draw shadow
            draw.text((63, y_cursor + 3), line, fill=theme["shadow_color"], font=title_font)
            # Draw primary text
            draw.text((60, y_cursor), line, fill=theme["text_color"], font=title_font)
            y_cursor += 70

        # ── 4. Subtitle Hooks ─────────────────────────────────────────────────
        if subtitle:
            sub_font = self._get_font("arial.ttf", theme["subtitle_size"])
            y_cursor += 20
            # Draw shadow
            draw.text((62, y_cursor + 2), subtitle, fill=theme["shadow_color"], font=sub_font)
            # Draw text
            draw.text((60, y_cursor), subtitle, fill=theme["accent_color"], font=sub_font)

        # Save resulting image
        img.save(output_path, format="PNG")
        return output_path


class FluxThumbnailGenerator(ThumbnailGenerator):
    """
    Placeholder AI Generator for Flux.
    Throws NotImplementedError as requested.
    """

    def generate_thumbnail(
        self,
        title: str,
        subtitle: str,
        output_path: Path,
        background_image_path: Path = None,
        theme: dict = DEVOTIONAL_GOLD_THEME,
    ) -> Path:
        raise NotImplementedError("Flux AI Thumbnail generator is not locally implemented.")
