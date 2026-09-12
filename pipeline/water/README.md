# Lot eau BG2EE

Autorités de phase 5. Les inventaires et plans générés ne valent ni QA, ni installation, ni release.

AR0900 nuit : [reprise v5](AR0900_NIGHT_REPAIR_20260912.md), validée ingame par l'utilisateur ;
alpha128/raccords appliqués comme au jour et cache moteur corrigé pour le changement de WED nuit.
À chaque prochaine carte jour : traiter aussi sa nuit selon la checklist §0.1 de
[`WATER_REPAIR_RUNBOOK.md`](../WATER_REPAIR_RUNBOOK.md) ; critères et preuves distincts par variante.

Guide de reprise LLM : [recettes eau validées](VALIDATED_WATER_RECIPES.md). Il consolide les
paramètres courants, les cas probants, les limites de généralisation et les échecs observés.
AR0300N v10 : reflets nuit validés, opacité160 appariée centres/secondaires ; RGB nocturne conservé.
Sélection : `manifests/ar0300n-reflections-alpha160-validated-20260912-v10.json`.
Exception artistique locale : conserver pages + DLL correspondante ; aucun défaut160 global.
Le défaut de teinte PVRZ brune intermittente est corrigé universellement dans le runtime, pas dans
les assets par carte : invariant et diagnostic dans `WATER_REPAIR_RUNBOOK.md` §0.2 ; QA AR0046N
dans `manifests/ar0046n-water-tint-validated-20260912-v7.json`.

Suivi vers release : [contrat opérationnel](WATER_RELEASE_TRACKING.md) et
`release-tracking-v1.json`. Audit strictement en lecture seule :
`python -B pipeline/scripts/audit_water_release_tracking.py`.
État courant :11identités `validated-ingame`,1fallback validé,4`pending-ingame`,1variante
historique non résolue et2familles intérieures bloquées, soit19identités. La matrice nominative est dans
`WATER_RELEASE_TRACKING.md` ; l'autorité machine reste le JSON.

AR1000 jour / WTPOOL : v1 rejetée sur crash de nom de page ; v2 charge mais rejetée pour
quadrillage, SeedVR x4 ayant amplifié la trame diagonale source. V3 installée sans IA : bilinéaire
x4 périodique3×3, interpolation cyclique linéaire36phases/15Hz ; énergie du motif réduite12,04×.
Verdict q0 : aucun quadrillage, eau jugée figée. Voie2 v5 exacte installée : blend30FPS,
matériau1, q0.70 ; validée ingame le2026-09-12. `AR1000N` est exclu.

Reprise AR0204/AR1600 : [correctif installé et QA](AR0204_AR1600_REPAIR_20260912.md).
Sélection installée courante :
`manifests/ar0204-ar1600-validated-installed-20260912-v1.json` ; raccords RGB/WED corrigés,
AR0204/AR1600/AR0900 validés0.70, interpolation30FPS conservée.

Pilote égouts : [WTSEW AR0404/AR2100](WTSEW_AR0404_PILOT_20260912.md), validé ingame.
AR0404 utilise la chaîne complète à `q=0.70` ; AR2100 est validée dans son état exact actuel
(WED stock, overlay WTSEW partagé, route2 absente donc `q=0`).

Pilote marais : [WTSWAM AR1607/AR1800](WTSWAM_AR1607_AR1800_PILOT_20260912.md), première QA
rejetée (tuilage, transparence, mouvement). Correctif v2 installé : alpha natif100 AR1607,
raccords RGB des deux cartes, matériau marais plus contrasté, diagnostics par WED ; `q=0.70`.
V2/v3 rejetées sous pluie : variante `WTSWAMR` omise (palette6frames face au WED36frames).
[Reprise ressource pluie v4](WTSWAM_RAIN_RESOURCE_REPAIR_20260912.md) : paire sec/pluie
isolée `WSWPIL`/`WSWPILR`, x4/36phases et route2 q0.70 ; état installé validé par l'utilisateur.
Toute autre identité WTSWAM reste absente du registre et tombe à `q=0`.

| Fichier | Rôle |
|---|---|
| `family-policy-v1.json` | Familles, méthode SeedVR et gates voie1/route2 |
| `release-tracking-v1.json` | Sélection eau courante, preuves hashées, QA et bloqueurs release |
| `release-tracking-v1.schema.json` | Schéma du suivi eau ; aucune autorisation release |
| `route2-registry-v1.json` | Entrées route2 approuvées ; absence/divergence = `q=0` |
| `../../engine/InfinityEngine-Enhancer/source-patchee/assets/water-route2/registry-v2.json` | Extension append-only consommée par le moteur |
| `manifests/wtlake-timeline30-q070-20260912-v1.json` | Lot WTLAKE 14 identités, 36 phases/15 Hz, blend 30 FPS, route2 `q=0.70` |
| `manifests/wtsew-ar0404-pilot-installed-20260912-v1.json` | Pilote WTSEW AR0404 installé, reçus assets/shaders/renderer, QA en attente |
| `manifests/wtsew-ar0404-ar2100-validated-20260912-v1.json` | Décision QA ingame : AR0404 full route2 validée, AR2100 fallback courant validé |
| `manifests/wtswam-ar1607-ar1800-pilot-installed-20260912-v1.json` | Installation initiale historique, rejetée par la QA suivante |
| `manifests/wtswam-ar1607-ar1800-rejected-20260912-v1.json` | Décision utilisateur et captures du rejet |
| `manifests/wtswam-ar1607-ar1800-repair-installed-20260912-v2.json` | Assets correctifs conservés ; renderer remplacé par v3 météo |
| `manifests/wtswam-weather-installed-20260912-v3.json` | Historique fpTone, rejeté en QA |
| `manifests/wtswam-rain-installed-20260912-v4.json` | Installation v4 : assets sec/pluie isolés, registre19, reçus immuables |
| `manifests/wtswam-ar1607-ar1800-validated-20260912-v1.json` | Sélection QA courante : les deux cartes v4 validées à q0.70 |
| `manifests/ar1000-wtpool-route1-candidate-20260912-v1.json` | AR1000 jour : candidat WTPOOL1 périodique 36phases q0 |
| `manifests/ar1000-wtpool-route1-load-crash-rejected-20260912-v1.json` | AR1000 jour v1 : rejet sur crash de chargement, cause page PVRZ mal nommée |
| `manifests/ar1000-wtpool-route1-grid-rejected-20260912-v2.json` | AR1000 jour v2 : rejet visuel du quadrillage SeedVR x4 |
| `manifests/ar1000-wtpool-periodic-bilinear-candidate-20260912-v3.json` | AR1000 jour v3 : candidat non génératif périodique |
| `manifests/ar1000-wtpool-periodic-bilinear-installed-20260912-v3.json` | AR1000 jour v3 : installation vérifiée, QA ingame en attente |
| `manifests/ar1000-wtpool-periodic-bilinear-static-rejected-20260912-v3.json` | AR1000 jour v3 : apparence q0 propre, mouvement rejeté comme figé |
| `manifests/ar1000-wtpool-route2-installed-20260912-v5.json` | AR1000 jour v5 : voie2 exacte q0.70/blend30FPS installée, QA en attente |
| `manifests/ar1000-wtpool-route2-validated-20260912-v5.json` | AR1000 jour v5 : décision QA ingame validée |
| `../scripts/build_ar1000_wtpool_route2_candidate.py` | Produit le registre exact AR1000 jour ; plan-only par défaut, `--run` explicite |
| `../scripts/orchestrate_water_batch.py` | Plan déterministe ; `--run` seul autorise l'exécution d'une étape supportée |
| `../scripts/build_wtlake_timeline_batch.py` | Assemble le candidat WTLAKE ; aucun SeedVR/build moteur/install/release implicite |
| `../scripts/build_wtsew_route2_pilot.py` | Produit le pilote AR0404 ; plan-only par défaut, exécution avec `--run` |
| `../scripts/build_wtswam_route2_pilot.py` | Produit le pilote AR1607/AR1800 ; plan-only par défaut, exécution avec `--run` |
| `../scripts/repair_wtswam_pilot.py` | Reprise du pilote rejeté depuis identités exactes ; nouveau run, plan-only sans `--run` |

Contrats :

- nouvelle inférence SeedVR du lot : `color_correction_method=none` ;
- artefacts témoins inchangés : AR0900 jour LAB, WTLAKE périodique wavelet ;
- voie 1 par lot : `route1-policy-v1.json` et `../scripts/build_water_route1_batch.py` ;
- raccords alpha secondaires confirmés : `../scripts/repair_water_secondary_alpha_seams.py` ;
- lots QA hors ligne : `../scripts/assemble_water_qa_batches.py` et `manifests/qa-batches-20260912-v1.json` ;
- voie1 avant route2 ;
- registre route2 exact, versionné, fail-closed ;
- le build moteur génère une table C++ depuis v2 et vérifie au démarrage les hashes TIS/PVRZ live ;
- aucune installation, reconstruction moteur, QA ou release dans l'orchestrateur de phase 5.
- le registre v3 WTLAKE expérimental est complet, exact et fail-closed ; AR0900 garde son ID parent.

Lot WTLAKE, plan puis assemblage explicite :

```powershell
python -B pipeline/scripts/build_wtlake_timeline_batch.py --output maps/water-batches/runs/<run-id>
python -B pipeline/scripts/build_wtlake_timeline_batch.py --output maps/water-batches/runs/<run-id> --run
```

Pilote WTSEW, plan puis production explicite dans un nouveau run :

```powershell
python -B pipeline/scripts/build_wtsew_route2_pilot.py --output maps/technical-overlays/WTSEW/runs/<run-id>
python -B pipeline/scripts/build_wtsew_route2_pilot.py --output maps/technical-overlays/WTSEW/runs/<run-id> --run
```

Pilote WTSWAM, plan puis production explicite dans un nouveau run :

```powershell
python -B pipeline/scripts/build_wtswam_route2_pilot.py --output maps/technical-overlays/WTSWAM/runs/<run-id>
python -B pipeline/scripts/build_wtswam_route2_pilot.py --output maps/technical-overlays/WTSWAM/runs/<run-id> --run
```

Plan complet en lecture seule :

```powershell
python -B pipeline/scripts/orchestrate_water_batch.py
```

Exécution future d'une étape supportée, après accord explicite :

```powershell
python -B pipeline/scripts/orchestrate_water_batch.py --stage preflight --run --run-id <nouveau-id>
```

`--run-id` doit être neuf. Un dossier existant est toujours refusé.
