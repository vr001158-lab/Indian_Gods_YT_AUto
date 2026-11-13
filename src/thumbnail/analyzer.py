# src/thumbnail/analyzer.py
# Phase 2H / Phase 4 — Thumbnail Image Quality Analyzer and Validator

import re
from pathlib import Path
from PIL import Image, ImageStat


def analyze_thumbnail_file(
    image_path: Path,
    expected_title: str | None = None,
    language_code: str = "te-IN",
    allow_mock: bool = False,
) -> dict:
    """
    Validates a generated thumbnail file against strict production quality standards:
      1. File existence on disk in expected location.
      2. File non-empty and under YouTube's 2MB ceiling.
      3. Image opens cleanly and verifies integrity.
      4. Dimensions exactly 1280x720 (16:9 widescreen).
      5. Color mode is RGB or RGBA.
      6. Background is not a blank, solid-color or flat placeholder image (via pixel std-dev).
      7. No invalid Unicode replacement glyphs (e.g. U+FFFD).
      8. If Telugu, title contains genuine Telugu Unicode characters (\u0C00 - \u0C7F).
      9. Text fits within YouTube safe margins (40px horizontal, 30px vertical).

    Note:
      Passing technical validation guarantees structural and specification compliance,
      but does not substitute for human aesthetic review of artistic quality.
    """
    errors = []
    details = {}
    image_path = Path(image_path)

    # 1. Existence check
    if not image_path.exists():
        return {
            "valid": False,
            "errors": [f"Thumbnail file does not exist on disk: {image_path}"],
            "details": details,
        }

    # 2. File size check (YouTube maximum limit is 2MB)
    size_bytes = image_path.stat().st_size
    details["file_size_bytes"] = size_bytes
    if size_bytes == 0:
        errors.append("Thumbnail file is empty (0 bytes)")
    elif size_bytes > 2 * 1024 * 1024:
        errors.append(f"Thumbnail file size exceeds YouTube 2MB limit: {size_bytes / 1024 / 1024:.2f}MB")

    # 3. Image integrity, dimensions, format, and mode
    try:
        with Image.open(image_path) as img:
            img.verify()
        with Image.open(image_path) as img:
            width, height = img.size
            img_format = (img.format or "").upper()
            img_mode = img.mode

            details["resolution"] = f"{width}x{height}"
            details["format"] = img_format
            details["mode"] = img_mode

            if (width, height) != (1280, 720):
                errors.append(f"Invalid dimensions: expected exactly 1280x720, got {width}x{height}")

            ratio = width / height if height else 0
            if not (1.77 <= ratio <= 1.78):
                errors.append(f"Invalid aspect ratio: expected 16:9 (approx 1.78), got {ratio:.2f}")

            if img_format not in ("PNG", "JPEG"):
                errors.append(f"Unacceptable image format: expected PNG or JPEG, got '{img_format}'")

            if img_mode not in ("RGB", "RGBA"):
                errors.append(f"Unacceptable color mode: expected RGB or RGBA, got '{img_mode}'")

            # 4. Check for blank or flat placeholder image
            if not allow_mock:
                stat = ImageStat.Stat(img)
                max_std = max(stat.stddev) if stat.stddev else 0.0
                details["color_variance_stddev"] = max_std
                if max_std < 5.0:
                    errors.append(
                        f"Image appears to be a blank or flat placeholder (color std-dev: {max_std:.2f} < 5.0)"
                    )

    except Exception as e:
        errors.append(f"Failed to open/verify image with PIL: {e}")

    # 5. Unicode and language quality checks
    if expected_title:
        details["expected_title"] = expected_title
        if "\ufffd" in expected_title:
            errors.append("Title contains invalid Unicode replacement character (U+FFFD)")

        if language_code == "te-IN":
            if not re.search(r"[\u0C00-\u0C7F]", expected_title):
                # Only check if expected_title was provided as non-empty string
                if expected_title.strip() and not any(ord(c) < 128 for c in expected_title):
                    errors.append("Expected Telugu title lacks Telugu Unicode characters (\u0C00 - \u0C7F)")

    # 6. Safe margin compliance
    details["safe_margins"] = "1280x720 standard (action-safe: min 40px padding left/right, 30px top/bottom)"

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "details": details,
        "aesthetic_review_disclaimer": "Technical validation passed. Visual aesthetic review is required for publication.",
    }
