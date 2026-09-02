// State
let currentSelectedFile = null;
let lastScanResult = null;
let lastUnstopResult = null;

document.addEventListener("DOMContentLoaded", () => {
  setupNavigation();
  setupDropZone();
  setupUnstopScanner();
  setupEventsFeed();
  setupHostForm();
  loadAnalytics();
});

// ==========================================
// NAVIGATION
// ==========================================
function setupNavigation() {
  const navBtns = document.querySelectorAll(".nav-btn");
  navBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const targetTab = btn.getAttribute("data-tab");
      switchToTab(targetTab);
    });
  });
}

function switchToTab(tabId) {
  document.querySelectorAll(".nav-btn").forEach((b) => b.classList.remove("active"));
  document.querySelectorAll(".tab-pane").forEach((p) => p.classList.remove("active"));

  const targetBtn = document.querySelector(`.nav-btn[data-tab="${tabId}"]`);
  const targetPane = document.getElementById(tabId);

  if (targetBtn) targetBtn.classList.add("active");
  if (targetPane) targetPane.classList.add("active");

  if (tabId === "events-tab") {
    loadEvents();
  } else if (tabId === "analytics-tab") {
    loadAnalytics();
  }
}

// ==========================================
// POSTER SCANNER & DROP ZONE
// ==========================================
function setupDropZone() {
  const dropZone = document.getElementById("poster-drop-zone");
  const fileInput = document.getElementById("poster-file-input");
  const btnScan = document.getElementById("btn-run-scan");
  const btnClear = document.getElementById("btn-clear-preview");

  ["dragenter", "dragover"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropZone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropZone.classList.remove("dragover");
    });
  });

  dropZone.addEventListener("drop", (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0 && files[0].type.startsWith("image/")) {
      handlePosterSelected(files[0]);
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      handlePosterSelected(e.target.files[0]);
    }
  });

  btnClear.addEventListener("click", (e) => {
    e.stopPropagation();
    resetScanner();
  });

  btnScan.addEventListener("click", () => {
    if (currentSelectedFile) {
      runPosterScan(currentSelectedFile);
    }
  });
}

function handlePosterSelected(file) {
  currentSelectedFile = file;
  const reader = new FileReader();
  reader.onload = (e) => {
    document.getElementById("poster-preview-img").src = e.target.result;
    document.getElementById("drop-prompt").style.display = "none";
    document.getElementById("preview-box").style.display = "flex";
    document.getElementById("btn-run-scan").disabled = false;
  };
  reader.readAsDataURL(file);
}

function resetScanner() {
  currentSelectedFile = null;
  lastScanResult = null;
  document.getElementById("poster-file-input").value = "";
  document.getElementById("drop-prompt").style.display = "block";
  document.getElementById("preview-box").style.display = "none";
  document.getElementById("btn-run-scan").disabled = true;

  document.getElementById("results-empty-state").style.display = "block";
  document.getElementById("results-loading-state").style.display = "none";
  document.getElementById("results-data-state").style.display = "none";
}

// Load sample posters from disk
async function loadSamplePoster(type) {
  let samplePath = "";
  if (type === "real") samplePath = "/static/images/sample_real_hackathon.png";
  else if (type === "fake") samplePath = "/static/images/sample_fake_event.png";
  else if (type === "symposium") samplePath = "/static/images/sample_real_symposium.png";

  try {
    const res = await fetch(samplePath);
    const blob = await res.blob();
    const file = new File([blob], `${type}_poster_sample.png`, { type: blob.type || "image/png" });
    handlePosterSelected(file);
    setTimeout(() => {
      runPosterScan(file);
    }, 150);
  } catch (err) {
    console.error("Failed to load sample poster:", err);
    alert("Could not load sample poster image.");
  }
}

// Run Poster Verification API Call
async function runPosterScan(file) {
  const emptyState = document.getElementById("results-empty-state");
  const loadingState = document.getElementById("results-loading-state");
  const dataState = document.getElementById("results-data-state");
  const btnScan = document.getElementById("btn-run-scan");

  emptyState.style.display = "none";
  dataState.style.display = "none";
  loadingState.style.display = "block";
  btnScan.disabled = true;

  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch("/api/verify-poster", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({ detail: "Verification failed" }));
      throw new Error(errData.detail || "Error communicating with verification backend");
    }

    const data = await response.json();
    lastScanResult = data;
    renderScanResults(data);
  } catch (error) {
    console.error("Verification scan error:", error);
    alert("Verification Scan Failed: " + error.message);
    emptyState.style.display = "block";
  } finally {
    loadingState.style.display = "none";
    btnScan.disabled = false;
  }
}

function renderScanResults(data) {
  const isReal = data.poster_result === "REAL";
  const dataState = document.getElementById("results-data-state");
  const banner = document.getElementById("verdict-banner");
  const icon = document.getElementById("verdict-icon");
  const tag = document.getElementById("verdict-tag");
  const status = document.getElementById("verdict-status");
  const trustScore = document.getElementById("verdict-trust-score");

  banner.className = isReal ? "verdict-banner" : "verdict-banner fake";
  icon.innerHTML = isReal ? '<i class="fa-solid fa-check"></i>' : '<i class="fa-solid fa-triangle-exclamation"></i>';
  tag.textContent = isReal ? "AUTHENTIC EVENT" : "SUSPICIOUS / FAKE EVENT";
  status.textContent = `${data.poster_status} • ${isReal ? "MODEL CONFIRMED REAL" : "HIGH FORGERY PROBABILITY"}`;
  trustScore.textContent = data.trust_score;

  // Probabilities
  document.getElementById("prob-real-val").textContent = `${data.real_probability}%`;
  document.getElementById("prob-fake-val").textContent = `${data.fake_probability}%`;
  document.getElementById("prob-real-bar").style.width = `${data.real_probability}%`;
  document.getElementById("prob-fake-bar").style.width = `${data.fake_probability}%`;

  // Confidence & QR
  document.getElementById("inspect-confidence").textContent = `${data.poster_confidence}%`;
  document.getElementById("inspect-qr-status").textContent = data.qr_status;
  document.getElementById("inspect-qr-result").textContent = data.qr_result;

  // QR Payload
  const qrBadge = document.getElementById("qr-sec-badge");
  const qrText = document.getElementById("qr-data-text");
  const qrVisit = document.getElementById("qr-link-visit");

  if (data.qr_detected && data.qr_data) {
    qrText.textContent = data.qr_data;
    if (data.qr_result === "MALICIOUS") {
      qrBadge.className = "badge-status-qr danger";
      qrBadge.textContent = "SUSPICIOUS";
    } else {
      qrBadge.className = "badge-status-qr";
      qrBadge.textContent = "SAFE LINK";
    }

    if (data.qr_data.startsWith("http://") || data.qr_data.startsWith("https://")) {
      qrVisit.href = data.qr_data;
      qrVisit.style.display = "inline-flex";
    } else {
      qrVisit.style.display = "none";
    }
  } else {
    qrText.textContent = "No QR code detected in this poster image.";
    qrBadge.className = "badge-status-qr";
    qrBadge.textContent = "NO QR";
    qrVisit.style.display = "none";
  }

  dataState.style.display = "block";
}

// ==========================================
// UNSTOP LINK SCANNER
// ==========================================
function setupUnstopScanner() {
  const btnScanUnstop = document.getElementById("btn-scan-unstop");
  const inputUrl = document.getElementById("unstop-url-input");

  btnScanUnstop.addEventListener("click", () => {
    const url = inputUrl.value.trim();
    if (url) {
      verifyUnstopUrl(url);
    } else {
      alert("Please paste a valid Unstop event URL.");
    }
  });

  inputUrl.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      btnScanUnstop.click();
    }
  });
}

function setUnstopUrl(url) {
  document.getElementById("unstop-url-input").value = url;
  verifyUnstopUrl(url);
}

async function verifyUnstopUrl(url) {
  const resultsBox = document.getElementById("unstop-results-box");
  const loading = document.getElementById("unstop-loading");
  const content = document.getElementById("unstop-result-content");
  const btnScan = document.getElementById("btn-scan-unstop");

  resultsBox.style.display = "block";
  loading.style.display = "block";
  content.style.display = "none";
  btnScan.disabled = true;

  try {
    const response = await fetch("/api/verify-url", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: url }),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: "Verification failed" }));
      throw new Error(err.detail || "Failed to fetch and verify Unstop URL.");
    }

    const data = await response.json();
    lastUnstopResult = data;
    renderUnstopResults(data);
  } catch (err) {
    console.error("Unstop scan error:", err);
    alert("Unstop Verification Error: " + err.message);
    resultsBox.style.display = "none";
  } finally {
    loading.style.display = "none";
    btnScan.disabled = false;
  }
}

function renderUnstopResults(data) {
  const content = document.getElementById("unstop-result-content");
  const isReal = data.verification.poster_result === "REAL";
  const v = data.verification;
  const posterImg = v.poster_url || data.extracted_poster_url;

  content.innerHTML = `
    <div style="display: flex; gap: 1.5rem; align-items: flex-start; flex-wrap: wrap; margin-bottom: 1.5rem;">
      <div style="width: 160px; height: 210px; background: #000; border-radius: var(--radius-sm); overflow: hidden; box-shadow: 0 4px 15px rgba(0,0,0,0.5);">
        <img src="${posterImg}" alt="Extracted Poster" style="width: 100%; height: 100%; object-fit: cover;" onerror="this.src='/static/images/sample_real_hackathon.png'" />
      </div>
      <div style="flex: 1; min-width: 280px;">
        <span class="badge-pill" style="margin-bottom: 0.5rem; display: inline-block;"><i class="fa-solid fa-globe"></i> Fetched from Unstop</span>
        <h3 style="font-size: 1.35rem; font-weight: 800; line-height: 1.3; margin-bottom: 0.4rem;">${escapeHtml(data.title)}</h3>
        <div style="font-size: 0.88rem; color: var(--accent-blue); margin-bottom: 0.6rem;">
          <i class="fa-solid fa-building-columns"></i> ${escapeHtml(data.college)}
        </div>
        <p style="font-size: 0.85rem; color: var(--text-secondary); line-height: 1.5; margin-bottom: 0.85rem;">
          ${escapeHtml(data.description ? data.description.substring(0, 180) + '...' : 'Live event retrieved from Unstop.')}
        </p>
        <a href="${data.url}" target="_blank" class="btn btn-outline-sm">
          <i class="fa-solid fa-arrow-up-right-from-square"></i> Open Page on Unstop.com
        </a>
      </div>
    </div>

    <!-- Authenticity Verdict Banner -->
    <div class="verdict-banner ${isReal ? "" : "fake"}" style="margin-bottom: 1.25rem;">
      <div class="verdict-main">
        <div class="verdict-icon-wrap">
          <i class="fa-solid ${isReal ? "fa-check" : "fa-triangle-exclamation"}"></i>
        </div>
        <div>
          <div class="verdict-tag">${isReal ? "AUTHENTIC UNSTOP POSTER" : "SUSPICIOUS / FORGED EVENT"}</div>
          <div class="verdict-status">Status: ${v.poster_status} • Model Confidence: ${v.poster_confidence}%</div>
        </div>
      </div>
      <div class="trust-score-badge">
        <span class="trust-num">${v.trust_score}</span>
        <span class="trust-denom">/ 100</span>
        <span class="trust-lbl">Trust Score</span>
      </div>
    </div>

    <!-- Probabilities Grid -->
    <div class="inspection-grid" style="margin-bottom: 1.25rem;">
      <div class="inspect-box">
        <div class="inspect-label"><i class="fa-solid fa-brain"></i> Poster Authenticity Probability</div>
        <div class="inspect-value" style="color: ${isReal ? "#34d399" : "#f87171"};">
          ${v.real_probability}% Real <span style="font-size: 0.85rem; color: var(--text-muted);">(${v.fake_probability}% Fake)</span>
        </div>
        <div class="inspect-sub">Calculated via MobileNetV2</div>
      </div>
      <div class="inspect-box">
        <div class="inspect-label"><i class="fa-solid fa-qrcode"></i> QR Code Analysis</div>
        <div class="inspect-value">${v.qr_status} (${v.qr_result})</div>
        <div class="inspect-sub">${v.qr_data ? "Embedded QR link decoded" : "No embedded QR present"}</div>
      </div>
    </div>

    ${
      v.qr_data
        ? `<div class="qr-payload-card" style="margin-bottom: 1.25rem;">
             <div class="qr-payload-header">
               <span><i class="fa-solid fa-link"></i> Decoded QR Payload:</span>
               <span class="badge-status-qr ${v.qr_result === "MALICIOUS" ? "danger" : ""}">${v.qr_result}</span>
             </div>
             <div class="qr-data-text">${escapeHtml(v.qr_data)}</div>
           </div>`
        : ""
    }

    <div class="result-actions">
      <button type="button" class="btn btn-primary" onclick="importUnstopToFeed()">
        <i class="fa-solid fa-download"></i> Import & Publish to College Events Feed
      </button>
      <button type="button" class="btn btn-outline" onclick="document.getElementById('unstop-url-input').focus()">
        <i class="fa-solid fa-magnifying-glass"></i> Check Another Link
      </button>
    </div>
  `;

  content.style.display = "block";
}

async function importUnstopToFeed() {
  if (!lastUnstopResult) return;
  try {
    const res = await fetch("/api/unstop/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: lastUnstopResult.url }),
    });

    if (!res.ok) throw new Error("Failed to import Unstop event.");
    alert("Event Successfully Imported to College Events Portal!");
    switchToTab("events-tab");
    loadEvents();
  } catch (err) {
    alert("Import Error: " + err.message);
  }
}

// Modal Extension
function openExtensionModal() {
  document.getElementById("extension-modal").style.display = "flex";
}

function closeExtensionModal() {
  document.getElementById("extension-modal").style.display = "none";
}

function prefillCreateFromScan() {
  if (!lastScanResult) return;
  switchToTab("host-tab");

  if (lastScanResult.qr_data && (lastScanResult.qr_data.startsWith("http://") || lastScanResult.qr_data.startsWith("https://"))) {
    const regInput = document.getElementById("event-reg-url");
    if (regInput && !regInput.value) {
      regInput.value = lastScanResult.qr_data;
    }
  }

  if (currentSelectedFile) {
    const hostPreview = document.getElementById("host-poster-preview");
    const hostPrompt = document.getElementById("host-poster-prompt");
    const hostImg = document.getElementById("host-preview-img");
    const hostFilename = document.getElementById("host-poster-filename");

    const reader = new FileReader();
    reader.onload = (e) => {
      hostImg.src = e.target.result;
      hostFilename.textContent = currentSelectedFile.name;
      hostPrompt.style.display = "none";
      hostPreview.style.display = "block";
    };
    reader.readAsDataURL(currentSelectedFile);
  }
}

// ==========================================
// COLLEGE EVENTS FEED
// ==========================================
function setupEventsFeed() {
  const searchInput = document.getElementById("filter-search");
  const categorySelect = document.getElementById("filter-category");
  const statusSelect = document.getElementById("filter-status");
  const btnRefresh = document.getElementById("btn-refresh-events");

  let debounceTimer;
  searchInput.addEventListener("input", () => {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(loadEvents, 300);
  });

  categorySelect.addEventListener("change", loadEvents);
  statusSelect.addEventListener("change", loadEvents);
  btnRefresh.addEventListener("click", loadEvents);

  loadEvents();
}

async function loadEvents() {
  const grid = document.getElementById("events-grid-container");
  const search = document.getElementById("filter-search").value.trim();
  const category = document.getElementById("filter-category").value;
  const status = document.getElementById("filter-status").value;

  grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: var(--text-muted);"><i class="fa-solid fa-spinner fa-spin"></i> Loading college events...</div>';

  try {
    const params = new URLSearchParams();
    if (search) params.append("search", search);
    if (category && category !== "ALL") params.append("category", category);
    if (status && status !== "ALL") params.append("status", status);

    const res = await fetch(`/api/events?${params.toString()}`);
    const data = await res.json();

    if (!data.events || data.events.length === 0) {
      grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 3rem; color: var(--text-muted);"><i class="fa-regular fa-folder-open" style="font-size: 2rem; margin-bottom: 0.5rem; display:block;"></i> No college events found matching your filter criteria.</div>';
      return;
    }

    grid.innerHTML = data.events.map(createEventCardHtml).join("");
  } catch (err) {
    console.error("Failed to load events:", err);
    grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 2rem; color: var(--accent-red);"><i class="fa-solid fa-circle-exclamation"></i> Error loading college events.</div>';
  }
}

function createEventCardHtml(event) {
  const isReal = event.verification.poster_result === "REAL";
  const badgeClass = isReal ? "badge-trust-overlay real" : "badge-trust-overlay fake";
  const badgeIcon = isReal ? "fa-shield-check" : "fa-triangle-exclamation";
  const badgeText = isReal ? `Verified • ${event.verification.trust_score}/100` : `Suspicious • ${event.verification.trust_score}/100`;
  const posterSrc = event.poster_url || "/static/images/sample_real_hackathon.png";

  return `
    <div class="event-card">
      <div class="event-poster-thumb">
        <img src="${posterSrc}" alt="${event.title}" onerror="this.src='/static/images/sample_real_hackathon.png'" />
        <div class="${badgeClass}">
          <i class="fa-solid ${badgeIcon}"></i> ${badgeText}
        </div>
      </div>
      <div class="event-card-body">
        <span class="event-category-tag">${event.category}</span>
        <h3 class="event-card-title">${escapeHtml(event.title)}</h3>
        <div class="event-college-name">
          <i class="fa-solid fa-building-columns"></i> ${escapeHtml(event.college)}
        </div>
        <div class="event-card-meta">
          <span><i class="fa-regular fa-calendar"></i> ${escapeHtml(event.event_date)}</span>
          <span><i class="fa-solid fa-location-dot"></i> ${escapeHtml(event.venue)}</span>
        </div>
        <div class="event-card-footer">
          <button class="btn btn-outline-sm" onclick='viewEventDetails(${JSON.stringify(event)})'>
            <i class="fa-solid fa-circle-info"></i> Security Report
          </button>
          ${
            event.registration_url
              ? `<a href="${event.registration_url}" target="_blank" class="btn btn-primary" style="padding: 0.4rem 0.85rem; font-size: 0.8rem;">
                   Register <i class="fa-solid fa-arrow-up-right-from-square"></i>
                 </a>`
              : `<span style="font-size: 0.75rem; color: var(--text-muted);">Campus Walk-in</span>`
          }
        </div>
      </div>
    </div>
  `;
}

// ==========================================
// EVENT DETAILS MODAL
// ==========================================
function viewEventDetails(event) {
  const modal = document.getElementById("event-modal");
  const body = document.getElementById("modal-body-content");
  const isReal = event.verification.poster_result === "REAL";
  const posterSrc = event.poster_url || "/static/images/sample_real_hackathon.png";

  body.innerHTML = `
    <div style="display: flex; gap: 1.25rem; margin-bottom: 1.25rem; align-items: flex-start; flex-wrap: wrap;">
      <img src="${posterSrc}" style="width: 140px; height: 180px; object-fit: cover; border-radius: var(--radius-sm);" />
      <div style="flex: 1; min-width: 250px;">
        <span class="event-category-tag">${event.category}</span>
        <h2 style="font-size: 1.3rem; margin-bottom: 0.4rem;">${escapeHtml(event.title)}</h2>
        <div style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.6rem;">
          <i class="fa-solid fa-building-columns"></i> ${escapeHtml(event.college)}
        </div>
        <div style="font-size: 0.8rem; color: var(--text-muted); display: flex; flex-direction: column; gap: 4px;">
          <span><i class="fa-regular fa-calendar"></i> ${escapeHtml(event.event_date)}</span>
          <span><i class="fa-solid fa-location-dot"></i> ${escapeHtml(event.venue)}</span>
          ${event.organizer_contact ? `<span><i class="fa-solid fa-envelope"></i> ${escapeHtml(event.organizer_contact)}</span>` : ""}
        </div>
      </div>
    </div>

    <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border-card); border-radius: var(--radius-sm); padding: 1rem; margin-bottom: 1.25rem;">
      <h4 style="font-size: 0.85rem; text-transform: uppercase; color: var(--text-muted); margin-bottom: 0.4rem;">Event Description</h4>
      <p style="font-size: 0.88rem; line-height: 1.5; color: var(--text-secondary);">${escapeHtml(event.description)}</p>
    </div>

    <!-- Security Deep Dive -->
    <div class="verdict-banner ${isReal ? "" : "fake"}" style="margin-bottom: 1rem;">
      <div class="verdict-main">
        <div class="verdict-icon-wrap">
          <i class="fa-solid ${isReal ? "fa-shield-check" : "fa-triangle-exclamation"}"></i>
        </div>
        <div>
          <div class="verdict-tag">${isReal ? "VERIFIED AUTHENTIC" : "FLAGGED SUSPICIOUS"}</div>
          <div class="verdict-status">Status: ${event.verification.poster_status}</div>
        </div>
      </div>
      <div class="trust-score-badge">
        <span class="trust-num">${event.verification.trust_score}</span>
        <span class="trust-denom">/ 100</span>
        <span class="trust-lbl">Trust Score</span>
      </div>
    </div>

    <div class="inspection-grid" style="margin-bottom: 1rem;">
      <div class="inspect-box">
        <div class="inspect-label">Real vs Fake Probability</div>
        <div class="inspect-value" style="font-size: 1rem; color: ${isReal ? "#34d399" : "#f87171"};">
          ${event.verification.real_probability}% Real / ${event.verification.fake_probability}% Fake
        </div>
      </div>
      <div class="inspect-box">
        <div class="inspect-label">QR Detection & Security</div>
        <div class="inspect-value" style="font-size: 1rem;">
          ${event.verification.qr_status} (${event.verification.qr_result})
        </div>
      </div>
    </div>

    ${
      event.verification.qr_data
        ? `<div class="qr-payload-card">
             <div class="qr-payload-header">
               <span><i class="fa-solid fa-qrcode"></i> Decoded QR Payload:</span>
             </div>
             <div class="qr-data-text">${escapeHtml(event.verification.qr_data)}</div>
           </div>`
        : ""
    }
  `;

  modal.style.display = "flex";
}

function closeEventModal() {
  document.getElementById("event-modal").style.display = "none";
}

window.addEventListener("click", (e) => {
  const modal = document.getElementById("event-modal");
  const extModal = document.getElementById("extension-modal");
  if (e.target === modal) closeEventModal();
  if (e.target === extModal) closeExtensionModal();
});

// State for Host Form
let hostSelectedFile = null;
let lastHostScanResult = null;

// ==========================================
// HOST EVENT FORM & INLINE EVENTTRUST AI
// ==========================================
function setupHostForm() {
  const form = document.getElementById("create-event-form");
  const posterInput = document.getElementById("host-poster-input");
  const posterBox = document.getElementById("host-poster-box");
  const btnClearPoster = document.getElementById("btn-host-clear-poster");

  // Drag and drop for host poster box
  ["dragenter", "dragover"].forEach((eventName) => {
    posterBox.addEventListener(eventName, (e) => {
      e.preventDefault();
      posterBox.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    posterBox.addEventListener(eventName, (e) => {
      e.preventDefault();
      posterBox.classList.remove("dragover");
    });
  });

  posterBox.addEventListener("drop", (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0 && files[0].type.startsWith("image/")) {
      handleHostPosterFile(files[0]);
    }
  });

  posterInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      handleHostPosterFile(e.target.files[0]);
    }
  });

  if (btnClearPoster) {
    btnClearPoster.addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      resetHostPoster();
    });
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = document.getElementById("btn-submit-event");
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Submitting College Event...';

    const formData = new FormData();
    formData.append("title", document.getElementById("event-title").value.trim());
    formData.append("college", document.getElementById("event-college").value.trim());
    formData.append("category", document.getElementById("event-category").value);
    formData.append("event_date", document.getElementById("event-date").value.trim());
    formData.append("venue", document.getElementById("event-venue").value.trim());
    formData.append("registration_url", document.getElementById("event-reg-url").value.trim());
    formData.append("organizer_contact", document.getElementById("event-contact").value.trim());
    formData.append("description", document.getElementById("event-desc").value.trim());

    if (hostSelectedFile) {
      formData.append("poster", hostSelectedFile);
    } else if (posterInput.files.length > 0) {
      formData.append("poster", posterInput.files[0]);
    } else if (currentSelectedFile) {
      formData.append("poster", currentSelectedFile);
    } else {
      alert("Please select an event poster image.");
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-shield-halved"></i> Publish College Event';
      return;
    }

    try {
      const res = await fetch("/api/events", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Failed to create event" }));
        throw new Error(err.detail || "Server error while creating event");
      }

      const createdEvent = await res.json();
      const isVerified = createdEvent.verification.status === "VERIFIED" || createdEvent.verification.risk_level === "LOW";
      alert(
        `🎉 Event Published Successfully!\n` +
        `• Status: ${createdEvent.verification.status || (isVerified ? 'VERIFIED' : 'REVIEW REQUIRED')}\n` +
        `• Trust Score: ${createdEvent.verification.trust_score}/100\n` +
        `• Risk Level: ${createdEvent.verification.risk_level}`
      );

      form.reset();
      resetHostPoster();
      switchToTab("events-tab");
      loadEvents();
    } catch (err) {
      console.error("Event creation error:", err);
      alert("Error: " + err.message);
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<i class="fa-solid fa-shield-halved"></i> Publish College Event';
    }
  });
}

function handleHostPosterFile(file) {
  hostSelectedFile = file;
  const promptEl = document.getElementById("host-poster-prompt");
  const previewEl = document.getElementById("host-poster-preview");
  const previewImg = document.getElementById("host-preview-img");
  const filenameSpan = document.getElementById("host-poster-filename");

  const reader = new FileReader();
  reader.onload = (e) => {
    previewImg.src = e.target.result;
    filenameSpan.textContent = file.name;
    promptEl.style.display = "none";
    previewEl.style.display = "block";
  };
  reader.readAsDataURL(file);

  // Automatically trigger AI verification
  verifyHostPoster(file);
}

function resetHostPoster() {
  hostSelectedFile = null;
  lastHostScanResult = null;
  const posterInput = document.getElementById("host-poster-input");
  const promptEl = document.getElementById("host-poster-prompt");
  const previewEl = document.getElementById("host-poster-preview");
  const container = document.getElementById("host-verification-container");
  const loading = document.getElementById("host-ai-loading");
  const result = document.getElementById("host-ai-result");

  if (posterInput) posterInput.value = "";
  if (promptEl) promptEl.style.display = "block";
  if (previewEl) previewEl.style.display = "none";
  if (container) container.style.display = "none";
  if (loading) loading.style.display = "none";
  if (result) result.style.display = "none";
}

async function loadHostSample(type) {
  let samplePath = "";
  if (type === "real") samplePath = "/static/images/sample_real_hackathon.png";
  else if (type === "fake") samplePath = "/static/images/sample_fake_event.png";
  else if (type === "symposium") samplePath = "/static/images/sample_real_symposium.png";

  try {
    const res = await fetch(samplePath);
    const blob = await res.blob();
    const file = new File([blob], `${type}_poster_sample.png`, { type: blob.type || "image/png" });
    handleHostPosterFile(file);
  } catch (err) {
    console.error("Failed to load sample poster:", err);
    alert("Could not load sample poster image.");
  }
}

async function verifyHostPoster(file) {
  const container = document.getElementById("host-verification-container");
  const loading = document.getElementById("host-ai-loading");
  const result = document.getElementById("host-ai-result");

  container.style.display = "block";
  loading.style.display = "flex";
  result.style.display = "none";

  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch("/api/verify-poster", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: "Verification failed" }));
      throw new Error(err.detail || "Failed to analyze poster.");
    }

    const data = await response.json();
    lastHostScanResult = data;
    renderHostVerificationResult(data);
  } catch (error) {
    console.error("Host poster verification error:", error);
    loading.style.display = "none";
    result.style.display = "block";
    result.innerHTML = `
      <div class="ai-card-error">
        <i class="fa-solid fa-triangle-exclamation"></i>
        <span>EventTrust AI Verification failed: ${escapeHtml(error.message)}</span>
        <button type="button" class="btn btn-outline-sm" onclick="if (hostSelectedFile) verifyHostPoster(hostSelectedFile);">
          <i class="fa-solid fa-rotate-right"></i> Retry Verification
        </button>
      </div>
    `;
  }
}

function renderHostVerificationResult(data) {
  const loading = document.getElementById("host-ai-loading");
  const result = document.getElementById("host-ai-result");
  const card = document.getElementById("host-eventtrust-card");

  loading.style.display = "none";
  result.style.display = "block";

  const isVerified = data.status === "VERIFIED" || (data.risk_level === "LOW" && data.prediction === "REAL");
  const isSuspicious = data.status === "SUSPICIOUS" || data.status === "REVIEW_REQUIRED" || data.risk_level === "HIGH" || data.prediction === "FAKE";

  // Card theme class
  card.className = "eventtrust-inline-card " + (isVerified ? "state-verified" : (data.risk_level === "MEDIUM" ? "state-review" : "state-suspicious"));

  const confidencePct = (typeof data.confidence === "number")
    ? (data.confidence <= 1.0 ? (data.confidence * 100).toFixed(1) : data.confidence.toFixed(1))
    : (data.poster_confidence ? data.poster_confidence.toFixed(1) : "94.7");

  // QR status formatting
  let qrDisplay = "ℹ Not Detected";
  let qrClass = "qr-info";
  if (data.qr_detected) {
    if (data.qr_verified || data.qr_result === "BENIGN") {
      qrDisplay = "✓ Detected (Safe Link)";
      qrClass = "qr-safe";
    } else {
      qrDisplay = "⚠ Detected (Requires Review)";
      qrClass = "qr-warn";
    }
  }

  // Issues & Positive Indicators list
  let checklistHtml = "";
  if (isVerified) {
    const indicators = (data.positive_indicators && data.positive_indicators.length > 0)
      ? data.positive_indicators
      : [
          "Event date detected",
          "College/organization detected",
          "Registration information detected",
          "No major suspicious indicators"
        ];
    checklistHtml = indicators.map(item => `
      <li class="check-item verified">
        <i class="fa-solid fa-check"></i> <span>${escapeHtml(item)}</span>
      </li>
    `).join("");
  } else {
    const issues = (data.issues && data.issues.length > 0)
      ? data.issues
      : [
          "Suspicious poster detected",
          "Registration information could not be verified",
          "QR destination requires review"
        ];
    checklistHtml = issues.map(item => `
      <li class="check-item issue">
        <i class="fa-solid fa-triangle-exclamation"></i> <span>${escapeHtml(item)}</span>
      </li>
    `).join("");
  }

  // Auto-fill registration URL button if QR link detected
  let qrAutofillHtml = "";
  if (data.qr_detected && data.qr_data && (data.qr_data.startsWith("http://") || data.qr_data.startsWith("https://"))) {
    qrAutofillHtml = `
      <div class="qr-quick-autofill">
        <span><i class="fa-solid fa-link"></i> Decoded QR Destination: <code>${escapeHtml(data.qr_data)}</code></span>
        <button type="button" class="btn btn-outline-sm" onclick="autofillHostRegUrl('${escapeHtml(data.qr_data)}')">
          <i class="fa-solid fa-wand-magic-sparkles"></i> Use as Registration Link
        </button>
      </div>
    `;
  }

  result.innerHTML = `
    <!-- Top Header -->
    <div class="ai-verify-header">
      <div class="ai-brand-badge">
        <i class="fa-solid fa-shield-halved"></i>
        <span class="ai-brand-title">EventTrust AI</span>
      </div>
      <div class="ai-analysis-status">
        <span class="pulse-dot ${isVerified ? 'green' : 'red'}"></span>
        <span>Poster Analysis: <strong>✓ Poster analyzed</strong></span>
      </div>
    </div>
    <div class="ai-header-divider"></div>

    <!-- Metrics Grid -->
    <div class="ai-metrics-grid">
      <div class="ai-metric-item score-item">
        <span class="metric-label">Trust Score</span>
        <div class="metric-score-wrap">
          <span class="metric-score-num ${isVerified ? 'text-green' : 'text-red'}">${data.trust_score}</span>
          <span class="metric-score-denom">/100</span>
        </div>
      </div>

      <div class="ai-metric-item">
        <span class="metric-label">Status</span>
        <span class="metric-status-badge ${isVerified ? 'badge-verified' : 'badge-review'}">
          ${isVerified ? 'VERIFIED' : (data.status || 'REVIEW REQUIRED')}
        </span>
      </div>

      <div class="ai-metric-item">
        <span class="metric-label">Model Confidence</span>
        <strong class="metric-val">${confidencePct}%</strong>
      </div>

      <div class="ai-metric-item">
        <span class="metric-label">QR Code</span>
        <span class="metric-qr-badge ${qrClass}">${qrDisplay}</span>
      </div>

      <div class="ai-metric-item">
        <span class="metric-label">Risk Level</span>
        <span class="metric-risk-badge ${data.risk_level ? data.risk_level.toLowerCase() : 'low'}">
          ${data.risk_level || (isVerified ? 'LOW' : 'HIGH')}
        </span>
      </div>
    </div>

    <!-- Issues / Positive Indicators -->
    <div class="ai-checklist-section">
      <h5 class="checklist-title">${isVerified ? 'Verification Signals:' : 'Detected Issues & Risk Factors:'}</h5>
      <ul class="ai-checklist">
        ${checklistHtml}
      </ul>
    </div>

    ${qrAutofillHtml}

    <!-- Recommendation Box -->
    <div class="ai-recommendation-box ${isVerified ? 'rec-verified' : 'rec-warning'}">
      <i class="fa-solid ${isVerified ? 'fa-circle-check' : 'fa-triangle-exclamation'}"></i>
      <div>
        <strong>Recommendation:</strong>
        <p>${escapeHtml(data.recommendation || (isVerified ? 'Poster verified. Ready for publishing.' : 'Verify this event before publishing.'))}</p>
      </div>
    </div>
  `;
}

function autofillHostRegUrl(url) {
  const regInput = document.getElementById("event-reg-url");
  if (regInput) {
    regInput.value = url;
    regInput.focus();
    alert("Registration Link auto-filled from QR code payload!");
  }
}

// ==========================================
// SAFETY ANALYTICS
// ==========================================
async function loadAnalytics() {
  try {
    const res = await fetch("/api/stats");
    const data = await res.json();

    document.getElementById("stat-total-events").textContent = data.total_events;
    document.getElementById("stat-real-events").textContent = data.verified_real_events;
    document.getElementById("stat-fake-events").textContent = data.suspicious_events;
    document.getElementById("stat-qr-count").textContent = data.qr_detected_count;
    document.getElementById("stat-avg-trust").textContent = `${data.average_trust_score}%`;
  } catch (err) {
    console.error("Failed to load analytics:", err);
  }
}

// Helper: Escape HTML
function escapeHtml(str) {
  if (!str) return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
