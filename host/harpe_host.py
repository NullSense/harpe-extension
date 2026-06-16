#!/usr/bin/env python3
"""
Harpe native messaging host.

Speaks the Chrome/Firefox native-messaging protocol:
  - Each message is a 4-byte little-endian unsigned integer (message length)
    followed by that many bytes of UTF-8 JSON.

Incoming from extension:
  { "urls": ["https://…", …], "referer": "https://…" }

Outgoing to extension:
  { "results": [ {"url": "…", "ok": true, "path": "…"}, … ] }
  or on fatal error:
  { "results": [], "error": "…" }

The host pipes the URL list to `harpe -F - --json --referer <referer>` and
forwards harpe's JSON array back to the extension.
"""

import json
import struct
import subprocess
import sys
import shutil
import os
import logging
from pathlib import Path

# ── Logging (to stderr so it doesn't corrupt the stdout protocol) ────────────

logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="harpe-host %(levelname)s: %(message)s",
)
log = logging.getLogger("harpe-host")


# ── Native messaging framing ─────────────────────────────────────────────────

def read_message(stream) -> dict:
    """Read one native-messaging message from stream, return parsed JSON."""
    raw_len = stream.read(4)
    if len(raw_len) < 4:
        raise EOFError("stdin closed")
    (length,) = struct.unpack("<I", raw_len)
    if length == 0:
        return {}
    raw_msg = stream.read(length)
    if len(raw_msg) < length:
        raise EOFError("truncated message")
    return json.loads(raw_msg.decode("utf-8"))


def write_message(stream, obj: dict) -> None:
    """Write one native-messaging message to stream."""
    payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    stream.write(struct.pack("<I", len(payload)))
    stream.write(payload)
    stream.flush()


# ── Harpe invocation ─────────────────────────────────────────────────────────

def find_harpe() -> str:
    """
    Locate the `harpe` binary.

    Native-messaging hosts are launched by the browser with a minimal
    environment — the user's shell PATH (and additions like ~/bin) is often
    absent — so PATH lookup alone is unreliable. We therefore check, in order:
      1. an explicit HARPE_BIN override
      2. PATH (works if the browser inherited a full PATH)
      3. common install / shim locations, including ~/bin
    """
    # On Windows the binary is harpe.exe; elsewhere just harpe.
    names = ["harpe.exe", "harpe"] if os.name == "nt" else ["harpe"]

    def usable(p):
        return os.path.isfile(p) and (os.name == "nt" or os.access(p, os.X_OK))

    # 1. Explicit override — set HARPE_BIN in the host manifest's env if needed.
    override = os.environ.get("HARPE_BIN")
    if override and usable(override):
        return override

    # 2. On PATH (most common after `uv tool install harpe`)
    for n in names:
        found = shutil.which(n)
        if found:
            return found

    # 3. Common install / shim locations (uv, cargo, personal bin) — cross-platform.
    roots = [
        os.path.expanduser("~/.local/bin"),
        os.path.expanduser("~/bin"),
        os.path.expanduser("~/.cargo/bin"),
    ]
    if os.name == "nt":
        roots += [
            os.path.join(os.environ.get("APPDATA", ""), "Python", "Scripts"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "harpe"),
        ]
    for r in roots:
        for n in names:
            c = os.path.join(r, n)
            if usable(c):
                return c

    raise FileNotFoundError(
        "harpe binary not found. Install it with: uv tool install harpe, "
        "or set HARPE_BIN to its absolute path."
    )


def _linux_session_env() -> dict:
    """Reconstruct the desktop session env. The browser may launch the native
    host without WAYLAND_DISPLAY/DISPLAY/DBUS, which makes GUI openers no-op
    silently — recover them from the runtime dir so xdg-open can reach the WM."""
    env = os.environ.copy()
    try:
        uid = os.getuid()
    except AttributeError:
        return env
    run = env.get("XDG_RUNTIME_DIR") or f"/run/user/{uid}"
    env.setdefault("XDG_RUNTIME_DIR", run)
    if not env.get("WAYLAND_DISPLAY") and not env.get("DISPLAY"):
        for name in ("wayland-1", "wayland-0"):
            if os.path.exists(os.path.join(run, name)):
                env["WAYLAND_DISPLAY"] = name
                break
        if "WAYLAND_DISPLAY" not in env:
            env["DISPLAY"] = env.get("DISPLAY", ":0")
    if not env.get("DBUS_SESSION_BUS_ADDRESS"):
        bus = os.path.join(run, "bus")
        if os.path.exists(bus):
            env["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={bus}"
    return env


def open_in_file_manager(target: str) -> None:
    """Reveal a saved file (or folder) in the OS file manager. Raises if no
    opener could be launched (so the extension can tell the user the path)."""
    p = Path(os.path.expanduser(os.path.expandvars(target)))
    folder = str(p if p.is_dir() else p.parent)

    if sys.platform == "darwin":
        subprocess.Popen(["open", folder], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return
    if os.name == "nt":
        subprocess.Popen(["explorer", folder])
        return

    env = _linux_session_env()
    # Try a generic opener first, then common file managers (whichever exists).
    candidates = [["xdg-open", folder], ["gio", "open", folder], ["nautilus", folder],
                  ["dolphin", folder], ["thunar", folder], ["nemo", folder],
                  ["pcmanfm", folder], ["gdbus", "call", "-e", "-d",
                   "org.freedesktop.FileManager1", "-o", "/org/freedesktop/FileManager1",
                   "-m", "org.freedesktop.FileManager1.ShowFolders",
                   f"['file://{folder}']", ""]]
    for cmd in candidates:
        if not shutil.which(cmd[0]):
            continue
        try:
            subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return
        except Exception as exc:
            log.warning("opener %s failed: %s", cmd[0], exc)
    raise RuntimeError("no file manager found (tried xdg-open, gio, nautilus, dolphin, thunar, nemo, pcmanfm)")


# Per-media-type save folders. The engine reads these env vars at startup and
# groups files by source host inside each. We map the extension's settings to
# them when spawning harpe (a fresh process each grab, so env is read fresh).
_DIR_ENV = {"image": "HARPE_IMG_DIR", "video": "HARPE_VID_DIR", "audio": "HARPE_AUD_DIR"}


def default_dirs() -> dict:
    """The engine's built-in defaults (mirrors harpe.config) — used so the
    extension can show real paths as placeholders."""
    home = Path.home()
    videos = "Movies" if sys.platform == "darwin" else "Videos"
    return {
        "image": str(home / "Pictures" / "harpe"),
        "video": str(home / videos / "harpe"),
        "audio": str(home / "Music" / "harpe"),
    }


def run_harpe(urls, referer, dest=None, dirs=None) -> list[dict]:
    """
    Invoke `harpe -F - --json --referer <referer> [--dest <dest>]`, pipe urls on
    stdin, return parsed JSON array.

    `dirs` is an optional {image,video,audio: path} map; each non-empty entry is
    passed to the engine via its HARPE_*_DIR env var (per-type customisation).
    `dest` is the legacy single-folder override (used by the CLI).
    """
    harpe_bin = find_harpe()
    url_payload = "\n".join(urls) + "\n"

    env = os.environ.copy()
    if isinstance(dirs, dict):
        for kind, var in _DIR_ENV.items():
            v = dirs.get(kind)
            if isinstance(v, str) and v.strip():
                env[var] = os.path.expanduser(os.path.expandvars(v.strip()))

    cmd = [harpe_bin, "-F", "-", "--json", "--referer", referer]
    if dest:
        cmd += ["--dest", dest]
    log.info("running: %s (urls=%d)", " ".join(cmd), len(urls))

    result = subprocess.run(
        cmd,
        input=url_payload,
        capture_output=True,
        text=True,
        env=env,
        timeout=300,  # 5 min max
    )

    if result.returncode != 0:
        log.error("harpe exited %d: %s", result.returncode, result.stderr.strip())
        # Return error entries for each URL
        return [
            {
                "url": u,
                "ok": False,
                "error": f"harpe exited {result.returncode}: {result.stderr.strip()[:200]}",
            }
            for u in urls
        ]

    stdout = result.stdout.strip()
    if not stdout:
        log.error("harpe produced no output")
        return [{"url": u, "ok": False, "error": "harpe produced no output"} for u in urls]

    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError as exc:
        log.error("harpe output is not valid JSON: %s", exc)
        return [{"url": u, "ok": False, "error": "harpe output parse error"} for u in urls]

    if not isinstance(parsed, list):
        # harpe may wrap results — try common wrappers
        if isinstance(parsed, dict) and "results" in parsed:
            parsed = parsed["results"]
        else:
            parsed = [{"url": u, "ok": False, "error": "unexpected harpe output shape"} for u in urls]

    # Normalise: ensure every entry has at least url + ok
    normalised = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        entry = {"url": item.get("url", ""), "ok": bool(item.get("ok", False))}
        if "path" in item:
            entry["path"] = item["path"]
        if "error" in item:
            entry["error"] = item["error"]
        normalised.append(entry)

    return normalised


# ── Main loop ────────────────────────────────────────────────────────────────

def main() -> None:
    # Use binary streams — the framing protocol is binary
    stdin = sys.stdin.buffer
    stdout = sys.stdout.buffer

    log.info("harpe native host started (pid=%d)", os.getpid())

    while True:
        try:
            msg = read_message(stdin)
        except EOFError:
            log.info("stdin closed — exiting")
            break
        except Exception as exc:
            log.error("read error: %s", exc)
            write_message(stdout, {"results": [], "error": str(exc)})
            break

        if not msg:
            continue

        # Liveness probe — lets the extension auto-detect that the helper is
        # installed and silently upgrade to engine features (no manual toggle).
        if msg.get("ping"):
            write_message(stdout, {"ok": True, "pong": True, "defaults": default_dirs()})
            continue

        # Reveal a saved file/folder in the OS file manager (engine path — the
        # extension can't open arbitrary OS folders itself).
        if msg.get("open"):
            try:
                open_in_file_manager(str(msg["open"]))
                write_message(stdout, {"ok": True})
            except Exception as exc:
                log.error("open failed: %s", exc)
                write_message(stdout, {"ok": False, "error": str(exc)})
            continue

        urls = msg.get("urls", [])
        referer = msg.get("referer", "")

        # Optional save folder chosen in the extension settings. Expand ~ and
        # env vars; an empty/blank value means "let harpe use its default".
        dest_raw = msg.get("dest", "")
        dest = None
        if isinstance(dest_raw, str) and dest_raw.strip():
            dest = os.path.expanduser(os.path.expandvars(dest_raw.strip()))

        # Per-type folders from the extension settings (blank entries fall back
        # to the engine defaults).
        dirs = msg.get("dirs") if isinstance(msg.get("dirs"), dict) else None

        if not isinstance(urls, list) or not urls:
            write_message(stdout, {"results": [], "error": "no urls provided"})
            continue

        # Sanitise: keep only strings, strip whitespace
        urls = [str(u).strip() for u in urls if u and str(u).strip()]
        if not urls:
            write_message(stdout, {"results": [], "error": "no valid urls after sanitisation"})
            continue

        try:
            results = run_harpe(urls, referer, dest, dirs)
            write_message(stdout, {"results": results})
        except FileNotFoundError as exc:
            log.error("%s", exc)
            write_message(stdout, {"results": [], "error": str(exc)})
        except subprocess.TimeoutExpired:
            log.error("harpe timed out")
            write_message(stdout, {"results": [], "error": "harpe timed out"})
        except Exception as exc:
            log.error("unexpected error: %s", exc)
            write_message(stdout, {"results": [], "error": str(exc)})


if __name__ == "__main__":
    main()
