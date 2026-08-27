# Masques alpha spline — pipeline manuel à la demande

Cette procédure produit un masque alpha dont le contour est lissé par une
**spline périodique**. Elle est destinée aux silhouettes qui restent en gros
escaliers après l'upscale, alors que le lissage Gaussian seul reste trop fidèle
aux marches. Elle est validée visuellement sur la fontaine `AM0604A` et les
rives d'eau de `AR0604` avec `fit_error=1.0`.

Ce n'est **pas** une étape automatique de l'upscale, du build de map ni du
pipeline 30 fps. Les scripts ne modifient jamais le jeu : ils refusent
d'écraser leur sortie et écrivent seulement le PNG ou le build explicitement
demandé. Une QA visuelle doit approuver chaque emploi.

## Choisir la procédure

| Cible | Script | Ce qui est généré |
|---|---|---|
| Une silhouette d'animation / asset | `build_spline_alpha_mask.py` | un nouveau PNG alpha, sans pack runtime |
| Les rives / masques d'une map PVRZ | `build_spline_map_alpha.py` | un nouveau dossier TIS/PVRZ, sans override |

Pour un contour où les marches sont discrètes, commencer plutôt par le
nettoyage Gaussian documenté dans
[`GEOMETRIC_ALPHA_MASK_CLEANUP.md`](GEOMETRIC_ALPHA_MASK_CLEANUP.md). Employer
la spline lorsqu'il faut lisser la **trajectoire** elle-même.

## Réglage retenu sur AR0604

| Paramètre | Asset (`AM0604A`) | Map (`AR0604`) | Rôle |
|---|---:|---:|---|
| `fit-error` | `1.0` | `1.0` x4 | Compromis retenu : plus fidèle que `2.0`, bien moins crénelé que sigma3. |
| `sample-spacing` | `1.5` px x4 | `1.5` px x4 | Espacement des points de contour avant ajustement. |
| `supersample` | `4` | `2` | Rasterisation anti-aliasée avant réduction Lanczos. |
| seuil d'entrée | `127` | `127` | Définit la frontière opaque/transparente. |

Ne faire varier qu'un paramètre par essai. Descendre `fit-error` vers `0.5`
respecte davantage les petits détails mais laisse revenir des escaliers ; le
monter au-delà de `1.0` arrondit davantage et peut déplacer une pointe ou créer
une petite languette. `2.0` est conservé comme variante historique, pas comme
réglage par défaut.

## A. Créer un masque d'asset

Le script prend un PNG alpha en niveaux de gris ou un PNG RGBA ; il ajuste la
plus grande silhouette fermée. Il convient aux assets à silhouette principale
unique. Pour une map, des trous ou des états WED, utiliser impérativement la
procédure B.

```powershell
python pipeline/scripts/build_spline_alpha_mask.py `
  <alpha-source.png> <nouveau-masque.png> `
  --fit-error 1.0 --sample-spacing 1.5 --threshold 127 --supersample 4
```

Exemple reproductible de la fontaine :

```powershell
python pipeline/scripts/build_spline_alpha_mask.py `
  C:/Users/Adrien/Desktop/AM0604A-alpha-mask-current.png `
  C:/Users/Adrien/Desktop/AM0604A-alpha-mask-spline-fit1.0-retest.png `
  --fit-error 1.0 --sample-spacing 1.5 --supersample 4
```

Le résultat doit d'abord être comparé au masque source. Pour l'appliquer à une
animation 30 fps, faire ensuite — séparément — un nouveau run avec la formule
`alpha_final = alpha_source * masque / 255` :

```powershell
python pipeline/scripts/build_manual_alpha_mask_30fps_v2.py `
  --temporal-run <run-30fps-source> --resref <RESREF> `
  --mask <nouveau-masque.png> --output <nouveau-run>
```

Ce build conserve les RGB et la timeline ; il ne copie rien dans le jeu. Le
découpage par zone, la combinaison avec les autres zones et l'installation
restent des actions explicites décrites dans
[`ANIMATION_PACKS_PAR_ZONE.md`](ANIMATION_PACKS_PAR_ZONE.md).

## B. Créer une variante de map

Préconditions : build de référence déjà valide, pages PVRZ DXT5, WED disponible
dans le jeu installé et zone testable. Le script reconstruit l'alpha sur le
canvas WED complet, pas tuile par tuile. Il traite primaire et secondaire
séparément, préserve les trous/îlots et pose une bordure noire virtuelle pour
fermer correctement une rive qui touche le bord du canvas.

```powershell
python pipeline/scripts/build_spline_map_alpha.py `
  --area ARxxxx <build-reference> <nouveau-build> `
  --fit-error 1.0 --sample-spacing 1.5 --supersample 2
```

Exemple AR0604 :

```powershell
python pipeline/scripts/build_spline_map_alpha.py `
  --area AR0604 `
  maps/AR0604/runs/ar0604-geometric-alpha-sigma3-erode2-20260823/05_build/x4-primary-secondary-geometric-alpha-sigma3-erode2 `
  maps/AR0604/runs/<nouvel-essai>/05_build/x4-primary-secondary-spline-fit1.0 `
  --fit-error 1.0 --sample-spacing 1.5 --supersample 2
```

Puis valider sans lancer le jeu :

```powershell
python pipeline/scripts/verify_upscaled.py ARxxxx <nouveau-build> <rendu-primaire-x4.png>
```

Exiger au minimum : zéro tuile hors limites, dimension x4 correcte, PVRZ DXT5,
rapport `spline-alpha-report.json` présent et rendu des deux états WED vérifié.
Le script s'arrête volontairement si une même tuile est réemployée par plusieurs
cellules WED : ce cas exige une stratégie de duplication de tuiles avant de
modifier l'alpha.

## Installation et retour arrière

Ces scripts ne possèdent volontairement aucune option `--install`. Après QA
des fichiers, jeu fermé : créer un backup neuf, copier seulement le TIS et les
PVRZ de la zone vers `override`, puis comparer les SHA-256. Ne jamais copier
l'overlay liquide global (`WTSWAM`, `WTSEW`, etc.) : il reste stock.

Conserver dans le run : la commande, `spline-alpha-report.json`, les rendus
alpha avant/après, le chemin du backup et les screenshots ingame. Une variante
non validée reste un essai, même si le build technique est sain.

## Limites connues

- Le réglage ne devine pas l'intention d'une pointe extrêmement fine : tester
  d'abord `1.0`, puis réduire seulement si cette pointe dérive.
- Il modifie uniquement l'alpha visé ; il ne corrige pas une texture RGB, un
  mauvais ordre de calques ou une lacune WED.
- Les zones nuit sont des builds indépendants : les traiter et tester
  séparément, jamais par copie de l'alpha jour.
