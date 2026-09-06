#!/usr/bin/env python3
"""
Previsualise le rendu du theme sans pwnagotchi ni materiel.

Recompose un ecran 250x122 a l'identique du layout waveshare2in13_V2 :
memes coordonnees, memes polices, meme mode 1 bit. Sort un PNG agrandi.

    ./tools/preview.py                 # planche de tous les etats
    ./tools/preview.py awake           # un seul etat, en grand
    ./tools/preview.py ice --zoom 6

Les sorties vont dans preview/ (ignore par git).
"""

import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFont

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGES = os.path.join(RACINE, 'images')
SORTIE = os.path.join(RACINE, 'preview')

# --- layout waveshare2in13_V2, recopie de pwnagotchi/ui/hw/waveshare2in13_V2.py
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

# --- constantes du plugin (neuromancer.py)
HAUT = 16
COL_D = 95
PORTRAIT_X = 6

# --- textes d'exemple
DEMO = {
    'channel': 'CH 11',
    'aps': 'APS 11 (25)',
    'uptime': 'UP 00:09',
    'shakes': 'PWND 0 (12)',
    'mode': 'AUTO',
    'name': 'wackogotchi>',
    'status': "Hi! I'm Case",
}


def charger_polices():
    """Reproduit fonts.setup(10, 8, 10, 35, 25, 9) du layout V2."""
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
                print('  ! DejaVuSansMono absent, repli sur %s' % os.path.basename(normal))
                print('    installe-la pour un rendu fidele : sudo pacman -S ttf-dejavu')
            return polices
        except OSError:
            continue
    sys.exit('Aucune police monospace utilisable trouvee.')


def composer(etat, polices, ssid='LINKSYS_5G'):
    """Rend un ecran complet pour un etat donne."""
    ecran = Image.new('1', (LARGEUR, HAUTEUR), 1)   # 1 = blanc
    d = ImageDraw.Draw(ecran)

    # les deux filets horizontaux
    d.line([0, LIGNE_HAUT, LARGEUR, LIGNE_HAUT], fill=0)
    d.line([0, LIGNE_BAS, LARGEUR, LIGNE_BAS], fill=0)

    # bandeaux haut et bas
    for cle in ('channel', 'aps', 'uptime'):
        d.text(POS[cle], DEMO[cle], font=polices['bold'], fill=0)
    for cle in ('shakes', 'mode'):
        d.text(POS[cle], DEMO[cle], font=polices['bold'], fill=0)

    # le portrait
    chemin = os.path.join(IMAGES, etat + '.png')
    if not os.path.exists(chemin):
        sys.exit('image introuvable : %s' % chemin)
    portrait = Image.open(chemin).convert('1')
    ecran.paste(portrait, (PORTRAIT_X, HAUT))

    # colonne de droite
    d.text((COL_D, 16), DEMO['name'], font=polices['bold'], fill=0)
    d.text((COL_D, 34), DEMO['status'], font=polices['medium'], fill=0)

    # lignes ajoutees par le plugin, remplies seulement en mode ice
    if etat == 'ice':
        d.text((COL_D, 62), 'ICE BROKEN', font=polices['bold'], fill=0)
        d.text((COL_D, 78), ssid[:16], font=polices['medium'], fill=0)

    return ecran


def agrandir(img, zoom):
    return img.convert('L').resize(
        (img.width * zoom, img.height * zoom), Image.NEAREST)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('etat', nargs='?', help="etat a rendre (defaut : tous)")
    p.add_argument('--zoom', type=int, default=4, help='facteur d agrandissement')
    args = p.parse_args()

    os.makedirs(SORTIE, exist_ok=True)
    polices = charger_polices()

    etats = ([args.etat] if args.etat else
             sorted(f[:-4] for f in os.listdir(IMAGES) if f.endswith('.png')))

    rendus = []
    for etat in etats:
        img = composer(etat, polices)
        chemin = os.path.join(SORTIE, 'ecran_%s.png' % etat)
        agrandir(img, args.zoom).save(chemin)
        print('  %-8s -> %s' % (etat, os.path.relpath(chemin, RACINE)))
        rendus.append((etat, img))

    # planche verticale de tous les etats
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
