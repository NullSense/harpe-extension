# Harpe Browser Extension

A Manifest V3 browser extension that scans the **rendered DOM** of the current tab for images (including JS-injected and lazy-loaded ones, using your authenticated browser session), lets you pick images in a visual grid, and downloads them.

**It works with zero setup.** By default downloads happen in-browser via the
`chrome.downloads` API — no Python, no native host, nothing to install beyond the
extension itself. Files land in `Downloads/harpe/<site>/`.

The optional **Harpe engine** (a small local helper) unlocks saving to *any*
folder, plus video and gigapixel/IIIF downloads. It's **auto-detected** — if the
helper is installed the extension uses it automatically (the ⚙ settings show
"engine connected"); if not, it stays in built-in mode. No toggle. Everything
below describes installing that optional helper.

> Why a helper at all? A browser extension is sandboxed: it physically cannot
> save outside the Downloads folder or run external programs (yt-dlp for video,
> dezoomify for gigapixel). Every tool of this kind (1Password, KeePassXC, video
> downloaders) ships a small local helper for exactly this reason. Image
> grabbing needs no helper; only those two extras do.

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

### Just the extension (no setup)

Load `extension/` (see Step 3 below) or install from the store. Done — finding
and grabbing **images and direct/X-Twitter videos** works immediately, saving to
`Downloads/harpe/<site>/`. This needs no native software and a lean permission
set (`nativeMessaging` is **not** requested here).

### Optional: the Harpe engine (save anywhere, per-type folders, yt-dlp video)

Only needed if you click **"Enable Harpe engine"** in settings — that requests
the optional `nativeMessaging` permission on the spot, then talks to a small
local helper. Harpe has a **stable extension ID** baked into `manifest.json` (via
the `"key"` field), so the native host only has to be registered once — no
per-load ID juggling.

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

The committed `extension/manifest.json` is **Chrome-native** (service-worker
background, side panel) so this loads warning-free.

**Firefox / Zen / LibreWolf:** Firefox needs its own manifest variant (it has no
service-worker background and uses a native sidebar instead of the side panel),
so build it first and load the zip:

```sh
scripts/package.sh        # → dist/harpe-firefox-<ver>.zip
```

`about:debugging#/runtime/this-firefox` → **Load Temporary Add-on…** → pick
`dist/harpe-firefox-<ver>.zip`. The ID comes from
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
   unpacked" for dev). $5 one-time Chrome developer registration; build the
   package with `scripts/package.sh`, fill the listing, justify the `<all_urls>`
   host permission (see [`PRIVACY.md`](PRIVACY.md) — nothing is sent to us), and
   submit for review. `nativeMessaging` is an **optional** permission requested
   only when the user enables the engine, so the base listing stays lean.
2. **Helper** — one command: `host/install.sh` (or `install_host.bat`). The
   popup links here automatically when the helper is missing.

### Building the store packages

```sh
scripts/package.sh        # → dist/harpe-chrome-<ver>.zip + dist/harpe-firefox-<ver>.zip
```

The committed `extension/manifest.json` is **Chrome-native** (so "Load unpacked"
is warning-free in Chrome). `package.sh` produces a **tailored zip per store** —
a single cross-browser MV3 manifest can't satisfy both (Chrome rejects
`background.scripts`; Firefox has no service-worker background). Each build:

- **Chrome** — `background.service_worker`, native `side_panel`, one toolbar
  button. Drops the dev-only `key` and the Gecko-only keys.
- **Firefox** — `background.scripts` (event page), native `sidebar_action`, the
  `browser_specific_settings.gecko.id`; drops `side_panel`/`action` so there's a
  single sidebar button. `background.js` routes the click per browser.

Both drop the dev-only `"key"` (stores assign their own ID). AMO requires the
add-on be **signed by Mozilla** (automatic on submit). Both stores want a privacy
policy — [`PRIVACY.md`](PRIVACY.md) — and a listing description justifying
`<all_urls>`.

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
| Video  | `~/Videos/harpe/<site>/` | `~/Movies/harpe/<site>/` |
| Audio  | `~/Music/harpe/<site>/` | same |

**Each path is independently configurable.** Click the **⚙ gear** in the popup:

- With the engine installed you get three fields — **Images**, **Videos**,
  **Audio** — each pre-filled with its real default as a placeholder. Set any to
  an absolute path (e.g. `~/Downloads/art`, `$HOME/refs/clips`); `~` and `$VARS`
  are expanded by the native host. Leave a field blank to keep its default.
- Without the engine (built-in mode), only images can be saved, so you get a
  single **Downloads subfolder** field (default `harpe`); files land in
  `Downloads/<subfolder>/<site>/`.

Each non-blank engine path is passed to `harpe` via its `HARPE_IMG_DIR` /
`HARPE_VID_DIR` / `HARPE_AUD_DIR` environment variable; files are still grouped
by source site inside. Choices persist with `chrome.storage`. After a grab the
popup shows where the files landed with an **Open folder** button.

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

The native host wraps this: it receives `{urls, referer, dirs}` from the
extension (plus `{ping}` for liveness and `{open}` to reveal a folder), maps any
per-type `dirs` to the engine's `HARPE_*_DIR` env vars, pipes the URL list to
`harpe`, and returns `{results: […]}` back.

## Privacy

Full policy: [`PRIVACY.md`](PRIVACY.md). In short:

- No telemetry, no analytics, no accounts, no servers operated by us.
- The page is scanned **locally**; the list of found media never leaves the browser.
- The only network calls are to fetch the media you choose, and — only on X/Twitter
  posts — a query to X's public `cdn.syndication.twimg.com` endpoint to locate a
  tweet's downloadable video (just the public tweet ID is sent).
- Images are loaded by the browser (for dimension probing) using your existing
  session — no credentials leave your browser.
- The optional native host only receives URLs you explicitly select and runs
  `harpe` locally.
