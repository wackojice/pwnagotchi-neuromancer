# How it works

The plugin does not guess the mood: it **reads** what pwnagotchi's core just
wrote into the `face` element and translates it to a file through `MAPPING`.

The `face` element is not removed — the core keeps writing to it — it is simply
moved outside the visible frame. `name` is pulled into the right-hand column to
free up room for the portrait.

An e-ink refresh costs about two seconds, so the plugin only repaints when the
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
e-ink at two seconds per refresh the screen would flicker endlessly. The plugin
never touches it.

**Image loading is thread-safe.** pwnagotchi runs `on_loaded` in a separate
thread while the main thread builds the UI, so `on_ui_setup` can run *before*
the images exist. Both call the same idempotent loader, guarded by a lock.
This ordering was the bug that kept the portrait invisible on first install —
found only by tracing to the boot partition on real hardware.

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
