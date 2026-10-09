// State variables
let currentToken = localStorage.getItem("whistledrop_mod_token") || null;
let piiTimeout = null;
let searchTimeout = null;
let currentSidebarStatusFilter = "";

// Update top nav and sidebar UI based on auth state
function updateAuthUI() {
  const loginBtn = document.getElementById("btn-open-login-modal");
  const userBadge = document.getElementById("user-avatar-btn");
  if (currentToken) {
    if (loginBtn) loginBtn.classList.add("hidden");
    if (userBadge) userBadge.classList.remove("hidden");
  } else {
    if (loginBtn) loginBtn.classList.remove("hidden");
    if (userBadge) userBadge.classList.add("hidden");
  }
}

// Modal controls for Moderator Login
function openLoginModal() {
  const modal = document.getElementById("modal-login");
  const errBox = document.getElementById("login-error-alert");
  if (errBox) errBox.classList.add("hidden");
  if (modal) modal.classList.remove("hidden");
  const usernameInput = document.getElementById("input-mod-username");
  if (usernameInput) usernameInput.focus();
}

function closeLoginModal() {
  const modal = document.getElementById("modal-login");
  if (modal) modal.classList.add("hidden");
}

async function handleAdminLogin(e) {
  e.preventDefault();
  const usernameInput = document.getElementById("input-mod-username");
  const passwordInput = document.getElementById("input-mod-password");
  const submitBtn = document.getElementById("btn-login-submit");
  const errBox = document.getElementById("login-error-alert");

  const username = usernameInput.value.trim();
  const password = passwordInput.value;

  if (errBox) errBox.classList.add("hidden");
  submitBtn.disabled = true;
  submitBtn.innerHTML = "<span>Verifying...</span>";

  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Invalid credentials");

    currentToken = data.access_token;
    localStorage.setItem("whistledrop_mod_token", currentToken);
    updateAuthUI();
    closeLoginModal();
    showToast("Signed in as moderator", "success");
    switchView("mod-overview");
  } catch (err) {
    if (errBox) {
      errBox.textContent = err.message;
      errBox.classList.remove("hidden");
    } else {
      showToast(err.message, "error");
    }
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = "<span>Unlock Workspace</span>";
  }
}

function handleAdminLogout() {
  currentToken = null;
  localStorage.removeItem("whistledrop_mod_token");
  updateAuthUI();
  showToast("Signed out of moderator workspace", "info");
  switchView("submit");
}

function handleQueueNavClick() {
  if (!currentToken) {
    openLoginModal();
  } else {
    switchView("mod-overview");
  }
}

// --- Sidebar Status and Severity Filters ---
function filterBySidebarStatus(status) {
  if (!currentToken) {
    openLoginModal();
    return;
  }
  currentSidebarStatusFilter = status;
  
  // Update sidebar sub-item active state
  document.querySelectorAll(".nav-sub-item").forEach(el => el.classList.remove("active"));
  if (!status) {
    const el = document.getElementById("filter-view-all");
    if (el) el.classList.add("active");
  } else if (status === "SUBMITTED") {
    const el = document.getElementById("filter-view-submitted");
    if (el) el.classList.add("active");
  } else if (status === "UNDER_REVIEW") {
    const el = document.getElementById("filter-view-review");
    if (el) el.classList.add("active");
  } else if (status === "RESOLVED") {
    const el = document.getElementById("filter-view-resolved");
    if (el) el.classList.add("active");
  } else if (status === "DISMISSED") {
    const el = document.getElementById("filter-view-dismissed");
    if (el) el.classList.add("active");
  }

  // Sync with table dropdown if on overview
  const tableStatusSelect = document.getElementById("table-filter-status");
  if (tableStatusSelect) {
    tableStatusSelect.value = status;
  }
  
  switchView("mod-overview");
  loadAdminReports();
}

function filterBySidebarSeverity(severity) {
  if (!currentToken) {
    openLoginModal();
    return;
  }
  const tableSevSelect = document.getElementById("table-filter-severity");
  if (tableSevSelect) {
    tableSevSelect.value = severity;
  }
  switchView("mod-overview");
  loadAdminReports();
}

// --- User Menu Dropdown ---
function toggleUserMenu() {
  const menu = document.getElementById("user-menu-dropdown");
  if (menu) menu.classList.toggle("hidden");
}

document.addEventListener("click", (e) => {
  const userBtn = document.getElementById("user-avatar-btn");
  const menu = document.getElementById("user-menu-dropdown");
  if (userBtn && menu && !userBtn.contains(e.target) && !menu.contains(e.target)) {
    menu.classList.add("hidden");
  }
});

// --- View Switching ---
function switchView(viewId) {
  if (viewId === "mod-overview" && !currentToken) {
    openLoginModal();
    return;
  }

  document.querySelectorAll(".view-pane").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach(el => {
    if (!el.classList.contains("nav-ext")) el.classList.remove("active");
  });

  const targetPane = document.getElementById(`view-${viewId}`);
  if (targetPane) targetPane.classList.add("active");

  const breadcrumbRoot = document.getElementById("top-breadcrumb-root");
  const breadcrumb = document.getElementById("top-breadcrumb-page");

  if (viewId === "mod-overview") {
    document.getElementById("nav-case-queue").classList.add("active");
    if (breadcrumbRoot) breadcrumbRoot.textContent = "Moderator workspace";
    if (breadcrumb) breadcrumb.textContent = "Case Operations";
    loadAdminDashboardStats();
    loadAdminReports();
  } else if (viewId === "submit") {
    document.getElementById("nav-submit").classList.add("active");
    if (breadcrumbRoot) breadcrumbRoot.textContent = "Public Portal";
    if (breadcrumb) breadcrumb.textContent = "Submit Report";
  } else if (viewId === "track") {
    document.getElementById("nav-track").classList.add("active");
    if (breadcrumbRoot) breadcrumbRoot.textContent = "Public Portal";
    if (breadcrumb) breadcrumb.textContent = "Track Case";
  }
}

// --- Toast Notifications ---
function showToast(message, type = "info") {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.className = `toast-popup toast-${type}`;
  toast.classList.remove("hidden");
  setTimeout(() => {
    toast.classList.add("hidden");
  }, 4000);
}

// --- PII Pre-Check ---
function debouncePIICheck() {
  clearTimeout(piiTimeout);
  piiTimeout = setTimeout(triggerPIICheck, 600);
}

async function triggerPIICheck() {
  const desc = document.getElementById("input-description").value.trim();
  const banner = document.getElementById("pii-alert-banner");
  const title = document.getElementById("pii-banner-title");
  const text = document.getElementById("pii-banner-desc");

  if (desc.length < 15) {
    banner.classList.add("hidden");
    return;
  }

  try {
    const res = await fetch("/api/reports/preview-redaction", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ description: desc })
    });
    const data = await res.json();

    if (data.redactions_count > 0) {
      banner.classList.remove("hidden");
      title.textContent = `🛡️ AI Privacy Alert: ${data.redactions_count} Personal Identifier(s) Detected`;
      text.textContent = `Scrubbing: ${data.detected_types.join(", ")}. These will be masked automatically upon submission.`;
    } else {
      banner.classList.remove("hidden");
      title.textContent = "🛡️ AI Privacy Check: Clean";
      text.textContent = "No obvious names, emails, student/employee IDs, or phone numbers found.";
    }
  } catch (err) {
    console.error("PII preview error:", err);
  }
}

// --- Anonymous Report Submission ---
async function handleReportSubmit(e) {
  e.preventDefault();
  const submitBtn = document.getElementById("btn-submit-report");
  const originalText = submitBtn.innerHTML;

  const category = document.getElementById("input-category").value;
  const description = document.getElementById("input-description").value;
  const evidenceUrl = document.getElementById("input-evidence").value.trim() || null;

  submitBtn.disabled = true;
  submitBtn.innerHTML = "<span>Encrypting & Transmitting...</span>";

  try {
    const res = await fetch("/api/reports", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category, description, evidence_url: evidenceUrl })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Submission failed");

    // Populate Success Modal
    document.getElementById("success-case-code-val").textContent = data.case_code;
    document.getElementById("modal-ai-cat").textContent = data.ai_analysis.predicted_category || category;
    document.getElementById("modal-ai-conf").textContent = data.ai_analysis.confidence 
      ? `${(data.ai_analysis.confidence * 100).toFixed(1)}%` 
      : "N/A";
    
    const sevPill = document.getElementById("modal-sev-badge");
    sevPill.textContent = data.ai_analysis.severity;
    sevPill.className = `sev-pill sev-${data.ai_analysis.severity}`;

    document.getElementById("modal-ai-pii").textContent = data.ai_analysis.pii_redacted 
      ? `${data.ai_analysis.redactions_count} items scrubbed` 
      : "None detected";

    document.getElementById("modal-success").classList.remove("hidden");
    document.getElementById("public-report-form").reset();
    document.getElementById("pii-alert-banner").classList.add("hidden");

    // Refresh dashboard stats in background
    loadAdminDashboardStats();
  } catch (err) {
    showToast(err.message, "error");
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = originalText;
  }
}

function copySuccessCaseCode() {
  const code = document.getElementById("success-case-code-val").textContent;
  navigator.clipboard.writeText(code).then(() => {
    document.getElementById("copy-btn-label").textContent = "✓ Copied!";
    setTimeout(() => {
      document.getElementById("copy-btn-label").textContent = "📋 Copy Code";
    }, 2000);
  });
}

function closeSuccessModal() {
  document.getElementById("modal-success").classList.add("hidden");
}

function proceedToTrackFromModal() {
  const code = document.getElementById("success-case-code-val").textContent;
  closeSuccessModal();
  switchView("track");
  document.getElementById("input-track-code").value = code;
  document.getElementById("public-track-form").dispatchEvent(new Event("submit"));
}

// --- Public Case Tracking ---
async function handleTrackSubmit(e) {
  e.preventDefault();
  const codeInput = document.getElementById("input-track-code");
  const code = codeInput.value.trim().toUpperCase();
  const resultWrap = document.getElementById("track-result-wrap");

  try {
    const res = await fetch(`/api/reports/${encodeURIComponent(code)}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Case code not found");

    document.getElementById("track-disp-code").textContent = data.case_code;
    document.getElementById("track-disp-cat").textContent = data.category;
    
    const sevPill = document.getElementById("track-disp-sev");
    sevPill.textContent = data.severity;
    sevPill.className = `sev-pill sev-${data.severity}`;

    const stPill = document.getElementById("track-disp-status");
    stPill.textContent = formatStatusLabel(data.status);
    stPill.className = `status-pill status-${data.status}`;

    // Stepper
    updateTrackStepper(data.status);

    // Timeline Stream
    const stream = document.getElementById("track-timeline-stream");
    stream.innerHTML = "";
    if (data.updates && data.updates.length > 0) {
      data.updates.forEach(u => {
        const row = document.createElement("div");
        row.className = "timeline-row";
        row.innerHTML = `
          <div class="timeline-bullet"></div>
          <div class="timeline-bubble">
            <div class="bubble-head">
              <span class="bubble-status">${formatStatusLabel(u.status)}</span>
              <span class="bubble-date">${new Date(u.timestamp).toLocaleString()}</span>
            </div>
            <p class="bubble-text">${escapeHtml(u.message)}</p>
          </div>
        `;
        stream.appendChild(row);
      });
    }

    resultWrap.classList.remove("hidden");
  } catch (err) {
    showToast(err.message, "error");
    resultWrap.classList.add("hidden");
  }
}

function updateTrackStepper(status) {
  const s1 = document.getElementById("track-step-1");
  const s2 = document.getElementById("track-step-2");
  const s3 = document.getElementById("track-step-3");
  const c1 = document.getElementById("track-conn-1");
  const c2 = document.getElementById("track-conn-2");

  [s1, s2, s3].forEach(s => s.className = "stepper-item");
  [c1, c2].forEach(c => c.className = "stepper-connector");

  if (status === "SUBMITTED") {
    s1.classList.add("active");
  } else if (status === "UNDER_REVIEW") {
    s1.classList.add("completed");
    c1.classList.add("active");
    s2.classList.add("active");
  } else if (status === "RESOLVED" || status === "DISMISSED") {
    s1.classList.add("completed");
    c1.classList.add("active");
    s2.classList.add("completed");
    c2.classList.add("active");
    s3.classList.add("completed");
    s3.querySelector(".step-title").textContent = status === "RESOLVED" ? "Resolved" : "Dismissed";
  }
}

// --- Moderator Command Center (Dashboard Telemetry & Table) ---
async function loadAdminDashboardStats() {
  if (!currentToken) return;
  try {
    const res = await fetch("/api/admin/dashboard/stats", {
      headers: { "Authorization": `Bearer ${currentToken}` }
    });
    if (!res.ok) {
      if (res.status === 401) {
        handleAdminLogout();
      }
      return;
    }
    const stats = await res.json();

    const total = stats.total_reports || 0;
    const sub = (stats.by_status && stats.by_status.SUBMITTED) || 0;
    const rev = (stats.by_status && stats.by_status.UNDER_REVIEW) || 0;
    const resCount = (stats.by_status && stats.by_status.RESOLVED) || 0;
    const dis = (stats.by_status && stats.by_status.DISMISSED) || 0;

    // KPI row
    document.getElementById("stat-total").textContent = total;
    document.getElementById("stat-total-sub").textContent = `${total} case(s) in registry`;

    document.getElementById("stat-submitted").textContent = sub;
    document.getElementById("stat-submitted-sub").textContent = `${sub} of ${total} reports`;

    document.getElementById("stat-review").textContent = rev;
    document.getElementById("stat-review-sub").textContent = `${rev} of ${total} reports`;

    document.getElementById("stat-resolved").textContent = resCount;
    document.getElementById("stat-resolved-sub").textContent = `${resCount} of ${total} reports`;

    document.getElementById("stat-dismissed").textContent = dis;
    document.getElementById("stat-dismissed-sub").textContent = dis > 0 ? `${dis} of ${total} reports` : "No cases in view";

    // Sidebar counts
    document.getElementById("sidebar-total-badge").textContent = total;
    document.getElementById("sidebar-cnt-all").textContent = total;
    document.getElementById("sidebar-cnt-submitted").textContent = sub;
    document.getElementById("sidebar-cnt-review").textContent = rev;
    document.getElementById("sidebar-cnt-resolved").textContent = resCount;
    document.getElementById("sidebar-cnt-dismissed").textContent = dis;

    // Severity Mix Widget
    const crit = (stats.by_severity && stats.by_severity.CRITICAL) || 0;
    const high = (stats.by_severity && stats.by_severity.HIGH) || 0;
    const med = (stats.by_severity && stats.by_severity.MEDIUM) || 0;
    const low = (stats.by_severity && stats.by_severity.LOW) || 0;

    document.getElementById("severity-distribution-sub").textContent = `Current distribution · ${total} cases`;
    document.getElementById("sev-bar-cnt-crit").textContent = `${crit} / ${total}`;
    document.getElementById("sev-bar-cnt-high").textContent = `${high} / ${total}`;
    document.getElementById("sev-bar-cnt-med").textContent = `${med} / ${total}`;
    document.getElementById("sev-bar-cnt-low").textContent = `${low} / ${total}`;

    const pct = (n) => total > 0 ? `${((n / total) * 100).toFixed(1)}%` : "0%";
    document.getElementById("sev-bar-fill-crit").style.width = pct(crit);
    document.getElementById("sev-bar-fill-high").style.width = pct(high);
    document.getElementById("sev-bar-fill-med").style.width = pct(med);
    document.getElementById("sev-bar-fill-low").style.width = pct(low);

    // AI & Privacy Signals Widget
    const aiM = stats.ai_metrics || {};
    document.getElementById("metric-auto-classified").textContent = aiM.auto_classified || 0;
    document.getElementById("metric-flagged-review").textContent = aiM.flagged_for_review || 0;
    document.getElementById("metric-redactions-total").textContent = aiM.privacy_redacted_cases || 0;
    document.getElementById("metric-high-conf").textContent = total > 0 
      ? `${Math.round((aiM.high_confidence_ratio || 0.8) * 100)}%` 
      : "--";

    // Category Coverage Widget
    const byCat = stats.by_category || {};
    document.getElementById("cat-cnt-sec").textContent = byCat.Security || 0;
    document.getElementById("cat-cnt-har").textContent = byCat.Harassment || 0;
    document.getElementById("cat-cnt-cor").textContent = byCat.Corruption || 0;
    document.getElementById("cat-cnt-tec").textContent = byCat.Technical || 0;
    document.getElementById("cat-cnt-oth").textContent = byCat.Other || 0;

  } catch (err) {
    console.error("Dashboard metrics load error:", err);
  }
}

function debounceAdminSearch() {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(loadAdminReports, 300);
}

async function loadAdminReports() {
  if (!currentToken) return;
  const statusFilter = document.getElementById("table-filter-status").value || currentSidebarStatusFilter;
  const catFilter = document.getElementById("table-filter-category").value;
  const sevFilter = document.getElementById("table-filter-severity").value;
  const searchVal = document.getElementById("table-search-input").value.trim();

  const params = new URLSearchParams();
  if (statusFilter) params.append("status", statusFilter);
  if (catFilter) params.append("category", catFilter);
  if (sevFilter) params.append("severity", sevFilter);
  if (searchVal) params.append("search", searchVal);
  params.append("limit", "50");

  try {
    const res = await fetch(`/api/admin/reports?${params.toString()}`, {
      headers: { "Authorization": `Bearer ${currentToken}` }
    });
    if (!res.ok) {
      if (res.status === 401) {
        handleAdminLogout();
      }
      return;
    }
    const data = await res.json();
    const tbody = document.getElementById("queue-table-body");
    tbody.innerHTML = "";

    document.getElementById("queue-count-tag").textContent = `● ${data.reports.length} shown / ${data.total} total cases`;

    if (!data.reports || data.reports.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="5">
            <div class="empty-queue-box">
              <div class="empty-icon">📂</div>
              <h4>No cases in registry yet</h4>
              <p>The queue is completely clean. Reports will appear here in real time as soon as they are submitted through the public portal.</p>
              <button type="button" class="btn-emerald btn-sm" onclick="switchView('submit')">✍️ Submit a Report</button>
            </div>
          </td>
        </tr>
      `;
      return;
    }

    data.reports.forEach(r => {
      const tr = document.createElement("tr");
      tr.onclick = () => openCaseDossier(r.id);

      tr.innerHTML = `
        <td class="td-case">
          <div class="case-code-wrap">
            <div class="row-code-line">
              <span class="row-case-code">${r.case_code}</span>
              ${r.pii_redacted ? `<span class="row-redacted-badge">🛡️ ${r.redactions_count} redacted in record</span>` : ""}
            </div>
            <div class="row-summary-text">${escapeHtml(r.description_preview)}</div>
          </div>
        </td>
        <td class="td-cat"><span class="row-cat-text">${r.category}</span></td>
        <td class="td-sev"><span class="sev-pill sev-${r.severity}">${r.severity}</span></td>
        <td class="td-status"><span class="status-pill status-${r.status}">${formatStatusLabel(r.status)}</span></td>
        <td class="td-action"><span class="row-chevron">›</span></td>
      `;
      tbody.appendChild(tr);
    });

  } catch (err) {
    console.error("Queue table error:", err);
  }
}

// --- Case Dossier Inspector Drawer ---
async function openCaseDossier(reportId) {
  if (!currentToken) {
    openLoginModal();
    return;
  }
  try {
    const res = await fetch(`/api/admin/reports/${reportId}`, {
      headers: { "Authorization": `Bearer ${currentToken}` }
    });
    if (!res.ok) throw new Error("Unable to retrieve case record");
    const r = await res.json();

    document.getElementById("dossier-target-id").value = r.id;
    document.getElementById("dossier-case-code").textContent = r.case_code;
    
    document.getElementById("dossier-cat-badge").textContent = r.category;
    
    const sevPill = document.getElementById("dossier-sev-badge");
    sevPill.textContent = r.severity;
    sevPill.className = `sev-pill sev-${r.severity}`;

    const stPill = document.getElementById("dossier-status-badge");
    stPill.textContent = formatStatusLabel(r.status);
    stPill.className = `status-pill status-${r.status}`;

    document.getElementById("dossier-pii-badge").textContent = r.pii_redacted 
      ? `🛡️ ${r.redactions_count} PII Items Scrubbed`
      : "🛡️ Zero PII Detected";

    document.getElementById("dossier-narrative-text").textContent = r.description;

    const evWrap = document.getElementById("dossier-evidence-wrap");
    const evUrl = document.getElementById("dossier-evidence-url");
    if (r.evidence_url) {
      evUrl.href = r.evidence_url;
      evUrl.textContent = r.evidence_url;
      evWrap.classList.remove("hidden");
    } else {
      evWrap.classList.add("hidden");
    }

    // AI Confidence & Themes
    const confVal = r.ai_confidence ? (r.ai_confidence * 100).toFixed(1) : 0;
    document.getElementById("dossier-ai-conf-num").textContent = `Confidence: ${confVal}%`;
    document.getElementById("dossier-conf-bar").style.width = `${confVal}%`;

    const tagCloud = document.getElementById("dossier-tags-cloud");
    tagCloud.innerHTML = "";
    if (r.ai_tags && r.ai_tags.length > 0) {
      r.ai_tags.forEach(t => {
        const badge = document.createElement("span");
        badge.className = "tag-badge";
        badge.textContent = `#${t}`;
        tagCloud.appendChild(badge);
      });
    } else {
      tagCloud.innerHTML = `<span style="font-size: 0.75rem; color: var(--ink-400);">No specific tags extracted</span>`;
    }

    // Similar / Duplicate Incidents
    const simFeed = document.getElementById("dossier-similar-feed");
    simFeed.innerHTML = "";
    if (r.similar_reports && r.similar_reports.length > 0) {
      r.similar_reports.forEach(sim => {
        const row = document.createElement("div");
        row.className = "similar-row";
        row.innerHTML = `
          <div>
            <strong class="sim-code">${sim.case_code}</strong>
            <span style="font-size: 0.75rem; color: var(--ink-400); margin-left: 0.4rem;">(${sim.category} · ${formatStatusLabel(sim.status)})</span>
          </div>
          <span class="sim-match-pill">${(sim.similarity * 100).toFixed(0)}% Cosine Match</span>
        `;
        simFeed.appendChild(row);
      });
    } else {
      simFeed.innerHTML = `<div style="font-size: 0.8rem; color: var(--ink-400);">No duplicate or related incidents found in current registry.</div>`;
    }

    // Timeline Stream
    const timeStream = document.getElementById("dossier-timeline-feed");
    timeStream.innerHTML = "";
    if (r.updates) {
      r.updates.forEach(u => {
        const row = document.createElement("div");
        row.className = "timeline-row";
        row.innerHTML = `
          <div class="timeline-bullet"></div>
          <div class="timeline-bubble">
            <div class="bubble-head">
              <span class="bubble-status">${formatStatusLabel(u.status)}</span>
              <span class="bubble-date">${new Date(u.timestamp).toLocaleString()}</span>
            </div>
            <p class="bubble-text">${escapeHtml(u.message)}</p>
          </div>
        `;
        timeStream.appendChild(row);
      });
    }

    // Form inputs default - dynamically configure allowed transitions based on state machine
    const statusSelect = document.getElementById("dossier-status-select");
    const auditNoteInput = document.getElementById("dossier-audit-note");
    const submitBtn = document.querySelector("#dossier-status-form button[type='submit']");

    if (r.status === "SUBMITTED") {
      statusSelect.innerHTML = `
        <option value="UNDER_REVIEW" selected>UNDER_REVIEW (Begin Investigation)</option>
      `;
      statusSelect.disabled = false;
      auditNoteInput.disabled = false;
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = "<span>Record Status Transition</span>";
      }
    } else if (r.status === "UNDER_REVIEW") {
      statusSelect.innerHTML = `
        <option value="RESOLVED" selected>RESOLVED (Action Completed / Closed)</option>
        <option value="DISMISSED">DISMISSED (Insufficient Evidence / False Report)</option>
      `;
      statusSelect.disabled = false;
      auditNoteInput.disabled = false;
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.innerHTML = "<span>Record Status Transition</span>";
      }
    } else {
      // Terminal states: RESOLVED or DISMISSED
      statusSelect.innerHTML = `
        <option value="${r.status}">${r.status} (Case Closed / Terminal)</option>
      `;
      statusSelect.disabled = true;
      auditNoteInput.disabled = true;
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = "<span>Case Closed (Terminal State)</span>";
      }
    }

    auditNoteInput.value = "";

    document.getElementById("modal-inspector").classList.remove("hidden");
  } catch (err) {
    showToast(err.message, "error");
  }
}

function closeInspectorModal() {
  document.getElementById("modal-inspector").classList.add("hidden");
}

async function handleStatusUpdateSubmit(e) {
  e.preventDefault();
  const reportId = document.getElementById("dossier-target-id").value;
  const newStatus = document.getElementById("dossier-status-select").value;
  const message = document.getElementById("dossier-audit-note").value.trim();

  try {
    const res = await fetch(`/api/admin/reports/${reportId}/status`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${currentToken}`
      },
      body: JSON.stringify({ status: newStatus, message })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Status transition rejected");

    showToast("Status transition recorded successfully", "success");
    closeInspectorModal();
    loadAdminDashboardStats();
    loadAdminReports();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// Helpers
function formatStatusLabel(st) {
  if (st === "UNDER_REVIEW") return "Under review";
  if (st === "SUBMITTED") return "Submitted";
  if (st === "RESOLVED") return "Resolved";
  if (st === "DISMISSED") return "Dismissed";
  return st;
}

function escapeHtml(text) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return String(text).replace(/[&<>"']/g, m => map[m]);
}

// Explicit Global Window Bindings for Inline HTML Handlers
window.toggleUserMenu = toggleUserMenu;
window.openLoginModal = openLoginModal;
window.closeLoginModal = closeLoginModal;
window.handleAdminLogin = handleAdminLogin;
window.handleAdminLogout = handleAdminLogout;
window.handleQueueNavClick = handleQueueNavClick;
window.filterBySidebarStatus = filterBySidebarStatus;
window.filterBySidebarSeverity = filterBySidebarSeverity;
window.switchView = switchView;
window.openCaseDossier = openCaseDossier;
window.closeInspectorModal = closeInspectorModal;
window.handleStatusUpdateSubmit = handleStatusUpdateSubmit;
window.handleReportSubmit = handleReportSubmit;
window.copySuccessCaseCode = copySuccessCaseCode;
window.closeSuccessModal = closeSuccessModal;
window.proceedToTrackFromModal = proceedToTrackFromModal;
window.handleTrackSubmit = handleTrackSubmit;
window.debounceAdminSearch = debounceAdminSearch;
window.loadAdminReports = loadAdminReports;
window.loadAdminDashboardStats = loadAdminDashboardStats;
window.debouncePIICheck = debouncePIICheck;

// Bootstrap on page load
document.addEventListener("DOMContentLoaded", () => {
  updateAuthUI();
  switchView("submit");
  if (currentToken) {
    loadAdminDashboardStats();
  }
});
