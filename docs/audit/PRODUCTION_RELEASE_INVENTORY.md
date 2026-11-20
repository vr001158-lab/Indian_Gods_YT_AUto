# PRODUCTION RELEASE INVENTORY — DIVINE DARSHANAM DAILY
**Telugu Devotional AI Automation & Production Intelligence Engine**<br>
*Inventory Timestamp: 2026-11-11T22:25:00+05:30*<br>
*Repository: `Indian_Gods_YT_AUto`*<br>
*Target Channel: `@Divine_Dharshan_om` (Divine Dharshanam Daily)*<br>
*Production Language: STRICTLY Telugu (`te-IN`)*<br>

---

## 1. Executive Summary

This inventory prepares the repository for its first controlled production release following the completion of the Telugu Content Intelligence upgrade, defect remediations (DEF-01 through DEF-04), visual narrative asset acquisitions, and deployment-readiness auditing.

### Release Invariants Observed
- **Strictly Telugu-Only:** All content, blueprints, metadata, and QA enforcement are constrained to `te-IN`.
- **Zero Premature Deployment:** No files staged, no commits created, no branches pushed, no YouTube videos uploaded.
- **Asset Integrity Preserved:** All user files, generated images, scratch scripts, and manifests remain intact.

---

## 2. Git Working Tree State

### 2.1 Git Status Short (`git status --short`)
```text
 M data/assets/asset_manifest.json
 M data/assets/landscape_asset_manifest.json
 M src/assets/scanner.py
 M src/assets/selector.py
 M src/content/brief_generator.py
 M src/content/gemini_provider.py
 M src/decision/report.py
 M src/decision/strategy.py
 M src/pipeline/orchestrator.py
 M src/qa/gate.py
 M src/research/collector.py
 M src/script/generator.py
 M src/voice/generator.py
?? DEPLOYMENT_READINESS_AUDIT.md
?? FINAL_INTEGRATION_VERIFICATION.md
?? FINAL_VISUAL_AND_PUBLISHER_AUDIT.md
?? INDEPENDENT_PRODUCTION_READINESS_AUDIT.md
?? PRODUCTION_RELEASE_INVENTORY.md
?? RELEASE_CANDIDATE_REVIEW.md
?? REMEDIATION_REPORT.md
?? SCRIPT_QA_GUIDE.md
?? SOURCE_VERIFICATION_GUIDE.md
?? TELUGU_CONTENT_INTELLIGENCE.md
?? UPGRADE_AUDIT_REPORT.md
?? UPGRADE_CHANGELOG.md
?? VISUAL_ASSET_COMPLETION_REPORT.md
?? assets/gods/krishna/krishna_lifting_govardhan_hill_with_finger.png
?? assets/gods/lord_vishnu/kurma_avatar_mandara_mountain_samudra_manthan.png
?? assets/gods/lord_vishnu/vamana_trivikrama_three_strides_bali.png
?? assets/gods/narasimha/narasimha_emerging_from_pillar_prahlada.png
?? assets/gods_landscape_long_video/hanuman/hanuman_carrying_dronagiri_sanjeevani_landscape.png
?? assets/gods_landscape_long_video/krishna/krishna_lifting_govardhan_hill_with_finger_landscape.png
?? assets/gods_landscape_long_video/lord_vishnu/kurma_avatar_mandara_mountain_samudra_manthan_landscape.png
?? assets/gods_landscape_long_video/lord_vishnu/vamana_trivikrama_three_strides_bali_landscape.png
?? assets/gods_landscape_long_video/narasimha/narasimha_emerging_from_pillar_prahlada_landscape.png
?? assets/music/devotional/youtube_audio_library_aalaap_jhinjhoti.mp3
?? scratch/caption_hi.txt
?? scratch/check_annotations.py
?? scratch/check_github_runs.py
?? scratch/check_run_details.py
?? scratch/check_run_jobs.py
?? scratch/compose_all_deity_devotional_music.py
?? scratch/download_run_logs.py
?? scratch/fetch_job_logs.py
?? scratch/monitor_run.py
?? scratch/monitor_run_171.py
?? scratch/probe_gemini_models.py
?? scratch/probe_gemini_models_v2.py
?? scratch/probe_music.py
?? scratch/render_rc_videos.py
?? scratch/render_real_old_video.py
?? scratch/render_retention_videos.py
?? scratch/run_170_logs.txt
?? scratch/run_all_suites_report.py
?? scratch/run_latest_logs.txt
?? scratch/smoke_test_pocket_tts.py
?? scratch/test_synthesized_offline_fallback.py
?? scratch/trigger_workflow_dispatch.py
?? scratch/update_blueprints_clean_narration.py
?? scratch/update_manifest.py
?? scratch/update_manifest_pixabay.py
?? scratch/update_manifest_pixabay_v2.py
?? scratch/verify_5_visual_scenarios.py
?? scratch/verify_final_music.py
?? scratch/verify_rc_assets.py
?? scratch/verify_review.py
?? src/content/telugu_blueprints.py
?? src/decision/feedback.py
?? src/research/scriptural_source_registry.py
?? src/script/script_factuality_validator.py
?? src/script/script_qa_gate.py
?? src/script/script_quality_evaluator.py
?? src/script/script_retention_optimizer.py
?? tests/test_content_intelligence.py
?? tests/test_publisher_dry_run_safety.py
?? tests/test_remediation_defects.py
```

### 2.2 Git Diff Stat (`git diff --stat`)
```text
 data/assets/asset_manifest.json           | 17884 ++++++++++++++++++++++++----
 data/assets/landscape_asset_manifest.json |   324 +-
 src/assets/scanner.py                     |   159 +
 src/assets/selector.py                    |   256 +-
 src/content/brief_generator.py            |     4 +
 src/content/gemini_provider.py            |    19 +
 src/decision/report.py                    |    27 +-
 src/decision/strategy.py                  |   105 +-
 src/pipeline/orchestrator.py              |    20 +
 src/qa/gate.py                            |    30 +
 src/research/collector.py                 |    20 +-
 src/script/generator.py                   |    23 +-
 src/voice/generator.py                    |    21 +
 13 files changed, 16546 insertions(+), 2346 deletions(-)
```

### 2.3 Git Diff Check (`git diff --check`)
- Output: Empty (0 whitespace, trailing space, or carriage-return syntax errors).

---

## 3. Comprehensive File Inventory & Classification

### Summary of Counts by Category

| Category | File Count | Description |
| :--- | :---: | :--- |
| **1. Required Production Code** | **18** | 11 modified core modules + 7 new production modules in `src/` |
| **2. Tests** | **3** | New automated unit and safety test suites in `tests/` |
| **3. Required Narrative Assets** | **10** | 4 vertical PNGs + 5 landscape PNGs + 1 devotional MP3 audio |
| **4. Asset Manifests** | **2** | 2 modified JSON manifests tracking vertical and landscape visual metadata |
| **5. Documentation** | **13** | 13 audit, architectural, verification, and QA guide markdown reports |
| **6. Rendered MP4 Outputs** | **0** | All MP4 outputs are excluded from git tracking by `.gitignore` |
| **7. Temporary Scripts & Scratch** | **30** | One-off inspection, probe, log, and rendering scripts in `scratch/` |
| **Total Tracked & Untracked Files** | **76** | (13 modified tracked + 63 untracked) |

---

### Category 1: Required Production Code (18 Files)

#### Modified Tracked Modules (11 Files)
1. [`src/assets/scanner.py`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/src/assets/scanner.py) (15,844 B) — Scanner supporting landscape asset directories and narrative metadata.
2. [`src/assets/selector.py`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/src/assets/selector.py) (28,321 B) — Strict avatar/narrative matching and missing semantic fallback flagging.
3. [`src/content/brief_generator.py`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/src/content/brief_generator.py) (21,507 B) — Telugu blueprint routing and scriptural source integration.
4. [`src/content/gemini_provider.py`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/src/content/gemini_provider.py) (51,065 B) — Strict Telugu prompts, Indic citations, and 429 exponential backoff.
5. [`src/decision/report.py`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/src/decision/report.py) (8,643 B) — Feedback loop reporting integration.
6. [`src/decision/strategy.py`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/src/decision/strategy.py) (4,811 B) — Performance-weighted deity and topic selection logic.
7. [`src/pipeline/orchestrator.py`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/src/pipeline/orchestrator.py) (20,801 B) — Pre-Voice QA gate execution in canonical pipeline before voice synthesis.
8. [`src/qa/gate.py`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/src/qa/gate.py) (16,424 B) — Final multi-gate QA validator with Telugu-specific scoring.
9. [`src/research/collector.py`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/src/research/collector.py) (18,704 B) — Scriptural source registry connection and offline fallback mode.
10. [`src/script/generator.py`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/src/script/generator.py) (50,033 B) — Telugu script generator with pre-voice factuality and quality evaluation.
11. [`src/voice/generator.py`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/src/voice/generator.py) (23,912 B) — Hard pre-voice safety gate preventing TTS generation for unapproved scripts.

#### New Production Modules (Untracked) (7 Files)
12. [`src/content/telugu_blueprints.py`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/src/content/telugu_blueprints.py) (127,212 B) — Canonical Telugu devotional story blueprints and scene structures.
13. [`src/decision/feedback.py`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/src/decision/feedback.py) (4,142 B) — Historical publishing feedback engine for weighted topic selection.
14. [`src/research/scriptural_source_registry.py`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/src/research/scriptural_source_registry.py) (27,492 B) — Authenticated Vedic and Puranic source registry.
15. [`src/script/script_factuality_validator.py`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/src/script/script_factuality_validator.py) (5,389 B) — Scriptural factuality and theological verification engine.
16. [`src/script/script_qa_gate.py`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/src/script/script_qa_gate.py) (8,775 B) — Pre-Voice QA gate verifying language, length, factuality, and tone.
17. [`src/script/script_quality_evaluator.py`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/src/script/script_quality_evaluator.py) (5,292 B) — Telugu linguistic, prosodic, and devotional tone evaluator.
18. [`src/script/script_retention_optimizer.py`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/src/script/script_retention_optimizer.py) (10,397 B) — Pacing, hook scoring, and audience retention structure optimizer.

---

### Category 2: Tests (3 Files)

#### New Production Test Suites (Untracked) (3 Files)
1. [`tests/test_content_intelligence.py`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/tests/test_content_intelligence.py) (17,262 B) — Tests for Telugu content blueprints, scriptural registry, and feedback.
2. [`tests/test_publisher_dry_run_safety.py`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/tests/test_publisher_dry_run_safety.py) (4,895 B) — Tests verifying zero uploads occur in dry-run mode.
3. [`tests/test_remediation_defects.py`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/tests/test_remediation_defects.py) (11,490 B) — Regression tests for DEF-01, DEF-02, DEF-03, and DEF-04.

---

### Category 3: Required Narrative Assets (10 Files)

#### Vertical 9:16 Images for Telugu Shorts (Untracked) (4 Files)
1. [`assets/gods/krishna/krishna_lifting_govardhan_hill_with_finger.png`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/assets/gods/krishna/krishna_lifting_govardhan_hill_with_finger.png) (1,918,940 B, 768×1376) — Lord Krishna holding Mount Govardhan on little finger.
2. [`assets/gods/lord_vishnu/kurma_avatar_mandara_mountain_samudra_manthan.png`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/assets/gods/lord_vishnu/kurma_avatar_mandara_mountain_samudra_manthan.png) (2,235,719 B, 768×1376) — Kurma avatar tortoise supporting Mount Mandara.
3. [`assets/gods/lord_vishnu/vamana_trivikrama_three_strides_bali.png`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/assets/gods/lord_vishnu/vamana_trivikrama_three_strides_bali.png) (2,075,828 B, 736×1308) — Trivikrama avatar taking cosmic strides.
4. [`assets/gods/narasimha/narasimha_emerging_from_pillar_prahlada.png`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/assets/gods/narasimha/narasimha_emerging_from_pillar_prahlada.png) (1,927,268 B, 768×1376) — Lord Narasimha bursting from palace pillar.

*(Note: Vertical Hanuman Sanjeevani asset was pre-existing and is already tracked in git).*

#### Landscape 16:9 Images for Long Videos (Untracked) (5 Files)
5. [`assets/gods_landscape_long_video/hanuman/hanuman_carrying_dronagiri_sanjeevani_landscape.png`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/assets/gods_landscape_long_video/hanuman/hanuman_carrying_dronagiri_sanjeevani_landscape.png) (1,839,293 B, 1376×768) — Lord Hanuman flying with Dronagiri Mountain.
6. [`assets/gods_landscape_long_video/krishna/krishna_lifting_govardhan_hill_with_finger_landscape.png`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/assets/gods_landscape_long_video/krishna/krishna_lifting_govardhan_hill_with_finger_landscape.png) (1,965,663 B, 1376×768) — Lord Krishna holding Govardhan hill in 16:9.
7. [`assets/gods_landscape_long_video/lord_vishnu/kurma_avatar_mandara_mountain_samudra_manthan_landscape.png`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/assets/gods_landscape_long_video/lord_vishnu/kurma_avatar_mandara_mountain_samudra_manthan_landscape.png) (2,080,280 B, 1376×768) — Kurma avatar supporting Mandara in 16:9.
8. [`assets/gods_landscape_long_video/lord_vishnu/vamana_trivikrama_three_strides_bali_landscape.png`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/assets/gods_landscape_long_video/lord_vishnu/vamana_trivikrama_three_strides_bali_landscape.png) (2,192,445 B, 1376×768) — Trivikrama taking cosmic strides in 16:9.
9. [`assets/gods_landscape_long_video/narasimha/narasimha_emerging_from_pillar_prahlada_landscape.png`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/assets/gods_landscape_long_video/narasimha/narasimha_emerging_from_pillar_prahlada_landscape.png) (2,001,642 B, 1376×768) — Lord Narasimha emerging from pillar in 16:9.

#### Devotional Music Asset (Untracked) (1 File)
10. [`assets/music/devotional/youtube_audio_library_aalaap_jhinjhoti.mp3`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/assets/music/devotional/youtube_audio_library_aalaap_jhinjhoti.mp3) (7,112,657 B) — Canonical devotional BGM track (un-ignored by `.gitignore` via `!assets/music/devotional/*.mp3`).

---

### Category 4: Asset Manifests (2 Files)

#### Modified Tracked Manifests (2 Files)
1. [`data/assets/asset_manifest.json`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/data/assets/asset_manifest.json) — Enriched with avatar tags, narrative events, and `verified_visual` status for 392 vertical images.
2. [`data/assets/landscape_asset_manifest.json`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/data/assets/landscape_asset_manifest.json) (7,806 B) — Full index for 5 landscape long-video narrative assets.

---

### Category 5: Documentation & Audit Reports (13 Files)

#### New Documentation Reports (Untracked) (13 Files)
1. [`DEPLOYMENT_READINESS_AUDIT.md`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/DEPLOYMENT_READINESS_AUDIT.md) (11,900 B) — Independent deployment readiness audit report.
2. [`FINAL_INTEGRATION_VERIFICATION.md`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/FINAL_INTEGRATION_VERIFICATION.md) (16,115 B) — Defect remediation verification report.
3. [`FINAL_VISUAL_AND_PUBLISHER_AUDIT.md`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/FINAL_VISUAL_AND_PUBLISHER_AUDIT.md) (11,432 B) — Visual mismatch and publisher safety report.
4. [`INDEPENDENT_PRODUCTION_READINESS_AUDIT.md`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/INDEPENDENT_PRODUCTION_READINESS_AUDIT.md) (16,473 B) — First adversarial audit discovering DEF-01 to DEF-04.
5. [`PRODUCTION_RELEASE_INVENTORY.md`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/PRODUCTION_RELEASE_INVENTORY.md) — This document.
6. [`RELEASE_CANDIDATE_REVIEW.md`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/RELEASE_CANDIDATE_REVIEW.md) (13,222 B) — Release candidate video inspection report.
7. [`REMEDIATION_REPORT.md`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/REMEDIATION_REPORT.md) (10,609 B) — Defect remediation summary report.
8. [`SCRIPT_QA_GUIDE.md`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/SCRIPT_QA_GUIDE.md) (4,419 B) — Guide to the Pre-Voice Script QA validation gates.
9. [`SOURCE_VERIFICATION_GUIDE.md`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/SOURCE_VERIFICATION_GUIDE.md) (3,456 B) — Guide to scriptural source registry citations.
10. [`TELUGU_CONTENT_INTELLIGENCE.md`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/TELUGU_CONTENT_INTELLIGENCE.md) (6,792 B) — Architectural blueprint documentation.
11. [`UPGRADE_AUDIT_REPORT.md`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/UPGRADE_AUDIT_REPORT.md) (11,061 B) — Initial upgrade audit report.
12. [`UPGRADE_CHANGELOG.md`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/UPGRADE_CHANGELOG.md) (3,462 B) — Detailed changelog of all module enhancements.
13. [`VISUAL_ASSET_COMPLETION_REPORT.md`](file:///c:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/VISUAL_ASSET_COMPLETION_REPORT.md) (14,305 B) — Narrative asset completion and prompt audit.

---

### Category 6: Rendered MP4 Outputs (0 Files Tracked / Untracked in Git)

The following generated test outputs exist on disk but are **properly excluded** from git status by `.gitignore` rules (`output/` and `*.mp4`):
- `output/rc_renders/telugu_krishna_govardhan_short.mp4` (45,907,235 B)
- `output/rc_renders/telugu_kurma_avatar_landscape_long.mp4` (116,001,018 B)
- `data/videos/video_short_20261111_221518.mp4` (13,446,882 B)
- `data/videos/video_short_20261111_215903.mp4` (13,447,210 B)
- Extracted inspection frames (`output/rc_renders/*.png`)

---

### Category 7: Temporary Scripts and Scratch Files (30 Files)

All located in `scratch/` (transient utilities, CI log dumps, and experimental scripts):
1. `scratch/caption_hi.txt` (282 B)
2. `scratch/check_annotations.py` (557 B)
3. `scratch/check_github_runs.py` (687 B)
4. `scratch/check_run_details.py` (658 B)
5. `scratch/check_run_jobs.py` (740 B)
6. `scratch/compose_all_deity_devotional_music.py` (21,178 B)
7. `scratch/download_run_logs.py` (1,437 B)
8. `scratch/fetch_job_logs.py` (1,135 B)
9. `scratch/monitor_run.py` (1,923 B)
10. `scratch/monitor_run_171.py` (3,007 B)
11. `scratch/probe_gemini_models.py` (2,488 B)
12. `scratch/probe_gemini_models_v2.py` (1,044 B)
13. `scratch/probe_music.py` (808 B)
14. `scratch/render_rc_videos.py` (11,819 B)
15. `scratch/render_real_old_video.py` (4,726 B)
16. `scratch/render_retention_videos.py` (6,443 B)
17. `scratch/run_170_logs.txt` (249,249 B)
18. `scratch/run_all_suites_report.py` (3,011 B)
19. `scratch/run_latest_logs.txt` (273,747 B)
20. `scratch/smoke_test_pocket_tts.py` (6,120 B)
21. `scratch/test_synthesized_offline_fallback.py` (9,627 B)
22. `scratch/trigger_workflow_dispatch.py` (2,004 B)
23. `scratch/update_blueprints_clean_narration.py` (122,831 B)
24. `scratch/update_manifest.py` (4,537 B)
25. `scratch/update_manifest_pixabay.py` (10,227 B)
26. `scratch/update_manifest_pixabay_v2.py` (1,777 B)
27. `scratch/verify_5_visual_scenarios.py` (3,022 B)
28. `scratch/verify_final_music.py` (4,006 B)
29. `scratch/verify_rc_assets.py` (3,228 B)
30. `scratch/verify_review.py` (2,080 B)

---

## 4. Files That Must Never Be Committed

The following files and patterns are strictly forbidden from git commits:

| Category | File Patterns | Current Protection Status |
| :--- | :--- | :--- |
| **Secrets & OAuth Tokens** | `token.json`, `token_backup.json`, `credentials.json`, `client_secret.json`, `.env`, `.env.*` | **Protected** (Explicitly listed in `.gitignore` lines 1–9) |
| **Python Bytecode & Caches** | `__pycache__/`, `*.pyc`, `.pytest_cache/` | **Protected** (Explicitly listed in `.gitignore` lines 11–14) |
| **Rendered MP4 / Video Files** | `*.mp4`, `output/`, `data/videos/*`, `temp/`, `tmp/` | **Protected** (Explicitly listed in `.gitignore` lines 16–29, 38) |
| **Pipeline Intermediate Caches** | `data/research/*`, `data/decision/*`, `data/content_briefs/*`, `data/scripts/*`, `data/audio/*`, `data/visuals/*`, `data/thumbnails/*`, `data/qa/*` | **Protected** (Explicitly listed in `.gitignore` lines 32–42) |
| **Scratch Scripts & Logs** | `scratch/`, `*.log`, `scratch/*.txt` | **Unprotected in `.gitignore`** (Currently visible as untracked files; must be excluded during staging) |

---

## 5. Production Asset Reference Verification

Both manifests were programmatically verified against the filesystem:
- **`data/assets/asset_manifest.json`**:
  - Total vertical image entries: **392**
  - Missing image files on disk: **0**
  - Newly acquired narrative assets:
    - `assets/gods/krishna/krishna_lifting_govardhan_hill_with_finger.png` (`verified_visual`)
    - `assets/gods/lord_vishnu/kurma_avatar_mandara_mountain_samudra_manthan.png` (`verified_visual`)
    - `assets/gods/lord_vishnu/vamana_trivikrama_three_strides_bali.png` (`verified_visual`)
    - `assets/gods/narasimha/narasimha_emerging_from_pillar_prahlada.png` (`verified_visual`)
    - `assets/gods/hanuman/hanuman_carrying_dronagiri_mountain_sanjeevani_with_gada.png` (`verified_visual`)
- **`data/assets/landscape_asset_manifest.json`**:
  - Total landscape image entries: **5**
  - Missing image files on disk: **0**
  - Newly acquired landscape assets:
    - `assets/gods_landscape_long_video/hanuman/hanuman_carrying_dronagiri_sanjeevani_landscape.png` (`verified_visual`)
    - `assets/gods_landscape_long_video/krishna/krishna_lifting_govardhan_hill_with_finger_landscape.png` (`verified_visual`)
    - `assets/gods_landscape_long_video/lord_vishnu/kurma_avatar_mandara_mountain_samudra_manthan_landscape.png` (`verified_visual`)
    - `assets/gods_landscape_long_video/lord_vishnu/vamana_trivikrama_three_strides_bali_landscape.png` (`verified_visual`)
    - `assets/gods_landscape_long_video/narasimha/narasimha_emerging_from_pillar_prahlada_landscape.png` (`verified_visual`)
- **Devotional Audio Asset**:
  - `assets/music/devotional/youtube_audio_library_aalaap_jhinjhoti.mp3` verified present and un-ignored.

---

## 6. `.gitignore` Audit

Inspection of `.gitignore` confirmed:
1. **Accidental leaks prevented:** Tokens, keys, credentials, and MP4 media files are comprehensively ignored.
2. **Missing Exclusions Identified (Recommended additions for future commit):**
   - `scratch/` — To prevent 30 temporary developer scripts and logs from cluttering `git status`.
   - `*.log` — To prevent stray log files from being staged.
   - `.vscode/`, `.idea/` — IDE project settings.
   - Root temporary audit markdown files (or alternatively, formalize them under a `docs/audits/` directory).

---

## 7. Audit of Accidental or Unrelated Changes

All 13 modified tracked files were examined via `git diff`:
- No breaking changes or unauthorized refactoring were introduced.
- No modifications were made to scheduling intervals in `.github/workflows/`.
- No Hindi/English production paths were enabled.
- All modifications strictly support:
  1. Telugu-only scriptural source integration and blueprints.
  2. Pre-Voice Script QA validation and factuality gates.
  3. Strict avatar matching and safe fail-closed behavior for missing narrative assets.
  4. Pocket TTS fallback hierarchy.
  5. YouTube publisher dry-run safety invariant.

---

## 8. Controlled Staging Plan

### Recommended Files to Stage (33 Files)

When the user authorizes staging, the following 33 files should be staged together:

#### A. Core Modified Modules (11 Files)
- `src/assets/scanner.py`
- `src/assets/selector.py`
- `src/content/brief_generator.py`
- `src/content/gemini_provider.py`
- `src/decision/report.py`
- `src/decision/strategy.py`
- `src/pipeline/orchestrator.py`
- `src/qa/gate.py`
- `src/research/collector.py`
- `src/script/generator.py`
- `src/voice/generator.py`

#### B. New Production Modules (7 Files)
- `src/content/telugu_blueprints.py`
- `src/decision/feedback.py`
- `src/research/scriptural_source_registry.py`
- `src/script/script_factuality_validator.py`
- `src/script/script_qa_gate.py`
- `src/script/script_quality_evaluator.py`
- `src/script/script_retention_optimizer.py`

#### C. New Automated Test Suites (3 Files)
- `tests/test_content_intelligence.py`
- `tests/test_publisher_dry_run_safety.py`
- `tests/test_remediation_defects.py`

#### D. Verified Asset Manifests (2 Files)
- `data/assets/asset_manifest.json`
- `data/assets/landscape_asset_manifest.json`

#### E. Verified Narrative Assets (10 Files)
- `assets/gods/krishna/krishna_lifting_govardhan_hill_with_finger.png`
- `assets/gods/lord_vishnu/kurma_avatar_mandara_mountain_samudra_manthan.png`
- `assets/gods/lord_vishnu/vamana_trivikrama_three_strides_bali.png`
- `assets/gods/narasimha/narasimha_emerging_from_pillar_prahlada.png`
- `assets/gods_landscape_long_video/hanuman/hanuman_carrying_dronagiri_sanjeevani_landscape.png`
- `assets/gods_landscape_long_video/krishna/krishna_lifting_govardhan_hill_with_finger_landscape.png`
- `assets/gods_landscape_long_video/lord_vishnu/kurma_avatar_mandara_mountain_samudra_manthan_landscape.png`
- `assets/gods_landscape_long_video/lord_vishnu/vamana_trivikrama_three_strides_bali_landscape.png`
- `assets/gods_landscape_long_video/narasimha/narasimha_emerging_from_pillar_prahlada_landscape.png`
- `assets/music/devotional/youtube_audio_library_aalaap_jhinjhoti.mp3`

---

### Files to Exclude from Staging (43 Files)

1. **Scratch directory (30 files):** All files in `scratch/`.
2. **Audit documentation reports (13 files):**
   - `DEPLOYMENT_READINESS_AUDIT.md`, `FINAL_INTEGRATION_VERIFICATION.md`, `FINAL_VISUAL_AND_PUBLISHER_AUDIT.md`, `INDEPENDENT_PRODUCTION_READINESS_AUDIT.md`, `PRODUCTION_RELEASE_INVENTORY.md`, `RELEASE_CANDIDATE_REVIEW.md`, `REMEDIATION_REPORT.md`, `SCRIPT_QA_GUIDE.md`, `SOURCE_VERIFICATION_GUIDE.md`, `TELUGU_CONTENT_INTELLIGENCE.md`, `UPGRADE_AUDIT_REPORT.md`, `UPGRADE_CHANGELOG.md`, `VISUAL_ASSET_COMPLETION_REPORT.md`.
   *(These can either remain untracked for local reference or be committed in a separate documentation-only commit if desired).*

---

## 9. Blockers for Live YouTube Uploads

1. **OAuth 2.0 Credentials:**
   Live public publishing requires authenticating `@Divine_Dharshan_om` and populating `TOKEN_JSON` and `CREDENTIALS_JSON` in GitHub Secrets.
2. **Long Video Landscape Coverage:**
   Currently verified for Vishnu, Krishna, Narasimha, and Hanuman. Deities without landscape assets (Shiva, Ganesha) are safely blocked by fail-closed visual resolution.

---

## 10. Proposed Commit Message

```text
feat(telugu-engine): complete Telugu Content Intelligence upgrade and narrative assets

- Upgrade to strict te-IN devotional content intelligence architecture
- Implement canonical Telugu story blueprints and scriptural source registry
- Connect pre-voice script QA gate (DEF-01) and enforce before TTS synthesis
- Integrate historical publishing feedback loop for topic selection (DEF-03)
- Connect research pipeline to scriptural source registry (DEF-02)
- Enforce strict avatar matching and verified narrative visual assets (DEF-04)
- Add 9 verified narrative assets (Kurma, Vamana, Krishna Govardhan, Narasimha Pillar, Hanuman)
- Add landscape long-video asset manifest and fail-closed resolution
- Add automated test suites for content intelligence, remediation, and publisher dry-run safety
- Verified end-to-end with zero YouTube upload dry-run safety invariant
```
