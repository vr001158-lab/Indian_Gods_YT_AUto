# src/assets/contact_sheet.py
# Visual Review Contact Sheet Generator for Unapproved Deity Asset Candidates

from __future__ import annotations

import math
import subprocess
from pathlib import Path
from typing import Any, Optional
from PIL import Image, ImageDraw, ImageFont

from src.assets.inventory import AssetInventoryItem

CARD_W = 280
CARD_H = 380
IMG_BOX_W = 260
IMG_BOX_H = 260
MARGIN_X = 20
MARGIN_Y = 20
HEADER_H = 100
MAX_COLS = 4
MAX_ROWS = 4
MAX_ITEMS_PER_SHEET = MAX_COLS * MAX_ROWS  # 16 per page


def get_contact_sheet_font(size: int = 12) -> ImageFont.ImageFont:
    """Loads default or bundled font safely."""
    ttf_candidate = Path("assets/fonts/NotoSansTelugu-Variable.ttf")
    if ttf_candidate.exists():
        try:
            return ImageFont.truetype(str(ttf_candidate), size=size)
        except Exception:
            pass
    try:
        return ImageFont.load_default()
    except Exception:
        return ImageFont.load_default()


def extract_video_frame_cached(
    video_path: Path | str,
    frames_dir: Path | str = "data/review/extracted_frames",
    timestamp: str = "00:00:02",
) -> Optional[Path]:
    """
    Extracts a representative frame from a video using FFmpeg and caches it.
    If frame already exists and has non-zero size, returns cached frame immediately.
    """
    v_p = Path(video_path)
    f_dir = Path(frames_dir)
    f_dir.mkdir(parents=True, exist_ok=True)

    if not v_p.exists() or v_p.stat().st_size == 0:
        return None

    frame_name = f"frame_{v_p.stem}_{v_p.stat().st_size}.png"
    out_frame = f_dir / frame_name

    if out_frame.exists() and out_frame.stat().st_size > 0:
        return out_frame

    cmd = [
        "ffmpeg", "-y",
        "-ss", timestamp,
        "-i", str(v_p),
        "-vframes", "1",
        "-q:v", "2",
        str(out_frame),
    ]

    try:
        res = subprocess.run(cmd, capture_output=True, timeout=20)
        if res.returncode != 0 or not out_frame.exists() or out_frame.stat().st_size == 0:
            # Fallback to start of video
            cmd[2] = "00:00:00"
            subprocess.run(cmd, capture_output=True, timeout=20)
        if out_frame.exists() and out_frame.stat().st_size > 0:
            return out_frame
    except Exception:
        pass

    return None


def render_single_tile(
    draw: ImageDraw.ImageDraw,
    base_img: Image.Image,
    item: AssetInventoryItem,
    x: int,
    y: int,
    font: ImageFont.ImageFont,
    small_font: ImageFont.ImageFont,
    thumb_img: Optional[Image.Image] = None,
) -> None:
    """Renders one asset card tile on the contact sheet."""
    # Outer card container
    card_box = [(x, y), (x + CARD_W, y + CARD_H)]
    draw.rectangle(card_box, fill=(24, 24, 32), outline=(50, 50, 65), width=1)

    img_x = x + (CARD_W - IMG_BOX_W) // 2
    img_y = y + 10

    # Image box background
    draw.rectangle(
        [(img_x, img_y), (img_x + IMG_BOX_W, img_y + IMG_BOX_H)],
        fill=(12, 12, 16),
        outline=(60, 60, 80),
        width=1,
    )

    if thumb_img is not None:
        tw, th = thumb_img.size
        paste_x = img_x + (IMG_BOX_W - tw) // 2
        paste_y = img_y + (IMG_BOX_H - th) // 2
        base_img.paste(thumb_img, (paste_x, paste_y))
    else:
        # Placeholder for broken / unreadable asset
        draw.text(
            (img_x + 30, img_y + 110),
            "⚠️ UNREADABLE / BROKEN",
            fill=(255, 80, 80),
            font=font,
        )

    # UNAPPROVED Status Badge (Top-left of image box)
    badge_w = 110
    badge_h = 22
    draw.rectangle(
        [(img_x + 4, img_y + 4), (img_x + 4 + badge_w, img_y + 4 + badge_h)],
        fill=(180, 25, 25),
        outline=(255, 60, 60),
        width=1,
    )
    draw.text(
        (img_x + 10, img_y + 8),
        "● UNAPPROVED",
        fill=(255, 255, 255),
        font=small_font,
    )

    # Type / aspect ratio badge (Top-right of image box)
    ar_label = f"{item.file_type.upper()} ({item.aspect_ratio})"
    draw.rectangle(
        [(img_x + IMG_BOX_W - 95, img_y + 4), (img_x + IMG_BOX_W - 4, img_y + 4 + badge_h)],
        fill=(35, 45, 65),
        outline=(70, 100, 150),
        width=1,
    )
    draw.text(
        (img_x + IMG_BOX_W - 90, img_y + 8),
        ar_label,
        fill=(200, 220, 255),
        font=small_font,
    )

    # Text metadata below image box
    text_y = img_y + IMG_BOX_H + 10
    draw.text((x + 14, text_y), f"Candidate: {item.candidate_deity}", fill=(255, 215, 0), font=font)

    dim_str = f"{item.width}x{item.height}"
    if item.duration_seconds > 0:
        dim_str += f" | {item.duration_seconds}s"
    size_kb = round(item.file_size_bytes / 1024, 1)
    draw.text((x + 14, text_y + 20), f"{dim_str} • {size_kb} KB", fill=(180, 180, 190), font=small_font)

    # Truncate filename cleanly if long
    fn = Path(item.rel_path).name
    if len(fn) > 30:
        fn_display = fn[:14] + "..." + fn[-13:]
    else:
        fn_display = fn
    draw.text((x + 14, text_y + 38), fn_display, fill=(240, 240, 240), font=small_font)

    # Short relative folder
    folder_str = str(Path(item.rel_path).parent).replace("\\", "/")
    if len(folder_str) > 34:
        folder_str = folder_str[:16] + "..." + folder_str[-15:]
    draw.text((x + 14, text_y + 54), folder_str, fill=(120, 130, 150), font=small_font)


def render_contact_sheet_page(
    items: list[AssetInventoryItem],
    page_num: int,
    total_pages: int,
    deity_key: str,
    category: str,
    output_path: Path,
    frame_cache: dict[str, Path],
) -> Path:
    """Renders a single contact sheet image page (up to MAX_ITEMS_PER_SHEET items)."""
    n_items = len(items)
    cols = min(MAX_COLS, n_items) if n_items > 0 else 1
    rows = math.ceil(n_items / cols) if cols > 0 else 1

    sheet_w = MARGIN_X * 2 + cols * CARD_W + (cols - 1) * MARGIN_X
    sheet_h = HEADER_H + MARGIN_Y * 2 + rows * CARD_H + (rows - 1) * MARGIN_Y

    sheet_img = Image.new("RGB", (sheet_w, sheet_h), color=(14, 14, 18))
    draw = ImageDraw.Draw(sheet_img)

    title_font = get_contact_sheet_font(size=18)
    font = get_contact_sheet_font(size=12)
    small_font = get_contact_sheet_font(size=10)

    # ── Header ────────────────────────────────────────────────────────────────
    draw.rectangle([(0, 0), (sheet_w, HEADER_H)], fill=(20, 20, 26))
    header_title = f"DIVINE DHARSHANAM — VISUAL REVIEW CONTACT SHEET: {deity_key.upper()} ({category.upper()})"
    draw.text((MARGIN_X, 16), header_title, fill=(255, 215, 0), font=title_font)

    sub_title = (
        f"Page {page_num}/{total_pages} | Showing {n_items} unapproved candidates | "
        f"⚠️ Human Inspection Only: DOES NOT GRANT APPROVAL"
    )
    draw.text((MARGIN_X, 48), sub_title, fill=(255, 100, 100), font=font)

    audit_note = "All assets shown are strictly UNAPPROVED in production registry until explicit catalog registration."
    draw.text((MARGIN_X, 72), audit_note, fill=(160, 160, 180), font=small_font)
    draw.line([(0, HEADER_H), (sheet_w, HEADER_H)], fill=(60, 60, 80), width=1)

    # ── Render Tiles ──────────────────────────────────────────────────────────
    for idx, item in enumerate(items):
        r = idx // cols
        c = idx % cols
        tile_x = MARGIN_X + c * (CARD_W + MARGIN_X)
        tile_y = HEADER_H + MARGIN_Y + r * (CARD_H + MARGIN_Y)

        thumb_img = None
        if not item.is_broken:
            # Load thumbnail for image or extracted frame for video
            src_file: Optional[Path] = None
            if item.file_type == "video":
                src_file = frame_cache.get(item.rel_path)
            else:
                src_file = Path(item.rel_path)

            if src_file and src_file.exists():
                try:
                    with Image.open(src_file) as raw_img:
                        thumb = raw_img.copy()
                        thumb.thumbnail((IMG_BOX_W, IMG_BOX_H), Image.Resampling.LANCZOS)
                        thumb_img = thumb.convert("RGB")
                except Exception:
                    thumb_img = None

        render_single_tile(
            draw=draw,
            base_img=sheet_img,
            item=item,
            x=tile_x,
            y=tile_y,
            font=font,
            small_font=small_font,
            thumb_img=thumb_img,
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet_img.save(output_path, format="PNG")
    return output_path


def generate_all_contact_sheets(
    inventory: list[AssetInventoryItem],
    output_dir: str | Path = "data/review/contact_sheets",
    frames_dir: str | Path = "data/review/extracted_frames",
) -> dict[str, list[str]]:
    """
    Generates paginated visual review contact sheets for unapproved candidates,
    strictly grouped by candidate deity and separated by image vs video.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    f_dir = Path(frames_dir)
    f_dir.mkdir(parents=True, exist_ok=True)

    # 1. Pre-extract video frames for video items
    frame_cache: dict[str, Path] = {}
    video_items = [item for item in inventory if item.file_type == "video" and not item.is_broken]
    for v_item in video_items:
        extracted = extract_video_frame_cached(v_item.rel_path, frames_dir=f_dir)
        if extracted:
            frame_cache[v_item.rel_path] = extracted

    # 2. Filter unapproved candidates
    unapproved_items = [
        item for item in inventory
        if item.approval_status != "APPROVED"
    ]

    # 3. Group by candidate deity and category (image vs video)
    grouped: dict[tuple[str, str], list[AssetInventoryItem]] = {}
    for item in unapproved_items:
        key = (item.candidate_deity.lower(), item.file_type)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(item)

    generated_sheets: dict[str, list[str]] = {}

    for (deity_key, category), group_items in sorted(grouped.items()):
        total_items = len(group_items)
        if total_items == 0:
            continue

        total_pages = math.ceil(total_items / MAX_ITEMS_PER_SHEET)
        group_sheet_paths: list[str] = []

        for page in range(1, total_pages + 1):
            start_idx = (page - 1) * MAX_ITEMS_PER_SHEET
            end_idx = start_idx + MAX_ITEMS_PER_SHEET
            page_slice = group_items[start_idx:end_idx]

            sheet_filename = f"contact_sheet_{category}_{deity_key}_p{page}.png"
            sheet_path = out_dir / sheet_filename

            render_contact_sheet_page(
                items=page_slice,
                page_num=page,
                total_pages=total_pages,
                deity_key=deity_key,
                category=category,
                output_path=sheet_path,
                frame_cache=frame_cache,
            )
            group_sheet_paths.append(str(sheet_path))

        group_label = f"{deity_key}_{category}"
        generated_sheets[group_label] = group_sheet_paths

    return generated_sheets
