# Nettoyage géométrique des masques alpha de carte

Cette procédure est une correction **post-build** pour une zone dont le masque
alpha reste en escalier en jeu malgré la restauration alpha et le lissage
bilinéaire normal. Elle a été validée visuellement sur `AR0604` (fontaine et
eau `WTSWAM`) ; elle ne devient pas pour autant une étape automatique de toute
zone. Partir d'une capture en jeu et ne changer qu'un paramètre par essai.

Si le flou puis seuillage conserve une trajectoire nettement en marches, la
variante spline manuelle est documentée dans
[`SPLINE_ALPHA_MASK_PIPELINE.md`](SPLINE_ALPHA_MASK_PIPELINE.md). Le réglage
`fit_error=1.0` a été retenu sur AR0604 comme compromis entre cette recette
sigma3 et l'ancienne spline `fit_error=2.0`; il reste soumis à QA, jamais
automatique.

Le but est de lisser la **géométrie** du masque : arrondir les marches, puis
ajuster très finement la frontière opaque/transparente. Ce n'est pas un fondu
d'alpha. Le résultat reste binaire (`0` ou `255`) afin de garder une couverture
de rive nette.

## Préconditions et invariants

- Le build de référence est déjà valide : mêmes RGB x4, même TIS, pages PVRZ
  DXT5, et alpha restauré depuis le jeu.
- Lire d'abord `AREA_PREFLIGHT.md`, `ALPHA_MAP_PIPELINE.md`,
  `SECONDARY_TILE_PIPELINE.md` et, en présence d'eau, `WATER_MAP_PIPELINE.md`.
- Ne jamais déduire l'alpha depuis le RGB noir : noir peut être du décor ou du
  vide technique.
- L'overlay global (`WTSWAM`, `WTSEW`, `WTOIL`, etc.) reste inchangé. On corrige
  seulement les pages `ARxxxx.TIS` / `Axxxxxx.PVRZ` de la zone.
- La primaire et la secondaire WED sont deux états distincts. Traiter les deux
  lorsque la zone porte des tuiles secondaires (porte, décor conditionnel,
  fontaine). Ne pas appliquer le masque d'un état à l'autre.
- Chaque essai reçoit son propre `maps/<AREA>/runs/<run>/05_build/` et son
  propre backup d'installation. Aucun build antérieur n'est écrasé.

## Méthode

1. Partir d'un build PVRZ x4 déjà intégré et validé. Conserver son RGB,
   l'ordre des tuiles, le TIS et le layout d'atlas.
2. Pour chaque état WED, reconstruire sur un canvas **complet** l'alpha x4 des
   tuiles réellement dessinées. Ne pas flouter tuile par tuile : la frontière
   traverserait sinon les joints de 64 px.
3. Appliquer la recette géométrique :

   ```text
   alpha > 127 ? 255 : 0
   → GaussianBlur(sigma x4)
   → alpha > 127 ? 255 : 0
   ```

4. Découper de nouveau le canvas par tuiles WED, replacer uniquement leurs
   alphas dans les pages PVRZ et réencoder en DXT5. Le RGB doit rester
   strictement inchangé ; le TIS reste identique.
5. Vérifier le build, installer uniquement les assets de zone après backup,
   comparer les SHA-256, puis faire la QA en jeu sur tous les états WED.

Le prototype `AR0604` vérifie que chaque tuile WED concernée n'est employée que
par une cellule de l'état traité. Si une zone réutilise une même tuile à des
positions différentes, ne pas réemployer ce prototype tel quel : il faut soit
confirmer que le résultat alpha est identique à toutes les occurrences, soit
dupliquer ces tuiles proprement avant la correction.

## Réglages ouverts

Tous les rayons ci-dessous sont exprimés en **pixels x4**, pas en pixels monde
x1. Les augmenter un par un et conserver une capture comparable.

| Réglage | Effet | Valeur AR0604 retenue | Risque |
|---|---|---:|---|
| Seuil | Décide la frontière binaire après le flou | `127` | Déplace uniformément le contour ; ne pas le changer en même temps que les autres réglages. |
| `sigma` | Arrondit/simplifie la silhouette avant seuillage | `3` | Trop élevé déforme les détails ou fusionne des formes proches. |
| Érosion opaque | Réduit l'opaque, donc agrandit légèrement la transparence/eau | `2` | Peut manger une rive ou un décor si trop forte. Commencer à `1`, puis `2`. |
| Dilatation opaque | Agrandit l'opaque, donc réduit la transparence/eau | `0` | Peut renforcer un liseré noir. C'est ce qui s'est produit sur AR0604 à `1`. |

Une érosion ou une dilatation de `1` px x4 représente environ `0,25` px logique
x1. Les deux opérations sont exclusives dans un essai donné. La variante de
référence / retour arrière pour AR0604 est :

```text
threshold 127 → Gaussian sigma 3 x4 → threshold 127 → erosion opaque 2 px x4
```

L'essai actuellement sélectionné par l'utilisateur pour AR0604 est la dérivée
spline `fit_error=1.0`, construite à partir de cette référence selon
[`SPLINE_ALPHA_MASK_PIPELINE.md`](SPLINE_ALPHA_MASK_PIPELINE.md). La référence
sigma3 + érosion 2 reste conservée car elle est le point de retour sûr.

Le nettoyage peut encore être ajusté : `sigma`, seuil et érosion sont des
paramètres de QA, non une vérité globale. Si un défaut ne concerne qu'une
portion de rive, préférer un masque local documenté plutôt que dégrader toute
la carte. Si une lacune reste noire, vérifier d'abord sa couverture WED : une
transparence hors cellule liquide n'a pas le même remède qu'un liseré opaque
au-dessus d'une cellule d'eau.

## Implémentation de référence AR0604

Le prototype reproductible est conservé avec le run, afin de ne pas modifier le
pipeline de production avant une seconde validation :

```powershell
python maps/AR0604/runs/ar0604-geometric-alpha-sigma3-20260823/build_geometric_alpha_sigma3.py `
  <build-reference> <nouveau-build> --sigma 3 --opaque-erosion-x4 2
```

Il traite séparément les 437 cellules primaires et les 83 cellules secondaires
d'AR0604. Le build actuellement validé par l'utilisateur est :

```text
maps/AR0604/runs/ar0604-geometric-alpha-sigma3-erode2-20260823/
  05_build/x4-primary-secondary-geometric-alpha-sigma3-erode2/
```

## Validation et intégration

Avant l'installation :

```powershell
python pipeline/scripts/verify_upscaled.py AR0604 <nouveau-build> <rendu-primaire-x4.png>
```

Exiger :

- `out-of-bounds tiles: 0` ;
- dimension x4 de `256` par tuile ;
- pages PVRZ DXT5 ;
- build et script de provenance archivés dans le nouveau run.

Jeu fermé : sauvegarder les dix fichiers actifs d'AR0604, copier uniquement
`AR0604.TIS` et `A060400.PVRZ` à `A060408.PVRZ`, puis comparer les hashes.
Conserver les captures Steam avant/après dans `06_qa/` et noter le réglage dans
`TEST.md`. Ne mettre à jour le catalogue ou un manifeste de release qu'après
validation explicite de l'utilisateur.

## Historique AR0604

| Essai | Résultat |
|---|---|
| Feather alpha / water feather | N'a pas supprimé les marches géométriques. |
| `sigma 3` seul | Contours beaucoup plus propres, mais quelques liserés noirs. |
| `sigma 3` + dilatation opaque 1 px x4 | A renforcé le noir : rejeté. |
| `sigma 3` + érosion opaque 1 px x4 | Amélioration nette. |
| `sigma 3` + érosion opaque 2 px x4 | Réglage de référence validé, conservé comme point de retour pour les essais suivants. |
| Spline périodique `fit_error=2.0` | Contours très propres mais quelques petites pointes dérivent : conservé comme essai historique. |
| Spline périodique `fit_error=1.0` | Compromis choisi en QA AR0604 : fortement lissé, plus fidèle que `2.0`. Pipeline manuel documenté séparément. |
