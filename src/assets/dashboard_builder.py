# src/assets/dashboard_builder.py
# Offline Local Visual Asset Review Dashboard Generator

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


def build_dashboard_html(
    inventory_data: list[dict[str, Any]],
    matrix_data: dict[str, Any],
    duplicates_data: dict[str, Any],
    frame_map: dict[str, str],
) -> str:
    """
    Builds the standalone, offline-capable HTML review dashboard with all
    430 inventoried assets and metadata embedded directly.
    """
    embedded_inventory_json = json.dumps(inventory_data, ensure_ascii=False)
    embedded_matrix_json = json.dumps(matrix_data, ensure_ascii=False)
    embedded_duplicates_json = json.dumps(duplicates_data, ensure_ascii=False)
    embedded_frame_map_json = json.dumps(frame_map, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Batch Visual Asset Review Dashboard — Divine Dharshanam</title>
  <style>
    :root {{
      --bg-dark: #0b0d14;
      --card-bg: #141724;
      --card-border: #23273c;
      --gold: #f5c518;
      --gold-light: #ffd700;
      --red: #e74c3c;
      --green: #2ecc71;
      --amber: #f39c12;
      --purple: #9b59b6;
      --text: #e1e3ea;
      --text-muted: #8b90a4;
      --font-stack: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    }}

    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg-dark);
      color: var(--text);
      font-family: var(--font-stack);
      line-height: 1.5;
      padding-bottom: 80px;
    }}

    header {{
      background: linear-gradient(180deg, #181b2e 0%, #121422 100%);
      border-bottom: 2px solid var(--gold);
      padding: 20px 30px;
      position: sticky;
      top: 0;
      z-index: 100;
      box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    }}

    .header-top {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 15px;
    }}

    .title-area h1 {{
      font-size: 1.6rem;
      color: var(--gold);
      letter-spacing: 0.5px;
    }}
    .title-area p {{
      font-size: 0.85rem;
      color: var(--text-muted);
    }}

    .header-actions {{
      display: flex;
      gap: 10px;
      align-items: center;
    }}

    button {{
      background: #23273c;
      color: var(--text);
      border: 1px solid #363b58;
      padding: 8px 14px;
      border-radius: 6px;
      font-size: 0.85rem;
      font-weight: 600;
      cursor: pointer;
      transition: all 0.2s ease;
    }}
    button:hover {{ background: #2f3450; border-color: var(--gold); }}
    button.btn-primary {{
      background: var(--gold);
      color: #0b0d14;
      border: none;
    }}
    button.btn-primary:hover {{ background: var(--gold-light); }}
    button.btn-danger {{
      background: #78261e;
      color: #fff;
      border-color: var(--red);
    }}
    button.btn-danger:hover {{ background: var(--red); }}

    .security-banner {{
      background: #2a1515;
      border-left: 4px solid var(--red);
      padding: 8px 15px;
      margin-top: 15px;
      border-radius: 4px;
      font-size: 0.8rem;
      color: #ff9999;
      display: flex;
      align-items: center;
      gap: 8px;
    }}

    .stats-bar {{
      display: flex;
      gap: 20px;
      flex-wrap: wrap;
      margin-top: 15px;
      font-size: 0.85rem;
    }}
    .stat-pill {{
      background: rgba(255,255,255,0.05);
      padding: 4px 10px;
      border-radius: 12px;
      border: 1px solid rgba(255,255,255,0.1);
    }}
    .stat-pill span {{ font-weight: bold; color: var(--gold); }}

    /* Priority Filter Pills */
    .priority-section {{
      background: #141726;
      border-bottom: 1px solid #23273c;
      padding: 12px 30px;
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
    }}
    .priority-label {{
      font-size: 0.8rem;
      font-weight: bold;
      color: var(--gold);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .p-pill {{
      padding: 5px 12px;
      border-radius: 16px;
      font-size: 0.8rem;
      border: 1px solid #363b58;
      background: #1a1e32;
      color: #cbd0e2;
      cursor: pointer;
      transition: all 0.2s;
    }}
    .p-pill:hover {{ border-color: var(--gold); color: #fff; }}
    .p-pill.active {{
      background: #e74c3c;
      border-color: #e74c3c;
      color: #fff;
      font-weight: bold;
    }}

    /* Filters Section */
    .filters-section {{
      background: #10121d;
      border-bottom: 1px solid #1c2033;
      padding: 15px 30px;
      display: flex;
      gap: 15px;
      flex-wrap: wrap;
      align-items: center;
    }}
    .filter-group {{
      display: flex;
      flex-direction: column;
      gap: 4px;
    }}
    .filter-group label {{
      font-size: 0.72rem;
      text-transform: uppercase;
      color: var(--text-muted);
      letter-spacing: 0.5px;
    }}
    select, input[type="text"] {{
      background: #1a1e30;
      color: var(--text);
      border: 1px solid #2d334d;
      padding: 7px 10px;
      border-radius: 5px;
      font-size: 0.85rem;
      outline: none;
    }}
    select:focus, input[type="text"]:focus {{
      border-color: var(--gold);
    }}
    input[type="text"] {{ width: 220px; }}

    /* Main Container & Grid */
    main {{
      padding: 25px 30px;
      max-width: 1800px;
      margin: 0 auto;
    }}

    .results-count {{
      font-size: 0.9rem;
      color: var(--text-muted);
      margin-bottom: 15px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}

    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 20px;
    }}

    /* Asset Card */
    .card {{
      background: var(--card-bg);
      border: 1px solid var(--card-border);
      border-radius: 8px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      transition: all 0.2s ease;
      position: relative;
    }}
    .card:hover {{
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba(0,0,0,0.6);
      border-color: #3b4266;
    }}

    /* Visual status states */
    .card.decision-APPROVED {{
      border: 2px solid #2ecc71 !important;
      background: linear-gradient(180deg, #14301e 0%, #141724 50%);
    }}
    .card.decision-PROPOSED_FOR_APPROVAL {{
      border: 2px solid var(--amber) !important;
      background: linear-gradient(180deg, #242014 0%, #141724 50%);
    }}
    .card.decision-WRONG_DEITY {{
      border: 2px solid var(--red) !important;
      background: linear-gradient(180deg, #241414 0%, #141724 50%);
    }}
    .card.decision-UNCLEAR_IDENTITY {{
      border: 2px solid var(--amber) !important;
      background: linear-gradient(180deg, #242014 0%, #141724 50%);
    }}
    .card.decision-BROKEN_ASSET, .card.decision-DUPLICATE {{
      border: 2px solid var(--purple) !important;
      background: linear-gradient(180deg, #201424 0%, #141724 50%);
    }}

    .card-thumb-container {{
      width: 100%;
      height: 240px;
      background: #090a10;
      position: relative;
      display: flex;
      justify-content: center;
      align-items: center;
      overflow: hidden;
      border-bottom: 1px solid #1c2033;
    }}
    .card-thumb-container img {{
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
      cursor: pointer;
      transition: transform 0.2s;
    }}
    .card-thumb-container img:hover {{
      transform: scale(1.03);
    }}

    .card-badge {{
      position: absolute;
      top: 8px;
      padding: 3px 8px;
      border-radius: 4px;
      font-size: 0.7rem;
      font-weight: bold;
      letter-spacing: 0.5px;
      z-index: 2;
    }}
    .badge-unapproved {{
      left: 8px;
      background: #c0392b;
      color: #fff;
    }}
    .badge-approved {{
      left: 8px;
      background: #27ae60;
      color: #fff;
    }}
    .badge-type {{
      right: 8px;
      background: rgba(20, 25, 45, 0.85);
      border: 1px solid #363b58;
      color: #a0c0ff;
    }}
    .badge-broken {{
      top: 36px;
      left: 8px;
      background: #e74c3c;
      color: #fff;
    }}
    .badge-dup {{
      top: 36px;
      right: 8px;
      background: #8e44ad;
      color: #fff;
    }}

    .card-body {{
      padding: 12px 14px;
      display: flex;
      flex-direction: column;
      flex-grow: 1;
      gap: 8px;
    }}

    .card-deity {{
      font-size: 0.95rem;
      font-weight: bold;
      color: var(--gold);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .card-path {{
      font-family: monospace;
      font-size: 0.72rem;
      color: #aab0c8;
      background: #0f111c;
      padding: 4px 6px;
      border-radius: 4px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      cursor: pointer;
    }}
    .card-path:hover {{
      color: var(--gold);
      background: #171a2a;
    }}

    .card-meta-row {{
      display: flex;
      justify-content: space-between;
      font-size: 0.75rem;
      color: var(--text-muted);
    }}

    /* Review Controls inside Card */
    .review-controls {{
      margin-top: auto;
      padding-top: 10px;
      border-top: 1px solid #1c2033;
    }}
    .review-btn-grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 6px;
    }}
    .btn-action {{
      padding: 6px 4px;
      font-size: 0.75rem;
      border-radius: 4px;
      border: 1px solid #2d334d;
      background: #1a1e30;
      color: var(--text);
      text-align: center;
      cursor: pointer;
    }}
    .btn-action.btn-confirm {{ grid-column: span 2; font-weight: bold; }}
    .btn-action.btn-confirm.selected {{ background: #27ae60; color: #fff; border-color: #2ecc71; }}
    .btn-action.btn-wrong.selected {{ background: #c0392b; color: #fff; border-color: #e74c3c; }}
    .btn-action.btn-unclear.selected {{ background: #d35400; color: #fff; border-color: #f39c12; }}
    .btn-action.btn-broken.selected {{ background: #8e44ad; color: #fff; border-color: #9b59b6; }}
    .btn-action.btn-dup.selected {{ background: #2980b9; color: #fff; border-color: #3498db; }}

    .review-notes {{
      margin-top: 6px;
      width: 100%;
      background: #0d0f18;
      border: 1px solid #23273c;
      color: #cbd0e2;
      padding: 4px 6px;
      font-size: 0.75rem;
      border-radius: 4px;
    }}

    /* Lightbox Modal */
    .modal {{
      display: none;
      position: fixed;
      top: 0; left: 0; width: 100%; height: 100%;
      background: rgba(0,0,0,0.85);
      z-index: 200;
      justify-content: center;
      align-items: center;
      padding: 30px;
    }}
    .modal.active {{ display: flex; }}
    .modal-content {{
      max-width: 90vw;
      max-height: 90vh;
      background: #121420;
      border: 1px solid var(--gold);
      border-radius: 8px;
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }}
    .modal-img {{
      max-height: 70vh;
      object-fit: contain;
      background: #000;
    }}
    .modal-info {{
      padding: 15px 20px;
      font-size: 0.85rem;
      background: #151826;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }}
    .modal-close {{
      align-self: flex-end;
      padding: 6px 12px;
      margin: 10px;
      background: #c0392b;
      color: #fff;
    }}

    /* Toast Notification */
    .toast {{
      position: fixed;
      bottom: 25px;
      right: 25px;
      background: #27ae60;
      color: #fff;
      padding: 10px 18px;
      border-radius: 6px;
      font-size: 0.85rem;
      font-weight: bold;
      box-shadow: 0 4px 15px rgba(0,0,0,0.5);
      opacity: 0;
      transition: opacity 0.3s;
      z-index: 300;
      pointer-events: none;
    }}
    .toast.show {{ opacity: 1; }}
  </style>
</head>
<body>

  <header>
    <div class="header-top">
      <div class="title-area">
        <h1>DIVINE DHARSHANAM — ASSET REVIEW DASHBOARD</h1>
        <p>Batch Visual Asset Review & Candidate Staging Gateway • 430 Repository Assets</p>
      </div>
      <div class="header-actions">
        <button class="btn-primary" onclick="exportDecisionsJSON()">💾 Export Decisions JSON</button>
        <button onclick="document.getElementById('importFileInput').click()">📂 Import Decisions</button>
        <input type="file" id="importFileInput" style="display:none;" onchange="importDecisionsFile(event)">
        <button class="btn-danger" onclick="resetAllDecisions()">🔄 Clear All Decisions</button>
      </div>
    </div>

    <div class="security-banner">
      <strong>⚠️ SECURITY MANDATE:</strong>
      Decisions recorded in this dashboard do NOT alter the production approval registry (<code>src/assets/approval_registry.py</code>). They are staged strictly into <code>data/review/human_review_decisions.json</code> for audited code review.
    </div>

    <div class="stats-bar">
      <div class="stat-pill">Total Assets: <span id="statTotal">430</span></div>
      <div class="stat-pill">Approved Baseline: <span id="statApproved">14</span></div>
      <div class="stat-pill">Unapproved Candidates: <span id="statUnapproved">416</span></div>
      <div class="stat-pill">Duplicate Assets: <span id="statDuplicates">16</span></div>
      <div class="stat-pill">Broken Files: <span id="statBroken">11</span></div>
      <div class="stat-pill">Reviewed Decisions: <span id="statReviewed">0</span> / 430</div>
    </div>
  </header>

  <!-- Priority Quick-Filters -->
  <div class="priority-section">
    <div class="priority-label">🎯 High Priority Missing Weekday Deities:</div>
    <div class="p-pill" onclick="setPriorityFilter('ALL_PRIORITY')">🔥 All 4 Priority Deities (60 candidates)</div>
    <div class="p-pill" onclick="setPriorityFilter('parvathi')">Monday: Goddess Parvati (7)</div>
    <div class="p-pill" onclick="setPriorityFilter('subramanya')">Tuesday: Lord Kartikeya (39)</div>
    <div class="p-pill" onclick="setPriorityFilter('lakshmi_devi')">Friday: Mahalakshmi (12)</div>
    <div class="p-pill" onclick="setPriorityFilter('kali')">Tuesday: Goddess Kali (2)</div>
    <div class="p-pill" onclick="setPriorityFilter('ALL')">Clear Priority Filter</div>
  </div>

  <!-- Detailed Filters -->
  <div class="filters-section">
    <div class="filter-group">
      <label>Candidate Deity</label>
      <select id="filterDeity" onchange="applyFilters()">
        <option value="ALL">All Deities (430)</option>
      </select>
    </div>

    <div class="filter-group">
      <label>Media Type</label>
      <select id="filterType" onchange="applyFilters()">
        <option value="ALL">All Types</option>
        <option value="image">Images Only</option>
        <option value="video">Videos Only</option>
      </select>
    </div>

    <div class="filter-group">
      <label>Aspect Ratio</label>
      <select id="filterAspect" onchange="applyFilters()">
        <option value="ALL">All Orientations</option>
        <option value="9:16">9:16 Portrait</option>
        <option value="16:9">16:9 Landscape</option>
        <option value="1:1">1:1 Square</option>
        <option value="3:4">3:4 Portrait</option>
      </select>
    </div>

    <div class="filter-group">
      <label>Approval Status</label>
      <select id="filterApproval" onchange="applyFilters()">
        <option value="ALL">All Statuses</option>
        <option value="UNAPPROVED" selected>Unapproved Only (416)</option>
        <option value="APPROVED">Approved Only (14)</option>
      </select>
    </div>

    <div class="filter-group">
      <label>Health / Anomalies</label>
      <select id="filterHealth" onchange="applyFilters()">
        <option value="ALL">All Assets</option>
        <option value="CLEAN">Clean (Non-broken, Non-duplicate)</option>
        <option value="DUPLICATE">Duplicates Only (16)</option>
        <option value="BROKEN">Broken Only (11)</option>
      </select>
    </div>

    <div class="filter-group">
      <label>Review State</label>
      <select id="filterReviewState" onchange="applyFilters()">
        <option value="ALL">All</option>
        <option value="UNREVIEWED">Unreviewed</option>
        <option value="REVIEWED">Reviewed</option>
      </select>
    </div>

    <div class="filter-group">
      <label>Live Search</label>
      <input type="text" id="searchInput" placeholder="Search filename, deity, path..." oninput="applyFilters()">
    </div>

    <div class="filter-group" style="align-self: flex-end;">
      <button onclick="resetFilters()">Reset Filters</button>
    </div>
  </div>

  <main>
    <div class="results-count">
      <div id="resultsCount">Showing 0 of 430 assets</div>
      <div>Click any image to zoom in full resolution.</div>
    </div>

    <div class="grid" id="assetGrid">
      <!-- Cards rendered dynamically -->
    </div>
  </main>

  <!-- Modal for Lightbox Image Inspection -->
  <div class="modal" id="imageModal" onclick="closeModal(event)">
    <div class="modal-content" onclick="event.stopPropagation()">
      <button class="modal-close" onclick="closeModal()">Close (ESC)</button>
      <img id="modalImg" class="modal-img" src="" alt="Full Resolution Inspection">
      <div class="modal-info">
        <div>
          <strong id="modalTitle">Asset Path</strong>
          <div id="modalMeta" style="color: var(--text-muted); font-size: 0.8rem; margin-top: 4px;">Metadata</div>
        </div>
        <button class="btn-primary" onclick="copyModalPath()">📋 Copy Path</button>
      </div>
    </div>
  </div>

  <div class="toast" id="toast">Notification</div>

  <script>
    // Embedded Datasets (Pre-rendered from Repository)
    const INVENTORY = {embedded_inventory_json};
    const MATRIX = {embedded_matrix_json};
    const DUPLICATES = {embedded_duplicates_json};
    const FRAME_MAP = {embedded_frame_map_json};

    // Human Decisions Store (Keyed by exact rel_path)
    let DECISIONS = {{}};

    // Load persisted decisions from localStorage if present
    try {{
      const saved = localStorage.getItem("DIVINE_HUMAN_REVIEW_DECISIONS");
      if (saved) {{
        DECISIONS = JSON.parse(saved);
      }}
    }} catch(e) {{
      console.warn("Could not load from localStorage:", e);
    }}

    function saveDecisions() {{
      try {{
        localStorage.setItem("DIVINE_HUMAN_REVIEW_DECISIONS", JSON.stringify(DECISIONS));
        updateStats();
      }} catch(e) {{
        console.warn("Could not save to localStorage:", e);
      }}
    }}

    // Populate Deity Filter Dropdown
    function initFilters() {{
      const deitySelect = document.getElementById("filterDeity");
      const counts = {{}};
      INVENTORY.forEach(item => {{
        const d = item.candidate_deity || "unclassified";
        counts[d] = (counts[d] || 0) + 1;
      }});

      Object.keys(counts).sort().forEach(d => {{
        const opt = document.createElement("option");
        opt.value = d;
        opt.textContent = `${{d}} (${{counts[d]}})`;
        deitySelect.appendChild(opt);
      }});

      updateStats();
      applyFilters();
    }}

    function updateStats() {{
      const reviewedCount = Object.keys(DECISIONS).length;
      document.getElementById("statReviewed").textContent = reviewedCount;
    }}

    function setPriorityFilter(priorityKey) {{
      const deitySelect = document.getElementById("filterDeity");
      const pills = document.querySelectorAll(".p-pill");
      pills.forEach(p => p.classList.remove("active"));

      if (priorityKey === "ALL") {{
        deitySelect.value = "ALL";
      }} else if (priorityKey === "ALL_PRIORITY") {{
        deitySelect.value = "ALL";
      }} else {{
        deitySelect.value = priorityKey;
      }}

      // Mark clicked pill active
      event.target.classList.add("active");
      applyFilters(priorityKey === "ALL_PRIORITY" ? ["parvathi", "subramanya", "lakshmi_devi", "kali"] : null);
    }}

    function resetFilters() {{
      document.getElementById("filterDeity").value = "ALL";
      document.getElementById("filterType").value = "ALL";
      document.getElementById("filterAspect").value = "ALL";
      document.getElementById("filterApproval").value = "ALL";
      document.getElementById("filterHealth").value = "ALL";
      document.getElementById("filterReviewState").value = "ALL";
      document.getElementById("searchInput").value = "";
      document.querySelectorAll(".p-pill").forEach(p => p.classList.remove("active"));
      applyFilters();
    }}

    function applyFilters(priorityDeities = null) {{
      const deity = document.getElementById("filterDeity").value;
      const type = document.getElementById("filterType").value;
      const aspect = document.getElementById("filterAspect").value;
      const approval = document.getElementById("filterApproval").value;
      const health = document.getElementById("filterHealth").value;
      const reviewState = document.getElementById("filterReviewState").value;
      const search = document.getElementById("searchInput").value.trim().toLowerCase();

      const filtered = INVENTORY.filter(item => {{
        // Priority deities filter
        if (priorityDeities && !priorityDeities.includes(item.candidate_deity.toLowerCase())) {{
          return false;
        }}
        if (!priorityDeities && deity !== "ALL" && item.candidate_deity.toLowerCase() !== deity.toLowerCase()) {{
          return false;
        }}
        if (type !== "ALL" && item.file_type !== type) {{
          return false;
        }}
        if (aspect !== "ALL" && item.aspect_ratio !== aspect) {{
          return false;
        }}
        if (approval !== "ALL" && item.approval_status !== approval) {{
          return false;
        }}
        if (health === "CLEAN" && (item.is_broken || item.is_duplicate)) {{
          return false;
        }}
        if (health === "DUPLICATE" && !item.is_duplicate) {{
          return false;
        }}
        if (health === "BROKEN" && !item.is_broken) {{
          return false;
        }}

        const isReviewed = Boolean(DECISIONS[item.rel_path]);
        if (reviewState === "REVIEWED" && !isReviewed) return false;
        if (reviewState === "UNREVIEWED" && isReviewed) return false;

        if (search) {{
          const blob = (item.rel_path + " " + item.candidate_deity + " " + (item.candidate_avatar || "") + " " + item.sha256).toLowerCase();
          if (!blob.includes(search)) return false;
        }}

        return true;
      }});

      renderGrid(filtered);
    }}

    function renderGrid(items) {{
      const grid = document.getElementById("assetGrid");
      grid.innerHTML = "";
      document.getElementById("resultsCount").textContent = `Showing ${{items.length}} of ${{INVENTORY.length}} assets`;

      items.forEach(item => {{
        const card = document.createElement("div");
        card.className = "card";
        const dec = DECISIONS[item.rel_path];
        if (dec) {{
          card.classList.add(`decision-${{dec.decision}}`);
        }}

        // Resolve thumbnail src (relative to data/review/)
        let imgSrc = "";
        let isVideoFrame = false;
        if (item.file_type === "video") {{
          const framePath = FRAME_MAP[item.rel_path];
          if (framePath) {{
            imgSrc = framePath;
            isVideoFrame = true;
          }}
        }} else {{
          imgSrc = `../../${{item.rel_path}}`;
        }}

        const shortName = item.rel_path.split("/").pop();
        const shortSha = item.sha256 ? item.sha256.substring(0, 10) : "N/A";
        const sizeKb = (item.file_size_bytes / 1024).toFixed(1);

        card.innerHTML = `
          <div class="card-thumb-container">
            ${{item.approval_status === "APPROVED"
              ? `<div class="card-badge badge-approved">APPROVED</div>`
              : `<div class="card-badge badge-unapproved">UNAPPROVED</div>`
            }}
            <div class="card-badge badge-type">${{item.file_type.toUpperCase()}} (${{item.aspect_ratio}})</div>
            ${{item.is_broken ? `<div class="card-badge badge-broken">⚠️ CORRUPT</div>` : ""}}
            ${{item.is_duplicate ? `<div class="card-badge badge-dup">DUPLICATE</div>` : ""}}

            ${{item.is_broken
              ? `<div style="color:#ff6b6b;font-size:0.8rem;text-align:center;padding:15px;">⚠️ File Corrupt<br><small>${{item.broken_reason || "Unreadable"}}</small></div>`
              : `<img src="${{imgSrc}}" loading="lazy" alt="${{shortName}}" onclick="openModal('${{imgSrc}}', '${{item.rel_path}}', '${{item.candidate_deity}}', '${{item.width}}x${{item.height}}', '${{sizeKb}} KB')">`
            }}
          </div>

          <div class="card-body">
            <div class="card-deity">
              <span>${{item.candidate_deity}}</span>
              <span style="font-size:0.75rem;color:var(--text-muted);">${{item.candidate_avatar || ""}}</span>
            </div>
            <div class="card-path" title="Click to copy path" onclick="copyPath('${{item.rel_path}}')">${{shortName}}</div>

            <div class="card-meta-row">
              <span>Dim: ${{item.width}}x${{item.height}}</span>
              <span>Size: ${{sizeKb}} KB</span>
            </div>
            <div class="card-meta-row">
              <span>SHA: <code title="${{item.sha256}}">${{shortSha}}</code></span>
              <span>${{item.duration_seconds > 0 ? item.duration_seconds + "s" : ""}}</span>
            </div>

            <!-- Review Actions -->
            <div class="review-controls">
              <div class="review-btn-grid">
                <button class="btn-action btn-approved ${{dec && dec.decision === 'APPROVED' ? 'selected' : ''}}"
                  style="border-color:#2ecc71; color:#2ecc71; font-weight:bold;"
                  onclick="recordApprovedDecision('${{item.rel_path}}', this)">
                  ✅ Human Approve (Verified)
                </button>
                <button class="btn-action btn-confirm ${{dec && dec.decision === 'PROPOSED_FOR_APPROVAL' ? 'selected' : ''}}"
                  onclick="recordDecision('${{item.rel_path}}', 'PROPOSED_FOR_APPROVAL', this)">
                  ⏳ Propose (Pending Review)
                </button>
                <button class="btn-action btn-wrong ${{dec && dec.decision === 'WRONG_DEITY' ? 'selected' : ''}}"
                  onclick="recordDecision('${{item.rel_path}}', 'WRONG_DEITY', this)">
                  ❌ Wrong Deity
                </button>
                <button class="btn-action btn-unclear ${{dec && dec.decision === 'UNCLEAR_IDENTITY' ? 'selected' : ''}}"
                  onclick="recordDecision('${{item.rel_path}}', 'UNCLEAR_IDENTITY', this)">
                  ❓ Unclear
                </button>
                <button class="btn-action btn-broken ${{dec && dec.decision === 'BROKEN_ASSET' ? 'selected' : ''}}"
                  onclick="recordDecision('${{item.rel_path}}', 'BROKEN_ASSET', this)">
                  ⚠️ Broken
                </button>
                <button class="btn-action btn-dup ${{dec && dec.decision === 'DUPLICATE' ? 'selected' : ''}}"
                  onclick="recordDecision('${{item.rel_path}}', 'DUPLICATE', this)">
                  🔄 Duplicate
                </button>
              </div>
              <input type="text" class="review-notes" placeholder="Optional notes (e.g. depiction details)..."
                value="${{dec ? (dec.notes || '') : ''}}"
                onchange="updateNotes('${{item.rel_path}}', this.value)">
            </div>
          </div>
        `;
        grid.appendChild(card);
      }});
    }}

    function recordApprovedDecision(relPath, btnElem) {{
      let reviewer = localStorage.getItem("DDD_REVIEWER_ID");
      if (!reviewer || !reviewer.trim()) {{
        reviewer = prompt("Enter human reviewer identity (Name or Reviewer ID) to record explicit approval:");
        if (!reviewer || !reviewer.trim()) {{
          alert("Explicit approval requires a valid human reviewer identity.");
          return;
        }}
        localStorage.setItem("DDD_REVIEWER_ID", reviewer.trim());
      }}

      const card = btnElem.closest(".card");
      const notesInput = card.querySelector(".review-notes");
      const item = INVENTORY.find(i => i.rel_path === relPath);

      // Deselect siblings in grid
      const grid = btnElem.closest(".review-btn-grid");
      grid.querySelectorAll(".btn-action").forEach(b => b.classList.remove("selected"));

      if (DECISIONS[relPath] && DECISIONS[relPath].decision === "APPROVED") {{
        delete DECISIONS[relPath];
        card.className = "card";
        showToast(`Removed approval for ${{relPath.split('/').pop()}}`);
      }} else {{
        btnElem.classList.add("selected");
        DECISIONS[relPath] = {{
          decision: "APPROVED",
          reviewer: reviewer.trim(),
          candidate_deity: item ? item.candidate_deity : "unknown",
          candidate_avatar: item ? item.candidate_avatar : null,
          aspect_ratio: item ? item.aspect_ratio : "unknown",
          notes: notesInput ? notesInput.value.trim() : "",
          timestamp: new Date().toISOString()
        }};
        card.className = "card decision-APPROVED";
        showToast(`Approved by ${{reviewer.trim()}}: ${{relPath.split('/').pop()}}`);
      }}

      saveDecisions();
    }}

    function recordDecision(relPath, decisionType, btnElem) {{
      const card = btnElem.closest(".card");
      const notesInput = card.querySelector(".review-notes");
      const item = INVENTORY.find(i => i.rel_path === relPath);

      // Deselect siblings in grid
      const grid = btnElem.closest(".review-btn-grid");
      grid.querySelectorAll(".btn-action").forEach(b => b.classList.remove("selected"));

      // If already selected, toggle off
      if (DECISIONS[relPath] && DECISIONS[relPath].decision === decisionType) {{
        delete DECISIONS[relPath];
        card.className = "card";
        showToast(`Removed decision for ${{relPath.split('/').pop()}}`);
      }} else {{
        btnElem.classList.add("selected");
        DECISIONS[relPath] = {{
          decision: decisionType,
          candidate_deity: item ? item.candidate_deity : "unknown",
          candidate_avatar: item ? item.candidate_avatar : null,
          aspect_ratio: item ? item.aspect_ratio : "unknown",
          notes: notesInput ? notesInput.value.trim() : "",
          timestamp: new Date().toISOString()
        }};
        card.className = `card decision-${{decisionType}}`;
        showToast(`Recorded: ${{decisionType}} for ${{relPath.split('/').pop()}}`);
      }}

      saveDecisions();
    }}

    function updateNotes(relPath, notesText) {{
      if (DECISIONS[relPath]) {{
        DECISIONS[relPath].notes = notesText.trim();
        saveDecisions();
        showToast("Updated notes");
      }}
    }}

    function resetAllDecisions() {{
      if (confirm("Are you sure you want to clear all recorded review decisions?")) {{
        DECISIONS = {{}};
        saveDecisions();
        applyFilters();
        showToast("All review decisions cleared");
      }}
    }}

    function exportDecisionsJSON() {{
      const count = Object.keys(DECISIONS).length;
      if (count === 0) {{
        alert("No review decisions have been recorded yet. Mark assets using the buttons on each card first.");
        return;
      }}

      const summary = {{
        approved: 0,
        proposed_for_approval: 0,
        wrong_deity: 0,
        unclear_identity: 0,
        broken: 0,
        duplicate: 0
      }};

      Object.values(DECISIONS).forEach(d => {{
        if (d.decision === "APPROVED") summary.approved++;
        else if (d.decision === "PROPOSED_FOR_APPROVAL") summary.proposed_for_approval++;
        else if (d.decision === "WRONG_DEITY") summary.wrong_deity++;
        else if (d.decision === "UNCLEAR_IDENTITY") summary.unclear_identity++;
        else if (d.decision === "BROKEN_ASSET") summary.broken++;
        else if (d.decision === "DUPLICATE") summary.duplicate++;
      }});

      const exportPayload = {{
        exported_at: new Date().toISOString(),
        total_decisions: count,
        summary: summary,
        warning: "REVIEW DECISIONS ONLY. Must be audited before adding to TrustedAssetApprovalRegistry.",
        decisions: DECISIONS
      }};

      const jsonStr = JSON.stringify(exportPayload, null, 2);
      const blob = new Blob([jsonStr], {{ type: "application/json" }});
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "human_review_decisions.json";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showToast(`Exported ${{count}} decisions to human_review_decisions.json`);
    }}

    function importDecisionsFile(event) {{
      const file = event.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = function(e) {{
        try {{
          const data = JSON.parse(e.target.result);
          if (data.decisions) {{
            DECISIONS = data.decisions;
            saveDecisions();
            applyFilters();
            showToast(`Imported ${{Object.keys(DECISIONS).length}} decisions`);
          }} else {{
            alert("Invalid decisions file format: missing 'decisions' dictionary.");
          }}
        }} catch(err) {{
          alert("Error parsing JSON file: " + err);
        }}
      }};
      reader.readAsText(file);
    }}

    function copyPath(relPath) {{
      navigator.clipboard.writeText(relPath).then(() => {{
        showToast(`Copied path: ${{relPath.split('/').pop()}}`);
      }});
    }}

    let currentModalPath = "";
    function openModal(imgSrc, relPath, deity, dims, size) {{
      const modal = document.getElementById("imageModal");
      const modalImg = document.getElementById("modalImg");
      modalImg.src = imgSrc;
      document.getElementById("modalTitle").textContent = `${{deity.toUpperCase()}} — ${{relPath}}`;
      document.getElementById("modalMeta").textContent = `${{dims}} • ${{size}}`;
      currentModalPath = relPath;
      modal.classList.add("active");
    }}

    function closeModal(e) {{
      document.getElementById("imageModal").classList.remove("active");
    }}

    function copyModalPath() {{
      if (currentModalPath) copyPath(currentModalPath);
    }}

    document.addEventListener("keydown", (e) => {{
      if (e.key === "Escape") closeModal();
    }});

    function showToast(msg) {{
      const toast = document.getElementById("toast");
      toast.textContent = msg;
      toast.classList.add("show");
      setTimeout(() => toast.classList.remove("show"), 2000);
    }}

    window.onload = initFilters;
  </script>
</body>
</html>
"""


def generate_dashboard_file(
    inventory_path: Path | str = "data/review/candidate_asset_inventory.json",
    matrix_path: Path | str = "data/review/deity_coverage_matrix.json",
    duplicates_path: Path | str = "data/review/duplicates_and_broken.json",
    frames_dir: Path | str = "data/review/extracted_frames",
    output_html_path: Path | str = "data/review/asset_review_dashboard.html",
) -> Path:
    """Reads inventory JSON and generates the self-contained HTML review dashboard."""
    inv_p = Path(inventory_path)
    mat_p = Path(matrix_path)
    dup_p = Path(duplicates_path)
    f_dir = Path(frames_dir)
    out_p = Path(output_html_path)

    if not inv_p.exists():
        raise FileNotFoundError(f"Inventory JSON not found: {inv_p}")

    inventory = json.loads(inv_p.read_text(encoding="utf-8"))
    matrix = json.loads(mat_p.read_text(encoding="utf-8")) if mat_p.exists() else {}
    duplicates = json.loads(dup_p.read_text(encoding="utf-8")) if dup_p.exists() else {}

    # Frame map for videos
    frame_map: dict[str, str] = {}
    if f_dir.exists():
        for item in inventory:
            if item.get("file_type") == "video":
                stem = Path(item["rel_path"]).stem
                for f in f_dir.glob(f"*{stem}*"):
                    frame_map[item["rel_path"]] = f"extracted_frames/{f.name}"
                    break

    html_content = build_dashboard_html(
        inventory_data=inventory,
        matrix_data=matrix,
        duplicates_data=duplicates,
        frame_map=frame_map,
    )

    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(html_content, encoding="utf-8")
    return out_p
