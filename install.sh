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
DOSSIER_PLUGINS="/usr/local/share/pwnagotchi/custom-plugins"
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

echo "==> Installation du plugin dans $DOSSIER_PLUGINS"
mkdir -p "$DOSSIER_PLUGINS"
cp "$SOURCE/neuromancer.py" "$DOSSIER_PLUGINS/"

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

echo "==> Redemarrage du service"
systemctl restart pwnagotchi

echo
echo "Termine. Surveiller le demarrage avec :"
echo "  journalctl -u pwnagotchi -f | grep neuromancer"
