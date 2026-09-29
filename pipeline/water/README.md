# Eau BG2EE — index rapide

Ce dossier rassemble des solutions observées. Il n'impose ni ordre de traitement, ni lecture
préalable, ni voie 1 avant voie 2, ni audit, ni création de reçu à chaque essai. Partir du symptôme
et ouvrir uniquement la référence utile.

## Où chercher

**Appliquer le travail eau à une map : [`WATER_MAP_RUNBOOK.md`](WATER_MAP_RUNBOOK.md)** (ordre, STOP, installation, QA).
Chaînes : [spatiale x4](SPATIAL_X4_PIPELINE.md) → [30 FPS](TEMPORAL_30FPS_PIPELINE.md) → [contours](CONTOUR_MATTE_PIPELINE.md) ;
paramètres par famille : [`liquid-family-standard-v1.json`](liquid-family-standard-v1.json).
**État 2026-09-29 : toutes les maps à eau sont traitées** — les 63 WED à eau active sont validées en jeu
(chaîne A/B/C, `campaign.treatment` de `ingame-map-tracking-v1.json`) ; AR0700/AR0700N/AR2804/AR2805 n'ont
aucune cellule d'eau active. Une **revérification générale** (q, pluie, nuit) est ouverte : voir plus bas.

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

## Revérification générale q, pluie, nuit

Campagne `water-review-q-rain-night-20260929` (`campaign.review` + `maps[].review` de
`ingame-map-tracking-v1.json`, audit `audit_water_ingame_tracking.py`). Toutes les maps sont revues, même
déjà validées.

| Colonne | Portée | Contrôle |
|---|---|---|
| `review.q` | 63 WED à eau active | aspect sec ; choisir un q propre à la map (`current` = q du registre installé) |
| `review.rain` | 24 WED dont l'ARE a le bit météo `0x4` | `C:SetWeather(1)`, jeu non en pause, ~10 s ; flaques, pas de mosaïque ; pluie q0 par défaut |
| `review.night` | 6 WED nuit à eau active (AR0046N, AR0300N, AR0500N, AR0900N, AR1000N, AR2000N) | passer la nuit sur la map de jour ; teinte, opacité, raccords |

Nuit : scan du KEY vanilla (2026-09-29) — 31 WED `ARxxxxN` au total, **6 seulement** ont des cellules d'eau actives (ci-dessus) ; AR0700N déclare WTPOOL sans cellule active. Les autres maps à eau (AR1600, AR2300…) n'ont pas de WED nuit : la nuit réutilise la WED de jour sous éclairage nocturne (pas d'asset séparé, contrôlable pendant la revue q).

- Principe : INI `WaterOverlayStrength = 1.00` (plafond neutre) ; q fixé **par identité dans le registre**
  (DLL). Ne jamais régler q par l'INI.
- File : `python -B pipeline/scripts/water_review_queue.py list [--kind q|rain|night]` (commandes console incluses).
- Changer q : entrée(s) sèche(s) de la WED dans une copie du registre courant
  (`requests/<run>/registry-v3.json`), build DLL + `Install-WaterRuntime.ps1`, puis `water_review_queue.py sync-q`.
- Verdict : `water_review_queue.py record --wed ARxxxx --kind q|rain|night --state validated --quote "<message>"`.
- Contrôle log : `WATER_ROUTE2 draw wed=ARxxxx … q=<valeur>` ; opacité appariée : `WATER_ART_OPACITY … drawAlpha=<cible>`.

