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

### Step 1 — Load the extension

**Chrome / Chromium:**
1. Open `chrome://extensions`
2. Enable **Developer mode** (top-right toggle)
3. Click **Load unpacked** → select the `extension/` folder
4. Copy the **Extension ID** shown (32-character string, e.g. `abcdefghijklmnopabcdefghijklmnop`)

**Firefox:**
1. Open `about:debugging#/runtime/this-firefox`
2. Click **Load Temporary Add-on…** → select `extension/manifest.json`
   - For permanent installation, pack as `.xpi` and set an explicit `browser_specific_settings.gecko.id` in manifest.json first (e.g. `harpe@nullsense.com`)
3. Note the **Internal UUID** shown (used as the Firefox extension ID for native messaging)

### Step 2 — Install the native messaging host

```sh
cd host/

# Chrome only
./install.sh --chrome-id abcdefghijklmnopabcdefghijklmnop

# Firefox only
./install.sh --firefox-id harpe@nullsense.com

# Both
./install.sh --chrome-id abcdefghijklmnopabcdefghijklmnop \
             --firefox-id harpe@nullsense.com
```

The script:
- Substitutes the extension ID and absolute host path into the manifest template
- Copies the manifest to the correct NativeMessagingHosts directory for your OS and browser
- Makes `harpe_host.py` executable

### Native messaging host manifest locations

| Browser    | OS      | Per-user path |
|------------|---------|---------------|
| Chrome     | Linux   | `~/.config/google-chrome/NativeMessagingHosts/` |
| Chromium   | Linux   | `~/.config/chromium/NativeMessagingHosts/` |
| Chrome     | macOS   | `~/Library/Application Support/Google/Chrome/NativeMessagingHosts/` |
| Firefox    | Linux   | `~/.mozilla/native-messaging-hosts/` |
| Firefox    | macOS   | `~/Library/Application Support/Mozilla/NativeMessagingHosts/` |

System-wide locations (require root) are documented in `install.sh`.

### Step 3 — Verify

Open any image-heavy page, click the Harpe toolbar icon, and the side panel should open and scan the page. If the native host is unreachable, the "Grab" operation will show an error — check:

```sh
# Test the host directly
echo '{"urls":["https://example.com/test.jpg"],"referer":"https://example.com"}' | \
  python3 host/harpe_host.py
```

## The extension-ID chicken-and-egg

Chrome generates the extension ID from the public key in the extension package. When loading **unpacked** in developer mode, the ID is derived from the path, so it **changes** if you move the folder. Firefox uses a UUID that changes each temporary load session.

**Workarounds:**

- **Chrome (stable ID):** Generate a key pair, put the public key in `manifest.json` under `"key"`, and Chrome will use a fixed ID derived from that key. Run `install.sh` once with that ID.

  ```sh
  openssl genrsa 2048 | openssl pkcs8 -topk8 -nocrypt -out key.pem
  openssl rsa -in key.pem -pubout -outform DER | base64 -w0
  # Paste the base64 output as "key": "..." in manifest.json
  ```

- **Firefox (stable ID):** Add to `manifest.json`:
  ```json
  "browser_specific_settings": {
    "gecko": { "id": "harpe@nullsense.com" }
  }
  ```
  Then use `--firefox-id harpe@nullsense.com` in `install.sh`.

- **Development shortcut:** Run `install.sh` after each load with the new ID. It's a one-liner.

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
