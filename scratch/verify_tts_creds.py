"""Verify Google Cloud TTS credentials without printing secrets."""
import os
import sys
from pathlib import Path

gac = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
api_key = os.environ.get("GOOGLE_CLOUD_TTS_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")

if gac:
    p = Path(gac)
    if p.exists():
        print("CREDENTIAL_SOURCE: GOOGLE_APPLICATION_CREDENTIALS")
        print("CREDENTIAL_STATUS: OK")
        sys.exit(0)
    print("CREDENTIAL_SOURCE: GOOGLE_APPLICATION_CREDENTIALS")
    print("CREDENTIAL_STATUS: FAIL (path missing)")
    sys.exit(1)

if api_key:
    print("CREDENTIAL_SOURCE: API_KEY")
    print("CREDENTIAL_STATUS: OK")
    sys.exit(0)

try:
    import google.auth
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    if creds:
        print("CREDENTIAL_SOURCE: ADC")
        print("CREDENTIAL_STATUS: OK")
        sys.exit(0)
except Exception as exc:
    print(f"CREDENTIAL_STATUS: FAIL ({type(exc).__name__})")
    sys.exit(1)

print("CREDENTIAL_STATUS: FAIL (no credentials found)")
sys.exit(1)
