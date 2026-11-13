# src/thumbnail/providers/pollinations.py
# Phase 2H / Phase 4 — Pollinations AI Image Generation Provider for YouTube Thumbnails
#
# Dedicated AI background generation provider using the official Pollinations API.
# Exclusively generates 16:9 cinematic devotional backgrounds for YouTube thumbnails.
# Follows fail-closed design: no silent fallback to Flux, Gemini, or mock images.

import io
import os
import re
import time
import urllib.parse
from pathlib import Path
from typing import Optional
from PIL import Image

try:
    import requests
except ImportError:
    requests = None


# ── Exceptions ────────────────────────────────────────────────────────────────
class PollinationsError(RuntimeError):
    """Base exception for all Pollinations provider failures."""
    pass


class PollinationsAPIError(PollinationsError):
    """Raised when the Pollinations API returns an HTTP error status."""
    pass


class PollinationsTimeoutError(PollinationsError):
    """Raised when a request to Pollinations times out."""
    pass


class PollinationsImageValidationError(PollinationsError):
    """Raised when downloaded image bytes are corrupt, invalid, or empty."""
    pass


# ── Deity Iconography Knowledge Base ──────────────────────────────────────────
def _get_deity_iconography_details(
    deity_clean: str,
    event_clean: str,
    visual_setting: Optional[str] = None,
) -> tuple[str, str, str, list[str]]:
    """
    Returns authentic Vedic deity iconography, setting, lighting, and negative prompt keywords.
    Maintains dynamic flexibility across all avatars while ensuring anatomically and mythologically
    accurate visual representation for each specific deity.
    """
    deity_lower = deity_clean.lower()
    event_lower = event_clean.lower()

    if "varaha" in deity_lower or "varaha" in event_lower:
        subject_desc = (
            "Lord Vishnu in the unmistakable divine Varaha form, with a clearly visible noble boar head, "
            "elongated snout, and distinct curved white tusks, accompanied by a radiant blue-toned divine body (Shyama-varna), "
            "ornate golden crown (mukuta) and sacred Vedic jewelry. Visibly present Goddess Bhūmi Devi (Mother Earth), "
            "gracefully seated and supported upon Lord Varaha's raised tusk, depicted as a radiant divine female figure "
            "in traditional Indian silk attire with folded hands. Both figures are clearly illuminated with distinct, "
            "unobstructed features, divine golden aura, and anatomically coherent natural proportions."
        )
        setting_desc = (
            visual_setting.strip() if visual_setting and visual_setting.strip() else
            "churning primordial cosmic ocean with dramatic surging teal and turquoise waves, piercing rays of celestial golden sunlight breaking through ocean depths"
        )
        color_lighting_desc = (
            "brilliant divine golden aura, bright celestial gold, radiant Vishnu blue and deep luminous teal tones, "
            "vibrant devotional illumination with fully visible well-lit faces, avoiding excessively dark faces or underexposed figures"
        )
        specific_negatives = [
            "generic animal boar",
            "wild pig",
            "human face replacing the boar head",
            "missing tusks",
            "missing Bhūmi Devi",
            "missing Bhumi Devi",
            "extra limbs",
            "distorted anatomy",
            "cartoonish proportions",
            "blurry faces",
            "dark or hidden deity",
            "underexposed face",
            "shadowy hidden face",
        ]
    elif "narasimha" in deity_lower or "narasimha" in event_lower:
        subject_desc = (
            "Lord Vishnu in the magnificent divine Narasimha form, powerful noble lion head with flowing golden mane, "
            "expressive radiant divine eyes, strong heroic blue-gold human torso adorned with ornate mukuta crown and sacred ornaments"
        )
        setting_desc = (
            visual_setting.strip() if visual_setting and visual_setting.strip() else
            "celestial palace threshold at twilight, radiant shattered pillar emitting divine celestial illumination"
        )
        color_lighting_desc = "dramatic golden radiance and crimson twilight glows, high contrast cinematic lighting with fully illuminated deity"
        specific_negatives = ["generic animal lion", "distorted anatomy", "dark hidden face", "blurry features"]
    elif "krishna" in deity_lower or "krishna" in event_lower:
        subject_desc = (
            "Lord Krishna in enchanting divine form, beautiful blue-hued complexion, ornate peacock feather crown, "
            "radiant yellow silk pitambara, holding Mount Govardhan effortlessly on his little finger with serene smile"
        )
        setting_desc = (
            visual_setting.strip() if visual_setting and visual_setting.strip() else
            "Vrindavan hill landscape with rolling dark monsoon clouds illuminated by divine golden aura"
        )
        color_lighting_desc = "vibrant warm devotional colors, brilliant golden halos, deep indigo and emerald greens"
        specific_negatives = ["distorted face", "extra limbs", "dark hidden eyes"]
    elif "kurma" in deity_lower or "kurma" in event_lower:
        subject_desc = (
            "Lord Vishnu in the cosmic Kurma avatar, immense majestic tortoise form with glowing golden shell, "
            "supporting Mount Mandara with cosmic strength, surrounded by celestial devas and radiance"
        )
        setting_desc = (
            visual_setting.strip() if visual_setting and visual_setting.strip() else
            "cosmic ocean of milk during Samudra Manthan with swirling sacred waves and glowing celestial mists"
        )
        color_lighting_desc = "radiant golden luminescence and deep celestial blue ocean tones, volumetric lighting"
        specific_negatives = ["generic pet turtle", "distorted shell", "dark murky waters"]
    elif "hanuman" in deity_lower or "hanuman" in event_lower:
        subject_desc = (
            "Lord Hanuman in mighty glowing divine form, soaring heroically across the skies, carrying the golden Dronagiri mountain "
            "with radiant medicinal herbs, adorned with golden ornaments and flying saffron dhoti"
        )
        setting_desc = (
            visual_setting.strip() if visual_setting and visual_setting.strip() else
            "Himalayan mountain peaks under sunrise skies with golden clouds and morning rays"
        )
        color_lighting_desc = "brilliant sunrise gold, vibrant saffron, and celestial sky blue with bright heroic lighting"
        specific_negatives = ["generic wild monkey", "distorted limbs", "dark blurry face"]
    elif "shiva" in deity_lower or "shiva" in event_lower:
        subject_desc = (
            "Lord Shiva in serene divine form, meditative grace, sacred crescent moon in matted locks, sacred Ganga flowing, "
            "divine third eye, glowing trident (Trishula) and damaru, adorned with sacred rudraksha and serpents"
        )
        setting_desc = (
            visual_setting.strip() if visual_setting and visual_setting.strip() else
            "Mount Kailash snowy peaks beneath a starry cosmic galaxy and ethereal misty glow"
        )
        color_lighting_desc = "celestial moonlight silver, icy cobalt blue, and warm flame glows"
        specific_negatives = ["distorted face", "scary demon", "blurry features"]
    else:
        subject_desc = (
            f"Lord {deity_clean} in authentic Vedic divine form, adorned with ornate golden mukuta crown, sacred jewelry, "
            "radiant glowing divine halo, clearly illuminated noble face, and anatomically coherent natural proportions"
        )
        setting_desc = (
            visual_setting.strip() if visual_setting and visual_setting.strip() else
            "sacred Vedic celestial realm with ethereal radiant clouds and divine celestial lighting"
        )
        color_lighting_desc = "radiant divine golden radiance, rich devotional hues, cinematic volumetric lighting"
        specific_negatives = ["extra limbs", "distorted anatomy", "dark hidden deity", "blurry faces"]

    return subject_desc, setting_desc, color_lighting_desc, specific_negatives


# ── Prompt Builder ────────────────────────────────────────────────────────────
def build_thumbnail_background_prompt(
    topic: str,
    deity: str = "Divine Deity",
    main_event: Optional[str] = None,
    emotional_theme: Optional[str] = None,
    visual_setting: Optional[str] = None,
    thumbnail_title: Optional[str] = None,
) -> str:
    """
    Constructs a highly optimized, dynamic cinematic devotional prompt for YouTube thumbnails.
    Separates background generation from text overlay:
      - Subject positioned center/right (leaving left 35–40% reserved for Telugu typography)
      - Deity face and accompanying figures (e.g. Bhūmi Devi) clearly illuminated and unobstructed
      - Vivid dramatic lighting, rich devotional colors (bright gold, celestial blue, deep teal)
      - Avoids excessively dark faces or underexposed figures
      - Explicit negative constraints: absolutely no text, typography, letters, watermarks, or distorted anatomy
    """
    deity_clean = (deity or "Divine Deity").strip().title()
    topic_clean = (topic or "").strip()
    event_clean = (main_event or topic_clean).strip()
    emotion = (emotional_theme or "Devotional triumph, sacred awe, and divine protection").strip()

    subject_desc, setting_desc, color_desc, specific_negs = _get_deity_iconography_details(
        deity_clean=deity_clean,
        event_clean=event_clean,
        visual_setting=visual_setting,
    )

    base_negatives = [
        "no text", "no words", "no letters", "watermark", "logo", "labels",
        "subtitles", "caption", "banner", "signatures", "clean image without typography",
    ]
    all_negatives = ", ".join(base_negatives + specific_negs)

    prompt_parts = [
        f"Masterpiece 8k cinematic devotional artwork depicting {subject_desc}",
        f"Event context: {event_clean}",
        f"Atmosphere: {emotion}",
        f"Setting: {setting_desc}",
        f"Lighting and Palette: {color_desc}, volumetric god rays, high-contrast chiaroscuro",
        "Composition: widescreen 16:9 cinematic YouTube thumbnail framing with the divine deity positioned toward the center-right (from 40% to 100% width), reserving the left 35–40% area with smooth uncluttered deep atmospheric tones for title text overlay. The deity's face, tusks, and sacred figures remain completely unobstructed",
        "Style: hyper-detailed oil painting style with vibrant colors, sharp focus, 16:9 widescreen composition, ultra photorealistic sacred realism",
        f"Negative prompt: {all_negatives}",
    ]

    return ", ".join(prompt_parts)


# ── Sanitizer ─────────────────────────────────────────────────────────────────
def sanitize_log_url(url: str) -> str:
    """Removes API keys or secret tokens from URL strings before logging."""
    if not url:
        return ""
    # Redact query param key=...
    sanitized = re.sub(r"([?&]key=)[^&]+", r"\1[REDACTED]", url)
    sanitized = re.sub(r"([?&]api_key=)[^&]+", r"\1[REDACTED]", sanitized)
    sanitized = re.sub(r"(Bearer\s+)[a-zA-Z0-9_\-\.]+", r"\1[REDACTED]", sanitized)
    return sanitized


# ── Pollinations Provider ─────────────────────────────────────────────────────
class PollinationsProvider:
    """
    Production-grade Pollinations image generation provider.
    Exclusively dedicated to synthesizing 16:9 background images for YouTube thumbnails.
    """

    DEFAULT_BASE_URL = "https://image.pollinations.ai/prompt"
    DEFAULT_MODEL = "flux"
    DEFAULT_WIDTH = 1280
    DEFAULT_HEIGHT = 720
    DEFAULT_TIMEOUT = 45
    DEFAULT_MAX_RETRIES = 3

    def __init__(
        self,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
    ):
        self.model = (
            model
            or os.environ.get("POLLINATIONS_MODEL")
            or self.DEFAULT_MODEL
        ).strip()

        self.base_url = (
            base_url
            or os.environ.get("POLLINATIONS_ENDPOINT")
            or self.DEFAULT_BASE_URL
        ).rstrip("/")

        # Authentication key (optional for basic tier, required for paid/high-rate tier)
        self.api_key = api_key or os.environ.get("POLLINATIONS_API_KEY")

        # Network tuning
        self.timeout = int(
            timeout
            or os.environ.get("POLLINATIONS_TIMEOUT")
            or self.DEFAULT_TIMEOUT
        )
        self.max_retries = int(
            max_retries
            or os.environ.get("POLLINATIONS_MAX_RETRIES")
            or self.DEFAULT_MAX_RETRIES
        )

    def build_request_url(
        self,
        prompt: str,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        seed: Optional[int] = None,
    ) -> tuple[str, dict]:
        """
        Constructs the target GET URL and query parameters.
        Returns (url, params_dict).
        """
        clean_prompt = prompt.strip().replace("\n", " ")
        encoded_prompt = urllib.parse.quote(clean_prompt)
        url = f"{self.base_url}/{encoded_prompt}"

        params = {
            "width": width,
            "height": height,
            "model": self.model,
            "nologo": "true",
            "enhance": "false",
        }
        if seed is not None:
            params["seed"] = seed

        return url, params

    def build_headers(self) -> dict:
        """Constructs headers, safely injecting Authorization if API key exists."""
        headers = {
            "User-Agent": "DivineDharshanam/1.0 (Pollinations Thumbnail Generator)",
            "Accept": "image/*",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key.strip()}"
        return headers

    def generate_background(
        self,
        prompt: str,
        output_path: Path,
        seed: Optional[int] = None,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
    ) -> Path:
        """
        Fetches an AI-generated 16:9 background from Pollinations with exponential backoff retries.
        Validates the downloaded image before saving to output_path.
        Fails closed on error without mock or fallback substitution.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        url, params = self.build_request_url(prompt, width=width, height=height, seed=seed)
        headers = self.build_headers()

        log_url = sanitize_log_url(f"{url}?{urllib.parse.urlencode(params)}")
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                if requests is None:
                    raise PollinationsError("Python 'requests' library is required for Pollinations API calls.")

                response = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                )

                if response.status_code == 200:
                    raw_bytes = response.content
                    if not raw_bytes or len(raw_bytes) < 1024:
                        raise PollinationsImageValidationError(
                            f"Received truncated image payload ({len(raw_bytes) if raw_bytes else 0} bytes)"
                        )

                    # Verify image integrity with PIL
                    try:
                        with Image.open(io.BytesIO(raw_bytes)) as test_img:
                            test_img.verify()
                    except Exception as verify_err:
                        raise PollinationsImageValidationError(
                            f"Downloaded image bytes are unreadable or corrupt: {verify_err}"
                        )

                    # Re-open and convert cleanly to RGB, ensuring exact 1280x720 aspect
                    with Image.open(io.BytesIO(raw_bytes)) as img:
                        img_rgb = img.convert("RGB")
                        if img_rgb.size != (width, height):
                            # Resize to target canvas if model scaled dimensions
                            img_rgb = img_rgb.resize((width, height), Image.Resampling.LANCZOS)

                        # Write atomically via temp file to guarantee no incomplete saves
                        tmp_path = output_path.with_suffix(".tmp.png")
                        img_rgb.save(tmp_path, format="PNG")
                        if tmp_path.exists() and tmp_path.stat().st_size > 0:
                            if output_path.exists():
                                output_path.unlink()
                            tmp_path.rename(output_path)

                    return output_path

                elif response.status_code in (401, 403):
                    # Authentication / permission failure: fail immediately without retrying
                    raise PollinationsAPIError(
                        f"Pollinations authentication/permission error HTTP {response.status_code}. "
                        "Check POLLINATIONS_API_KEY configuration."
                    )
                elif response.status_code == 429:
                    # Rate limit: retry with backoff
                    last_error = PollinationsAPIError(f"Pollinations rate limit (HTTP 429) on attempt {attempt}")
                elif response.status_code >= 500:
                    # Server error: retry with backoff
                    last_error = PollinationsAPIError(
                        f"Pollinations server error HTTP {response.status_code} on attempt {attempt}"
                    )
                else:
                    raise PollinationsAPIError(
                        f"Pollinations unexpected HTTP status {response.status_code} on attempt {attempt}"
                    )

            except requests.Timeout as te:
                last_error = PollinationsTimeoutError(f"Pollinations request timed out after {self.timeout}s: {te}")
            except (PollinationsAPIError, PollinationsImageValidationError) as pe:
                last_error = pe
                if isinstance(pe, PollinationsAPIError) and "HTTP 401" in str(pe) or "HTTP 403" in str(pe):
                    raise
            except Exception as e:
                last_error = PollinationsError(f"Pollinations network error on attempt {attempt}: {e}")

            # Backoff before next attempt
            if attempt < self.max_retries:
                backoff_delay = 2 ** attempt
                time.sleep(backoff_delay)

        # All retries exhausted: fail closed
        err_msg = (
            f"❌ Pollinations thumbnail background generation failed after {self.max_retries} attempts: {last_error}\n"
            f"Target URL: {log_url}\n"
            "Fail-closed: No fallback to Flux or mock images allowed for thumbnail backgrounds."
        )
        raise PollinationsError(err_msg) from last_error
