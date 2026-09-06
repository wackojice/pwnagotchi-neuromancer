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

RACINE_SD="${1:-}"
SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ $EUID -ne 0 ]]; then
    echo "This script must run as root: sudo $0 <mountpoint>" >&2
    exit 1
fi

if [[ -z "$RACINE_SD" || ! -d "$RACINE_SD" ]]; then
    echo "Usage: sudo $0 <rootfs-partition-mountpoint>" >&2
    echo "Example: sudo $0 /run/media/$SUDO_USER/rootfs" >&2
    exit 1
fi

CONFIG="$RACINE_SD/etc/pwnagotchi/config.toml"
if [[ ! -f "$CONFIG" ]]; then
    echo "No $CONFIG here: this is not a pwnagotchi root partition." >&2
    exit 1
fi

echo "==> Target: $RACINE_SD"
grep -E '^main\.name|^ui\.display\.type|^ui\.invert' "$CONFIG" | sed 's/^/    /'

# --- images
DEST_IMG="$RACINE_SD/usr/local/share/neuromancer"
echo "==> Images -> /usr/local/share/neuromancer"
mkdir -p "$DEST_IMG"
cp "$SOURCE"/images/*.png "$DEST_IMG/"

# --- plugin
# The scanned directory depends on the version: main.custom_plugins is
# /usr/local/share/pwnagotchi/custom-plugins/ on 2.x and
# /etc/pwnagotchi/custom-plugins/ on recent forks. Read it rather than guess:
# the user config first, then the shipped defaults.
CHEMIN_PLUG="$(grep -hoP '^\s*main\.custom_plugins\s*=\s*"\K[^"]+' "$CONFIG" 2>/dev/null | head -1 || true)"
if [[ -z "$CHEMIN_PLUG" ]]; then
    DEFAUTS="$(find "$RACINE_SD" -maxdepth 9 -name 'defaults.toml' -path '*pwnagotchi*' 2>/dev/null | head -1 || true)"
    CHEMIN_PLUG="$(grep -hoP '^\s*main\.custom_plugins\s*=\s*"\K[^"]+' "$DEFAUTS" 2>/dev/null | head -1 || true)"
fi
CHEMIN_PLUG="${CHEMIN_PLUG:-/usr/local/share/pwnagotchi/custom-plugins/}"
DEST_PLUG="$RACINE_SD/${CHEMIN_PLUG#/}"
echo "==> Plugin -> $CHEMIN_PLUG"
mkdir -p "$DEST_PLUG"
cp "$SOURCE/neuromancer.py" "$DEST_PLUG/"
# stale bytecode from a previous version must go
rm -rf "$DEST_PLUG/__pycache__"
# clean up a copy left in the other possible location
for autre in "$RACINE_SD/usr/local/share/pwnagotchi/custom-plugins" \
             "$RACINE_SD/etc/pwnagotchi/custom-plugins"; do
    if [[ "$autre" != "${DEST_PLUG%/}" && -f "$autre/neuromancer.py" ]]; then
        rm -f "$autre/neuromancer.py" "$autre/__pycache__/neuromancer."*
        echo "    removed stale copy from ${autre#$RACINE_SD}"
    fi
done

# --- voice: the package often lives in a venv
echo "==> Neuromancer voice"
LOCALE_PWN="$(find "$RACINE_SD" -maxdepth 9 -type d -path '*pwnagotchi/locale' 2>/dev/null | head -1 || true)"
if [[ -n "$LOCALE_PWN" ]]; then
    mkdir -p "$LOCALE_PWN/neuromancer/LC_MESSAGES"
    cp "$SOURCE/locale/neuromancer/LC_MESSAGES/voice.mo" "$LOCALE_PWN/neuromancer/LC_MESSAGES/"
    echo "    installed in ${LOCALE_PWN#$RACINE_SD}/neuromancer"
    VOIX_OK=1
else
    echo "    ! locale directory not found, voice not installed" >&2
    VOIX_OK=0
fi

# --- configuration
echo "==> Configuration"
cp "$CONFIG" "$CONFIG.bak.$(date +%s)"
echo "    backup: $(basename "$CONFIG").bak.*"

if grep -q '^main\.plugins\.neuromancer\.enabled' "$CONFIG"; then
    sed -i 's/^main\.plugins\.neuromancer\.enabled.*/main.plugins.neuromancer.enabled = true/' "$CONFIG"
else
    printf '\nmain.plugins.neuromancer.enabled = true\n' >> "$CONFIG"
fi
echo "    plugin enabled"

if [[ "$VOIX_OK" == "1" ]]; then
    if grep -qE '^main\.lang' "$CONFIG"; then
        sed -i 's/^main\.lang.*/main.lang = "neuromancer"/' "$CONFIG"
    else
        printf 'main.lang = "neuromancer"\n' >> "$CONFIG"
    fi
    echo "    language switched to neuromancer"
fi

sync
echo
echo "Done. Unmount the card cleanly, put it back in the pi and power it on:"
echo "    udisksctl unmount -b <partition>"
echo
echo "Then, once the pi is reachable:"
echo "    journalctl -u pwnagotchi -f | grep neuromancer"
