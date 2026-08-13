"""
Run this ONCE locally to generate a fresh token.json.
Then copy the contents into GitHub Secrets as TOKEN_JSON.

Usage:
    pip install google-auth-oauthlib google-auth
    python refresh_token.py
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
    print("1. Copy the contents of token.json")
    print("2. Go to your GitHub repo → Settings → Secrets and variables → Actions")
    print("3. Create a secret named: TOKEN_JSON")
    print("4. Paste the token.json contents as the value")
    print("5. Add token.json to .gitignore and DELETE it locally")

    print("\n📄 token.json contents:\n")
    print(token_path.read_text())


if __name__ == "__main__":
    main()