# Eau BG2EE — index rapide

Ce dossier rassemble des solutions observées. Il n'impose ni ordre de traitement, ni lecture
préalable, ni voie 1 avant voie 2, ni audit, ni création de reçu à chaque essai. Partir du symptôme
et ouvrir uniquement la référence utile.

## Où chercher

**Appliquer le travail eau à une map : [`WATER_MAP_RUNBOOK.md`](WATER_MAP_RUNBOOK.md)** (ordre, STOP, installation, QA).
Chaînes : [spatiale x4](SPATIAL_X4_PIPELINE.md) → [30 FPS](TEMPORAL_30FPS_PIPELINE.md) → [contours](CONTOUR_MATTE_PIPELINE.md) ;
paramètres par famille : [`liquid-family-standard-v1.json`](liquid-family-standard-v1.json).
État standard courant : `lake` (AR1600), `pool` (AR0408/AR0703), `sewage` (AR2100) et `swamp`
(AR0500/AR0500N) ont des validations ingame A/B ; C reste utilisable provisoirement et devra être refondu puis
réappliqué à toutes les maps/familles traitées (`WATER-006`).

| Besoin | Référence |
|---|---|
| Symptôme visuel ou crash | [`VALIDATED_WATER_RECIPES.md`](VALIDATED_WATER_RECIPES.md) |
| Réparation TIS/PVRZ/WED | [`../WATER_REPAIR_RUNBOOK.md`](../WATER_REPAIR_RUNBOOK.md) |
| Mouvement procédural/runtime | [`../WATER_ROUTE2_EXPERIMENT_RUNBOOK.md`](../WATER_ROUTE2_EXPERIMENT_RUNBOOK.md) |
| Animation 30 FPS réels, toutes familles | [`TEMPORAL_30FPS_PIPELINE.md`](TEMPORAL_30FPS_PIPELINE.md) |
| Contours devant l'eau (frange sombre, cordes épaisses) | [`CONTOUR_MATTE_PIPELINE.md`](CONTOUR_MATTE_PIPELINE.md) |
| Conception surfaces liquides | [`BASE_PIPELINES_SURFACES_LIQUIDES.md`](BASE_PIPELINES_SURFACES_LIQUIDES.md) |
| File QA ingame exhaustive, une carte à la fois | `ingame-map-tracking-v1.json` |
| Sélection finale et QA | [`WATER_RELEASE_TRACKING.md`](WATER_RELEASE_TRACKING.md) |
| Politique machine par famille | `family-policy-v1.json` |
| Registre route2 | `route2-registry-v1.json` et registre v2 du moteur |

## Cas AR1000 jour et nuit validés

- Famille : `pool-wtpool` ; identité : `AR1000` jour uniquement.
- V1 : crash causé par un nom de page PVRZ incompatible.
- V2 : quadrillage causé par SeedVR, qui amplifiait la trame diagonale de la source 64×64.
- V3 : WTPOOL2 bilinéaire x4 en contexte périodique 3×3, sans IA ; quadrillage supprimé mais eau
  jugée figée à `q=0`.
- V5 validée ingame : 6→36 phases linéaires à 15 Hz, interpolation renderer 30 FPS, matériau eau
  `id=1`, route2 exacte `q=0.70`.
- `AR1000N` appartient à `swamp-wtswam`, pas à `pool-wtpool` : alias sec `WSWPIL`, 36 phases à
  15 Hz, blend 30 FPS, matériau `id=5`, route2 exacte `q=0.70`.
- Le rendu nocturne sec d'AR1000N est validé ingame avec son animation discrète ; `WSWPILR` pluie
  est installé mais n'a pas été observé séparément.

Références finales :

- `manifests/ar1000-wtpool-route2-validated-20260912-v5.json`
- `manifests/ar1000-wtpool-route2-installed-20260912-v5.json`
- `manifests/ar1000n-wtswam-route2-validated-20260912-v1.json`
- `manifests/ar1000n-wtswam-route2-installed-20260912-v1.json`
- `../scripts/build_ar1000_wtpool_route2_candidate.py`
- `../scripts/build_ar1000n_wtswam_route2_candidate.py`

## État et sécurité

`ingame-map-tracking-v1.json` suit les 67 WED liquides, variantes nuit incluses, en regroupant les
overlays par carte. `release-tracking-v1.json` conserve séparément les sélections finales. Audits :

```powershell
python -B pipeline/scripts/audit_water_ingame_tracking.py --json
python -B pipeline/scripts/audit_water_release_tracking.py --json
```

Fermer le jeu et InfinityLoader avant une installation. Une validation ingame et une intégration
release sont deux décisions séparées ; aucun fichier de release n'est modifié sans demande explicite.
