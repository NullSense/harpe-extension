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
import json, os, sys, zipfile

src, dist = sys.argv[1], sys.argv[2]
os.makedirs(dist, exist_ok=True)

manifest = json.load(open(os.path.join(src, "manifest.json")))
ver = manifest["version"]
manifest.pop("key", None)  # dev-only ID pin; stores assign their own ID
manifest_bytes = json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8")

out = os.path.join(dist, f"harpe-{ver}.zip")
if os.path.exists(out):
    os.remove(out)

with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for root, _dirs, files in os.walk(src):
        for f in files:
            if f == ".DS_Store":
                continue
            full = os.path.join(root, f)
            arc = os.path.relpath(full, src)
            if arc == "manifest.json":
                z.writestr(arc, manifest_bytes)  # key-stripped copy
            else:
                z.write(full, arc)
print(f"built {out} (key stripped, version {ver})")
PY
