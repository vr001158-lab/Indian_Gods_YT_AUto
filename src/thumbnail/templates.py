# src/thumbnail/templates.py
# Phase 2H — Thumbnail Design Templates and Color Presets

# Sleek aesthetic presets
DEVOTIONAL_GOLD_THEME = {
    "bg_color":          (24, 18, 30),      # Sleek deep purple/dark background
    "accent_color":      (255, 185, 35),    # Sacred golden yellow
    "text_color":        (255, 255, 255),   # Clean white
    "shadow_color":      (0, 0, 0),         # Drop shadow black
    "title_size":        56,
    "subtitle_size":     32,
    "branding_size":     24,
    "branding_text":     "DIVINE DHARSHANAM DAILY",
}

DEVOTIONAL_SCHEME_RED = {
    "bg_color":          (32, 10, 10),      # Deep crimson background
    "accent_color":      (255, 99, 71),     # Tomato red highlight
    "text_color":        (245, 245, 245),
    "shadow_color":      (0, 0, 0),
    "title_size":        56,
    "subtitle_size":     32,
    "branding_size":     24,
    "branding_text":     "DIVINE DHARSHANAM DAILY",
}


def get_thumbnail_theme(language_code: str = "hi-IN", theme_name: str = "gold") -> dict:
    """Returns a theme dictionary localized with native branding text."""
    base = dict(DEVOTIONAL_GOLD_THEME if theme_name == "gold" else DEVOTIONAL_SCHEME_RED)
    if language_code == "te-IN":
        base["branding_text"] = "దివ్య దర్శనం"
    elif language_code == "hi-IN":
        base["branding_text"] = "दिव्य दर्शनम्"
    return base
