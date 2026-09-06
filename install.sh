#!/usr/bin/env bash
#
# Installs the Neuromancer theme on a pwnagotchi.
# Run this ON the pwnagotchi (not from your computer).
#
#   curl -sL https://raw.githubusercontent.com/wackojice/pwnagotchi-neuromancer/main/install.sh | sudo bash
#
# or, from a local clone:
#
#   sudo ./install.sh

set -euo pipefail

DOSSIER_IMAGES="/usr/local/share/neuromancer"
# The scanned directory depends on the version: read it from the config,
# then from the shipped defaults, then fall back to the 2.x location.
DOSSIER_PLUGINS=""
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

echo "==> Images -> $DOSSIER_IMAGES"
mkdir -p "$DOSSIER_IMAGES"
cp "$SOURCE"/images/*.png "$DOSSIER_IMAGES/"

DOSSIER_PLUGINS="$(grep -hoP '^\s*main\.custom_plugins\s*=\s*"\K[^"]+' "$CONFIG" 2>/dev/null | head -1 || true)"
if [[ -z "$DOSSIER_PLUGINS" ]]; then
    DEFAUTS="$(find / -maxdepth 9 -name 'defaults.toml' -path '*pwnagotchi*' -not -path '*/proc/*' 2>/dev/null | head -1 || true)"
    DOSSIER_PLUGINS="$(grep -hoP '^\s*main\.custom_plugins\s*=\s*"\K[^"]+' "$DEFAUTS" 2>/dev/null | head -1 || true)"
fi
DOSSIER_PLUGINS="${DOSSIER_PLUGINS:-/usr/local/share/pwnagotchi/custom-plugins/}"

echo "==> Plugin -> $DOSSIER_PLUGINS"
mkdir -p "$DOSSIER_PLUGINS"
cp "$SOURCE/neuromancer.py" "$DOSSIER_PLUGINS/"
rm -rf "$DOSSIER_PLUGINS/__pycache__"
# remove a copy left in the other possible location
for autre in /usr/local/share/pwnagotchi/custom-plugins /etc/pwnagotchi/custom-plugins; do
    if [[ "$autre" != "${DOSSIER_PLUGINS%/}" && -f "$autre/neuromancer.py" ]]; then
        rm -f "$autre/neuromancer.py" "$autre/__pycache__/neuromancer."* 2>/dev/null || true
        echo "  removed stale copy from $autre"
    fi
done

echo "==> Neuromancer voice"
# pwnagotchi often lives in a venv (/home/pi/.pwn), where a plain import
# fails. So look for the package on disk, venv included.
LOCALE_PWN=""
for candidat in \
    "$(python3 -c 'import pwnagotchi, os; print(os.path.join(os.path.dirname(pwnagotchi.__file__), "locale"))' 2>/dev/null || true)" \
    /home/pi/.pwn/lib/python3*/site-packages/pwnagotchi/locale \
    /usr/local/lib/python3*/dist-packages/pwnagotchi/locale \
    /usr/lib/python3*/dist-packages/pwnagotchi/locale
do
    if [[ -n "$candidat" && -d "$candidat" ]]; then LOCALE_PWN="$candidat"; break; fi
done
if [[ -z "$LOCALE_PWN" ]]; then
    LOCALE_PWN="$(find / -maxdepth 8 -type d -path '*pwnagotchi/locale' -not -path '*/proc/*' 2>/dev/null | head -1 || true)"
fi
if [[ -n "$LOCALE_PWN" && -d "$LOCALE_PWN" ]]; then
    mkdir -p "$LOCALE_PWN/neuromancer/LC_MESSAGES"
    cp "$SOURCE/locale/neuromancer/LC_MESSAGES/voice.mo" "$LOCALE_PWN/neuromancer/LC_MESSAGES/"
    echo "  installed in $LOCALE_PWN/neuromancer"
    VOIX_OK=1
else
    echo "  ! pwnagotchi locale directory not found, voice not installed" >&2
    VOIX_OK=0
fi

echo "==> Configuration"
if [[ ! -f "$CONFIG" ]]; then
    echo "  $CONFIG not found - enable the plugin manually:" >&2
    echo "  main.plugins.neuromancer.enabled = true" >&2
elif grep -q '^main\.plugins\.neuromancer\.enabled' "$CONFIG"; then
    sed -i 's/^main\.plugins\.neuromancer\.enabled.*/main.plugins.neuromancer.enabled = true/' "$CONFIG"
    echo "  existing line updated"
else
    cp "$CONFIG" "$CONFIG.bak.$(date +%s)"
    printf '\nmain.plugins.neuromancer.enabled = true\n' >> "$CONFIG"
    echo "  line added (backup: $CONFIG.bak.*)"
fi

if [[ "${VOIX_OK:-0}" == "1" ]]; then
    if grep -qE '^main\.lang' "$CONFIG" 2>/dev/null; then
        sed -i 's/^main\.lang.*/main.lang = "neuromancer"/' "$CONFIG"
        echo "  language switched to neuromancer"
    else
        printf 'main.lang = "neuromancer"\n' >> "$CONFIG"
        echo "  neuromancer language added"
    fi
fi

echo "==> Restarting the service"
systemctl restart pwnagotchi

echo
echo "Done. Watch it start with:"
echo "  journalctl -u pwnagotchi -f | grep neuromancer"
