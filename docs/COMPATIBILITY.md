# Compatibility

**The layout adapts to the detected screen.** At startup the plugin reads the
active driver's `layout()`, finds the usable band between the two horizontal
rules, places the portrait there and derives the text column. If the portrait
does not fit, images are scaled with `NEAREST` — no antialiasing, so the pixel
art survives.

**Hardware-tested across three setups**, spanning the oldest release these
boards can run and the newest one there is:

| | Board | pwnagotchi | Base | Arch | Display |
|---|---|---|---|---|---|
| 1 | Pi Zero W | 2.9.5.3 | | armv6l (32-bit) | `waveshare_2` |
| 2 | 64-bit Pi | 2.9.5.4 | | aarch64 | `waveshare_4`, rotated 180° |
| 3 | 64-bit Pi | **2.9.5.8** | Debian 13, Python 3.13 | aarch64 | `waveshare_4`, rotated 180° |

All three run the same plugin unchanged: the layout is derived from whatever the
active driver reports, and the plugin is pure Python with no compiled parts, so
architecture makes no difference.

**The voice was audited against each one**, rather than against a single
reference — `msgid` strings differ between releases, and gettext matches byte
for byte, so one changed character drops a line back to English:

| Release | Translatable strings | Covered |
|---|---|---|
| 2.9.5.3 | 69 | **69** |
| 2.9.5.4 | 104 | **104** |
| 2.9.5.8 | 104 | **104** |

2.9.5.8 moves things about: the venv lives at `/opt/.pwn`, custom plugins are
read from `/etc/pwnagotchi/custom-plugins/`, handshakes land in
`/etc/pwnagotchi/handshakes`, and a device name may no longer contain an
underscore. The installers read these paths from the config rather than assuming
them, so nothing here needs adjusting by hand.

The geometries below are **simulation-tested** — verified against the real
driver layouts, but not confirmed on a physical device. Reports welcome.

| Screen | Portrait | Text column |
|---|---|---|
| Waveshare 2.13" (250 × 122) | 76 × 80 at y=16 | x=95 |
| Waveshare 1.54" (200 × 200) | 76 × 80 at y=16 | x=95 |
| Waveshare 2.7" (264 × 176) | 76 × 80 at y=16 | x=95 |
| Tri-color (212 × 104) | **scaled to 72 × 76**, y=14 | x=91 |

Developed on a **Waveshare 2.13" v2** with pwnagotchi 2.9.5.3, then confirmed on
a second device running **2.9.5.4 on 64-bit**, and on a clean install of
**2.9.5.8** — both with a `waveshare_4` panel mounted upside down.

> **Note for Pi Zero W (v1) owners:** the releases page confirms it — 2.9.5.6 is
> the last one carrying a `32bit` image at all; 2.9.5.7 and 2.9.5.8 ship 64-bit
> only. The maintainer has stated 32-bit is unsupported, and in practice the last
> workable release for these boards is **2.9.5.3**, which is what device 1 above
> runs. This theme works there, and its voice is audited against that release
> specifically.

To force coordinates, replace `None` with an integer at the top of the plugin:

```python
TOP = None    # auto: just below the top rule
COL_R = None   # auto: right after the portrait
```

---

[Back to the README](../README.md)
