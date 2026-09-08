# Project status

Updated **2026-09-06**.

## In one line

Complete and validated on **two different machines**: a 32-bit Pi Zero W running
2.9.5.3 with a `waveshare_2` panel, and a 64-bit board running 2.9.5.4 with a
`waveshare_4` panel mounted upside down. Same plugin, unchanged, on both.

## Done

- [x] Repository, GPL-3.0 licence, English documentation
- [x] `install.sh` — one-command install, config backed up
- [x] `tools/install-sdcard.sh` — install from the SD card, no data cable needed
- [x] `tools/preview.py` — hardware-free preview
- [x] `happy` face made distinguishable from `awake` (they differed by 15 pixels
      out of 6080)
- [x] Neuromancer voice: all 104 lines rewritten, via gettext
- [x] Adaptive layout: detects the screen, scales the images if needed
- [x] Line pacing: queued and advanced one at a time, so short-lived lines are
      not lost
- [x] Status bar: `NODES`, deck temperature, and the stock label collision fixed
- [x] **First hardware test — successful**
- [x] **Second machine, different everything** — 64-bit, pwnagotchi 2.9.5.4,
      `waveshare_4` display at 180°. Faces animate, lines scroll, layout correct
- [x] Both config.toml layouts supported (flat keys and `[sections]`)
- [x] Config backed up on every path, previous language recorded
- [x] `uninstall.sh` — install → uninstall → reinstall cycle verified on the
      real SD card, including the language-restore path

## Open

- [ ] `install.sh` (the SSH route) has never run on hardware — no data cable
      available. It shares its logic with `install-sdcard.sh`, which is
      hardware-tested on two machines, but that is not proof
- [ ] Layout tests on simulated geometries — the only tests that stand in for
      hardware nobody owns
- [ ] Unmapped states: `ANGRY`, `BROKEN` and `UPLOAD` fall back to `awake`.
      The recipe is known: solid black visor with a white motif knocked out
- [ ] Random variants: pwnagotchi accepts several images per state and picks one
      at random — two or three `awake` variants would make Case less static
- [ ] Screens never dressed up: startup, session summary, manual mode

## Verified in the source, not assumed

Read-only reference clone in `~/Work/reference/pwnagotchi` (jayofelony, `noai`).

- `Bitmap.image` exists — `components.py` does `self.image = Image.open(path)`
- `ui._state._state` is the element dict — moving elements works
- all 19 `faces.py` constants used by `MAPPING` exist
- `ui._layout` comes from `impl.layout()` and exposes `width`, `height`,
  `line1`, `line2`
- the voice goes through standard gettext: `Voice.__init__` loads
  `locale/<lang>/LC_MESSAGES/voice.mo`
- every 2.13" variant (`V2`, `V3`, `V4`, `b_V4`) is 250 × 122
- `main.custom_plugins` is `/usr/local/share/pwnagotchi/custom-plugins/` on 2.x
  and `/etc/pwnagotchi/custom-plugins/` on recent forks — hence the detection

## Design decisions

- **Plugin, not a fork.** Forking the 34 MB project would have meant resyncing
  on every upstream update, and rebuilding an SD image to install. A plugin
  installs over any existing setup and switches off with one config line.
- **gettext locale, not a `Voice` subclass.** Same reasoning: no project code
  touched.
- **The queue, not sampling.** Reading the status at a fixed interval favoured
  long-lived lines and hid the short ones entirely.
- **`PWND` kept.** It is the counter the community recognises; renaming it cost
  more in clarity than it gained in style.

## The bug the second machine caught

Its `config.toml` used the `[section]` layout — which is what pwnagotchi writes
after its first run — while the installer only ever appended flat keys. The key
would have landed inside whatever section came last: valid TOML, no error, and
the plugin silently never enabled.

Two smaller ones surfaced the same way: a `grep` for flat-format keys that
aborted the script under `set -e` when it matched nothing, and the same class of
bug already fixed once earlier. The lesson is the same each time — anything that
reads a config must handle both layouts, and every `grep` that is allowed to
find nothing needs `|| true`.

## The bug that cost the most

`on_ui_setup` runs **before** `on_loaded`: pwnagotchi handles each plugin's
events in a dedicated thread, and the view is built before plugin loading is
announced. The plugin found `self.images` empty, gave up, and never added its
portrait — with no error anywhere in the logs.

Invisible to code review and to simulation alike. It took instrumenting the
plugin to write its steps to the boot partition with `fsync`, so the trace would
survive an unclean shutdown. `neuromancer-trace.txt` is still there, and remains
the project's best diagnostic tool.

## Not a theme problem

The pwnagotchi restarts itself with `5 epochs without visible access points`
when it sees no network for several minutes — a safeguard against a known
Raspberry Pi Wi-Fi driver bug. Raise `main.mon_max_blind_epochs` in quiet areas.
