/**
 * Harpe background service worker (MV3).
 *
 * Responsibilities:
 *   1. Open the side panel when the toolbar icon is clicked.
 *   2. Relay SCAN requests from the popup to the active tab's content script.
 *   3. Accept GRAB requests: forward chosen URLs to the native messaging host,
 *      receive harpe's JSON response, relay it back to the popup, and surface
 *      a browser notification.
 *
 * Native messaging host name: "com.nullsense.harpe"
 * Protocol: Chrome native messaging (4-byte LE length prefix), JSON messages.
 *
 * Outgoing to host: { urls: string[], referer: string, dest?: string }
 * Incoming from host: { results: [{url, ok, path?, error?}, ...] }
 */

"use strict";

const HOST_NAME = "com.nullsense.harpe";

// ── Side panel ───────────────────────────────────────────────────────────────

// Open side panel on icon click (MV3 side panel API)
chrome.action.onClicked.addListener(async (tab) => {
  try {
    // sidePanel.open is available in Chrome 116+
    await chrome.sidePanel.open({ tabId: tab.id });
  } catch (e) {
    // Fallback for browsers that don't support sidePanel (Firefox, older Chrome)
    // Open as a popup window instead
    const url = chrome.runtime.getURL("popup.html") + "?tabId=" + tab.id;
    await chrome.windows.create({
      url,
      type: "popup",
      width: 900,
      height: 700,
    });
  }
});

// Allow the side panel to be shown on any tab
chrome.sidePanel
  ?.setPanelBehavior?.({ openPanelOnActionClick: true })
  .catch(() => {});

// ── Message routing ──────────────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "HARPE_SCAN_REQUEST") {
    handleScan(msg.tabId).then(sendResponse).catch((err) =>
      sendResponse({ ok: false, error: String(err) })
    );
    return true;
  }

  if (msg.type === "HARPE_PING") {
    pingHost().then((m) =>
      sendResponse({ available: !!(m && m.ok), defaults: (m && m.defaults) || null })
    );
    return true;
  }

  if (msg.type === "HARPE_GRAB") {
    handleGrab(msg.urls, msg.referer, { dirs: msg.dirs, folder: msg.folder })
      .then(sendResponse)
      .catch((err) => sendResponse({ ok: false, error: String(err) }));
    return true;
  }

  // Reveal a saved file in its folder. Engine downloads go through the native
  // host (it can open any OS folder); built-in downloads use chrome.downloads.
  if (msg.type === "HARPE_OPEN") {
    openInHost(msg.path).then(sendResponse).catch((err) =>
      sendResponse({ ok: false, error: String(err) })
    );
    return true;
  }
  if (msg.type === "HARPE_OPEN_DOWNLOAD") {
    try {
      chrome.downloads.show(msg.id);
      sendResponse({ ok: true });
    } catch (e) {
      try { chrome.downloads.showDefaultFolder(); sendResponse({ ok: true }); }
      catch (e2) { sendResponse({ ok: false, error: String(e2) }); }
    }
    return false;
  }

  return false;
});

// Ask the native host to reveal a saved path in the OS file manager.
function openInHost(path) {
  return new Promise((resolve) => {
    let done = false;
    const finish = (v) => { if (!done) { done = true; resolve(v); } };
    let port;
    try {
      port = chrome.runtime.connectNative(HOST_NAME);
    } catch (e) {
      return finish({ ok: false, error: String(e) });
    }
    const timer = setTimeout(() => { try { port.disconnect(); } catch {} finish({ ok: true }); }, 2500);
    port.onMessage.addListener((m) => { clearTimeout(timer); try { port.disconnect(); } catch {} finish(m || { ok: true }); });
    port.onDisconnect.addListener(() => { clearTimeout(timer); finish({ ok: false, error: "host disconnected" }); });
    try { port.postMessage({ open: path }); } catch (e) { clearTimeout(timer); finish({ ok: false, error: String(e) }); }
  });
}

// ── Helper detection + routing ────────────────────────────────────────────────

// Probe the native host once. If it answers, the engine is installed and we use
// it automatically (save anywhere + future video/gigapixel); otherwise we fall
// back to the built-in chrome.downloads path. No manual toggle needed.
// Resolves to the host's ping reply ({ok, defaults, ...}) or null if absent.
function pingHost() {
  return new Promise((resolve) => {
    let done = false;
    const finish = (v) => { if (!done) { done = true; resolve(v); } };
    let port;
    try {
      port = chrome.runtime.connectNative(HOST_NAME);
    } catch {
      return finish(null);
    }
    const timer = setTimeout(() => { try { port.disconnect(); } catch {} finish(null); }, 2500);
    port.onMessage.addListener((m) => { clearTimeout(timer); try { port.disconnect(); } catch {} finish(m || null); });
    port.onDisconnect.addListener(() => { clearTimeout(timer); finish(null); });
    try { port.postMessage({ ping: true }); } catch { clearTimeout(timer); finish(null); }
  });
}

async function handleGrab(urls, referer, cfg) {
  // Prefer the engine when the helper is installed; otherwise built-in download.
  const m = await pingHost();
  return m && m.ok
    ? handleGrabHost(urls, referer, cfg.dirs)
    : handleGrabBuiltin(urls, referer, cfg.folder);
}

// ── Built-in downloader (chrome.downloads — no native host) ───────────────────

function safeFilename(url) {
  try {
    const u = new URL(url);
    let base = decodeURIComponent((u.pathname.split("/").pop() || "").split("?")[0]);
    base = base.replace(/[^\w.\- ]+/g, "_").slice(0, 100);
    if (!/\.[a-z0-9]{2,5}$/i.test(base)) base += ".jpg";
    return base || "image.jpg";
  } catch {
    return "image.jpg";
  }
}

// Build a Downloads-relative subfolder: "<folder>/<site>" (no absolute paths,
// no traversal — chrome.downloads rejects those).
function buildSubfolder(folder, referer) {
  let f = (folder || "harpe").trim()
    .replace(/^[/\\]+/, "")
    .replace(/\.\.+/g, "")
    .replace(/[<>:"|?*]+/g, "_");
  try {
    const host = new URL(referer).hostname.replace(/^www\./, "");
    if (host) f += "/" + host;
  } catch { /* no referer */ }
  return f.replace(/\/+/g, "/").replace(/[/\\]+$/, "");
}

function downloadOne(url, filename) {
  return new Promise((resolve) => {
    try {
      chrome.downloads.download({ url, filename, conflictAction: "uniquify" }, (id) => {
        if (chrome.runtime.lastError || id === undefined) {
          resolve({ url, ok: false, error: chrome.runtime.lastError?.message || "download failed" });
        } else {
          resolve({ url, ok: true, path: filename, id });
        }
      });
    } catch (e) {
      resolve({ url, ok: false, error: String(e?.message || e) });
    }
  });
}

async function handleGrabBuiltin(urls, referer, folder) {
  const sub = buildSubfolder(folder, referer);
  const results = [];
  for (const url of urls) {
    results.push(await downloadOne(url, sub ? `${sub}/${safeFilename(url)}` : safeFilename(url)));
  }
  notifyDone(results);
  return { ok: results.every((r) => r.ok), results };
}

// ── Scan ─────────────────────────────────────────────────────────────────────

async function handleScan(tabId) {
  // Ensure content script is injected (handles cases where the tab was opened
  // before the extension was installed, or the tab is a special page).
  try {
    await chrome.scripting.executeScript({
      target: { tabId },
      files: ["js/content.js"],
    });
  } catch {
    // Already injected or restricted page — ignore, carry on.
  }

  const response = await new Promise((resolve, reject) => {
    chrome.tabs.sendMessage(tabId, { type: "HARPE_SCAN" }, (r) => {
      if (chrome.runtime.lastError) reject(new Error(chrome.runtime.lastError.message));
      else resolve(r);
    });
  });

  // Fold any grabbable videos into the image grid (prepended): direct <video>
  // files the content script found, plus X/Twitter MP4s resolved here.
  if (response && response.ok) {
    const vids = [...(response.videos || [])];
    if (response.tweetId) {
      try { vids.push(...await resolveTweetVideos(response.tweetId)); } catch { /* best-effort */ }
    }
    if (vids.length) response.images = [...vids, ...(response.images || [])];
  }
  return response;
}

// X/Twitter public syndication endpoint → MP4 variants. No auth, no yt-dlp; the
// background can fetch cross-origin thanks to <all_urls> host permission.
function tweetToken(id) {
  return ((Number(id) / 1e15) * Math.PI).toString(36).replace(/(0+|\.)/g, "");
}
async function resolveTweetVideos(id) {
  const url = `https://cdn.syndication.twimg.com/tweet-result?id=${id}&token=${tweetToken(id)}&lang=en`;
  const r = await fetch(url, { headers: { Accept: "application/json" } });
  if (!r.ok) return [];
  const j = await r.json();
  const out = [];
  for (const m of (j.mediaDetails || [])) {
    if ((m.type === "video" || m.type === "animated_gif") && m.video_info?.variants) {
      const best = m.video_info.variants
        .filter((v) => v.content_type === "video/mp4" && v.url)
        .sort((a, b) => (b.bitrate || 0) - (a.bitrate || 0))[0];
      if (best) {
        const dm = /\/(\d+)x(\d+)\//.exec(best.url);
        const w = dm ? +dm[1] : 0, h = dm ? +dm[2] : 0;
        out.push({ url: best.url, kind: "video", poster: m.media_url_https || null, w, h, area: w * h });
      }
    }
  }
  return out;
}

// ── Grab ─────────────────────────────────────────────────────────────────────

async function handleGrabHost(urls, referer, dirs) {
  return new Promise((resolve) => {
    let port;
    let responded = false;
    let buffer = "";
    let expectedLength = null;
    let rawBuffer = null; // Uint8Array accumulator for length-prefixed protocol
    let rawOffset = 0;

    function finish(result) {
      if (responded) return;
      responded = true;
      try {
        port.disconnect();
      } catch {}
      resolve(result);
    }

    try {
      port = chrome.runtime.connectNative(HOST_NAME);
    } catch (e) {
      resolve({ ok: false, error: "Could not connect to native host: " + e.message });
      return;
    }

    port.onMessage.addListener((msg) => {
      // Chrome native messaging deserialises JSON for us, so msg is already an object
      if (msg && typeof msg === "object") {
        const ok = Array.isArray(msg.results)
          ? msg.results.every((r) => r.ok !== false)
          : !!msg.ok;
        finish({ ok, results: msg.results, raw: msg });
        notifyDone(msg.results || []);
      } else {
        finish({ ok: false, error: "Unexpected response from native host", raw: msg });
      }
    });

    port.onDisconnect.addListener(() => {
      const err = chrome.runtime.lastError;
      if (!responded) {
        finish({
          ok: false,
          error: err ? err.message : "Native host disconnected unexpectedly",
        });
      }
    });

    // Send the request — Chrome auto-frames with the 4-byte length prefix.
    // `dirs` carries per-type folders (blank entries = harpe's defaults).
    port.postMessage({ urls, referer, dirs: dirs || {} });
  });
}

// ── Notification ─────────────────────────────────────────────────────────────

function notifyDone(results) {
  const ok = results.filter((r) => r.ok).length;
  const fail = results.length - ok;

  // Surface the folder the files landed in (engine returns absolute paths).
  const firstPath = results.find((r) => r.ok && r.path)?.path;
  const folder = firstPath ? dirOf(firstPath) : "";

  let message;
  if (fail === 0) {
    message = `Downloaded ${ok} file${ok !== 1 ? "s" : ""}` + (folder ? ` → ${folder}` : ".");
  } else if (ok === 0) {
    message = `All ${fail} download${fail !== 1 ? "s" : ""} failed.`;
  } else {
    message = `${ok} downloaded, ${fail} failed` + (folder ? ` → ${folder}` : ".");
  }

  chrome.notifications.create({
    type: "basic",
    iconUrl: "icons/icon48.png",
    title: "Harpe",
    message,
  });
}

// Folder portion of a saved path (handles both / and \ separators).
function dirOf(p) {
  const i = Math.max(String(p).lastIndexOf("/"), String(p).lastIndexOf("\\"));
  return i > 0 ? String(p).slice(0, i) : String(p);
}
