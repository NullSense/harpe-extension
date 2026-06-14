#!/usr/bin/env bash
# install.sh — register the Harpe native messaging host for every browser found.
#
# One command does everything:
#
#     ./install.sh
#
# It bakes in Harpe's stable extension IDs (see EXTENSION_ID / GECKO_ID below),
# auto-detects which browsers are installed, and writes the host manifest into
# each one's NativeMessagingHosts directory. Re-run it any time (e.g. after
# moving the repo) — it's idempotent.
#
# Options:
#   --chrome-id <ID>    ALSO allow this Chromium extension ID (e.g. the Chrome
#                       Web Store ID once published). Repeatable.
#   --firefox-id <ID>   ALSO allow this Firefox add-on ID. Repeatable.
#   --all               Write to every known browser dir, even if not detected.
#   --uninstall         Remove the host manifest from all browsers.
#
# Native-messaging host manifest locations are documented inline below.

set -euo pipefail

# ── Stable identities (derived from extension/manifest.json "key") ─────────────
EXTENSION_ID="ginhcamellmffiamggkiaemdklcnechf"   # Chromium: id from the manifest "key"
GECKO_ID="harpe@nullsense.com"                     # Firefox: browser_specific_settings.gecko.id
HOST_NAME="com.nullsense.harpe"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOST_SCRIPT="$SCRIPT_DIR/harpe_host.py"
MANIFEST_FILE="$HOST_NAME.json"

CHROME_IDS=("$EXTENSION_ID")
FIREFOX_IDS=("$GECKO_ID")
FORCE_ALL=0
UNINSTALL=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --chrome-id)  CHROME_IDS+=("$2"); shift 2 ;;
    --firefox-id) FIREFOX_IDS+=("$2"); shift 2 ;;
    --all)        FORCE_ALL=1; shift ;;
    --uninstall)  UNINSTALL=1; shift ;;
    -h|--help)    sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

[[ -f "$HOST_SCRIPT" ]] || { echo "ERROR: host script not found: $HOST_SCRIPT" >&2; exit 1; }
chmod +x "$HOST_SCRIPT"
command -v python3 >/dev/null || { echo "ERROR: python3 is required but not found." >&2; exit 1; }

# ── Per-OS browser → NativeMessagingHosts directories ──────────────────────────
OS="$(uname -s)"
declare -a CHROMIUM_DIRS=()   # use allowed_origins (chrome-extension://ID/)
declare -a FIREFOX_DIRS=()    # use allowed_extensions (gecko id)

if [[ "$OS" == "Darwin" ]]; then
  A="$HOME/Library/Application Support"
  CHROMIUM_DIRS=(
    "$A/Google/Chrome" "$A/Google/Chrome Beta" "$A/Chromium"
    "$A/BraveSoftware/Brave-Browser" "$A/Microsoft Edge" "$A/Vivaldi" "$A/net.imput.helium"
  )
  FIREFOX_DIRS=("$A/Mozilla" "$A/LibreWolf" "$A/zen")
  CH_SUB="NativeMessagingHosts"; FF_SUB="NativeMessagingHosts"
else
  C="$HOME/.config"
  CHROMIUM_DIRS=(
    "$C/google-chrome" "$C/google-chrome-beta" "$C/chromium"
    "$C/BraveSoftware/Brave-Browser" "$C/microsoft-edge" "$C/vivaldi" "$C/helium"
  )
  FIREFOX_DIRS=("$HOME/.mozilla" "$HOME/.librewolf" "$HOME/.zen")
  CH_SUB="NativeMessagingHosts"; FF_SUB="native-messaging-hosts"
fi

# ── JSON writers ───────────────────────────────────────────────────────────────
write_chrome_manifest() {
  local dest_dir="$1/$CH_SUB"
  mkdir -p "$dest_dir"
  {
    printf '{\n'
    printf '  "name": "%s",\n' "$HOST_NAME"
    printf '  "description": "Harpe native messaging host — pipes image URLs to the harpe download engine.",\n'
    printf '  "path": "%s",\n' "$HOST_SCRIPT"
    printf '  "type": "stdio",\n'
    printf '  "allowed_origins": [\n'
    local first=1 id
    for id in "${CHROME_IDS[@]}"; do
      [[ $first -eq 1 ]] && first=0 || printf ',\n'
      printf '    "chrome-extension://%s/"' "$id"
    done
    printf '\n  ]\n}\n'
  } > "$dest_dir/$MANIFEST_FILE"
  echo "  ✓ $dest_dir/$MANIFEST_FILE"
}

write_firefox_manifest() {
  local dest_dir="$1/$FF_SUB"
  mkdir -p "$dest_dir"
  {
    printf '{\n'
    printf '  "name": "%s",\n' "$HOST_NAME"
    printf '  "description": "Harpe native messaging host — pipes image URLs to the harpe download engine.",\n'
    printf '  "path": "%s",\n' "$HOST_SCRIPT"
    printf '  "type": "stdio",\n'
    printf '  "allowed_extensions": [\n'
    local first=1 id
    for id in "${FIREFOX_IDS[@]}"; do
      [[ $first -eq 1 ]] && first=0 || printf ',\n'
      printf '    "%s"' "$id"
    done
    printf '\n  ]\n}\n'
  } > "$dest_dir/$MANIFEST_FILE"
  echo "  ✓ $dest_dir/$MANIFEST_FILE"
}

remove_manifest() { # $1 = browser base dir, $2 = subdir
  local f="$1/$2/$MANIFEST_FILE"
  [[ -f "$f" ]] && { rm -f "$f"; echo "  ✗ removed $f"; }
}

# ── Run ────────────────────────────────────────────────────────────────────────
if [[ $UNINSTALL -eq 1 ]]; then
  echo "Removing Harpe native host…"
  for d in "${CHROMIUM_DIRS[@]}"; do remove_manifest "$d" "$CH_SUB"; done
  for d in "${FIREFOX_DIRS[@]}";  do remove_manifest "$d" "$FF_SUB"; done
  echo "Done."
  exit 0
fi

echo "Installing Harpe native host"
echo "  host script : $HOST_SCRIPT"
echo "  Chromium IDs: ${CHROME_IDS[*]}"
echo "  Firefox IDs : ${FIREFOX_IDS[*]}"
echo

wrote=0
for d in "${CHROMIUM_DIRS[@]}"; do
  if [[ $FORCE_ALL -eq 1 || -d "$d" ]]; then write_chrome_manifest "$d"; wrote=$((wrote+1)); fi
done
for d in "${FIREFOX_DIRS[@]}"; do
  if [[ $FORCE_ALL -eq 1 || -d "$d" ]]; then write_firefox_manifest "$d"; wrote=$((wrote+1)); fi
done

echo
if [[ $wrote -eq 0 ]]; then
  echo "No supported browsers detected. Re-run with --all to write to every known location."
else
  echo "Installed into $wrote browser profile dir(s)."
fi
echo "Make sure 'harpe' is installed (uv tool install harpe) or on PATH / in ~/bin."
