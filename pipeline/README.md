# Maps — pipeline de référence

Point d'entrée unique pour les décors TIS/PVRZ. L'état courant et le run sélectionné viennent
exclusivement d'[`../areas.csv`](../areas.csv). Les scripts vivent dans `scripts/`; leur classement
par domaine est dans [`scripts/README.md`](scripts/README.md).

## Méthode actuelle

```text
rendus x1 vérifiés
  → préflight automatique
  → audit eau si routé
  → SeedVR2 7B INT8 / LAB / x4
  → build TIS/PVRZ
  → vérification technique
  → installation réversible
  → QA utilisateur
  → décision catalogue
  → décision release séparée
```

AR0602 utilise actuellement le run x4 7B/LAB sans masque CGI désigné par `areas.csv`. Les anciens
essais hybrides ou x2 ne sont pas des références.

## Procédure et gates

### 1. Vérifier le maître x1

```powershell
python pipeline/scripts/validate_x1_masters.py --area ARxxxx
```

Gate : `OK` sur chaque variante requise. `--fix` modifie le maître ; ne l'utiliser qu'après avoir
confirmé que la régénération depuis le jeu est souhaitée.

### 2. Qualifier la zone

```powershell
python pipeline/scripts/audit_area_preflight.py `
  ARxxxx maps/ARxxxx/runs/<run>/00_preflight/ARxxxx-preflight.json
```

Gate : `blockers: []`. Le rapport route vers eau, alpha, secondaires et jour/nuit. Lire
[`AREA_PREFLIGHT.md`](AREA_PREFLIGHT.md) si une branche est requise.

### 3. Auditer l'eau, si routée

```powershell
python pipeline/scripts/audit_water_area.py `
  ARxxxx maps/ARxxxx/runs/<run>/00_water_audit/ARxxxx-water-audit.json
```

Appliquer ensuite [`WATER_MAP_PIPELINE.md`](WATER_MAP_PIPELINE.md). La politique des overlays
globaux est définie uniquement par `releases/BG2-HD-Upscale/manifests/overlay-sources.json`; ne
jamais la déduire de l'installation.

### 4. Produire les images x4

Lire `split_seedvr` dans `areas.csv`, puis utiliser uniquement l'orchestrateur actuel :

```powershell
python pipeline/scripts/run_seedvr_comfyui.py `
  --area ARxxxx --run <run> --preflight <preflight.json> `
  --tile-kind tuiles-principales --split-grid 2 4 `
  --scale 4 --expected-scale 4
```

Ajouter le secondaire avec `--append` lorsqu'il est requis. Adapter `--split-rows` ou
`--split-grid C R` à la valeur du catalogue. Le découpage intégré conserve le recouvrement et
l'alignement ; les anciens splitters manuels sont archivés et ne doivent pas être utilisés.

Gate : dimensions assemblées exactement égales aux dimensions x1 multipliées par quatre.

### 5. Construire

```powershell
python pipeline/scripts/build_upscaled_area.py `
  ARxxxx <principale-x4.png> <build-dir> <secondaire-x4.png>
```

- DXT1 pour une zone totalement opaque ; DXT5 dès qu'un alpha est nécessaire.
- `0 resampled` obligatoire.
- Pages PVRZ 2048 par défaut, 4096 seulement pour respecter le resref de huit caractères.
- Ne jamais forcer une taille de page pour « améliorer » l'image.
- Appliquer les options eau indiquées par le rapport, pas à l'intuition.

### 6. Vérifier

```powershell
python pipeline/scripts/verify_upscaled.py ARxxxx <build-dir> <principale-x4.png>
```

Gates : dimensions de tuile x4, `out-of-bounds tiles: 0`, inventaire TIS/PVRZ fermé et noms de
resref valides. Le PSNR est informatif pour l'eau et les zones transparentes.

### 7. Installer et restaurer

Jeu et InfinityLoader fermés. Utiliser les scripts transactionnels adaptés au type d'asset, garder
le reçu `install-backup.json`, puis comparer tous les SHA-256. Ne jamais copier un dossier de build
à la main ni écraser un overlay partagé au passage.

Gate : inventaire attendu exact et zéro divergence build ↔ jeu.

Un repack expérimental de l'encapsulation Deflate peut être produit sans reconstruire les images
ni modifier le PVR/DXT décodé :

```powershell
python pipeline/scripts/repack_pvrz_compression.py `
  <build-source> <nouveau-dossier-absent> --level 0
```

Cette branche sert uniquement à mesurer la latence atomique des grandes pages PVRZ. Elle exige un
nouveau dossier, copie le TIS à l'identique, vérifie le SHA-256 de chaque PVR décodé et émet
`repack-manifest.json`. Son surcoût disque doit être mesuré ; son résultat reste `pending-ingame`
et ne change ni `areas.csv` ni la méthode de build courante sans une décision ultérieure.

### 8. QA et promotion

Une QA requiert une session ingame contrôlée et l'acceptation explicite de l'utilisateur. Une
capture, un log, un fichier d'override ou `installed-pending-qa` n'est pas une validation.

Après QA, demander séparément :

1. la mise à jour d'`areas.csv` ;
2. l'intégration au manifeste de release selon `AGENTS.md`.

Ne jamais modifier `$mapSpecs`, `content.json`, le staging ou l'archive sans autorisation
affirmative ponctuelle.

## Branches spécialisées actives

| Besoin | Document |
|---|---|
| Qualification | [`AREA_PREFLIGHT.md`](AREA_PREFLIGHT.md) |
| Découpage | [`MAP_SPLITTING_POLICY.md`](MAP_SPLITTING_POLICY.md) |
| Jour/nuit | [`DAY_NIGHT_MAP_PIPELINE.md`](DAY_NIGHT_MAP_PIPELINE.md) |
| Eau | [`WATER_MAP_PIPELINE.md`](WATER_MAP_PIPELINE.md) |
| Autres liquides | [`OTHER_LIQUID_MAP_PIPELINE.md`](OTHER_LIQUID_MAP_PIPELINE.md) |
| Alpha | [`ALPHA_MAP_PIPELINE.md`](ALPHA_MAP_PIPELINE.md) |
| Secondaires | [`SECONDARY_TILE_PIPELINE.md`](SECONDARY_TILE_PIPELINE.md) |
| Nettoyage géométrique alpha | [`GEOMETRIC_ALPHA_MASK_CLEANUP.md`](GEOMETRIC_ALPHA_MASK_CLEANUP.md) |
| Masque spline validé | [`SPLINE_ALPHA_MASK_PIPELINE.md`](SPLINE_ALPHA_MASK_PIPELINE.md) |
| Correction Topaz locale | [`TOPAZ_GIGAPIXEL_CLI_REFERENCE.md`](TOPAZ_GIGAPIXEL_CLI_REFERENCE.md) |

Les post-mortems AR0300, AR0413 et AR2903 sont archivés. Leurs conclusions réutilisables sont dans
[`../docs/DECISIONS.md`](../docs/DECISIONS.md), pas dans la procédure courante.

## Tests légers

Le cœur maps manque encore de fixtures unitaires complètes. Pour une modification de structure ou
documentation :

```powershell
python -m unittest pipeline.tests.test_repository_docs
python pipeline/scripts/audit_area_preflight.py --help
python pipeline/scripts/validate_x1_masters.py --help
python pipeline/scripts/audit_water_area.py --help
python pipeline/scripts/run_seedvr_comfyui.py --help
```

Pour une modification fonctionnelle, ajouter d'abord une fixture WED/TIS/PVRZ minimale au lieu de
lancer une inférence lourde.
