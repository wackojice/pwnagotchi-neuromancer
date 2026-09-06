# First install on the pi

Step-by-step for the first run on real hardware — as much a checklist for
verifying as for installing.

**This assumes a working pwnagotchi.** The theme installs on top of an existing
setup; if you have not flashed one yet, see [pwnagotchi.ai](https://pwnagotchi.ai/)
or [jayofelony/pwnagotchi](https://github.com/jayofelony/pwnagotchi) first.

---

## 1. Reaching the pwnagotchi

Plug the pi into your computer over USB. It usually appears at `10.0.0.2`:

```bash
ping -c 3 10.0.0.2
ssh pi@10.0.0.2
```

> Default password: `raspberry`. If the ping fails, check that the USB network
> interface came up on your side (`ip -brief addr | grep usb`) and that the
> cable actually carries data — not a charge-only one.

Over Wi-Fi, use the pi's address on your network instead.

## 2. Record the current configuration

**Before** installing, note what is already there, so you can go back:

```bash
grep -E '^main\.(name|lang)|^ui\.display\.type' /etc/pwnagotchi/config.toml
```

Keep the `ui.display.type` value: that is your screen model, and it decides
which layout the plugin will detect.

## 3. Install

### No data cable? Use the SD card

With the pi powered off, its card mounted on your computer:

```bash
lsblk -o NAME,SIZE,FSTYPE,LABEL,MOUNTPOINT

sudo ./tools/install-sdcard.sh /run/media/$USER/rootfs

udisksctl unmount -b /dev/sdX2
udisksctl unmount -b /dev/sdX1
```

The script prints the configuration it found before doing anything: check it is
the right pwnagotchi.

This route is also safer for a first attempt — a system that fails to boot is
fixed by remounting the card, whereas a boot failure over SSH leaves you locked
out.

### Over SSH

```bash
git clone https://github.com/wackojice/pwnagotchi-neuromancer.git
cd pwnagotchi-neuromancer
sudo ./install.sh
```

The script:
1. copies the six images to `/usr/local/share/neuromancer/`
2. copies `neuromancer.py` into whichever directory `main.custom_plugins` names
3. installs the voice next to pwnagotchi's other locales
4. enables `main.plugins.neuromancer.enabled` and `main.lang = "neuromancer"`
   (backing up `config.toml` first)
5. restarts the service

## 4. Watch it start

This is the step that matters. In another SSH session:

```bash
journalctl -u pwnagotchi -f | grep -i neuromancer
```

**What you want to see:**

```
[neuromancer] on_ui_setup appele
[neuromancer] 6 images chargees : awake, happy, ice, look_l, look_r, sleep
[neuromancer] layout : ecran 250x122, portrait en (6,16), texte en x=95
[neuromancer] element nm_face ajoute
[neuromancer] premier rendu : image awake
```

The same lines are written to **`neuromancer-trace.txt` on the boot partition**,
flushed immediately. Pull the card and read it from any computer — it survives
an unclean shutdown, unlike the journal, which stays in cache.

## 5. Troubleshooting

| Message | Cause | Fix |
|---|---|---|
| `awake.png est obligatoire, plugin inactif` | images missing or unreadable | check `ls /usr/local/share/neuromancer/` |
| `layout illisible (...)` | driver exposes no `line1`/`line2` | harmless, 2.13" defaults are used |
| `deplacement de <name> impossible` | internal structure differs | that element will overlap the portrait; adjust `_deplacer` |
| `bande utile trop petite` | very small screen | force `HAUT` and `COL_D` in the plugin |
| nothing at all in the journal | plugin not loaded | check `main.plugins.neuromancer.enabled = true`, and that the plugin sits in the directory `main.custom_plugins` names |
| trace stops after `on_ui_setup` | images failed to load | check the image path and permissions |

If the screen stays blank: `sudo systemctl status pwnagotchi`, then
`journalctl -u pwnagotchi -n 100 --no-pager`.

## 6. The pi restarts on its own

Not a theme problem. pwnagotchi restarts itself when it sees no access point
for several epochs:

```
[CRITICAL] 5 epochs without visible access points -> restarting ...
```

It is a safeguard against a known Raspberry Pi Wi-Fi driver bug where the
monitor interface silently stops capturing. In a quiet area with few networks
it fires needlessly. Raise the threshold:

```toml
main.mon_max_blind_epochs = 15
```

`main.no_restart = true` disables it entirely — not recommended: if the driver
really wedges, the pi stays blind forever.

## 7. Rolling back

```bash
sudo sed -i 's/^main\.plugins\.neuromancer\.enabled.*/main.plugins.neuromancer.enabled = false/' /etc/pwnagotchi/config.toml
sudo sed -i 's/^main\.lang.*/main.lang = "en"/' /etc/pwnagotchi/config.toml
sudo systemctl restart pwnagotchi
```

The pwnagotchi returns to its ASCII faces and original lines. Nothing in the
project was modified, so the added files can stay where they are.

The installer left a timestamped backup:

```bash
ls -la /etc/pwnagotchi/config.toml.bak.*
```
