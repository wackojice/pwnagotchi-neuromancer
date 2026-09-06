#!/usr/bin/env bash
#
# Installe le theme Neuromancer sur un pwnagotchi.
# A lancer SUR le pwnagotchi (pas depuis le PC).
#
#   curl -sL https://raw.githubusercontent.com/wackojice/pwnagotchi-neuromancer/main/install.sh | sudo bash
#
# ou, depuis une copie locale du depot :
#
#   sudo ./install.sh

set -euo pipefail

DOSSIER_IMAGES="/usr/local/share/neuromancer"
# le dossier scanne depend de la version : lu depuis la config, sinon les
# defauts livres, sinon l'emplacement historique des 2.x
DOSSIER_PLUGINS=""
CONFIG="/etc/pwnagotchi/config.toml"
SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $EUID -ne 0 ]]; then
    echo "Ce script doit tourner en root : sudo ./install.sh" >&2
    exit 1
fi

if [[ ! -f "$SOURCE/neuromancer.py" ]]; then
    echo "neuromancer.py introuvable dans $SOURCE" >&2
    exit 1
fi

echo "==> Installation des images dans $DOSSIER_IMAGES"
mkdir -p "$DOSSIER_IMAGES"
cp "$SOURCE"/images/*.png "$DOSSIER_IMAGES/"

DOSSIER_PLUGINS="$(grep -hoP '^\s*main\.custom_plugins\s*=\s*"\K[^"]+' "$CONFIG" 2>/dev/null | head -1)"
if [[ -z "$DOSSIER_PLUGINS" ]]; then
    DEFAUTS="$(find / -maxdepth 9 -name 'defaults.toml' -path '*pwnagotchi*' -not -path '*/proc/*' 2>/dev/null | head -1)"
    DOSSIER_PLUGINS="$(grep -hoP '^\s*main\.custom_plugins\s*=\s*"\K[^"]+' "$DEFAUTS" 2>/dev/null | head -1)"
fi
DOSSIER_PLUGINS="${DOSSIER_PLUGINS:-/usr/local/share/pwnagotchi/custom-plugins/}"

echo "==> Installation du plugin dans $DOSSIER_PLUGINS"
mkdir -p "$DOSSIER_PLUGINS"
cp "$SOURCE/neuromancer.py" "$DOSSIER_PLUGINS/"
rm -rf "$DOSSIER_PLUGINS/__pycache__"
# retire un exemplaire laisse dans l'autre emplacement possible
for autre in /usr/local/share/pwnagotchi/custom-plugins /etc/pwnagotchi/custom-plugins; do
    if [[ "$autre" != "${DOSSIER_PLUGINS%/}" && -f "$autre/neuromancer.py" ]]; then
        rm -f "$autre/neuromancer.py" "$autre/__pycache__/neuromancer."* 2>/dev/null || true
        echo "  exemplaire retire de $autre"
    fi
done

echo "==> Installation de la voix Neuromancer"
# pwnagotchi vit souvent dans un venv (/home/pi/.pwn) : l'import direct echoue
# alors. On cherche donc le paquet sur le disque, venv compris.
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
    LOCALE_PWN="$(find / -maxdepth 8 -type d -path '*pwnagotchi/locale' -not -path '*/proc/*' 2>/dev/null | head -1)"
fi
if [[ -n "$LOCALE_PWN" && -d "$LOCALE_PWN" ]]; then
    mkdir -p "$LOCALE_PWN/neuromancer/LC_MESSAGES"
    cp "$SOURCE/locale/neuromancer/LC_MESSAGES/voice.mo" "$LOCALE_PWN/neuromancer/LC_MESSAGES/"
    echo "  voix installee dans $LOCALE_PWN/neuromancer"
    VOIX_OK=1
else
    echo "  ! dossier locale de pwnagotchi introuvable, voix non installee" >&2
    VOIX_OK=0
fi

echo "==> Activation dans $CONFIG"
if [[ ! -f "$CONFIG" ]]; then
    echo "  $CONFIG introuvable — active le plugin a la main :" >&2
    echo "  main.plugins.neuromancer.enabled = true" >&2
elif grep -q '^main\.plugins\.neuromancer\.enabled' "$CONFIG"; then
    sed -i 's/^main\.plugins\.neuromancer\.enabled.*/main.plugins.neuromancer.enabled = true/' "$CONFIG"
    echo "  ligne existante mise a jour"
else
    cp "$CONFIG" "$CONFIG.bak.$(date +%s)"
    printf '\nmain.plugins.neuromancer.enabled = true\n' >> "$CONFIG"
    echo "  ligne ajoutee (sauvegarde : $CONFIG.bak.*)"
fi

if [[ "${VOIX_OK:-0}" == "1" ]]; then
    if grep -qE '^main\.lang' "$CONFIG" 2>/dev/null; then
        sed -i 's/^main\.lang.*/main.lang = "neuromancer"/' "$CONFIG"
        echo "  langue basculee sur neuromancer"
    else
        printf 'main.lang = "neuromancer"\n' >> "$CONFIG"
        echo "  langue neuromancer ajoutee"
    fi
fi

echo "==> Redemarrage du service"
systemctl restart pwnagotchi

echo
echo "Termine. Surveiller le demarrage avec :"
echo "  journalctl -u pwnagotchi -f | grep neuromancer"
