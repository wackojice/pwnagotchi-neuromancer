import os
import time
import logging
import threading
from collections import deque
from textwrap import TextWrapper

from PIL import Image

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.faces as faces
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import Bitmap, LabeledValue, Text


# By default the plugin derives these from the detected screen layout, which
# makes it work on any driver. Put an integer instead of None to force a value.
TOP = None      # top of the portrait; auto = just below the top rule
COL_R = None    # right-hand text column; auto = right after the portrait
MARGIN_X = 6    # portrait offset from the left edge
GUTTER = 13     # gap between the portrait and the text column

# fallbacks when the layout cannot be read (tuned for waveshare2in13_V2)
TOP_DEFAULT = 16
COL_R_DEFAULT = 95


def _trace(message):
    """Write a trace line straight to the boot partition.

    The usual journal can sit in cache and vanish when the pi is unplugged
    without a clean shutdown. Here we write and force a flush, onto a FAT
    partition readable from any computer.
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
    __version__ = '3.7.3'
    __license__ = 'GPL3'
    __description__ = 'Neuromancer faces and voice, ICE BROKEN screen, adaptive layout'

    FOLDER = '/usr/local/share/neuromancer'
    PWN_SECONDS = 8         # seconds the ICE BROKEN screen stays up
    LINE_SECONDS = 6        # minimum seconds a line stays readable
    LINE_WIDTH = 20         # characters per line before wrapping
    QUEUE_MAX = 3           # lines held in the queue at most
    MAX_LINES = 2           # a third line would land on top of the deck reading

    # Status-bar labels rewritten into Gibson's vocabulary.
    # Each entry: element -> (label, x or None, spacing or None)
    # LabeledValue places its value at x + spacing + 5*len(label), counting
    # 5 px per character while the font is 6 px wide: a longer label needs both
    # a shift and wider spacing, otherwise its value creeps back over it. That
    # already happens in stock pwnagotchi, where 'CH 11' touches 'APS'.
    # 'shakes' deliberately keeps PWND: it is the counter the whole pwnagotchi
    # community recognises, and renaming it would hurt clarity.
    LABELS = {
        'aps': ('NODES', 40, 12),
    }

    DECK_TEMPERATURE = True # show the SoC temperature
    DECK_INTERVAL = 30      # seconds between temperature readings
    FALLBACK = 'awake'      # fallback image for any unmapped state

    # each pwnagotchi state -> file name (without .png)
    # several states may point at the same image, on purpose
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
        faces.BORED: 'bored',
        faces.LONELY: 'bored',
        faces.SAD: 'bored',
        faces.DEMOTIVATED: 'bored',
        faces.ANGRY: 'angry',
        faces.BROKEN: 'angry',
        faces.DEBUG: 'awake',   # on_custom(): any plugin message, not a fault
        # the core cycles through these three while uploading, which animates
        # the progress bar on its own
        faces.UPLOAD: 'upload',
        faces.UPLOAD1: 'upload1',
        faces.UPLOAD2: 'upload2',
    }

    def __init__(self):
        self.images = {}
        self.bitmap = None
        self.until = 0
        self.ssid = ''
        self.shown = None       # name of the image currently placed
        self.top = TOP_DEFAULT
        self.col_r = COL_R_DEFAULT
        self.line = None        # line currently on screen
        self.line_until = 0     # do not replace it before this instant
        self.last_seen = None   # last status read from the core
        self._mutex = threading.Lock()  # on_loaded and on_ui_setup race
        self.deck = ''          # last temperature read
        self.deck_until = 0     # instant of the next reading
        self.queue = deque(maxlen=self.QUEUE_MAX)  # lines waiting their turn
        # same settings as the Text element, so we count the lines it will draw
        self.wrapper = TextWrapper(width=self.LINE_WIDTH, replace_whitespace=False)

    # ---------------------------------------------------------------- chargement

    def _load_images(self):
        """Load the PNGs. Idempotent: does nothing if already done.

        pwnagotchi runs on_loaded in a separate thread while the main thread
        builds the UI, so on_ui_setup may run before the images exist. Both
        hooks call this.
        """
        # both hooks run in distinct threads and can enter here at the same
        # time: without a lock the images get loaded twice
        with self._mutex:
            if self.images:
                return
            self._load_now()

    def _load_now(self):
        names = set(self.MAPPING.values()) | {'ice', self.FALLBACK}
        for name in names:
            path = os.path.join(self.FOLDER, name + '.png')
            try:
                self.images[name] = Image.open(path).convert('1')
            except Exception as e:
                logging.warning('[neuromancer] %s missing (%s)' % (path, e))

        if self.FALLBACK not in self.images:
            logging.error('[neuromancer] %s.png is required, plugin inactive' % self.FALLBACK)
            self.images = {}
            return

        _trace('%d images loaded (%s)'
               % (len(self.images), ', '.join(sorted(self.images))))

    def on_loaded(self):
        self._load_images()

    # ---------------------------------------------------------------- interface

    def _compute_layout(self, ui):
        """Derive coordinates from the screen layout and fit the images.

        Finds the two horizontal rules to get the usable band, then scales the
        portrait down if it does not fit. Falls back to the 2.13" v2 values
        when the layout cannot be read.
        """
        self.top = TOP if TOP is not None else TOP_DEFAULT
        self.col_r = COL_R if COL_R is not None else COL_R_DEFAULT

        try:
            layout = ui._layout
            width = layout['width']
            y_top = layout['line1'][1]
            y_bottom = layout['line2'][1]
        except Exception as e:
            logging.warning('[neuromancer] layout unreadable (%s), using defaults' % e)
            return

        avail_h = y_bottom - y_top - 4
        if avail_h < 20 or width < 60:
            logging.warning('[neuromancer] usable band too small (%dx%d)' % (width, avail_h))
            return

        if TOP is None:
            self.top = y_top + 2

        # le portrait doit tenir dans la bande, et laisser la place au texte
        ref = self.images[self.FALLBACK]
        max_w = max(40, width // 2 - MARGIN_X)
        scale = min(avail_h / ref.height, max_w / ref.width, 1.0)

        if scale < 0.999:
            target = (max(1, int(ref.width * scale)), max(1, int(ref.height * scale)))
            # NEAREST: preserve the pixel art, no antialiasing
            self.images = {name: img.resize(target, Image.NEAREST)
                           for name, img in self.images.items()}
            logging.info('[neuromancer] images scaled to %dx%d' % target)

        if COL_R is None:
            self.col_r = MARGIN_X + self.images[self.FALLBACK].width + GUTTER

        _trace('layout: screen %dx%d, portrait at (%d,%d), text at x=%d'
               % (width, layout['height'], MARGIN_X, self.top, self.col_r))

    def on_ui_setup(self, ui):
        _trace('on_ui_setup called')

        # on_loaded may not have run yet: load them ourselves
        self._load_images()
        if not self.images:
            _trace('on_ui_setup: cannot load images, giving up')
            return

        self._compute_layout(ui)

        # 'face' stays in place: the core writes to it and we read it in
        # on_ui_update. We simply push it outside the frame (h = 122).
        self._move(ui, 'face', (0, 300))

        # the stock layout puts 'name' at (5,20) and 'status' at (125,20),
        # but our portrait occupies x 6-82: move them to the right column
        self._move(ui, 'name', (self.col_r, self.top))
        # 'status' changes far too fast to be read: push it out of frame and
        # copy its content ourselves at a controlled pace (see on_ui_update).
        # The core keeps writing to it freely.
        self._move(ui, 'status', (0, 300))

        self._rename_labels(ui)

        for element in ('friend_face', 'friend_name'):
            try:
                ui.remove_element(element)
            except Exception:
                pass

        self.bitmap = Bitmap(os.path.join(self.FOLDER, self.FALLBACK + '.png'),
                             xy=(MARGIN_X, self.top))
        # Bitmap reopened the file: hand it our copy, which may have been
        # scaled for this screen
        self.bitmap.image = self.images[self.FALLBACK]
        ui.add_element('nm_face', self.bitmap)
        _trace('nm_face element added')

        ui.add_element('nm_line', Text(
            value='', position=(self.col_r, self.top + 18),
            color=0, font=fonts.Medium,
            wrap=True, max_length=self.LINE_WIDTH))

        ui.add_element('nm_deck', Text(
            value='', position=(self.col_r, self.top + 46),
            color=0, font=fonts.Medium))

        ui.add_element('nm_status', LabeledValue(
            color=0, label='', value='', position=(self.col_r, self.top + 62),
            label_font=fonts.Bold, text_font=fonts.Medium))
        ui.add_element('nm_target', LabeledValue(
            color=0, label='', value='', position=(self.col_r, self.top + 78),
            label_font=fonts.Bold, text_font=fonts.Medium))

    def _rename_labels(self, ui):
        """Switch the status bar to Gibson's vocabulary.

        Only labels that fit are touched: 'UP' would become 'JACKED', but the
        element already sits at x=185 on a 250 px screen and would overflow.
        """
        for name, (label, x, spacing) in self.LABELS.items():
            try:
                element = ui._state._state[name]
                element.label = label
                if x is not None:
                    element.xy = (x, element.xy[1])
                if spacing is not None:
                    element.label_spacing = spacing
            except Exception as e:
                logging.warning('[neuromancer] label %s unchanged: %s' % (name, e))

    def _temperature(self):
        """SoC temperature in degrees, or empty string if unreadable."""
        try:
            with open('/sys/class/thermal/thermal_zone0/temp') as f:
                return '%d\u00b0C' % (int(f.read().strip()) / 1000)
        except Exception:
            return ''

    def _show_deck(self, ui):
        """Show the temperature, refreshed at a slow interval."""
        if not self.DECK_TEMPERATURE:
            return
        now = time.time()
        if now < self.deck_until:
            return
        self.deck_until = now + self.DECK_INTERVAL

        value = self._temperature()
        if value and value != self.deck:
            self.deck = value
            ui.set('nm_deck', 'DECK %s' % value)

    @staticmethod
    def _move(ui, name, xy):
        try:
            ui._state._state[name].xy = xy
        except Exception as e:
            logging.warning('[neuromancer] cannot move %s: %s' % (name, e))

    def on_unload(self, ui):
        with ui._lock:
            for element in ('nm_face', 'nm_line', 'nm_deck', 'nm_status', 'nm_target'):
                try:
                    ui.remove_element(element)
                except Exception:
                    pass

    # ---------------------------------------------------------------- evenements

    def _pace_lines(self, ui):
        """Show the core's lines one after another, each for its own time.

        pwnagotchi replaces its status on every event: some lines live forty
        seconds, others a single one. Merely sampling the status at a fixed
        interval would only ever show the slow ones.

        So we watch every change and queue it, then advance one line per
        LINE_SECONDS. The queue is bounded: under heavy activity the oldest
        lines are dropped rather than letting the display fall behind reality.

        Writing back into 'status' would cause a refresh loop: we never touch
        it, we render into our own element.
        """
        # 1. capture what the core just wrote
        try:
            current = ui.get('status')
        except Exception:
            current = None

        if current and current != self.last_seen:
            self.last_seen = current
            if current != self.line and current not in self.queue:
                self.queue.append(current)

        # 2. advance once the current line has had its time
        if time.time() < self.line_until or not self.queue:
            return

        self.line = self._fit(self.queue.popleft())
        self.line_until = time.time() + self.LINE_SECONDS
        ui.set('nm_line', self.line)

    def _fit(self, text):
        """Trim a line to MAX_LINES.

        The deck reading sits at a fixed height, right where a third line
        would be drawn: long statuses used to overprint it. Cut on a word
        boundary so a MAC address is never sliced in half.
        """
        lines = self.wrapper.wrap(text)
        if len(lines) <= self.MAX_LINES:
            return text
        kept = lines[:self.MAX_LINES]
        words = kept[-1].split()
        while words and len(' '.join(words)) + 1 > self.LINE_WIDTH:
            words.pop()
        kept[-1] = (' '.join(words) + '\u2026') if words else '\u2026'
        return ' '.join(kept)

    def on_handshake(self, agent, filename, access_point, client_station):
        if 'ice' not in self.images:
            return
        self.ssid = (access_point or {}).get('hostname') or '???'
        self.until = time.time() + self.PWN_SECONDS
        logging.info('[neuromancer] ICE BROKEN on %s' % self.ssid)

    def on_ui_update(self, ui):
        if self.bitmap is None or not self.images:
            return

        self._pace_lines(ui)
        self._show_deck(ui)

        if time.time() < self.until:
            wanted = 'ice'
        else:
            # read what the core just decided, and translate it
            try:
                current = ui.get('face')
            except Exception:
                current = None
            wanted = self.MAPPING.get(current, self.FALLBACK)

        if wanted not in self.images:
            wanted = self.FALLBACK

        # an e-ink refresh costs ~2 s: only repaint on a real change
        if wanted == self.shown:
            return
        if self.shown is None:
            _trace('first render: image %s' % wanted)
        self.shown = wanted

        self.bitmap.image = self.images[wanted]
        if wanted == 'ice':
            ui.set('nm_status', 'ICE BROKEN')
            ui.set('nm_target', self.ssid[:16])
        else:
            ui.set('nm_status', '')
            ui.set('nm_target', '')
