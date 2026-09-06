# Première installation sur le Pi

Marche à suivre pour le premier essai sur le matériel. Rien de tout ce dépôt
n'a encore tourné sur un vrai pwnagotchi : ce document sert autant à installer
qu'à vérifier.

---

## 1. Joindre le pwnagotchi

Branche le Pi en USB sur le PC. Il s'expose en général en `10.0.0.2` :

```bash
ping -c 3 10.0.0.2
ssh pi@10.0.0.2
```

> Mot de passe par défaut : `raspberry`. Si le ping échoue, vérifier que
> l'interface USB est bien montée côté PC (`ip -brief addr | grep usb`) et que
> le câble transmet les données — pas un câble de charge seule.

En Wi-Fi, remplacer l'adresse par celle du Pi sur le réseau.

## 2. Relever la configuration actuelle

**Avant** d'installer, noter ce qui existe — pour pouvoir revenir en arrière :

```bash
grep -E '^main\.(name|lang)|^ui\.display\.type' /etc/pwnagotchi/config.toml
```

Retenir la valeur de `ui.display.type` : c'est le modèle d'écran, et il
détermine le layout que le plugin va détecter.

## 3. Installer

### Sans câble de données : par la carte SD

Si aucun câble micro-USB avec fils de données n'est disponible, on peut
installer directement sur la carte, Pi éteint. C'est aussi plus prudent pour un
premier essai : si le système ne démarre pas, il suffit de remonter la carte
pour revenir en arrière — alors qu'un plantage au boot laisse sans accès SSH.

```bash
# carte dans le lecteur ; elle se monte en general toute seule
lsblk -o NAME,SIZE,FSTYPE,LABEL,MOUNTPOINT

sudo ./tools/install-sdcard.sh /run/media/$USER/rootfs

# demonter proprement avant de retirer la carte
udisksctl unmount -b /dev/sdX2
udisksctl unmount -b /dev/sdX1
```

Le script affiche la configuration trouvée avant d'agir : vérifier qu'il s'agit
bien du bon pwnagotchi.

### En SSH

```bash
git clone https://github.com/wackojice/pwnagotchi-neuromancer.git
cd pwnagotchi-neuromancer
sudo ./install.sh
```

Le script :
1. copie les 6 images dans `/usr/local/share/neuromancer/`
2. copie `neuromancer.py` dans `/etc/pwnagotchi/custom-plugins/`
3. installe la voix dans le dossier `locale/` du paquet pwnagotchi
4. active `main.plugins.neuromancer.enabled` et `main.lang = "neuromancer"`
   (en sauvegardant `config.toml` au préalable)
5. redémarre le service

## 4. Surveiller le démarrage

C'est l'étape qui compte. Dans une autre session SSH :

```bash
journalctl -u pwnagotchi -f | grep -i neuromancer
```

**Ce qu'on veut voir :**

```
[neuromancer] 6 images chargees : awake, happy, ice, look_l, look_r, sleep
[neuromancer] ecran 250x122, portrait en (6,16), texte en x=95
```

La seconde ligne confirme que le layout a été détecté. Si elle annonce une
géométrie différente de la tienne, c'est que le driver expose autre chose —
ce n'est pas forcément une erreur.

## 5. Diagnostic si ça cloche

| Message | Cause | Correctif |
|---|---|---|
| `awake.png est obligatoire, plugin inactif` | images absentes ou illisibles | vérifier `ls /usr/local/share/neuromancer/` |
| `layout illisible (...), valeurs par defaut` | le driver n'expose pas `line1`/`line2` | sans gravité, valeurs de la 2.13 utilisées |
| `deplacement de <nom> impossible` | structure interne différente | l'élément se superposera au portrait, à corriger dans `_deplacer` |
| `bande utile trop petite` | écran très petit | forcer `HAUT` et `COL_D` en haut du plugin |
| rien du tout dans le journal | plugin non chargé | vérifier la ligne `main.plugins.neuromancer.enabled = true` |

Si le portrait s'affiche mais que le texte le chevauche, ce sont `name` et
`status` qui n'ont pas été déplacés — voir la troisième ligne du tableau.

Si l'écran reste vide ou blanc : `sudo systemctl status pwnagotchi` et lire la
trace complète, `journalctl -u pwnagotchi -n 100 --no-pager`.

## 6. Ce qu'il faut regarder à l'œil

Une fois que ça tourne, les deux points sur lesquels on n'a aucune certitude :

- **Le portrait crépite-t-il ?** La zone casque est dense en traits de 1 px.
  Sur un e-ink, ça peut fourmiller. Si c'est le cas, alléger cette zone.
- **Les visages sont-ils distinguables** à un mètre, en vrai, dans la lumière
  ambiante ? `awake`, `happy` et `sleep` doivent se reconnaître d'un coup d'œil.

Prendre une photo de l'écran et la rapporter : c'est le seul retour qui compte.

## 7. Revenir en arrière

```bash
sudo sed -i 's/^main\.plugins\.neuromancer\.enabled.*/main.plugins.neuromancer.enabled = false/' /etc/pwnagotchi/config.toml
sudo sed -i 's/^main\.lang.*/main.lang = "en"/' /etc/pwnagotchi/config.toml
sudo systemctl restart pwnagotchi
```

Le pwnagotchi retrouve ses visages ASCII et ses phrases d'origine. Rien du
projet n'a été modifié : les fichiers ajoutés peuvent rester en place sans
effet.

Une sauvegarde horodatée de `config.toml` a été créée par l'installeur :

```bash
ls -la /etc/pwnagotchi/config.toml.bak.*
```
