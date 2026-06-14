# Harpe Browser Extension

A Manifest V3 browser extension that scans the **rendered DOM** of the current tab for images (including JS-injected and lazy-loaded ones, using your authenticated browser session), lets you pick images in a visual grid, and hands the chosen URLs to the locally-installed **harpe** download engine.

## Architecture

```
Browser tab (content script)
  │  scans live DOM → img/srcset/lazy-attrs/CSS bg/meta/link preload/<a href>
  │  returns: [{url, w, h, area}, …]
  ↓
Background service worker
  │  receives selected URLs + page URL from popup
  │  calls chrome.runtime.connectNative("com.nullsense.harpe")
  ↓
Native messaging host  (host/harpe_host.py)
  │  speaks 4-byte LE length-prefix + UTF-8 JSON protocol
  │  runs: harpe -F - --json --referer <page-url>
  │         stdin = one URL per line
  ↓
harpe engine  (installed via: uv tool install harpe)
  │  downloads with correct UA/Referer/naming/dedup
  │  stdout = JSON: [{url, ok, path|error}, …]
  ↑
Results flow back up through host → background → popup → UI badge per image
```

**Why a native host?** A pure browser extension cannot make arbitrary cross-origin requests with spoofed headers or write files to disk. The native host delegates both concerns to `harpe`, which runs as a trusted local process with full filesystem and network access using the user's desired download settings.

## Prerequisites

1. **harpe** engine installed:
   ```sh
   uv tool install harpe
   ```
   Verify: `harpe --help`

2. **Python 3.8+** (for the native host — already on most systems)

3. **Chrome 116+** or **Firefox 91+** (for side panel / native messaging)

## Directory layout

```
harpe-extension/
├── extension/              ← Load this directory as the unpacked extension
│   ├── manifest.json
│   ├── popup.html
│   ├── css/popup.css
│   ├── js/
│   │   ├── content.js      ← DOM scanner (runs in page context)
│   │   ├── background.js   ← Service worker (scan relay + native messaging)
│   │   └── popup.js        ← Side-panel / popup UI
│   └── icons/
├── host/
│   ├── harpe_host.py                    ← Native messaging host (executable)
│   ├── com.nullsense.harpe.json         ← Chrome host manifest template
│   ├── com.nullsense.harpe.firefox.json ← Firefox host manifest template
│   └── install.sh                       ← Installs host manifests
└── README.md
```

No build step required — the extension is plain vanilla JS (ES2020).

## Installation

Harpe has a **stable extension ID** baked into `manifest.json` (via the `"key"`
field), so the native host only has to be registered once — no per-load ID
juggling.

- Chromium ID: `ginhcamellmffiamggkiaemdklcnechf`
- Firefox ID:  `harpe@nullsense.com`

### Step 1 — Install the `harpe` engine

```sh
uv tool install harpe      # or have `harpe` on PATH / in ~/bin
harpe --help               # verify
```

### Step 2 — Register the native host (one command)

```sh
# macOS / Linux — auto-detects every installed browser, no arguments needed:
host/install.sh

# Windows (Chrome, Chromium, Edge, Brave, Firefox):
host\install_host.bat
```

`install.sh` writes the host manifest into the `NativeMessagingHosts` directory
of each browser it finds (Chrome, Chromium, Brave, Edge, Vivaldi, Helium,
Firefox, LibreWolf, Zen). Useful flags:

| Flag | Effect |
|------|--------|
| _(none)_ | install for all detected browsers using the baked IDs |
| `--all` | also write to browsers that aren't detected yet |
| `--chrome-id <ID>` | additionally allow another Chromium ID (e.g. the Web Store ID once published) |
| `--firefox-id <ID>` | additionally allow another Firefox add-on ID |
| `--uninstall` | remove the host manifest everywhere |

### Step 3 — Load the extension

**Chrome / Chromium / Edge / Brave / Helium:** `chrome://extensions` →
**Developer mode** → **Load unpacked** → pick the `extension/` folder. The ID
will be `ginhcamellmffiamggkiaemdklcnechf` (from the manifest `key`).

**Firefox / Zen / LibreWolf:** `about:debugging#/runtime/this-firefox` →
**Load Temporary Add-on…** → pick `extension/manifest.json`. The ID comes from
`browser_specific_settings.gecko.id`.

### Step 4 — Verify

Open an image-heavy page, click the Harpe icon, pick images, **Grab**. If the
helper isn't reachable the popup shows a setup hint. Test the host directly:

```sh
echo '{"urls":["https://example.com/test.jpg"],"referer":"https://example.com"}' \
  | python3 host/harpe_host.py
```

### Native messaging host manifest locations

| Browser  | OS    | Per-user path |
|----------|-------|---------------|
| Chrome   | Linux | `~/.config/google-chrome/NativeMessagingHosts/` |
| Chromium | Linux | `~/.config/chromium/NativeMessagingHosts/` |
| Chrome   | macOS | `~/Library/Application Support/Google/Chrome/NativeMessagingHosts/` |
| Firefox  | Linux | `~/.mozilla/native-messaging-hosts/` |
| Firefox  | macOS | `~/Library/Application Support/Mozilla/NativeMessagingHosts/` |
| (Chrome/Edge/Brave/Firefox) | Windows | per-user **registry** keys under `HKCU\Software\…\NativeMessagingHosts\com.nullsense.harpe` |

## Distribution

A browser store can ship the *extension*, but **not** the native messaging host:
the store sandbox can't drop a file into `NativeMessagingHosts/` or touch the
registry. So every native-messaging tool (1Password, KeePassXC, Plasma
Integration, …) is **two pieces**: the extension from the store, and a local
helper installed separately. The two-step is unavoidable; the goal is to make
each step a single action:

1. **Extension** — one click from the Chrome Web Store / Firefox AMO (or "Load
   unpacked" for dev). $5 one-time Chrome developer registration; zip the
   `extension/` folder, fill the listing, justify the `nativeMessaging` /
   `<all_urls>` permissions, submit for review. For a helper-dependent tool,
   **"unlisted"** visibility or plain GitHub + Developer mode is often saner.
2. **Helper** — one command: `host/install.sh` (or `install_host.bat`). The
   popup links here automatically when the helper is missing.

**Python vs Rust?** The host can be *any* executable — a Python script (what we
use), a shell script, or a compiled Go/Rust binary. A compiled binary is only
worth it if you want a zero-dependency, single-file helper. Here it's pointless:
`harpe` itself is Python, so Python is already required — the host stays a small
`.py` (with a `.bat` shim on Windows, which needs `.exe`/`.bat`, not `.py`).

### Keeping dev and Web Store IDs the same

The published Chrome Web Store ID is assigned by Google when you first create the
item, and may differ from the baked dev ID. To unify them, after creating the
draft item open **Package → View public key**, copy it into `manifest.json`'s
`"key"`, and re-run `host/install.sh --chrome-id <store-id>` (the host allows
multiple origins, so dev + store IDs can both work).

> **Signing key:** the manifest `"key"` is the *public* half. The matching
> private key lives **outside this repo** at `~/.config/harpe-extension/key.pem`
> (git-ignored). Keep it safe — it's what proves ownership of the ID if you ever
> self-distribute a signed `.crx`. Losing it just means a new ID; leaking it
> lets someone publish under your ID.

## Where files are saved

By default Harpe sorts downloads by media type into per-site subfolders:

| Media  | Default folder | macOS |
|--------|----------------|-------|
| Images | `~/Pictures/harpe/<site>/` | same |
| Video  | `~/Videos/harpe/` | `~/Movies/harpe/` |
| Audio  | `~/Music/harpe/` | same |

The extension downloads images, so they land in `~/Pictures/harpe/<site>/`.

To change it, click the **⚙ gear** in the popup and set **Save images to** an
absolute path (e.g. `~/Downloads/art` or `$HOME/refs`). `~` and `$VARS` are
expanded by the native host. Leave it blank to use the defaults above. The
choice is stored with `chrome.storage` and sent to the host as `dest`, which
passes it to `harpe --dest`.

## Content-script scanning details

The content script runs in the page's own context (`document_idle`), so it sees the fully rendered DOM including JS-injected and lazy-loaded images. It scans:

1. `<img>` — `src`, `srcset`, and lazy-load attributes (`data-src`, `data-lazy-src`, `data-original`, `data-srcset`, `data-lazy-srcset`, `data-echo`, `data-url`, `data-lazy`)
2. `<picture><source>` — `srcset` / `data-srcset`
3. CSS `background-image` — computed style on all elements
4. `<link rel="preload" as="image">`
5. `<meta property="og:image">` / `<meta name="twitter:image">`
6. `<a href>` ending in `.jpg`, `.png`, `.gif`, `.webp`, `.avif`, `.svg`, etc.

All URLs are resolved to absolute, deduplicated, and sorted by pixel area (largest first). Images with a long edge < 100 px are dropped (likely icons/spacers), but the floor is relaxed if it would otherwise produce an empty result set — mirroring harpe's own behaviour.

## Engine contract

```
harpe -F - --json --referer <page-url>
# stdin:  one image URL per line
# stdout: JSON array [{url, ok, path|error}, …]
```

The native host wraps this exactly: it receives `{urls, referer}` from the extension, pipes the URL list to `harpe`, and returns `{results: […]}` back.

## Privacy

- No telemetry, no external network calls from the extension itself.
- Images are loaded by the browser (for dimension probing) using your existing session — no credentials leave your browser.
- The native host only receives URLs you explicitly select and sends them to `harpe` running locally.
