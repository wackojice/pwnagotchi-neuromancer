import os
import time
import logging

from PIL import Image

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.faces as faces
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import Bitmap, LabeledValue


# coordonnees calees sur le layout officiel waveshare2in13_V2 :
# ecran 250x122, filet haut y=14, filet bas y=108
HAUT = 16      # sommet du portrait, juste sous le filet du haut
COL_D = 95     # colonne de droite, apres le portrait (x 6-82)


class Neuromancer(plugins.Plugin):
    __author__ = 'wackojice'
    __version__ = '2.0.0'
    __license__ = 'GPL3'
    __description__ = 'Faces Neuromancer + ecran ICE BROKEN (Waveshare 2.13 v2, 250x122)'

    DOSSIER = '/usr/local/share/neuromancer'
    DUREE_PWN = 8          # secondes d'affichage apres un handshake
    DEFAUT = 'awake'       # image de repli si un etat n'a pas de fichier

    # chaque etat du pwnagotchi -> nom de fichier (sans .png)
    # plusieurs etats peuvent pointer vers la meme image, c'est voulu
    MAPPING = {
        faces.LOOK_R: 'look_r',
        faces.LOOK_R_HAPPY: 'look_r',
        faces.LOOK_L: 'look_l',
        faces.LOOK_L_HAPPY: 'look_l',
        faces.SLEEP: 'sleep',
        faces.SLEEP2: 'sleep',
        faces.AWAKE: 'awake',
        faces.COOL: 'awake',
        faces.INTENSE: 'awake',
        faces.SMART: 'awake',
        faces.MOTIVATED: 'awake',
        faces.HAPPY: 'happy',
        faces.GRATEFUL: 'happy',
        faces.EXCITED: 'happy',
        faces.FRIEND: 'happy',
        faces.BORED: 'sleep',
        faces.LONELY: 'sleep',
        faces.SAD: 'sleep',
        faces.DEMOTIVATED: 'sleep',
    }

    def __init__(self):
        self.images = {}
        self.bitmap = None
        self.jusqua = 0
        self.ssid = ''
        self.affiche = None     # nom de l'image actuellement posee

    # ---------------------------------------------------------------- chargement

    def on_loaded(self):
        noms = set(self.MAPPING.values()) | {'ice', self.DEFAUT}
        for nom in noms:
            chemin = os.path.join(self.DOSSIER, nom + '.png')
            try:
                self.images[nom] = Image.open(chemin).convert('1')
            except Exception as e:
                logging.warning('[neuromancer] %s absent (%s)' % (chemin, e))

        if self.DEFAUT not in self.images:
            logging.error('[neuromancer] %s.png est obligatoire, plugin inactif' % self.DEFAUT)
            self.images = {}
            return

        logging.info('[neuromancer] %d images chargees : %s'
                     % (len(self.images), ', '.join(sorted(self.images))))

    # ---------------------------------------------------------------- interface

    def on_ui_setup(self, ui):
        if not self.images:
            return

        # 'face' reste en place : le coeur ecrit dedans et on le lit dans
        # on_ui_update. On l'expulse simplement hors du cadre (h = 122).
        self._deplacer(ui, 'face', (0, 300))

        # le layout officiel met 'name' en (5,20) et 'status' en (125,20),
        # or notre portrait occupe x 6-82 : on rapatrie tout en colonne droite
        self._deplacer(ui, 'name', (COL_D, 16))
        self._deplacer(ui, 'status', (COL_D, 34))

        for element in ('friend_face', 'friend_name'):
            try:
                ui.remove_element(element)
            except Exception:
                pass

        self.bitmap = Bitmap(os.path.join(self.DOSSIER, self.DEFAUT + '.png'),
                             xy=(6, HAUT))
        ui.add_element('nm_face', self.bitmap)

        ui.add_element('nm_statut', LabeledValue(
            color=0, label='', value='', position=(COL_D, 62),
            label_font=fonts.Bold, text_font=fonts.Medium))
        ui.add_element('nm_cible', LabeledValue(
            color=0, label='', value='', position=(COL_D, 78),
            label_font=fonts.Bold, text_font=fonts.Medium))

    @staticmethod
    def _deplacer(ui, nom, xy):
        try:
            ui._state._state[nom].xy = xy
        except Exception as e:
            logging.warning('[neuromancer] deplacement de %s impossible : %s' % (nom, e))

    def on_unload(self, ui):
        with ui._lock:
            for element in ('nm_face', 'nm_statut', 'nm_cible'):
                try:
                    ui.remove_element(element)
                except Exception:
                    pass

    # ---------------------------------------------------------------- evenements

    def on_handshake(self, agent, filename, access_point, client_station):
        if 'ice' not in self.images:
            return
        self.ssid = (access_point or {}).get('hostname') or '???'
        self.jusqua = time.time() + self.DUREE_PWN
        logging.info('[neuromancer] ICE BROKEN sur %s' % self.ssid)

    def on_ui_update(self, ui):
        if self.bitmap is None or not self.images:
            return

        if time.time() < self.jusqua:
            voulu = 'ice'
        else:
            # on lit ce que le coeur vient de decider, et on traduit
            try:
                courant = ui.get('face')
            except Exception:
                courant = None
            voulu = self.MAPPING.get(courant, self.DEFAUT)

        if voulu not in self.images:
            voulu = self.DEFAUT

        # un refresh e-ink coute ~2 s : on ne repeint que sur changement reel
        if voulu == self.affiche:
            return
        self.affiche = voulu

        self.bitmap.image = self.images[voulu]
        if voulu == 'ice':
            ui.set('nm_statut', 'ICE BROKEN')
            ui.set('nm_cible', self.ssid[:16])
        else:
            ui.set('nm_statut', '')
            ui.set('nm_cible', '')
