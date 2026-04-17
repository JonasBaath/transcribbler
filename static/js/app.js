/* ============================================================
   transcribbler — Frontend application
   ============================================================ */

"use strict";

// In-app dialogs — used instead of window.confirm/alert/prompt so Electron's
// native Chromium dialog (with Electron icon) doesn't appear.
function _appDialog({ message, title, mode, defaultValue = "" }) {
  // mode: "confirm" | "alert" | "prompt"
  return new Promise(resolve => {
    const modal  = document.getElementById("modal-confirm");
    const msgEl  = document.getElementById("confirm-modal-message");
    const titleEl = document.getElementById("confirm-modal-title");
    const okBtn  = document.getElementById("btn-confirm-ok");
    const canBtn = document.getElementById("btn-confirm-cancel");
    if (!modal || !msgEl || !okBtn || !canBtn) {
      if (mode === "alert")   { window.alert(message); resolve(undefined); return; }
      if (mode === "prompt")  { resolve(window.prompt(message, defaultValue)); return; }
      resolve(window.confirm(message)); return;
    }
    msgEl.textContent = message;
    titleEl.textContent = title || (mode === "alert" ? "Meddelande" : "Bekräfta");

    // Inject/remove an input for prompt mode
    let input = modal.querySelector("#confirm-modal-input");
    if (mode === "prompt") {
      if (!input) {
        input = document.createElement("input");
        input.type = "text";
        input.id = "confirm-modal-input";
        input.style.cssText = "width:100%;margin-top:8px;";
        msgEl.insertAdjacentElement("afterend", input);
      }
      input.value = defaultValue;
    } else if (input) {
      input.remove(); input = null;
    }

    // Hide Cancel button for alert mode
    canBtn.style.display = (mode === "alert") ? "none" : "";

    modal.classList.remove("hidden");
    const cleanup = (v) => {
      modal.classList.add("hidden");
      canBtn.style.display = "";
      okBtn.removeEventListener("click", onOk);
      canBtn.removeEventListener("click", onCancel);
      document.removeEventListener("keydown", onKey);
      modal.removeEventListener("click", onBackdrop);
      resolve(v);
    };
    const onOk = () => {
      if (mode === "prompt") cleanup(input ? input.value : defaultValue);
      else if (mode === "alert") cleanup(undefined);
      else cleanup(true);
    };
    const onCancel = () => cleanup(mode === "prompt" ? null : false);
    const onKey = (e) => {
      if (e.key === "Escape") { e.preventDefault(); onCancel(); }
      else if (e.key === "Enter" && !(mode === "prompt" && e.target !== input)) {
        e.preventDefault(); onOk();
      }
    };
    const onBackdrop = (e) => { if (e.target === modal) onCancel(); };
    okBtn.addEventListener("click", onOk);
    canBtn.addEventListener("click", onCancel);
    document.addEventListener("keydown", onKey);
    modal.addEventListener("click", onBackdrop);
    setTimeout(() => (input || okBtn).focus(), 0);
  });
}
function appConfirm(message, opts = {}) { return _appDialog({ message, title: opts.title, mode: "confirm" }); }
function appAlert(message, opts = {}) {
  const container = document.getElementById("toast-container");
  if (container) {
    const toast = document.createElement("div");
    toast.className = "toast";
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
      toast.classList.add("toast-out");
      toast.addEventListener("animationend", () => toast.remove());
    }, 2500);
    return Promise.resolve();
  }
  return _appDialog({ message, title: opts.title, mode: "alert" });
}
function appPrompt(message, defaultValue = "", opts = {}) { return _appDialog({ message, title: opts.title, mode: "prompt", defaultValue }); }

// ---------------------------------------------------------------------------
// Electron native menu integration
// ---------------------------------------------------------------------------
if (window.electronAPI) {
  if (window.electronAPI.platform === 'darwin') {
    document.documentElement.classList.add('electron-mac');
    document.body.classList.add('electron-mac');
  }
  // Double-click on topbar or splash to maximize/restore (macOS hiddenInset titlebar)
  if (window.electronAPI.titlebarDoubleClick) {
    for (const id of ['topbar', 'splash']) {
      const el = document.getElementById(id);
      if (el) {
        el.addEventListener('dblclick', (e) => {
          // Only trigger on the drag region itself, not on interactive children
          if (e.target.closest('button, input, select, textarea, a, [contenteditable]')) return;
          window.electronAPI.titlebarDoubleClick();
        });
      }
    }
  }
  if (window.electronAPI.onMenuClick) {
    window.electronAPI.onMenuClick((btnId) => {
      const el = document.getElementById(btnId);
      if (el) el.click();
    });
  }
  // Sync menu language with app language
  if (window.electronAPI.setMenuLang) {
    window.electronAPI.setMenuLang(currentLang);
    const origSetLang = setLang;
    setLang = function(lang) {
      origSetLang(lang);
      window.electronAPI.setMenuLang(lang);
    };
  }
}

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let project = null;
let _currentFolder = null;
let _currentCoder = null;
let currentTid = null;
let currentText = "";
let annotations = [];

// Pending annotation selection
let pendingSelection = null;  // {start, end, text}
let pendingPoint = null;      // {x, y} (normalised 0-1) for image-pin annotations
let pendingAnnId = null;      // for edit/detail popup
let _annEditId = null;        // when set, ann-popup confirm PATCHes this annotation's code
let _savedSelRange = null;    // saved Selection range so popup focus doesn't collapse it

// Feature state — declared here so all functions can reference them
let formattingSpans = [];
let numberingEnabled  = false;
let transOrderEnabled = false;
let selectedTids = new Set();   // multi-selected transcript ids
let _dragSelecting = false;     // true while left button held over transcript list
let _dragMoved     = false;     // true once drag extended to a second item
let currentFontIdx = parseInt(localStorage.getItem("transcribbler_font_size") || "1", 10);
let currentFontFamily = localStorage.getItem("transcribbler_font_family") || "sans";

// Search state — must be at top to avoid TDZ when clearSearch() is called early
let searchMatches = [];
let searchIndex  = -1;

// Font formatting constants — must be at top (used by applyFontSettings called early)
const FMT_SIZES    = [13, 15, 17, 20];
const FMT_KEY_SIZE = "transcribbler_font_size";
const FMT_KEY_FAM  = "transcribbler_font_family";

// Audio job state
let _pendingJobResult = null;
let _hfTokenCallback  = null;
let _audioCommitResolve = null;  // resolves when speaker dialog is confirmed/cancelled — drives multi-file audio batches
let _audioBatch = [];            // {jobId, name, speakers_found, voice_matches} per pending audio file (multi-file mode)
let _transcriptAborted = false;  // set true when user cancels mid-transcription

// Voice profile state
let _voiceProfileMeta = null;   // {coder, model, dim, created} or null

// Undo / redo stacks — each entry: {type: "add"|"delete", tid, ann}
let undoStack = [];
let redoStack = [];
const MAX_UNDO_DEPTH = 200;
function pushUndo(a) { undoStack.push(a); if (undoStack.length > MAX_UNDO_DEPTH) undoStack.shift(); _annChangeCounter++; }
function pushRedo(a) { redoStack.push(a); if (redoStack.length > MAX_UNDO_DEPTH) redoStack.shift(); }

// Audio player / segment sync
let segments       = [];   // [{speaker, start, end, text}] for current transcript
let segmentCharMap = [];   // [{charStart, charEnd, timeStart, timeEnd}]

// Text edit mode
let _textEditMode = false;

// Feature: segment weight + anchor
let useWeightEnabled   = false;

// Feature: waveform
let useWaveformEnabled = false;
let _wavesurfer        = null;   // WaveSurfer instance for current audio transcript
let _wavesurferSeeking = false;  // prevent feedback loop between audio <-> wavesurfer seek
let _wfZoom            = 1;      // current zoom level for waveform
let _wfHandlers        = null;   // bound handlers on audio-player/button — removed in _destroyWaveform

// OCR bounding box overlay
let _ocrBoxesVisible = false;

// Per-transcript source image panel state: tid → {open: bool, boxesVisible: bool}
let _sourceImgState = {};

// Analysis view state
let _analysisData = null;
let _analysisState = {
  selectedCodes: new Set(),
  selectedExcerpts: new Set(),
  displayMode: "separate",
  exportMode: false,
  showMemos: false,
  anchorOnly: false,
  searchQuery: "",
};
let _analysisActive = false;

// ---------------------------------------------------------------------------
// PopupManager — prevents floating popups from overlapping each other.
// When a new popup is shown, the manager nudges it so it does not cover any
// popup that is already visible.
// ---------------------------------------------------------------------------
const PopupManager = (() => {
  const _registered = [];
  function register(el) {
    if (!_registered.find(r => r.el === el)) {
      _registered.push({ id: el.id || el.className, el });
    }
  }
  function _visibleRects(excludeEl) {
    return _registered
      .filter(r => r.el !== excludeEl &&
                   !r.el.classList.contains("hidden") &&
                   r.el.offsetParent !== null)
      .map(r => r.el.getBoundingClientRect());
  }
  function _overlaps(a, b) {
    return !(a.right <= b.left || a.left >= b.right ||
             a.bottom <= b.top || a.top >= b.bottom);
  }
  /**
   * Position `el` at (x, y) while avoiding overlap with other visible popups.
   * `el` must already be unhidden so we can measure it.
   */
  function position(el, x, y, opts = {}) {
    const GAP = 8;
    el.style.left = x + "px";
    el.style.top  = y + "px";
    const w = el.offsetWidth  || opts.estWidth  || 260;
    const h = el.offsetHeight || opts.estHeight || 280;
    // Viewport clamp (preserves original positionPopup logic).
    let left = Math.min(x, window.innerWidth - w - 4);
    let top  = y;
    if (top + h > window.innerHeight && y - h - GAP > 0) {
      top = y - h - GAP;
    } else {
      top = Math.min(top, window.innerHeight - h - 4);
    }
    left = Math.max(4, left);
    top  = Math.max(4, top);
    // Nudge away from every visible sibling popup.
    const others = _visibleRects(el);
    for (let attempt = 0; attempt < 6; attempt++) {
      const myRect = { left, top, right: left + w, bottom: top + h };
      const hit = others.find(r => _overlaps(myRect, r));
      if (!hit) break;
      const down = hit.bottom + GAP;
      if (down + h <= window.innerHeight) { top = down; continue; }
      const up = hit.top - h - GAP;
      if (up >= 0) { top = up; continue; }
      const right = hit.right + GAP;
      if (right + w <= window.innerWidth) { left = right; continue; }
      const leftC = hit.left - w - GAP;
      if (leftC >= 0) { left = leftC; continue; }
      top += GAP * 2; left += GAP * 2;
      break;
    }
    el.style.left = left + "px";
    el.style.top  = top  + "px";
  }
  return { register, position };
})();
let _annChangeCounter = 0;

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------
async function api(method, url, body = null) {
  try {
    const opts = { method, headers: { "Content-Type": "application/json" } };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(url, opts);
    if (!res.ok) {
      const raw = await res.text();
      let errText = raw;
      try { const j = JSON.parse(raw); errText = j.error || raw; } catch {}
      console.error(`API ${method} ${url} → ${res.status}`, errText);
      return { ok: false, error: errText, _status: res.status };
    }
    return res.json();
  } catch (err) {
    console.error(`API ${method} ${url} exception:`, err);
    return { ok: false, error: String(err) };
  }
}
const GET  = (u)    => api("GET", u);
const POST = (u, b) => api("POST", u, b);
const DEL  = (u)    => api("DELETE", u);
const PATCH = (u,b) => api("PATCH", u, b);

// ---------------------------------------------------------------------------
// Splash / project open+new
// ---------------------------------------------------------------------------
const CODER_KEY = "transcribbler_coder";

document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
  });
});

// ---- Load recent projects on startup ----
async function loadRecentProjects() {
  const res = await GET("/api/project/recent");
  const list = document.getElementById("recent-list");
  const section = document.getElementById("recent-section");
  list.innerHTML = "";
  if (!res.recent || res.recent.length === 0) {
    section.style.display = "none";
    return;
  }
  section.style.display = "";
  res.recent.slice(0, 5).forEach((r, i) => {
    const li = document.createElement("li");
    if (i === 0) li.classList.add("recent-selected");
    li.innerHTML = `
      <span class="recent-icon">📁</span>
      <span class="recent-info">
        <span class="recent-name">${esc(r.name)}</span>
        <span class="recent-path">${esc(r.folder)}</span>
      </span>
      <button class="recent-delete" title="${t("delete.title") || "Ta bort"}">✕</button>`;
    li.querySelector(".recent-delete").addEventListener("click", (e) => {
      e.stopPropagation();
      _showDeleteConfirm(r.folder, r.name);
    });
    li.addEventListener("click", () => {
      document.querySelectorAll("#recent-list li").forEach(el => el.classList.remove("recent-selected"));
      li.classList.add("recent-selected");
      document.getElementById("open-folder").value = r.folder;
      _checkEncrypted(r.folder);
    });
    list.appendChild(li);
  });
  // Pre-fill most recent
  document.getElementById("open-folder").value = res.recent[0].folder;
  _checkEncrypted(res.recent[0].folder);
}

// ---- Native folder pickers ----
async function pickFolder(targetInputId) {
  let folder;
  if (window.electronAPI) {
    folder = await window.electronAPI.pickFolder();
  } else {
    const res = await GET("/api/pick-folder");
    folder = res.folder;
  }
  if (folder) {
    document.getElementById(targetInputId).value = folder;
    if (targetInputId === "open-folder") _checkEncrypted(folder);
  }
}
document.getElementById("btn-pick-open").addEventListener("click", () => pickFolder("open-folder"));
document.getElementById("btn-pick-new").addEventListener("click",  () => pickFolder("new-folder"));

// ---- Open ----
["open-coder", "open-folder", "open-password"].forEach(id => {
  document.getElementById(id).addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); document.getElementById("btn-open").click(); }
  });
});

document.getElementById("btn-open").addEventListener("click", async () => {
  const folder = document.getElementById("open-folder").value.trim();
  const coder  = document.getElementById("open-coder").value.trim();
  const password = document.getElementById("open-password").value || "";
  const errEl  = document.getElementById("splash-error");
  errEl.textContent = "";
  if (!folder || !coder) { errEl.textContent = t("error.fill.all"); return; }
  const body = { folder, coder };
  if (password) body.password = password;
  const res = await POST("/api/project/open", body);
  if (res.error === "encrypted" || res.error === "wrong_password") {
    document.getElementById("open-password-section").classList.remove("hidden");
    errEl.textContent = res.error === "encrypted"
      ? t("error.password.required") : t("error.wrong.password");
    document.getElementById("open-password").focus();
    return;
  }
  if (res.error) { errEl.textContent = res.error; return; }
  localStorage.setItem(CODER_KEY, coder);
  enterApp(res.project, coder, folder);
});

// ---- New ----
["new-coder", "new-folder", "new-name"].forEach(id => {
  document.getElementById(id).addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); document.getElementById("btn-new").click(); }
  });
});

document.getElementById("btn-new").addEventListener("click", async () => {
  const folder = document.getElementById("new-folder").value.trim();
  const name   = document.getElementById("new-name").value.trim();
  const coder  = document.getElementById("new-coder").value.trim();
  const errEl  = document.getElementById("splash-error");
  errEl.textContent = "";
  if (!folder || !name || !coder) { errEl.textContent = t("error.fill.all"); return; }

  // Encryption
  const encrypt = document.getElementById("new-encrypt").checked;
  let password = "";
  if (encrypt) {
    const mode = document.querySelector('input[name="pw-mode"]:checked')?.value;
    if (mode === "strong") {
      password = document.getElementById("generated-passphrase").textContent.trim();
    } else {
      password = document.getElementById("new-password").value;
      const confirm = document.getElementById("new-password-confirm").value;
      if (!_validatePassword(password)) return;
      if (password !== confirm) { errEl.textContent = t("pw.mismatch"); return; }
    }
    if (!password) { errEl.textContent = t("error.fill.all"); return; }
  }

  const body = { folder, name, coder };
  if (password) body.password = password;
  const res = await POST("/api/project/new", body);
  if (res.error) { errEl.textContent = res.error; return; }
  localStorage.setItem(CODER_KEY, coder);
  enterApp(res.project, coder, folder);
});

// ---- Encryption UI interactions ----
document.getElementById("new-encrypt").addEventListener("change", (e) => {
  document.getElementById("encrypt-options").classList.toggle("hidden", !e.target.checked);
  if (e.target.checked) {
    const mode = document.querySelector('input[name="pw-mode"]:checked')?.value;
    if (mode === "strong") _fetchPassphrase();
  }
});

document.querySelectorAll('input[name="pw-mode"]').forEach(r => {
  r.addEventListener("change", () => {
    const isStrong = r.value === "strong" && r.checked;
    document.getElementById("pw-standard").classList.toggle("hidden", isStrong);
    document.getElementById("pw-strong").classList.toggle("hidden", !isStrong);
    if (isStrong) _fetchPassphrase();
  });
});

async function _fetchPassphrase() {
  const res = await GET("/api/crypto/generate-passphrase");
  if (res.passphrase) {
    document.getElementById("generated-passphrase").textContent = res.passphrase;
  }
}

document.getElementById("btn-regen-passphrase").addEventListener("click", _fetchPassphrase);

document.getElementById("btn-copy-passphrase").addEventListener("click", async () => {
  const text = document.getElementById("generated-passphrase").textContent;
  try {
    await navigator.clipboard.writeText(text);
    const btn = document.getElementById("btn-copy-passphrase");
    const orig = btn.textContent;
    btn.textContent = t("encrypt.copied");
    setTimeout(() => { btn.textContent = orig; }, 1500);
  } catch (e) { /* clipboard blocked */ }
});

// Password validation hints
document.getElementById("new-password").addEventListener("input", (e) => {
  _renderPwHints(e.target.value);
});

function _validatePassword(pw) {
  const ok = pw.length >= 8 && /[A-Z]/.test(pw) && /[a-z]/.test(pw)
    && /[0-9]/.test(pw) && /[^A-Za-z0-9]/.test(pw);
  if (!ok) {
    _renderPwHints(pw);
  }
  return ok;
}

function _renderPwHints(pw) {
  const hints = document.getElementById("pw-hints");
  const checks = [
    { ok: pw.length >= 8, label: t("pw.hint.length") },
    { ok: /[A-Z]/.test(pw), label: t("pw.hint.upper") },
    { ok: /[a-z]/.test(pw), label: t("pw.hint.lower") },
    { ok: /[0-9]/.test(pw), label: t("pw.hint.digit") },
    { ok: /[^A-Za-z0-9]/.test(pw), label: t("pw.hint.special") },
  ];
  hints.innerHTML = checks.map(c =>
    `<li class="${c.ok ? "ok" : "fail"}">${c.label}</li>`
  ).join("");
}

// Check encryption when folder is selected for open
async function _checkEncrypted(folder) {
  if (!folder) return;
  const res = await POST("/api/project/check-encrypted", { folder });
  const section = document.getElementById("open-password-section");
  if (res.encrypted) {
    section.classList.remove("hidden");
    document.getElementById("open-password").focus();
  } else {
    section.classList.add("hidden");
    document.getElementById("open-password").value = "";
  }
}

// ---- Delete project confirmation ----
let _deleteFolder = null;

function _showDeleteConfirm(folder, name) {
  _deleteFolder = folder;
  document.getElementById("delete-project-name").textContent = name + " (" + folder + ")";
  document.getElementById("delete-confirm-check").checked = false;
  document.getElementById("btn-delete-confirm").disabled = true;
  const modal = document.getElementById("modal-delete-project");
  modal.classList.remove("hidden");
  applyTranslations();
}

document.getElementById("delete-confirm-check").addEventListener("change", (e) => {
  document.getElementById("btn-delete-confirm").disabled = !e.target.checked;
});

document.getElementById("btn-delete-confirm").addEventListener("click", async () => {
  if (!_deleteFolder) return;
  const res = await POST("/api/project/delete", { folder: _deleteFolder });
  _deleteFolder = null;
  document.getElementById("modal-delete-project").classList.add("hidden");
  if (res.ok || res.error) {
    loadRecentProjects();
  }
});

document.getElementById("btn-delete-cancel").addEventListener("click", () => {
  _deleteFolder = null;
  document.getElementById("modal-delete-project").classList.add("hidden");
});

function enterApp(proj, coder, folder) {
  project = proj;
  _currentCoder = coder;
  if (folder) _currentFolder = folder;
  numberingEnabled  = !!proj.numbering;
  transOrderEnabled = !!proj.trans_order;
  document.getElementById("splash").classList.add("hidden");
  document.getElementById("app").classList.remove("hidden");
  document.getElementById("project-title").textContent = proj.name;
  document.getElementById("coder-badge").textContent = `Kodare: ${coder}`;
  const nb = document.getElementById("setting-numbering");
  if (nb) nb.checked = numberingEnabled;
  const to = document.getElementById("setting-trans-order");
  if (to) to.checked = transOrderEnabled;
  const ai = document.getElementById("setting-auto-identify");
  if (ai) ai.checked = !!proj.auto_identify;
  useWeightEnabled   = !!proj.use_weight;
  useWaveformEnabled = !!proj.use_waveform;
  const uw = document.getElementById("setting-use-weight");
  if (uw) uw.checked = useWeightEnabled;
  const uwv = document.getElementById("setting-use-waveform");
  if (uwv) uwv.checked = useWaveformEnabled;
  renderTranscriptList();
  renderCodebook();
  // Load voice profile status in background
  loadVoiceProfileStatus();
}

// ---- Inline project rename ----
(function () {
  const el = document.getElementById("project-title");

  function startEdit() {
    if (!project) return;
    el.contentEditable = "true";
    el.focus();
    // Place cursor at end
    const range = document.createRange();
    range.selectNodeContents(el);
    range.collapse(false);
    window.getSelection().removeAllRanges();
    window.getSelection().addRange(range);
  }

  async function commitEdit() {
    el.contentEditable = "false";
    const newName = el.textContent.trim();
    if (!newName || newName === project.name) {
      el.textContent = project.name; // restore if blank or unchanged
      return;
    }
    const res = await PATCH("/api/project/settings", { name: newName });
    if (res.ok) {
      project.name = newName;
    } else {
      el.textContent = project.name; // revert on error
    }
  }

  el.addEventListener("dblclick", startEdit);
  el.addEventListener("keydown", e => {
    if (e.key === "Enter") { e.preventDefault(); commitEdit(); }
    if (e.key === "Escape") { el.textContent = project ? project.name : ""; el.contentEditable = "false"; }
  });
  el.addEventListener("blur", () => {
    if (el.contentEditable === "true") commitEdit();
  });
})();

// ---- Language toggle ----
function toggleLang() {
  setLang(currentLang === "sv" ? "en" : "sv");
}
document.getElementById("btn-lang").addEventListener("click", toggleLang);
document.getElementById("btn-lang-splash").addEventListener("click", toggleLang);

// ---- Restore saved coder name & load recents on page load ----
window.addEventListener("DOMContentLoaded", () => {
  // Register all known floating popups with PopupManager.
  ["ann-popup", "ann-detail", "code-tooltip",
   "transcript-ctx-menu", "code-ctx-menu", "settings-popover"
  ].forEach(id => {
    const el = document.getElementById(id);
    if (el) PopupManager.register(el);
  });

  applyTranslations();
  const savedCoder = localStorage.getItem(CODER_KEY);
  if (savedCoder) {
    document.getElementById("open-coder").value = savedCoder;
    document.getElementById("new-coder").value  = savedCoder;
  }
  loadRecentProjects().then(() => {
    const folder = document.getElementById("open-folder").value.trim();
    const coder  = document.getElementById("open-coder").value.trim();
    if (folder && coder) {
      document.getElementById("btn-open").focus();
    } else {
      document.getElementById(folder ? "open-coder" : "open-folder").focus();
    }
  });
});

document.getElementById("btn-close-project").addEventListener("click", () => {
  // Remember current project so we can restore on cancel
  window._preSwitch = { folder: _currentFolder, coder: _currentCoder };
  resetAllProjectState();
  document.getElementById("app").classList.add("hidden");
  document.getElementById("splash").classList.remove("hidden");
  document.getElementById("btn-cancel-switch").classList.remove("hidden");
  // Restore saved coder name into splash inputs
  const savedCoder = localStorage.getItem(CODER_KEY);
  if (savedCoder) {
    document.getElementById("open-coder").value = savedCoder;
    document.getElementById("new-coder").value  = savedCoder;
  }
  // Check if the pre-filled folder is encrypted
  const folder = document.getElementById("open-folder").value.trim();
  if (folder) _checkEncrypted(folder);
});

document.getElementById("btn-cancel-switch").addEventListener("click", async () => {
  const pre = window._preSwitch;
  document.getElementById("btn-cancel-switch").classList.add("hidden");
  window._preSwitch = null;
  if (pre?.folder && pre?.coder) {
    const errEl = document.getElementById("splash-error");
    errEl.textContent = "";
    const pw = document.getElementById("open-password").value || "";
    const body = { folder: pre.folder, coder: pre.coder };
    if (pw) body.password = pw;
    const res = await POST("/api/project/open", body);
    if (res.error === "encrypted" || res.error === "wrong_password") {
      document.getElementById("open-password-section").classList.remove("hidden");
      errEl.textContent = res.error === "encrypted"
        ? t("error.password.required") : t("error.wrong.password");
      document.getElementById("open-password").focus();
      return;
    }
    if (res.error) { errEl.textContent = res.error; return; }
    localStorage.setItem(CODER_KEY, pre.coder);
    enterApp(res.project, pre.coder, pre.folder);
  }
});

/**
 * Reset ALL UI and in-memory state so no data leaks between projects.
 * Called when closing / switching projects.
 */
function resetAllProjectState() {
  // --- Core data ---
  project = null; _currentFolder = null; _currentCoder = null;
  currentTid = null; currentText = ""; annotations = [];

  // --- Encryption UI reset ---
  document.getElementById("open-password-section")?.classList.add("hidden");
  const openPw = document.getElementById("open-password");
  if (openPw) openPw.value = "";
  document.getElementById("splash-error").textContent = "";

  // --- Editor & formatting ---
  formattingSpans = [];
  segments = []; segmentCharMap = [];
  if (_textEditMode) exitTextEditMode();

  // --- Undo / redo ---
  undoStack = []; redoStack = [];

  // --- Selection / pending annotation ---
  pendingSelection = null; pendingPoint = null;
  pendingAnnId = null; _annEditId = null;
  selectedTids = new Set();

  // --- Search (in-transcript) ---
  searchMatches = []; searchIndex = -1;
  const searchBar = document.getElementById("search-bar");
  if (searchBar) searchBar.classList.add("hidden");
  const searchInput = document.getElementById("search-input");
  if (searchInput) searchInput.value = "";

  // --- Project-wide search modal ---
  closeProjectSearch();

  // --- Analysis view ---
  _analysisData = null;
  _analysisState = {
    selectedCodes: new Set(),
    selectedExcerpts: new Set(),
    displayMode: "separate",
    exportMode: false,
    showMemos: false,
    anchorOnly: false,
    searchQuery: "",
  };
  _analysisActive = false;
  _analysisLastCounter = -1;
  _annChangeCounter = 0;
  // Ensure analysis view is hidden and coding view restored
  document.getElementById("analysis-view")?.classList.add("hidden");
  ["sidebar-left", "handle-left", "editor-pane", "handle-right", "sidebar-right"].forEach(id => {
    document.getElementById(id)?.classList.remove("hidden");
  });
  document.getElementById("btn-view-coding")?.classList.add("active");
  document.getElementById("btn-view-analysis")?.classList.remove("active");

  // --- Audio / waveform ---
  _destroyWaveform();
  const ap = document.getElementById("audio-player");
  if (ap) { ap.pause(); ap.removeAttribute("src"); ap.load(); }
  document.getElementById("audio-player-wrap")?.classList.add("hidden");
  document.getElementById("transcript-text")?.classList.remove("has-audio");
  _pendingJobResult = null;
  _hfTokenCallback = null;
  _audioCommitResolve = null;
  _audioBatch = [];
  _transcriptAborted = false;

  // --- Voice profile ---
  _voiceProfileMeta = null;

  // --- Source image / OCR state ---
  _sourceImgState = {};
  _ocrBoxesVisible = false;

  // --- Editor pane DOM ---
  document.getElementById("editor-placeholder")?.classList.remove("hidden");
  document.getElementById("editor-content")?.classList.add("hidden");
  const toolbar = document.getElementById("editor-toolbar");
  if (toolbar) toolbar.classList.add("hidden");

  // --- Transcript list ---
  const ul = document.getElementById("transcript-list");
  if (ul) ul.innerHTML = "";

  // --- Codebook sidebar ---
  const cbTree = document.getElementById("codebook-tree");
  if (cbTree) cbTree.innerHTML = "";

  // --- Analysis content ---
  const analysisContent = document.getElementById("analysis-content");
  if (analysisContent) analysisContent.innerHTML = "";
  const analysisCbTree = document.getElementById("analysis-codebook-tree");
  if (analysisCbTree) analysisCbTree.innerHTML = "";
}

// ---------------------------------------------------------------------------
// Transcript list
// ---------------------------------------------------------------------------
/** A, B, …, Z, AA, AB, … */
function transLabel(idx) {
  let label = "";
  let n = idx;
  do {
    label = String.fromCharCode(65 + (n % 26)) + label;
    n = Math.floor(n / 26) - 1;
  } while (n >= 0);
  return label;
}

function renderTranscriptList() {
  const ul = document.getElementById("transcript-list");
  ul.innerHTML = "";
  const transcripts = project.transcripts || [];

  // Group transcripts by category
  const groups = {};          // categoryName -> [{tr, idx}]
  const uncategorized = [];
  transcripts.forEach((tr, idx) => {
    if (tr.category) {
      (groups[tr.category] = groups[tr.category] || []).push({ tr, idx });
    } else {
      uncategorized.push({ tr, idx });
    }
  });
  const hasCategories = Object.keys(groups).length > 0;

  function appendHeader(label) {
    const hdr = document.createElement("li");
    hdr.className = "trans-category-header";
    hdr.textContent = label;
    ul.appendChild(hdr);
  }

  function appendItem({ tr, idx }) {
    const li = document.createElement("li");
    li.dataset.tid = tr.id;
    if (tr.id === currentTid) li.classList.add("active");
    if (selectedTids.has(tr.id)) li.classList.add("selected");
    const prefix = transOrderEnabled ? `<span class="trans-label">${transLabel(idx)}.</span> ` : "";
    li.innerHTML = `<span class="drag-handle" title="Dra för att ordna om">⋮⋮</span><span class="trans-name">${prefix}${esc(tr.name)}</span><span class="trans-del" title="Ta bort">✕</span>`;

    // Only allow HTML5 drag when initiated from the drag handle
    const handle = li.querySelector(".drag-handle");
    handle.addEventListener("mousedown", () => { li.draggable = true; });
    // --- HTML5 drag-and-drop for reordering ---
    li.addEventListener("dragstart", e => {
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", tr.id);
      li.classList.add("dragging");
    });
    li.addEventListener("dragend", () => {
      li.draggable = false;
      li.classList.remove("dragging");
      ul.querySelectorAll("li.drag-over-above, li.drag-over-below").forEach(el => {
        el.classList.remove("drag-over-above", "drag-over-below");
      });
    });
    li.addEventListener("dragover", e => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      // Determine if cursor is in top or bottom half
      const rect = li.getBoundingClientRect();
      const midY = rect.top + rect.height / 2;
      if (e.clientY < midY) {
        li.classList.add("drag-over-above");
        li.classList.remove("drag-over-below");
      } else {
        li.classList.add("drag-over-below");
        li.classList.remove("drag-over-above");
      }
    });
    li.addEventListener("dragleave", () => {
      li.classList.remove("drag-over-above", "drag-over-below");
    });
    li.addEventListener("drop", e => {
      e.preventDefault();
      li.classList.remove("drag-over-above", "drag-over-below");
      const draggedTid = e.dataTransfer.getData("text/plain");
      if (!draggedTid || draggedTid === tr.id) return;
      // Determine insert position
      const rect = li.getBoundingClientRect();
      const midY = rect.top + rect.height / 2;
      const insertBefore = e.clientY < midY;
      _reorderTranscript(draggedTid, tr.id, insertBefore);
    });

    li.addEventListener("mousedown", e => {
      if (e.button !== 0 || e.target.classList.contains("trans-del") || e.target.classList.contains("drag-handle")) return;
      _dragSelecting = true;
      _dragMoved = false;
      // Start a fresh drag selection from this item (if not already selected and no modifier)
      if (!e.metaKey && !e.ctrlKey && !selectedTids.has(tr.id)) {
        selectedTids.clear();
        ul.querySelectorAll("li.selected").forEach(el => el.classList.remove("selected"));
        selectedTids.add(tr.id);
        li.classList.add("selected");
      }
    });
    li.addEventListener("click", e => {
      if (e.target.classList.contains("trans-del") || e.target.classList.contains("drag-handle")) return;
      if (_dragMoved) { _dragMoved = false; return; } // drag ended here — skip click
      if (e.metaKey || e.ctrlKey) {
        if (selectedTids.has(tr.id)) selectedTids.delete(tr.id);
        else selectedTids.add(tr.id);
        li.classList.toggle("selected", selectedTids.has(tr.id));
      } else {
        selectedTids.clear();
        loadTranscript(tr.id);
      }
    });
    li.querySelector(".trans-del").addEventListener("click", async e => {
      e.stopPropagation();
      if (!await appConfirm(t("confirm.del.transcript", { name: tr.name }))) return;
      const res = await DEL(`/api/transcripts/${tr.id}`);
      if (res.ok) { project = res.project; renderTranscriptList(); if (currentTid === tr.id) clearEditor(); }
    });
    ul.appendChild(li);
  }

  // Sorted categories first, uncategorized last
  Object.keys(groups).sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }))
    .forEach(cat => { appendHeader(cat); groups[cat].forEach(appendItem); });

  if (hasCategories && uncategorized.length > 0) appendHeader(t("trans.uncategorized"));
  uncategorized.forEach(appendItem);
}

async function _reorderTranscript(draggedTid, targetTid, insertBefore) {
  // Reorder the local transcripts array, then persist via API
  const list = project.transcripts;
  const dragIdx = list.findIndex(t => t.id === draggedTid);
  if (dragIdx === -1) return;
  // Remove dragged item
  const [item] = list.splice(dragIdx, 1);
  // Find new target index (after removal)
  let targetIdx = list.findIndex(t => t.id === targetTid);
  if (targetIdx === -1) { list.push(item); } else {
    if (!insertBefore) targetIdx += 1;
    list.splice(targetIdx, 0, item);
  }
  project.transcripts = list;
  renderTranscriptList();
  // Persist to backend
  const order = list.map(t => t.id);
  await PATCH("/api/transcripts/reorder", { order });
}

function clearEditor() {
  currentTid = null; currentText = ""; annotations = [];
  formattingSpans = [];
  segments = []; segmentCharMap = [];
  undoStack = []; redoStack = [];
  if (_textEditMode) exitTextEditMode();
  document.getElementById("editor-placeholder").classList.remove("hidden");
  document.getElementById("editor-content").classList.add("hidden");
  document.getElementById("audio-player-wrap")?.classList.add("hidden");
  document.getElementById("transcript-text")?.classList.remove("has-audio");
  const toolbar = document.getElementById("editor-toolbar");
  if (toolbar) toolbar.classList.add("hidden");
}

// ---- Add transcript modal ----
function resetTranscriptModal() {
  document.getElementById("trans-error").textContent = "";
  document.getElementById("trans-progress-wrap")?.classList.add("hidden");
  const bar = document.getElementById("trans-progress-bar-inner");
  if (bar) bar.style.width = "0%";
  document.getElementById("trans-name").value = "";
  document.getElementById("trans-file").value = "";
  document.getElementById("file-selected-list").innerHTML = "";
  document.getElementById("file-drop-text").textContent = "Klicka för att välja fil, eller dra hit";
  document.getElementById("btn-trans-confirm").disabled = false;
  document.getElementById("audio-options")?.classList.add("hidden");
  document.getElementById("scribbler-options")?.classList.add("hidden");
  const scribblerPw = document.getElementById("scribbler-password");
  if (scribblerPw) scribblerPw.value = "";
  document.getElementById("diar-options")?.classList.add("hidden");
  const diarCb = document.getElementById("diar-enabled");
  if (diarCb) diarCb.checked = false;
  // Reset language choice to default and hide Whisper model size
  const lc = document.getElementById("language-choice");
  if (lc) lc.value = "autodetect";
  const mw = document.getElementById("whisper-model-wrap");
  if (mw) mw.style.display = "none";
}

document.getElementById("btn-add-transcript").addEventListener("click", () => {
  _transcriptAborted = false;
  resetTranscriptModal();
  document.getElementById("modal-transcript").classList.remove("hidden");
});
document.getElementById("btn-trans-cancel").addEventListener("click", () => {
  const inProgress = document.getElementById("btn-trans-confirm").disabled;
  _transcriptAborted = true;
  _audioBatch = [];
  if (inProgress) {
    // Transcription running — stay in modal, reset to initial state
    document.getElementById("trans-progress-wrap")?.classList.add("hidden");
    document.getElementById("trans-error").textContent = "";
    document.getElementById("btn-trans-confirm").disabled = false;
  } else {
    document.getElementById("modal-transcript").classList.add("hidden");
  }
});

// Diarization checkbox toggle
document.getElementById("diar-enabled")?.addEventListener("change", async function () {
  const opts = document.getElementById("diar-options");
  if (this.checked) {
    // Check if HF token is saved
    const cfg = await GET("/api/config/hf-token");
    if (!cfg.has_token) {
      this.checked = false;
      openHfTokenModal(() => { this.checked = true; opts.classList.remove("hidden"); updateDiarVoiceStatus(); });
      return;
    }
    opts.classList.remove("hidden");
    updateDiarVoiceStatus();
    _updateModelWrapVisibility();
  } else {
    opts.classList.add("hidden");
  }
});

// Slider live-update display values
document.getElementById("diar-seg-thr")?.addEventListener("input", function () {
  document.getElementById("diar-seg-val").textContent = parseFloat(this.value).toFixed(2);
});
document.getElementById("diar-clu-thr")?.addEventListener("input", function () {
  document.getElementById("diar-clu-val").textContent = parseFloat(this.value).toFixed(2);
});

// File picker — show selected filenames
document.getElementById("trans-file").addEventListener("change", function () {
  updateFileList(this.files);
});

// Drag-and-drop
const dropZone = document.getElementById("file-drop-zone");
dropZone.addEventListener("dragover", e => { e.preventDefault(); dropZone.classList.add("dragover"); });
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("dragover"));
dropZone.addEventListener("drop", e => {
  e.preventDefault();
  dropZone.classList.remove("dragover");
  document.getElementById("trans-file").files = e.dataTransfer.files;
  updateFileList(e.dataTransfer.files);
});

function updateFileList(files) {
  const list = document.getElementById("file-selected-list");
  const dropText = document.getElementById("file-drop-text");
  list.innerHTML = "";
  if (!files || files.length === 0) {
    dropText.textContent = "Klicka för att välja fil, eller dra hit";
    document.getElementById("audio-options").classList.add("hidden");
    document.getElementById("scribbler-options").classList.add("hidden");
    document.getElementById("image-options")?.classList.add("hidden");
    document.getElementById("zip-notice")?.classList.add("hidden");
    return;
  }
  dropText.textContent = "";
  const anyAudio = Array.from(files).some(f => isAudioFile(f.name));
  const anyScribbler = Array.from(files).some(f => isScribblerFile(f.name));
  const anyImage = Array.from(files).some(f => isImageFile(f.name));
  const anyZip = Array.from(files).some(f => /\.zip$/i.test(f.name));
  document.getElementById("audio-options").classList.toggle("hidden", !anyAudio);
  document.getElementById("scribbler-options").classList.toggle("hidden", !anyScribbler);
  document.getElementById("image-options")?.classList.toggle("hidden", !anyImage);
  document.getElementById("zip-notice")?.classList.toggle("hidden", !anyZip);
  if (anyAudio) _updateModelWrapVisibility();

  Array.from(files).forEach(f => {
    const li = document.createElement("li");
    const icon = isAudioFile(f.name) ? "🎙" : isImageFile(f.name) ? "🖼" : isScribblerFile(f.name) ? "🔐" : /\.zip$/i.test(f.name) ? "📦" : "📄";
    li.innerHTML = `<span class="file-icon">${icon}</span><span>${esc(f.name)}</span>`;
    list.appendChild(li);
  });
  // Pre-fill name if single file
  if (files.length === 1) {
    const nameInput = document.getElementById("trans-name");
    if (!nameInput.value) nameInput.value = files[0].name.replace(/\.[^.]+$/, "");
  }
}

function isAudioFile(name) {
  return /\.(mp3|wav|m4a|mp4|ogg|flac|webm)$/i.test(name);
}
function isImageFile(name) {
  return /\.(jpe?g|png|bmp|tiff?|webp|heic|heif)$/i.test(name);
}
function isScribblerFile(name) {
  return /\.(scribbler|nsenc)$/i.test(name);
}

// --- Progress bar helper ---
const STAGE_LABELS = {
  "pending":      "Förbereder…",
  "loading_model":"Laddar modell…",
  "diarizing":    "Identifierar talare…",
  "diarizing_cpu":"Identifierar talare (CPU — kan ta lång tid)…",
  "transcribing": "Whisper transkriberar…",
  "ocr":          "Tolkar text i bild…",
  "saving":       "Sparar…",
  "done":         "Klart!",
};
function updateProgressBar(progress, stage, extra) {
  const wrap = document.getElementById("trans-progress-wrap");
  wrap.classList.remove("hidden");
  document.getElementById("trans-progress-bar-inner").style.width = `${Math.round(progress * 100)}%`;
  document.getElementById("trans-progress-pct").textContent = `${Math.round(progress * 100)}%`;
  // Show CPU warning when diarizing on CPU
  let displayStage = stage;
  if (stage === "diarizing" && extra && extra.diar_device === "cpu") {
    displayStage = "diarizing_cpu";
  }
  document.getElementById("trans-progress-stage").textContent =
    STAGE_LABELS[displayStage] || stage || "Arbetar…";
}

// --- Job polling ---
function pollJob(jobId, onDone, onError) {
  GET(`/api/jobs/${jobId}`).then(res => {
    updateProgressBar(res.progress || 0, res.stage || "", {diar_device: res.diar_device});
    if (res.status === "done") { onDone(res); return; }
    if (res.status === "error") { onError(res.error || "Okänt fel"); return; }
    setTimeout(() => pollJob(jobId, onDone, onError), 2000);
  }).catch(err => onError(String(err)));
}

function pollJobAsync(jobId) {
  return new Promise((resolve, reject) => pollJob(jobId, resolve, reject));
}

document.getElementById("btn-trans-confirm").addEventListener("click", async () => {
  _transcriptAborted = false;
  const fileInput  = document.getElementById("trans-file");
  const name       = document.getElementById("trans-name").value.trim();
  const langChoice = document.getElementById("language-choice")?.value || "autodetect";
  const model      = document.getElementById("trans-model")?.value || "medium";
  const diarEnabled = document.getElementById("diar-enabled").checked;
  const errEl = document.getElementById("trans-error");
  errEl.textContent = "";

  const files = fileInput.files;
  if (!files || files.length === 0) { errEl.textContent = t("error.no.file"); return; }

  // Build diarization settings (only relevant for audio)
  const autoIdentify = document.getElementById("diar-auto-identify")?.checked && !!_voiceProfileMeta;
  const diarSettings = {
    diarization:            diarEnabled ? "1" : "0",
    num_speakers:           document.getElementById("diar-num-speakers").value.trim(),
    min_speakers:           document.getElementById("diar-min-speakers").value.trim(),
    max_speakers:           document.getElementById("diar-max-speakers").value.trim(),
    segmentation_threshold: document.getElementById("diar-seg-thr").value,
    clustering_threshold:   document.getElementById("diar-clu-thr").value,
    auto_identify:          autoIdentify ? "1" : "0",
    word_timestamps:        document.getElementById("diar-word-timestamps")?.checked ? "1" : "0",
  };

  document.getElementById("btn-trans-confirm").disabled = true;

  const imageFiles = Array.from(files).filter(f => isImageFile(f.name));
  const audioFiles = Array.from(files).filter(f => isAudioFile(f.name));
  let imageIdx = 0;
  let audioIdx = 0;

  // Upload files one by one
  for (const file of files) {
    // Visa "laddar upp"-status innan fetch (syns vid stora filer)
    if (isImageFile(file.name)) {
      imageIdx++;
      const uploadLabel = imageFiles.length > 1
        ? `Bild ${imageIdx}/${imageFiles.length} — Laddar upp…`
        : "Laddar upp…";
      updateProgressBar(0, "");
      document.getElementById("trans-progress-stage").textContent = uploadLabel;
      document.getElementById("trans-progress-pct").textContent = "0%";
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("name", files.length === 1 ? name : "");
    formData.append("language_choice", langChoice);
    formData.append("model", model);

    if (isAudioFile(file.name)) {
      // Append diarization params
      Object.entries(diarSettings).forEach(([k, v]) => { if (v) formData.append(k, v); });
    }
    if (isImageFile(file.name)) {
      const doOcr = document.getElementById("image-ocr")?.checked !== false;
      formData.append("run_ocr", doOcr ? "1" : "0");
    }
    if (isScribblerFile(file.name)) {
      const pw = document.getElementById("scribbler-password")?.value || "";
      if (!pw) { errEl.textContent = t("error.scribbler.no_password") || "Ange lösenord för .scribbler-filen."; document.getElementById("btn-trans-confirm").disabled = false; return; }
      formData.append("scribbler_password", pw);
    }

    const res = await fetch("/api/transcripts/upload", { method: "POST", body: formData });
    const data = await res.json();

    if (data.error) {
      errEl.textContent = data.error;
      document.getElementById("btn-trans-confirm").disabled = false;
      return;
    }

    if (data.job_id) {
      if (!isImageFile(file.name)) {
        updateProgressBar(0, "pending");
      }
      if (isAudioFile(file.name)) {
        // Audio — vänta sekventiellt på transkribering, samla resultatet i
        // _audioBatch så att talarnamn kan ges för alla filer SAMTIDIGT efter
        // hela uppladdningen är klar (möjliggör obevakad körning över natten).
        audioIdx++;
        const _audN = audioIdx;
        const prefix = audioFiles.length > 1 ? `Fil ${_audN}/${audioFiles.length} — ` : "";
        try {
          const jobRes = await new Promise((resolve, reject) => {
            function poll() {
              if (_transcriptAborted) { reject("aborted"); return; }
              GET(`/api/jobs/${data.job_id}`).then(res => {
                if (_transcriptAborted) { reject("aborted"); return; }
                const pct = Math.round((res.progress || 0) * 100);
                const stageLabel = STAGE_LABELS[res.stage] || res.stage || "Arbetar…";
                updateProgressBar(res.progress || 0, "");
                document.getElementById("trans-progress-stage").textContent = prefix + stageLabel;
                document.getElementById("trans-progress-pct").textContent = `${pct}%`;
                if (res.status === "done")  { resolve(res); return; }
                if (res.status === "error") { reject(res.error || "Okänt fel"); return; }
                setTimeout(poll, 2000);
              }).catch(err => reject(String(err)));
            }
            poll();
          });

          // Stash for the batch dialog — do NOT open speaker dialog yet
          _audioBatch.push({
            jobId:          data.job_id,
            name:           name || file.name.replace(/\.[^.]+$/, ""),
            originalFile:   file.name,
            speakers_found: jobRes.speakers_found || [],
            voice_matches:  jobRes.voice_matches || {},
          });
          continue;
        } catch (errMsg) {
          if (errMsg === "aborted") return;
          errEl.textContent = errMsg;
          document.getElementById("btn-trans-confirm").disabled = false;
          document.getElementById("trans-progress-wrap")?.classList.add("hidden");
          return;
        }
      }
      // Bild-OCR — vänta sekventiellt så att nästa fil kan startas efteråt
      try {
        const _imgN = imageIdx; // capture current index for closure
        const prefix = imageFiles.length > 1 ? `Bild ${_imgN}/${imageFiles.length} — ` : "";
        const jobRes = await new Promise((resolve, reject) => {
          function poll() {
            GET(`/api/jobs/${data.job_id}`).then(res => {
              const pct = Math.round((res.progress || 0) * 100);
              const stageLabel = STAGE_LABELS[res.stage] || res.stage || "Arbetar…";
              updateProgressBar(res.progress || 0, "");
              document.getElementById("trans-progress-stage").textContent = prefix + stageLabel;
              document.getElementById("trans-progress-pct").textContent = `${pct}%`;
              if (res.status === "done") { resolve(res); return; }
              if (res.status === "error") { reject(res.error || "Okänt fel"); return; }
              setTimeout(poll, 2000);
            }).catch(err => reject(String(err)));
          }
          poll();
        });
        if (jobRes.project) project = jobRes.project;
        renderTranscriptList();
      } catch (errMsg) {
        errEl.textContent = errMsg;
        document.getElementById("btn-trans-confirm").disabled = false;
        document.getElementById("trans-progress-wrap")?.classList.add("hidden");
        return;
      }
    }

    // Synchronous text/docx response (image/audio jobs hanteras ovan)
    if (data.project) project = data.project;
  }

  renderTranscriptList();
  document.getElementById("modal-transcript").classList.add("hidden");
  document.getElementById("btn-trans-confirm").disabled = false;

  // If we collected any audio jobs, open the batch speaker dialog now
  if (_audioBatch.length > 0) {
    openBatchSpeakerDialog();
  }
});

// ---------------------------------------------------------------------------
// HF Token modal
// ---------------------------------------------------------------------------
function openHfTokenModal(onSaved) {
  _hfTokenCallback = onSaved || null;
  document.getElementById("hf-token-status").textContent = "";
  document.getElementById("hf-token-input").value = "";
  document.getElementById("modal-hf-token").classList.remove("hidden");
}

document.getElementById("btn-hf-cancel")?.addEventListener("click", () => {
  document.getElementById("modal-hf-token").classList.add("hidden");
  _hfTokenCallback = null;
});

document.getElementById("btn-hf-save")?.addEventListener("click", async () => {
  const token = document.getElementById("hf-token-input").value.trim();
  const statusEl = document.getElementById("hf-token-status");
  if (!token) return;

  statusEl.textContent = "Verifierar…";
  statusEl.style.color = "var(--text-dim)";
  const res = await POST("/api/config/hf-token", { token });

  if (res.error) {
    statusEl.textContent = res.error;
    statusEl.style.color = "var(--error, #e55)";
    return;
  }

  statusEl.textContent = t("hf.saved");
  statusEl.style.color = "var(--ok, #4c4)";
  setTimeout(() => {
    document.getElementById("modal-hf-token").classList.add("hidden");
    if (_hfTokenCallback) { _hfTokenCallback(); _hfTokenCallback = null; }
  }, 800);
});

// ---------------------------------------------------------------------------
// Voice profile
// ---------------------------------------------------------------------------
async function loadVoiceProfileStatus() {
  const res = await GET("/api/voice-profile");
  _voiceProfileMeta = res.has_profile ? res : null;
  updateDiarVoiceStatus();
}

function updateDiarVoiceStatus() {
  // Röstprofil-funktionen dold tillsvidare — raden förblir dold.
  return;
}

function openVoiceProfileModal() {
  const modal = document.getElementById("modal-voice-profile");
  const statusBox = document.getElementById("voice-profile-status-box");
  const metaEl = document.getElementById("voice-profile-meta");
  const errEl = document.getElementById("voice-modal-error");
  const progress = document.getElementById("voice-extract-progress");
  errEl.textContent = "";
  progress.classList.add("hidden");
  document.getElementById("voice-file-input").value = "";

  if (_voiceProfileMeta) {
    const d = new Date(_voiceProfileMeta.created).toLocaleDateString();
    metaEl.textContent = `${_voiceProfileMeta.dim}-dim · ${d}`;
    statusBox.classList.remove("hidden");
  } else {
    statusBox.classList.add("hidden");
  }
  modal.classList.remove("hidden");
}

document.getElementById("btn-voice-profile")?.addEventListener("click", () => {
  document.getElementById("settings-popover")?.classList.add("hidden");
  openVoiceProfileModal();
});

document.getElementById("btn-voice-cancel")?.addEventListener("click", () => {
  document.getElementById("modal-voice-profile").classList.add("hidden");
});

document.getElementById("btn-voice-delete")?.addEventListener("click", async () => {
  if (!await appConfirm("Ta bort röstprofil?")) return;
  const res = await DEL("/api/voice-profile");
  if (res.ok) {
    _voiceProfileMeta = null;
    updateDiarVoiceStatus();
    document.getElementById("voice-profile-status-box").classList.add("hidden");
  }
});

document.getElementById("btn-voice-extract")?.addEventListener("click", async () => {
  const fileInput = document.getElementById("voice-file-input");
  const errEl = document.getElementById("voice-modal-error");
  const progress = document.getElementById("voice-extract-progress");

  if (!fileInput.files.length) { errEl.textContent = "Välj en ljudfil först."; return; }
  errEl.textContent = "";
  progress.classList.remove("hidden");
  document.getElementById("btn-voice-extract").disabled = true;

  const fd = new FormData();
  fd.append("file", fileInput.files[0]);

  try {
    const res = await fetch("/api/voice-profile/extract", { method: "POST", body: fd });
    const data = await res.json();
    if (data.error) {
      errEl.textContent = data.error;
    } else {
      _voiceProfileMeta = { has_profile: true, ...data };
      updateDiarVoiceStatus();
      const metaEl = document.getElementById("voice-profile-meta");
      const d = new Date(data.created).toLocaleDateString();
      metaEl.textContent = `${data.dim}-dim · ${d}`;
      document.getElementById("voice-profile-status-box").classList.remove("hidden");
    }
  } catch (e) {
    errEl.textContent = "Nätverksfel: " + e;
  } finally {
    progress.classList.add("hidden");
    document.getElementById("btn-voice-extract").disabled = false;
  }
});

// Auto-identify setting (project-level)
document.getElementById("setting-auto-identify")?.addEventListener("change", async function () {
  const res = await PATCH("/api/project/settings", { auto_identify: this.checked });
  if (res.ok) project = res.project;
});

// ---------------------------------------------------------------------------
// Speaker naming dialog
// ---------------------------------------------------------------------------
function openSpeakerNamingDialog(speakersFound, voiceMatches) {
  const rows = document.getElementById("speaker-name-rows");
  rows.innerHTML = "";
  document.getElementById("spk-error").textContent = "";
  voiceMatches = voiceMatches || {};

  if (!speakersFound || speakersFound.length === 0) {
    // No diarization — commit immediately with empty map
    commitTranscript({});
    return;
  }

  // Determine coder name for auto-fill
  const coderName = document.getElementById("coder-badge")?.textContent?.replace("Kodare: ", "").trim() || "";

  speakersFound.forEach(spkId => {
    const match = voiceMatches[spkId];
    const isAuto    = match && match.action === "auto";
    const isSuggest = match && match.action === "suggest";
    const pct       = match ? Math.round(match.similarity * 100) : 0;

    const row = document.createElement("div");
    row.className = "speaker-name-row";

    let badgeHtml = "";
    let prefill   = "";
    if (isAuto) {
      prefill   = coderName;
      badgeHtml = `<span class="spk-match-badge" title="${pct}% ${t("voice.match.auto")}">${pct}%</span>`;
    } else if (isSuggest) {
      badgeHtml = `<span class="spk-match-badge suggest" title="${pct}% ${t("voice.match.suggest")}">${pct}%</span>`;
    }

    row.innerHTML = `
      <span class="spk-id">${esc(spkId)}</span>
      ${badgeHtml}
      <span class="spk-arrow">→</span>
      <input type="text" class="spk-name-input" data-spk="${escAttr(spkId)}"
        placeholder="${esc(spkId)}" value="${escAttr(prefill)}" />`;
    rows.appendChild(row);
  });

  document.getElementById("modal-speaker-names").classList.remove("hidden");
  // Focus first empty input
  const first = rows.querySelector("input:not([value])") || rows.querySelector("input");
  if (first) first.focus();
}

document.getElementById("btn-spk-cancel")?.addEventListener("click", () => {
  document.getElementById("modal-speaker-names").classList.add("hidden");
  _pendingJobResult = null;
  // Signal the upload loop that the user aborted — abort the rest of the batch
  if (_audioCommitResolve) {
    const r = _audioCommitResolve;
    _audioCommitResolve = null;
    r(false);
  }
});

document.getElementById("btn-spk-confirm")?.addEventListener("click", async () => {
  const speakerMap = {};
  document.querySelectorAll(".spk-name-input").forEach(inp => {
    const spkId = inp.dataset.spk;
    const name  = inp.value.trim();
    if (name) speakerMap[spkId] = name;
  });
  await commitTranscript(speakerMap);
});

async function commitTranscript(speakerMap) {
  if (!_pendingJobResult) return;
  const { jobId, name } = _pendingJobResult;
  const errEl = document.getElementById("spk-error");
  errEl.textContent = "";

  const res = await POST(`/api/transcripts/commit/${jobId}`, { name, speakers: speakerMap });
  if (res.error) {
    // Don't resolve _audioCommitResolve — leave the dialog open so user can retry
    errEl.textContent = res.error;
    return;
  }

  project = res.project;
  _pendingJobResult = null;
  document.getElementById("modal-speaker-names").classList.add("hidden");
  renderTranscriptList();

  // Signal the upload loop that this audio file is committed — continue with the next
  if (_audioCommitResolve) {
    const r = _audioCommitResolve;
    _audioCommitResolve = null;
    r(true);
  }
}

// ---------------------------------------------------------------------------
// Batch speaker naming dialog (multi-file)
// ---------------------------------------------------------------------------
function openBatchSpeakerDialog() {
  const list = document.getElementById("batch-speaker-list");
  list.innerHTML = "";
  document.getElementById("batch-spk-error").textContent = "";
  document.getElementById("batch-spk-progress").classList.add("hidden");

  const coderName = document.getElementById("coder-badge")?.textContent?.replace("Kodare: ", "").trim() || "";

  _audioBatch.forEach((job, idx) => {
    const fileSection = document.createElement("div");
    fileSection.className = "batch-speaker-file";
    fileSection.dataset.batchIdx = String(idx);

    const header = document.createElement("div");
    header.className = "batch-speaker-file-header";
    header.innerHTML = `<span>${esc(job.name)}</span><span class="file-num">(${idx + 1}/${_audioBatch.length})</span>`;
    fileSection.appendChild(header);

    if (!job.speakers_found || job.speakers_found.length === 0) {
      const none = document.createElement("div");
      none.className = "no-speakers";
      none.textContent = t("batch.spk.none") || "Inga talare identifierade — sparas som transkript utan talarnamn.";
      fileSection.appendChild(none);
    } else {
      job.speakers_found.forEach(spkId => {
        const match     = (job.voice_matches || {})[spkId];
        const isAuto    = match && match.action === "auto";
        const isSuggest = match && match.action === "suggest";
        const pct       = match ? Math.round(match.similarity * 100) : 0;

        let badgeHtml = "";
        let prefill   = "";
        if (isAuto) {
          prefill   = coderName;
          badgeHtml = `<span class="spk-match-badge" title="${pct}% ${t("voice.match.auto")}">${pct}%</span>`;
        } else if (isSuggest) {
          badgeHtml = `<span class="spk-match-badge suggest" title="${pct}% ${t("voice.match.suggest")}">${pct}%</span>`;
        }

        const row = document.createElement("div");
        row.className = "speaker-name-row";
        row.innerHTML = `
          <span class="spk-id">${esc(spkId)}</span>
          ${badgeHtml}
          <span class="spk-arrow">→</span>
          <input type="text" class="batch-spk-input" data-batch-idx="${idx}" data-spk="${escAttr(spkId)}"
            placeholder="${esc(spkId)}" value="${escAttr(prefill)}" />`;
        fileSection.appendChild(row);
      });
    }

    list.appendChild(fileSection);
  });

  document.getElementById("modal-batch-speakers").classList.remove("hidden");
  // Focus first empty input
  const first = list.querySelector(".batch-spk-input:not([value])") || list.querySelector(".batch-spk-input");
  if (first) first.focus();
}

async function commitBatchSpeakers(speakerMaps) {
  // speakerMaps: array of {jobId, name, speakers: {SPEAKER_XX: "Name", ...}}
  const errEl = document.getElementById("batch-spk-error");
  const progEl = document.getElementById("batch-spk-progress");
  const curEl  = document.getElementById("batch-spk-cur");
  const totEl  = document.getElementById("batch-spk-total");
  errEl.textContent = "";
  totEl.textContent = String(speakerMaps.length);
  curEl.textContent = "0";
  progEl.classList.remove("hidden");

  // Disable buttons during commit
  document.getElementById("btn-batch-spk-save").disabled = true;
  document.getElementById("btn-batch-spk-skip").disabled = true;

  const failed = [];
  for (let i = 0; i < speakerMaps.length; i++) {
    curEl.textContent = String(i + 1);
    const { jobId, name, speakers } = speakerMaps[i];
    try {
      const res = await POST(`/api/transcripts/commit/${jobId}`, { name, speakers });
      if (res.error) {
        failed.push({ idx: i, name, error: res.error });
      } else {
        project = res.project;
      }
    } catch (e) {
      failed.push({ idx: i, name, error: String(e) });
    }
  }

  document.getElementById("btn-batch-spk-save").disabled = false;
  document.getElementById("btn-batch-spk-skip").disabled = false;

  if (failed.length > 0) {
    errEl.textContent = `${failed.length} fil(er) misslyckades: ${failed.map(f => f.name).join(", ")}. Försök igen för att retry:a.`;
    // Keep _audioBatch only with the failed entries so the user can retry
    _audioBatch = failed.map(f => _audioBatch[f.idx]);
    progEl.classList.add("hidden");
    return;
  }

  // All succeeded
  _audioBatch = [];
  document.getElementById("modal-batch-speakers").classList.add("hidden");
  renderTranscriptList();
}

document.getElementById("btn-batch-spk-save")?.addEventListener("click", async () => {
  // Collect speaker maps from inputs
  const maps = _audioBatch.map((job, idx) => {
    const speakers = {};
    document.querySelectorAll(`.batch-spk-input[data-batch-idx="${idx}"]`).forEach(inp => {
      const spkId = inp.dataset.spk;
      const name  = inp.value.trim();
      if (name) speakers[spkId] = name;
    });
    return { jobId: job.jobId, name: job.name, speakers };
  });
  await commitBatchSpeakers(maps);
});

document.getElementById("btn-batch-spk-skip")?.addEventListener("click", async () => {
  // Commit all with empty speaker maps (keep SPEAKER_XX names)
  const maps = _audioBatch.map(job => ({ jobId: job.jobId, name: job.name, speakers: {} }));
  await commitBatchSpeakers(maps);
});

// ---------------------------------------------------------------------------
// Load transcript + annotations
// ---------------------------------------------------------------------------
async function loadTranscript(tid) {
  currentTid = tid;
  formattingSpans = [];
  segments       = [];
  segmentCharMap = [];
  const transcript = project.transcripts.find(tr => tr.id === tid);

  // Fetch text + annotations (critical) — formatting is optional
  const [textRes, annRes] = await Promise.all([
    GET(`/api/transcripts/${tid}/text`),
    GET(`/api/transcripts/${tid}/annotations`),
  ]);
  currentText = textRes.text || "";
  annotations = annRes.annotations || [];

  // Audio player — show/hide + set source
  const audioWrap   = document.getElementById("audio-player-wrap");
  const audioPlayer = document.getElementById("audio-player");
  const modelBadge  = document.getElementById("audio-model-badge");
  if (transcript && transcript.source === "audio" && transcript.audio_file) {
    audioPlayer.src = `/api/transcripts/${tid}/audio`;
    modelBadge.textContent = transcript.model_label || transcript.whisper_model || "Whisper";
    audioWrap.classList.remove("hidden");
    // Load segments asynchronously for click-to-seek
    GET(`/api/transcripts/${tid}/segments`).then(res => {
      if (res.segments && res.segments.length) {
        segments       = res.segments;
        segmentCharMap = buildSegmentCharMap(segments);
        const txtEl = document.getElementById("transcript-text");
        txtEl.classList.add("has-audio");
        txtEl.title = t("play.here");
      }
    }).catch(() => {});
  } else {
    audioWrap.classList.add("hidden");
    audioPlayer.src = "";
    const txtEl = document.getElementById("transcript-text");
    txtEl.classList.remove("has-audio");
    txtEl.removeAttribute("title");
  }

  // Waveform — init if audio + use_waveform, destroy otherwise
  _destroyWaveform();
  if (useWaveformEnabled && transcript && transcript.source === "audio" && transcript.audio_file) {
    _initWaveform(tid);
  }

  // Source image — reset fully on every transcript switch
  const sourceBtn   = document.getElementById("btn-source-img");
  const sourceSep   = document.getElementById("fmt-sep-source");
  const sourcePanel = document.getElementById("source-img-panel");
  const handleSrc   = document.getElementById("handle-source");
  const srcImg      = document.getElementById("source-img");
  const ocrSVG      = document.getElementById("ocr-box-overlay");
  sourcePanel.classList.add("hidden");
  handleSrc?.classList.add("hidden");
  srcImg.src = "";
  if (ocrSVG) { while (ocrSVG.firstChild) ocrSVG.removeChild(ocrSVG.firstChild); }
  _ocrBoxesVisible = false;
  document.getElementById("btn-ocr-boxes")?.classList.remove("active");

  const _hasSourceImg = transcript && transcript.source === "image" && transcript.source_file;
  const _hasPhotos = transcript && transcript.photos && transcript.photos.length > 0;
  if (_hasSourceImg || _hasPhotos) {
    sourceBtn.classList.remove("hidden");
    sourceSep?.classList.remove("hidden");
    // Restore per-transcript open/boxes state
    const imgState = _sourceImgState[tid];
    if (imgState && imgState.open) {
      _openSourcePanel(tid, transcript);
      _ocrBoxesVisible = imgState.boxesVisible || false;
      document.getElementById("btn-ocr-boxes")?.classList.toggle("active", _ocrBoxesVisible);
      if (_ocrBoxesVisible && _hasSourceImg) loadOcrBoxes(tid);
    }
  } else {
    sourceBtn.classList.add("hidden");
    sourceSep?.classList.add("hidden");
  }

  // Show editor
  document.getElementById("editor-placeholder").classList.add("hidden");
  document.getElementById("editor-content").classList.remove("hidden");
  document.getElementById("editor-title").textContent = transcript ? transcript.name : tid;
  updateAnnBadge();
  clearSearch(true);

  // Highlight active item in sidebar
  document.querySelectorAll("#transcript-list li").forEach(li => {
    li.classList.toggle("active", li.dataset.tid === tid);
  });

  // Show format toolbar
  const toolbar = document.getElementById("editor-toolbar");
  if (toolbar) toolbar.classList.remove("hidden");
  applyFontSettings();
  updateFmtBtnStates();

  renderTranscriptText();

  // Fetch formatting spans separately (non-critical — failure is silent)
  GET(`/api/transcripts/${tid}/formatting`).then(fmtRes => {
    formattingSpans = (fmtRes && fmtRes.spans) || [];
    if (formattingSpans.length) applyFormatSpans();
  }).catch(() => {});
}

function updateAnnBadge() {
  document.getElementById("ann-count-badge").textContent =
    `${annotations.length} kodning${annotations.length !== 1 ? "ar" : ""}`;
}

// ---------------------------------------------------------------------------
// Audio sync helpers
// ---------------------------------------------------------------------------
function buildSegmentCharMap(segs) {
  // Mirror the server-side text construction (core/transcribe.py, end of
  // transcribe_with_diarization):
  //   for seg in diar_segments:
  //     if seg.speaker == "—": line = seg.text          (inaudible — no prefix)
  //     else:                  line = f"[{seg.speaker}]: {seg.text}"
  //   text = "\n".join(lines)
  const nonEmpty = segs.filter(s => s.text);
  let pos = 0;
  return nonEmpty.map((seg) => {
    const line     = seg.speaker === "—" ? seg.text : `[${seg.speaker}]: ${seg.text}`;
    const charStart = pos;
    const charEnd   = pos + line.length;
    pos = charEnd + 1; // +1 for the \n separator
    return { charStart, charEnd, timeStart: seg.start, timeEnd: seg.end };
  });
}

function charOffsetToTime(charOffset) {
  for (const r of segmentCharMap) {
    if (charOffset >= r.charStart && charOffset <= r.charEnd) return r.timeStart;
  }
  // Fallback: nearest segment
  if (!segmentCharMap.length) return null;
  let best = segmentCharMap[0];
  let bestDist = Math.min(Math.abs(charOffset - best.charStart), Math.abs(charOffset - best.charEnd));
  for (const r of segmentCharMap) {
    const d = Math.min(Math.abs(charOffset - r.charStart), Math.abs(charOffset - r.charEnd));
    if (d < bestDist) { bestDist = d; best = r; }
  }
  return best.timeStart;
}

// ---------------------------------------------------------------------------
// Source image panel
// ---------------------------------------------------------------------------
function renderOcrBoxes(boxes) {
  const svg = document.getElementById("ocr-box-overlay");
  if (!svg) return;
  // Clear previous rects
  while (svg.firstChild) svg.removeChild(svg.firstChild);
  for (const b of boxes) {
    const rect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("x", b.x);
    rect.setAttribute("y", b.y);
    rect.setAttribute("width", b.w);
    rect.setAttribute("height", b.h);
    const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
    title.textContent = b.text;
    rect.appendChild(title);
    svg.appendChild(rect);
  }
}

function _openSourcePanel(tid, transcript) {
  const tr = transcript || project?.transcripts?.find(t => t.id === tid);
  const hasSourceImg = tr?.source === "image" && tr?.source_file;
  const photos = tr?.photos || [];

  const srcImgWrap = document.getElementById("source-img-wrap");
  const srcImg = document.getElementById("source-img");
  if (hasSourceImg) {
    srcImg.src = `/api/transcripts/${tid}/source-image`;
    srcImgWrap?.classList.remove("hidden");
  } else {
    srcImg.src = "";
    srcImgWrap?.classList.add("hidden");
  }

  const photosEl = document.getElementById("note-photos-container");
  if (photosEl) {
    photosEl.innerHTML = "";
    for (let n = 0; n < photos.length; n++) {
      const img = document.createElement("img");
      img.className = "note-photo";
      img.src = `/api/transcripts/${tid}/photo/${n}`;
      img.alt = `foto ${n + 1}`;
      photosEl.appendChild(img);
    }
    photosEl.classList.toggle("hidden", photos.length === 0);
  }

  const titleEl = document.getElementById("source-panel-title");
  if (titleEl) {
    titleEl.textContent = hasSourceImg && photos.length > 0 ? "Källbild & foton"
                        : photos.length > 0 ? "Foton" : "Källbild";
  }
  document.getElementById("btn-ocr-boxes")?.classList.toggle("hidden", !hasSourceImg);
  const ocrPhotosBtn = document.getElementById("btn-ocr-photos");
  if (ocrPhotosBtn) ocrPhotosBtn.style.display = photos.length > 0 ? "" : "none";
  document.getElementById("source-img-panel").classList.remove("hidden");
  document.getElementById("handle-source")?.classList.remove("hidden");
  const pinBtn = document.getElementById("btn-pin-mode");
  if (pinBtn) pinBtn.classList.toggle("hidden", !hasSourceImg);
  if (!hasSourceImg && pinModeEnabled) pinModeEnabled = false;
  _updatePinModeUi();
  if (hasSourceImg) renderPointPins();
}

// ---- Point annotations on source image -----------------------------------

function renderPointPins() {
  const overlay = document.getElementById("point-overlay");
  if (!overlay) return;
  overlay.innerHTML = "";
  const points = (annotations || []).filter(a => a.kind === "point");
  if (points.length === 0) return;

  // Number map: prefer codebook hierarchy numbers (1, 1.1, ...) when enabled,
  // otherwise fall back to insertion order per code.
  const flat = _buildNumberedFlat();
  const numByCode = {};
  flat.forEach(c => { if (c.number) numByCode[c.id] = c.number; });
  const seqByCode = {};

  points.forEach(p => {
    const code = (project?.codes || []).find(c => c.id === p.code_id);
    seqByCode[p.code_id] = (seqByCode[p.code_id] || 0) + 1;
    const label = (numberingEnabled && numByCode[p.code_id])
      ? numByCode[p.code_id]
      : String(seqByCode[p.code_id]);
    const pin = document.createElement("div");
    pin.className = "point-pin";
    pin.style.left = (p.x * 100) + "%";
    pin.style.top  = (p.y * 100) + "%";
    pin.style.background = code ? code.color : "#888";
    pin.textContent = label;
    pin.title = (code ? code.name : p.code_id) + (p.memo ? `\n${p.memo}` : "");
    pin.dataset.annId = p.id;
    _attachPinDragHandlers(pin, p);
    overlay.appendChild(pin);
  });
}

// Drag eller klick på en pin. Om muspekaren rör sig >4 px under mousedown
// tolkas det som drag och pinnen flyttas (PATCH av x/y vid mouseup).
// Annars öppnas detail-popupen vid pinnens position.
function _attachPinDragHandlers(pin, ann) {
  let dragging = false;
  let moved = false;
  let startX = 0, startY = 0;
  let overlayRect = null;

  pin.addEventListener("mousedown", (e) => {
    e.preventDefault();
    e.stopPropagation();
    dragging = true;
    moved = false;
    startX = e.clientX; startY = e.clientY;
    const overlay = document.getElementById("point-overlay");
    overlayRect = overlay.getBoundingClientRect();
    pin.style.zIndex = 20;

    function onMove(ev) {
      if (!dragging) return;
      if (!moved && Math.hypot(ev.clientX - startX, ev.clientY - startY) > 4) {
        moved = true;
        pin.classList.add("dragging");
      }
      if (moved) {
        const nx = Math.min(1, Math.max(0, (ev.clientX - overlayRect.left) / overlayRect.width));
        const ny = Math.min(1, Math.max(0, (ev.clientY - overlayRect.top) / overlayRect.height));
        pin.style.left = (nx * 100) + "%";
        pin.style.top  = (ny * 100) + "%";
        pin.dataset.x = nx; pin.dataset.y = ny;
      }
    }

    async function onUp(ev) {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
      dragging = false;
      pin.style.zIndex = "";
      pin.classList.remove("dragging");
      if (!moved) {
        // treat as click → open detail popup at pin location
        showAnnDetail(ann.id, { clientX: ev.clientX, clientY: ev.clientY });
        return;
      }
      const nx = parseFloat(pin.dataset.x);
      const ny = parseFloat(pin.dataset.y);
      const res = await PATCH(
        `/api/transcripts/${currentTid}/annotations/${ann.id}`,
        { x: nx, y: ny }
      );
      if (res.ok) {
        const a = annotations.find(x => x.id === ann.id);
        if (a) { a.x = nx; a.y = ny; }
      } else {
        // revert visual position on error
        renderPointPins();
      }
    }

    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  });
}

let pinModeEnabled = false;

function _updatePinModeUi() {
  const btn = document.getElementById("btn-pin-mode");
  const img = document.getElementById("source-img");
  const hint = document.getElementById("source-img-hint");
  if (btn) btn.classList.toggle("active", pinModeEnabled);
  if (img) img.classList.toggle("pin-mode", pinModeEnabled);
  if (hint) hint.classList.toggle("hidden", !pinModeEnabled);
}

document.getElementById("btn-pin-mode")?.addEventListener("click", () => {
  pinModeEnabled = !pinModeEnabled;
  _updatePinModeUi();
});

document.getElementById("source-img")?.addEventListener("click", (e) => {
  if (!pinModeEnabled) return;
  if (!currentTid) return;
  const tr = project?.transcripts?.find(t => t.id === currentTid);
  if (!tr || tr.source !== "image") return;
  const img = e.currentTarget;
  const rect = img.getBoundingClientRect();
  const x = (e.clientX - rect.left) / rect.width;
  const y = (e.clientY - rect.top) / rect.height;
  if (x < 0 || x > 1 || y < 0 || y > 1) return;
  pendingSelection = null;
  pendingPoint = { x, y };
  showAnnPopup(e.clientX, e.clientY);
});

async function loadOcrBoxes(tid) {
  const res = await fetch(`/api/transcripts/${tid}/ocr-boxes`);
  if (!res.ok) return;
  const data = await res.json();
  renderOcrBoxes(data.boxes || []);
  const svg = document.getElementById("ocr-box-overlay");
  if (svg && _ocrBoxesVisible) svg.classList.remove("hidden");
}

document.getElementById("btn-source-img")?.addEventListener("click", () => {
  if (!currentTid) return;
  const tr = project?.transcripts?.find(t => t.id === currentTid);
  _openSourcePanel(currentTid, tr);
  if (tr?.source === "image") loadOcrBoxes(currentTid);
  _sourceImgState[currentTid] = { open: true, boxesVisible: _ocrBoxesVisible };
});
document.getElementById("btn-close-source")?.addEventListener("click", () => {
  document.getElementById("source-img-panel").classList.add("hidden");
  document.getElementById("handle-source")?.classList.add("hidden");
  document.getElementById("source-img").src = "";
  const svg = document.getElementById("ocr-box-overlay");
  if (svg) { while (svg.firstChild) svg.removeChild(svg.firstChild); }
  const pc = document.getElementById("note-photos-container");
  if (pc) { pc.innerHTML = ""; pc.classList.add("hidden"); }
  if (currentTid) _sourceImgState[currentTid] = { open: false, boxesVisible: _ocrBoxesVisible };
});
document.getElementById("btn-ocr-photos")?.addEventListener("click", async () => {
  if (!currentTid) return;
  const btn = document.getElementById("btn-ocr-photos");
  btn.disabled = true;
  btn.title = "Kör OCR…";
  try {
    const res = await POST(`/api/transcripts/${currentTid}/ocr-photos`, {});
    if (res.error) { await appAlert(res.error); btn.disabled = false; btn.title = "Extrahera text från foton (OCR)"; return; }
    await new Promise((resolve, reject) => {
      function poll() {
        GET(`/api/jobs/${res.job_id}`).then(j => {
          if (j.status === "done") { resolve(j.result); return; }
          if (j.status === "error") { reject(j.error || "Okänt fel"); return; }
          setTimeout(poll, 1500);
        }).catch(reject);
      }
      poll();
    });
    // Reload transcript text
    const txt = await GET(`/api/transcripts/${currentTid}/text`);
    if (txt.text !== undefined) {
      currentText = txt.text;
      renderTranscriptText();
    }
  } catch (e) {
    await appAlert("OCR misslyckades: " + e);
  } finally {
    btn.disabled = false;
    btn.title = "Extrahera text från foton (OCR)";
  }
});
document.getElementById("btn-ocr-boxes")?.addEventListener("click", () => {
  _ocrBoxesVisible = !_ocrBoxesVisible;
  const svg = document.getElementById("ocr-box-overlay");
  const btn = document.getElementById("btn-ocr-boxes");
  if (svg) svg.classList.toggle("hidden", !_ocrBoxesVisible);
  if (btn) btn.classList.toggle("active", _ocrBoxesVisible);
  if (currentTid) _sourceImgState[currentTid] = { open: true, boxesVisible: _ocrBoxesVisible };
});

// ---------------------------------------------------------------------------
// Text edit mode
// ---------------------------------------------------------------------------
function enterTextEditMode() {
  if (!currentTid) return;
  _textEditMode = true;
  const area = document.getElementById("text-edit-area");
  area.value = currentText;
  document.getElementById("transcript-text").classList.add("hidden");
  document.getElementById("text-edit-wrap").classList.remove("hidden");
  document.getElementById("btn-edit-text").classList.add("active");
  area.focus();
}

function exitTextEditMode() {
  _textEditMode = false;
  document.getElementById("text-edit-wrap").classList.add("hidden");
  document.getElementById("transcript-text").classList.remove("hidden");
  document.getElementById("btn-edit-text").classList.remove("active");
}

document.getElementById("btn-edit-text")?.addEventListener("click", () => {
  if (_textEditMode) exitTextEditMode();
  else enterTextEditMode();
});

document.getElementById("btn-text-cancel")?.addEventListener("click", exitTextEditMode);

document.getElementById("btn-text-save")?.addEventListener("click", async () => {
  if (!currentTid) return;
  const newText = document.getElementById("text-edit-area").value;
  if (annotations.length > 0) {
    const ok = await appConfirm("Det finns " + annotations.length + " kodning(ar) på detta transkript. Om du ändrar texten kan deras positioner bli felaktiga. Fortsätta ändå?");
    if (!ok) return;
  }
  const res = await PATCH(`/api/transcripts/${currentTid}/text`, { text: newText });
  if (res.error) { await appAlert(res.error); return; }
  currentText = newText;
  exitTextEditMode();
  // Re-render with updated text (annotations stay but may be misaligned — user was warned)
  renderTranscriptText();
});

// Rename transcript
// ---------------------------------------------------------------------------
(function setupRenameTranscript() {
  const btn = document.getElementById("btn-rename-transcript");
  if (!btn) return;

  btn.addEventListener("click", () => {
    if (!currentTid) return;
    const titleEl = document.getElementById("editor-title");
    const currentName = titleEl.textContent;

    // Replace span with input
    const input = document.createElement("input");
    input.id = "editor-title-input";
    input.type = "text";
    input.value = currentName;
    titleEl.replaceWith(input);
    input.focus();
    input.select();

    async function commitRename() {
      const newName = input.value.trim();
      // Restore span first
      const span = document.createElement("span");
      span.id = "editor-title";
      input.replaceWith(span);

      if (!newName || newName === currentName) {
        span.textContent = currentName;
        return;
      }

      const res = await PATCH(`/api/transcripts/${currentTid}/rename`, { name: newName });
      if (res.error) {
        span.textContent = currentName;
        await appAlert(res.error);
        return;
      }
      // Update in-memory project data
      const tr = (project.transcripts || []).find(t => t.id === currentTid);
      if (tr) tr.name = newName;
      span.textContent = newName;
      // Update sidebar list item
      const li = document.querySelector(`#transcript-list li[data-tid="${currentTid}"] .trans-name`);
      if (li) li.textContent = newName;
    }

    input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") { e.preventDefault(); commitRename(); }
      if (e.key === "Escape") {
        const span = document.createElement("span");
        span.id = "editor-title";
        span.textContent = currentName;
        input.replaceWith(span);
      }
    });
    input.addEventListener("blur", commitRename);
  });
})();

// ---------------------------------------------------------------------------
// Render transcript with highlights
// ---------------------------------------------------------------------------
function renderTranscriptText() {
  const container = document.getElementById("transcript-text");
  container.innerHTML = buildHighlightedHTML(currentText, annotations, project.codes);
  container.querySelectorAll(".annotation-span").forEach(span => {
    span.addEventListener("click", e => {
      e.stopPropagation();
      const allIds = (span.dataset.annIds || span.dataset.annId).split(",").filter(Boolean);
      if (allIds.length <= 1) {
        showAnnDetail(allIds[0] || span.dataset.annId);
      } else {
        // Multiple overlapping annotations — let user pick which one
        _showAnnPicker(allIds, { clientX: e.clientX, clientY: e.clientY });
      }
    });
  });
  // Post-render: font, search highlights, formatting (each guarded)
  try { applyFontSettings(); } catch(e) {}
  try { applySearchHighlightsIfActive(); } catch(e) {}
  try { applyFormatSpans(); } catch(e) {}
}

function buildHighlightedHTML(text, anns, codes) {
  if (!anns.length) return esc(text);

  const codeMap = {};
  (codes || []).forEach(c => codeMap[c.id] = c);

  // Collect all boundary points so overlapping annotations each get their own segment
  const pts = new Set([0, text.length]);
  for (const a of anns) {
    const s = Math.max(0, a.start);
    const e = Math.min(text.length, a.end);
    if (s < e) { pts.add(s); pts.add(e); }
  }
  const boundaries = [...pts].sort((a, b) => a - b);

  let result = "";
  for (let i = 0; i < boundaries.length - 1; i++) {
    const segS = boundaries[i];
    const segE = boundaries[i + 1];
    const seg  = text.slice(segS, segE);

    // All annotations fully covering this segment (sorted by start so primary is earliest)
    const covering = anns
      .filter(a => a.start <= segS && a.end >= segE)
      .sort((a, b) => a.start - b.start);

    if (!covering.length) {
      result += esc(seg);
      continue;
    }

    const primary = covering[0];
    const code0   = codeMap[primary.code_id];
    const color0  = code0 ? code0.color : "#888";
    const alpha   = Math.round(255 * 0.28).toString(16).padStart(2, "0");

    // Stacked underlines via box-shadow: each annotation gets its own 2px line, 3px apart
    const shadows = covering.map((a, idx) => {
      const c   = codeMap[a.code_id];
      const col = c ? c.color : "#888";
      return `0 ${2 + idx * 3}px 0 0 ${col}`;
    }).join(", ");

    const allIds = covering.map(a => a.id).join(",");
    const titles = covering.map(a => {
      const c = codeMap[a.code_id];
      return c ? c.name : a.code_id;
    }).join(", ");

    result += `<span class="annotation-span" data-ann-id="${escAttr(primary.id)}" data-ann-ids="${escAttr(allIds)}" style="background:${color0}${alpha}; box-shadow:${shadows};" title="${escAttr(titles)}">${esc(seg)}</span>`;
  }

  return result;
}

// ---------------------------------------------------------------------------
// Audio sync — click in transcript text to seek audio
// ---------------------------------------------------------------------------
document.getElementById("transcript-text").addEventListener("click", e => {
  if (!segmentCharMap.length) return;
  // Only seek on bare click (no text selected, not clicking an annotation)
  const sel = window.getSelection();
  if (sel && !sel.isCollapsed) return;
  if (e.target.classList.contains("annotation-span")) return;

  const container = document.getElementById("transcript-text");
  let charOffset = null;

  // caretRangeFromPoint (WebKit/Blink) or caretPositionFromPoint (Gecko)
  if (document.caretRangeFromPoint) {
    const r = document.caretRangeFromPoint(e.clientX, e.clientY);
    if (r) {
      const pre = document.createRange();
      pre.setStart(container, 0);
      pre.setEnd(r.startContainer, r.startOffset);
      charOffset = pre.toString().length;
    }
  } else if (document.caretPositionFromPoint) {
    const pos = document.caretPositionFromPoint(e.clientX, e.clientY);
    if (pos) {
      const pre = document.createRange();
      pre.setStart(container, 0);
      pre.setEnd(pos.offsetNode, pos.offset);
      charOffset = pre.toString().length;
    }
  }

  if (charOffset !== null) {
    const time = charOffsetToTime(charOffset);
    if (time !== null) {
      const player = document.getElementById("audio-player");
      // Seek to the clicked position. If the player is already playing it
      // continues from the new time; if paused it stays paused. This prevents
      // accidental playback while coding (annotating text).
      if (player) { player.currentTime = time; }
    }
  }
});

// ---------------------------------------------------------------------------
// Undo / redo
// ---------------------------------------------------------------------------
async function undo() {
  if (!undoStack.length || !currentTid) return;
  const action = undoStack[undoStack.length - 1];
  if (action.tid !== currentTid) return;
  undoStack.pop();

  if (action.type === "add") {
    const res = await DEL(`/api/transcripts/${action.tid}/annotations/${action.ann.id}`);
    if (res.ok) {
      annotations = annotations.filter(a => a.id !== action.ann.id);
      updateAnnBadge(); renderTranscriptText(); renderPointPins();
      pushRedo({ type: "add", tid: action.tid, ann: action.ann });
    } else {
      pushUndo(action);
    }
  } else if (action.type === "delete") {
    const res = await POST(`/api/transcripts/${action.tid}/annotations`, _annPostBody(action.ann));
    if (res.ok) {
      annotations.push(res.annotation);
      updateAnnBadge(); renderTranscriptText(); renderPointPins();
      pushRedo({ type: "delete", tid: action.tid, ann: res.annotation });
    } else {
      pushUndo(action);
    }
  }
}

function _annPostBody(a) {
  if (a.kind === "point") {
    return {
      kind: "point", code_id: a.code_id, x: a.x, y: a.y,
      memo: a.memo || "", weight: a.weight ?? 50, anchor: !!a.anchor,
    };
  }
  return {
    code_id: a.code_id, start: a.start, end: a.end, text: a.text,
    memo: a.memo || "", weight: a.weight ?? 50, anchor: !!a.anchor,
  };
}

async function redo() {
  if (!redoStack.length || !currentTid) return;
  const action = redoStack[redoStack.length - 1];
  if (action.tid !== currentTid) return;
  redoStack.pop();

  if (action.type === "add") {
    // Re-add annotation
    const res = await POST(`/api/transcripts/${action.tid}/annotations`, _annPostBody(action.ann));
    if (res.ok) {
      annotations.push(res.annotation);
      updateAnnBadge(); renderTranscriptText(); renderPointPins();
      pushUndo({ type: "add", tid: action.tid, ann: res.annotation });
    } else {
      pushRedo(action);
    }
  } else if (action.type === "delete") {
    // Re-delete annotation
    const res = await DEL(`/api/transcripts/${action.tid}/annotations/${action.ann.id}`);
    if (res.ok) {
      annotations = annotations.filter(a => a.id !== action.ann.id);
      updateAnnBadge(); renderTranscriptText(); renderPointPins();
      pushUndo({ type: "delete", tid: action.tid, ann: action.ann });
    } else {
      pushRedo(action);
    }
  }
}

// ---------------------------------------------------------------------------
// Text selection → annotation popup
// ---------------------------------------------------------------------------
document.getElementById("transcript-text").addEventListener("mouseup", e => {
  const sel = window.getSelection();
  if (!sel || sel.isCollapsed) return;
  const text = sel.toString();
  if (!text.trim()) return;

  // Calculate character offsets
  const container = document.getElementById("transcript-text");
  const range = sel.getRangeAt(0);
  const preRange = document.createRange();
  preRange.setStart(container, 0);
  preRange.setEnd(range.startContainer, range.startOffset);
  const start = preRange.toString().length;
  const end = start + text.length;

  pendingSelection = { start, end, text };
  // Save the selection range so it survives focus moving to the popup
  _savedSelRange = range.cloneRange();
  const selRect = range.getBoundingClientRect();
  showAnnPopup(selRect.left, selRect.bottom);
});

document.addEventListener("mousedown", e => {
  if (!document.getElementById("ann-popup").contains(e.target) &&
      !document.getElementById("ann-detail").contains(e.target)) {
    // Close popup WITHOUT calling removeAllRanges() — calling it during mousedown
    // prevents the browser from tracking the drag-selection that follows on the
    // same mousedown, so subsequent annotation selections would always be empty.
    document.getElementById("ann-popup").classList.add("hidden");
    pendingSelection = null;
    _savedSelRange = null;
    hideAnnDetail();
  }
});

function showAnnPopup(x, y) {
  const popup = document.getElementById("ann-popup");
  popup.classList.remove("hidden");
  document.getElementById("ann-memo").value = "";
  // Weight row
  const weightRow = document.getElementById("ann-weight-row");
  if (weightRow) weightRow.classList.toggle("hidden", !useWeightEnabled);
  const weightInput = document.getElementById("ann-weight");
  if (weightInput) { weightInput.value = 50; document.getElementById("ann-weight-val").textContent = "50"; }
  // Anchor (key passage) checkbox — reset on each new annotation
  const anchorCb = document.getElementById("ann-anchor");
  if (anchorCb) anchorCb.checked = false;
  renderAnnCodeList();
  positionPopup(popup, x, y);
}

// Prevent clicks inside the annotation popup from collapsing the text selection.
// For non-input elements (code list items, buttons, labels, etc.) we call
// preventDefault on mousedown so the browser doesn't move focus and collapse
// the selection.  Input/textarea elements are excluded so typing still works;
// for those we restore the saved selection range via a focus handler.
document.getElementById("ann-popup").addEventListener("mousedown", e => {
  const tag = e.target.tagName;
  if (tag !== "INPUT" && tag !== "TEXTAREA") {
    e.preventDefault();
  }
});

// When an input inside the popup gains focus, restore the saved transcript
// selection so the highlight remains visible.
document.getElementById("ann-popup").addEventListener("focusin", () => {
  if (_savedSelRange) {
    const sel = window.getSelection();
    if (sel.rangeCount === 0 || sel.isCollapsed) {
      sel.removeAllRanges();
      sel.addRange(_savedSelRange);
    }
  }
});

function hideAnnPopup() {
  document.getElementById("ann-popup").classList.add("hidden");
  pendingSelection = null;
  pendingPoint = null;
  _annEditId = null;
  _savedSelRange = null;
  // Only clear the visual selection on explicit close (Cancel / Escape / Confirm),
  // not when called from the mousedown backdrop handler above.
  window.getSelection()?.removeAllRanges();
}

function renderAnnCodeList() {
  setupAnnSearch();
}

document.getElementById("btn-ann-confirm").addEventListener("click", async () => {
  const selected = document.querySelector(".ann-code-option.selected");
  if (!selected) { await appAlert(t("alert.pick.code")); return; }

  // Edit-mode: change the code on an existing annotation (optimistic UI)
  if (_annEditId) {
    const editId = _annEditId;
    const newCodeId = selected.dataset.codeId;
    _annEditId = null;

    // Optimistic: update local state and re-render immediately
    const ann = annotations.find(a => a.id === editId);
    const prevCodeId = ann ? ann.code_id : null;
    if (ann) ann.code_id = newCodeId;
    if (ann && ann.kind === "point") renderPointPins();
    else renderTranscriptText();
    updateAnnBadge();
    _refreshCodebookManagerIfOpen();
    hideAnnPopup();
    _annChangeCounter++;

    // Persist in background; rollback on failure
    PATCH(
      `/api/transcripts/${currentTid}/annotations/${editId}`,
      { code_id: newCodeId }
    ).then(res => {
      if (!res.ok) {
        // Rollback optimistic update
        const rollbackAnn = annotations.find(a => a.id === editId);
        if (rollbackAnn && prevCodeId !== null) {
          rollbackAnn.code_id = prevCodeId;
          if (rollbackAnn.kind === "point") renderPointPins();
          else renderTranscriptText();
          updateAnnBadge();
          _refreshCodebookManagerIfOpen();
        }
        appAlert(`Kunde inte byta kod: ${res.error || "okänt fel"}`);
      }
    });
    return;
  }

  if (!pendingSelection && !pendingPoint) return;
  const memo   = document.getElementById("ann-memo").value;
  const weight = useWeightEnabled ? parseInt(document.getElementById("ann-weight")?.value || "50", 10) : 50;
  const anchor = !!(document.getElementById("ann-anchor")?.checked);

  let body;
  if (pendingPoint) {
    body = {
      kind: "point",
      code_id: selected.dataset.codeId,
      x: pendingPoint.x, y: pendingPoint.y,
      memo, weight, anchor,
    };
  } else {
    body = {
      code_id: selected.dataset.codeId,
      start: pendingSelection.start,
      end:   pendingSelection.end,
      text:  pendingSelection.text,
      memo, weight, anchor,
    };
  }

  const res = await POST(`/api/transcripts/${currentTid}/annotations`, body);
  if (res.ok) {
    annotations.push(res.annotation);
    updateAnnBadge();
    if (res.annotation.kind === "point") {
      renderPointPins();
    } else {
      renderTranscriptText();
    }
    pushUndo({ type: "add", tid: currentTid, ann: res.annotation });
    redoStack = [];
  } else {
    await appAlert(`Kunde inte spara kodning: ${res.error || "okänt fel"}`);
  }
  hideAnnPopup();
});

document.getElementById("btn-ann-cancel").addEventListener("click", hideAnnPopup);

// ---------------------------------------------------------------------------
// Annotation picker (overlapping annotations)
// ---------------------------------------------------------------------------
function _showAnnPicker(annIds, pos) {
  // Remove any existing picker
  document.getElementById("ann-picker")?.remove();

  const picker = document.createElement("div");
  picker.id = "ann-picker";
  picker.style.cssText = `
    position: fixed; z-index: 9999; background: var(--bg2); border: 1px solid var(--border);
    border-radius: var(--radius); box-shadow: 0 4px 12px rgba(0,0,0,0.3); padding: 4px 0;
    min-width: 180px; max-width: 300px;
  `;

  const codeMap = {};
  (project.codes || []).forEach(c => codeMap[c.id] = c);

  for (const annId of annIds) {
    const ann = annotations.find(a => a.id === annId);
    if (!ann) continue;
    const code = codeMap[ann.code_id];
    const item = document.createElement("div");
    item.style.cssText = `
      padding: 6px 12px; cursor: pointer; display: flex; align-items: center; gap: 8px;
      font-size: 13px; color: var(--text);
    `;
    item.addEventListener("mouseenter", () => item.style.background = "var(--bg3)");
    item.addEventListener("mouseleave", () => item.style.background = "transparent");

    const dot = document.createElement("span");
    dot.style.cssText = `width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; background: ${code ? code.color : "#888"}`;
    item.appendChild(dot);

    const label = document.createElement("span");
    label.textContent = code ? buildPath(project.codes, ann.code_id) : ann.code_id;
    label.style.cssText = "overflow: hidden; text-overflow: ellipsis; white-space: nowrap;";
    item.appendChild(label);

    item.addEventListener("click", (e) => {
      e.stopPropagation();
      picker.remove();
      showAnnDetail(annId, pos);
    });
    picker.appendChild(item);
  }

  document.body.appendChild(picker);

  // Position near click
  const x = Math.min(pos.clientX, window.innerWidth - 310);
  const y = Math.min(pos.clientY, window.innerHeight - picker.offsetHeight - 10);
  picker.style.left = x + "px";
  picker.style.top = y + "px";

  // Close on outside click
  const closeHandler = (e) => {
    if (!picker.contains(e.target)) {
      picker.remove();
      document.removeEventListener("mousedown", closeHandler);
    }
  };
  setTimeout(() => document.addEventListener("mousedown", closeHandler), 0);
}

// ---------------------------------------------------------------------------
// Annotation detail (click on highlight)
// ---------------------------------------------------------------------------
function showAnnDetail(annId, posOverride) {
  pendingAnnId = annId;
  const ann = annotations.find(a => a.id === annId);
  if (!ann) return;
  const code = (project.codes || []).find(c => c.id === ann.code_id);
  const codeEl = document.getElementById("ann-detail-code");
  codeEl.textContent = code ? `${buildPath(project.codes, ann.code_id)}` : ann.code_id;
  codeEl.title = t("ann.change.code") || "Klicka för att byta kod";
  codeEl.style.cursor = "pointer";
  document.getElementById("ann-detail-memo").value = ann.memo || "";
  // Weight
  const weightRow = document.getElementById("ann-detail-weight-row");
  if (weightRow) {
    weightRow.classList.toggle("hidden", !useWeightEnabled);
    const wi = document.getElementById("ann-detail-weight");
    const wv = document.getElementById("ann-detail-weight-val");
    if (wi) { wi.value = ann.weight ?? 50; if (wv) wv.textContent = wi.value; }
  }
  // Anchor
  const anchorRow = document.getElementById("ann-detail-anchor-row");
  if (anchorRow) {
    anchorRow.classList.remove("hidden");  // always visible (anchor is free of use_weight)
    const ac = document.getElementById("ann-detail-anchor");
    if (ac) ac.checked = !!ann.anchor;
  }

  // Prefer an explicit position (e.g. pin click), then the pin element, then
  // the text-span for text annotations, then a sensible fallback.
  let rect;
  if (posOverride) {
    rect = { left: posOverride.clientX, bottom: posOverride.clientY };
  } else if (ann.kind === "point") {
    const pinEl = document.querySelector(`.point-pin[data-ann-id="${annId}"]`);
    rect = pinEl ? pinEl.getBoundingClientRect() : { left: 200, bottom: 200 };
  } else {
    const span = document.querySelector(`[data-ann-id="${annId}"]`);
    rect = span ? span.getBoundingClientRect() : { left: 200, bottom: 200 };
  }
  const detail = document.getElementById("ann-detail");
  detail.classList.remove("hidden");
  positionPopup(detail, rect.left, rect.bottom + window.scrollY);
}

function hideAnnDetail() {
  document.getElementById("ann-detail").classList.add("hidden");
  pendingAnnId = null;
}

document.getElementById("btn-ann-update").addEventListener("click", async () => {
  if (!pendingAnnId) return;
  const annId = pendingAnnId;
  const memo   = document.getElementById("ann-detail-memo").value;
  const anchor = !!(document.getElementById("ann-detail-anchor")?.checked);
  const patch  = { memo, anchor };
  if (useWeightEnabled) {
    patch.weight = parseInt(document.getElementById("ann-detail-weight")?.value || "50", 10);
  }
  hideAnnDetail();
  const res = await PATCH(`/api/transcripts/${currentTid}/annotations/${annId}`, patch);
  if (res.ok) {
    const ann = annotations.find(a => a.id === annId);
    if (ann) {
      ann.memo = memo;
      ann.anchor = anchor;
      if (useWeightEnabled) ann.weight = patch.weight;
    }
    _annChangeCounter++;
    if (ann && ann.kind === "point") renderPointPins();
    else renderTranscriptText();
    updateAnnBadge();
  }
  _refreshCodebookManagerIfOpen();
});

document.getElementById("btn-ann-remove").addEventListener("click", async () => {
  if (!pendingAnnId) return;
  const annId = pendingAnnId;
  // Hide detail popup BEFORE showing confirm dialog to avoid overlap
  hideAnnDetail();
  if (!await appConfirm(t("confirm.del.ann"))) return;
  const annToDelete = annotations.find(a => a.id === annId);
  const res = await DEL(`/api/transcripts/${currentTid}/annotations/${annId}`);
  if (res.ok) {
    annotations = annotations.filter(a => a.id !== annId);
    updateAnnBadge();
    renderTranscriptText();
    renderPointPins();
    if (annToDelete) {
      pushUndo({ type: "delete", tid: currentTid, ann: annToDelete });
      redoStack = [];
    }
  }
});

document.getElementById("btn-ann-detail-cancel").addEventListener("click", hideAnnDetail);

// Click the code line in the detail popup to change which code this annotation uses.
document.getElementById("ann-detail-code").addEventListener("click", () => {
  if (!pendingAnnId) return;
  const annId = pendingAnnId;
  hideAnnDetail();
  _annEditId = annId;
  const popup = document.getElementById("ann-popup");
  popup.classList.remove("hidden");
  document.getElementById("ann-memo").value = "";
  const weightRow = document.getElementById("ann-weight-row");
  if (weightRow) weightRow.classList.add("hidden");
  renderAnnCodeList();
  // Position near the original detail popup location
  const detail = document.getElementById("ann-detail");
  const r = detail.getBoundingClientRect();
  positionPopup(popup, r.left, r.top + window.scrollY);
});

// ---------------------------------------------------------------------------
// Codebook
// ---------------------------------------------------------------------------
function renderCodebook() {
  const container = document.getElementById("codebook-tree");
  container.innerHTML = "";
  const tree = buildTree(project.codes || []);
  if (numberingEnabled) assignNumbers(tree, "");
  tree.forEach(node => container.appendChild(renderCodeNode(node, 0)));
  if (numberingEnabled) addNumbersToCodebook(tree);
  // Re-apply any active search filter
  const q = document.getElementById("codebook-search")?.value || "";
  if (q) filterCodebook(q);
}

function renderCodeNode(node, depth) {
  const wrap = document.createElement("div");
  wrap.className = "code-node";

  const item = document.createElement("div");
  item.className = "code-item";
  item.dataset.codeId = node.id;
  item.style.paddingLeft = `${14 + depth * 14}px`;
  item.innerHTML = `
    <span class="code-dot" style="background:${node.color}"></span>
    <span class="code-name">${esc(node.name)}</span>
    <button class="code-edit-btn" title="Redigera">✎</button>`;
  item.querySelector(".code-edit-btn").addEventListener("click", e => {
    e.stopPropagation();
    openCodeModal(node);
  });
  wrap.appendChild(item);

  if (node.children && node.children.length) {
    const ch = document.createElement("div");
    ch.className = "code-children";
    node.children.forEach(child => ch.appendChild(renderCodeNode(child, depth + 1)));
    wrap.appendChild(ch);
  }
  return wrap;
}

// ---- Add code button ----
document.getElementById("btn-add-code").addEventListener("click", () => openCodeModal(null));

function openCodeModal(code, prefillName) {
  document.getElementById("code-modal-title").textContent = code ? t("code.edit.title") : t("code.new.title");
  document.getElementById("code-edit-id").value = code ? code.id : "";
  document.getElementById("code-name").value = prefillName !== undefined ? (prefillName || "") : (code ? code.name : "");
  document.getElementById("code-color").value = code ? code.color : (PALETTE_PRIMARY ? PALETTE_PRIMARY[0] : "#0072B2");
  document.getElementById("code-description").value = code ? (code.description || "") : "";
  document.getElementById("code-error").textContent = "";

  // Build parent select
  const sel = document.getElementById("code-parent");
  sel.innerHTML = `<option value="">— ingen (toppnivå) —</option>`;
  buildFlatList(project.codes || []).forEach(c => {
    if (code && c.id === code.id) return; // Can't be own parent
    const opt = document.createElement("option");
    opt.value = c.id;
    opt.textContent = c.ancestors.length
      ? c.ancestors.join(" › ") + " › " + c.name
      : c.name;
    if (code && code.parent === c.id) opt.selected = true;
    sel.appendChild(opt);
  });

  const delBtn = document.getElementById("btn-code-delete");
  delBtn.classList.toggle("hidden", !code);

  // Initialise colour palette
  const chosenColor = document.getElementById("code-color").value;
  if (typeof selectPaletteColor === "function") {
    selectPaletteColor(chosenColor);
    updateParentShades();
  }

  document.getElementById("modal-code").classList.remove("hidden");
}

document.getElementById("btn-code-cancel").addEventListener("click", () => {
  _pendingCodeFromAnn = null;
  document.getElementById("modal-code").classList.add("hidden");
});

document.getElementById("btn-code-confirm").addEventListener("click", async () => {
  const id   = document.getElementById("code-edit-id").value;
  const name = document.getElementById("code-name").value.trim();
  const parent = document.getElementById("code-parent").value || null;
  const color  = document.getElementById("code-color").value;
  const desc   = document.getElementById("code-description").value.trim();
  const errEl  = document.getElementById("code-error");
  errEl.textContent = "";
  if (!name) { errEl.textContent = "Namn krävs."; return; }

  // Snapshot existing code IDs so we can identify the newly created code below.
  const prevIds = new Set((project && project.codes ? project.codes : []).map(c => c.id));

  let res;
  if (id) {
    res = await PATCH(`/api/codes/${id}`, { name, parent, color, description: desc });
  } else {
    res = await POST("/api/codes", { name, parent, color, description: desc });
  }
  if (res.error) { errEl.textContent = res.error; return; }
  project = res.project;
  renderCodebook();
  if (currentTid) renderTranscriptText(); // Refresh highlight colors
  document.getElementById("modal-code").classList.add("hidden");
  _refreshCodebookManagerIfOpen();

  // If this create came from the annotation popup, apply the new code to the
  // selection or point that was active when the popup was open.
  if (!id && currentTid && (_pendingCodeFromAnn || _pendingCodeFromPoint)) {
    const sel = _pendingCodeFromAnn;
    const pt  = _pendingCodeFromPoint;
    _pendingCodeFromAnn = null;
    _pendingCodeFromPoint = null;
    const newCode = (project.codes || []).find(c => !prevIds.has(c.id));
    if (newCode) {
      const body = pt
        ? { kind: "point", code_id: newCode.id, x: pt.x, y: pt.y, memo: "", weight: 50 }
        : { code_id: newCode.id, start: sel.start, end: sel.end, text: sel.text, memo: "", weight: 50 };
      const annRes = await POST(`/api/transcripts/${currentTid}/annotations`, body);
      if (annRes.ok) {
        annotations.push(annRes.annotation);
        updateAnnBadge();
        if (annRes.annotation.kind === "point") renderPointPins();
        else renderTranscriptText();
        pushUndo({ type: "add", tid: currentTid, ann: annRes.annotation });
        redoStack = [];
      }
    }
  }
});

document.getElementById("btn-code-delete").addEventListener("click", async () => {
  const id = document.getElementById("code-edit-id").value;
  if (!id) return;
  if (!await appConfirm(t("confirm.del.code"))) return;
  const res = await DEL(`/api/codes/${id}`);
  if (res.ok) {
    project = res.project;
    renderCodebook();
    if (currentTid) renderTranscriptText();
    document.getElementById("modal-code").classList.add("hidden");
    _refreshCodebookManagerIfOpen();
  }
});

// ---------------------------------------------------------------------------
// Export
// ---------------------------------------------------------------------------
function downloadFromEndpoint(url, filename) {
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

// ---------------------------------------------------------------------------
// Export modal
// ---------------------------------------------------------------------------
document.getElementById("btn-export-menu").addEventListener("click", () => {
  const lastFolder = localStorage.getItem("transcribbler_export_folder") || "";
  document.getElementById("export-folder-input").value = lastFolder;
  document.getElementById("export-status").textContent = "";
  document.getElementById("btn-export-confirm").disabled = false;
  document.getElementById("modal-export").classList.remove("hidden");
});

document.getElementById("btn-export-browse").addEventListener("click", async () => {
  let folder;
  if (window.electronAPI) {
    folder = await window.electronAPI.pickFolder();
  } else {
    const res = await GET("/api/pick-folder");
    folder = res.folder;
  }
  if (folder) {
    document.getElementById("export-folder-input").value = folder;
    localStorage.setItem("transcribbler_export_folder", folder);
  }
});

document.getElementById("btn-export-cancel").addEventListener("click", () => {
  document.getElementById("modal-export").classList.add("hidden");
});

document.getElementById("btn-export-confirm").addEventListener("click", async () => {
  const folder = document.getElementById("export-folder-input").value.trim();
  if (!folder) {
    document.getElementById("export-status").textContent = t("export.err.no.folder");
    return;
  }
  const formats = [];
  if (document.getElementById("exp-fmt-csv").checked)            formats.push("csv");
  if (document.getElementById("exp-fmt-csv-tidy")?.checked)      formats.push("csv_tidy");
  if (document.getElementById("exp-fmt-md-codes").checked)       formats.push("md_codes");
  if (document.getElementById("exp-fmt-md-codebook").checked)    formats.push("md_codebook");
  if (document.getElementById("exp-fmt-md-transcript").checked)  formats.push("md_transcript");
  if (document.getElementById("exp-fmt-qdpx")?.checked)          formats.push("qdpx");
  if (formats.length === 0) {
    document.getElementById("export-status").textContent = t("export.err.no.format");
    return;
  }
  localStorage.setItem("transcribbler_export_folder", folder);
  const btn = document.getElementById("btn-export-confirm");
  btn.disabled = true;
  document.getElementById("export-status").textContent = "…";
  const res = await POST("/api/export/to-folder", { folder, formats, tid: currentTid });
  btn.disabled = false;
  if (res.ok) {
    document.getElementById("export-status").textContent =
      t("export.ok", { count: res.written.length, folder: res.folder });
  } else {
    document.getElementById("export-status").textContent = res.error || t("export.err.no.format");
  }
});

// ---------------------------------------------------------------------------
// Merge
// ---------------------------------------------------------------------------
document.getElementById("btn-merge").addEventListener("click", () => {
  document.getElementById("merge-result").textContent = "";
  document.getElementById("merge-error").textContent = "";
  document.getElementById("merge-path").value = "";
  document.getElementById("modal-merge").classList.remove("hidden");
});
document.getElementById("btn-merge-cancel").addEventListener("click", () => {
  document.getElementById("modal-merge").classList.add("hidden");
});
document.getElementById("btn-merge-confirm").addEventListener("click", async () => {
  const path = document.getElementById("merge-path").value.trim();
  if (!path) return;
  const res = await POST("/api/merge", { path });
  if (res.error) {
    document.getElementById("merge-error").textContent = res.error;
  } else {
    document.getElementById("merge-result").textContent =
      `Importerade ${res.imported} kodningar från ${res.coder} (${res.skipped} redan fanns).`;
    // Reload if current transcript was affected
    if (currentTid && res.transcript_id === currentTid) loadTranscript(currentTid);
  }
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function esc(str) {
  return String(str)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;")
    .replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
function escAttr(str) { return String(str).replace(/"/g, "&quot;"); }

function buildTree(codes) {
  const byId = {};
  codes.forEach(c => byId[c.id] = { ...c, children: [] });
  const roots = [];
  codes.forEach(c => {
    const node = byId[c.id];
    if (c.parent && byId[c.parent]) byId[c.parent].children.push(node);
    else roots.push(node);
  });
  return roots;
}

function buildFlatList(codes) {
  const byId = {};
  codes.forEach(c => byId[c.id] = c);
  function ancestors(code) {
    const chain = [];
    let pid = code.parent;
    while (pid && byId[pid]) { chain.unshift(byId[pid].name); pid = byId[pid].parent; }
    return chain;
  }
  return codes.map(c => ({ ...c, ancestors: ancestors(c) }));
}

function buildPath(codes, codeId) {
  const flat = buildFlatList(codes);
  const code = flat.find(c => c.id === codeId);
  if (!code) return codeId;
  return [...code.ancestors, code.name].join(" › ");
}

function positionPopup(el, x, y) {
  PopupManager.position(el, x, y + 8);
}

// ---------------------------------------------------------------------------
// Theme toggle (dark / light)
// ---------------------------------------------------------------------------
const THEME_KEY = "transcribbler_theme";

function applyTheme(theme) {
  document.body.classList.toggle("light", theme === "light");
  // Label shows the mode we will switch TO (i.e. the action)
  const label = theme === "light" ? t("btn.theme.to.dark") : t("btn.theme.to.light");
  const btn = document.getElementById("btn-theme");
  if (btn) btn.textContent = label;
  const btnSplash = document.getElementById("btn-theme-splash");
  if (btnSplash) btnSplash.textContent = label;
}

// Restore saved preference
applyTheme(localStorage.getItem(THEME_KEY) || "dark");

function _toggleTheme() {
  const next = document.body.classList.contains("light") ? "dark" : "light";
  localStorage.setItem(THEME_KEY, next);
  applyTheme(next);
}
document.getElementById("btn-theme").addEventListener("click", _toggleTheme);
document.getElementById("btn-theme-splash")?.addEventListener("click", _toggleTheme);

// ---------------------------------------------------------------------------
// Search in transcript
// ---------------------------------------------------------------------------
document.getElementById("search-input").addEventListener("input", runSearch);
document.getElementById("btn-search-next").addEventListener("click", () => stepSearch(1));
document.getElementById("btn-search-prev").addEventListener("click", () => stepSearch(-1));
document.getElementById("btn-search-clear").addEventListener("click", () => clearSearch());

document.getElementById("search-input").addEventListener("keydown", e => {
  if (e.key === "Enter") stepSearch(e.shiftKey ? -1 : 1);
  if (e.key === "Escape") clearSearch();
});

function runSearch() {
  const q = document.getElementById("search-input").value;
  if (!q || !currentText) { clearSearchHighlights(); return; }
  searchMatches = [];
  const lower = currentText.toLowerCase();
  const ql = q.toLowerCase();
  let pos = 0;
  while ((pos = lower.indexOf(ql, pos)) !== -1) {
    searchMatches.push({ start: pos, end: pos + q.length });
    pos += q.length;
  }
  searchIndex = searchMatches.length > 0 ? 0 : -1;
  renderTranscriptText();
  scrollToMatch();
  updateSearchCount();
}

function stepSearch(dir) {
  if (!searchMatches.length) return;
  searchIndex = (searchIndex + dir + searchMatches.length) % searchMatches.length;
  const all = document.querySelectorAll(".search-match");
  all.forEach((el, i) => el.classList.toggle("search-active", i === searchIndex));
  scrollToMatch();
  updateSearchCount();
}

function openSearch() {
  if (!currentTid) return;
  document.getElementById("search-bar").classList.remove("hidden");
  const inp = document.getElementById("search-input");
  inp.focus();
  inp.select();
}

function clearSearch(skipRender) {
  document.getElementById("search-input").value = "";
  document.getElementById("search-bar").classList.add("hidden");
  searchMatches = []; searchIndex = -1;
  if (!skipRender) renderTranscriptText();
  updateSearchCount();
}

function clearSearchHighlights() {
  searchMatches = []; searchIndex = -1;
  renderTranscriptText();
  updateSearchCount();
}

function updateSearchCount() {
  const el = document.getElementById("search-count");
  const q = document.getElementById("search-input").value;
  if (!q) { el.textContent = ""; return; }
  if (!searchMatches.length) { el.textContent = "0 / 0"; return; }
  el.textContent = `${searchIndex + 1} / ${searchMatches.length}`;
}

function scrollToMatch() {
  const active = document.querySelector(".search-match.search-active");
  if (active) active.scrollIntoView({ block: "center", behavior: "smooth" });
}

function applySearchHighlightsIfActive() {
  if (!searchMatches.length) return;
  const container = document.getElementById("transcript-text");
  highlightInDOM(container, searchMatches, searchIndex);
}
/**
 * Build a char-offset → DOM text-node map for a container element.
 * Returns [{node, start, end}] sorted by document order.
 */
function buildNodeCharMap(container) {
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
  const textNodes = [];
  let node;
  while ((node = walker.nextNode())) textNodes.push(node);
  let charPos = 0;
  return textNodes.map(n => {
    const start = charPos;
    charPos += n.textContent.length;
    return { node: n, start, end: charPos };
  });
}

function highlightInDOM(container, matches, activeIdx) {
  for (let mi = 0; mi < matches.length; mi++) {
    const m = matches[mi];
    const nodeMap = buildNodeCharMap(container);
    for (const nm of nodeMap) {
      if (nm.end <= m.start || nm.start >= m.end) continue;
      const localStart = Math.max(0, m.start - nm.start);
      const localEnd   = Math.min(nm.node.textContent.length, m.end - nm.start);
      if (localStart >= localEnd) continue;
      try {
        const range = document.createRange();
        range.setStart(nm.node, localStart);
        range.setEnd(nm.node, localEnd);
        const span = document.createElement("span");
        span.className = "search-match" + (mi === activeIdx ? " search-active" : "");
        range.surroundContents(span);
      } catch (_) {}
      break;
    }
  }
}

// ---------------------------------------------------------------------------
// Transcript memo (opens via right-click on transcript in sidebar)
// ---------------------------------------------------------------------------
let memoTargetTid = null;

// Context menu
const ctxMenu = document.getElementById("transcript-ctx-menu");

document.getElementById("transcript-list").addEventListener("contextmenu", e => {
  const li = e.target.closest("li[data-tid]");
  if (!li) return;
  e.preventDefault();
  memoTargetTid = li.dataset.tid;
  // If right-clicking outside the current selection, reset to just this item
  if (!selectedTids.has(memoTargetTid)) {
    selectedTids.clear();
    selectedTids.add(memoTargetTid);
    renderTranscriptList();
  }
  ctxMenu.classList.remove("hidden");
  PopupManager.position(ctxMenu, e.clientX, e.clientY, { estWidth: 180, estHeight: 100 });
});

// Drag-select: extend selection while left button held and pointer moves over items
document.getElementById("transcript-list").addEventListener("mouseover", e => {
  if (!_dragSelecting) return;
  const li = e.target.closest("li[data-tid]");
  if (!li || !e.buttons) return; // abort if button released outside a mouseup target
  const tid = li.dataset.tid;
  if (!selectedTids.has(tid)) {
    _dragMoved = true;
    selectedTids.add(tid);
    li.classList.add("selected");
  }
});

document.addEventListener("mouseup", () => { _dragSelecting = false; });

// ---------------------------------------------------------------------------
// Dropdown menus (Export, Tools) — click-toggle
// ---------------------------------------------------------------------------
function closeAllDropdowns() {
  document.querySelectorAll(".dropdown.open").forEach(d => d.classList.remove("open"));
}

document.querySelectorAll(".dropdown > button").forEach(btn => {
  btn.addEventListener("click", e => {
    e.stopPropagation();
    const dd = btn.closest(".dropdown");
    const wasOpen = dd.classList.contains("open");
    closeAllDropdowns();
    if (!wasOpen) dd.classList.add("open");
  });
});

// ---------------------------------------------------------------------------
// Code context menu (right-click on code in sidebar)
// ---------------------------------------------------------------------------
let _ctxCodeId = null;
const codeCtxMenu = document.getElementById("code-ctx-menu");

document.getElementById("codebook-tree").addEventListener("contextmenu", e => {
  const item = e.target.closest(".code-item[data-code-id]");
  if (!item) return;
  e.preventDefault();
  _ctxCodeId = item.dataset.codeId;
  codeCtxMenu.classList.remove("hidden");
  PopupManager.position(codeCtxMenu, e.clientX, e.clientY, { estWidth: 180, estHeight: 80 });
});

document.getElementById("ctx-code-rename").addEventListener("click", async () => {
  codeCtxMenu.classList.add("hidden");
  if (!_ctxCodeId || !project) return;
  const code = (project.codes || []).find(c => c.id === _ctxCodeId);
  if (!code) return;
  const newName = await appPrompt(t("ctx.code.rename.prompt") || "Nytt namn:", code.name);
  if (!newName || !newName.trim() || newName.trim() === code.name) return;
  PATCH(`/api/codes/${_ctxCodeId}`, {
    name: newName.trim(),
    parent: code.parent || null,
    color: code.color,
    description: code.description || "",
  }).then(res => {
    if (res.error) { appAlert(res.error); return; }
    project = res.project;
    renderCodebook();
    _refreshCodebookManagerIfOpen();
  });
});

// Hide code context menu; close dropdowns; clear transcript selection when clicking outside the list
document.addEventListener("click", e => {
  ctxMenu.classList.add("hidden");
  codeCtxMenu?.classList.add("hidden");
  closeAllDropdowns();
  const inList = document.getElementById("transcript-list").contains(e.target);
  if (!inList && selectedTids.size > 0) {
    selectedTids.clear();
    renderTranscriptList();
  }
});
document.addEventListener("contextmenu", e => {
  if (!document.getElementById("transcript-list").contains(e.target))
    ctxMenu.classList.add("hidden");
  if (!document.getElementById("codebook-tree").contains(e.target))
    codeCtxMenu?.classList.add("hidden");
});

document.getElementById("ctx-search").addEventListener("click", async () => {
  if (!memoTargetTid) return;
  if (memoTargetTid !== currentTid) await loadTranscript(memoTargetTid);
  openSearch();
});

document.getElementById("ctx-memo").addEventListener("click", () => {
  if (!memoTargetTid) return;
  const tr = project.transcripts.find(tr => tr.id === memoTargetTid);
  document.getElementById("memo-modal-title").textContent =
    "Memo — " + (tr ? tr.name : memoTargetTid);
  document.getElementById("modal-memo-text").value = tr?.memo || "";
  document.getElementById("modal-memo").classList.remove("hidden");
  setTimeout(() => document.getElementById("modal-memo-text").focus(), 50);
});

document.getElementById("btn-memo-cancel").addEventListener("click", () => {
  document.getElementById("modal-memo").classList.add("hidden");
});

document.getElementById("btn-memo-save").addEventListener("click", async () => {
  if (!memoTargetTid) return;
  const memo = document.getElementById("modal-memo-text").value;
  await PATCH(`/api/transcripts/${memoTargetTid}/memo`, { memo });
  const tr = project.transcripts.find(tr => tr.id === memoTargetTid);
  if (tr) tr.memo = memo;
  document.getElementById("modal-memo").classList.add("hidden");
});

// ---------------------------------------------------------------------------
// Transcript categorization
// ---------------------------------------------------------------------------
let _categorizeTids = [];

document.getElementById("ctx-categorize").addEventListener("click", () => {
  const tids = selectedTids.size > 0 ? [...selectedTids] : (memoTargetTid ? [memoTargetTid] : []);
  if (tids.length === 0) return;
  openCategorizeModal(tids);
});

function openCategorizeModal(tids) {
  _categorizeTids = tids;
  // Populate datalist with all distinct categories in the project
  const cats = [...new Set((project.transcripts || []).map(tr => tr.category).filter(Boolean))].sort();
  const dl = document.getElementById("cat-datalist");
  dl.innerHTML = cats.map(c => `<option value="${esc(c)}">`).join("");
  // Pre-fill if all selected transcripts share the same category
  const selCats = [...new Set(tids.map(id => {
    const tr = project.transcripts.find(tr => tr.id === id);
    return tr?.category || "";
  }))];
  document.getElementById("cat-name-input").value = selCats.length === 1 ? selCats[0] : "";
  document.getElementById("modal-categorize").classList.remove("hidden");
  setTimeout(() => document.getElementById("cat-name-input").focus(), 50);
}

document.getElementById("btn-cat-cancel")?.addEventListener("click", () => {
  document.getElementById("modal-categorize").classList.add("hidden");
});

document.getElementById("btn-cat-save")?.addEventListener("click", async () => {
  const category = document.getElementById("cat-name-input").value.trim();
  if (!category) return;
  const res = await PATCH("/api/transcripts/categorize", { tids: _categorizeTids, category });
  if (res.ok) {
    project = res.project;
    selectedTids.clear();
    renderTranscriptList();
    document.getElementById("modal-categorize").classList.add("hidden");
  }
});

document.getElementById("btn-cat-remove")?.addEventListener("click", async () => {
  const res = await PATCH("/api/transcripts/categorize", { tids: _categorizeTids, category: null });
  if (res.ok) {
    project = res.project;
    selectedTids.clear();
    renderTranscriptList();
    document.getElementById("modal-categorize").classList.add("hidden");
  }
});


// ---------------------------------------------------------------------------
// Statistics modal
// ---------------------------------------------------------------------------
document.getElementById("btn-stats").addEventListener("click", openStats);
document.getElementById("btn-stats-close").addEventListener("click", () => {
  document.getElementById("modal-stats").classList.add("hidden");
});

document.querySelectorAll("input[name='stats-scope']").forEach(r => {
  r.addEventListener("change", openStats);
});

async function openStats() {
  const scope = document.querySelector("input[name='stats-scope']:checked").value;
  const tid = (scope === "transcript" && currentTid) ? currentTid : null;
  const res = await GET(`/api/stats${tid ? `?tid=${tid}` : ""}`);
  renderStats(res);
  document.getElementById("modal-stats").classList.remove("hidden");
}

function renderStats(data) {
  const body = document.getElementById("stats-body");
  if (!data.rows || data.rows.length === 0) {
    body.innerHTML = "<p style='color:var(--text-dim);margin-top:12px'>Inga kodningar ännu.</p>";
    return;
  }
  const maxCount = Math.max(...data.rows.map(r => r.count));
  let html = `<p style="font-size:12px;color:var(--text-dim);margin:10px 0">
    ${data.total_annotations} kodningar totalt · ${data.transcript_count} transkript</p>
    <table class="stats-table">
    <thead><tr>
      <th>${t("stats.col.code")}</th>
      <th>${t("stats.col.count")}</th>
      <th style="min-width:120px"></th>
      <th>${t("stats.col.chars")}</th>
      <th>${t("stats.col.coders")}</th>
    </tr></thead><tbody>`;

  data.rows.forEach(row => {
    const pct = maxCount ? (row.count / maxCount * 100).toFixed(0) : 0;
    html += `<tr>
      <td><span class="code-dot" style="background:${row.color};display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px"></span>${esc(row.name)}</td>
      <td style="text-align:right;font-weight:600">${row.count}</td>
      <td><div class="stats-bar"><div class="stats-bar-fill" style="width:${pct}%;background:${row.color}"></div></div></td>
      <td style="text-align:right;color:var(--text-dim)">${row.char_count}</td>
      <td style="color:var(--text-dim)">${row.coders.join(", ")}</td>
    </tr>`;
  });
  html += "</tbody></table>";
  body.innerHTML = html;
}

// ---------------------------------------------------------------------------
// IRR modal
// ---------------------------------------------------------------------------
document.getElementById("btn-irr").addEventListener("click", openIRR);
document.getElementById("btn-irr-close").addEventListener("click", () => {
  document.getElementById("modal-irr").classList.add("hidden");
});
document.getElementById("btn-irr-compute").addEventListener("click", computeIRR);

async function openIRR() {
  document.getElementById("irr-result").classList.add("hidden");
  document.getElementById("irr-error").textContent = "";

  const codersRes = await GET("/api/coders");
  const coders = codersRes.coders || [];

  const selA = document.getElementById("irr-coder-a");
  const selB = document.getElementById("irr-coder-b");
  selA.innerHTML = coders.map(c => `<option value="${esc(c)}">${esc(c)}</option>`).join("");
  selB.innerHTML = coders.map((c, i) =>
    `<option value="${esc(c)}" ${i === 1 ? "selected" : ""}>${esc(c)}</option>`).join("");

  const selT = document.getElementById("irr-transcript");
  selT.innerHTML = (project.transcripts || []).map(t =>
    `<option value="${esc(t.id)}" ${t.id === currentTid ? "selected" : ""}>${esc(t.name)}</option>`
  ).join("");

  document.getElementById("modal-irr").classList.remove("hidden");
}

async function computeIRR() {
  const coderA = document.getElementById("irr-coder-a").value;
  const coderB = document.getElementById("irr-coder-b").value;
  const tid    = document.getElementById("irr-transcript").value;
  const errEl  = document.getElementById("irr-error");
  errEl.textContent = "";

  const res = await GET(`/api/transcripts/${tid}/irr?coder_a=${encodeURIComponent(coderA)}&coder_b=${encodeURIComponent(coderB)}`);
  if (res.error) { errEl.textContent = res.error; return; }

  // Kappa display
  const k = res.kappa;
  const kColor = k >= 0.6 ? "var(--success)" : k >= 0.4 ? "#f9c74f" : "var(--danger)";
  document.getElementById("irr-kappa-display").innerHTML = `
    <div class="kappa-box">
      <span class="kappa-value" style="color:${kColor}">κ = ${k.toFixed(3)}</span>
      <span class="kappa-label">${esc(res.interpretation)}</span>
      <span class="kappa-sub">Po = ${res.po} · Pe = ${res.pe} · n = ${res.n_chars.toLocaleString()} tecken</span>
    </div>`;

  // Per-code table
  const tbody = document.getElementById("irr-table-body");
  tbody.innerHTML = res.per_code.map(row => `
    <tr>
      <td><span class="code-dot" style="background:${row.color};display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px"></span>${esc(row.name)}</td>
      <td style="text-align:right">${row.coder_a}</td>
      <td style="text-align:right">${row.coder_b}</td>
      <td style="text-align:right">${row.agreement}</td>
    </tr>`).join("");

  document.getElementById("irr-result").classList.remove("hidden");
}

// ============================================================
// FEATURE 1: Resizable panels
// ============================================================

const PANEL_KEY = "transcribbler_panels";

(function initResizablePanels() {
  const workspace = document.getElementById("workspace");
  try {
    const saved = JSON.parse(localStorage.getItem(PANEL_KEY) || "{}");
    if (saved.left)  { workspace.style.setProperty("--left-w",  saved.left);  document.documentElement.style.setProperty("--left-w",  saved.left); }
    if (saved.right) { workspace.style.setProperty("--right-w", saved.right); document.documentElement.style.setProperty("--right-w", saved.right); }
  } catch(e) {}

  function makeDraggable(handleId, side) {
    const handle = document.getElementById(handleId);
    if (!handle) return;
    handle.addEventListener("mousedown", e => {
      e.preventDefault();
      handle.classList.add("dragging");
      const startX = e.clientX;
      const cols = getComputedStyle(workspace).gridTemplateColumns.split(" ");
      // cols order: [leftW, 4px, 1frPx, 4px, rightW]
      const startW = parseFloat(side === "left" ? cols[0] : cols[4]);

      const onMove = mv => {
        const delta = mv.clientX - startX;
        if (side === "left") {
          const w = Math.max(140, Math.min(520, startW + delta));
          workspace.style.setProperty("--left-w", w + "px");
          document.documentElement.style.setProperty("--left-w", w + "px");
        } else {
          const w = Math.max(160, Math.min(520, startW - delta));
          workspace.style.setProperty("--right-w", w + "px");
          document.documentElement.style.setProperty("--right-w", w + "px");
        }
      };
      const onUp = () => {
        handle.classList.remove("dragging");
        const cols2 = getComputedStyle(workspace).gridTemplateColumns.split(" ");
        try {
          const s = JSON.parse(localStorage.getItem(PANEL_KEY) || "{}");
          s.left  = cols2[0];
          s.right = cols2[4];
          localStorage.setItem(PANEL_KEY, JSON.stringify(s));
        } catch(e) {}
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
      };
      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
    });
  }

  makeDraggable("handle-left",  "left");
  makeDraggable("handle-right", "right");

  // Source image panel resize
  const SOURCE_W_KEY = "transcribbler_source_w";
  const savedSrcW = localStorage.getItem(SOURCE_W_KEY);
  if (savedSrcW) {
    const panel = document.getElementById("source-img-panel");
    if (panel) panel.style.width = savedSrcW;
  }

  const handleSrc = document.getElementById("handle-source");
  if (handleSrc) {
    handleSrc.addEventListener("mousedown", e => {
      e.preventDefault();
      handleSrc.classList.add("dragging");
      const startX = e.clientX;
      const panel  = document.getElementById("source-img-panel");
      const startW = panel.getBoundingClientRect().width;
      const onMove = mv => {
        const maxW = panel.parentElement ? panel.parentElement.getBoundingClientRect().width * 0.95 : 9999;
        const w = Math.max(180, Math.min(maxW, startW - (mv.clientX - startX)));
        panel.style.width = w + "px";
      };
      const onUp = () => {
        handleSrc.classList.remove("dragging");
        localStorage.setItem(SOURCE_W_KEY, panel.style.width);
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
      };
      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
    });
  }
})();


// ============================================================
// FEATURE 2: Text formatting overlay (bold / italic)
// ============================================================

function applyFontSettings() {
  const txt = document.getElementById("transcript-text");
  if (!txt) return;
  txt.style.fontSize   = FMT_SIZES[currentFontIdx] + "px";
  txt.style.fontFamily = currentFontFamily === "serif"
    ? "Georgia, 'Times New Roman', serif"
    : "var(--font)";
}

function updateFmtBtnStates() {
  document.getElementById("fmt-sans") .classList.toggle("active", currentFontFamily === "sans");
  document.getElementById("fmt-serif").classList.toggle("active", currentFontFamily === "serif");
}

document.getElementById("fmt-a-minus").addEventListener("click", () => {
  currentFontIdx = Math.max(0, currentFontIdx - 1);
  localStorage.setItem(FMT_KEY_SIZE, currentFontIdx);
  applyFontSettings();
});
document.getElementById("fmt-a-plus").addEventListener("click", () => {
  currentFontIdx = Math.min(FMT_SIZES.length - 1, currentFontIdx + 1);
  localStorage.setItem(FMT_KEY_SIZE, currentFontIdx);
  applyFontSettings();
});
document.getElementById("fmt-sans").addEventListener("click", () => {
  currentFontFamily = "sans";
  localStorage.setItem(FMT_KEY_FAM, currentFontFamily);
  applyFontSettings();
  updateFmtBtnStates();
});
document.getElementById("fmt-serif").addEventListener("click", () => {
  currentFontFamily = "serif";
  localStorage.setItem(FMT_KEY_FAM, currentFontFamily);
  applyFontSettings();
  updateFmtBtnStates();
});

// Use mousedown + preventDefault so the button click doesn't steal focus and
// collapse the current text selection before the handler runs.
document.getElementById("fmt-bold").addEventListener("mousedown", e => {
  e.preventDefault();
  applyFormatToSelection("bold");
});
document.getElementById("fmt-italic").addEventListener("mousedown", e => {
  e.preventDefault();
  applyFormatToSelection("italic");
});

async function applyFormatToSelection(fmtType) {
  if (!currentTid) { await appAlert(t("alert.no.transcript.fmt")); return; }
  const sel = window.getSelection();
  if (!sel || sel.isCollapsed) return;
  const selText = sel.toString();
  if (!selText.trim()) return;

  const container = document.getElementById("transcript-text");
  const range = sel.getRangeAt(0);
  const preRange = document.createRange();
  preRange.setStart(container, 0);
  preRange.setEnd(range.startContainer, range.startOffset);
  const start = preRange.toString().length;
  const end   = start + selText.length;

  const res = await POST(`/api/transcripts/${currentTid}/formatting`, {
    start, end, type: fmtType
  });
  if (res.ok) {
    formattingSpans.push(res.span);
    applyFormatSpans();
  }
  sel.removeAllRanges();
}

function applyFormatSpans() {
  if (!formattingSpans || !formattingSpans.length) return;
  const container = document.getElementById("transcript-text");
  if (!container) return;

  const sorted = [...formattingSpans].sort((a, b) => a.start - b.start);

  // Build char map once; DOM doesn't change between span applications
  // (each surroundContents may split text nodes, so rebuild after each wrap)
  for (const span of sorted) {
    if (container.querySelector(`[data-fmt-id="${span.id}"]`)) continue;

    const nodeMap = buildNodeCharMap(container);

    for (const nm of nodeMap) {
      if (nm.end <= span.start || nm.start >= span.end) continue;
      const localStart = Math.max(0, span.start - nm.start);
      const localEnd   = Math.min(nm.node.textContent.length, span.end - nm.start);
      if (localStart >= localEnd) continue;
      try {
        const r = document.createRange();
        r.setStart(nm.node, localStart);
        r.setEnd(nm.node, localEnd);
        const el = document.createElement(span.type === "bold" ? "strong" : "em");
        el.className = "fmt-span";
        el.dataset.fmtId = span.id;
        el.title = "Klicka för att ta bort formatering";
        el.addEventListener("click", ev => {
          ev.stopPropagation();
          removeFmtSpan(span.id);
        });
        r.surroundContents(el);
        break; // one pass per span
      } catch(err) { /* skip overlapping ranges */ }
    }
  }
}

async function removeFmtSpan(spanId) {
  if (!currentTid) return;
  const res = await DEL(`/api/transcripts/${currentTid}/formatting/${spanId}`);
  if (res.ok) {
    formattingSpans = formattingSpans.filter(s => s.id !== spanId);
    renderTranscriptText();
  }
}

updateFmtBtnStates();


// ============================================================
// FEATURE 3: Colorblind-safe color palette (Wong 2011)
// ============================================================

const PALETTE_PRIMARY = [
  "#0072B2","#E69F00","#009E73","#56B4E9","#D55E00",
  "#CC79A7","#F0E442","#000000","#882255","#44AA99"
];
const PALETTE_EXTENDED = [
  "#332288","#117733","#999933","#88CCEE","#DDCC77",
  "#CC6677","#AA4499","#DDDDDD","#888888","#661100"
];

function _hexToHSL(hex) {
  let r = parseInt(hex.slice(1,3),16)/255;
  let g = parseInt(hex.slice(3,5),16)/255;
  let b = parseInt(hex.slice(5,7),16)/255;
  const max = Math.max(r,g,b), min = Math.min(r,g,b);
  let h=0, s=0, l=(max+min)/2;
  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d/(2-max-min) : d/(max+min);
    switch(max) {
      case r: h=((g-b)/d+(g<b?6:0))/6; break;
      case g: h=((b-r)/d+2)/6; break;
      case b: h=((r-g)/d+4)/6; break;
    }
  }
  return [h*360, s*100, l*100];
}

function _hslToHex(h, s, l) {
  h/=360; s/=100; l/=100;
  const hue2rgb=(p,q,t)=>{
    if(t<0)t+=1; if(t>1)t-=1;
    if(t<1/6) return p+(q-p)*6*t;
    if(t<1/2) return q;
    if(t<2/3) return p+(q-p)*(2/3-t)*6;
    return p;
  };
  let r,g,b;
  if(s===0){ r=g=b=l; }
  else {
    const q=l<0.5?l*(1+s):l+s-l*s, p=2*l-q;
    r=hue2rgb(p,q,h+1/3); g=hue2rgb(p,q,h); b=hue2rgb(p,q,h-1/3);
  }
  return "#"+[r,g,b].map(x=>Math.round(x*255).toString(16).padStart(2,"0")).join("");
}

function generateShades(hex, count=5) {
  const [h, s] = _hexToHSL(hex);
  return Array.from({length:count}, (_,i) => _hslToHex(h, Math.min(s,80), 25+i*13));
}

function buildPaletteRow(container, colors) {
  container.innerHTML = "";
  colors.forEach(color => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "palette-swatch";
    btn.style.background = color;
    btn.title = color;
    btn.dataset.color = color;
    btn.addEventListener("click", () => selectPaletteColor(color));
    container.appendChild(btn);
  });
}

function selectPaletteColor(color) {
  const hidden   = document.getElementById("code-color");
  const dot      = document.getElementById("palette-selected-dot");
  const hexLabel = document.getElementById("palette-selected-hex");
  if (hidden)   hidden.value        = color;
  if (dot)      dot.style.background = color;
  if (hexLabel) hexLabel.textContent = color;
  document.querySelectorAll(".palette-swatch").forEach(b =>
    b.classList.toggle("selected", b.dataset.color === color));
}

function updateParentShades() {
  const parentId   = document.getElementById("code-parent").value;
  const shadesWrap = document.getElementById("palette-shades-wrap");
  const shadesRow  = document.getElementById("palette-shades");
  if (parentId && project) {
    const pc = (project.codes||[]).find(c => c.id === parentId);
    if (pc && pc.color) {
      buildPaletteRow(shadesRow, generateShades(pc.color));
      shadesWrap.style.display = "";
      return;
    }
  }
  shadesWrap.style.display = "none";
}

function initColorPalette() {
  const primary = document.getElementById("palette-primary");
  const extended = document.getElementById("palette-extended");
  const moreBtn  = document.getElementById("btn-palette-more");
  if (!primary) return;
  buildPaletteRow(primary,  PALETTE_PRIMARY);
  buildPaletteRow(extended, PALETTE_EXTENDED);
  moreBtn.addEventListener("click", () => {
    const showing = extended.style.display !== "none";
    extended.style.display = showing ? "none" : "";
    moreBtn.textContent = showing ? "Visa fler ▾" : "Visa färre ▴";
  });
  document.getElementById("code-parent").addEventListener("change", updateParentShades);
}

// Palette is initialised in openCodeModal directly (see that function)

initColorPalette();


// ============================================================
// FEATURE 4: Auto-numbering of codes
// ============================================================

document.getElementById("setting-numbering").addEventListener("change", async function() {
  numberingEnabled = this.checked;
  await PATCH("/api/project/settings", { numbering: numberingEnabled });
  if (project) project.numbering = numberingEnabled;
  renderCodebook();
  if (currentTid) renderTranscriptText();
});

document.getElementById("setting-trans-order").addEventListener("change", async function() {
  transOrderEnabled = this.checked;
  await PATCH("/api/project/settings", { trans_order: transOrderEnabled });
  if (project) project.trans_order = transOrderEnabled;
  renderTranscriptList();
});

document.getElementById("setting-use-weight")?.addEventListener("change", async function() {
  useWeightEnabled = this.checked;
  await PATCH("/api/project/settings", { use_weight: useWeightEnabled });
  if (project) project.use_weight = useWeightEnabled;
});

document.getElementById("setting-use-waveform")?.addEventListener("change", async function() {
  useWaveformEnabled = this.checked;
  await PATCH("/api/project/settings", { use_waveform: useWaveformEnabled });
  if (project) project.use_waveform = useWaveformEnabled;
  // Re-apply to current transcript
  if (currentTid) {
    const transcript = (project?.transcripts || []).find(t => t.id === currentTid);
    _destroyWaveform();
    if (useWaveformEnabled && transcript?.source === "audio" && transcript?.audio_file) {
      _initWaveform(currentTid);
    } else {
      document.getElementById("waveform-wrap").classList.add("hidden");
    }
  }
});

function assignNumbers(nodes, prefix) {
  nodes.forEach((node, i) => {
    const num = prefix ? `${prefix}.${i+1}` : `${i+1}`;
    node.number = num;
    if (node.children && node.children.length) assignNumbers(node.children, num);
  });
}

function addNumbersToCodebook(tree) {
  if (!numberingEnabled) return;
  function walk(nodes) {
    nodes.forEach(node => {
      const item = document.querySelector(`.code-item[data-code-id="${node.id}"]`);
      if (item) {
        const nameEl = item.querySelector(".code-name");
        if (nameEl && !nameEl.querySelector(".code-number")) {
          const numSpan = document.createElement("span");
          numSpan.className = "code-number";
          numSpan.textContent = node.number + ". ";
          nameEl.prepend(numSpan);
        }
      }
      if (node.children) walk(node.children);
    });
  }
  walk(tree);
}

// (renderCodebook now calls assignNumbers/addNumbersToCodebook directly)


// ============================================================
// ============================================================
// FEATURE 5b: Codebook manager modal
// ============================================================

document.getElementById("btn-codebook").addEventListener("click", openCodebookManager);
document.getElementById("btn-codebook-close").addEventListener("click", () => {
  document.getElementById("modal-codebook").classList.add("hidden");
});
document.getElementById("btn-cb-add").addEventListener("click", () => {
  document.getElementById("modal-codebook").classList.add("hidden");
  openCodeModal(null);
});

document.getElementById("btn-cb-merge").addEventListener("click", openMergeCodes);
document.getElementById("btn-merge-codes-cancel").addEventListener("click", () => {
  document.getElementById("modal-merge-codes").classList.add("hidden");
});
document.getElementById("btn-merge-codes-confirm").addEventListener("click", confirmMergeCodes);

function openMergeCodes() {
  const codes = project ? (project.codes || []) : [];
  if (codes.length < 2) return;
  const flat = _buildNumberedFlat();
  const buildOpts = (sel) => {
    sel.innerHTML = "";
    flat.forEach(c => {
      const numPfx = (numberingEnabled && c.number) ? `${c.number}. ` : "";
      const path = c.ancestors.length ? c.ancestors.join(" > ") + " > " : "";
      const opt = document.createElement("option");
      opt.value = c.id;
      opt.textContent = numPfx + path + c.name;
      sel.appendChild(opt);
    });
  };
  buildOpts(document.getElementById("merge-source"));
  buildOpts(document.getElementById("merge-target"));
  if (flat.length > 1) document.getElementById("merge-target").selectedIndex = 1;
  document.getElementById("merge-status").textContent = "";
  document.getElementById("modal-merge-codes").classList.remove("hidden");
}

async function confirmMergeCodes() {
  const sourceId = document.getElementById("merge-source").value;
  const targetId = document.getElementById("merge-target").value;
  const statusEl = document.getElementById("merge-status");
  if (sourceId === targetId) {
    statusEl.textContent = "Källkod och målkod kan inte vara samma.";
    return;
  }
  const sourceName = document.getElementById("merge-source").selectedOptions[0]?.textContent || sourceId;
  const targetName = document.getElementById("merge-target").selectedOptions[0]?.textContent || targetId;
  if (!await appConfirm(
    `Alla kodningar från "${sourceName}" flyttas till "${targetName}". Källkoden "${sourceName}" tas bort permanent. Fortsätta?`
  )) return;
  const btn = document.getElementById("btn-merge-codes-confirm");
  btn.disabled = true;
  statusEl.textContent = "Slår ihop…";
  const res = await POST("/api/codes/merge", { source_id: sourceId, target_id: targetId });
  btn.disabled = false;
  if (res.ok) {
    project = res.project;
    document.getElementById("modal-merge-codes").classList.add("hidden");
    renderCodebook();
    if (currentTid) {
      const annRes = await GET(`/api/transcripts/${currentTid}/annotations`);
      if (annRes) annotations = annRes.annotations || [];
      renderTranscriptText();
    }
    openCodebookManager();
  } else {
    statusEl.textContent = res.error || "Något gick fel.";
  }
}

async function openCodebookManager() {
  closeAllDropdowns();
  // Fetch annotation counts and anchor indicators in parallel
  let counts = {}, anchors = {};
  try {
    const [rCounts, rAnchors] = await Promise.all([
      fetch("/api/codes/stats"),
      fetch("/api/codes/anchors"),
    ]);
    if (rCounts.ok) counts = await rCounts.json();
    if (rAnchors.ok) anchors = await rAnchors.json();
  } catch (_) {}
  renderCodebookManager(counts, anchors);
  document.getElementById("modal-codebook").classList.remove("hidden");
}

function renderCodebookManager(counts, anchors = {}) {
  const list = document.getElementById("codebook-mgr-list");
  list.innerHTML = "";
  const codes = project ? (project.codes || []) : [];
  const tree = buildTree(codes);
  if (numberingEnabled) assignNumbers(tree, "");

  if (!tree.length) {
    const empty = document.createElement("p");
    empty.className = "cb-mgr-empty";
    empty.textContent = t("codebook.empty");
    list.appendChild(empty);
    return;
  }

  function renderRow(node, depth) {
    const row = document.createElement("div");
    row.className = "cb-mgr-row";
    row.style.paddingLeft = `${depth * 20 + 8}px`;

    const dot = document.createElement("span");
    dot.className = "code-dot";
    dot.style.background = node.color || "#888";

    const nameWrap = document.createElement("span");
    nameWrap.className = "cb-mgr-name-wrap";
    const numStr = (numberingEnabled && node.number) ? `${node.number}.\u2009` : "";
    nameWrap.innerHTML = `<span class="cb-mgr-name">${esc(numStr + node.name)}</span>` +
      (node.description ? `<span class="cb-mgr-desc">${esc(node.description)}</span>` : "");

    const count = counts[node.id] || 0;
    const badge = document.createElement("span");
    badge.className = "cb-mgr-count";
    badge.title = t("code.ann.count");
    badge.textContent = count > 0 ? count : "—";

    const editBtn = document.createElement("button");
    editBtn.className = "code-edit-btn";
    editBtn.title = t("code.edit.title");
    editBtn.textContent = "✎";
    editBtn.addEventListener("click", () => {
      document.getElementById("modal-codebook").classList.add("hidden");
      openCodeModal(node);
    });

    row.appendChild(dot);
    row.appendChild(nameWrap);
    if (anchors[node.id]) {
      const pin = document.createElement("span");
      pin.className = "cb-mgr-anchor";
      pin.title = anchors[node.id].text || t("ann.anchor.label");
      pin.textContent = "📌";
      row.appendChild(pin);
    }
    row.appendChild(badge);
    row.appendChild(editBtn);
    list.appendChild(row);

    if (node.children) node.children.forEach(child => renderRow(child, depth + 1));
  }

  tree.forEach(node => renderRow(node, 0));
}

// Re-render codebook manager (if open) after a code is saved/deleted
function _refreshCodebookManagerIfOpen() {
  if (!document.getElementById("modal-codebook").classList.contains("hidden")) {
    openCodebookManager();
  }
}

// ============================================================
// FEATURE 5: Code tree view modal
// ============================================================

document.getElementById("btn-codetree").addEventListener("click", openCodeTree);
document.getElementById("btn-codetree-close").addEventListener("click", () => {
  document.getElementById("modal-codetree").classList.add("hidden");
});

// PNG export (loads html2canvas on demand)
document.getElementById("btn-ct-png").addEventListener("click", async () => {
  const btn = document.getElementById("btn-ct-png");
  const orig = btn.textContent;
  btn.textContent = "…";
  if (!window.html2canvas) {
    await new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = "https://html2canvas.hertzen.com/dist/html2canvas.min.js";
      s.onload = resolve; s.onerror = reject;
      document.head.appendChild(s);
    });
  }
  const content = document.getElementById("codetree-content");
  const canvas  = await html2canvas(content, { backgroundColor: null, scale: 2 });
  const link = document.createElement("a");
  link.download = "kodtrad.png";
  link.href = canvas.toDataURL("image/png");
  link.click();
  btn.textContent = orig;
});

// PDF: print-media isolation
document.getElementById("btn-ct-pdf").addEventListener("click", () => {
  document.body.classList.add("print-codetree");
  window.print();
  document.body.classList.remove("print-codetree");
});

function openCodeTree() {
  renderCodeTree();
  document.getElementById("modal-codetree").classList.remove("hidden");
}

// ============================================================
// FEATURE 6: Project-wide search
// ============================================================

document.getElementById("btn-project-search").addEventListener("click", openProjectSearch);
document.getElementById("btn-proj-search-close").addEventListener("click", closeProjectSearch);
document.getElementById("btn-proj-search-run").addEventListener("click", runProjectSearch);
let _projSearchTimer = null;
document.getElementById("proj-search-input").addEventListener("keydown", e => {
  if (e.key === "Enter")  { clearTimeout(_projSearchTimer); runProjectSearch(); }
  if (e.key === "Escape") closeProjectSearch();
});
document.getElementById("proj-search-input").addEventListener("input", () => {
  clearTimeout(_projSearchTimer);
  const q = document.getElementById("proj-search-input").value.trim();
  if (q.length >= 3)
    _projSearchTimer = setTimeout(runProjectSearch, 300);
});

function openProjectSearch() {
  document.getElementById("modal-project-search").classList.remove("hidden");
  document.getElementById("proj-search-input").focus();
}

function closeProjectSearch() {
  document.getElementById("modal-project-search").classList.add("hidden");
}

function _makeSnippetEl(match, query, tid) {
  const el = document.createElement("div");
  el.className = "proj-search-snippet";
  const s   = match.snippet;
  const ms  = match.snippet_match_start;
  const me  = ms + query.length;
  el.innerHTML = esc(s.slice(0, ms)) +
    `<mark>${esc(s.slice(ms, me))}</mark>` +
    esc(s.slice(me));
  el.addEventListener("click", async () => {
    closeProjectSearch();
    if (tid !== currentTid) await loadTranscript(tid);
    document.getElementById("search-input").value = query;
    openSearch();
    runSearch();
    // Navigate to the specific occurrence
    const idx = searchMatches.findIndex(m => m.start === match.start);
    if (idx !== -1) { searchIndex = idx; scrollToMatch(); updateSearchCount(); }
  });
  return el;
}

async function runProjectSearch() {
  const q = document.getElementById("proj-search-input").value.trim();
  if (q.length < 2) return;

  const summaryEl = document.getElementById("proj-search-summary");
  const resultsEl = document.getElementById("proj-search-results");
  summaryEl.textContent = "";
  resultsEl.innerHTML = `<div class="proj-search-loading">Söker…</div>`;

  const res = await GET(`/api/search?q=${encodeURIComponent(q)}`);

  if (!res.results) {
    resultsEl.innerHTML = `<div class="proj-search-empty">Något gick fel.</div>`;
    return;
  }

  if (res.total_matches === 0) {
    summaryEl.textContent = `Inga träffar för "${q}"`;
    resultsEl.innerHTML = `<div class="proj-search-empty">Inga träffar hittades.</div>`;
    return;
  }

  const tPlural = res.results.length === 1 ? "transkript" : "transkript";
  const mPlural = res.total_matches === 1 ? "träff" : "träffar";
  summaryEl.textContent =
    `${res.total_matches} ${mPlural} i ${res.results.length} ${tPlural}`;

  resultsEl.innerHTML = "";
  const SHOW_LIMIT = 5;

  for (const group of res.results) {
    const groupEl = document.createElement("div");
    groupEl.className = "proj-search-group";

    // Header
    const header = document.createElement("div");
    header.className = "proj-search-group-header";
    const matchWord = group.matches.length === 1 ? "träff" : "träffar";
    header.innerHTML =
      `<span class="proj-search-chevron">▼</span>` +
      `<span class="proj-search-group-name">${esc(group.name)}</span>` +
      `<span class="proj-search-group-count">${group.matches.length} ${matchWord}</span>`;

    // Snippets
    const snippetWrap = document.createElement("div");
    snippetWrap.className = "proj-search-snippets";

    const visible = group.matches.slice(0, SHOW_LIMIT);
    const hidden  = group.matches.slice(SHOW_LIMIT);

    for (const match of visible) {
      snippetWrap.appendChild(_makeSnippetEl(match, q, group.tid));
    }

    if (hidden.length > 0) {
      const moreEl = document.createElement("div");
      moreEl.className = "proj-search-more";
      moreEl.textContent = `+${hidden.length} till`;
      moreEl.addEventListener("click", () => {
        for (const match of hidden)
          snippetWrap.insertBefore(_makeSnippetEl(match, q, group.tid), moreEl);
        moreEl.remove();
      });
      snippetWrap.appendChild(moreEl);
    }

    // Collapse/expand on header click
    header.addEventListener("click", () => {
      const closing = !snippetWrap.classList.contains("hidden");
      snippetWrap.classList.toggle("hidden", closing);
      header.querySelector(".proj-search-chevron").textContent = closing ? "▶" : "▼";
    });

    groupEl.appendChild(header);
    groupEl.appendChild(snippetWrap);
    resultsEl.appendChild(groupEl);
  }
}

function renderCodeTree() {
  const content = document.getElementById("codetree-content");
  content.innerHTML = "";

  const tree = buildTree(project ? project.codes || [] : []);
  if (numberingEnabled) assignNumbers(tree, "");

  const titleEl = document.createElement("div");
  titleEl.className = "codetree-title";
  titleEl.textContent = project ? project.name : "Kodbok";
  content.appendChild(titleEl);

  if (!tree.length) {
    const empty = document.createElement("p");
    empty.style.cssText = "color:var(--text-dim);padding:16px";
    empty.textContent = "Inga koder ännu.";
    content.appendChild(empty);
    return;
  }
  tree.forEach(node => content.appendChild(renderCtNode(node, 0)));
}

function renderCtNode(node, depth) {
  const wrap = document.createElement("div");
  wrap.className = "ct-node";
  wrap.style.marginLeft = depth * 20 + "px";

  const row = document.createElement("div");
  row.className = "ct-row";

  const bar = document.createElement("div");
  bar.className = "ct-bar";
  bar.style.background = node.color || "#888";

  const chevron = document.createElement("span");
  chevron.className = "ct-chevron";
  chevron.textContent = (node.children && node.children.length) ? "▼" : " ";

  const nameWrap = document.createElement("div");
  nameWrap.className = "ct-name-wrap";
  const numStr = (numberingEnabled && node.number) ? `${node.number}. ` : "";
  const nameEl = document.createElement("span");
  nameEl.className = "ct-name";
  nameEl.textContent = numStr + node.name;
  nameWrap.appendChild(nameEl);

  if (node.description) {
    const descEl = document.createElement("span");
    descEl.className = "ct-desc";
    descEl.textContent = node.description;
    nameWrap.appendChild(descEl);
  }

  row.appendChild(bar);
  row.appendChild(chevron);
  row.appendChild(nameWrap);
  wrap.appendChild(row);

  if (node.children && node.children.length) {
    const childWrap = document.createElement("div");
    childWrap.className = "ct-children";
    node.children.forEach(child => childWrap.appendChild(renderCtNode(child, depth + 1)));
    wrap.appendChild(childWrap);

    chevron.style.cursor = "pointer";
    chevron.addEventListener("click", () => {
      const collapsed = childWrap.style.display === "none";
      childWrap.style.display = collapsed ? "" : "none";
      chevron.textContent = collapsed ? "▼" : "▶";
    });
  }
  return wrap;
}


// ============================================================
// FEATURE 6: Searchable code popup with "create new" option
// ============================================================

function _buildNumberedFlat() {
  const flat = buildFlatList(project ? project.codes || [] : []);
  if (numberingEnabled) {
    const tree = buildTree(project ? project.codes || [] : []);
    assignNumbers(tree, "");
    const numMap = {};
    function collectNums(nodes) {
      nodes.forEach(n => { numMap[n.id] = n.number; if(n.children) collectNums(n.children); });
    }
    collectNums(tree);
    flat.forEach(c => { c.number = numMap[c.id] || ""; });
  }
  return flat;
}

function setupAnnSearch() {
  const searchInput = document.getElementById("ann-search");
  const list        = document.getElementById("ann-code-list");
  const createRow   = document.getElementById("ann-create-row");
  const createBtn   = document.getElementById("btn-ann-create-code");
  const flat        = _buildNumberedFlat();

  function renderList(query) {
    const q = (query || "").toLowerCase().trim();
    list.innerHTML = "";

    const filtered = q
      ? flat.filter(c => {
          const fullPath = [...c.ancestors, c.name].join(" ").toLowerCase();
          return fullPath.includes(q);
        })
      : flat;

    filtered.forEach(code => {
      const div = document.createElement("div");
      div.className = "ann-code-option";
      div.dataset.codeId = code.id;
      const numPfx = (numberingEnabled && code.number) ? `${code.number}. ` : "";
      div.innerHTML = `<span class="code-dot" style="background:${code.color}"></span>
        <span>${esc(numPfx)}${code.ancestors.length ? esc(code.ancestors.join(" › ")) + " › " : ""}${esc(code.name)}</span>`;
      div.addEventListener("click", () => {
        list.querySelectorAll(".ann-code-option").forEach(d => d.classList.remove("selected"));
        div.classList.add("selected");
      });
      list.appendChild(div);
    });

    // Show "create" option when query matches nothing exactly
    const exactMatch = flat.find(c => c.name.toLowerCase() === q);
    if (q && !exactMatch) {
      createBtn.textContent = `+ Skapa "${query}"`;
      createRow.classList.remove("hidden");
    } else {
      createRow.classList.add("hidden");
    }
  }

  renderList("");

  if (searchInput) {
    searchInput.value = "";
    // Remove previous handler if any
    if (searchInput._annHandler) {
      searchInput.removeEventListener("input", searchInput._annHandler);
    }
    searchInput._annHandler = () => renderList(searchInput.value);
    searchInput.addEventListener("input", searchInput._annHandler);
    // Auto-focus after popup shown, then restore the text selection so the
    // user can still see what they highlighted while picking a code.
    setTimeout(() => {
      searchInput.focus();
      if (_savedSelRange) {
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(_savedSelRange);
      }
    }, 50);
  }
}

// "Create new code" from popup — preserves the active selection/point so the
// new code gets applied to it once the user confirms the create-code modal.
let _pendingCodeFromAnn = null;   // {start, end, text} or null
let _pendingCodeFromPoint = null; // {x, y} or null
document.getElementById("btn-ann-create-code").addEventListener("click", () => {
  const q = (document.getElementById("ann-search").value || "").trim();
  if (!q) return;
  _pendingCodeFromAnn   = pendingSelection ? { ...pendingSelection } : null;
  _pendingCodeFromPoint = pendingPoint     ? { ...pendingPoint }     : null;
  hideAnnPopup();
  openCodeModal(null, q);
});


// ============================================================
// Settings popover toggle
// ============================================================

document.getElementById("btn-settings").addEventListener("click", e => {
  e.stopPropagation();
  document.getElementById("settings-popover").classList.toggle("hidden");
});

document.addEventListener("click", e => {
  const wrap = document.getElementById("settings-wrap");
  if (wrap && !wrap.contains(e.target)) {
    document.getElementById("settings-popover").classList.add("hidden");
  }
});

// --- System info (loaded once, shown in settings popover) ---
(function loadSystemInfo() {
  GET("/api/system-info").then(info => {
    const box = document.getElementById("system-info-box");
    if (!box) return;
    const lines = [];
    if (info.ram_gb) lines.push(`RAM: ${info.ram_gb} GB`);
    if (info.gpu && info.gpu !== "none") {
      lines.push(`GPU: ${info.gpu.toUpperCase()}`);
    }
    if (info.disk_free_gb) lines.push(`${currentLang === "sv" ? "Disk ledig" : "Disk free"}: ${info.disk_free_gb} GB`);

    const warns = info.warnings || [];
    if (warns.includes("no_gpu")) {
      lines.push(`<span class="sys-warn">${currentLang === "sv"
        ? "Ingen GPU — diarisering kommer köras på CPU (långsamt)"
        : "No GPU — diarization will run on CPU (slow)"}</span>`);
    }
    if (warns.includes("low_ram")) {
      lines.push(`<span class="sys-warn">${currentLang === "sv"
        ? "Lite RAM — transkription kan bli långsam"
        : "Low RAM — transcription may be slow"}</span>`);
    }
    if (warns.includes("low_disk")) {
      lines.push(`<span class="sys-warn">${currentLang === "sv"
        ? "Lite diskutrymme — ML-modeller kräver ~2 GB"
        : "Low disk space — ML models require ~2 GB"}</span>`);
    }

    box.innerHTML = lines.join("<br>");
    box.classList.remove("hidden");
  }).catch(() => { /* system-info endpoint unavailable — skip silently */ });
})();


// ============================================================
// Keyboard shortcuts
// ============================================================
document.addEventListener("keydown", e => {
  const ctrl = e.ctrlKey || e.metaKey;
  const inInput = e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA";

  // Ctrl+Z — undo (skip when focus is in a text field)
  if (ctrl && e.key === "z" && !e.shiftKey && !inInput) {
    e.preventDefault();
    undo();
    return;
  }

  // Ctrl+Y or Ctrl+Shift+Z — redo
  if (ctrl && (e.key === "y" || (e.key === "z" && e.shiftKey)) && !inInput) {
    e.preventDefault();
    redo();
    return;
  }

  // Ctrl+F — open/focus search (transcript search in coding view, excerpt search in analysis view)
  if (ctrl && e.key === "f") {
    if (_analysisActive) {
      e.preventDefault();
      const el = document.getElementById("analysis-search");
      if (el) { el.focus(); el.select(); }
    } else if (currentTid) {
      e.preventDefault();
      openSearch();
    }
    return;
  }

  // Escape — close floating popups
  if (e.key === "Escape") {
    hideAnnPopup();
    hideAnnDetail();
    document.getElementById("settings-popover")?.classList.add("hidden");
  }
});


// ============================================================
// Codebook search / filter
// ============================================================
document.getElementById("codebook-search")?.addEventListener("input", function () {
  filterCodebook(this.value);
});

function filterCodebook(query) {
  const q = (query || "").toLowerCase().trim();
  if (!q) {
    document.querySelectorAll("#codebook-tree .code-node").forEach(n => n.style.display = "");
    return;
  }

  const flat = buildFlatList(project ? project.codes || [] : []);
  const matchIds = new Set();

  flat.forEach(c => {
    const fullText = [...c.ancestors, c.name].join(" ").toLowerCase();
    if (fullText.includes(q)) {
      matchIds.add(c.id);
      // Include all ancestors so the tree context is preserved
      let pid = c.parent;
      while (pid) {
        matchIds.add(pid);
        const par = (project.codes || []).find(x => x.id === pid);
        pid = par ? par.parent : null;
      }
    }
  });

  document.querySelectorAll("#codebook-tree .code-item[data-code-id]").forEach(item => {
    const node = item.closest(".code-node");
    if (node) node.style.display = matchIds.has(item.dataset.codeId) ? "" : "none";
  });
}


// ============================================================
// Language-choice dropdown — show/hide Whisper model size
// ============================================================
function _updateModelWrapVisibility() {
  const choice = document.getElementById("language-choice")?.value || "autodetect";
  const wrap   = document.getElementById("whisper-model-wrap");
  if (wrap) wrap.style.display = (choice === "en" || choice === "other") ? "" : "none";
  // Word-level timestamps only relevant for KB-Whisper (sv/autodetect)
  const wordTsRow = document.getElementById("diar-word-ts-row");
  if (wordTsRow) wordTsRow.classList.toggle("hidden", choice === "en" || choice === "other");
}

document.getElementById("language-choice")?.addEventListener("change", _updateModelWrapVisibility);


// ============================================================
// FEATURE: Code tooltip (hover on code in right sidebar)
// ============================================================
(function () {
  const tree = document.getElementById("codebook-tree");
  const tip  = document.getElementById("code-tooltip");
  if (!tree || !tip) return;

  tree.addEventListener("mouseover", e => {
    const item = e.target.closest(".code-item");
    if (!item) { tip.classList.add("hidden"); return; }
    const codeId = item.dataset.codeId;
    const code   = (project?.codes || []).find(c => c.id === codeId);
    if (!code?.description) { tip.classList.add("hidden"); return; }
    tip.textContent = code.description;
    tip.classList.remove("hidden");
    _positionTooltip(e.clientX, e.clientY);
  });

  tree.addEventListener("mousemove", e => {
    if (!tip.classList.contains("hidden")) _positionTooltip(e.clientX, e.clientY);
  });

  tree.addEventListener("mouseleave", () => tip.classList.add("hidden"));

  function _positionTooltip(cx, cy) {
    const margin = 12;
    tip.style.left = "0"; tip.style.top = "0"; // reset so getBoundingClientRect is correct
    tip.classList.remove("hidden");
    const tw = tip.offsetWidth, th = tip.offsetHeight;
    PopupManager.position(tip, cx + margin, cy + margin, { estWidth: tw, estHeight: th });
  }
})();


// ============================================================
// FEATURE: Segment weight slider live update
// ============================================================
document.getElementById("ann-weight")?.addEventListener("input", function () {
  document.getElementById("ann-weight-val").textContent = this.value;
});
document.getElementById("ann-detail-weight")?.addEventListener("input", function () {
  document.getElementById("ann-detail-weight-val").textContent = this.value;
});


// ============================================================
// FEATURE: Code matrix modal (transkript × kod)
// ============================================================
document.getElementById("btn-code-matrix")?.addEventListener("click", openCodeMatrix);
document.getElementById("btn-code-matrix-close")?.addEventListener("click", () => {
  document.getElementById("modal-code-matrix").classList.add("hidden");
});

async function openCodeMatrix() {
  closeAllDropdowns();
  document.getElementById("modal-code-matrix").classList.remove("hidden");
  const wrap = document.getElementById("code-matrix-wrap");
  wrap.innerHTML = "<p style='padding:12px;color:var(--text-dim)'>Laddar…</p>";
  const data = await GET("/api/code-matrix");
  renderCodeMatrix(data, wrap);
}

function renderCodeMatrix(data, wrap) {
  if (!data.codes || data.codes.length === 0) {
    wrap.innerHTML = "<p style='padding:12px;color:var(--text-dim)'>Inga annoteringar ännu.</p>";
    return;
  }
  const table = document.createElement("table");
  table.className = "matrix-table";
  // Header row
  const thead = table.createTHead();
  const hrow  = thead.insertRow();
  const th0   = document.createElement("th");
  th0.className = "row-header";
  th0.textContent = t("sidebar.transcripts") || "Transkript";
  hrow.appendChild(th0);
  data.codes.forEach(c => {
    const th = document.createElement("th");
    th.title = c.name;
    th.innerHTML = `<span style="color:${esc(c.color)}">■</span> ${esc(c.name)}`;
    hrow.appendChild(th);
  });
  // Data rows
  const tbody = table.createTBody();
  data.transcripts.forEach(tr => {
    const row = tbody.insertRow();
    const td0 = document.createElement("td");
    td0.className = "row-header";
    td0.textContent = tr.name;
    row.appendChild(td0);
    data.codes.forEach(c => {
      const count = (data.matrix[tr.id] || {})[c.id] || 0;
      const td = row.insertCell();
      td.textContent = count > 0 ? count : "";
      td.className   = count === 0 ? "matrix-cell-zero" : "";
    });
  });
  // Totals row
  const tfoot = table.createTFoot();
  const frow  = tfoot.insertRow();
  const ftd0  = document.createElement("td");
  ftd0.className  = "row-header";
  ftd0.textContent = "Totalt";
  ftd0.style.fontWeight = "600";
  frow.appendChild(ftd0);
  data.codes.forEach(c => {
    const td = frow.insertCell();
    td.textContent = data.totals[c.id] || 0;
    td.style.fontWeight = "600";
  });

  wrap.innerHTML = "";
  wrap.appendChild(table);
}


// ============================================================
// FEATURE: Co-occurrence modal (kod × kod)
// ============================================================
document.getElementById("btn-cooccurrence")?.addEventListener("click", openCooccurrence);
document.getElementById("btn-cooccurrence-close")?.addEventListener("click", () => {
  document.getElementById("modal-cooccurrence").classList.add("hidden");
});

async function openCooccurrence() {
  closeAllDropdowns();
  document.getElementById("modal-cooccurrence").classList.remove("hidden");
  const wrap = document.getElementById("cooccurrence-wrap");
  wrap.innerHTML = "<p style='padding:12px;color:var(--text-dim)'>Laddar…</p>";
  const data = await GET("/api/cooccurrence");
  renderCooccurrence(data, wrap);
}

function renderCooccurrence(data, wrap) {
  if (!data.codes || data.codes.length === 0) {
    wrap.innerHTML = "<p style='padding:12px;color:var(--text-dim)'>Inga kodsamförekomster ännu.</p>";
    return;
  }
  const codes  = data.codes;
  const matrix = data.matrix;
  const table  = document.createElement("table");
  table.className = "matrix-table";
  // Header
  const thead = table.createTHead();
  const hrow  = thead.insertRow();
  const th0   = document.createElement("th");
  th0.className = "row-header";
  hrow.appendChild(th0);
  codes.forEach(c => {
    const th = document.createElement("th");
    th.title = c.name;
    th.innerHTML = `<span style="color:${esc(c.color)}">■</span> ${esc(c.name)}`;
    hrow.appendChild(th);
  });
  // Data rows
  const tbody = table.createTBody();
  codes.forEach(ca => {
    const row = tbody.insertRow();
    const td0 = document.createElement("td");
    td0.className  = "row-header";
    td0.innerHTML  = `<span style="color:${esc(ca.color)}">■</span> ${esc(ca.name)}`;
    row.appendChild(td0);
    codes.forEach(cb => {
      const td = row.insertCell();
      if (ca.id === cb.id) {
        td.className = "matrix-diag";
        td.textContent = "—";
      } else {
        const count = (matrix[ca.id] || {})[cb.id] || 0;
        td.textContent = count > 0 ? count : "";
        td.className   = count === 0 ? "matrix-cell-zero" : "";
      }
    });
  });
  wrap.innerHTML = "";
  wrap.appendChild(table);
}


// ============================================================
// FEATURE: Waveform (WaveSurfer.js)
// ============================================================
function _initWaveform(tid) {
  if (!window.WaveSurfer) return;
  const wrap = document.getElementById("waveform-wrap");
  if (!wrap) return;
  _destroyWaveform();
  wrap.classList.remove("hidden");
  const audioPlayer = document.getElementById("audio-player");

  try {
    const cachedPeaks = _loadWaveformPeaks(tid);
    const wsOpts = {
      container:     "#waveform",
      waveColor:     getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || "#0072B2",
      progressColor: "rgba(0,0,0,0.25)",
      height:        72,
      barWidth:      2,
      barGap:        1,
      barRadius:     1,
      interact:      true,
      url:           `/api/transcripts/${tid}/audio`,
    };
    if (cachedPeaks) wsOpts.peaks = cachedPeaks;
    _wavesurfer = WaveSurfer.create(wsOpts);
  } catch (err) {
    console.error("WaveSurfer init failed:", err);
    wrap.classList.add("hidden");
    return;
  }
  // Cache peaks after first decode to skip re-download next time
  _wavesurfer.on("ready", () => _cacheWaveformPeaks(tid));

  // Clicking waveform seeks audio player
  _wavesurfer.on("interaction", pos => {
    if (!audioPlayer) return;
    _wavesurferSeeking = true;
    _wavesurfer.pause();
    audioPlayer.currentTime = pos;
    audioPlayer.play().catch(() => {});
    setTimeout(() => { _wavesurferSeeking = false; }, 200);
  });

  // Hide native <audio> element + model badge, show minimal controls instead
  if (audioPlayer) audioPlayer.style.display = "none";
  const modelBadgeWf = document.getElementById("audio-model-badge");
  if (modelBadgeWf) modelBadgeWf.style.display = "none";
  const wfCtrl = document.getElementById("waveform-controls");
  if (wfCtrl) { wfCtrl.classList.remove("hidden"); wfCtrl.style.display = "flex"; }

  // Play/pause button
  const wfPlayBtn = document.getElementById("wf-play-pause");
  const wfTime    = document.getElementById("wf-time");
  const wfVolume  = document.getElementById("wf-volume");

  function _fmtTime(s) {
    const m = Math.floor(s / 60), sec = Math.floor(s % 60);
    return `${m}:${sec.toString().padStart(2, "0")}`;
  }
  function _updateWfTime() {
    if (!audioPlayer || !wfTime) return;
    wfTime.textContent = `${_fmtTime(audioPlayer.currentTime)} / ${_fmtTime(audioPlayer.duration || 0)}`;
  }

  const _refreshPlayBtn = () => {
    if (wfPlayBtn) wfPlayBtn.textContent = audioPlayer && !audioPlayer.paused ? "⏸" : "▶";
  };
  const togglePlayPause = () => {
    if (!audioPlayer) return;
    if (audioPlayer.paused) { audioPlayer.play().catch(() => {}); }
    else { audioPlayer.pause(); }
    _refreshPlayBtn();
  };
  const onPlay  = _refreshPlayBtn;
  const onPause = _refreshPlayBtn;
  const onEnded = _refreshPlayBtn;
  const onVolume = () => { if (audioPlayer && wfVolume) audioPlayer.volume = wfVolume.value; };

  // Spacebar shortcut — gated by checkbox, persisted in localStorage
  const wfSpaceBox = document.getElementById("wf-space-enabled");
  if (wfSpaceBox) {
    const saved = localStorage.getItem("wf_space_enabled");
    wfSpaceBox.checked = saved === null ? true : saved === "1";
  }
  const onSpaceToggle = () => {
    if (wfSpaceBox) localStorage.setItem("wf_space_enabled", wfSpaceBox.checked ? "1" : "0");
  };
  const onKeydown = (ev) => {
    if (ev.code !== "Space" && ev.key !== " ") return;
    if (!wfSpaceBox || !wfSpaceBox.checked) return;
    const t = ev.target;
    const tag = (t && t.tagName) ? t.tagName.toUpperCase() : "";
    if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || (t && t.isContentEditable)) return;
    ev.preventDefault();
    togglePlayPause();
  };

  wfPlayBtn?.addEventListener("click", togglePlayPause);
  audioPlayer?.addEventListener("play",  onPlay);
  audioPlayer?.addEventListener("pause", onPause);
  audioPlayer?.addEventListener("ended", onEnded);
  audioPlayer?.addEventListener("timeupdate", _updateWfTime);
  audioPlayer?.addEventListener("durationchange", _updateWfTime);
  wfVolume?.addEventListener("input", onVolume);
  wfSpaceBox?.addEventListener("change", onSpaceToggle);
  document.addEventListener("keydown", onKeydown);

  // Keep waveform progress in sync with audio player
  audioPlayer?.addEventListener("timeupdate", _syncWaveformToPlayer);

  _refreshPlayBtn();
  _wfHandlers = { togglePlayPause, onPlay, onPause, onEnded, onVolume, onSpaceToggle, onKeydown, _updateWfTime };

}

function _syncWaveformToPlayer() {
  if (_wavesurferSeeking || !_wavesurfer) return;
  const ap  = document.getElementById("audio-player");
  if (!ap || !ap.duration) return;
  _wavesurfer.seekTo(ap.currentTime / ap.duration);
}

function _destroyWaveform() {
  const ap = document.getElementById("audio-player");
  ap?.removeEventListener("timeupdate", _syncWaveformToPlayer);
  if (_wfHandlers) {
    const btn = document.getElementById("wf-play-pause");
    const vol = document.getElementById("wf-volume");
    const spc = document.getElementById("wf-space-enabled");
    btn?.removeEventListener("click", _wfHandlers.togglePlayPause);
    ap?.removeEventListener("play",  _wfHandlers.onPlay);
    ap?.removeEventListener("pause", _wfHandlers.onPause);
    ap?.removeEventListener("ended", _wfHandlers.onEnded);
    ap?.removeEventListener("timeupdate", _wfHandlers._updateWfTime);
    ap?.removeEventListener("durationchange", _wfHandlers._updateWfTime);
    vol?.removeEventListener("input", _wfHandlers.onVolume);
    spc?.removeEventListener("change", _wfHandlers.onSpaceToggle);
    document.removeEventListener("keydown", _wfHandlers.onKeydown);
    _wfHandlers = null;
  }
  if (_wavesurfer) {
    try { _wavesurfer.destroy(); } catch (_) {}
    _wavesurfer = null;
  }
  const wrap = document.getElementById("waveform-wrap");
  if (wrap) wrap.classList.add("hidden");
  // Restore native <audio> element + model badge
  const ap2 = document.getElementById("audio-player");
  if (ap2) ap2.style.display = "";
  const modelBadgeWf2 = document.getElementById("audio-model-badge");
  if (modelBadgeWf2) modelBadgeWf2.style.display = "";
  const wfCtrl2 = document.getElementById("waveform-controls");
  if (wfCtrl2) { wfCtrl2.style.display = "none"; }
  _wfZoom = 1;
}

// Peaks cache in localStorage — avoids re-decoding audio on every load
function _loadWaveformPeaks(tid) {
  try {
    const raw = localStorage.getItem(`wf_peaks_${tid}`);
    return raw ? JSON.parse(raw) : undefined;
  } catch (_) { return undefined; }
}

// After WaveSurfer decodes audio it can export peaks for caching
// (called lazily after ready event — only if peaks weren't already cached)
function _cacheWaveformPeaks(tid) {
  if (!_wavesurfer) return;
  const key = `wf_peaks_${tid}`;
  if (localStorage.getItem(key)) return;  // already cached
  try {
    const peaks = _wavesurfer.exportPeaks();
    localStorage.setItem(key, JSON.stringify(peaks));
  } catch (_) {}
}

document.getElementById("waveform-zoom-in")?.addEventListener("click", () => {
  if (!_wavesurfer) return;
  _wfZoom = Math.min(_wfZoom * 2, 256);
  _wavesurfer.zoom(_wfZoom);
});
document.getElementById("waveform-zoom-out")?.addEventListener("click", () => {
  if (!_wavesurfer) return;
  _wfZoom = Math.max(_wfZoom / 2, 1);
  _wavesurfer.zoom(_wfZoom);
});

// ---------------------------------------------------------------------------
// Analysis View
// ---------------------------------------------------------------------------

let _analysisLastCounter = -1;

document.getElementById("btn-view-coding").addEventListener("click", () => toggleView("coding"));
document.getElementById("btn-view-analysis").addEventListener("click", () => toggleView("analysis"));

function toggleView(view) {
  const isCoding = view === "coding";
  _analysisActive = !isCoding;

  // Toggle buttons
  document.getElementById("btn-view-coding").classList.toggle("active", isCoding);
  document.getElementById("btn-view-analysis").classList.toggle("active", !isCoding);

  // Toggle coding view elements
  ["sidebar-left", "handle-left", "editor-pane", "handle-right", "sidebar-right"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.toggle("hidden", !isCoding);
  });

  // Toggle analysis view
  document.getElementById("analysis-view").classList.toggle("hidden", isCoding);

  if (!isCoding) {
    if (!_analysisData || _annChangeCounter !== _analysisLastCounter) {
      loadAnalysisData();
    }
  }
}

async function loadAnalysisData() {
  const content = document.getElementById("analysis-content");
  content.innerHTML = '<div class="analysis-empty">Laddar…</div>';
  try {
    _analysisData = await GET("/api/analysis/excerpts");
    _analysisLastCounter = _annChangeCounter;
    renderAnalysisCodebook();
    renderAnalysisContent();
  } catch (e) {
    content.innerHTML = '<div class="analysis-empty">Kunde inte ladda data.</div>';
  }
}

function renderAnalysisCodebook() {
  const container = document.getElementById("analysis-codebook-tree");
  container.innerHTML = "";
  if (!_analysisData || !project) return;

  const codes = project.codes || [];
  const tree = buildTree(codes);
  if (numberingEnabled) assignNumbers(tree, "");
  const counts = _analysisData.code_counts || {};

  function renderNode(node, depth) {
    const item = document.createElement("div");
    item.className = "analysis-code-item";
    if (!counts[node.id]) item.classList.add("no-excerpts");
    item.style.paddingLeft = (depth * 14 + 12) + "px";

    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = _analysisState.selectedCodes.has(node.id);
    cb.addEventListener("change", () => onAnalysisCodeToggle(node.id, cb.checked, node));

    const dot = document.createElement("span");
    dot.className = "code-dot";
    dot.style.background = node.color || "#888";
    dot.style.width = "10px";
    dot.style.height = "10px";

    const name = document.createElement("span");
    const numPfx = (numberingEnabled && node.number) ? `${node.number}. ` : "";
    name.textContent = numPfx + node.name;

    const count = document.createElement("span");
    count.className = "analysis-code-count";
    count.textContent = counts[node.id] || "—";

    item.appendChild(cb);
    item.appendChild(dot);
    item.appendChild(name);
    item.appendChild(count);
    container.appendChild(item);

    if (node.children) node.children.forEach(c => renderNode(c, depth + 1));
  }

  tree.forEach(n => renderNode(n, 0));
}

function _getDescendantIds(node) {
  const ids = [];
  if (node.children) {
    for (const c of node.children) {
      ids.push(c.id);
      ids.push(..._getDescendantIds(c));
    }
  }
  return ids;
}

function onAnalysisCodeToggle(codeId, checked, node) {
  if (checked) {
    _analysisState.selectedCodes.add(codeId);
  } else {
    _analysisState.selectedCodes.delete(codeId);
  }
  // Propagate to children
  if (node) {
    const childIds = _getDescendantIds(node);
    for (const id of childIds) {
      if (checked) _analysisState.selectedCodes.add(id);
      else _analysisState.selectedCodes.delete(id);
    }
    // Update checkbox states in DOM
    document.querySelectorAll("#analysis-codebook-tree .analysis-code-item input[type='checkbox']").forEach(cb => {
      const item = cb.closest(".analysis-code-item");
      const dot = item?.querySelector(".code-dot");
      // Find code by matching — re-render is simpler
    });
    renderAnalysisCodebook();
  }
  renderAnalysisContent();
}

function filterAnalysisExcerpts() {
  if (!_analysisData) return [];
  let excerpts = _analysisData.excerpts;
  const sel = _analysisState.selectedCodes;
  if (sel.size > 0) {
    excerpts = excerpts.filter(e => sel.has(e.code_id));
  } else {
    return [];
  }
  if (_analysisState.anchorOnly) {
    excerpts = excerpts.filter(e => e.anchor);
  }
  if (_analysisState.searchQuery) {
    const q = _analysisState.searchQuery.toLowerCase();
    excerpts = excerpts.filter(e =>
      (e.text && e.text.toLowerCase().includes(q)) ||
      (e.memo && e.memo.toLowerCase().includes(q)) ||
      (e.transcript_name && e.transcript_name.toLowerCase().includes(q))
    );
  }
  return excerpts;
}

function _highlightText(text, query) {
  if (!query) return esc(text);
  const lower = text.toLowerCase();
  const ql = query.toLowerCase();
  let result = "";
  let pos = 0;
  let idx;
  while ((idx = lower.indexOf(ql, pos)) !== -1) {
    result += esc(text.slice(pos, idx));
    result += `<mark>${esc(text.slice(idx, idx + query.length))}</mark>`;
    pos = idx + query.length;
  }
  result += esc(text.slice(pos));
  return result;
}

function _updateAnalysisExportButton() {
  const btn = document.getElementById("btn-analysis-export");
  // Always enable — "Exportera allt" and "Alla nyckelpassager" work without code selection
  btn.disabled = false;
  btn.title = "";
}

function renderAnalysisContent() {
  const container = document.getElementById("analysis-content");
  const excerpts = filterAnalysisExcerpts();
  const mode = _analysisState.displayMode;
  const showMemos = _analysisState.showMemos;
  const exportMode = _analysisState.exportMode;
  const searchQ = _analysisState.searchQuery;

  _updateAnalysisExportButton();

  if (_analysisState.selectedCodes.size === 0) {
    container.innerHTML = '<div class="analysis-empty">Välj koder i kodboken till vänster för att visa utdrag.</div>';
    return;
  }
  if (excerpts.length === 0) {
    container.innerHTML = '<div class="analysis-empty">Inga utdrag matchar filtren.</div>';
    return;
  }

  container.innerHTML = "";

  if (mode === "separate") {
    renderCodeInCodeMode(container, excerpts, showMemos, exportMode, searchQ);
  } else {
    renderSeparateMode(container, excerpts, showMemos, exportMode, searchQ);
  }
}

function _createExcerptCard(e, showMemos, exportMode, searchQ) {
  const card = document.createElement("div");
  card.className = "analysis-excerpt-card";
  card.dataset.excerptId = e.id;
  if (e.anchor) card.classList.add("anchor-card");

  const header = document.createElement("div");
  header.className = "analysis-excerpt-header";
  if (e.anchor) {
    const pin = document.createElement("span");
    pin.className = "anchor-icon";
    pin.textContent = "📌";
    header.appendChild(pin);
  }
  const label = document.createElement("span");
  label.textContent = `${e.transcript_label}. ${e.transcript_name} — ${e.coder}`;
  header.appendChild(label);
  card.appendChild(header);

  const text = document.createElement("div");
  text.className = "analysis-excerpt-text";
  text.innerHTML = _highlightText(e.text || "", searchQ);
  card.appendChild(text);

  if (showMemos && e.memo) {
    const memo = document.createElement("div");
    memo.className = "analysis-excerpt-memo";
    memo.innerHTML = _highlightText(e.memo, searchQ);
    card.appendChild(memo);
  }

  if (exportMode) {
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.className = "analysis-excerpt-checkbox";
    cb.checked = _analysisState.selectedExcerpts.has(e.id);
    cb.addEventListener("change", () => {
      if (cb.checked) _analysisState.selectedExcerpts.add(e.id);
      else _analysisState.selectedExcerpts.delete(e.id);
    });
    card.appendChild(cb);
  }

  return card;
}

function renderSeparateMode(container, excerpts, showMemos, exportMode, searchQ) {
  // Kod-i-kod (inline) mode: show text passages with overlapping code
  // highlights rendered inline, similar to the coding view.
  // Group overlapping excerpts from the same transcript region into one
  // merged block where each code's color appears as an inline highlight.

  if (!excerpts.length) return;

  const codes = (project && project.codes) || [];
  const codeMap = {};
  codes.forEach(c => codeMap[c.id] = c);

  // Group excerpts by transcript + overlapping region
  // Key: transcript_id. Within each transcript, merge overlapping ranges.
  const byTranscript = {};
  const transcriptOrder = [];
  for (const e of excerpts) {
    if (!byTranscript[e.transcript_id]) {
      byTranscript[e.transcript_id] = [];
      transcriptOrder.push(e.transcript_id);
    }
    byTranscript[e.transcript_id].push(e);
  }

  for (const tid of transcriptOrder) {
    const group = byTranscript[tid];
    // Sort by start position
    group.sort((a, b) => a.start - b.start || a.end - b.end);

    // Merge overlapping excerpts into clusters
    const clusters = [];
    let cur = null;
    for (const e of group) {
      if (cur && e.start < cur.end) {
        // Overlapping — extend cluster
        cur.end = Math.max(cur.end, e.end);
        cur.excerpts.push(e);
      } else {
        cur = { start: e.start, end: e.end, excerpts: [e] };
        clusters.push(cur);
      }
    }

    for (const cluster of clusters) {
      const exs = cluster.excerpts;
      const first = exs[0];

      // Build the full text span for this cluster
      let fullText = "";
      let minStart = Infinity, maxEnd = -Infinity;
      for (const e of exs) {
        if (e.start < minStart) minStart = e.start;
        if (e.end > maxEnd) maxEnd = e.end;
        if (e.text && e.text.length > fullText.length) fullText = e.text;
      }

      const card = document.createElement("div");
      card.className = "analysis-excerpt-card code-inline-card";
      if (exs.some(e => e.anchor)) card.classList.add("anchor-card");

      // Header: transcript label + code legend
      const header = document.createElement("div");
      header.className = "analysis-excerpt-header";
      if (exs.some(e => e.anchor)) {
        const pin = document.createElement("span");
        pin.className = "anchor-icon";
        pin.textContent = "\ud83d\udccc";
        header.appendChild(pin);
      }
      const label = document.createElement("span");
      label.textContent = `${first.transcript_label}. ${first.transcript_name} \u2014 ${first.coder}`;
      header.appendChild(label);
      card.appendChild(header);

      // Code legend showing which codes are in this cluster
      const legend = document.createElement("div");
      legend.className = "code-inline-legend";
      const seenCodes = new Set();
      for (const e of exs) {
        if (seenCodes.has(e.code_id)) continue;
        seenCodes.add(e.code_id);
        const chip = document.createElement("span");
        chip.className = "code-inline-chip";
        const alpha = Math.round(255 * 0.28).toString(16).padStart(2, "0");
        chip.style.background = (e.code_color || "#888") + alpha;
        chip.style.borderBottom = `2px solid ${e.code_color || "#888"}`;
        const numPfx = (numberingEnabled && e.code_number) ? `${e.code_number}. ` : "";
        chip.textContent = numPfx + e.code_name;
        legend.appendChild(chip);
      }
      card.appendChild(legend);

      // Text body with inline highlights
      const textEl = document.createElement("div");
      textEl.className = "analysis-excerpt-text";

      if (exs.length === 1) {
        // Single code — just show text with that code's highlight
        const alpha = Math.round(255 * 0.28).toString(16).padStart(2, "0");
        textEl.innerHTML = `<span style="background:${first.code_color || "#888"}${alpha}; box-shadow:0 2px 0 0 ${first.code_color || "#888"}">${_highlightText(fullText, searchQ)}</span>`;
      } else {
        // Multiple overlapping codes — build highlighted segments
        // Normalize all positions relative to the cluster start
        const base = minStart;
        const textLen = fullText.length;

        // Boundary-based highlighting like buildHighlightedHTML
        const pts = new Set([0, textLen]);
        for (const e of exs) {
          const s = Math.max(0, e.start - base);
          const en = Math.min(textLen, e.end - base);
          if (s < en) { pts.add(s); pts.add(en); }
        }
        const boundaries = [...pts].sort((a, b) => a - b);

        let html = "";
        for (let i = 0; i < boundaries.length - 1; i++) {
          const segS = boundaries[i];
          const segE = boundaries[i + 1];
          const seg = fullText.slice(segS, segE);
          const absS = base + segS;
          const absE = base + segE;

          const covering = exs.filter(e => e.start <= absS && e.end >= absE);

          if (!covering.length) {
            html += _highlightText(seg, searchQ);
            continue;
          }

          const primary = covering[0];
          const alpha = Math.round(255 * 0.28).toString(16).padStart(2, "0");
          const color0 = primary.code_color || "#888";

          const shadows = covering.map((a, idx) => {
            const col = a.code_color || "#888";
            return `0 ${2 + idx * 3}px 0 0 ${col}`;
          }).join(", ");

          const titles = covering.map(a => a.code_name).join(", ");
          html += `<span style="background:${color0}${alpha}; box-shadow:${shadows};" title="${escAttr(titles)}">${_highlightText(seg, searchQ)}</span>`;
        }
        textEl.innerHTML = html;
      }
      card.appendChild(textEl);

      // Memos
      if (showMemos) {
        for (const e of exs) {
          if (e.memo) {
            const memo = document.createElement("div");
            memo.className = "analysis-excerpt-memo";
            const codeLabel = e.code_name ? `[${e.code_name}] ` : "";
            memo.innerHTML = codeLabel + _highlightText(e.memo, searchQ);
            card.appendChild(memo);
          }
        }
      }

      // Export checkbox
      if (exportMode) {
        const cb = document.createElement("input");
        cb.type = "checkbox";
        cb.className = "analysis-excerpt-checkbox";
        cb.checked = exs.some(e => _analysisState.selectedExcerpts.has(e.id));
        cb.addEventListener("change", () => {
          for (const e of exs) {
            if (cb.checked) _analysisState.selectedExcerpts.add(e.id);
            else _analysisState.selectedExcerpts.delete(e.id);
          }
        });
        card.appendChild(cb);
      }

      container.appendChild(card);
    }
  }
}

function renderCodeInCodeMode(container, excerpts, showMemos, exportMode, searchQ) {
  if (!project) return;
  const codes = project.codes || [];
  const tree = buildTree(codes);
  if (numberingEnabled) assignNumbers(tree, "");

  const byCode = {};
  for (const e of excerpts) {
    if (!byCode[e.code_id]) byCode[e.code_id] = [];
    byCode[e.code_id].push(e);
  }

  function hasExcerpts(node) {
    if (byCode[node.id]) return true;
    return (node.children || []).some(c => hasExcerpts(c));
  }

  function renderTree(nodes, parentEl) {
    for (const node of nodes) {
      if (!hasExcerpts(node)) continue;
      const heading = document.createElement("div");
      heading.className = "analysis-code-heading";
      const dot = document.createElement("span");
      dot.className = "code-dot";
      dot.style.background = node.color || "#888";
      heading.appendChild(dot);
      const numPfx = (numberingEnabled && node.number) ? `${node.number}. ` : "";
      const nameEl = document.createElement("span");
      nameEl.textContent = numPfx + node.name;
      heading.appendChild(nameEl);
      if (byCode[node.id]) {
        const count = document.createElement("span");
        count.className = "code-count";
        count.textContent = `(${byCode[node.id].length})`;
        heading.appendChild(count);
      }
      parentEl.appendChild(heading);

      if (byCode[node.id]) {
        for (const e of byCode[node.id]) {
          parentEl.appendChild(_createExcerptCard(e, showMemos, exportMode, searchQ));
        }
      }
      if (node.children && node.children.length) {
        const childGroup = document.createElement("div");
        childGroup.className = "analysis-child-group";
        renderTree(node.children, childGroup);
        if (childGroup.children.length) parentEl.appendChild(childGroup);
      }
    }
  }

  renderTree(tree, container);
}

// Toolbar event listeners
document.querySelectorAll('input[name="analysis-display"]').forEach(r => {
  r.addEventListener("change", () => {
    _analysisState.displayMode = r.value;
    renderAnalysisContent();
  });
});

document.getElementById("analysis-show-memos").addEventListener("change", (e) => {
  _analysisState.showMemos = e.target.checked;
  renderAnalysisContent();
});

document.getElementById("analysis-anchor-only").addEventListener("change", (e) => {
  _analysisState.anchorOnly = e.target.checked;
  renderAnalysisContent();
});

document.getElementById("analysis-export-mode").addEventListener("change", (e) => {
  _analysisState.exportMode = e.target.checked;
  _analysisState.selectedExcerpts.clear();
  renderAnalysisContent();
});

let _analysisSearchTimer = null;
document.getElementById("analysis-search").addEventListener("input", (e) => {
  clearTimeout(_analysisSearchTimer);
  _analysisSearchTimer = setTimeout(() => {
    _analysisState.searchQuery = e.target.value.trim();
    renderAnalysisContent();
  }, 200);
});

// Select all / none
document.getElementById("btn-analysis-all").addEventListener("click", () => {
  if (!project) return;
  _analysisState.selectedCodes = new Set((project.codes || []).map(c => c.id));
  renderAnalysisCodebook();
  renderAnalysisContent();
});
document.getElementById("btn-analysis-none").addEventListener("click", () => {
  _analysisState.selectedCodes.clear();
  renderAnalysisCodebook();
  renderAnalysisContent();
});

// Export
document.getElementById("btn-analysis-export").addEventListener("click", () => {
  document.getElementById("modal-analysis-export").classList.remove("hidden");
  document.getElementById("analysis-export-status").textContent = "";
  // Enable/disable the "excerpts" radio based on export mode
  const excerptRadio = document.querySelector('input[name="analysis-export-type"][value="excerpts"]');
  if (excerptRadio) excerptRadio.disabled = !_analysisState.exportMode;
  // Default to "codes" selection
  const codesRadio = document.querySelector('input[name="analysis-export-type"][value="codes"]');
  if (codesRadio) codesRadio.checked = true;
});

document.getElementById("btn-analysis-export-close").addEventListener("click", () => {
  document.getElementById("modal-analysis-export").classList.add("hidden");
});

document.querySelectorAll(".analysis-fmt-btn").forEach(btn => {
  btn.addEventListener("click", () => doAnalysisExport(btn.dataset.format));
});

async function doAnalysisExport(format) {
  const statusEl = document.getElementById("analysis-export-status");
  const exportType = document.querySelector('input[name="analysis-export-type"]:checked')?.value || "codes";

  if (format === "pdf") {
    window.print();
    return;
  }

  if (format === "png") {
    statusEl.textContent = "Genererar PNG…";
    try {
      if (!window.html2canvas) {
        await new Promise((resolve, reject) => {
          const s = document.createElement("script");
          s.src = "https://html2canvas.hertzen.com/dist/html2canvas.min.js";
          s.onload = resolve; s.onerror = reject;
          document.head.appendChild(s);
        });
      }
      const el = document.getElementById("analysis-content");
      // Apply print-like light-theme styles for clean PNG output
      const prevHeight = el.style.maxHeight;
      const prevOverflow = el.style.overflow;
      el.classList.add("png-export-ready");
      el.style.maxHeight = "none";
      el.style.overflow = "visible";
      // Allow layout to settle before capture
      await new Promise(r => setTimeout(r, 50));
      const canvas = await html2canvas(el, { backgroundColor: "#ffffff", scale: 2, useCORS: true });
      // Restore original styles
      el.classList.remove("png-export-ready");
      el.style.maxHeight = prevHeight;
      el.style.overflow = prevOverflow;
      const link = document.createElement("a");
      link.download = "analys.png";
      link.href = canvas.toDataURL("image/png");
      link.click();
      statusEl.textContent = "PNG exporterad.";
    } catch (e) {
      const el2 = document.getElementById("analysis-content");
      el2.classList.remove("png-export-ready");
      el2.style.maxHeight = "";
      el2.style.overflow = "";
      statusEl.textContent = "Kunde inte generera PNG.";
    }
    return;
  }

  statusEl.textContent = "Exporterar…";
  const body = {
    format,
    mode: _analysisState.displayMode,
    anchor_only: false,
  };

  if (exportType === "all") {
    // Export all coded segments — no code/excerpt filter, no anchor filter
    body.anchor_only = false;
  } else if (exportType === "key") {
    // Export key passages only — force anchor_only, no code/excerpt filter
    body.anchor_only = true;
  } else if (exportType === "excerpts" && _analysisState.exportMode) {
    body.excerpt_ids = [..._analysisState.selectedExcerpts];
  } else {
    // "codes" — export selected codes
    body.code_ids = [..._analysisState.selectedCodes];
  }

  try {
    const res = await fetch("/api/analysis/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json();
      statusEl.textContent = err.error || "Export misslyckades.";
      return;
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const cd = res.headers.get("content-disposition") || "";
    const fnMatch = cd.match(/filename=(.+)/);
    link.download = fnMatch ? fnMatch[1] : `analys.${format}`;
    link.href = url;
    link.click();
    URL.revokeObjectURL(url);
    statusEl.textContent = "Export klar.";
  } catch (e) {
    statusEl.textContent = "Export misslyckades.";
  }
}
