#!/usr/bin/env bash
#
# Installs the Neuromancer theme on a pwnagotchi.
# Run this ON the pwnagotchi (not from your computer), from a clone of the
# repository -- the script needs the images and the locale that sit next to it:
#
#   git clone https://github.com/wackojice/pwnagotchi-neuromancer.git
#   cd pwnagotchi-neuromancer
#   sudo ./install.sh

set -euo pipefail

IMAGES_DIR="/usr/local/share/neuromancer"
# The scanned directory depends on the version: read it from the config,
# then from the shipped defaults, then fall back to the 2.x location.
PLUGINS_DIR=""
CONFIG="/etc/pwnagotchi/config.toml"
SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $EUID -ne 0 ]]; then
    echo "This script must run as root: sudo ./install.sh" >&2
    exit 1
fi

if [[ ! -f "$SOURCE/neuromancer.py" ]]; then
    echo "neuromancer.py not found in $SOURCE" >&2
    exit 1
fi

echo "==> Images -> $IMAGES_DIR"
mkdir -p "$IMAGES_DIR"
cp "$SOURCE"/images/*.png "$IMAGES_DIR/"

# read via configure.py: it understands both the flat and the section layout
PLUGINS_DIR="$(python3 "$SOURCE/tools/configure.py" "$CONFIG" plugins-dir 2>/dev/null || true)"
if [[ -z "$PLUGINS_DIR" ]]; then
    DEFAULTS="$(find / -maxdepth 9 -name 'defaults.toml' -path '*pwnagotchi*' -not -path '*/proc/*' 2>/dev/null | head -1 || true)"
    if [[ -n "$DEFAULTS" ]]; then
        PLUGINS_DIR="$(python3 "$SOURCE/tools/configure.py" "$DEFAULTS" plugins-dir 2>/dev/null || true)"
    fi
fi
PLUGINS_DIR="${PLUGINS_DIR:-/usr/local/share/pwnagotchi/custom-plugins/}"

echo "==> Plugin -> $PLUGINS_DIR"
mkdir -p "$PLUGINS_DIR"
cp "$SOURCE/neuromancer.py" "$PLUGINS_DIR/"
rm -rf "$PLUGINS_DIR/__pycache__"
# remove a copy left in the other possible location
for other in /usr/local/share/pwnagotchi/custom-plugins /etc/pwnagotchi/custom-plugins; do
    if [[ "$other" != "${PLUGINS_DIR%/}" && -f "$other/neuromancer.py" ]]; then
        rm -f "$other/neuromancer.py" "$other/__pycache__/neuromancer."* 2>/dev/null || true
        echo "  removed stale copy from $other"
    fi
done

echo "==> Neuromancer voice"
# pwnagotchi often lives in a venv (/home/pi/.pwn), where a plain import
# fails. So look for the package on disk, venv included.
LOCALE_DIR=""
for candidat in \
    "$(python3 -c 'import pwnagotchi, os; print(os.path.join(os.path.dirname(pwnagotchi.__file__), "locale"))' 2>/dev/null || true)" \
    /opt/.pwn/lib/python3*/site-packages/pwnagotchi/locale \
    /home/pi/.pwn/lib/python3*/site-packages/pwnagotchi/locale \
    /usr/local/lib/python3*/dist-packages/pwnagotchi/locale \
    /usr/lib/python3*/dist-packages/pwnagotchi/locale
do
    if [[ -n "$candidat" && -d "$candidat" ]]; then LOCALE_DIR="$candidat"; break; fi
done
if [[ -z "$LOCALE_DIR" ]]; then
    LOCALE_DIR="$(find / -maxdepth 8 -type d -path '*pwnagotchi/locale' -not -path '*/proc/*' 2>/dev/null | head -1 || true)"
fi
if [[ -n "$LOCALE_DIR" && -d "$LOCALE_DIR" ]]; then
    mkdir -p "$LOCALE_DIR/neuromancer/LC_MESSAGES"
    cp "$SOURCE/locale/neuromancer/LC_MESSAGES/voice.mo" "$LOCALE_DIR/neuromancer/LC_MESSAGES/"
    echo "  installed in $LOCALE_DIR/neuromancer"
    VOICE_OK=1
else
    echo "  ! pwnagotchi locale directory not found, voice not installed" >&2
    VOICE_OK=0
fi

echo "==> Configuration"
if [[ ! -f "$CONFIG" ]]; then
    echo "  $CONFIG not found - enable the plugin manually:" >&2
    echo "  main.plugins.neuromancer.enabled = true" >&2
else
    # Back up before touching anything, on every path. A reinstall used to skip
    # this, which is exactly when there is most to lose.
    BACKUP="$CONFIG.bak.$(date +%s)"
    cp "$CONFIG" "$BACKUP"
    echo "  backup: $BACKUP"

    # config.toml comes in two styles (flat keys, or [sections]) and pwnagotchi
    # rewrites it into the second on its own. Appending a flat key to a file
    # using sections would silently attach it to the last section, leaving the
    # plugin disabled. configure.py handles both.
    OUT="$(python3 "$SOURCE/tools/configure.py" "$CONFIG" enable)"
    echo "  plugin enabled ($(echo "$OUT" | grep -oP 'STYLE=\K.*') style config)"

    PREV_LANG="$(echo "$OUT" | grep -oP 'PREVIOUS_LANG=\K.*')"
    if [[ "${VOICE_OK:-0}" == "1" && -n "$PREV_LANG" ]]; then
        printf '%s\n' "$PREV_LANG" > "$IMAGES_DIR/.previous-lang"
        echo "  language was \"$PREV_LANG\", switched to neuromancer"
    elif [[ "${VOICE_OK:-0}" == "1" ]]; then
        echo "  language already neuromancer"
    fi
fi

echo "==> Restarting the service"
systemctl restart pwnagotchi

echo
echo "Done. Watch it start with:"
echo "  journalctl -u pwnagotchi -f | grep neuromancer"
