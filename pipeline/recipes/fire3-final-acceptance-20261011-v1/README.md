# FIRE_3 — final accepté 2026-10-11

- QA explicite utilisateur : « oui c'est bon je valide tout. MAJ le suivi si necessaire et committe. »
- 10 cartes /34 occurrences ; Apollo8 30 FPS /28 phases distinctes /14⁄15 s.
- Aura : fondu intérieur4px x4 seul, sigma0 ; cœur lumineux, dimensions/centres/cycles natifs conservés.
- Décision : `animations/index/qa-decisions/FIRE_3/2026-10-11-accepted-fire3-fade4-30fps-all-maps-v1.json`.
- Sélection courante : `animations/index/selections/FIRE_3.json` ; réserve temporelle clôturée partout.
- Production : `animations/ressources/FIRE_3/runs/fire3-fade4-30fps-all-maps-accepted-20261011-v1`.
- Pack complet exact : `animations/packs-par-zone/fire3-fade4-30fps-all-maps-accepted-20261011-v1`.
- Acceptation : `acceptance.json` ; fichiers/contrats installés identiques au pack, anciennes QA immuables conservées.
- Installation : recettes `fire3-aura-fade4-30fps-20261011-v1` (AR0202), `fire3-aura-fade4-all-areas-20261011-v1` (9 autres cartes), reçus transactionnels/sauvegardes conservés.
- AM1400A : QA contour actuel acceptée ; FPIT1S : QA acquise reconfirmée ; voir recette `animations-targeted-acceptance-20261011-v1`.
- AM1400N : QA historique conservée ; aucune nouvelle validation nocturne dans cette session.
- Release : aucune mutation ; candidat/package à actualiser pendant finalisation explicitement demandée.
- Reste global : `docs/validation/animations-cleanup-status-20261011-v1.json`.

## Reproduction

```powershell
python pipeline/scripts/run_animation_upscale_30fps_v2.py build --base-runtime-only --base-pack animations/packs-par-zone/soa-ar0202-lot4-accepted-reserve-fire3-animation-20260916/AR0202 --resref FIRE_3 --run fire3-native-anchors-apo8-30fps-20261011-v1 --approve-plan-sha256 54c2d40376d2db756d34fc7cc0fda13568ea08813dd683a0d93ee2138b255759
python pipeline/recipes/fire3-apo8-30fps-20261011-v1/prepare.py
python pipeline/recipes/fire3-aura-preview-20261011-v1/preview.py
python pipeline/recipes/fire3-aura-fade4-30fps-20261011-v1/prepare.py
python pipeline/recipes/fire3-aura-fade4-all-areas-20261011-v1/prepare.py
python pipeline/recipes/fire3-aura-fade4-all-areas-20261011-v1/install.py --verify-only
```

Recettes à sorties neuves uniquement ; ne pas rejouer sur les runs/preuves scellés. Médias générés locaux exclus de Git ; recettes/paramètres/checks/reçus suivis. Aucun réusinage global requis.
