// State variables
let currentToken = localStorage.getItem("whistledrop_mod_token") || null;
let piiTimeout = null;
let searchTimeout = null;

// --- Tab Switching ---
function switchTab(tabId) {
  document.querySelectorAll(".tab-pane").forEach(el => el.classList.remove("active"));
  document.querySelectorAll(".nav-btn").forEach(el => {
    if (!el.classList.contains("api-link")) el.classList.remove("active");
  });

  const targetPane = document.getElementById(`tab-${tabId}`);
  const targetBtn = document.getElementById(`nav-btn-${tabId}`);
  if (targetPane) targetPane.classList.add("active");
  if (targetBtn) targetBtn.classList.add("active");

  if (tabId === "admin") {
    checkAdminAuthState();
  }
}

// --- Toast Notifications ---
function showToast(message, type = "info") {
  const toast = document.getElementById("toast");
  toast.textContent = message;
  toast.className = `toast toast-${type}`;
  toast.classList.remove("hidden");
  setTimeout(() => {
    toast.classList.add("hidden");
  }, 4000);
}

// --- PII Pre-Check ---
function debouncePIICheck() {
  clearTimeout(piiTimeout);
  piiTimeout = setTimeout(triggerPIICheck, 700);
}

async function triggerPIICheck() {
  const desc = document.getElementById("report-description").value.trim();
  const banner = document.getElementById("pii-alert-banner");
  const title = document.getElementById("pii-alert-title");
  const text = document.getElementById("pii-alert-desc");

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
      banner.className = "pii-alert-banner warning";
      title.textContent = `🛡️ AI Privacy Alert: ${data.redactions_count} Identifier(s) Detected`;
      text.textContent = `Found: ${data.detected_types.join(", ")}. These will be automatically scrubbed upon transmission.`;
    } else {
      banner.className = "pii-alert-banner";
      title.textContent = "🛡️ AI Privacy Check: Clean";
      text.textContent = "No obvious personal names, emails, IDs, or phone numbers detected.";
    }
    banner.classList.remove("hidden");
  } catch (err) {
    console.error("PII check error:", err);
  }
}

// --- Report Submission ---
async function handleReportSubmit(e) {
  e.preventDefault();
  const submitBtn = document.getElementById("btn-submit-report");
  const btnText = submitBtn.querySelector(".btn-text");
  const spinner = submitBtn.querySelector(".btn-spinner");

  const category = document.getElementById("report-category").value;
  const description = document.getElementById("report-description").value;
  const evidenceUrl = document.getElementById("report-evidence").value.trim() || null;

  submitBtn.disabled = true;
  btnText.textContent = "Encrypting & Scrubbing PII...";

  try {
    const res = await fetch("/api/reports", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        category,
        description,
        evidence_url: evidenceUrl
      })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Failed to submit report");
    }

    // Populate Success Modal
    document.getElementById("success-case-code").textContent = data.case_code;
    document.getElementById("modal-ai-category").textContent = data.ai_analysis.predicted_category || category;
    document.getElementById("modal-ai-confidence").textContent = data.ai_analysis.confidence 
      ? `${(data.ai_analysis.confidence * 100).toFixed(1)}%` 
      : "N/A";
    document.getElementById("modal-severity-badge").textContent = data.ai_analysis.severity;
    document.getElementById("modal-severity-badge").className = `severity-badge-pill badge severity-${data.ai_analysis.severity}`;
    document.getElementById("modal-ai-pii").textContent = data.ai_analysis.pii_redacted 
      ? `${data.ai_analysis.redactions_count} scrubbed` 
      : "None detected";

    document.getElementById("modal-success").classList.remove("hidden");
    document.getElementById("report-form").reset();
    document.getElementById("pii-alert-banner").classList.add("hidden");

  } catch (err) {
    showToast(err.message, "error");
  } finally {
    submitBtn.disabled = false;
    btnText.textContent = "Transmit Anonymous Report";
  }
}

function copySuccessCaseCode() {
  const code = document.getElementById("success-case-code").textContent;
  navigator.clipboard.writeText(code).then(() => {
    document.getElementById("copy-btn-text").textContent = "✓ Copied!";
    setTimeout(() => {
      document.getElementById("copy-btn-text").textContent = "📋 Copy Code";
    }, 2000);
  });
}

function closeSuccessModal() {
  document.getElementById("modal-success").classList.add("hidden");
}

function proceedToTrackFromModal() {
  const code = document.getElementById("success-case-code").textContent;
  closeSuccessModal();
  switchTab("track");
  document.getElementById("track-case-code").value = code;
  document.getElementById("track-form").dispatchEvent(new Event("submit"));
}

// --- Tracking ---
async function handleTrackSubmit(e) {
  e.preventDefault();
  const codeInput = document.getElementById("track-case-code");
  const code = codeInput.value.trim().toUpperCase();
  const resultContainer = document.getElementById("track-result-container");

  try {
    const res = await fetch(`/api/reports/${encodeURIComponent(code)}`);
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || "Unable to find case record");
    }

    // Populate Details
    document.getElementById("track-display-code").textContent = data.case_code;
    
    const catBadge = document.getElementById("track-display-category");
    catBadge.textContent = data.category;
    
    const sevBadge = document.getElementById("track-display-severity");
    sevBadge.textContent = data.severity;
    sevBadge.className = `badge severity-${data.severity}`;

    const stBadge = document.getElementById("track-display-status");
    stBadge.textContent = data.status;
    stBadge.className = `badge status-badge status-${data.status}`;

    // Stepper logic
    updateStepper(data.status);

    // Timeline updates
    const feed = document.getElementById("track-timeline-feed");
    feed.innerHTML = "";
    if (data.updates && data.updates.length > 0) {
      data.updates.forEach(upd => {
        const item = document.createElement("div");
        item.className = "timeline-item";
        item.innerHTML = `
          <div class="timeline-dot"></div>
          <div class="timeline-content">
            <div class="timeline-header">
              <span class="timeline-status">${upd.status}</span>
              <span class="timeline-date">${new Date(upd.timestamp).toLocaleString()}</span>
            </div>
            <div class="timeline-message">${escapeHtml(upd.message)}</div>
          </div>
        `;
        feed.appendChild(item);
      });
    }

    resultContainer.classList.remove("hidden");
  } catch (err) {
    showToast(err.message, "error");
    resultContainer.classList.add("hidden");
  }
}

function updateStepper(status) {
  const stepSub = document.getElementById("step-submitted");
  const stepRev = document.getElementById("step-under-review");
  const stepRes = document.getElementById("step-resolved");
  const line1 = document.getElementById("line-1");
  const line2 = document.getElementById("line-2");

  // Reset
  [stepSub, stepRev, stepRes].forEach(s => s.className = "stepper-step");
  [line1, line2].forEach(l => l.className = "stepper-line");

  if (status === "SUBMITTED") {
    stepSub.classList.add("active");
  } else if (status === "UNDER_REVIEW") {
    stepSub.classList.add("completed");
    line1.classList.add("active");
    stepRev.classList.add("active");
  } else if (status === "RESOLVED" || status === "DISMISSED") {
    stepSub.classList.add("completed");
    line1.classList.add("active");
    stepRev.classList.add("completed");
    line2.classList.add("active");
    stepRes.classList.add("completed");
    stepRes.querySelector(".step-label").textContent = status === "RESOLVED" ? "Resolved" : "Dismissed";
  }
}

// --- Moderator Portal ---
function checkAdminAuthState() {
  if (currentToken) {
    document.getElementById("admin-login-view").classList.add("hidden");
    document.getElementById("admin-dashboard-view").classList.remove("hidden");
    loadAdminDashboardStats();
    loadAdminReports();
  } else {
    document.getElementById("admin-login-view").classList.remove("hidden");
    document.getElementById("admin-dashboard-view").classList.add("hidden");
  }
}

async function handleAdminLogin(e) {
  e.preventDefault();
  const usernameInput = document.getElementById("admin-username").value;
  const passwordInput = document.getElementById("admin-password").value;

  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: usernameInput, password: passwordInput })
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Authentication failed");
    }

    currentToken = data.access_token;
    localStorage.setItem("whistledrop_mod_token", currentToken);
    document.getElementById("current-mod-username").textContent = data.username;
    checkAdminAuthState();
    showToast("Authenticated successfully as Moderator", "success");
  } catch (err) {
    showToast(err.message, "error");
  }
}

function handleAdminLogout() {
  currentToken = null;
  localStorage.removeItem("whistledrop_mod_token");
  checkAdminAuthState();
  showToast("Signed out", "info");
}

async function loadAdminDashboardStats() {
  try {
    const res = await fetch("/api/admin/dashboard/stats", {
      headers: { "Authorization": `Bearer ${currentToken}` }
    });
    if (res.status === 401) {
      handleAdminLogout();
      return;
    }
    const data = await res.json();

    document.getElementById("stat-total").textContent = data.total_reports || 0;
    document.getElementById("stat-pending").textContent = (data.by_status.UNDER_REVIEW || 0) + (data.by_status.SUBMITTED || 0);
    document.getElementById("stat-critical").textContent = data.by_severity.CRITICAL || 0;
    document.getElementById("stat-resolved").textContent = (data.by_status.RESOLVED || 0);
  } catch (err) {
    console.error("Dashboard stats error:", err);
  }
}

function debounceAdminSearch() {
  clearTimeout(searchTimeout);
  searchTimeout = setTimeout(loadAdminReports, 400);
}

async function loadAdminReports() {
  const status = document.getElementById("filter-status").value;
  const category = document.getElementById("filter-category").value;
  const severity = document.getElementById("filter-severity").value;
  const search = document.getElementById("filter-search").value.trim();

  const params = new URLSearchParams();
  if (status) params.append("status", status);
  if (category) params.append("category", category);
  if (severity) params.append("severity", severity);
  if (search) params.append("search", search);
  params.append("limit", "50");

  try {
    const res = await fetch(`/api/admin/reports?${params.toString()}`, {
      headers: { "Authorization": `Bearer ${currentToken}` }
    });
    if (res.status === 401) {
      handleAdminLogout();
      return;
    }
    const data = await res.json();
    const tbody = document.getElementById("reports-table-body");
    tbody.innerHTML = "";

    if (!data.reports || data.reports.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-dim); padding: 2rem;">No whistleblower reports match the current filter criteria.</td></tr>`;
      return;
    }

    data.reports.forEach(r => {
      const tr = document.createElement("tr");
      const confPercent = r.ai_confidence ? `${(r.ai_confidence * 100).toFixed(0)}%` : "--";
      
      tr.innerHTML = `
        <td><span class="table-code">${r.case_code}</span></td>
        <td>${r.category}</td>
        <td>
          <div class="table-ai-pill">
            <strong>${r.ai_category || r.category}</strong>
            <span class="table-conf">Conf: ${confPercent}</span>
          </div>
        </td>
        <td><span class="badge severity-${r.severity}">${r.severity}</span></td>
        <td><span class="badge status-badge status-${r.status}">${r.status}</span></td>
        <td>
          ${r.similar_reports_count > 0 
            ? `<span class="badge" style="background: rgba(245, 158, 11, 0.2); color: #fbbf24;">⚠️ ${r.similar_reports_count} similar</span>` 
            : `<span style="color: var(--text-dim); font-size: 0.8rem;">None</span>`}
        </td>
        <td style="color: var(--text-dim); font-size: 0.8rem;">${new Date(r.created_at).toLocaleDateString()}</td>
        <td>
          <button class="btn-secondary btn-sm" onclick="inspectReport('${r.id}')">Inspect</button>
        </td>
      `;
      tbody.appendChild(tr);
    });

  } catch (err) {
    console.error("Error loading reports:", err);
  }
}

// --- Report Inspector Drawer ---
async function inspectReport(reportId) {
  try {
    const res = await fetch(`/api/admin/reports/${reportId}`, {
      headers: { "Authorization": `Bearer ${currentToken}` }
    });
    const report = await res.json();
    if (!res.ok) throw new Error(report.detail || "Failed to fetch report details");

    document.getElementById("update-report-id").value = report.id;
    document.getElementById("inspect-case-code").textContent = report.case_code;
    document.getElementById("inspect-category").textContent = report.category;
    
    const sevBadge = document.getElementById("inspect-severity");
    sevBadge.textContent = report.severity;
    sevBadge.className = `badge severity-${report.severity}`;

    const stBadge = document.getElementById("inspect-status");
    stBadge.textContent = report.status;
    stBadge.className = `badge status-badge status-${report.status}`;

    document.getElementById("inspect-pii-badge").textContent = report.pii_redacted 
      ? `🛡️ ${report.redactions_count} PII Items Scrubbed`
      : "🛡️ Zero PII Detected";

    document.getElementById("inspect-description").textContent = report.description;

    const evBox = document.getElementById("inspect-evidence-link");
    const evUrl = document.getElementById("inspect-evidence-url");
    if (report.evidence_url) {
      evUrl.href = report.evidence_url;
      evUrl.textContent = report.evidence_url;
      evBox.classList.remove("hidden");
    } else {
      evBox.classList.add("hidden");
    }

    // AI Confidence & Themes
    document.getElementById("inspect-ai-category").textContent = report.ai_category || report.category;
    const confVal = report.ai_confidence ? (report.ai_confidence * 100).toFixed(1) : 0;
    document.getElementById("inspect-ai-conf-text").textContent = `Confidence: ${confVal}%`;
    document.getElementById("inspect-ai-conf-bar").style.width = `${confVal}%`;

    // Tags
    const tagsContainer = document.getElementById("inspect-tags-container");
    tagsContainer.innerHTML = "";
    if (report.ai_tags && report.ai_tags.length > 0) {
      report.ai_tags.forEach(t => {
        const chip = document.createElement("span");
        chip.className = "tag-chip";
        chip.textContent = `#${t}`;
        tagsContainer.appendChild(chip);
      });
    } else {
      tagsContainer.innerHTML = `<span style="color: var(--text-dim); font-size: 0.8rem;">No tags extracted</span>`;
    }

    // Similar reports
    const simList = document.getElementById("inspect-similar-list");
    simList.innerHTML = "";
    if (report.similar_reports && report.similar_reports.length > 0) {
      report.similar_reports.forEach(sim => {
        const item = document.createElement("div");
        item.className = "similar-case-item";
        item.innerHTML = `
          <div>
            <strong style="color: var(--cyan); font-family: var(--font-mono);">${sim.case_code}</strong>
            <span style="margin-left: 0.5rem; font-size: 0.8rem; color: var(--text-dim);">(${sim.category} - ${sim.status})</span>
          </div>
          <span class="similar-match-pill">${(sim.similarity * 100).toFixed(0)}% Cosine Match</span>
        `;
        simList.appendChild(item);
      });
    } else {
      simList.innerHTML = `<div style="color: var(--text-dim); font-size: 0.85rem;">No co-related or duplicate incidents found in registry.</div>`;
    }

    // Timeline updates
    const tFeed = document.getElementById("inspect-timeline-feed");
    tFeed.innerHTML = "";
    if (report.updates) {
      report.updates.forEach(u => {
        const tItem = document.createElement("div");
        tItem.className = "timeline-item";
        tItem.innerHTML = `
          <div class="timeline-dot"></div>
          <div class="timeline-content">
            <div class="timeline-header">
              <span class="timeline-status">${u.status}</span>
              <span class="timeline-date">${new Date(u.timestamp).toLocaleString()}</span>
            </div>
            <div class="timeline-message">${escapeHtml(u.message)}</div>
          </div>
        `;
        tFeed.appendChild(tItem);
      });
    }

    // Status select defaults
    document.getElementById("new-status-select").value = report.status === "SUBMITTED" ? "UNDER_REVIEW" : report.status;
    document.getElementById("status-note-input").value = "";

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
  const reportId = document.getElementById("update-report-id").value;
  const newStatus = document.getElementById("new-status-select").value;
  const message = document.getElementById("status-note-input").value.trim();

  try {
    const res = await fetch(`/api/admin/reports/${reportId}/status`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${currentToken}`
      },
      body: JSON.stringify({ status: newStatus, message: message })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Status transition rejected");
    }

    showToast("Case status updated successfully!", "success");
    closeInspectorModal();
    loadAdminDashboardStats();
    loadAdminReports();
  } catch (err) {
    showToast(err.message, "error");
  }
}

// Security helper
function escapeHtml(text) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return String(text).replace(/[&<>"']/g, m => map[m]);
}
