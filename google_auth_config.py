"""
google_auth_config.py — Central Google OAuth Configuration

Architecture:
  OAuth (token.json)  — used ONLY for authenticated YouTube publishing.
  YouTube API Key     — used for research (search.list, videos.list).
                        Public-data reads do NOT require OAuth.

Scope rationale:
  youtube.upload — videos.insert (upload to YouTube channel)
  drive.file     — optional Google Drive backup

NOTE: youtube.readonly is intentionally excluded.
  Research uses a public-data API key (YOUTUBE_API_KEY env var), not OAuth.
  Google rejects combined youtube.upload + youtube.readonly OAuth requests
  in this project's consent configuration.
"""

from pathlib import Path
import json
import sys
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

# ── Centralized OAuth scope set ───────────────────────────────────────────────
# All callers (upload + research) MUST use this exact list.
# Changing this list requires re-running refresh_token.py and updating TOKEN_JSON.
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",  # upload: videos.insert
    "https://www.googleapis.com/auth/drive.file",      # optional: Google Drive backup
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
    Load credentials from token_file, validate scopes, refresh if expired.

    Raises ValueError with clear re-authorization instructions if:
      - token.json is missing
      - token.json was issued without the required scopes
      - the token is expired and cannot be refreshed
    """
    if not token_file.exists():
        raise ValueError(
            "❌ Missing token.json. Please generate it locally using:\n"
            "       python refresh_token.py\n"
            "   Then update the TOKEN_JSON GitHub Secret with the new token.json."
        )

    # ── 1. Raw scope check BEFORE loading credentials ─────────────────────
    # Credentials.from_authorized_user_file() silently overwrites .scopes with
    # the requested list, making post-load scope checks unreliable for detecting
    # stale tokens. Read the JSON directly instead.
    token_scopes = _read_raw_scopes_from_file(token_file)
    required_scopes = set(SCOPES)

    if token_scopes and not required_scopes.issubset(token_scopes):
        missing = sorted(required_scopes - token_scopes)
        raise ValueError(
            f"\n❌ OAUTH SCOPE ERROR — token.json is missing required upload scopes.\n"
            f"   Missing scopes : {missing}\n"
            f"   Token has      : {sorted(token_scopes)}\n"
            f"   Required       : {sorted(required_scopes)}\n\n"
            f"   A refresh_token CANNOT upgrade its own scope set.\n"
            f"   👉 Fix (local): python refresh_token.py\n"
            f"   👉 Then update the TOKEN_JSON GitHub Secret with the new token.json."
        )

    # ── 2. Load credentials ────────────────────────────────────────────────
    creds = None
    try:
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    except Exception as e:
        raise ValueError(f"❌ Error reading token.json: {e}")

    # ── 3. Refresh if expired ──────────────────────────────────────────────
    if creds.expired and creds.refresh_token:
        print("🔄 Refreshing expired Google credentials...", file=sys.stderr)
        try:
            creds.refresh(Request())
            token_file.write_text(creds.to_json(), encoding="utf-8")
        except Exception as e:
            raise ValueError(
                f"❌ Failed to refresh expired token: {e}\n"
                f"   Run: python refresh_token.py   then update TOKEN_JSON."
            )
    elif not creds.valid:
        raise ValueError(
            "❌ Credentials are invalid and cannot be refreshed.\n"
            "   Run: python refresh_token.py   then update TOKEN_JSON."
        )

    return creds
