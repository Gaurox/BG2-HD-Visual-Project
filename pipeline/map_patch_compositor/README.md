# Compositing déterministe de patch de carte

Insère un patch raster dans une map raster sans IA, sans modifier les entrées et sans promotion
automatique vers `areas.csv`, un build, l'installation ou la release.

## Contrat v1

- Entrées : PNG/BMP/TIFF sRGB 8 bits `RGB` ou `RGBA`, sans ICC embarqué; JPEG/WebP refusés en mode strict.
- Transformation : échelle isotrope + translation, sous-pixel autorisé; pas de rotation/perspective.
- Raccord : gradients du décor périphérique, optimisation robuste, rejet des candidats ambigus.
- Masque : différence résiduelle, morphologie, dilatation, fade distance + gaussien, garde anti-bord
  rectangulaire.
- Couleur : correction LAB bornée, gardée seulement si elle améliore le contexte commun.
- Alpha de la map : conservé. Alpha du patch éventuel réduit seulement la couverture de fusion.
- Sortie : format/dimensions de la map; pixels hors masque conservés exactement après décodage.

Le patch fourni à AR3003 est une image RGB opaque et la map comporte des décors symétriques : une
`map_search_roi` est recommandée pour choisir une occurrence précise si le score de crête est ambigu.

## Commandes

Préparer/valider sans écrire :

```powershell
python -m pipeline.map_patch_compositor inspect --map <map.png> --patch <patch.png>
python -m pipeline.map_patch_compositor plan --map <map.png> --patch <patch.png> --config <config.json>
```

Composer uniquement après décision explicite, dans un nouveau dossier absent :

```powershell
python -m pipeline.map_patch_compositor compose `
  --map <map.png> --patch <patch.png> --config <config.json> `
  --output-run output/map-patch-compositor/<run-id> --run
```

`compose` crée `<output-run>.partial`, contrôle les hashes source avant/après, puis renomme
atomiquement le dossier. Une erreur conserve le `.partial` et ne produit pas d'image finale.

## Workflow Codex par zone

Quand un patch est joint au chat et que l'utilisateur désigne `ARxxxx`, employer les commandes par
zone. Elles résolvent la primaire x4 retenue par `areas.csv`, ou la sélection de patch courante si
elle existe.

```powershell
# Lecture seule : map parent, run proposé, destination et contraintes de recalage.
python -m pipeline.map_patch_compositor area-plan --area AR3003 --patch <patch.png>

# Écrit un nouveau run dérivé ; le raster parent n'est jamais modifié ni supprimé.
python -m pipeline.map_patch_compositor area-apply `
  --area AR3003 --patch <patch.png> --config <config.json> --run

# Après validation visuelle explicite : pointe vers le nouveau raster pour un futur patch/build.
python -m pipeline.map_patch_compositor area-select `
  --area AR3003 --run-id <run-id-produit> --run
```

`area-apply` produit :

```text
maps/<AREA>/runs/<nouveau-run>/
├── tuiles-principales/03_assemble/<map>--patch-<hash>.png
├── control/
├── config.resolved.json
└── run.json
```

Le raster reste dans un nouveau run voisin du run parent, jamais dans le dossier du parent scellé.
`area-select` conserve une sélection immuable sous
`maps/<AREA>/patch-compositor-primary-selections/` et met à jour seulement le pointeur courant
`maps/<AREA>/patch-compositor-primary-current.json`.

## Configuration

Copier `defaults.json`, puis ne surcharger que les clés nécessaires. Coordonnées : `[x, y, largeur,
hauteur]`, origine haut-gauche; `map_search_roi`, exclusions map/patch et `object_seed_patch` sont
optionnels. Réduire `scale_min`/`scale_max` au plus près de l’échelle attendue : une plage large est
moins discriminante sur les décors répétés.

Le manifeste de run contient les hashes, paramètres résolus, versions, transformation, métriques et
hashs de sortie. Les chemins externes sont décrits par nom+hash, sans chemin personnel absolu.

## Artefacts `compose`

```text
run.json
config.resolved.json
result/<nom-map>.<format>
control/placement.json
control/registration-mask-patch.png
control/object-support-mask-map.png
control/blend-mask-map.png
control/residual-before-map.png
control/residual-after-map.png
control/before-after-zoom.png
control/metrics.json
```

Le résultat reste un raster intermédiaire. Même après `area-select`, construire TIS/PVRZ, installer,
valider en jeu ou changer `areas.csv` restent des décisions séparées : une sélection de patch ne
prouve ni QA, ni installation, ni release.
