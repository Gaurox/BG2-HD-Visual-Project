# Contours devant l'eau — détourage par silhouette RGB x4 (toutes familles)

**Contrat C du 2026-09-25 : matte silhouette RGB x4 + spline fit 1.0 + `central_water`, défaut pour toutes les
familles** (validé AR1600, puis sur la map test de chaque famille). Exceptions **par map** (jamais par famille) :
`contour_map_overrides` du standard — AR0408 et AR0703 gardent le matte gaussien antérieur (spline refusée en jeu).
Le producteur lit ce défaut et ces exceptions (`contour_spline_fit`) ; `--spline-fit 0` = matte gaussien seul.
Historique : matte gaussien validé AR1600 (2026-09-23), jugé améliorable (AR0500N, 2026-09-24), remplacé.
Famille `sewage` validée sur AR2100 avec le matte actuel accepté en l'état ; adaptation `CONTOUR-NET`
explicitement abandonnée. Contrat : `liquid-family-standard-v1.json`.
Famille `pool` validée sur AR0703 (10 paires, alpha 128).
Historique et mesures : [`AR1600_CONTOURS_MATTE_ESSAI_20260923.md`](AR1600_CONTOURS_MATTE_ESSAI_20260923.md).
Remplace l'approche Potrace du masque x1 ([essai Astra](AR1600_CONTOURS_ESSAI_20260923.md), rejeté).

## Principe

| Constat (AR1600) | Conséquence |
|---|---|
| Frange sombre = fond noir du RGB x4 révélé par l'alpha HD adouci, hors masque natif | corriger la géométrie, pas « éclaircir » |
| Le RGB x4 dessine l'objet net, droit, plus fin, **dans** le masque natif, sur fond noir | le RGB x4 est la meilleure source de silhouette |
| Potrace du masque x1 sur cordes de 1–4 px x1 → formes en « os », marbrure | ne pas vectoriser le x1 pour les éléments fins |
| Liseré clair SeedVR au bord (≈2 px objets larges, 1 px cordes) | recolorer depuis l'intérieur du même objet |

Recette (fonctions `silhouette`, `edge_rgb`, `extend_colours` de `build_water_contour_matte_trial.py`) :

1. Couverture M : RGB x4 non noir (> 20) à ≤ 4 px x4 du bord natif, fermeture 3×3, taches < 12 px ôtées,
   AA gaussien σ 0,8 / rampe 0,35 ; intérieur natif > 4 px toujours opaque (détails sombres gardés).
2. RGB primaire : liseré recoloré (2 px si largeur locale > 8 px x4 ; 1 px depuis l'axe pour 4–8 px ;
   intact en dessous), puis couleur prolongée 5 px vers l'extérieur (aucun noir sous filtrage/AA).
3. RGB secondaire (art marin) prolongé côté objet.
4. Passes `U → P → a·S` : `S = 1−M`, `P = M/(1−a(1−M))`, `a` = WATER_ALPHA de l'ARE (0 → 128).
5. BC3 sélectif : seuls les blocs 4×4 touchés changent ; alpha à extrémités exactes ; marges 4 px recalculées
   pour les canaux modifiés ; blocs hors sélection octet-identiques.

## Producteur

[`pipeline/scripts/build_water_contour_matte.py`](../scripts/build_water_contour_matte.py) — une map par run ;
fenêtres 8×8 cellules + halo 1 cellule. Régression : reproduit à l'octet les 804 tuiles AR1600 installées.
Tests : `pipeline/tests/test_water_contour_matte.py`.

```powershell
$v = 'G:/AI/BG2_Vanilla_23534562'
python -B pipeline/scripts/build_water_contour_matte.py survey --area AR0404 AR2100 --vanilla-root $v
python -B pipeline/scripts/build_water_contour_matte.py prepare --area AR0404 --vanilla-root $v --output maps/water-batches/runs/ar0404-contour-matte-<date>-v1
python -B pipeline/scripts/build_water_contour_matte.py encode  --area AR0404 --vanilla-root $v --output maps/water-batches/runs/ar0404-contour-matte-<date>-v1
```

Installation, jeu fermé : `Install-AreaOverrideAssets.ps1 -SourceRoot <run>/override-candidate -BackupRoot backups/water/<run>`,
puis reçu `record_water_decision.py install --kind contour` ; déroulé complet : [WATER_MAP_RUNBOOK.md](WATER_MAP_RUNBOOK.md). Seules des pages `A…PVRZ` de base changent ; WED/TIS/overlays/DLL intacts,
donc compatible avec l'eau 30 FPS ([TEMPORAL_30FPS_PIPELINE.md](TEMPORAL_30FPS_PIPELINE.md)).

### Cellules d'eau pure voisines (`central_water`, défaut depuis 2026-09-25)

Les cellules liquides sans secondaire ont une primaire opaque ; comptées comme objet, leur couverture débordait de
1–4 px dans la paire voisine → ligne au bord de cellule (AR5000 : saut 5,69 vs 2,7 de référence). Par défaut elles
entrent dans le matte comme eau (RGB noir, masque vide). `--no-central-water` = matte historique (runs antérieurs).
Jonctions eau pure ↔ paire mesurées en live (rapport au saut de bloc 4×4) avant reprise : AR1600 1,37,
AR0500N 1,41, AR0500 1,14 ; AR0503 1,03, AR2100 1,02 (non repris).

### Portée et refus (automatiques, rapportés dans `prepare.json`)

- Traitées : cellules WED avec secondaire et un bit d'overlay liquide (`flags & 0x1E`).
- Ignorées : sans secondaire (eau pure ou art translucide, contrat différent), portes, animées, tuile partagée,
  paire non complémentaire, sentinelle, tuile dont le RGB hors masque natif n'est pas noir (> 15 %).
- Refus carte : pages non BC3, atlas autre que pas 264/marge 4, ou fond non noir généralisé
  (médiane > 5 % ou > 5 % des tuiles) = **base déjà traitée**. Relancer alors depuis les pages non traitées :
  `--source-backup <install-backup>` (répétable, premier trouvé prioritaire). AR1600 :
  `backups/water/ar1600-contour-colour-trial-20260923-v2/override-backup-20260923-063203` puis
  `backups/water/ar1600-contour-matte-map-20260923-v1/override-backup-20260923-205837`.
- Variante nuit sans ARE propre (ex. AR1000N) : WATER_ALPHA lu dans l'ARE jour.

## État par map — survey du 2026-09-23 (lecture seule)

Rapport : [`manifests/contour-matte-survey-20260923-v1.json`](manifests/contour-matte-survey-20260923-v1.json).
Instantané historique du survey 2026-09-23. C est désormais installé sur AR1600, AR2100, AR0408, AR0703,
AR0500, AR0500N, AR5200 et AR0503 ; toutes ces installations restent provisoires au niveau du standard global. `a` ≠ 128 :
composition de paire non encore vue en jeu.

| Famille | Map | a | Paires | Sans secondaire | Ignorées | Prêt |
|---|---|---:|---:|---:|---:|---|
| WTLAKE | AR1600 | 128 | 421 | 166 | — | **installé** (relance : backups) |
| WTLAKE | AR0900 / AR0204 / AR2300 | 128 | 858 / 442 / 1105 | 775 / 218 / 0 | 2 / 1 / 6 fond | oui |
| WTPOOL | AR1000 | 128 | 37 | 0 | 0 | oui |
| WTSWAM | AR1000N / AR1607 / AR1800 | 128 / **100** / 128 | 37 / 348 / 94 | 0 / 525 / 7 | 0 / 1 / 0 | oui |
| WTSEW | AR0404 / AR2100 | 128 | 138 / 169 | 2 / 39 | 0 | oui |
| WTOIL | AR0413 / AR0503 | 128 | 227 / 67 | 349 / 84 | 0 | oui ; **AR0503 installé** ; AR0413 : contrat alpha0 historique à surveiller |
| WTLAKA–D | AR3000 / AR6300 | 128 / **160** | 137 / 36 | 184 / 0 | 1 / 0 | oui ; **AR6300 installé** (alpha 160 validé) |
| WTLAVA–D | AR0011 / AR5200 | 128 | 101 / 287 | 0 | 0 / 5 | oui ; **AR5200 installé** |
| WT5000A–D | AR5203 / AR5000 | 128 | 267 / 402 | 366 / 321 | 1 / 0 | oui ; **AR5000 installé** (v3 `central_water`) |

### Validations par map

| Map | Famille | Run | QA en jeu | Suite |
|---|---|---|---|---|
| AR2100 | WTSEW | `ar2100-contour-matte-20260923-v1` | validée avec réserve — `ar2100-contour-user-qa-20260923-v3.json` | matte accepté en l'état ; adaptation CONTOUR-NET abandonnée (v1 rejet historique, v2 citation non canonique) |
| AR0408 | WTPOOL | `ar0408-contour-matte-20260923-v1` | **à revoir** (utilisateur, 2026-09-23) — reçu `ar0408-contour-installed-20260923-v1.json` encore installé | défaut non décrit : demander ce qui ne va pas avant tout nouvel essai `-v2` |
| AR0703 | WTPOOL | `ar0703-contour-matte-20260923-v1` | validée — `ar0703-contour-user-qa-20260923-v1.json` | 10 paires ; alpha 128 |
| AR0500 | WTSWAM | `ar0500-contour-matte-20260924-v1` | validation jour historique — `ar0500-contour-user-qa-20260924-v1.json` | supersédée comme standard par la décision globale du 2026-09-24 |
| AR0503 | WTOIL | `ar0503-contour-matte-20260924-v1` | validée avec réserve — `ar0503-contour-user-qa-20260924-v1.json` | 67 paires, 84 cellules sans secondaire ; construit sur les pages réparées par A ; mêmes réserves que les autres familles |
| AR5000 | WT5000A–D | `ar5000-contour-matte-20260924-v3` (v1 : lignes aux jonctions) | validée — `ar5000-contour-user-qa-20260925-v1.json` | `central_water` sur les pages A-v2 (240 interfaces) ; jonction 5,69 → 3,14 |
| AR6300 | WTLAKA–D | `ar6300-contour-matte-20260925-v1` (réinstallé) | validée — `ar6300-contour-user-qa-20260925-v1.json` | 36 paires, alpha 160 ; essais spline v3 (fit 1) / v5 (fit 4 + AA) non retenus |
| AR5200 | WTLAVA–D | `ar5200-contour-matte-20260924-v1` | validée avec réserve — `ar5200-contour-user-qa-20260924-v1.json` | 287 paires, 5 ignorées fond non noir ; mêmes réserves que les autres familles (C provisoire) |
| AR0500N | WTSWAM | `ar0500n-contour-matte-20260924-v1` | **rejetée** — `ar0500n-contour-user-qa-20260924-v1.json` | version courante conservée pour le développement ; refonte puis réapplication toutes familles à prévoir |
| Lot swamp (14, liste : TEMPORAL_30FPS_PIPELINE) | WTSWAM (+ WTPOOL AR1100) | `<map>-contour-matte-20260925-v1` (spline fit 1 + `central_water`, a = 128) | **validées** 2026-09-25 — `<map>-contour-user-qa-20260925-v1.json` | construit après A+B, sans reprise |
| AR1600 / AR0500 / AR0500N | lac / marais | `ar1600|ar0500|ar0500n-contour-matte-20260925-v1` | **validées** 2026-09-25 — `*-contour-user-qa-20260925-v1.json` (AR0500N : remplace le rejet du 2026-09-24) | reprise `central_water` depuis les pages non traitées ; jonction 5,64 → 3,46 / 3,59 → 3,03 / 3,12 → 2,86 (réf. 4,13 / 3,16 / 2,22 : AR0500N reste 1,29×) |

## Spline fit 1 (défaut depuis 2026-09-25)

`spline_coverage` : le contour de la silhouette x4 (trous et îlots conservés) est réajusté par spline périodique
(`build_spline_map_alpha.spline_mask`, fit 1.0 px x4, pas 1,5, suréchantillonnage 2), puis rasterisé par aire ;
bornes identiques au matte (intérieur natif > 4 px opaque, rien au-delà de 4 px du masque natif). **Alpha
seulement** : le RGB reste réparé sur la silhouette d'origine (sinon les creux comblés propagent du noir, AR6300 v2).
`--spline-aa σ` ajoute le flou du matte sur le tracé réajusté (essai fit 4 + AA 0,8 sur AR6300 non retenu).

| Étape | Résultat |
|---|---|
| AR6300, 1er essai fit 1 puis fit 4 + AA | jugé non concluant (tracé anguleux / marche au bord des fenêtres) |
| AR1600, fit 1 sur tous les décors devant l'eau et les berges | **validé** — `ar1600-contour-user-qa-20260925-v2.json` |
| Maps test des familles, fit 1 | validé AR2100, AR0503, AR5200, AR6300, AR5000, AR0500, AR0500N ; **refusé AR0408, AR0703** (matte antérieur réinstallé) |

Défaut résiduel connu, commun aux variantes : fin liseré jaune-clair = RGB de bord recoloré (`edge_rgb`).

## Limites connues

- Liseré cyan-vert résiduel sur éléments < 8 px x4 (échelle, cordages) : correction couleur testée, non retenue.
- Cellules sans secondaire non traitées : objets posés sur l'art marin translucide (ex. AR0900 775, AR1607 525)
  gardent leurs contours actuels.
- Cellules d'art peint (eau/mousse dans le décor) conservées telles quelles : ce ne sont pas des contours.
- Un lot par map ; QA ingame de chaque map avant de généraliser un réglage.
