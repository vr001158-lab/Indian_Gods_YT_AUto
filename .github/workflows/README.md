# GitHub Actions Production Automation — Divine Dharshanam Daily

## Overview

The Divine Dharshanam Daily automated workflow (`divine-dharshanam-daily.yml`) executes daily multilingual content generation and YouTube publishing.

---

## Required GitHub Secrets

Configure the following secrets in **Repository Settings → Secrets and variables → Actions**:

| Secret Name | Required | Purpose | Where Used |
| :--- | :---: | :--- | :--- |
| `TOKEN_JSON` | **Yes** | Authorized OAuth refresh token and credentials JSON string. | Reconstructed into `token.json` for YouTube Data API v3 publishing. |
| `CREDENTIALS_JSON` | **Yes** | Client ID and Client Secret JSON string for Google OAuth. | Reconstructed into `credentials.json` for token refresh. |
| `YOUTUBE_API_KEY` | Optional | YouTube Data API v3 key for public data research lookups. | Used by `src/research` module for video trend discovery. |

> **IMPORTANT**: Never commit raw credential values to code or documentation. GitHub Actions Secrets are injected securely at runtime.

---

## Required GitHub Variables

Configure the following environment variables in **Repository Settings → Secrets and variables → Actions → Variables**:

| Variable Name | Default | Purpose |
| :--- | :---: | :--- |
| `CONTENT_TYPE` | `short` | Default content format for scheduled runs (`short`: 1080x1920 9:16 | `long`: 1920x1080 16:9). |

---

## Schedule & Timezone

- **Schedule**: Daily at `04:00 UTC` (`0 4 * * *`).
- **Timezone Conversion**: `04:00 UTC` corresponds to **`09:30 AM IST`** (Indian Standard Time, UTC+5:30).

---

## Manual Trigger (`workflow_dispatch`)

You can manually trigger a production run at any time via the GitHub Actions UI:

1. Navigate to **Actions → Divine Dharshanam Daily — Production Automated Pipeline**.
2. Click **Run workflow**.
3. Select parameters:
   - **Content Format**: `short` or `long`.
   - **Target Language**: `hi-IN`, `te-IN`, or `ta-IN`.
   - **Dry Run Mode**: Check `true` to stop before YouTube upload.

---

## Workflow Execution Steps & Safety Gates

```
1. Checkout & Setup Environment
2. Install System Dependencies & FFmpeg
3. Reconstruct token.json securely
4. Run Unit Test Suite (420+ tests) ──[ FAIL ]──> STOP (No upload)
5. Run Canonical Pipeline (run_pipeline.py)
   ├── Research → Decision → Brief → Script → Voice → Visuals → Video → Thumbnail
   ├── Final QA Gate ────────────────[ FAIL ]──> STOP (No upload)
   └── Duplicate Protection ──────────[ FAIL ]──> STOP (No upload)
6. Upload to YouTube [PRIVATE STATUS ONLY]
7. Upload Custom 16:9 / 9:16 Thumbnail
8. Commit Updated publishing_history.json
```

---

## Privacy & Safety Policy

- **Upload Privacy**: **PRIVATE** (Hard-coded and non-negotiable). Automated runs **NEVER** publish content publicly.
- **Concurrency Protection**: Enabled (`cancel-in-progress: false`). Prevents simultaneous production runs from creating duplicate content.
- **Ephemeral State Persistence**: Lightweight state (`data/publishing_history.json`) is committed after successful runs to ensure duplicate protection functions across ephemeral runners.

---

## Recovery Procedure

If a workflow run fails:

1. **Check Logs**: Inspect the GitHub Actions run log to identify the failing stage (e.g. Test failure, QA rejection, or API rate limit).
2. **Local Debugging**: Run the canonical pipeline locally with `--dry-run`:
   ```bash
   python run_pipeline.py --content-type short --dry-run
   ```
3. **Re-run Workflow**: After fixing issues, trigger the workflow manually using `workflow_dispatch`.
