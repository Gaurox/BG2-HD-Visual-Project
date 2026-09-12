# Eau BG2EE — index rapide

Ce dossier rassemble des solutions observées. Il n'impose ni ordre de traitement, ni lecture
préalable, ni voie 1 avant voie 2, ni audit, ni création de reçu à chaque essai. Partir du symptôme
et ouvrir uniquement la référence utile.

## Où chercher

| Besoin | Référence |
|---|---|
| Symptôme visuel ou crash | [`VALIDATED_WATER_RECIPES.md`](VALIDATED_WATER_RECIPES.md) |
| Réparation TIS/PVRZ/WED | [`../WATER_REPAIR_RUNBOOK.md`](../WATER_REPAIR_RUNBOOK.md) |
| Mouvement procédural/runtime | [`../WATER_ROUTE2_EXPERIMENT_RUNBOOK.md`](../WATER_ROUTE2_EXPERIMENT_RUNBOOK.md) |
| Sélection finale et QA | [`WATER_RELEASE_TRACKING.md`](WATER_RELEASE_TRACKING.md) |
| Politique machine par famille | `family-policy-v1.json` |
| Registre route2 | `route2-registry-v1.json` et registre v2 du moteur |

## Cas AR1000 jour validé

- Famille : `pool-wtpool` ; identité : `AR1000` jour uniquement.
- V1 : crash causé par un nom de page PVRZ incompatible.
- V2 : quadrillage causé par SeedVR, qui amplifiait la trame diagonale de la source 64×64.
- V3 : WTPOOL2 bilinéaire x4 en contexte périodique 3×3, sans IA ; quadrillage supprimé mais eau
  jugée figée à `q=0`.
- V5 validée ingame : 6→36 phases linéaires à 15 Hz, interpolation renderer 30 FPS, matériau eau
  `id=1`, route2 exacte `q=0.70`.
- `AR1000N` n'a pas été traité et aucune conclusion ne lui est propagée.

Références finales :

- `manifests/ar1000-wtpool-route2-validated-20260912-v5.json`
- `manifests/ar1000-wtpool-route2-installed-20260912-v5.json`
- `../scripts/build_ar1000_wtpool_route2_candidate.py`

## État et sécurité

`release-tracking-v1.json` est l'état machine courant. Son audit est facultatif :

```powershell
python -B pipeline/scripts/audit_water_release_tracking.py --json
```

Fermer le jeu et InfinityLoader avant une installation. Une validation ingame et une intégration
release sont deux décisions séparées ; aucun fichier de release n'est modifié sans demande explicite.
