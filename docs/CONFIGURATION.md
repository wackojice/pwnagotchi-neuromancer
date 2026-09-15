# Configuration

Everything you can change, and where.

# Settings

At the top of `neuromancer.py`:

| Constant | Purpose |
|---|---|
| `FOLDER` | where the PNGs live |
| `PWN_SECONDS` | seconds the ICE BROKEN screen stays up (default: 8) |
| `SMILE_SECONDS` | seconds `happy.png` is held right after it (default: 4) |
| `LABELS` | status-bar labels, as `name: (text, x, spacing)` |
| `LINE_SECONDS` | minimum seconds a line stays readable (default: 6) |
| `LINE_WIDTH` | characters per line before wrapping |
| `QUEUE_MAX` | lines held in the queue (default: 3) |
| `FALLBACK` | fallback image |
| `TOP` / `COL_R` | portrait and text column — `None` means auto |
| `MARGIN_X` / `GUTTER` | left margin and gap between portrait and text |
| `LABELS` | status-bar labels to rewrite, with position and spacing |
| `DECK_TEMPERATURE` | show the SoC temperature |
| `DECK_INTERVAL` | seconds between temperature readings |

# The status bar

The plugin also renames interface labels:

| pwnagotchi | Neuromancer |
|---|---|
| `APS 9 (19)` | `NODES 9 (19)` |

`PWND` stays: it is the counter the whole pwnagotchi community recognises, and
renaming it would cost more in clarity than it gains in style. `ICE BROKEN`
keeps its meaning on the capture screen, where context makes it obvious. `UP`
and `CH` stay too — the uptime element already sits at `x = 185` on a 250 px
screen, and a longer label would overflow.

This renaming incidentally fixes a pwnagotchi display flaw. A `LabeledValue`
places its value at `x + spacing + 5 × len(label)`, counting 5 px per character
while the font is 6 px wide: the longer the label, the further its value creeps
back over it — hence the `CH 11APS` collision in the stock layout. The plugin
repositions the elements and widens the spacing.

# Deck temperature

A `DECK 44°C` line shows the SoC temperature, read from
`/sys/class/thermal/thermal_zone0/temp` every `DECK_INTERVAL` seconds. Useful
on a Pi Zero, and fitting for the vocabulary — a cyberdeck running hot.

Turn it off with `DECK_TEMPERATURE = False`.

---

[Back to the README](../README.md)
