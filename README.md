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
  │  receives selected URLs + page URL + per-type dirs/grouping/metadata from popup
  │  calls chrome.runtime.connectNative("com.nullsense.harpe")
  ↓
Native messaging host  (harpe --native-host)
  │  speaks 4-byte LE length-prefix + UTF-8 JSON protocol, in-process
  │  {urls, referer, dirs?, items?, group?} | {ping} | {open} | {pick}
  ↓
harpe engine  (installed via: uv tool install harpe — registers the host itself)
  │  downloads with correct UA/Referer, descriptive naming, per-type folders
  │  reply = JSON: {results:[{url, ok, path|error, kind}]} | {ok, defaults} | {ok, path}
  ↑
Results flow back up through host → background → popup → UI badge per image
```

**Why a native host?** A pure browser extension cannot make arbitrary cross-origin requests with spoofed headers or write files to disk. The host delegates both to `harpe`, which runs as a trusted local process. `harpe` *is* the host (`harpe --native-host`), so there is no separate helper to ship or maintain.

## Prerequisites

1. **harpe** engine installed (it registers itself as the native host):
   ```sh
   uv tool install harpe
   ```
   Verify: `harpe --help`

2. **Chrome 116+** or **Firefox 121+** (for side panel / sidebar / native messaging)

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
├── store/                  ← store listing assets + screenshot generator
├── scripts/package.sh      ← builds per-browser store zips
└── README.md
```

The native host now lives in the `harpe` engine (`harpe --native-host`,
`harpe install-host`), not in this repo.

No build step required — the extension is plain vanilla JS (ES2020).

## Installation

### Just the extension (no setup)

Load `extension/` (see Step 3 below) or install from the store. Done — finding
and grabbing **images and direct/X-Twitter videos** works immediately, saving to
`Downloads/harpe/<site>/`. This needs no native software and a lean permission
set (`nativeMessaging` is **not** requested here).

### Optional: the Harpe engine (save anywhere, per-type folders, yt-dlp video)

Only needed if you click **"Enable Harpe engine"** in settings — that requests
the optional `nativeMessaging` permission on the spot, then talks to the local
engine. The engine **is its own native host and registers itself**, so there's no
separate script to run.

- Chromium ID: `ginhcamellmffiamggkiaemdklcnechf`
- Firefox ID:  `harpe@nullsense.com`

### Step 1 — Install the `harpe` engine (registers itself)

```sh
uv tool install harpe      # also auto-registers the native host on first run
harpe --help               # verify
```

`harpe` registers the browser native-messaging host the first time it runs (for
every detected Chromium & Firefox browser; Windows via the registry). To do it
explicitly, or after publishing to a store with a different id:

```sh
harpe install-host                      # (re)register for detected browsers
harpe install-host --chrome-id <ID>     # also allow another Chromium id
harpe install-host --firefox-id <ID>    # also allow another Firefox id
harpe install-host --all                # write even to browsers not detected yet
harpe uninstall-host                    # remove everywhere
```

The host manifest's `path` points at a tiny launcher that runs
`harpe --native-host`, so upgrading `harpe` needs no re-register.

### Step 2 — Load the extension

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

### Step 3 — Verify

Open an image-heavy page, click the Harpe icon, pick images, **Grab**. If the
engine isn't reachable the popup shows a setup hint. Sanity-check the host
protocol directly:

```sh
printf '\x10\x00\x00\x00{"ping": true}' | harpe --native-host | tail -c +5
# → {"ok": true, "pong": true, "defaults": {...}, "version": "..."}
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
2. **Engine** — one command: `uv tool install harpe`, which registers the native
   host itself (first run or `harpe install-host`). The popup links here when the
   engine is missing.

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

The host registration is owned by `harpe` (`harpe install-host` writes a launcher
+ the per-browser manifests / Windows registry keys), so there is nothing host-
related to bundle into the store package.

### Keeping dev and Web Store IDs the same

The published Chrome Web Store ID is assigned by Google when you first create the
item, and may differ from the baked dev ID. To unify them, after creating the
draft item open **Package → View public key**, copy it into `manifest.json`'s
`"key"`, then run `harpe install-host --chrome-id <store-id>` (the host allows
multiple origins, so dev + store IDs both work).

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

`harpe --native-host` speaks the browser native-messaging protocol in-process and
dispatches each request to the engine:

| Request | Reply |
|---------|-------|
| `{ping:true}` | `{ok, pong, defaults:{image,video,audio}, version}` |
| `{urls, referer, dirs?, items?, group?}` | `{results:[{url, ok, path?, kind?\|error?}]}` |
| `{open:"<path>"}` | `{ok}` (reveals the folder in the OS file manager) |
| `{pick:true, start?}` | `{ok, path}` (native folder chooser; `path` null if cancelled) |

`dirs` = per-type roots (Images/Videos/Audio); `items` = per-url
`{name, author}` for descriptive filenames; `group` = `site｜author｜both｜none`
nesting. The legacy `harpe -F - --json` CLI path still exists for terminal use.

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
