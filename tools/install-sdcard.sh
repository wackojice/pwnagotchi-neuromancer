#!/usr/bin/env bash
#
# Installe le theme sur la carte SD du pwnagotchi, montee sur cette machine.
# Utile quand on n'a pas de cable micro-USB avec fils de donnees, ou pour un
# premier essai : si le Pi ne demarre pas, on remonte la carte et on defait.
#
#   sudo ./tools/install-sdcard.sh /run/media/<user>/rootfs
#
# Le Pi doit etre eteint et la carte inseree dans ce PC.

set -euo pipefail

RACINE_SD="${1:-}"
SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ $EUID -ne 0 ]]; then
    echo "Ce script doit tourner en root : sudo $0 <point-de-montage>" >&2
    exit 1
fi

if [[ -z "$RACINE_SD" || ! -d "$RACINE_SD" ]]; then
    echo "Usage : sudo $0 <point-de-montage-de-la-partition-rootfs>" >&2
    echo "Exemple : sudo $0 /run/media/$SUDO_USER/rootfs" >&2
    exit 1
fi

CONFIG="$RACINE_SD/etc/pwnagotchi/config.toml"
if [[ ! -f "$CONFIG" ]]; then
    echo "Pas de $CONFIG : ce n'est pas la partition racine d'un pwnagotchi." >&2
    exit 1
fi

echo "==> Cible : $RACINE_SD"
grep -E '^main\.name|^ui\.display\.type|^ui\.invert' "$CONFIG" | sed 's/^/    /'

# --- images
DEST_IMG="$RACINE_SD/usr/local/share/neuromancer"
echo "==> Images -> /usr/local/share/neuromancer"
mkdir -p "$DEST_IMG"
cp "$SOURCE"/images/*.png "$DEST_IMG/"

# --- plugin
# Le dossier scanne depend de la version : main.custom_plugins vaut
# /usr/local/share/pwnagotchi/custom-plugins/ sur les 2.x, et
# /etc/pwnagotchi/custom-plugins/ sur les forks recents. On le lit plutot que
# de le deviner : d'abord la config de l'utilisateur, puis les defauts livres.
CHEMIN_PLUG="$(grep -hoP '^\s*main\.custom_plugins\s*=\s*"\K[^"]+' "$CONFIG" 2>/dev/null | head -1)"
if [[ -z "$CHEMIN_PLUG" ]]; then
    DEFAUTS="$(find "$RACINE_SD" -maxdepth 9 -name 'defaults.toml' -path '*pwnagotchi*' 2>/dev/null | head -1)"
    CHEMIN_PLUG="$(grep -hoP '^\s*main\.custom_plugins\s*=\s*"\K[^"]+' "$DEFAUTS" 2>/dev/null | head -1)"
fi
CHEMIN_PLUG="${CHEMIN_PLUG:-/usr/local/share/pwnagotchi/custom-plugins/}"
DEST_PLUG="$RACINE_SD/${CHEMIN_PLUG#/}"
echo "==> Plugin -> $CHEMIN_PLUG"
mkdir -p "$DEST_PLUG"
cp "$SOURCE/neuromancer.py" "$DEST_PLUG/"
# nettoyage d'un exemplaire laisse dans l'autre emplacement possible
for autre in "$RACINE_SD/usr/local/share/pwnagotchi/custom-plugins" \
             "$RACINE_SD/etc/pwnagotchi/custom-plugins"; do
    if [[ "$autre" != "${DEST_PLUG%/}" && -f "$autre/neuromancer.py" ]]; then
        rm -f "$autre/neuromancer.py" "$autre/__pycache__/neuromancer."*
        echo "    exemplaire retire de ${autre#$RACINE_SD}"
    fi
done

# --- voix : le paquet vit souvent dans un venv
echo "==> Voix Neuromancer"
LOCALE_PWN="$(find "$RACINE_SD" -maxdepth 9 -type d -path '*pwnagotchi/locale' 2>/dev/null | head -1)"
if [[ -n "$LOCALE_PWN" ]]; then
    mkdir -p "$LOCALE_PWN/neuromancer/LC_MESSAGES"
    cp "$SOURCE/locale/neuromancer/LC_MESSAGES/voice.mo" "$LOCALE_PWN/neuromancer/LC_MESSAGES/"
    echo "    installee dans ${LOCALE_PWN#$RACINE_SD}/neuromancer"
    VOIX_OK=1
else
    echo "    ! dossier locale introuvable, voix non installee" >&2
    VOIX_OK=0
fi

# --- configuration
echo "==> Configuration"
cp "$CONFIG" "$CONFIG.bak.$(date +%s)"
echo "    sauvegarde : $(basename "$CONFIG").bak.*"

if grep -q '^main\.plugins\.neuromancer\.enabled' "$CONFIG"; then
    sed -i 's/^main\.plugins\.neuromancer\.enabled.*/main.plugins.neuromancer.enabled = true/' "$CONFIG"
else
    printf '\nmain.plugins.neuromancer.enabled = true\n' >> "$CONFIG"
fi
echo "    plugin active"

if [[ "$VOIX_OK" == "1" ]]; then
    if grep -qE '^main\.lang' "$CONFIG"; then
        sed -i 's/^main\.lang.*/main.lang = "neuromancer"/' "$CONFIG"
    else
        printf 'main.lang = "neuromancer"\n' >> "$CONFIG"
    fi
    echo "    langue basculee sur neuromancer"
fi

sync
echo
echo "Termine. Demonte proprement la carte, remets-la dans le Pi et allume-le :"
echo "    udisksctl unmount -b <partition>"
echo
echo "Puis, une fois le Pi joignable :"
echo "    journalctl -u pwnagotchi -f | grep neuromancer"
