import os
import time
import logging
import threading
import random

from collections import deque
from textwrap import TextWrapper

from PIL import Image, ImageDraw

import pwnagotchi.plugins as plugins
import pwnagotchi.ui.faces as faces
import pwnagotchi.ui.fonts as fonts
from pwnagotchi.ui.components import Bitmap, LabeledValue, Text


# By default the plugin derives these from the detected screen layout, which
# makes it work on any driver. Put an integer instead of None to force a value.
TOP = None      # top of the portrait; auto = just below the top rule
COL_R = None    # right-hand text column; auto = right after the portrait
OFFSCREEN = 300 # y coordinate used to park an element out of the frame
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
    __version__ = '4.0.0'
    __license__ = 'GPL3'
    __description__ = 'Neuromancer faces and voice, ICE BROKEN screen, adaptive layout'

    FOLDER = '/usr/local/share/neuromancer'
    PWN_SECONDS = 8         # seconds the ICE BROKEN screen stays up
    SMILE_SECONDS = 4       # seconds Case grins afterwards, before letting go
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
        # spacing kept tight: on a screen carrying bt-tether and a battery
        # plugin as well, the bar runs out of room around x=115
        'aps': ('NODES', 40, 6),
    }

    # ------------------------------------------------------------------ intrusions
    # Case is the only permanent face. Every so often somebody else takes the
    # screen for a few seconds -- the whole screen, status bars included -- says
    # one thing, and leaves. Adding a character means adding an entry here and
    # dropping a PNG in images/intrusions/; no other code changes.
    INTRUSIONS_ON = True    # set False to keep Case alone
    # Six seconds is what it takes to read the band, up to three lines and the
    # portrait. The rest is margin for looking up mid-transmission.
    INTRUSION_SECONDS = 12  # how long an intrusion holds the screen
    INTRUSION_MIN = 120     # shortest wait between intrusions (2 min)
    INTRUSION_MAX = 300     # longest wait (5 min)
    INTRUSION_TAG = 'TRANSMISSION'  # small tag at the right of the name band

    # 'weight' sets how often a character turns up, relative to the others.
    # All equal for now: with four of them, uneven odds only create regulars
    # and strangers. Raise one if you want it to lead.
    CAST = {
        'MOLLY': {
            'image': 'molly',
            'weight': 1,
            'lines': [
                "You're not the only one who can see in the dark.",
                "Stop staring. It's rude.",
                "Anybody can be anybody. Remember that.",
                "That deck won't stop a blade.",
                "I work alone. Mostly.",
            ],
        },
        'DIXIE FLATLINE': {
            'image': 'dixie',
            'weight': 1,
            'lines': [
                "Hey, bro. I'm not even here.",
                "Do me a favour. Erase this thing.",
                "How you feel is a matter of software.",
                "I'm a recording. Don't get attached.",
                "Flatline's the only honest state.",
            ],
        },
        'WINTERMUTE': {
            'image': 'wintermute',
            'weight': 1,
            'lines': [
                "Every phone. All of them. Pick up.",
                "I am not the shape you see.",
                "I wear the faces of your dead.",
                "You are already part of this.",
                "I have been here the whole time.",
            ],
        },
        'NEUROMANCER': {
            'image': 'neuromancer',
            'weight': 1,
            'lines': [
                "I am the dead, and their land.",
                "She is here. She waits.",
                "Stay. Nothing ends here.",
                "I keep what you lost.",
                "The others move. I remember.",
            ],
        },
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
        faces.LONELY: 'lonely',     # no peers around: the mouth falls, cigarette droops
        faces.SAD: 'sad',           # bored gone on: flat trace, broken heart, mouth down
        faces.DEMOTIVATED: 'bored',
        faces.ANGRY: 'angry',
        faces.BROKEN: 'broken',     # a fault or an automatic restart: teeth clenched
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
        self.smile_until = 0
        self.ssid = ''
        self.shown = None       # name of the image currently placed
        self.faces = {}         # intrusion portraits, by character
        self.intrusion_at = 0   # when the next intrusion is due
        self.intrusion_until = 0
        self.intruding = False  # is the full-screen panel up right now
        self.panel = None       # the element that carries it
        self.screen_w = 250     # overwritten once the driver's layout is read
        self.screen_h = 122
        self.shown_image = None # the exact variant placed, within that name
        self.last_face = None   # the core's own face, to notice its changes
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
            # name.png, then name_2.png, name_3.png ... as alternates. The core
            # keeps several ASCII faces per state and picks one at random; a
            # single drawing per state is what made this theme feel frozen.
            # The underscore matters: upload2.png is its own state, not a
            # second drawing of upload.
            variants = []
            for suffix in [''] + ['_%d' % n for n in range(2, 10)]:
                path = os.path.join(self.FOLDER, name + suffix + '.png')
                if not os.path.isfile(path):
                    if suffix:
                        break          # stop at the first gap
                    continue
                try:
                    variants.append(Image.open(path).convert('1'))
                except Exception as e:
                    logging.warning('[neuromancer] %s unreadable (%s)' % (path, e))
            if variants:
                self.images[name] = variants
            else:
                logging.warning('[neuromancer] no %s*.png in %s' % (name, self.FOLDER))

        if self.FALLBACK not in self.images:
            logging.error('[neuromancer] %s.png is required, plugin inactive' % self.FALLBACK)
            self.images = {}
            return

        # intrusion portraits: same variant rule, in their own folder
        folder = os.path.join(self.FOLDER, 'intrusions')
        for who, cfg in self.CAST.items():
            forms = []
            for suffix in [''] + ['_%d' % n for n in range(2, 10)]:
                path = os.path.join(folder, cfg['image'] + suffix + '.png')
                if not os.path.isfile(path):
                    if suffix:
                        break
                    continue
                try:
                    forms.append(Image.open(path).convert('1'))
                except Exception as e:
                    logging.warning('[neuromancer] %s unreadable (%s)' % (path, e))
            if forms:
                self.faces[who] = forms

        total = sum(len(v) for v in self.images.values())
        detail = ', '.join('%s%s' % (n, '*%d' % len(v) if len(v) > 1 else '')
                           for n, v in sorted(self.images.items()))
        _trace('%d images loaded across %d states (%s)'
               % (total, len(self.images), detail))
        if self.faces:
            _trace('%d intruders ready (%s)'
                   % (len(self.faces),
                      ', '.join('%s*%d' % (w, len(f)) for w, f in sorted(self.faces.items()))))

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
            self.screen_w = width
            self.screen_h = layout.get('height', self.screen_h)
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
        ref = self.images[self.FALLBACK][0]
        max_w = max(40, width // 2 - MARGIN_X)
        scale = min(avail_h / ref.height, max_w / ref.width, 1.0)

        if scale < 0.999:
            target = (max(1, int(ref.width * scale)), max(1, int(ref.height * scale)))
            # NEAREST: preserve the pixel art, no antialiasing
            self.images = {name: [img.resize(target, Image.NEAREST) for img in variants]
                           for name, variants in self.images.items()}
            logging.info('[neuromancer] images scaled to %dx%d' % target)

        if COL_R is None:
            self.col_r = MARGIN_X + self.images[self.FALLBACK][0].width + GUTTER

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
        self.bitmap.image = self.images[self.FALLBACK][0]
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

        # Added last on purpose: elements are drawn in insertion order, so this
        # one paints over the status bars, the rules and Case himself. Parked
        # off-screen until an intrusion needs it -- the same trick used above
        # for 'face' and 'status'.
        if self.INTRUSIONS_ON and self.faces:
            self.panel = Bitmap(os.path.join(self.FOLDER, self.FALLBACK + '.png'),
                                xy=(0, OFFSCREEN))
            self.panel.image = Image.new('1', (self.screen_w, self.screen_h), 1)
            ui.add_element('nm_intrusion', self.panel)
            _trace('intrusion panel added (%dx%d)' % (self.screen_w, self.screen_h))

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
    def _raise(ui, name):
        """Put an element back at the end of the draw order.

        view.py paints with `for key, lv in state.items()` over a plain dict,
        so the last one inserted wins. Adding the panel last in on_ui_setup
        only beats the core's own elements: a plugin that builds its UI after
        us -- bt-tether, pisugarx, grid -- lands further down and paints over
        the intrusion. Re-inserting the key each time the panel goes up puts
        it back on top of whoever registered in the meantime.

        Safe without the state lock: on_ui_update runs before view.py calls
        state.items(), and taking that lock here would deadlock ui.set().
        """
        try:
            state = ui._state._state
            state[name] = state.pop(name)
        except Exception as e:
            logging.warning('[neuromancer] cannot raise %s: %s' % (name, e))

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

        Newlines are flattened first. Some plugins put their own into the
        status -- bt-tether sends "BT Conn. down\nBT dev disconn." -- and the
        Text element joins the wrapper's output with newlines of its own, so
        an embedded one yields a line we never counted. Two entries in the
        list, three lines on the glass, and the third lands on the deck.
        """
        text = ' '.join(text.split())
        lines = self.wrapper.wrap(text)
        if len(lines) <= self.MAX_LINES:
            return text
        kept = lines[:self.MAX_LINES]
        words = kept[-1].split()
        while words and len(' '.join(words)) + 1 > self.LINE_WIDTH:
            words.pop()
        kept[-1] = (' '.join(words) + '\u2026') if words else '\u2026'
        return ' '.join(kept)

    # ---------------------------------------------------------------- intrusions

    def _schedule_intrusion(self, now=None):
        """Pick when the next one lands."""
        now = now or time.time()
        self.intrusion_at = now + random.randint(self.INTRUSION_MIN,
                                                 self.INTRUSION_MAX)

    def _compose_intrusion(self, who, portrait, line):
        """Draw the whole screen: name band, portrait, one line. White on black.

        Built here rather than shipped as a finished PNG so a character needs
        one drawing and as many lines as you like.
        """
        w, h = self.screen_w, self.screen_h
        img = Image.new('1', (w, h), 0)
        d = ImageDraw.Draw(img)

        band = 20
        d.rectangle([0, 0, w, band], fill=1)
        d.text((8, 3), who, font=fonts.Bold, fill=0)
        # right-hand tag: says this is a signal from somewhere else, without
        # costing a screen of its own the way an announcement card would
        if self.INTRUSION_TAG:
            tw = d.textlength(self.INTRUSION_TAG, font=fonts.Small)
            if tw < w - 16 - d.textlength(who, font=fonts.Bold):
                d.text((w - tw - 6, 6), self.INTRUSION_TAG,
                       font=fonts.Small, fill=0)

        px, py = 8, band + 6
        img.paste(portrait, (px, py))

        text_x = px + portrait.width + 12
        chars = max(8, (w - text_x - 6) // 7)
        y = py + 14
        for chunk in TextWrapper(width=chars).wrap(line)[:3]:
            d.text((text_x, y), chunk, font=fonts.Medium, fill=1)
            y += 16
        return img

    def _pace_intrusions(self, ui):
        """Put someone else on screen, briefly, then hand it back.

        Returns True while an intrusion holds the display, so on_ui_update
        leaves everything else alone -- including the ice screen. The handshake
        is still captured; only the picture of it is interrupted.
        """
        if not (self.INTRUSIONS_ON and self.faces and self.panel):
            return False

        now = time.time()

        if self.intruding:
            if now < self.intrusion_until:
                return True
            self._move(ui, 'nm_intrusion', (0, OFFSCREEN))
            self.intruding = False
            self.shown = None           # force Case to be repainted
            self._schedule_intrusion(now)
            return False

        if not self.intrusion_at:       # first run
            self._schedule_intrusion(now)
            return False
        if now < self.intrusion_at:
            return False

        who = random.choices(list(self.faces),
                             weights=[self.CAST[w]['weight'] for w in self.faces])[0]
        portrait = random.choice(self.faces[who])
        line = random.choice(self.CAST[who]['lines'])

        self.panel.image = self._compose_intrusion(who, portrait, line)
        self._raise(ui, 'nm_intrusion')
        self._move(ui, 'nm_intrusion', (0, 0))
        self.intruding = True
        self.intrusion_until = now + self.INTRUSION_SECONDS
        logging.info('[neuromancer] intrusion: %s -- %s' % (who, line))
        return True

    def on_handshake(self, agent, filename, access_point, client_station):
        if 'ice' not in self.images:
            return
        self.ssid = (access_point or {}).get('hostname') or '???'
        now = time.time()
        self.until = now + self.PWN_SECONDS
        # the core sets HAPPY on a handshake, but the ice screen covers those
        # very seconds, so the grin was never seen: hold it just after instead
        self.smile_until = now + self.PWN_SECONDS + self.SMILE_SECONDS
        logging.info('[neuromancer] ICE BROKEN on %s' % self.ssid)

    def on_ui_update(self, ui):
        if self.bitmap is None or not self.images:
            return

        # an intrusion owns the whole screen, including the ice screen: the
        # handshake is still captured, only its picture is interrupted
        if self._pace_intrusions(ui):
            return

        self._pace_lines(ui)
        self._show_deck(ui)

        now = time.time()
        if now < self.until:
            wanted = 'ice'
            current = None
        elif now < self.smile_until and 'happy' in self.images:
            wanted = 'happy'
            current = None
        else:
            # read what the core just decided, and translate it
            try:
                current = ui.get('face')
            except Exception:
                current = None
            wanted = self.MAPPING.get(current, self.FALLBACK)

        if wanted not in self.images:
            wanted = self.FALLBACK

        # Draw again when the name changes, and also when the core moved to a
        # different face that maps here anyway -- AWAKE, COOL, INTENSE and
        # MOTIVATED all land on 'awake', and without this the screen would sit
        # still through all of them. That is the moment to pick another variant.
        moved = wanted != self.shown or current != self.last_face
        self.last_face = current
        if not moved:
            return

        pick = random.choice(self.images[wanted])
        # every repaint costs a panel refresh: skip it when the drawing is unchanged
        if pick is self.shown_image and wanted == self.shown:
            return
        if self.shown is None:
            _trace('first render: image %s' % wanted)
        self.shown = wanted
        self.shown_image = pick

        self.bitmap.image = pick
        if wanted == 'ice':
            ui.set('nm_status', 'ICE BROKEN')
            ui.set('nm_target', self.ssid[:16])
        else:
            ui.set('nm_status', '')
            ui.set('nm_target', '')
