"""
google_auth_config.py — Central Google OAuth Configuration
Defines required scopes and common authentication logic for YouTube & Google Drive.
"""

from pathlib import Path
import json
import sys
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

# Centralized scopes required by the system
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/drive.file"
]

CREDENTIALS_FILE = Path("credentials.json")
TOKEN_FILE = Path("token.json")

def get_google_credentials(token_file: Path = TOKEN_FILE, credentials_file: Path = CREDENTIALS_FILE) -> Credentials:
    """
    Load credentials from token_file, refresh if expired, and validate scopes.
    Raises ValueError if scopes are incompatible or credentials cannot be authorized.
    """
    creds = None
    if token_file.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
        except Exception as e:
            print(f"⚠️ Error reading existing token file: {e}", file=sys.stderr)
            creds = None

    if creds:
        # Check scope compatibility
        token_scopes = set(creds.scopes or [])
        required_scopes = set(SCOPES)
        if not required_scopes.issubset(token_scopes):
            raise ValueError(
                f"❌ CRITICAL AUTH ERROR: Existing token.json has incompatible scopes.\n"
                f"Required: {SCOPES}\n"
                f"Found: {list(token_scopes)}\n"
                f"👉 Fix: Please delete token.json and run 'python refresh_token.py' again."
            )

        # Refresh token if expired
        if creds.expired and creds.refresh_token:
            print("🔄 Refreshing expired Google credentials...", file=sys.stderr)
            try:
                creds.refresh(Request())
                token_file.write_text(creds.to_json())
            except Exception as e:
                raise ValueError(f"❌ Failed to refresh expired token: {e}. Please reauthorize.")
        elif not creds.valid:
            raise ValueError("❌ Credentials are invalid. Please reauthorize by running refresh_token.py.")
    else:
        # If credentials are not present at all
        raise ValueError(
            "❌ Missing token.json. Please generate it locally using refresh_token.py "
            "and configure the TOKEN_JSON secret in GitHub Actions."
        )

    return creds
