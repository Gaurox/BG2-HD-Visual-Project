# Phase 4 — pilote Bodhi Q3m K6 x2

- État : **produit, assemblé isolément, vérifié avec le lecteur/compositeur natif hors jeu**. Pas d'installation, QA ingame ou release ; aucun pointeur actif modifié.
- Cible : `BODHI.CRE`, `0x7F30`, `monster-bg2ee-2.7.3.0`, owner `3` ; `NBOHG1` profil `4`, `NBOHG2` profil `5`, règle `2`.
- Contrat/plan source des phases 1/2 repris ; 270 travaux modèle + deux marqueurs, 1 620 cibles K6 ; guides xBR acquis relus, aucun nouveau xBR. RTX 5090, Torch `2.7.0+cu128`, ReboutCX FP16 x4 fixed86/q32, BOX float32 x2 ; encodeur exhaustif OKLab² f64. Sans B, Q8c ni tramage.
- Rapport final : `verification.json` ; assemblage reproductible : `assemble.py` ; `work/` contient preuves/aperçus locaux ignorés.

## Résultat

| BAM | Profil | Frames / marqueurs | Cycles / slots | Frames F>0 / pixels F>0 | Pixels vérifiés C++ |
|---|---|---|---|---|---|
| `NBOHG1` | `4` | `594 / 450` | `54 / 756` | `144 / 255 846` | `31 001 724` |
| `NBOHG2` | `5` | `648 / 522` | `63 / 1 575` | `126 / 220 962` | `31 018 356` |
| Total | | `1 242 / 972` | `117 / 2 331` | `270 / 476 808` | **`62 020 080`** |

- Source BAM → cache → feuilles V6 : centres/dimensions/transparence, représentants x1, toutes les frames et cycles/slots identiques ; I/F/dep des feuilles identiques aux résultats persistants.
- Catalogue V2 isolé : `sprite/.work/q3m-monster-pilot-x2-pack-20261003-v2/iee-assets/creature-sprites/CreatureSprites-XN.catalog` ; deux composants/shards V6, seul ID `0x7F30` ; SHA `76DBFE68ED99253F05450F0205755BD51D01A08471FBEB1CD7089C97ADE0EFEC`.
- Feuilles inchangées : `sprite/.work/q3m-monster-pilot-x2-leaves-20261003-v1/{NBOHG1,NBOHG2}.registry` ; aucun réencodage pendant l'assemblage du catalogue.
- Oracle scalaire indépendant de `Profile.decode` : six fits, transparence 128/ombre 64, ombre opaque, palette RGB arbitraire avec alpha matière uniforme ; neuf palettes × trois encodages natifs. Tous les slots résolus et centres vérifiés par les bounds d'une composition à un calque. Hors contexte GL/jeu.
- Runtime candidat de phase 3 conservé, SHA `ade49a32a4685e490e773843519fd5f221b79aaffda10cbac02b56d94d4f6759` ; aucune modification de source runtime C++ ; seul son outil de test gagne `--pack`. Nouveau build de test sous `.work/q3m-monster-phase4-20261003-v1/`, sans reconstruire le candidat scellé.

## Correction rencontrée / cache

- L'inspecteur Python `run_creature_sprite_x2.inspect_registry_catalog` conservait une restriction Character pour tout V6. Il valide maintenant chaque couple profil/règle contre owner/ID de **toutes** les appartenances ; Character `1/1/owner1` reste identique, Monster limité aux profils figés. Test ajouté : catalogue Monster + Character accepté, composant partagé avec mauvais ID Monster refusé. Sept tests Monster + onze tests du writer partagé passés ; aucune QA globale répétée.
- Premier assemblage `...pack-20261003-v1` incomplet, conservé hors des preuves finales ; `v2` est le résultat final.
- Namespace initial : `daa7639c9fcc01f85a93029851f1476ff1f4d490591be8394d6034b0ebd80fd3`.
- Namespace courant : `21a989cf5180280bbcc3801296b65e40e2af11f83b63e1a29a3249ecd44bd75c` dans `sprite/.work/q3m-monster-pilot-x2-20261003-v1/x2/`.
- Adoption de 272 résultats **Q3m réels** : recettes complètes identiques sauf SHA de l'inspecteur ; source ancienne épinglée au commit `1e0eda3d`, AST de tout le module hors `inspect_registry_catalog` strictement identique ; guides/I/F/dep validés, ZIP copiés octet pour octet vers le nouveau namespace. Cache original conservé ; aucune nouvelle inférence. Preuve : `pack.json/cache_adoption`.
- Reprise réelle : `272/272` hits, aucun import Torch/processeur, SHA de tous les NPZ inchangés. Le cache courant est réutilisable en phase 5 sans adopter une recette différente par simple ressemblance d'image.

## Aperçus / limites

- Planche représentative : `work/preview-v1/preview.png` + `preview.json` ; trois cycles non nuls par BAM, source NN x2 / guide xBR neutre / Q3m neutre-chaud-froid, centres alignés. Inspection hors jeu : silhouettes, ombres et teintes cohérentes sur ces six échantillons ; **pas d'acceptation QA ni de preuve temporelle/ingame**.
- L'aperçu initial inclus dans le pack n'est qu'un échantillon ; utiliser la planche représentative ci-dessus.
- Les 78 Character, 81 paperdolls, shaders/UI Nearest et configuration BOX monde restent acquis : aucun octet installé, configuration, catalogue actif ou suivi QA/release écrit. Pas d'audit global de ces acquisitions.

## Reproduction / suite

```powershell
$pilotPython = (Get-Content config/workspace-paths.local.json -Raw | ConvertFrom-Json).paths.chainner_python
# Reprise du pilote : cache courant uniquement, 272 hits attendus, sans GPU.
& $pilotPython -B pipeline/scripts/palette_monster.py run --refs NBOHG1 NBOHG2 --cache sprite/.work/q3m-monster-pilot-x2-20261003-v1 --workers 4
# Nouveau catalogue/oracles/aperçu seulement ; ne pas remplacer v2.
& $pilotPython -B docs/measurements/q3m-monster-pilot-x2-20261003-v1/assemble.py --leaves sprite/.work/q3m-monster-pilot-x2-leaves-20261003-v1 --cache sprite/.work/q3m-monster-pilot-x2-20261003-v1 --output <nouvelle-destination>
& ./.work/q3m-monster-phase4-20261003-v1/build/Release/iee_palette_monster_tests.exe --pack sprite/.work/q3m-monster-pilot-x2-pack-20261003-v2/iee-assets/creature-sprites sprite/.work/q3m-monster-pilot-x2-pack-20261003-v2/NBOHG1-oracle.bin
& ./.work/q3m-monster-phase4-20261003-v1/build/Release/iee_palette_monster_tests.exe --pack sprite/.work/q3m-monster-pilot-x2-pack-20261003-v2/iee-assets/creature-sprites sprite/.work/q3m-monster-pilot-x2-pack-20261003-v2/NBOHG2-oracle.bin
# PHASE 5, non exécutée : Bodhi complète, même cache ; 272 hits + 972 nouveaux travaux modèle.
& $pilotPython -B pipeline/scripts/palette_monster.py run --ids 0x7F30 --cache sprite/.work/q3m-monster-pilot-x2-20261003-v1 --workers 4
```

Prochaine unité : Bodhi complète (13 BAM / 8 100 frames), puis MGLC et MBEH ; installation et catalogue conservant les 78 Character appartiennent aux phases 6/7.
