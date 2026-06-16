# Harpe — Privacy Policy

_Last updated: 2026-06-16_

Harpe is a browser extension that finds images and videos on the page you are
viewing and downloads the ones you choose. It is designed to keep your data on
your own machine.

## What Harpe does

- **Scans the current page** (in your browser) for image and video candidates so
  it can show them to you. This scanning happens locally in the content script;
  the list of found media never leaves your browser.
- **Downloads the items you select** to your computer, either through the
  browser's own download mechanism or, if you have explicitly enabled it, through
  the optional local Harpe engine.

## Data we collect

**None.** Harpe has no analytics, no telemetry, no tracking, no accounts, and no
remote servers operated by us. We do not collect, store, transmit, or sell any
personal data, browsing history, page content, or download activity.

## Network requests Harpe makes

Harpe only contacts the internet to do the job you asked for:

1. **The media you choose** — Harpe fetches/downloads the specific image or video
   files you select, directly from the site or CDN that hosts them. This is the
   same network access that would occur if you saved the file yourself.
2. **X / Twitter videos** — to find a tweet's downloadable video, Harpe queries
   X's public tweet-syndication endpoint (`cdn.syndication.twimg.com`). Only the
   public tweet ID from the page you are viewing is sent, and only when that page
   is an X/Twitter post. No account or personal information is sent.

Harpe does **not** send the pages you visit, the media it finds, or your download
choices to us or any third-party analytics service.

## The optional local engine (native messaging)

The `nativeMessaging` permission is **optional** and is requested only if you
click **"Enable Harpe engine"**. When enabled, Harpe passes the URLs you chose to
download — plus the page address as a referer — to the Harpe program running
**on your own computer**, which performs the download. This data stays on your
machine; it is not sent to us.

## Permissions and why they are needed

- **Host access to all sites (`<all_urls>`)** — you can navigate to any website,
  so Harpe must be able to read the current page to find media on it. The page is
  read locally and not transmitted anywhere.
- **`scripting`** — to run the page scanner on demand.
- **`downloads`** — to save the files you select.
- **`notifications`** — to tell you when a download finishes.
- **`storage`** — to remember your save-folder settings (stored locally in the
  browser).
- **`sidePanel`** — to show Harpe's UI in the browser side panel.
- **`nativeMessaging`** (optional) — only if you enable the local engine, as
  described above.

## Changes

If this policy changes, the updated version will be published in this repository
with a new "Last updated" date.

## Contact

Questions: open an issue at https://github.com/NullSense/harpe-extension
