"""
google_auth_config.py — Central Google OAuth Configuration

Architecture:
  OAuth (token.json)  — used ONLY for authenticated YouTube publishing.
  YouTube API Key     — used for research (search.list, videos.list).
                        Public-data reads do NOT require OAuth.

Scope rationale:
  youtube.upload — videos.insert (upload to YouTube channel)

NOTE: drive.file and youtube.readonly are intentionally excluded.
  Research uses a public-data API key (YOUTUBE_API_KEY env var), not OAuth.
  Google Drive backup is disabled from the core production path.
"""

from pathlib import Path
import json
import os
import sys
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

# ── Centralized OAuth scope set ───────────────────────────────────────────────
# All callers (upload) MUST use this exact list.
# Changing this list requires re-running refresh_token.py and updating TOKEN_JSON.
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
]


CREDENTIALS_FILE = Path("credentials.json")
TOKEN_FILE = Path("token.json")


def _read_raw_scopes_from_file(token_file: Path) -> set:
    """
    Read the 'scopes' field directly from the token JSON file.

    Credentials.from_authorized_user_file() fills creds.scopes from the
    *requested* scopes argument, NOT from what is stored in the file.
    To detect stale/insufficient tokens we must read the raw JSON.
    Returns an empty set if the file is absent or the field is missing.
    """
    try:
        data = json.loads(token_file.read_text(encoding="utf-8"))
        raw = data.get("scopes", [])
        if isinstance(raw, list):
            return set(raw)
    except Exception:
        pass
    return set()


def get_google_credentials(
    token_file: Path = TOKEN_FILE,
    credentials_file: Path = CREDENTIALS_FILE,
) -> Credentials:
    """
    Load credentials from token_file or TOKEN_JSON env var, validate scopes, refresh if expired.

    Raises ValueError with clear re-authorization instructions if:
      - token.json and TOKEN_JSON env var are both missing
      - token was issued without the required scopes
      - the token is expired and cannot be refreshed
    """
    token_path = Path(token_file) if token_file is not None else TOKEN_FILE
    token_data = None

    if token_path.exists():
        try:
            token_data = json.loads(token_path.read_text(encoding="utf-8"))
        except Exception as e:
            raise ValueError(f"❌ Error reading token.json: {e}")
    elif "TOKEN_JSON" in os.environ and os.environ["TOKEN_JSON"].strip():
        try:
            token_data = json.loads(os.environ["TOKEN_JSON"].strip())
        except Exception as e:
            raise ValueError(f"❌ Error parsing TOKEN_JSON environment variable: {e}")
    else:
        raise ValueError(
            "❌ Missing OAuth token. Please generate it locally using:\n"
            "       python refresh_token.py\n"
            "   Then update the TOKEN_JSON GitHub Secret with the new token.json."
        )

    # ── 1. Structural check on parsed token data ──────────────────────────
    if not isinstance(token_data, dict):
        raise ValueError("❌ Invalid OAuth credentials: token data is not a valid JSON dictionary.")

    # ── 2. Raw scope check BEFORE loading credentials ─────────────────────
    raw_scopes = token_data.get("scopes")
    if raw_scopes is None:
        raise ValueError(
            "❌ OAUTH SCOPE ERROR — token is missing required 'scopes' metadata.\n"
            "   Run: python refresh_token.py   then update TOKEN_JSON."
        )

    token_scopes = set(raw_scopes) if isinstance(raw_scopes, list) else set(raw_scopes.split()) if isinstance(raw_scopes, str) else set()
    if not token_scopes:
        raise ValueError(
            "❌ OAUTH SCOPE ERROR — token 'scopes' metadata is empty.\n"
            "   Run: python refresh_token.py   then update TOKEN_JSON."
        )

    required_scopes = set(SCOPES)
    if not required_scopes.issubset(token_scopes):
        missing = sorted(required_scopes - token_scopes)
        raise ValueError(
            f"\n❌ OAUTH SCOPE ERROR — token is missing required upload scopes.\n"
            f"   Missing scopes : {missing}\n"
            f"   Token has      : {sorted(token_scopes)}\n"
            f"   Required       : {sorted(required_scopes)}\n\n"
            f"   A refresh_token CANNOT upgrade its own scope set.\n"
            f"   👉 Fix (local): python refresh_token.py\n"
            f"   👉 Then update the TOKEN_JSON GitHub Secret with the new token.json."
        )

    # ── 3. Load credentials using Google Auth Library ──────────────────────
    creds = None
    try:
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        else:
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
    except Exception as e:
        raise ValueError(f"❌ Error constructing Google OAuth credentials: {e}")

    # ── 4. Validate refresh capability and refresh if expired ──────────────
    if creds.expired and creds.refresh_token:
        print("🔄 Refreshing expired Google credentials...", file=sys.stderr)
        try:
            creds.refresh(Request())
            if token_path.exists():
                try:
                    token_path.write_text(creds.to_json(), encoding="utf-8")
                except Exception:
                    pass
        except Exception as e:
            raise ValueError(
                f"❌ Failed to refresh expired token: {e}\n"
                f"   Run: python refresh_token.py   then update TOKEN_JSON."
            )
    elif creds.expired and not creds.refresh_token:
        raise ValueError(
            "❌ Expired credentials lack a refresh_token and cannot be refreshed.\n"
            "   Run: python refresh_token.py   then update TOKEN_JSON."
        )
    elif not creds.valid:
        raise ValueError(
            "❌ Credentials are invalid and cannot be refreshed.\n"
            "   Run: python refresh_token.py   then update TOKEN_JSON."
        )

    # Reject access-token-only credentials that cannot support automated refresh
    if not getattr(creds, "refresh_token", None):
        raise ValueError(
            "❌ Missing 'refresh_token' in OAuth credentials.\n"
            "   Access-token-only credentials cannot be refreshed for automated production runs.\n"
            "   Run: python refresh_token.py   then update TOKEN_JSON."
        )

    return creds
