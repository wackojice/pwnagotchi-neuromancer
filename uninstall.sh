#!/usr/bin/env bash
#
# Removes the Neuromancer theme from a pwnagotchi.
# Run this ON the pwnagotchi:
#
#   sudo ./uninstall.sh
#
# Or, against an SD card mounted on another computer -- the pi powered off:
#
#   sudo NEUROMANCER_TEST_ROOT=/run/media/<user>/rootfs ./uninstall.sh
#
# Deliberately cautious: it only removes what this project installed, and only
# restores settings it still recognises as its own. Anything you changed after
# installing is left alone.

set -euo pipefail

# ROOT lets the test suite point the script at a fake tree; empty in real use.
ROOT="${NEUROMANCER_TEST_ROOT:-}"
IMAGES_DIR="$ROOT/usr/local/share/neuromancer"
CONFIG="$ROOT/etc/pwnagotchi/config.toml"

if [[ $EUID -ne 0 && -z "$ROOT" ]]; then
    echo "This script must run as root: sudo ./uninstall.sh" >&2
    exit 1
fi

echo "==> Configuration"
if [[ -f "$CONFIG" ]]; then
    BACKUP="$CONFIG.bak.$(date +%s)"
    cp "$CONFIG" "$BACKUP"
    echo "  backup: $BACKUP"

    PREV_LANG="$(cat "$IMAGES_DIR/.previous-lang" 2>/dev/null || true)"
    PREV_LANG="${PREV_LANG:-en}"
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    OUT="$(python3 "$SCRIPT_DIR/tools/configure.py" "$CONFIG" disable "$PREV_LANG")"
    echo "  plugin disabled ($(echo "$OUT" | grep -oP 'STYLE=\K.*') style config)"
    echo "  language restored to \"$PREV_LANG\" if it was still ours"
else
    echo "  $CONFIG not found, nothing to change"
fi

echo "==> Plugin"
SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# configure.py reads both the flat and the section layout; the two known
# directories are swept below regardless, so this is belt and braces
PLUGIN_PATH="$(python3 "$SOURCE/tools/configure.py" "$CONFIG" plugins-dir 2>/dev/null || true)"
[[ -n "$PLUGIN_PATH" ]] && PLUGIN_PATH="$ROOT$PLUGIN_PATH"
REMOVED=0
for dir in "$PLUGIN_PATH" "$ROOT/usr/local/share/pwnagotchi/custom-plugins" "$ROOT/etc/pwnagotchi/custom-plugins"; do
    [[ -z "$dir" ]] && continue
    if [[ -f "$dir/neuromancer.py" ]]; then
        rm -f "$dir/neuromancer.py" "$dir/__pycache__/neuromancer."*
        echo "  removed from $dir"
        REMOVED=1
    fi
done
[[ "$REMOVED" == "0" ]] && echo "  no plugin file found"

echo "==> Voice"
LOCALE_FOUND=0
for dir in "$ROOT"/opt/.pwn/lib/python3*/site-packages/pwnagotchi/locale \
           "$ROOT"/home/pi/.pwn/lib/python3*/site-packages/pwnagotchi/locale \
           "$ROOT"/usr/local/lib/python3*/dist-packages/pwnagotchi/locale \
           "$ROOT"/usr/lib/python3*/dist-packages/pwnagotchi/locale
do
    if [[ -d "$dir/neuromancer" ]]; then
        rm -rf "$dir/neuromancer"
        echo "  removed $dir/neuromancer"
        LOCALE_FOUND=1
    fi
done
[[ "$LOCALE_FOUND" == "0" ]] && echo "  no neuromancer locale found"

echo "==> Images"
if [[ -d "$IMAGES_DIR" ]]; then
    rm -rf "$IMAGES_DIR"
    echo "  removed $IMAGES_DIR"
else
    echo "  $IMAGES_DIR already gone"
fi

echo "==> Trace file"
for boot in "$ROOT/boot/firmware" "$ROOT/boot"; do
    if [[ -f "$boot/neuromancer-trace.txt" ]]; then
        rm -f "$boot/neuromancer-trace.txt"
        echo "  removed $boot/neuromancer-trace.txt"
        break
    fi
done

echo
echo "Done. Restart to go back to the stock pwnagotchi:"
echo "    sudo systemctl restart pwnagotchi"
echo
echo "Your configuration backups are still there:"
echo "    ls -la $CONFIG.bak.*"
