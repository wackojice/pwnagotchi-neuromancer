# How it works

The plugin does not guess the mood: it **reads** what pwnagotchi's core just
wrote into the `face` element and translates it to a file through `MAPPING`.

The `face` element is not removed — the core keeps writing to it — it is simply
moved outside the visible frame. `name` is pulled into the right-hand column to
free up room for the portrait.

Every repaint costs a panel refresh, so the plugin only repaints when the
image actually changes, never on every `on_ui_update` call.

**Lines stay readable.** pwnagotchi replaces its status on every event, and
their lifetimes are wildly uneven: `Waiting for 40s` lasts forty seconds,
`I'm bored...` lasts one. Sampling the status at a fixed interval would only
ever show the slow ones. So the plugin moves `status` out of frame, watches
every change and queues it, then advances one line per `LINE_SECONDS` seconds.
The queue is capped at `QUEUE_MAX`: under heavy activity the oldest lines are
dropped rather than letting the display fall behind reality.

Writing back into `status` would be simpler but causes a refresh loop: each
write marks a change, which triggers a render, which calls the plugin again. On
e-ink the screen would flicker endlessly. The plugin never touches it.

**Image loading is thread-safe.** pwnagotchi runs `on_loaded` in a separate
thread while the main thread builds the UI, so `on_ui_setup` can run *before*
the images exist. Both call the same idempotent loader, guarded by a lock.
This ordering was the bug that kept the portrait invisible on first install —
found only by tracing to the boot partition on real hardware.

**A transmission takes the screen by short-circuiting the update.**
`_pace_intrusions()` runs first in `on_ui_update` and returns `True` for as
long as it holds the display, so nothing below it runs — not the line queue,
not the deck reading, not even the ICE BROKEN screen. The handshake is still
captured; only the picture of it is interrupted. When the time is up the panel
is parked off-screen at `(0, 300)`, `self.shown` is cleared so Case is
repainted rather than assumed to be still there, and the next intrusion is
scheduled.

**The panel is composed at runtime, not shipped as finished images.** A
character costs one drawing and as many lines as you like: `_compose_intrusion`
builds the name band, pastes the portrait and wraps the line to the width left
beside it. Shipping ready-made screens would mean one PNG per character *per
line*, and adding a reply would mean redrawing. Characters can have several
forms — `name_2.png`, `name_3.png` — picked at random like the face variants.

**An intrusion has to be drawn last.** `view.py` paints with
`for key, lv in state.items()` over a plain dict, so the element inserted last
is the one on top, and `Bitmap.draw` pastes without a mask, so a full-screen
bitmap is opaque. Adding the panel last in `on_ui_setup` is not enough: it only
beats the core's own elements. A plugin that builds its UI *after* us —
bt-tether, pisugarx, grid — lands further down the dict and paints straight
over the transmission. The fix re-inserts the key every time the panel goes up,
which also catches a plugin that rebuilds its element in between. Found on
hardware as a stray `BT -` across a character's name band.

# Preview without hardware

The repo ships a tool that recomposes the 250 × 122 screen exactly like the
`waveshare2in13_V2` layout — same coordinates, same fonts, same 1-bit mode:

```bash
./tools/preview.py                # every state, plus a contact sheet
./tools/preview.py ice --zoom 6   # one state, enlarged
```

PNGs land in `preview/` (git-ignored). Needs Pillow, and `DejaVuSansMono` for a
faithful render (`sudo pacman -S ttf-dejavu` on Arch, `fonts-dejavu` on Debian)
— otherwise it falls back to another monospace font and says so.

---

[Back to the README](../README.md)
