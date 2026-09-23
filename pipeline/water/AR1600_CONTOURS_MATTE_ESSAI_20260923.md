# AR1600 — contours devant l'eau par silhouette RGB x4 (essai)

2026-09-23. **Zone bateau validée ingame** ([QA](manifests/ar1600-contour-matte-zone-user-qa-20260923-v1.json)) ; **carte entière validée à 99 %** ([QA](manifests/ar1600-contour-matte-map-user-qa-20260923-v1.json) ; réserve acceptée : liseré cyan-vert résiduel sur l'échelle/cordages fins). Procédé généralisé : [CONTOUR_MATTE_PIPELINE.md](CONTOUR_MATTE_PIPELINE.md). Remplace, sur la même zone, l'[essai Astra](AR1600_CONTOURS_ESSAI_20260923.md)
(jugé insatisfaisant par l'utilisateur). Pas de release.

## Diagnostic (mesures sur la zone bateau)

| Constat | Mesure |
|---|---|
| Frange sombre = noir RGB révélé par l'alpha HD adouci, **hors** masque natif | 0–2 px x4 extérieurs : 83 % RGB ≤ 8 ; 2–4 px : 100 % |
| Pas de liseré sombre peint dans l'objet | bord intérieur natif lum 68 vs cœur 67 |
| Le RGB x4 (SeedVR) dessine des silhouettes nettes, droites, plus fines, **dans** le masque natif | 5 774 px hors natif (tous ≤ 4 px) ; parties fines 6 px x4 vs 8 px natif |
| Liseré clair verdâtre SeedVR au bord de l'objet | objets larges : d1 lum 96 / d2 70 vs cœur 65 ; cordes : 1 px |
| Échec Astra : Potrace du masque x1 sur cordes de 1–4 px x1 → formes « os » ; remplissage intérieur → marbrure | visuel `comparison-detail.png`, `comparison-colour-detail-bc3.png` du run Astra |

## Recette

Producteur : [`pipeline/scripts/build_water_contour_matte_trial.py`](../scripts/build_water_contour_matte_trial.py)
(`prepare`, `encode`). Run : `maps/water-batches/runs/ar1600-contour-matte-trial-20260923-v1/`.

1. Couverture M = RGB x4 non noir (> 20) à ≤ 4 px x4 du bord natif, fermeture 3×3, taches < 12 px ôtées,
   AA gaussien 0,8 / rampe 0,35 ; intérieur natif > 4 px toujours opaque (détails sombres conservés).
2. RGB : liseré clair remplacé par l'intérieur du même objet — 2 px si largeur locale > 8 px x4, 1 px depuis
   l'axe pour cordes 4–8 px, intact en dessous ; couleur prolongée 5 px vers l'extérieur (filtrage sans noir).
3. Art marin secondaire prolongé côté objet ; passes inchangées vs Astra : S = 1−M, P = M/(1−a(1−M)), a = 128.
4. Même zone, même périmètre exact 4 px + rampe 12 px, même BC3 sélectif ; source = pages **pré-Astra**
   (sauvegarde Astra, hashes vérifiés) ; blocs hors sélection identiques au pré-Astra.

Erreur de couverture BC3 au bord : moyenne 0,0016 (Astra 0,0062). Comparatifs 3 colonnes (avant / Astra / candidat) :
`comparison-3-{full,rigging,sail-pier,deck}.png` — simulations, pas des captures.

## Installation, QA, retour arrière

Reçu : [`manifests/ar1600-contour-matte-installed-20260923-v1.json`](manifests/ar1600-contour-matte-installed-20260923-v1.json) ;
8 pages `A1600{37..41,56..58}.PVRZ` ; WED/TIS/overlay 30 FPS/DLL intacts.

QA : `C:MoveToArea("AR1600")`, bateau autour de `(2048,2208)` : cordes/filets (finesse, continuité, halo),
mât/voile/ponton (liseré clair ou sombre), zoom normal/fort, eau animée. Transition vers l'ancien contour en périphérie.

Retour à l'état Astra, jeu fermé : `pipeline/scripts/Restore-AreaOverrideAssets.ps1 -BackupPath
backups/water/ar1600-contour-matte-trial-20260923-v1/override-backup-20260923-204930 -GameRoot <jeu>`.

Limites : cordes < 4 px x4 gardent leur RGB (halo possible) ; un pixel sombre isolé visible dans le gréement ;
compensation de paire toujours non validée ingame ; généralisation map entière non faite.

## Extension à toute la carte (2026-09-23)

Producteur : [`build_water_contour_matte_map.py`](../scripts/build_water_contour_matte_map.py) (`prepare`, `encode`),
mêmes fonctions de recette, sans rampe de transition ; fenêtres 8×8 cellules + halo 1 cellule.
Run : `maps/water-batches/runs/ar1600-contour-matte-map-20260923-v1/`. 421 paires d'eau qualifiées, 0 exclue
(aucune porte, tuile partagée, animée ou paire non complémentaire) ; 804 tuiles, 48 pages ; erreur de couverture BC3 0,0016.
Tuiles intérieures de la zone validée identiques au pixel près à l'essai de zone. Contrôles visuels hors bateau :
`check-{39-42,17-35,16-31,47-46}.png` (simulation).

Reçu : [`manifests/ar1600-contour-matte-map-installed-20260923-v1.json`](manifests/ar1600-contour-matte-map-installed-20260923-v1.json).
Retour à l'état « zone validée », jeu fermé : `Restore-AreaOverrideAssets.ps1 -BackupPath
backups/water/ar1600-contour-matte-map-20260923-v1/override-backup-20260923-205837 -GameRoot <jeu>`.
Hors portée : AR1600N, cellules d'eau sans secondaire (166, eau pure), autres maps.
