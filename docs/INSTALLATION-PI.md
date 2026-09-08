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

## 4. First boot: one restart is expected

Case will appear, stay frozen for twenty to thirty seconds, and the device will
restart itself. The run after that is the working one.

This is pwnagotchi reacting to a changed `config.toml`, not a failure. Combined
with a slow board, the two boots can take several minutes before anything moves
on screen — and an e-ink panel gives no hint that work is happening.

Judge it on the second run, not the first.

Some devices repeat this on every boot. One tested here turned out to have done
so for five months before the theme existed, which its own logs showed. If yours
does it too, check its history before blaming the install:

```bash
grep -c 'Re|Started' /etc/pwnagotchi/log/pwnagotchi.log
```

Note that a config mounting the log directory in RAM (`[fs.memory.mounts.log]`)
loses whatever was not synced before the last unclean shutdown, so recent
entries may simply be missing.

## 5. Watch it start

This is the step that matters. In another SSH session:

```bash
journalctl -u pwnagotchi -f | grep -i neuromancer
```

**What you want to see:**

```
[neuromancer] on_ui_setup called
[neuromancer] 6 images loaded (awake, happy, ice, look_l, look_r, sleep)
[neuromancer] layout: screen 250x122, portrait at (6,16), text at x=95
[neuromancer] nm_face element added
[neuromancer] first render: image awake
```

The `screen WxH` line confirms the layout was detected from your own driver, so
the numbers will differ on another display.

The same events are written to **`neuromancer-trace.txt` on the boot partition**
(timestamped, without the `[neuromancer]` prefix),
flushed immediately. Pull the card and read it from any computer — it survives
an unclean shutdown, unlike the journal, which stays in cache.

## 6. Troubleshooting

| Message | Cause | Fix |
|---|---|---|
| `awake.png is required, plugin inactive` | images missing or unreadable | check `ls /usr/local/share/neuromancer/` |
| `<name>.png missing` | one image absent; the rest still work | copy it from `images/` |
| `layout unreadable (...), using defaults` | driver exposes no `line1`/`line2` | harmless, the 2.13" defaults are used |
| `cannot move <name>` | internal UI structure differs | that element will overlap the portrait; adjust `_move` |
| `usable band too small (WxH)` | very small screen | force `TOP` and `COL_R` at the top of the plugin |
| `images scaled to WxH` | portrait did not fit | informational, the layout adapted itself |
| `on_ui_setup: cannot load images, giving up` | images unreadable at setup time | check the path and permissions of `/usr/local/share/neuromancer/` |
| nothing at all in the journal | plugin not loaded | check that the plugin is enabled, and that it sits in the directory `main.custom_plugins` names. If your config uses `[sections]`, a flat `main.plugins...` key will not take effect |
| trace stops after `on_ui_setup called` | images failed to load | same as above |

A healthy startup looks like this, in order:

```
on_ui_setup called
6 images loaded (awake, happy, ice, look_l, look_r, sleep)
layout: screen 250x122, portrait at (6,16), text at x=95
nm_face element added
first render: image awake
```

If the screen stays blank: `sudo systemctl status pwnagotchi`, then
`journalctl -u pwnagotchi -n 100 --no-pager`.

## 7. The pi restarts on its own, over and over

Different from the single restart in step 4: that one happens once, right after
installing. This is a loop, every minute or so, indefinitely.

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

## 8. Rolling back

```bash
sudo ./uninstall.sh
sudo systemctl restart pwnagotchi
```

Disables the plugin, removes the files it installed, and restores the language
you had before — the value is recorded at install time, so it is restored rather
than guessed. If you changed `main.lang` yourself afterwards, the script says so
and leaves it alone.

To disable without removing anything:

```bash
sudo sed -i 's/^main\.plugins\.neuromancer\.enabled.*/main.plugins.neuromancer.enabled = false/' /etc/pwnagotchi/config.toml
sudo systemctl restart pwnagotchi
```

The installer left a timestamped backup:

```bash
ls -la /etc/pwnagotchi/config.toml.bak.*
```
