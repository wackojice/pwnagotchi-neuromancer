import os
import time
import logging
import threading
from collections import deque

from PIL import Image

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.faces as faces
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import Bitmap, LabeledValue, Text


# Par defaut, le plugin deduit ces valeurs du layout de l'ecran detecte, ce qui
# le rend utilisable sur n'importe quel driver. Mettre un entier a la place de
# None pour forcer une valeur.
HAUT = None    # sommet du portrait ; auto = juste sous le filet du haut
COL_D = None   # colonne de texte de droite ; auto = apres le portrait
MARGE_X = 6    # decalage du portrait depuis le bord gauche
GOUTTIERE = 13 # espace entre le portrait et la colonne de texte

# valeurs de repli si le layout n'est pas lisible (calees sur waveshare2in13_V2)
HAUT_DEFAUT = 16
COL_D_DEFAUT = 95


def _trace(message):
    """Ecrit une trace immediatement sur la partition de boot.

    Le journal habituel peut rester en cache et se perdre quand le Pi est
    debranche sans arret propre. Ici on ecrit et on force le vidage, sur une
    partition FAT lisible depuis n'importe quel PC.
    """
    logging.info('[neuromancer] %s' % message)
    for dossier in ('/boot/firmware', '/boot'):
        if not os.path.isdir(dossier):
            continue
        try:
            with open(os.path.join(dossier, 'neuromancer-trace.txt'), 'a') as f:
                f.write('%s  %s\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), message))
                f.flush()
                os.fsync(f.fileno())
        except Exception:
            pass
        break


class Neuromancer(plugins.Plugin):
    __author__ = 'wackojice'
    __version__ = '3.3.1'
    __license__ = 'GPL3'
    __description__ = 'Visages et voix Neuromancer + ecran ICE BROKEN, layout adaptatif'

    DOSSIER = '/usr/local/share/neuromancer'
    DUREE_PWN = 8          # secondes d'affichage apres un handshake
    DUREE_PHRASE = 6       # duree minimale d'affichage d'une replique
    LARGEUR_PHRASE = 20    # caracteres par ligne avant retour a la ligne
    FILE_MAX = 3           # repliques en attente au maximum
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
        self.haut = HAUT_DEFAUT
        self.col_d = COL_D_DEFAUT
        self.phrase = None      # replique actuellement affichee
        self.phrase_jusqua = 0  # instant avant lequel on ne la remplace pas
        self.vue = None         # dernier statut lu chez le coeur
        self._verrou = threading.Lock()  # on_loaded et on_ui_setup sont concurrents
        self.file = deque(maxlen=self.FILE_MAX)  # repliques en attente

    # ---------------------------------------------------------------- chargement

    def _charger_images(self):
        """Charge les PNG en memoire. Idempotente : ne fait rien si c'est deja fait.

        pwnagotchi lance on_loaded dans un thread separe pendant que le thread
        principal construit l'interface : on_ui_setup peut donc s'executer avant
        que les images soient la. Les deux appellent cette methode.
        """
        # les deux hooks tournent dans des threads distincts et peuvent entrer
        # ici en meme temps : sans verrou, les images sont chargees deux fois
        with self._verrou:
            if self.images:
                return
            self._charger_vraiment()

    def _charger_vraiment(self):
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

        _trace('%d images chargees (%s)'
               % (len(self.images), ', '.join(sorted(self.images))))

    def on_loaded(self):
        self._charger_images()

    # ---------------------------------------------------------------- interface

    def _calculer_layout(self, ui):
        """Deduit les coordonnees du layout de l'ecran, et adapte les images.

        Cherche les deux filets horizontaux pour connaitre la bande utile, puis
        redimensionne le portrait s'il n'y tient pas. Retombe sur les valeurs
        de la 2.13 v2 si le layout n'est pas lisible.
        """
        self.haut = HAUT if HAUT is not None else HAUT_DEFAUT
        self.col_d = COL_D if COL_D is not None else COL_D_DEFAUT

        try:
            layout = ui._layout
            largeur = layout['width']
            y_haut = layout['line1'][1]
            y_bas = layout['line2'][1]
        except Exception as e:
            logging.warning('[neuromancer] layout illisible (%s), valeurs par defaut' % e)
            return

        dispo_h = y_bas - y_haut - 4
        if dispo_h < 20 or largeur < 60:
            logging.warning('[neuromancer] bande utile trop petite (%dx%d)' % (largeur, dispo_h))
            return

        if HAUT is None:
            self.haut = y_haut + 2

        # le portrait doit tenir dans la bande, et laisser la place au texte
        ref = self.images[self.DEFAUT]
        max_w = max(40, largeur // 2 - MARGE_X)
        echelle = min(dispo_h / ref.height, max_w / ref.width, 1.0)

        if echelle < 0.999:
            cible = (max(1, int(ref.width * echelle)), max(1, int(ref.height * echelle)))
            # NEAREST : on preserve le pixel art, pas d'anti-aliasing
            self.images = {nom: img.resize(cible, Image.NEAREST)
                           for nom, img in self.images.items()}
            logging.info('[neuromancer] images redimensionnees en %dx%d' % cible)

        if COL_D is None:
            self.col_d = MARGE_X + self.images[self.DEFAUT].width + GOUTTIERE

        _trace('layout : ecran %dx%d, portrait en (%d,%d), texte en x=%d'
               % (largeur, layout['height'], MARGE_X, self.haut, self.col_d))

    def on_ui_setup(self, ui):
        _trace('on_ui_setup appele')

        # on_loaded a pu ne pas encore tourner : on charge nous-memes
        self._charger_images()
        if not self.images:
            _trace('on_ui_setup : chargement impossible, abandon')
            return

        self._calculer_layout(ui)

        # 'face' reste en place : le coeur ecrit dedans et on le lit dans
        # on_ui_update. On l'expulse simplement hors du cadre (h = 122).
        self._deplacer(ui, 'face', (0, 300))

        # le layout officiel met 'name' en (5,20) et 'status' en (125,20),
        # or notre portrait occupe x 6-82 : on rapatrie tout en colonne droite
        self._deplacer(ui, 'name', (self.col_d, self.haut))
        # 'status' change bien trop vite pour etre lu : on le sort du cadre et
        # on recopie son contenu nous-memes, a intervalle maitrise (voir
        # on_ui_update). Le coeur continue d'y ecrire librement.
        self._deplacer(ui, 'status', (0, 300))

        for element in ('friend_face', 'friend_name'):
            try:
                ui.remove_element(element)
            except Exception:
                pass

        self.bitmap = Bitmap(os.path.join(self.DOSSIER, self.DEFAUT + '.png'),
                             xy=(MARGE_X, self.haut))
        # le Bitmap a rouvert le fichier : on lui repasse notre copie, qui a pu
        # etre redimensionnee pour l'ecran
        self.bitmap.image = self.images[self.DEFAUT]
        ui.add_element('nm_face', self.bitmap)
        _trace('element nm_face ajoute')

        ui.add_element('nm_phrase', Text(
            value='', position=(self.col_d, self.haut + 18),
            color=0, font=fonts.Medium,
            wrap=True, max_length=self.LARGEUR_PHRASE))

        ui.add_element('nm_statut', LabeledValue(
            color=0, label='', value='', position=(self.col_d, self.haut + 46),
            label_font=fonts.Bold, text_font=fonts.Medium))
        ui.add_element('nm_cible', LabeledValue(
            color=0, label='', value='', position=(self.col_d, self.haut + 62),
            label_font=fonts.Bold, text_font=fonts.Medium))

    @staticmethod
    def _deplacer(ui, nom, xy):
        try:
            ui._state._state[nom].xy = xy
        except Exception as e:
            logging.warning('[neuromancer] deplacement de %s impossible : %s' % (nom, e))

    def on_unload(self, ui):
        with ui._lock:
            for element in ('nm_face', 'nm_phrase', 'nm_statut', 'nm_cible'):
                try:
                    ui.remove_element(element)
                except Exception:
                    pass

    # ---------------------------------------------------------------- evenements

    def _temporiser_phrase(self, ui):
        """Affiche les repliques du coeur l'une apres l'autre, chacune son temps.

        pwnagotchi remplace son statut a chaque evenement : certaines repliques
        vivent quarante secondes, d'autres une seule. Se contenter de lire le
        statut a intervalle regulier ne montrerait que les premieres.

        On surveille donc chaque changement et on l'empile, puis on defile a
        raison d'une replique par DUREE_PHRASE. La file est bornee : en cas de
        forte activite, les plus anciennes sont abandonnees plutot que de
        prendre du retard sur le present.

        Ecrire dans 'status' provoquerait une boucle de rafraichissement : on
        n'y touche jamais, on affiche dans notre propre element.
        """
        # 1. capturer ce que le coeur vient d'ecrire
        try:
            courant = ui.get('status')
        except Exception:
            courant = None

        if courant and courant != self.vue:
            self.vue = courant
            if courant != self.phrase and courant not in self.file:
                self.file.append(courant)

        # 2. defiler quand la replique en cours a fait son temps
        if time.time() < self.phrase_jusqua or not self.file:
            return

        self.phrase = self.file.popleft()
        self.phrase_jusqua = time.time() + self.DUREE_PHRASE
        ui.set('nm_phrase', self.phrase)

    def on_handshake(self, agent, filename, access_point, client_station):
        if 'ice' not in self.images:
            return
        self.ssid = (access_point or {}).get('hostname') or '???'
        self.jusqua = time.time() + self.DUREE_PWN
        logging.info('[neuromancer] ICE BROKEN sur %s' % self.ssid)

    def on_ui_update(self, ui):
        if self.bitmap is None or not self.images:
            return

        self._temporiser_phrase(ui)

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
        if self.affiche is None:
            _trace('premier rendu : image %s' % voulu)
        self.affiche = voulu

        self.bitmap.image = self.images[voulu]
        if voulu == 'ice':
            ui.set('nm_statut', 'ICE BROKEN')
            ui.set('nm_cible', self.ssid[:16])
        else:
            ui.set('nm_statut', '')
            ui.set('nm_cible', '')
