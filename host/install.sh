#!/usr/bin/env bash
# install.sh — Install the Harpe native messaging host for Chrome and/or Firefox.
#
# Usage:
#   ./install.sh --chrome-id <EXTENSION_ID>
#   ./install.sh --firefox-id <ADDON_ID>
#   ./install.sh --chrome-id <EXTENSION_ID> --firefox-id <ADDON_ID>
#
# The EXTENSION_ID for Chrome looks like: abcdefghijklmnopabcdefghijklmnop
# The ADDON_ID for Firefox looks like:    harpe@nullsense.com  (set in manifest.json)
#
# Native messaging host manifest locations:
#
#   Chrome on Linux:
#     Per-user:   ~/.config/google-chrome/NativeMessagingHosts/
#     System:     /etc/opt/chrome/native-messaging-hosts/
#
#   Chromium on Linux:
#     Per-user:   ~/.config/chromium/NativeMessagingHosts/
#     System:     /etc/chromium/native-messaging-hosts/
#
#   Chrome on macOS:
#     Per-user:   ~/Library/Application Support/Google/Chrome/NativeMessagingHosts/
#     System:     /Library/Google/Chrome/NativeMessagingHosts/
#
#   Firefox on Linux:
#     Per-user:   ~/.mozilla/native-messaging-hosts/
#     System:     /usr/lib/mozilla/native-messaging-hosts/
#
#   Firefox on macOS:
#     Per-user:   ~/Library/Application Support/Mozilla/NativeMessagingHosts/
#     System:     /Library/Application Support/Mozilla/NativeMessagingHosts/

set -euo pipefail

# ── Locate this script's directory ──────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOST_SCRIPT="$SCRIPT_DIR/harpe_host.py"
MANIFEST_CHROME="$SCRIPT_DIR/com.nullsense.harpe.json"
MANIFEST_FIREFOX="$SCRIPT_DIR/com.nullsense.harpe.firefox.json"
MANIFEST_NAME="com.nullsense.harpe.json"

# ── Argument parsing ─────────────────────────────────────────────────────────

CHROME_ID=""
FIREFOX_ID=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --chrome-id)  CHROME_ID="$2";  shift 2 ;;
    --firefox-id) FIREFOX_ID="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$CHROME_ID" && -z "$FIREFOX_ID" ]]; then
  echo "Usage: $0 --chrome-id <ID> [--firefox-id <ADDON_ID>]" >&2
  echo "       $0 --firefox-id <ADDON_ID>" >&2
  exit 1
fi

# ── Sanity checks ────────────────────────────────────────────────────────────

if [[ ! -f "$HOST_SCRIPT" ]]; then
  echo "ERROR: Host script not found: $HOST_SCRIPT" >&2
  exit 1
fi

# Ensure the host script is executable
chmod +x "$HOST_SCRIPT"

# Ensure Python 3 is available
if ! command -v python3 &>/dev/null; then
  echo "ERROR: python3 is required but not found in PATH." >&2
  exit 1
fi

# ── OS detection ─────────────────────────────────────────────────────────────

OS="$(uname -s)"

case "$OS" in
  Linux)
    CHROME_DIR="$HOME/.config/google-chrome/NativeMessagingHosts"
    CHROMIUM_DIR="$HOME/.config/chromium/NativeMessagingHosts"
    FIREFOX_DIR="$HOME/.mozilla/native-messaging-hosts"
    ;;
  Darwin)
    CHROME_DIR="$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts"
    CHROMIUM_DIR="$HOME/Library/Application Support/Chromium/NativeMessagingHosts"
    FIREFOX_DIR="$HOME/Library/Application Support/Mozilla/NativeMessagingHosts"
    ;;
  *)
    echo "WARNING: Unsupported OS '$OS'. Manifest paths may be wrong." >&2
    CHROME_DIR="$HOME/.config/google-chrome/NativeMessagingHosts"
    CHROMIUM_DIR="$HOME/.config/chromium/NativeMessagingHosts"
    FIREFOX_DIR="$HOME/.mozilla/native-messaging-hosts"
    ;;
esac

# ── Helper: write manifest ───────────────────────────────────────────────────

install_manifest() {
  local src="$1"     # template file
  local dest_dir="$2"
  local extra_sed="$3"  # extra sed expression (for IDs)

  mkdir -p "$dest_dir"
  local dest="$dest_dir/$MANIFEST_NAME"

  sed \
    -e "s|__HOST_PATH__|$HOST_SCRIPT|g" \
    ${extra_sed:+-e "$extra_sed"} \
    "$src" > "$dest"

  echo "  Installed: $dest"
}

# ── Chrome / Chromium ────────────────────────────────────────────────────────

if [[ -n "$CHROME_ID" ]]; then
  echo "Installing Chrome/Chromium native messaging host (ID: $CHROME_ID)…"
  ID_SED="s|__EXTENSION_ID__|$CHROME_ID|g"
  install_manifest "$MANIFEST_CHROME" "$CHROME_DIR"   "$ID_SED"
  install_manifest "$MANIFEST_CHROME" "$CHROMIUM_DIR" "$ID_SED"
  echo "  Done. Reload the extension in chrome://extensions if already loaded."
fi

# ── Firefox ──────────────────────────────────────────────────────────────────

if [[ -n "$FIREFOX_ID" ]]; then
  echo "Installing Firefox native messaging host (addon ID: $FIREFOX_ID)…"
  ID_SED="s|__FIREFOX_EXTENSION_ID__|$FIREFOX_ID|g"
  install_manifest "$MANIFEST_FIREFOX" "$FIREFOX_DIR" "$ID_SED"
  echo "  Done. Reload the extension in about:debugging if already loaded."
fi

echo ""
echo "Harpe native host installed successfully."
echo "Host script: $HOST_SCRIPT"
echo ""
echo "Make sure 'harpe' is installed: uv tool install harpe"
