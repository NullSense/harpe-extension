# Store assets

Listing images for the Chrome Web Store and Firefox AMO, plus the source that
generates them. Everything here is **offline and reproducible** — no stock photos,
no external fetches. The "found media" tiles are procedural SVG art; the panel in
each shot is rendered from the **real** `extension/css/popup.css`, so the
screenshots always match the shipping UI.

## Final images (`images/`)

| File | Size | Use |
|------|------|-----|
| `harpe-scan.png` | 1280×800 | Screenshot — scan results: grid of found images + a video card, ready to grab |
| `harpe-settings.png` | 1280×800 | Screenshot — per-type save folders (Images / Videos / Audio) |
| `harpe-saved.png` | 1280×800 | Screenshot — grab complete: "Saved to …" + Open folder |
| `harpe-marquee.png` | 1400×560 | Chrome Web Store **marquee** promo tile |
| `harpe-small.png` | 440×280 | Chrome Web Store **small** promo tile |

1280×800 suits CWS screenshots and AMO. (CWS also accepts 640×400; AMO accepts
any size.)

## Regenerating

```sh
python3 store/build_assets.py            # writes assets/ + templates/
# serve the parent so templates can reach ../assets:
python3 -m http.server 8799 --directory store
# then render each template at the size in its :root --shot-w/h with a headless
# browser (e.g. Playwright) and save into images/:
#   /templates/screenshot-scan.html      → 1280×800 → images/harpe-scan.png
#   /templates/screenshot-settings.html  → 1280×800 → images/harpe-settings.png
#   /templates/screenshot-saved.html     → 1280×800 → images/harpe-saved.png
#   /templates/promo-marquee.html        → 1400×560 → images/harpe-marquee.png
#   /templates/promo-small.html          →  440×280 → images/harpe-small.png
```

`build_assets.py` copies `extension/css/popup.css` into `templates/`, so re-run it
after changing the popup styles to keep the screenshots in sync.

## Listing copy (reuse for both stores)

**Summary:** Grab any image or video from any page — scan the live page, pick what
you want, download it. Works in your browser with no setup; an optional local
engine adds save-anywhere, per-type folders, and yt-dlp sources.

**Single purpose (CWS):** Download images and videos from the page the user is
viewing.

**Permission justification (`<all_urls>`):** You can navigate to any website, so
the extension must read the current page to find media on it. The page is scanned
locally and never transmitted to us — see [`../PRIVACY.md`](../PRIVACY.md).
