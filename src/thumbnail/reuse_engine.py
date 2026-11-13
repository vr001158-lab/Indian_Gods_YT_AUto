# src/thumbnail/reuse_engine.py
# Phase 2H / Phase 4 — Zero-Cost Thumbnail Asset Reuse Engine
#
# Primary engine for generating ₹0 production thumbnails:
#   1. Resolves deity and avatar from topic and script.
#   2. Executes the 4-priority selection chain (approved artwork -> visual map -> video frames -> anonymous Pollinations).
#   3. Composes 1280x720 thumbnail with PIL (Telugu typography, branding, safe margins, devotional gold border).
#   4. Emits detailed thumbnail metadata JSON.
#   5. Strictly zero API cost, zero paid dependencies.

from __future__ import annotations

import os
import json
import time
from pathlib import Path
from typing import Optional, Any

from src.thumbnail.asset_index import DeityAssetIndex, resolve_deity_and_avatar
from src.thumbnail.asset_selector import (
    ThumbnailAssetSelector,
    SelectedThumbnailAsset,
    NoSuitableThumbnailAssetError,
)
from src.thumbnail.composer import compose_reused_thumbnail
from src.thumbnail.analyzer import analyze_thumbnail_file


class ThumbnailReuseEngine:
    """
    Zero-Cost Thumbnail Generation Engine with intelligent asset reuse.
    """

    def __init__(self, asset_index: Optional[DeityAssetIndex] = None):
        self.asset_index = asset_index or DeityAssetIndex()
        self.selector = ThumbnailAssetSelector(self.asset_index)

    def generate(
        self,
        topic: str,
        script_title: str,
        subtitle: Optional[str] = None,
        deity: Optional[str] = None,
        avatar: Optional[str] = None,
        visual_map_path: Optional[Path] = None,
        video_path: Optional[Path] = None,
        output_image_path: Optional[Path] = None,
        output_meta_path: Optional[Path] = None,
        language_code: str = "te-IN",
        allow_pollinations_fallback: bool = True,
        pollinations_timeout: int = 15,
    ) -> dict[str, Any]:
        """
        Executes the zero-cost asset reuse thumbnail workflow.
        Returns complete metadata dict.
        Raises NoSuitableThumbnailAssetError if no suitable asset exists.
        """
        start_time = time.time()

        # 1. Resolve canonical deity and avatar
        res_deity, res_avatar = resolve_deity_and_avatar(
            f"{topic} {script_title} {deity or ''} {avatar or ''}"
        )
        final_deity = res_deity or (deity or "").lower() or "lord_shiva"
        final_avatar = res_avatar or (avatar.lower() if avatar else None)

        # 2. Select best asset across the 4 priorities
        selected: SelectedThumbnailAsset = self.selector.select_thumbnail_asset(
            topic=script_title or topic,
            deity_hint=final_deity,
            avatar_hint=final_avatar,
            visual_map_path=visual_map_path,
            video_path=video_path,
            allow_pollinations_fallback=allow_pollinations_fallback,
            pollinations_timeout=pollinations_timeout,
        )

        # 3. Setup output file paths
        ts = time.strftime("%Y%m%d_%H%M%S")
        if output_image_path is None:
            out_img = Path("data/thumbnails") / f"thumbnail_{ts}.png"
        else:
            out_img = Path(output_image_path)
        out_img.parent.mkdir(parents=True, exist_ok=True)

        if output_meta_path is None:
            out_meta = Path("data/thumbnails") / f"thumbnail_metadata_{ts}.json"
        else:
            out_meta = Path(output_meta_path)
        out_meta.parent.mkdir(parents=True, exist_ok=True)

        # 4. Compose final 1280x720 thumbnail using PIL
        t_comp_start = time.time()
        compose_reused_thumbnail(
            background_path=Path(selected.asset_path),
            title=script_title or topic,
            subtitle=subtitle or "",
            output_path=out_img,
            language_code=language_code,
        )
        comp_time = round(time.time() - t_comp_start, 3)
        total_time = round(time.time() - start_time, 2)

        # 5. Technical Validation via existing analyzer
        validation = analyze_thumbnail_file(
            out_img,
            expected_title=script_title or topic,
            language_code=language_code,
            allow_mock=False,
        )

        # 6. Build Metadata Report
        metadata = {
            "status": "SUCCESS" if validation["valid"] else "FAILED_VALIDATION",
            "generation_mode": "ZERO_COST_ASSET_REUSE",
            "api_spending_inr": 0.0,
            "api_spending_usd": 0.0,
            "engine": "ThumbnailReuseEngine",
            "selected_asset": {
                "source_path": selected.asset_path,
                "priority_level": selected.priority_level,
                "priority_name": selected.priority_name,
                "deity": selected.deity,
                "avatar": selected.avatar,
                "verification_status": selected.verification_status,
                "selection_reason": selected.selection_reason,
                "quality_score": selected.quality_score,
            },
            "output_files": {
                "thumbnail_image": str(out_img).replace("\\", "/"),
                "thumbnail_metadata": str(out_meta).replace("\\", "/"),
            },
            "timings": {
                "composition_seconds": comp_time,
                "total_seconds": total_time,
            },
            "validation": validation,
            "audit_trail": selected.metadata.get("audit_trail", []),
        }

        # Write metadata JSON
        with open(out_meta, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        return metadata
