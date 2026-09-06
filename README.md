# pwnagotchi-neuromancer

Un thème pour [pwnagotchi](https://pwnagotchi.ai/) : la tête ASCII est remplacée
par un portrait cyberpunk en pixel art, et un écran **ICE BROKEN** s'affiche à
chaque handshake capturé.

![aperçu de l'écran](docs/apercu_ecran.png)

*Rendu attendu sur Waveshare 2.13" — agrandi ×4.*

## Ce que ça fait

- remplace les 19 visages ASCII par 5 portraits en pixel art 1 bit
- affiche un écran dédié pendant quelques secondes après chaque handshake,
  avec le SSID de la cible
- réorganise la mise en page pour libérer la place du portrait

Le plugin **ne modifie pas** pwnagotchi : il s'installe comme plugin
personnalisé et se désactive en une ligne de config.

## Installation

Sur le pwnagotchi (pas depuis le PC) :

```bash
git clone https://github.com/wackojice/pwnagotchi-neuromancer.git
cd pwnagotchi-neuromancer
sudo ./install.sh
```

Le script copie les images, installe le plugin, active la ligne
`main.plugins.neuromancer.enabled = true` dans `/etc/pwnagotchi/config.toml`
(en sauvegardant l'ancien) et redémarre le service.

### Installation manuelle

```bash
sudo mkdir -p /usr/local/share/neuromancer
sudo cp images/*.png /usr/local/share/neuromancer/
sudo cp neuromancer.py /usr/local/share/pwnagotchi/custom-plugins/
```

Puis dans `/etc/pwnagotchi/config.toml` :

```toml
main.plugins.neuromancer.enabled = true
```

```bash
sudo systemctl restart pwnagotchi
```

### Vérifier que ça tourne

```bash
journalctl -u pwnagotchi -f | grep neuromancer
```

Au démarrage, le plugin annonce le nombre d'images chargées.

## Compatibilité

Développé et calé sur **Waveshare 2.13" v2** (250 × 122), testé avec le fork
[jayofelony/pwnagotchi](https://github.com/jayofelony/pwnagotchi) branche `noai`.

Les autres variantes 2.13" (`V3`, `V4`, `b_V4`) partagent la même résolution
250 × 122 et devraient fonctionner sans modification.

Pour un écran de taille différente, ajuster `HAUT` et `COL_D` en haut du plugin
d'après le `layout()` du driver correspondant dans
`pwnagotchi/ui/hw/`. Sur la variante tricolore (212 × 104), il faut aussi
réduire les images à environ 68 px de haut.

## Les visages

| Fichier | État | Correspondance |
|---|---|---|
| `awake.png` | neutre, visière allumée | `AWAKE`, `COOL`, `INTENSE`, `SMART`, `MOTIVATED` |
| `happy.png` | coin de la bouche relevé | `HAPPY`, `GRATEFUL`, `EXCITED`, `FRIEND` |
| `look_l.png` / `look_r.png` | regard de côté | `LOOK_L`, `LOOK_R` et leurs variantes *happy* |
| `sleep.png` | visière éteinte + zZz | `SLEEP`, `SLEEP2`, `BORED`, `LONELY`, `SAD`, `DEMOTIVATED` |
| `ice.png` | glace brisée | affiché après un handshake |

Toutes les images font 76-77 × 80, en **1 bit pur**, sans anti-aliasing.

Le `MAPPING` en haut du plugin se réorganise librement : plusieurs états peuvent
pointer vers la même image, et `awake.png` sert de repli pour tout état non prévu.

## Réglages

En haut de `neuromancer.py` :

| Constante | Rôle |
|---|---|
| `DOSSIER` | emplacement des PNG |
| `DUREE_PWN` | secondes d'affichage de l'écran ICE BROKEN |
| `DEFAUT` | image de repli |
| `HAUT` | ordonnée du haut du portrait |
| `COL_D` | abscisse de la colonne de texte de droite |

## Comment ça marche

Le plugin ne devine pas l'humeur : il **lit** ce que le cœur de pwnagotchi vient
d'écrire dans l'élément `face`, puis le traduit en fichier via `MAPPING`.

L'élément `face` n'est pas supprimé — le cœur continue d'y écrire — il est
déplacé hors du cadre visible. Les éléments `name` et `status` sont rapatriés en
colonne de droite pour libérer la place du portrait.

Un rafraîchissement e-ink coûte environ deux secondes : le plugin ne repeint que
lorsque l'image change réellement, jamais à chaque appel de `on_ui_update`.

## Dessiner ses propres visages

Deux principes, appris à la dure :

- **Des aplats pleins, pas du trait fin.** Un contour de 1 px disparaît ou
  crépite sur un e-ink ; une masse noire survit toujours.
- **Pas de primitives vectorielles.** Une bouche tracée à l'arc ou un texte posé
  avec une police jurent avec un dessin pixelisé. Dessiner à la main, à l'échelle
  finale.

## Licence

GPL-3.0 — comme pwnagotchi, dont ce plugin utilise les interfaces.

Le nom et l'esthétique font référence au roman *Neuromancer* de William Gibson.
Projet non officiel, sans affiliation.
