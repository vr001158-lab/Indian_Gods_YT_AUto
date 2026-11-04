# Telugu Production & Publishing Policy (Phase 2L)

## 1. Executive Summary

The **Divine Dharshanam Daily** automated pipeline is configured for **Telugu-only (`te-IN`) production and publishing**. All automated and manual production workflows generate, render, and upload Telugu content exclusively. Hindi (`hi-IN`) and other languages are disabled and rejected across all production safety gates.

Voice narration uses **Pocket TTS Telugu Female** (`prasadvittaldev/pocket-tts-telugu-female-syspin`) as the primary default voice provider, with Microsoft Edge Neural TTS (`te-IN-ShrutiNeural`) and Kokoro/Piper as fallback providers.

---

## 2. Publishing Schedule & Quotas

All publishing quotas are calculated using **`Asia/Kolkata`** (IST, UTC+05:30).

### Daily Shorts Quota (Maximum 2 per day)
* **Limit:** Exactly **2 Telugu Shorts per calendar day** in `Asia/Kolkata`.
* **Counting:** Counts only successful YouTube uploads recorded in `data/publishing_history.json`.
* **Slots:**
  * **Slot 1 (Morning Short):** 06:30 AM IST (01:00 UTC) every day.
  * **Slot 2 (Evening Short):** 06:30 PM IST (13:00 UTC) every day.
* **Format:** Vertical 9:16, 1080x1920, target 30–60s (max 180s).
* **Rejection:** Any attempt to publish a 3rd short on the same Kolkata calendar day is blocked before video composition and upload.

### Long-Video Quota (One Every 3 Days / Rolling 72-Hour Window)
* **Limit:** At most **one landscape long video per rolling 72-hour period**.
* **Counting:** Calculated from the timestamp of the last successful long-video upload.
* **Slot:** Every 3 days at 11:30 AM IST (06:00 UTC).
* **Interval:** If less than 72 hours have elapsed since the prior long-video upload, subsequent long-video uploads are blocked with the exact hours remaining reported.
* **Manual runs:** Workflow dispatch triggers cannot bypass the 72-hour rolling restriction.

### Daily Global Upload Ceiling
* No more than 2 total videos (Shorts + Long) can be published on any single calendar day in `Asia/Kolkata`.

---

## 3. Landscape Long-Video Profile & Assets

### Video Specifications
* **Canvas:** 1920x1080
* **Aspect Ratio:** 16:9 Landscape
* **Duration:**
  * Minimum: **120 seconds**
  * Maximum: **300 seconds**
  * Target: **180–240 seconds**
* **Audio:** 48,000 Hz, stereo AAC, Telugu narration with devotional background music attenuated at -22 dBFS.
* **Captions:** Burned Telugu subtitles (`resolve_caption_font('te-IN')`) placed in the bottom safe area (`y = 0.82 * height`, font size 36–38 pt, line length max 50 characters).

### Landscape Source Asset Directory Structure
Long videos select visual assets **strictly** from:

```text
assets/
└── gods_landscape_long_video/
    ├── 7Kondala_Swami/
    ├── ayyappa/
    ├── ganesha/
    ├── hanuman/
    ├── krishna/
    ├── lakshmi_devi/
    ├── lord_shiva/
    ├── lord_vishnu/
    ├── narasimha/
    ├── parvathi/
    ├── ram/
    └── subramanya/
```

### Asset Selection Rules
* **Strict Isolation:** Long-video visuals are selected exclusively from `assets/gods_landscape_long_video/<deity>/`.
* **No Fallback to Shorts Assets:** Under no circumstances does the long-video pipeline fall back to `assets/gods/`.
* **Orientation Validation:** Assets must have `width >= height`. Portrait assets (e.g. 9:16) placed in landscape folders are automatically rejected during scanning and validation.
* **Fail-Closed on Missing Assets:** If a deity folder contains no valid landscape assets, the pipeline halts gracefully and reports the missing assets instead of publishing distorted or incorrect visuals.

---

## 4. Quota Enforcement & Concurrency Architecture

### Pre-Upload Verification
1. **Pipeline Initiation:** `PipelineRunner.execute_pipeline()` verifies the language is `te-IN` and calls `check_publishing_quota()`.
2. **Final QA Gate:** `validate_qa_for_publishing()` verifies language, duration bounds, duplicate video records, and active quotas.
3. **Pre-Upload Lock:** `publish_video()` re-checks the quota immediately before calling `upload_to_youtube()` under a process-level file lock (`data/publishing_history.json.lock`).

### Atomic State Persistence
* `src/publisher/quota.record_successful_publish` uses cross-platform locking (`msvcrt.locking` on Windows, `fcntl.flock` on Linux).
* History is read under lock, quotas are re-validated, new entries are appended, and written via atomic file rename (`os.replace`).
* Malformed or corrupted history files fail closed with `ValueError` and are never wiped or reset.

### Dry Runs and Failures
* **Dry Runs (`--dry-run`):** Validate all pipeline steps and print quota status without performing uploads or modifying `publishing_history.json`. Dry runs do not consume quota.
* **Failed Uploads:** If the YouTube upload API raises an error or fails, no entry is added to `publishing_history.json`, preserving available quota for a subsequent run.

---

## 5. GitHub Actions Workflow Configuration

Workflow file: `.github/workflows/divine-dharshanam-daily.yml`

### Schedule (UTC vs IST)
| Job | IST (Asia/Kolkata) | UTC (GitHub Cron) | Frequency | Format |
|---|---|---|---|---|
| Slot 1 Short | 06:30 AM IST | `0 1 * * *` | Daily | 9:16 Vertical Short |
| Long Landscape Video | 11:30 AM IST | `0 6 */3 * *` | Every 3 Days | 16:9 Landscape Long |
| Slot 2 Short | 06:30 PM IST | `0 13 * * *` | Daily | 9:16 Vertical Short |

### Manual Execution (`workflow_dispatch`)
* **Content Type:** `short` or `long`
* **Format:** `narrated`
* **Language:** `te-IN` (Telugu only)
* **Dry Run:** `true` by default
