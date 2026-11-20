# Human Visual Review Instructions: Batch Deity Asset Curation

**Repository:** `Indian_Gods_YT_AUto`
**Dashboard Path:** [`data/review/asset_review_dashboard.html`](file:///C:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/data/review/asset_review_dashboard.html)
**Security Boundary:** Review-Only Staging. Does **NOT** alter the production approval registry.

---

## 1. Quick Start: Launching the Review Dashboard

The dashboard is completely self-contained and offline-compatible (zero CDN or internet access required).

### Option A: Open directly in Browser
Open the HTML file directly:
```text
file:///C:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/data/review/asset_review_dashboard.html
```

### Option B: Local HTTP Server (Optional)
```powershell
python -m http.server 8080 --directory C:\Users\chenn\Downloads\Gods_Channel\Indian_Gods_YT_AUto
# Then navigate to: http://localhost:8080/data/review/asset_review_dashboard.html
```

---

## 2. Priority Deities: Unblocking Missing Weekday Automation

The current production weekday schedule requires 7 weekday deity groups. Four deities currently have **ZERO** approved assets in the registry, but have existing candidate artwork ready for visual review:

### Priority 1: Goddess Parvati (`parvathi`)
- **Weekday:** Monday (Somvar)
- **Candidate Pool:** 7 images in `assets/gods/parvathi/`
- **Iconography Check:** Traditional red or green saree, Trishula, lotus, trident, gentle divine facial expression, seated on lion or beside Shiva. Reject generic apsaras or modern non-devotional art.

### Priority 2: Lord Kartikeya / Skanda (`subramanya`)
- **Weekday:** Tuesday (Mangalvar)
- **Candidate Pool:** 39 images in `assets/gods/subramanya/`
- **Iconography Check:** Vel (divine spear), peacock mount (Mayura), youthful radiant commander of the gods, single or six faces (Shanmukha).

### Priority 3: Goddess Mahalakshmi (`lakshmi_devi`)
- **Weekday:** Friday (Shukravar)
- **Candidate Pool:** 12 images in `assets/gods/lakshmi_devi/`
- **Iconography Check:** Seated on red/pink lotus, golden Kalasha, coins showering from hand, four arms holding lotuses, auspicious red/gold attire.

### Priority 4: Goddess Kali (`kali`)
- **Weekday:** Tuesday (Mangalvar)
- **Candidate Pool:** 2 images located in `assets/gods/subramanya/` (e.g. `Kali and murugan.jpg`)
- **Iconography Check:** Dark blue/black complexion, Garland of skulls, Khadga (sword), fierce protective expression, tongue outstretched.

---

## 3. Visual Review Guidelines & Quality Standards

When evaluating any candidate asset, check:

1. **Deity Identity Consistency:**
   - Does the artwork depict the exact intended deity?
   - If multiple deities are present (e.g. Shiva and Parvati together), note in the text box whether it is suitable for joint depiction or should be marked `UNCLEAR_IDENTITY`.
2. **Avatar Isolation:**
   - For Vishnu assets: Is it specifically Kurma, Vamana, Narasimha, Krishna, Rama, or generic Vishnu? Never propose an avatar-specific asset as generic Vishnu.
3. **No Watermarks or Stock Text:**
   - Reject images with stock photo watermarks, commercial logos, or distracting digital artifacts.
4. **Resolution & Aspect Ratio:**
   - Verify resolution is suitable (portrait >= 720x1280, landscape >= 1280x720).
   - Reject heavily compressed, blurry, or stretched assets.

---

## 4. Review Controls Reference

On each asset card in the dashboard:

| Control | Action / Status Recorded | Usage Guidelines |
| :--- | :--- | :--- |
| **✔️ Looks Correct** | `PROPOSED_FOR_APPROVAL` | High-quality, authentic depiction matching the candidate deity. Recommended for promotion into the trusted catalog. |
| **❌ Wrong Deity** | `WRONG_DEITY` | Depicts a completely different deity (e.g., Hanuman found in a Shiva directory). Note the actual deity in the notes input. |
| **❓ Unclear** | `UNCLEAR_IDENTITY` | Ambiguous iconography, modern abstract styling, or indeterminate deity. |
| **⚠️ Broken** | `BROKEN_ASSET` | Corrupt image, zero-byte file, unplayable video, or severe compression distortion. |
| **🔄 Duplicate** | `DUPLICATE` | Visually or byte-for-byte identical copy of another existing asset. |

---

## 5. Decision Persistence & Export

1. **Auto-Save:** Every decision click and note input is automatically saved in your browser's `localStorage` under `DIVINE_HUMAN_REVIEW_DECISIONS`. Closing or refreshing the page will not lose your progress.
2. **Export Decisions:** Click **"💾 Export Decisions JSON"** in the top header.
   - Downloads [`data/review/human_review_decisions.json`](file:///C:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/data/review/human_review_decisions.json).
3. **Transferability:** You can resume review on another machine by clicking **"📂 Import Decisions"** and selecting your previously exported JSON file.

---

## 6. Strict Security Invariant: How Approvals Are Actually Granted

> [!IMPORTANT]
> The review dashboard is strictly a **decision staging tool**.
> Marking an asset as *"Looks Correct"* in the dashboard **DOES NOT** grant production approval and does **NOT** modify `src/assets/approval_registry.py`.

### Promotion Workflow into Production:
1. Reviewer completes visual curation in the dashboard and clicks **"Export Decisions JSON"**.
2. A developer or release auditor reviews the exported `human_review_decisions.json`.
3. For every confirmed candidate, an explicit `TrustedAssetApprovalRecord` entry is manually added to `_BUILTIN_TRUSTED_APPROVAL_RECORDS` in [`src/assets/approval_registry.py`](file:///C:/Users/chenn/Downloads/Gods_Channel/Indian_Gods_YT_AUto/src/assets/approval_registry.py).
4. Run `python -m unittest tests/test_asset_approval_trust.py` and full suite to verify.
