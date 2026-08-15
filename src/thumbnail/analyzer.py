# src/thumbnail/analyzer.py
# Phase 2H — Thumbnail Image Analyzer

from pathlib import Path
from PIL import Image


def analyze_thumbnail_file(image_path: Path) -> dict:
    """
    Analyzes a generated thumbnail to verify resolution, format, aspect ratio,
    and size constraints.
    """
    errors = []

    # 1. Existence check
    if not image_path.exists():
        return {
            "valid":  False,
            "errors": ["File does not exist on disk"]
        }

    # 2. Size check (YouTube maximum limit is 2MB)
    size_bytes = image_path.stat().st_size
    if size_bytes == 0:
        errors.append("File is empty (0 bytes)")
    elif size_bytes > 2 * 1024 * 1024:
        errors.append(f"File size exceeds YouTube 2MB limit: {size_bytes / 1024 / 1024:.2f}MB")

    # 3. Image dimensions check
    try:
        with Image.open(image_path) as img:
            width, height = img.size
            img_format = img.format

            if width != 1280 or height != 720:
                errors.append(f"Invalid dimensions: expected 1280x720, got {width}x{height}")

            # Aspect ratio check (16:9)
            # 1280 / 720 = 1.7777...
            ratio = width / height
            if not (1.77 <= ratio <= 1.78):
                errors.append(f"Invalid aspect ratio: expected 16:9 (approx 1.78), got {ratio:.2f}")

            if img_format.lower() not in ("png", "jpeg"):
                errors.append(f"Unacceptable format: expected PNG or JPEG, got {img_format}")

    except Exception as e:
        errors.append(f"Failed to open image file with PIL: {e}")

    # 4. Readability placeholder
    # Simulates text contrast analyzer/readability indicator
    # Return valid status
    return {
        "valid":  len(errors) == 0,
        "errors": errors
    }
