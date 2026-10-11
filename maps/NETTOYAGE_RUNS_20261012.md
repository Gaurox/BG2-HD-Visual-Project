# Maps — anciens runs : nettoyage effectué

Date : 2026-10-12. **Nettoyage exécuté sur demande explicite de l’utilisateur.**

Reçu final : [`cleanup-executed-20261012-v1.json`](cleanup-executed-20261012-v1.json).
Preuves d’exécution versionnées, compressées sans perte :
[`cleanup-evidence-20261012-v1/index.json`](cleanup-evidence-20261012-v1/index.json).
Les SHA256 décompressés correspondent aux preuves locales du reçu ; aucun reçu historique réécrit.
**14 217 médias/binaires retirés des 29 dossiers ; aucun échec.**
822 fichiers conservés vérifiés par SHA256, dont les preuves et les fichiers des 19 cas ambigus.
Travail validé et sources conservés ; aucun fichier release modifié par ce nettoyage.

**Espace libre sur G : +2,980 Go mesurés pendant l’opération.**
4,454 Go de fichiers retirés ; après liens physiques, 3,369 Go de données uniques
et 3,396 Go d’allocation associée. Le delta du volume inclut toute l’activité du disque
pendant cette période ; l’écart n’est pas attribué à une opération précise.

Périmètre : maps, eau, runs d’overlays techniques, essais/archives de maps. Animations, sprites,
sauvegardes générales, builds moteur, payloads/release et sources natives hors proposition.

## Inventaire et proposition conservés pour traçabilité

- 702 dossiers mesurés : **212.813 Go** logiques.
- **29 dossiers d’essais obsolètes**, 14217 fichiers médias/binaires proposés : **4.454 Go** logiques.
- 650 dossiers sélectionnés/acceptés ou dépendances conservés ; 19 dossiers ambigus exclus du lot de suppression.
- **Gain estimé après liens physiques : 3,369 Go** de données uniques ; 1,085 Go restent
  portés par des liens conservés ailleurs. Compression/allocation disque non mesurées.
- JSON, manifestes, décisions, recettes, logs/code et médias identifiés comme preuves conservés.
- Tailles = somme des longueurs de fichiers, Go décimaux ; gain disque réel peut différer selon
  allocation/compression/liens physiques.

Liste approuvée exacte, conservée sans réécriture : [`cleanup-candidates-20261012-v1.json`](cleanup-candidates-20261012-v1.json).

## Lot exécuté — médias d’essais uniquement

| Dossier | Go de fichiers retirés | Go uniques estimés avant suppression | Motif / remplacement retenu |
|---|---:|---:|---|
| `maps/water-batches/runs/voie1-alpha128-x4-20260912-v3` | 1.877 | 0.800 | Uninstalled/unaccepted route1 test batch of September12, superseded by accepted per-map family chains |
| `maps/water-batches/runs/ar5200-water-30fps-20260924-v1` | 0.440 | 0.440 | Unaccepted/superseded trial stage; selected accepted replacement: ar5200-lava-torus-30fps-20260924-v1 |
| `maps/water-batches/runs/ar5000-water-30fps-20260924-v1` | 0.335 | 0.335 | Unaccepted/superseded trial stage; selected accepted replacement: ar5000-water-30fps-20260924-v3 |
| `maps/water-batches/runs/ar5000-water-30fps-20260924-v2` | 0.335 | 0.335 | Unaccepted/superseded trial stage; selected accepted replacement: ar5000-water-30fps-20260924-v3 |
| `maps/water-batches/runs/ar6300-water-30fps-20260925-v2` | 0.218 | 0.218 | Unaccepted/superseded trial stage; selected accepted replacement: ar6300-water-30fps-20260925-v3 |
| `archive/abandoned/gigapixel/AR0500` | 0.170 | 0.170 | Unreferenced experiment/preview directory outside selected runs |
| `maps/water-batches/runs/ar0500n-contour-matte-20260924-v1` | 0.117 | 0.117 | Unaccepted/superseded trial stage; selected accepted replacement: ar0500n-contour-matte-20260925-v1 |
| `maps/water-batches/runs/ar5000-contour-matte-20260924-v2` | 0.101 | 0.101 | Unaccepted/superseded trial stage; selected accepted replacement: ar5000-contour-matte-20260924-v3 |
| `maps/water-batches/runs/ar5000-contour-matte-20260924-v1` | 0.101 | 0.101 | Unaccepted/superseded trial stage; selected accepted replacement: ar5000-contour-matte-20260924-v3 |
| `maps/water-batches/runs/ar0413-water-x4-20260928-v2` | 0.100 | 0.100 | Unaccepted/superseded trial stage; selected accepted replacement: ar0413-water-x4-20260928-v5 |
| `maps/water-batches/runs/ar0413-water-x4-20260928-v1` | 0.099 | 0.099 | Unaccepted/superseded trial stage; selected accepted replacement: ar0413-water-x4-20260928-v5 |
| `maps/AR0410/runs/legacy-upscale-tests-20260818` | 0.083 | 0.083 | Documented unselected historical experiment: ar0410-legacy-upscale-tests |
| `archive/tests-upscale/AR0700` | 0.066 | 0.066 | Unreferenced experiment/preview directory outside selected runs |
| `maps/water-batches/runs/ar3000-water-x4-20260929-v2` | 0.056 | 0.056 | Rejected central RGB harmonisation; validated final recipe retains the unharmonised decor with refined BC3 / q / paired opacity instead |
| `maps/water-batches/runs/ar3000-water-x4-20260929-v3` | 0.055 | 0.055 | Rejected central RGB harmonisation; validated final recipe retains the unharmonised decor with refined BC3 / q / paired opacity instead |
| `maps/water-batches/runs/ar5203-water-x4-20260929-v2` | 0.049 | 0.049 | Rejected central RGB harmonisation; validated final recipe retains the unharmonised decor with refined BC3 / q / paired opacity instead |
| `maps/water-batches/runs/ar5203-water-x4-20260929-v3` | 0.048 | 0.048 | Rejected central RGB harmonisation; validated final recipe retains the unharmonised decor with refined BC3 / q / paired opacity instead |
| `maps/water-batches/runs/ar3000-contour-matte-20260929-v1` | 0.029 | 0.029 | Unaccepted/superseded trial stage; selected accepted replacement: ar3000-contour-matte-20260929-v2 |
| `maps/water-batches/runs/ar0413-contour-matte-20260928-v1` | 0.026 | 0.026 | Unaccepted/superseded trial stage; selected accepted replacement: ar0413-contour-matte-20260928-v3 |
| `maps/water-batches/runs/ar0413-contour-matte-20260928-v2` | 0.023 | 0.023 | Unaccepted/superseded trial stage; selected accepted replacement: ar0413-contour-matte-20260928-v3 |
| `maps/water-batches/runs/ar0404-contour-matte-20260929-v1` | 0.022 | 0.022 | Unaccepted/superseded trial stage; selected accepted replacement: ar0404-contour-matte-20260929-v2 |
| `maps/water-batches/runs/ar6300-contour-matte-20260925-v2` | 0.018 | 0.018 | Unaccepted/superseded trial stage; selected accepted replacement: ar6300-contour-matte-20260925-v1 |
| `maps/water-batches/runs/ar6300-contour-matte-20260925-v3` | 0.018 | 0.018 | Unaccepted/superseded trial stage; selected accepted replacement: ar6300-contour-matte-20260925-v1 |
| `maps/water-batches/runs/ar6300-contour-matte-20260925-v4` | 0.018 | 0.018 | Unaccepted/superseded trial stage; selected accepted replacement: ar6300-contour-matte-20260925-v1 |
| `maps/water-batches/runs/ar6300-contour-matte-20260925-v5` | 0.018 | 0.018 | Unaccepted/superseded trial stage; selected accepted replacement: ar6300-contour-matte-20260925-v1 |
| `maps/water-batches/runs/ar3000-teal-opacity160-20260929-v1` | 0.014 | 0.014 | Obsolete opacity attempt: all binary files are byte-identical to preserved v2; v2 corrects secondary runtime coverage |
| `maps/water-batches/runs/ar0413-water-x4-20260928-v4` | 0.010 | 0.010 | Unaccepted/superseded trial stage; selected accepted replacement: ar0413-water-x4-20260928-v5 |
| `maps/water-batches/runs/voie1-secondary-alpha-seams-x4-20260912-v1` | 0.007 | 0.000 | Uninstalled/unaccepted route1 test batch of September12, superseded by accepted per-map family chains |
| `maps/water-batches/runs/ar1000-wtpool-route1-page-alias-20260912-v2` | 0.001 | 0.001 | Explicitly rejected visual grid; diagnostic JSON and conclusion remain; final WTPOOL family is retained |

## À conserver même si ancien ou peu référencé

- Runs RGB désignés par `areas.csv` et sources des candidats/maps release (lecture uniquement).
- Les 14 contours `*-lake-final-contour-20260926-v1` : acceptation WTLAKE par lot,
  pas d’absence de validation déduite du manque de manifeste individuel.
- AR0413 : spatial v3, bases v5, contour v3, opacité64, timeline et reset explicitement retenus
  dans `ar0413-final-user-qa-20260928-v1.json`.
- AR3000 : opacité160 v2, correctifs runtime/raccords du 11 octobre, sources déclarées par les QA.
- Les répertoires de bases/reset ou réparations sans clôture documentaire précise : exclus du lot.
- `maps/AR1300/...preview` : malgré son nom, source sélectionnée ; conservée.

## Cas exclus / incertitudes

**Décision utilisateur du 2026-10-12 : conserver les 19 dossiers.** Taille totale remesurée :
252 341 371 octets = **252,34 Mo**. Conservation décidée ; aucun nettoyage supplémentaire
en attente sur ces dossiers. Usage/validation de leurs anciens essais restent indéterminés.

| Dossier | Go complets | Pourquoi exclu |
|---|---:|---|
| `maps/water-batches/runs/wtlake-ar0300n-ar1604-qa-repair-20260926-v1` | 0.125 | No direct accepted reference found; use/retirement not established solely by absence of a link |
| `maps/water-batches/runs/ar5203-base-reset-20260929-v1` | 0.034 | No direct accepted reference found; use/retirement not established solely by absence of a link |
| `maps/water-batches/runs/ar1607-base-reset-20260929-v1` | 0.029 | No direct accepted reference found; use/retirement not established solely by absence of a link |
| `maps/water-batches/runs/ar3000-base-reset-20260929-v1` | 0.014 | No direct accepted reference found; use/retirement not established solely by absence of a link |
| `maps/water-batches/runs/ar1604-fit1-no-new-secondary-20260926-v1` | 0.013 | No direct accepted reference found; use/retirement not established solely by absence of a link |
| `maps/water-batches/runs/ar1604-fit1-no-new-secondary-20260926-v2` | 0.012 | No direct accepted reference found; use/retirement not established solely by absence of a link |
| `maps/water-batches/runs/ar1800-base-reset-20260929-v1` | 0.009 | No direct accepted reference found; use/retirement not established solely by absence of a link |
| `maps/AR0900/diagnostics` | 0.004 | No accepted/current root reference, but historical links or ambiguous selection remain |
| `maps/water-batches/runs/ar1003-pool-final-contour-20260925-v1` | 0.003 | No direct accepted reference found; use/retirement not established solely by absence of a link |
| `maps/water-batches/runs/ar0404-base-reset-20260929-v1` | 0.003 | No direct accepted reference found; use/retirement not established solely by absence of a link |
| `maps/water-batches/runs/ar1004-pool-final-contour-20260925-v1` | 0.002 | No direct accepted reference found; use/retirement not established solely by absence of a link |
| `maps/water-batches/runs/ar0703-contour-matte-20260925-spline1` | 0.002 | No accepted/current root reference, but historical links or ambiguous selection remain |
| `maps/water-batches/runs/ar0506-pool-final-contour-20260925-v1` | 0.002 | No direct accepted reference found; use/retirement not established solely by absence of a link |
| `maps/AR1300/cadrages-pont-levis` | 0.001 | No accepted/current root reference, but historical links or ambiguous selection remain |
| `maps/water-batches/runs/ar1000-wtpool-route2-q070-20260912-v4` | 0.000 | No direct accepted reference found; use/retirement not established solely by absence of a link |
| `maps/water-batches/runs/ar1000n-base-reset-20260929-v1` | 0.000 | No direct accepted reference found; use/retirement not established solely by absence of a link |
| `maps/AR0516/test-native-wed-occlusion-20260827-painted-mask-p49` | 0.000 | No accepted/current root reference, but historical links or ambiguous selection remain |
| `maps/water-batches/runs/ar0011-base-reset-20260929-v1` | 0.000 | No direct accepted reference found; use/retirement not established solely by absence of a link |
| `maps/water-batches/runs/ar0500-water-x4-20260924-v1` | 0.000 | No direct accepted reference found; use/retirement not established solely by absence of a link |

## Vérification documentaire réalisée

17272 fichiers texte du dépôt inspectés ; 3679 métadonnées
de dépendances suivies depuis les décisions acceptées. Références : `areas.csv`, QA eau finales,
registre courant, recettes et sources des manifestes release lus sans modification.
Les nombres de versions et les dates ne servent pas seuls de critère. Le nettoyage a conservé
les preuves JSON/logs à leurs chemins d’origine et les 19 cas ambigus. Les binaires des essais
retirés sont volontairement absents ; leurs manifestes historiques ne certifient plus leur
disponibilité physique. Les décisions QA finales restent inchangées. La liste approuvée est
conservée comme historique ; consulter le reçu d’exécution avant toute tentative de reprise.
