# Traiter une map d'eau — runbook agent

Point d'entrée unique pour appliquer le travail eau validé à **une** map (une WED : jour et nuit sont deux
maps). Suivre l'ordre ; chaque `STOP` = s'arrêter et demander à l'utilisateur, sans contourner.
Recettes et raisons : [SPATIAL_X4_PIPELINE.md](SPATIAL_X4_PIPELINE.md), [TEMPORAL_30FPS_PIPELINE.md](TEMPORAL_30FPS_PIPELINE.md),
[CONTOUR_MATTE_PIPELINE.md](CONTOUR_MATTE_PIPELINE.md). État de chaque map : `plan_water_map.py inventory`. Référence validée : AR1600 (2026-09-23).
Suivi courant A/B/C et QA : [`manifests/water-standard-map-status-20260923-v1.json`](manifests/water-standard-map-status-20260923-v1.json).

## Règles fixes

- Une map par tâche ; ne toucher aucune autre map, variante jour/nuit ou famille.
- Jeu **et** InfinityLoader fermés avant toute installation (les scripts refusent sinon).
- Jamais : release (payload, staging, `content.json`, TP2, archive), `maps/*/runs` ou `backups/` dans Git,
  réécriture d'un run ou d'un reçu existant (nouveau dossier `-vN` à chaque essai).
- QA : l'agent ne lance pas le jeu et ne déduit jamais une validation ; il donne la commande
  `C:MoveToArea("ARxxxx")` et enregistre seulement la réponse de l'utilisateur.
- Commit : seulement sur demande. Committer scripts, docs, `pipeline/water/manifests/`, `pipeline/water/requests/`,
  `route2-registry-current.json` ; jamais `animations/` ni changements hors eau non liés.
- Python : `python` (3.11, Pillow ≥ 12, NumPy, SciPy). Chemins locaux via `config://` (`workspace_paths.py`).

## 0. Qualifier la map (lecture seule)

```powershell
git status --short                                   # préserver les changements hors périmètre
$v = 'G:/AI/BG2_Vanilla_23534562'; $run = 'maps/water-batches/runs/<map>-water-x4-<date>-v1'
python -B pipeline/scripts/plan_water_map.py plan --area ARxxxx --vanilla-root $v --output $run
python -B pipeline/scripts/build_water_contour_matte.py survey --area ARxxxx --vanilla-root $v
```

`plan` : famille(s), alias, plans de toutes les étapes ; **STOP** si `stops` non vide (traitement antérieur,
overlay inconnu, master secondaire ambigu, base absente). `decisions_owed` : ce qui reste à trancher (30 FPS bloqué,
pas de pluie). `survey` : `a` (WATER_ALPHA), paires, refus pour l'étape C.
Les trois étapes sont indépendantes ; faire celles qui s'appliquent, **dans l'ordre A → B → C**.

Références : AR1600 valide la recette lac ; AR2100 valide `sewage` A → B, avec C historiquement accepté
avec réserve et désormais provisoire. Contrat dans `liquid-family-standard-v1.json` : SeedVR x4, matériau 4,
cycle 2,4 s / 72 phases. Les garde-fous de review restent applicables.
AR0408 valide `pool` A → B ; AR0703 valide A → B et fournit la QA historique C : bilinéaire x4, matériau 1,
cycle figé 2,4 s / 72 phases, **force route2 0,70 sur le groupe sec** (la timeline seule paraît figée), pluie q0,
contours C provisoires `rgb-x4-silhouette-matte` (10 paires, alpha 128).
AR0500 jour et AR0500N nuit valident `swamp` A → B : SeedVR 7B x4, matériau 5, cycle 2,4 s / 72 phases,
force route2 0,70 sur les groupes sec et pluie ; QA sèche validée, pluie non observée. C reste applicable mais
provisoire : continuer en l'état, puis reconstruire/réinstaller toutes les maps après validation de sa refonte.
AR5200 valide `lava` B → C (2026-09-24) : A seulement **construit** (contextes x1 + topologie, non installé ;
sa WED bilinéaire est remplacée par B), B `seedvr-torus` 12 clés / 216 phases / 7,2 s, q0 matériau 1,
C provisoire validé avec les mêmes réserves que les autres familles.
AR0503 valide `oil` A → B → C (2026-09-24) : A SeedVR x4 (master secondaire d'un run direct), B `seedvr-torus`
1×1 + harmoniques ≤ 9 + égalisation (la v1 sans filtres « grouillait »), C provisoire avec réserve.
AR5000 valide `brown_flow` A → B → C (2026-09-25) : A avec interfaces par famille (240), B `seedvr-torus` 2×2
128 phases/4,27 s + décrêtage x1, C `central_water` ; v1/v2 montraient des lignes aux bords de cellules.
AR6300 valide `lake_teal` B → C (2026-09-25) : A construit seulement (aucune cellule d'eau pure), B `seedvr-torus`
sans décrêtage (il créait une grille), C gaussien à alpha 160 ; essais spline des contours non retenus.

| Étape | S'applique si | Sinon |
|---|---|---|
| A. Eau x4 spatiale (overlay alias + bases) | `plan` sans `stops` | STOP (voir `plan-report.json`) |
| B. Eau 30 FPS réels | A installé et validé ; famille présente dans `temporal-plan.json` | famille bloquée : STOP, décision utilisateur |
| C. Contours devant l'eau | `survey` → `"ready": true` | voir STOP ci-dessous |

C ne dépend ni de A ni de B : C seul reste possible (y compris sur une map « décision utilisateur »).
Ordre : C modifie les pages de base ; faire ou refaire A (bases) après C écraserait C → restaurer C d'abord.

## A. Eau x4 spatiale

Détails : [SPATIAL_X4_PIPELINE.md](SPATIAL_X4_PIPELINE.md). ComfyUI lancé si une famille est `seedvr`.

```powershell
python -B pipeline/scripts/build_water_map_x4.py --run $run --stage all
& pipeline/scripts/Install-AreaOverrideAssets.ps1 -SourceRoot $run/override-candidate -BackupRoot backups/water/<run>
python -B pipeline/scripts/build_water_map_x4.py --run $run --stage verify-installed
python pipeline/scripts/record_water_decision.py install --area ARxxxx --kind spatial --run $run --override-backup backups/water/<run>/<override-backup-stamp>
```

Puis QA (section D). Les 8 témoins du lot `liquid-families-x4-20260923-v1` sont déjà faits (alias `Q9*`).

## B. Eau 30 FPS réels

Pré-requis : étape A installée et validée ; ComfyUI lancé (`config://comfyui_url`, file vide) si `seedvr`.

1. Plan : `$run/temporal-plan.json` écrit par `plan_water_map.py` (alias `YF…` standard, matériau de la famille,
   `base_registry` = registre de la DLL installée via [`route2-registry-current.json`](route2-registry-current.json)).
   Témoins du lot 2026-09-23 : plan à écrire à la main (modèle dans TEMPORAL_30FPS_PIPELINE.md).
2. `prepare` (`--plan $run/temporal-plan.json`), `interpolate`, `upscale`, `build`, `review` de `build_liquid_temporal_30fps.py`, run
   `maps/water-batches/runs/<map>-water-30fps-<date>-v1`. Critères post-BC3 (`build.json`) :
   netteté max/min ≤ 1,25, pas max/médian ≤ 1,4 ; sinon montrer `review-30fps.mp4` et demander.
3. Copier `<run>/registry-v3.json` et `<run>/plan.json` sous `pipeline/water/requests/<run>/`.
4. DLL : commande CMake complète dans TEMPORAL_30FPS_PIPELINE.md, avec
   `-DIEE_WATER_ROUTE2_REGISTRY=<repo>/pipeline/water/requests/<run>/registry-v3.json` ; `ctest` doit passer.
5. Installation, jeu fermé :

```powershell
& pipeline/scripts/Install-AreaOverrideAssets.ps1 -SourceRoot <run>/candidate -BackupRoot backups/water/<run>/override
pwsh pipeline/scripts/Install-WaterRuntime.ps1 -Dll <build>/Release/InfinityEngine-Enhancer.dll `
     -Registry pipeline/water/requests/<run>/registry-v3.json -Label <run>
python pipeline/scripts/record_water_decision.py install --area ARxxxx --kind temporal-30fps --run <run> `
     --override-backup backups/water/<run>/override/<override-backup-stamp> `
     --runtime-receipt backups/water/<run>/runtime/install-backup.json
```

**STOP** si : `prepare` exige `cycle_seconds` (pavages A–D : vitesse WED ambiguë) ; phases > 225 ;
groupe à alpha variable ou lookups différents ; DLL live ≠ pointeur (`Install-WaterRuntime.ps1` refuse) ;
`seedvr-torus` refusé (adjacences WED hors tore du layout : autre lave que AR5200 à vérifier une par une).
Lave : pas d'étape A installée ; B prend `source_wed`/`selection` du run A construit (plan AR5200 :
`pipeline/water/requests/ar5200-lava-torus-30fps-20260924-v1/temporal-plan.json`). Pluie à clés identiques :
le producteur réutilise la sortie SeedVR du groupe sec.

## C. Contours devant l'eau

```powershell
python -B pipeline/scripts/build_water_contour_matte.py prepare --area ARxxxx --vanilla-root $v --output maps/water-batches/runs/<map>-contour-matte-<date>-v1   # spline fit 1 + central_water par défaut ; exceptions par map dans le standard
python -B pipeline/scripts/build_water_contour_matte.py encode  --area ARxxxx --vanilla-root $v --output <même run>
& pipeline/scripts/Install-AreaOverrideAssets.ps1 -SourceRoot <run>/override-candidate -BackupRoot backups/water/<run>
python pipeline/scripts/record_water_decision.py install --area ARxxxx --kind contour --run <run> `
     --override-backup backups/water/<run>/<override-backup-stamp>
```

**STOP** si `survey` n'est pas prêt : base déjà traitée (relance uniquement avec `--source-backup` des pages non
traitées, voir CONTOUR_MATTE_PIPELINE.md), pages non BC3, atlas non standard. **Signaler** dans la demande de QA :
`a` ≠ 128 (AR1607 = 100, AR6300 = 160, composition non encore vue en jeu), huile (contrat alpha0 historique),
cellules ignorées nombreuses.

## D. Demande de QA et enregistrement

Donner à l'utilisateur : ce qui a changé, `C:MoveToArea("ARxxxx")`, quoi regarder (B : fluidité, pop toutes
les 0,4 s, raccord de boucle, pluie ; C : cordes/gréement, frange sombre, liseré clair), le chemin du rollback.
Après sa réponse, et seulement alors :

```powershell
python pipeline/scripts/record_water_decision.py qa --area ARxxxx --kind contour `
     --selection pipeline/water/manifests/<reçu installed>.json --result validated --quote "<message exact>"
```

`--result validated-with-reserve --reserve "<réserve>"` ou `rejected` selon la réponse. Mettre à jour la ligne
de la map dans le tableau d'état de TEMPORAL_30FPS_PIPELINE.md / CONTOUR_MATTE_PIPELINE.md.
Refaire les bases A alors que C est installé (cas AR5000) : reconstituer les pages d'avant A (sauvegarde A,
sinon sauvegarde C, sinon live ; vérifier l'égalité au build x4 de la carte) dans une racine de jeu temporaire,
lancer `build_liquid_base_x4_trial.py --game-root <racine temporaire> --plan <run A>/request.json --run` vers un
nouveau run, installer ses pages, puis reconstruire C depuis le live. Le reçu `install` de ces bases est refusé une
fois C installé (pages remplacées) : consigner le run et la sauvegarde dans la note du reçu C.
QA de A enregistrée après B (B réécrit la WED) : ajouter `--superseded-by <reçu installed de B>` ; après B **et** C
(pages de base réécrites), répéter l'option : `--superseded-by <B> --superseded-by <C>` (AR0503).

## Retour arrière (jeu fermé)

```powershell
& pipeline/scripts/Restore-AreaOverrideAssets.ps1 -BackupPath <dossier override-backup-*>   # depuis la racine du dépôt
pwsh pipeline/scripts/Install-WaterRuntime.ps1 -Restore -Receipt backups/water/<run>/runtime/install-backup.json
```

Restaurer dans l'ordre inverse de l'installation ; le restore DLL remet aussi le pointeur de registre.
