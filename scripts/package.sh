#!/usr/bin/env bash
# Build a clean store-submission zip from extension/.
#
# Strips the manifest "key" field (development-only ID pin; the stores assign
# their own ID) and produces dist/harpe-<version>.zip. The same artifact uploads
# to both the Chrome Web Store and Firefox AMO — Firefox ignores the absent key,
# and both read the same MV3 manifest.
#
# Dev-only convenience; end users never run this. Needs only python3.
set -euo pipefail

here="$(cd "$(dirname "$0")/.." && pwd)"

python3 - "$here/extension" "$here/dist" <<'PY'
import copy, json, os, sys, zipfile

src, dist = sys.argv[1], sys.argv[2]
os.makedirs(dist, exist_ok=True)

base = json.load(open(os.path.join(src, "manifest.json")))
ver = base["version"]


# The dev manifest (extension/manifest.json) is Chrome-native so "Load unpacked"
# is warning-free in Chrome. Firefox-only keys are injected into the FF build
# here (Firefox has no service-worker background and doesn't know side_panel).

def chrome_manifest():
    # Chrome: native side panel, one toolbar button. Drop dev/Gecko-only keys.
    m = copy.deepcopy(base)
    m.pop("key", None)                        # stores assign their own ID
    m.pop("browser_specific_settings", None)  # Gecko-only
    m.pop("sidebar_action", None)             # belt-and-suspenders
    m["background"].pop("scripts", None)
    return m


def firefox_manifest():
    # Firefox: native sidebar (its own button) + event-page background.
    m = copy.deepcopy(base)
    m.pop("key", None)
    m.pop("side_panel", None)                 # Chrome-only
    m.pop("action", None)                     # avoid a 2nd, redundant button
    if "sidePanel" in m.get("permissions", []):
        m["permissions"] = [p for p in m["permissions"] if p != "sidePanel"]
    m["background"] = {"scripts": ["js/background.js"]}  # no service worker on FF
    m["sidebar_action"] = {
        "default_title": "Harpe",
        "default_panel": "popup.html",
        "default_icon": {"16": "icons/icon16.png", "32": "icons/icon32.png"},
    }
    return m


def build(name, manifest):
    out = os.path.join(dist, f"harpe-{name}-{ver}.zip")
    if os.path.exists(out):
        os.remove(out)
    mb = json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _dirs, files in os.walk(src):
            for f in files:
                if f == ".DS_Store":
                    continue
                full = os.path.join(root, f)
                arc = os.path.relpath(full, src)
                if arc == "manifest.json":
                    z.writestr(arc, mb)
                else:
                    z.write(full, arc)
    print(f"built {out}")


build("chrome", chrome_manifest())
build("firefox", firefox_manifest())
print(f"version {ver} — Chrome=side panel, Firefox=native sidebar, key stripped")
PY
