/**
 * Harpe popup / side-panel UI.
 *
 * Flow:
 *   1. On load, ask the background to scan the active tab.
 *   2. Render results as a thumbnail grid with dimension badges.
 *   3. User clicks thumbnails to toggle selection; "Select all" / "Clear" helpers.
 *   4. "Grab N" sends selected URLs + page URL to background → native host → harpe.
 *   5. Show per-image result (tick/cross) after the download finishes.
 */

"use strict";

// ── State ────────────────────────────────────────────────────────────────────

let scanResult = null; // { images, pageUrl, pageTitle }
let selected = new Set(); // Set<url string>
let tabId = null;
let grabInProgress = false;
let saveDest = ""; // chosen save folder
let useEngine = false; // false = built-in chrome.downloads; true = native host

// ── DOM refs ─────────────────────────────────────────────────────────────────

const $status = document.getElementById("status");
const $grid = document.getElementById("grid");
const $btnSelectAll = document.getElementById("btn-select-all");
const $btnClear = document.getElementById("btn-clear");
const $btnGrab = document.getElementById("btn-grab");
const $btnRescan = document.getElementById("btn-rescan");
const $pageTitle = document.getElementById("page-title");
const $count = document.getElementById("count");
const $hostHint = document.getElementById("host-hint");

// A grab error means the native helper is missing/unreachable when the message
// mentions the host or the connection (vs. a normal per-image download failure).
function looksLikeHostError(msg) {
  return /native (messaging )?host|not found|connect to native|disconnected|host not|No such file/i.test(
    String(msg || "")
  );
}
const $btnSettings = document.getElementById("btn-settings");
const $settings = document.getElementById("settings");
const $dest = document.getElementById("dest");
const $destLabel = document.getElementById("dest-label");
const $settingsHelp = document.getElementById("settings-help");
const $useEngine = document.getElementById("use-engine");
const $btnSaveSettings = document.getElementById("btn-save-settings");
const $settingsStatus = document.getElementById("settings-status");

// ── Settings (save folder + download mode) ─────────────────────────────────────

function applyMode() {
  if (useEngine) {
    $destLabel.textContent = "Save to (absolute folder)";
    $dest.placeholder = "~/Pictures/harpe  (blank = engine default)";
    $settingsHelp.innerHTML =
      "Downloads via the local Harpe engine to any folder " +
      "(<code>~</code> and <code>$VARS</code> allowed). Also enables video &amp; gigapixel.";
  } else {
    $destLabel.textContent = "Save to (subfolder of Downloads)";
    $dest.placeholder = "harpe  (organised by site)";
    $settingsHelp.innerHTML =
      "Images download to your <code>Downloads</code> folder, grouped by site. No setup needed.";
  }
}

async function loadSettings() {
  try {
    const { dest, useEngine: ue } = await chrome.storage.local.get(["dest", "useEngine"]);
    saveDest = typeof dest === "string" ? dest : "";
    useEngine = Boolean(ue);
    $dest.value = saveDest;
    $useEngine.checked = useEngine;
  } catch {
    saveDest = ""; useEngine = false;
  }
  applyMode();
}

async function saveSettings() {
  saveDest = $dest.value.trim();
  useEngine = $useEngine.checked;
  try {
    await chrome.storage.local.set({ dest: saveDest, useEngine });
    $settingsStatus.textContent = useEngine
      ? (saveDest ? `Engine → ${saveDest}` : "Engine → default folders")
      : (saveDest ? `Downloads/${saveDest}/<site>/` : "Downloads/harpe/<site>/");
    $settingsStatus.hidden = false;
    setTimeout(() => { $settingsStatus.hidden = true; }, 2600);
  } catch (e) {
    $settingsStatus.textContent = "Could not save: " + e.message;
    $settingsStatus.hidden = false;
  }
}

function toggleSettings() {
  const open = $settings.hidden;
  $settings.hidden = !open;
  $btnSettings.setAttribute("aria-expanded", String(open));
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function setStatus(msg, cls = "") {
  $status.textContent = msg;
  $status.className = "status " + cls;
}

function updateControls() {
  const n = selected.size;
  $btnGrab.textContent = n > 0 ? `Grab ${n}` : "Grab";
  $btnGrab.disabled = n === 0 || grabInProgress;
  $count.textContent =
    scanResult ? `${scanResult.images.length} images found` : "";
}

function fmtDims(w, h) {
  if (!w && !h) return "? × ?";
  return `${w} × ${h}`;
}

function fmtArea(area) {
  if (!area) return "";
  if (area >= 1_000_000) return `${(area / 1_000_000).toFixed(1)} MP`;
  if (area >= 1_000) return `${(area / 1_000).toFixed(0)} kpx`;
  return `${area} px²`;
}

// ── Rendering ────────────────────────────────────────────────────────────────

function renderGrid(images) {
  $grid.innerHTML = "";
  if (!images || images.length === 0) {
    const msg = document.createElement("p");
    msg.className = "empty";
    msg.textContent = "No images found on this page.";
    $grid.appendChild(msg);
    return;
  }

  for (const img of images) {
    const card = document.createElement("div");
    card.className = "card";
    card.dataset.url = img.url;

    const thumb = document.createElement("img");
    thumb.className = "thumb";
    thumb.loading = "lazy";
    thumb.src = img.url;
    thumb.alt = "";
    thumb.onerror = () => {
      thumb.src = ""; // blank on error
      card.classList.add("error");
    };

    const info = document.createElement("div");
    info.className = "info";

    const dimSpan = document.createElement("span");
    dimSpan.className = "dims";
    dimSpan.textContent = fmtDims(img.w, img.h);

    const areaSpan = document.createElement("span");
    areaSpan.className = "area";
    areaSpan.textContent = fmtArea(img.area);

    info.appendChild(dimSpan);
    info.appendChild(areaSpan);

    const checkmark = document.createElement("div");
    checkmark.className = "checkmark";
    checkmark.textContent = "✓";

    card.appendChild(thumb);
    card.appendChild(info);
    card.appendChild(checkmark);

    card.addEventListener("click", () => toggleSelect(img.url, card));

    $grid.appendChild(card);
  }
}

function toggleSelect(url, card) {
  if (selected.has(url)) {
    selected.delete(url);
    card.classList.remove("selected");
  } else {
    selected.add(url);
    card.classList.add("selected");
  }
  updateControls();
}

function selectAll() {
  if (!scanResult) return;
  for (const img of scanResult.images) selected.add(img.url);
  for (const card of $grid.querySelectorAll(".card"))
    card.classList.add("selected");
  updateControls();
}

function clearAll() {
  selected.clear();
  for (const card of $grid.querySelectorAll(".card"))
    card.classList.remove("selected");
  updateControls();
}

// ── Scan ─────────────────────────────────────────────────────────────────────

async function doScan() {
  selected.clear();
  $grid.innerHTML = "";
  setStatus("Scanning page…", "scanning");
  $btnRescan.disabled = true;
  $btnGrab.disabled = true;
  $pageTitle.textContent = "";
  $count.textContent = "";

  try {
    if (!tabId) {
      const [tab] = await chrome.tabs.query({
        active: true,
        currentWindow: true,
      });
      tabId = tab?.id;
    }
    if (!tabId) throw new Error("No active tab");

    const result = await chrome.runtime.sendMessage({
      type: "HARPE_SCAN_REQUEST",
      tabId,
    });

    if (!result?.ok) throw new Error(result?.error || "Scan failed");

    scanResult = result;
    $pageTitle.textContent = result.pageTitle || result.pageUrl;
    renderGrid(result.images);
    setStatus(
      result.images.length
        ? "Click images to select, then Grab."
        : "No images found.",
      result.images.length ? "ok" : "warn"
    );
  } catch (err) {
    setStatus("Error: " + err.message, "error");
  } finally {
    $btnRescan.disabled = false;
    updateControls();
  }
}

// ── Grab ─────────────────────────────────────────────────────────────────────

async function doGrab() {
  if (!scanResult || selected.size === 0 || grabInProgress) return;
  grabInProgress = true;
  $btnGrab.disabled = true;
  $hostHint.hidden = true;
  setStatus(`Downloading ${selected.size} image(s)…`, "scanning");

  // Grey-out non-selected cards
  for (const card of $grid.querySelectorAll(".card")) {
    if (!selected.has(card.dataset.url)) card.classList.add("dim");
  }

  try {
    const urls = [...selected];
    const result = await chrome.runtime.sendMessage({
      type: "HARPE_GRAB",
      urls,
      referer: scanResult.pageUrl,
      useEngine,
      folder: saveDest,
    });

    if (!result) throw new Error("No response from background");

    // Whole-grab failure (e.g. native helper missing) — no per-image results.
    if (result.ok === false && (!result.results || result.results.length === 0)) {
      const msg = result.error || "Grab failed";
      setStatus(msg, "error");
      if (looksLikeHostError(msg)) $hostHint.hidden = false;
      return;
    }

    // Annotate cards with per-image results
    if (result.results) {
      const byUrl = new Map(result.results.map((r) => [r.url, r]));
      for (const card of $grid.querySelectorAll(".card.selected")) {
        const r = byUrl.get(card.dataset.url);
        if (!r) continue;
        const badge = document.createElement("div");
        badge.className = "result-badge " + (r.ok ? "ok" : "fail");
        badge.textContent = r.ok ? "✓" : "✗";
        badge.title = r.ok ? r.path || "Downloaded" : r.error || "Failed";
        card.appendChild(badge);
      }
    }

    const ok = result.results?.filter((r) => r.ok).length ?? 0;
    const fail = (result.results?.length ?? 0) - ok;
    if (fail === 0) {
      setStatus(`Downloaded ${ok} image${ok !== 1 ? "s" : ""}.`, "ok");
    } else if (ok === 0) {
      setStatus(`All ${fail} downloads failed.`, "error");
    } else {
      setStatus(`${ok} downloaded, ${fail} failed.`, "warn");
    }
  } catch (err) {
    setStatus("Grab failed: " + err.message, "error");
    if (looksLikeHostError(err.message)) $hostHint.hidden = false;
  } finally {
    grabInProgress = false;
    // Restore dim cards
    for (const card of $grid.querySelectorAll(".card.dim"))
      card.classList.remove("dim");
    updateControls();
  }
}

// ── Init ─────────────────────────────────────────────────────────────────────

// Extract tabId from URL params (fallback popup mode)
const params = new URLSearchParams(location.search);
if (params.has("tabId")) tabId = parseInt(params.get("tabId"), 10);

$btnSelectAll.addEventListener("click", selectAll);
$btnClear.addEventListener("click", clearAll);
$btnGrab.addEventListener("click", doGrab);
$btnRescan.addEventListener("click", doScan);
$btnSettings.addEventListener("click", toggleSettings);
$btnSaveSettings.addEventListener("click", saveSettings);
$useEngine.addEventListener("change", () => { useEngine = $useEngine.checked; applyMode(); });
$dest.addEventListener("keydown", (e) => { if (e.key === "Enter") saveSettings(); });

function init() {
  loadSettings();
  doScan();
}

document.addEventListener("DOMContentLoaded", init);
// DOMContentLoaded may have already fired (side panel loads synchronously)
if (document.readyState !== "loading") init();
