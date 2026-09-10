#!/usr/bin/env bash
#
# Installs the theme onto the pwnagotchi SD card, mounted on this computer.
# Useful without a data-capable micro-USB cable, and safer for a first try:
# if the pi fails to boot, remount the card and undo it.
#
#   sudo ./tools/install-sdcard.sh /run/media/<user>/rootfs
#
# The pi must be powered off, with its card in this computer.

set -euo pipefail

SD_ROOT="${1:-}"
SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ $EUID -ne 0 ]]; then
    echo "This script must run as root: sudo $0 <mountpoint>" >&2
    exit 1
fi

if [[ -z "$SD_ROOT" || ! -d "$SD_ROOT" ]]; then
    echo "Usage: sudo $0 <rootfs-partition-mountpoint>" >&2
    echo "Example: sudo $0 /run/media/$SUDO_USER/rootfs" >&2
    exit 1
fi

CONFIG="$SD_ROOT/etc/pwnagotchi/config.toml"
if [[ ! -f "$CONFIG" ]]; then
    echo "No $CONFIG here: this is not a pwnagotchi root partition." >&2
    exit 1
fi

echo "==> Target: $SD_ROOT"
# both config styles: flat keys, or [sections] with bare keys
grep -E '^\s*(main\.)?name *=|^\s*(ui\.display\.)?type *=|^\s*(ui\.)?invert *=' \
     "$CONFIG" 2>/dev/null | head -4 | sed 's/^/    /' || true

# --- images
DEST_IMG="$SD_ROOT/usr/local/share/neuromancer"
echo "==> Images -> /usr/local/share/neuromancer"
mkdir -p "$DEST_IMG"
cp "$SOURCE"/images/*.png "$DEST_IMG/"

# --- plugin
# The scanned directory depends on the version: main.custom_plugins is
# /usr/local/share/pwnagotchi/custom-plugins/ on 2.x and
# /etc/pwnagotchi/custom-plugins/ on recent forks. Read it rather than guess:
# the user config first, then the shipped defaults.
# configure.py reads both layouts; a grep for the flat form alone quietly
# installed the plugin into the wrong directory on releases whose defaults
# are written as sections, and pwnagotchi then never loaded it
PLUGIN_PATH="$(python3 "$SOURCE/tools/configure.py" "$CONFIG" plugins-dir 2>/dev/null || true)"
if [[ -z "$PLUGIN_PATH" ]]; then
    DEFAULTS="$(find "$SD_ROOT" -maxdepth 9 -name 'defaults.toml' -path '*pwnagotchi*' 2>/dev/null | head -1 || true)"
    if [[ -n "$DEFAULTS" ]]; then
        PLUGIN_PATH="$(python3 "$SOURCE/tools/configure.py" "$DEFAULTS" plugins-dir 2>/dev/null || true)"
    fi
fi
PLUGIN_PATH="${PLUGIN_PATH:-/usr/local/share/pwnagotchi/custom-plugins/}"
DEST_PLUG="$SD_ROOT/${PLUGIN_PATH#/}"
echo "==> Plugin -> $PLUGIN_PATH"
mkdir -p "$DEST_PLUG"
cp "$SOURCE/neuromancer.py" "$DEST_PLUG/"
# stale bytecode from a previous version must go
rm -rf "$DEST_PLUG/__pycache__"
# clean up a copy left in the other possible location
for other in "$SD_ROOT/usr/local/share/pwnagotchi/custom-plugins" \
             "$SD_ROOT/etc/pwnagotchi/custom-plugins"; do
    if [[ "$other" != "${DEST_PLUG%/}" && -f "$other/neuromancer.py" ]]; then
        rm -f "$other/neuromancer.py" "$other/__pycache__/neuromancer."*
        echo "    removed stale copy from ${other#$SD_ROOT}"
    fi
done

# --- voice: the package often lives in a venv
echo "==> Neuromancer voice"
LOCALE_DIR="$(find "$SD_ROOT" -maxdepth 9 -type d -path '*pwnagotchi/locale' 2>/dev/null | head -1 || true)"
if [[ -n "$LOCALE_DIR" ]]; then
    mkdir -p "$LOCALE_DIR/neuromancer/LC_MESSAGES"
    cp "$SOURCE/locale/neuromancer/LC_MESSAGES/voice.mo" "$LOCALE_DIR/neuromancer/LC_MESSAGES/"
    echo "    installed in ${LOCALE_DIR#$SD_ROOT}/neuromancer"
    VOICE_OK=1
else
    echo "    ! locale directory not found, voice not installed" >&2
    VOICE_OK=0
fi

# --- configuration
echo "==> Configuration"
cp "$CONFIG" "$CONFIG.bak.$(date +%s)"
echo "    backup: $(basename "$CONFIG").bak.*"

# Two config styles exist (flat keys or [sections]); configure.py handles both.
OUT="$(python3 "$SOURCE/tools/configure.py" "$CONFIG" enable)"
echo "    plugin enabled ($(echo "$OUT" | grep -oP 'STYLE=\K.*') style config)"

if [[ "$VOICE_OK" == "1" ]]; then
    PREV_LANG="$(echo "$OUT" | grep -oP 'PREVIOUS_LANG=\K.*')"
    if [[ -n "$PREV_LANG" ]]; then
        printf '%s\n' "$PREV_LANG" > "$DEST_IMG/.previous-lang"
        echo "    language was \"$PREV_LANG\", switched to neuromancer"
    else
        echo "    language already neuromancer"
    fi
fi

sync
echo
echo "Done. Unmount the card cleanly, put it back in the pi and power it on:"
echo "    udisksctl unmount -b <partition>"
echo
echo "Then, once the pi is reachable:"
echo "    journalctl -u pwnagotchi -f | grep neuromancer"
