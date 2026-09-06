# État du projet

> Où on en est, et par quoi reprendre. Mis à jour le **2026-09-05**.

## En une phrase

Le thème est **complet et prêt à installer** — visages, voix et layout
adaptatif — mais **rien n'a encore tourné sur un vrai pwnagotchi**.

## Fait

- [x] Dépôt monté, structure et licence GPL-3.0
- [x] `install.sh` : installation en une commande, avec sauvegarde de la config
- [x] Outil de prévisualisation hors matériel (`tools/preview.py`)
- [x] Visage `happy` rendu discernable de `awake` (il n'en différait que par
      15 pixels sur 6080)
- [x] Voix Neuromancer : les 104 répliques réécrites, via gettext
- [x] Layout adaptatif : détecte l'écran, réduit les images si besoin

## À faire

- [ ] **Premier test sur le Pi** — voir `docs/INSTALLATION-PI.md`
- [ ] Passer le dépôt public (seulement après le test)
- [ ] États non mappés : `ANGRY`, `BROKEN`, `UPLOAD` affichent `awake`.
      La recette est connue : visière en aplat noir + motif blanc
- [ ] Corriger le chevauchement `CH 11APS 11` — défaut du layout upstream
      (`channel` en x=0, `aps` en x=28), que le plugin pourrait décaler
- [ ] Le vide dans la colonne droite, entre le statut et le filet du bas

## Vérifié dans le code source (pas supposé)

Le clone de référence est dans `~/Work/reference/pwnagotchi` (branche `noai`,
lecture seule, hors dépôt).

- `Bitmap.image` existe bien — `components.py` fait `self.image = Image.open(path)`
- `ui._state._state` est le dict des éléments — le déplacement fonctionne
- les 19 constantes de `faces.py` utilisées par le `MAPPING` existent toutes
- `ui._layout` vient de `impl.layout()` et expose `width`, `height`, `line1`, `line2`
- la voix passe par gettext standard : `Voice.__init__` charge
  `locale/<lang>/LC_MESSAGES/voice.mo`
- toutes les variantes 2.13" (`V2`, `V3`, `V4`, `b_V4`) font 250 × 122

## Incertitudes assumées

- **Le rendu e-ink** n'a jamais été vu. La zone casque du portrait est dense en
  traits de 1 px et pourrait crépiter — l'opérateur trouve les images très bien
  telles quelles, décision prise de ne pas y toucher avant d'avoir vu le réel.
- **La police** : le rendu de `tools/preview.py` utilise DejaVuSansMono, comme
  pwnagotchi. Fidèle, mais un e-ink n'est pas un écran.

## Décisions prises

- **Plugin plutôt que fork** de `jayofelony/pwnagotchi` : les 34 Mo du projet
  auraient traîné une resynchronisation à chaque mise à jour, et l'installation
  serait passée par une reconstruction d'image SD. Un plugin s'installe
  par-dessus n'importe quelle installation et se désactive en une ligne.
- **Locale gettext plutôt que surcharge de `Voice`** : même logique, aucun code
  du projet modifié.
- **Dépôt privé** jusqu'au premier test matériel réussi.

## Commandes utiles

```bash
cd ~/Work/pwnagotchi-neuromancer
./tools/preview.py && imv preview/     # voir le rendu
$EDITOR locale/neuromancer/LC_MESSAGES/voice.po
msgfmt -o locale/neuromancer/LC_MESSAGES/voice.mo locale/neuromancer/LC_MESSAGES/voice.po
```
