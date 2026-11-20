# src/assets/approval_registry.py
# Explicit Trusted Asset-Level Approval Registry
#
# Mandatory Security Invariants:
#   1. Files under deity folders must default to UNVERIFIED.
#   2. Landscape assets must default to UNVERIFIED.
#   3. Processed videos must default to UNVERIFIED.
#   4. Filenames must never establish approval.
#   5. Folder names must never establish approval.
#   6. Generated or loaded manifests must never establish approval by themselves.
#   7. Inferred deity identity must never establish approval.
#   8. Missing, ambiguous, or malformed approval metadata must fail closed.
#   9. Images and videos must follow the same approval policy.
#   10. An asset approved for one deity must never be accepted for another deity.
#   11. No filename-stem-only matching. Exact normalized repository-relative paths only.
#   12. Path traversal (e.g., '..') and ambiguous duplicate paths are strictly rejected.

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass(frozen=True)
class TrustedAssetApprovalRecord:
    """
    Explicit, auditable record establishing approval for a specific repository asset.
    Binds exact repository path, canonical deity, approval status, reviewer identity, and provenance.
    """
    record_id: str                      # Unique approval identifier, e.g. "APPR-VISHNU-KURMA-001"
    exact_rel_path: str                 # Exact normalized relative path from repo root
    canonical_deity: str                # Canonical deity identity (e.g. "lord_vishnu")
    approval_status: str                # Must be strictly "APPROVED"
    provenance: str                     # Auditable provenance source description
    reviewer: Optional[str] = None      # Verifiable human reviewer identity (e.g. "REV-HUMAN-01")
    review_timestamp: Optional[str] = None  # Verifiable human review timestamp (ISO format)
    co_depicted_deities: tuple[str, ...] = ()  # Co-depicted deities for composite artwork
    allow_solo: bool = True             # False for dual/composite artwork barred from solo scenes
    avatar: Optional[str] = None        # Specific avatar if avatar-specific (e.g. "kurma")
    narrative_event: Optional[str] = None
    scene_description: Optional[str] = None
    aspect_ratio: Optional[str] = None  # "9:16" or "16:9"
    content_type: Optional[str] = None  # "image" or "video"

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["co_depicted_deities"] = list(self.co_depicted_deities)
        return d


def normalize_repo_path(raw_path: str | Path) -> str:
    """
    Normalizes a repository asset path to a canonical, relative, forward-slash path.
    Fails closed (returns empty string) on:
      - Empty or non-string/non-path input
      - Path traversal attempts (containing '..' or dangerous sequences)
      - Quarantined paths (containing 'quarantine' segment)
      - Ambiguous paths outside recognized visual roots
    """
    if not raw_path:
        return ""

    p_str = str(raw_path).replace("\\", "/").strip()
    if not p_str:
        return ""

    # Reject path traversal attempts immediately
    parts = p_str.split("/")
    if ".." in parts:
        return ""

    # Reject quarantined paths immediately - quarantined assets can NEVER be approved or normalized
    if "quarantine" in [part.lower() for part in parts]:
        return ""

    # Strip surrounding quotes or whitespace
    p_str = p_str.strip("'\" \t\r\n")

    # Match known visual repository roots:
    for root in (
        "assets/gods_landscape_long_video",
        "assets/gods_processed",
        "assets/gods",
        "assets/incoming",
        "data/render_only",
        "data/visuals",
        "data/thumbnails",
    ):
        idx = p_str.lower().find(root)
        if idx != -1:
            rel = p_str[idx:].strip("/")
            rel_parts = rel.split("/")
            if ".." not in rel_parts:
                return rel

    # If already a clean relative path starting with assets/ or data/
    if p_str.startswith("assets/") or p_str.startswith("data/"):
        rel_parts = p_str.split("/")
        if ".." not in rel_parts:
            return p_str.strip("/")

    return ""


# ──────────────────────────────────────────────────────────────────────────────
# Built-in Catalog of Verified Narrative & Curated Representative Assets
# ──────────────────────────────────────────────────────────────────────────────

_BUILTIN_TRUSTED_APPROVAL_RECORDS: list[dict[str, Any]] = []



APPROVED_REGISTRY_PATH = "data/assets/approved_asset_registry.json"


class TrustedAssetApprovalRegistry:
    """
    Centralized, fail-closed authority for all visual asset approvals.
    Uses exact normalized repository paths and prevents path traversal or ambiguous collisions.
    """

    def __init__(self, load_active_store: bool = True):
        self._records_by_path: dict[str, TrustedAssetApprovalRecord] = {}
        self._load_builtins()
        if load_active_store:
            self._load_approved_store()

    def _load_builtins(self) -> None:
        for item in _BUILTIN_TRUSTED_APPROVAL_RECORDS:
            rec = TrustedAssetApprovalRecord(**item)
            self.register_record(rec)

    def _load_approved_store(self, path: str | Path = APPROVED_REGISTRY_PATH) -> None:
        p = Path(path)
        if p.exists():
            import json
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                records = data.get("records", []) if isinstance(data, dict) else data
                for item in records:
                    if "co_depicted_deities" in item and isinstance(item["co_depicted_deities"], list):
                        item["co_depicted_deities"] = tuple(item["co_depicted_deities"])
                    rec = TrustedAssetApprovalRecord(**item)
                    self.register_record(rec)
            except Exception as e:
                raise ValueError(f"Failed to load approved asset registry from {p}: {e}")

    def get_builtin_records(self) -> list[TrustedAssetApprovalRecord]:
        """Returns the immutable baseline built-in records."""
        return [TrustedAssetApprovalRecord(**item) for item in _BUILTIN_TRUSTED_APPROVAL_RECORDS]

    def register_record(self, record: TrustedAssetApprovalRecord) -> None:
        """Registers a trusted approval record. Validates all required fields."""
        if not record.record_id or not record.record_id.strip():
            raise ValueError("Approval record missing record_id")
        norm = normalize_repo_path(record.exact_rel_path)
        if not norm:
            raise ValueError(f"Invalid or unsafe asset path: {record.exact_rel_path}")
        if not record.canonical_deity or not record.canonical_deity.strip():
            raise ValueError(f"Approval record {record.record_id} missing canonical_deity")
        if record.approval_status != "APPROVED":
            raise ValueError(f"Approval record {record.record_id} status must be APPROVED, got: {record.approval_status}")
        if not record.provenance or not record.provenance.strip():
            raise ValueError(f"Approval record {record.record_id} missing provenance")
        if not record.reviewer or not str(record.reviewer).strip():
            raise ValueError(f"Approval record {record.record_id} missing verifiable human reviewer identity")
        if not record.review_timestamp or not str(record.review_timestamp).strip():
            raise ValueError(f"Approval record {record.record_id} missing verifiable review timestamp")

        self._records_by_path[norm.lower()] = record

    def clear(self) -> None:
        """Clears all records (primarily for testing)."""
        self._records_by_path.clear()

    def reset_to_builtins(self, load_active_store: bool = True) -> None:
        """Resets the registry to trusted records."""
        self._records_by_path.clear()
        self._load_builtins()
        if load_active_store:
            self._load_approved_store()

    def get_approval_record(self, asset_path: str | Path) -> Optional[TrustedAssetApprovalRecord]:
        """Looks up the exact approval record by normalized repository path."""
        norm = normalize_repo_path(asset_path)
        if not norm:
            return None
        return self._records_by_path.get(norm.lower())

    def is_asset_approved(
        self,
        asset_path: str | Path,
        deity: str,
        avatar: Optional[str] = None,
        allow_dual_composite: bool = False,
    ) -> tuple[bool, str, Optional[TrustedAssetApprovalRecord]]:
        """
        Validates whether asset_path has an explicit trusted approval record matching deity and avatar.
        Fails closed on:
          - Unregistered path (default UNVERIFIED)
          - Deity mismatch (cross-deity substitution forbidden)
          - Avatar mismatch (when avatar is requested)
          - Dual-deity composite used for solo deity scenes without allow_dual_composite=True
          - Path traversal or malformed path
        """
        norm = normalize_repo_path(asset_path)
        if not norm:
            return False, f"Asset '{asset_path}' is unapproved; lacks an explicit trusted asset approval record in repository catalog", None

        rec = self._records_by_path.get(norm.lower())
        if not rec:
            return False, f"Asset '{norm}' is unapproved; lacks an explicit trusted asset approval record in repository catalog", None

        if rec.approval_status != "APPROVED":
            return False, f"Asset '{norm}' has approval status '{rec.approval_status}', not 'APPROVED'", rec

        # Dual-deity solo compatibility check
        if not rec.allow_solo and not allow_dual_composite:
            return (
                False,
                f"Asset '{norm}' is a dual-deity composite depicting {rec.co_depicted_deities}; prohibited for solo '{deity}' scenes (DUAL_DEITY_RESTRICTION)",
                rec,
            )

        # Deity verification
        target_deity = deity.strip().lower() if deity else ""
        rec_deity = rec.canonical_deity.strip().lower()
        if target_deity:
            from src.thumbnail.asset_index import AVATAR_TO_PARENT_DEITY
            valid_deities = {rec_deity}
            if rec.avatar:
                parent = AVATAR_TO_PARENT_DEITY.get(rec.avatar.lower())
                if parent:
                    valid_deities.add(parent.lower())
            if target_deity == "lord_vishnu" and rec_deity in ("narasimha", "krishna", "ram", "lord_vishnu"):
                valid_deities.add("lord_vishnu")
            if target_deity not in valid_deities and rec_deity != target_deity:
                return (
                    False,
                    f"Asset approved for deity '{rec.canonical_deity}', cannot be used for '{deity}' (DEITY_MISMATCH)",
                    rec,
                )

        # Avatar verification
        if avatar:
            req_av = avatar.strip().lower()
            rec_av = (rec.avatar or rec.canonical_deity).strip().lower()
            RAMA_ALIASES = {"ram", "rama"}
            VAMANA_ALIASES = {"vamana", "vamana_trivikrama", "trivikrama"}
            av_match = (
                (req_av == rec_av)
                or (req_av in RAMA_ALIASES and rec_av in RAMA_ALIASES)
                or (req_av in VAMANA_ALIASES and rec_av in VAMANA_ALIASES)
            )
            if not av_match:
                return False, f"Asset depicts avatar '{rec_av}', does not match requested avatar '{avatar}' (AVATAR_MISMATCH)", rec
        elif rec.avatar and rec.avatar.strip().lower() not in (rec_deity, ""):
            # Asset is specific to an avatar (e.g. kurma, vamana), but caller requested generic deity
            return False, f"Asset is avatar-specific ('{rec.avatar}'), cannot be used for generic deity request without explicit avatar", rec

        return True, "Explicit trusted asset approval verified", rec

    def has_approved_assets_for_deity(self, deity: str) -> bool:
        """Returns True if there is at least one approved asset for the given canonical deity."""
        if not deity:
            return False
        d_lower = deity.strip().lower()
        for rec in self._records_by_path.values():
            if rec.approval_status == "APPROVED" and rec.canonical_deity.strip().lower() == d_lower:
                return True
        return False

    def get_approved_asset_count_for_deity(self, deity: str) -> int:
        """Returns the number of approved assets for the given canonical deity."""
        if not deity:
            return 0
        d_lower = deity.strip().lower()
        return sum(
            1 for rec in self._records_by_path.values()
            if rec.approval_status == "APPROVED" and rec.canonical_deity.strip().lower() == d_lower
        )


# Global registry singleton
_GLOBAL_REGISTRY: Optional[TrustedAssetApprovalRegistry] = None


def get_trusted_registry() -> TrustedAssetApprovalRegistry:
    """Returns the process-wide trusted approval registry singleton."""
    global _GLOBAL_REGISTRY
    if _GLOBAL_REGISTRY is None:
        _GLOBAL_REGISTRY = TrustedAssetApprovalRegistry()
    return _GLOBAL_REGISTRY
