"""
refresh_token.py — Local OAuth re-authorization tool.

Run this ONCE locally whenever:
  - You need to generate a new token.json for the first time
  - You have added new OAuth scopes to google_auth_config.SCOPES
  - The existing token.json is missing scopes (yields HTTP 403 from the API)

Usage:
    python refresh_token.py

The script opens a browser for Google consent and writes token.json locally.
NEVER commit token.json to Git.
After running, copy the token.json contents into the TOKEN_JSON GitHub Secret.
"""

from google_auth_oauthlib.flow import InstalledAppFlow
from pathlib import Path
import json
import sys

import google_auth_config

def main():
    # Support both client_secret.json and credentials.json
    secret_path = Path("client_secret.json")
    if not secret_path.exists():
        secret_path = Path("credentials.json")

    if not secret_path.exists():
        print("❌ ERROR: Neither client_secret.json nor credentials.json was found in the current directory.")
        print("   Please download client secrets from Google Cloud Console and save as credentials.json.")
        sys.exit(1)

    print(f"🔑 Using client secrets from: {secret_path}")
    flow = InstalledAppFlow.from_client_secrets_file(
        str(secret_path),
        google_auth_config.SCOPES
    )

    # 🔥 IMPORTANT: force refresh token generation
    creds = flow.run_local_server(
        port=0,
        access_type="offline",   # REQUIRED for refresh_token
        prompt="consent"         # FORCE Google to show consent screen
    )

    token_path = Path("token.json")
    token_path.write_text(creds.to_json())

    # ✅ Validate refresh token exists
    token_data = json.loads(token_path.read_text())

    print("\n==============================")
    print("✅ token.json generated successfully!")
    print("==============================\n")

    if "refresh_token" in token_data:
        print("🔥 SUCCESS: Refresh token is present (PERMANENT access enabled)")
    else:
        print("⚠️ WARNING: No refresh_token found!")
        print("👉 Fix: Revoke app access and run again")

    print("\nNext steps:")
    print("1. Open token.json in a text editor (do NOT share it publicly).")
    print("2. Copy its full contents.")
    print("3. Go to: GitHub repo → Settings → Secrets and variables → Actions")
    print("4. Update (or create) secret named: TOKEN_JSON")
    print("5. Paste the token.json contents as the secret value.")
    print("6. Ensure token.json is in .gitignore and DELETE it locally after updating the secret.")
    print("\n⚠️  Do NOT print or share token.json contents in logs or chat.")


if __name__ == "__main__":
    main()