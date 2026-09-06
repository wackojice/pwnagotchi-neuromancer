#!/usr/bin/env python3
"""
Preview the theme without a pwnagotchi or any hardware.

Recomposes a 250x122 screen exactly like the waveshare2in13_V2 layout: same
coordinates, same fonts, same 1-bit mode. Writes an enlarged PNG.

    ./tools/preview.py                 # contact sheet of every state
    ./tools/preview.py awake           # a single state, enlarged
    ./tools/preview.py ice --zoom 6

Output goes to preview/ (git-ignored).
"""

import argparse
import gettext
import os
import sys
from textwrap import TextWrapper

from PIL import Image, ImageDraw, ImageFont

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGES = os.path.join(RACINE, 'images')
SORTIE = os.path.join(RACINE, 'preview')

# --- waveshare2in13_V2 layout, copied from pwnagotchi/ui/hw/waveshare2in13_V2.py
LARGEUR, HAUTEUR = 250, 122
LIGNE_HAUT = 14
LIGNE_BAS = 108
POS = {
    'channel': (0, 0),
    'aps': (28, 0),
    'uptime': (185, 0),
    'shakes': (0, 109),
    'mode': (225, 109),
}

# --- plugin constants (neuromancer.py)
HAUT = 16
COL_D = 95
MAX_STATUS = 20   # layout['status']['max'] from the V2 driver
PORTRAIT_X = 6

# --- sample texts
# labels as the plugin rewrites them (see LABELS in neuromancer.py)
# format: (label, value, x, spacing)
DEMO = {
    'channel': ('CH', '11', 0, 5),
    'aps': ('NODES', '9 (19)', 40, 12),
    'uptime': ('UP', '00:09:13', 185, 5),
    'shakes': ('PWND', '1 (12)', 0, 8),
    'mode': ('AUTO', '', 225, 0),
    'name': 'Case>',
    'deck': 'DECK 44°C',
}

# one line per state, taken from the real neuromancer locale
REPLIQUES = {
    'awake':  "Sniff. Deauth. Repeat.",
    'happy':  "I'm living the life!",
    'look_l': "So many networks!!!",
    'look_r': "Associating to {what}",
    'sleep':  "I dreamed of electric sheep",
    'ice':    "Cool, we got {num} new handshake{plural}!",
}


def charger_voix():
    """Load the repo's neuromancer locale, falling back to English."""
    chemin = os.path.join(RACINE, 'locale')
    try:
        t = gettext.translation('voice', chemin, languages=['neuromancer'])
        return t.gettext
    except OSError:
        print('  ! neuromancer locale missing, using English text')
        return lambda s: s


def statut(etat, _):
    """Render this state's line, placeholders filled in."""
    brut = _(REPLIQUES.get(etat, "Sniff. Deauth. Repeat."))
    return brut.format(what='LINKSYS_5G', num=3, plural='s',
                       secs=30, name='pwny42', mac='AA:BB:CC')


def charger_polices():
    """Mirrors fonts.setup(10, 8, 10, 35, 25, 9) from the V2 layout."""
    candidats = [
        ('DejaVuSansMono.ttf', 'DejaVuSansMono-Bold.ttf'),
        ('/usr/share/fonts/TTF/DejaVuSansMono.ttf',
         '/usr/share/fonts/TTF/DejaVuSansMono-Bold.ttf'),
        ('LiberationMono-Regular.ttf', 'LiberationMono-Bold.ttf'),
        ('NotoSansMono-Regular.ttf', 'NotoSansMono-Bold.ttf'),
    ]
    for normal, gras in candidats:
        try:
            polices = {
                'small': ImageFont.truetype(normal, 9),
                'medium': ImageFont.truetype(normal, 10),
                'bold_small': ImageFont.truetype(gras, 8),
                'bold': ImageFont.truetype(gras, 10),
            }
            if 'DejaVu' not in normal:
                print('  ! DejaVuSansMono missing, falling back to %s' % os.path.basename(normal))
                print('    install it for a faithful render: sudo pacman -S ttf-dejavu')
            return polices
        except OSError:
            continue
    sys.exit('No usable monospace font found.')


def composer(etat, polices, _, ssid='LINKSYS_5G'):
    """Render a full screen for one state."""
    ecran = Image.new('1', (LARGEUR, HAUTEUR), 1)   # 1 = blanc
    d = ImageDraw.Draw(ecran)

    # the two horizontal rules
    d.line([0, LIGNE_HAUT, LARGEUR, LIGNE_HAUT], fill=0)
    d.line([0, LIGNE_BAS, LARGEUR, LIGNE_BAS], fill=0)

    # top and bottom bars, drawn like LabeledValue: bold label, then the
    # value at x + spacing + 5 * len(label)
    for cle in ('channel', 'aps', 'uptime', 'shakes', 'mode'):
        libelle, valeur, x, espacement = DEMO[cle]
        y = POS[cle][1]
        d.text((x, y), libelle, font=polices['bold'], fill=0)
        if valeur:
            d.text((x + espacement + 5 * len(libelle), y), valeur,
                   font=polices['medium'], fill=0)

    # the portrait
    path = os.path.join(IMAGES, etat + '.png')
    if not os.path.exists(path):
        sys.exit('image not found: %s' % path)
    portrait = Image.open(path).convert('1')
    ecran.paste(portrait, (PORTRAIT_X, HAUT))

    # right-hand column
    d.text((COL_D, 16), DEMO['name'], font=polices['bold'], fill=0)
    # pwnagotchi wraps the status with TextWrapper(width=20)
    texte = statut(etat, _)
    lignes = TextWrapper(width=MAX_STATUS, replace_whitespace=False).wrap(texte)
    y = 34
    for ligne in lignes[:2]:
        d.text((COL_D, y), ligne, font=polices['medium'], fill=0)
        y += 12

    # lines added by the plugin, filled only in ice mode
    d.text((COL_D, 62), DEMO['deck'], font=polices['medium'], fill=0)
    if etat == 'ice':
        d.text((COL_D, 78), 'ICE BROKEN', font=polices['bold'], fill=0)
        d.text((COL_D, 94), ssid[:16], font=polices['medium'], fill=0)

    return ecran


def agrandir(img, zoom):
    return img.convert('L').resize(
        (img.width * zoom, img.height * zoom), Image.NEAREST)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('etat', nargs='?', help='state to render (default: all)')
    p.add_argument('--zoom', type=int, default=4, help='zoom factor')
    args = p.parse_args()

    os.makedirs(SORTIE, exist_ok=True)
    polices = charger_polices()
    _ = charger_voix()

    etats = ([args.etat] if args.etat else
             sorted(f[:-4] for f in os.listdir(IMAGES) if f.endswith('.png')))

    rendus = []
    for etat in etats:
        img = composer(etat, polices, _)
        chemin = os.path.join(SORTIE, 'ecran_%s.png' % etat)
        agrandir(img, args.zoom).save(chemin)
        print('  %-8s -> %s' % (etat, os.path.relpath(chemin, RACINE)))
        rendus.append((etat, img))

    # vertical contact sheet of every state
    if len(rendus) > 1:
        marge = 6
        planche = Image.new('L',
                            (LARGEUR, (HAUTEUR + marge) * len(rendus) - marge),
                            180)
        for i, (_, img) in enumerate(rendus):
            planche.paste(img.convert('L'), (0, i * (HAUTEUR + marge)))
        chemin = os.path.join(SORTIE, 'planche.png')
        agrandir(planche, args.zoom).save(chemin)
        print('\n  planche -> %s' % os.path.relpath(chemin, RACINE))


if __name__ == '__main__':
    main()
