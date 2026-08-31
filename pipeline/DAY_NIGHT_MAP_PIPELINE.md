# Cartes jour/nuit

`areas.csv` est l'autorité : `has_night_variant`, maîtres x1, `runs_nuit`, `build_nuit` et
`status_nuit`. Ne maintenir aucune liste de zones dans ce guide.

## Contrat

- Un WED `ARxxxxN` réel est obligatoire ; aucun repli silencieux vers le jour.
- Jour et nuit ont des runs, corrections LAB, builds et QA séparés.
- La découpe vient de la surface x1 de chaque variante.
- Les overlays globaux sont partagés et ne font pas partie du build de zone.
- Une validation jour ne valide pas la nuit, et inversement.

## Maîtres et production

```powershell
python pipeline/scripts/batch_extract.py --night
python pipeline/scripts/batch_extract_secondary.py --night
python pipeline/scripts/validate_x1_masters.py --area ARxxxx --night

python pipeline/scripts/audit_area_preflight.py `
  ARxxxx <run-nuit>/00_preflight/ARxxxx-preflight.json

python pipeline/scripts/run_seedvr_comfyui.py `
  --area ARxxxx --run <run-nuit> --preflight <preflight.json> `
  --tile-kind tuiles-principales-nuit --split-grid <col> <lig> `
  --scale 4 --expected-scale 4

python pipeline/scripts/run_seedvr_comfyui.py `
  --area ARxxxx --run <run-nuit> --preflight <preflight.json> `
  --tile-kind tuiles-secondaires-nuit --split-grid <col> <lig> `
  --scale 4 --expected-scale 4 --append

python pipeline/scripts/build_upscaled_area.py `
  ARxxxxN <principale-nuit-x4.png> <build-dir> <secondaire-nuit-x4.png>
python pipeline/scripts/verify_upscaled.py `
  ARxxxxN <build-dir> <principale-nuit-x4.png>
```

Omettre ou adapter `--split-grid` selon [`MAP_SPLITTING_POLICY.md`](MAP_SPLITTING_POLICY.md).

## Limite de nommage PVRZ

Le resref TIS dérivé de la nuit laisse deux chiffres de page (`AxxxxN00..99`), contre trois pour
le jour. Avec des pages de 2048, une grande variante peut dépasser cette limite et planter au
chargement.

`build_upscaled_area.py` :

1. utilise 2048 lorsque le namespace tient ;
2. passe à 4096 seulement si nécessaire ;
3. refuse le build si le plafond reste dépassé.

Ne jamais forcer 4096 pour uniformiser et ne jamais reconvertir un build valide sans décision. Le
rapport de build est la preuve de la taille et du nombre de pages retenus.

## Installation et état

Utiliser `inject_build.py` comme dans [`README.md`](README.md), avec le resref nuit et un reçu
distinct. Après QA explicite, modifier seulement les colonnes nuit de `areas.csv`; l'intégration
release reste une décision séparée.
