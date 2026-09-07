#!/usr/bin/env bash
#
# Removes the Neuromancer theme from a pwnagotchi.
# Run this ON the pwnagotchi:
#
#   sudo ./uninstall.sh
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

    if grep -q '^main\.plugins\.neuromancer\.enabled' "$CONFIG"; then
        sed -i 's/^main\.plugins\.neuromancer\.enabled.*/main.plugins.neuromancer.enabled = false/' "$CONFIG"
        echo "  plugin disabled"
    fi

    # Only touch main.lang if it is still ours: a language set by the user after
    # installing must survive untouched.
    CURRENT_LANG="$(grep -oP '^\s*main\.lang\s*=\s*"\K[^"]+' "$CONFIG" 2>/dev/null | head -1 || true)"
    if [[ "$CURRENT_LANG" == "neuromancer" ]]; then
        PREV_LANG="$(cat "$IMAGES_DIR/.previous-lang" 2>/dev/null || true)"
        PREV_LANG="${PREV_LANG:-en}"
        sed -i "s/^main\.lang.*/main.lang = \"$PREV_LANG\"/" "$CONFIG"
        echo "  language restored to \"$PREV_LANG\""
    elif [[ -n "$CURRENT_LANG" ]]; then
        echo "  language is \"$CURRENT_LANG\", not ours: left untouched"
    fi
else
    echo "  $CONFIG not found, nothing to change"
fi

echo "==> Plugin"
PLUGIN_PATH="$(grep -oP '^\s*main\.custom_plugins\s*=\s*"\K[^"]+' "$CONFIG" 2>/dev/null | head -1 || true)"
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
for dir in "$ROOT"/home/pi/.pwn/lib/python3*/site-packages/pwnagotchi/locale \
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
