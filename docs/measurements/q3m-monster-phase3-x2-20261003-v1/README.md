# Phase 3 — producteur/cache et lecteur Q3m Monster x2

- État : implémenté, tests CPU/natifs ciblés passés, DLL candidate compilée. **Aucune inférence GPU, production Monster, installation ou QA ingame.**
- Entrées immuables : `../q3m-monster-contract-x2-20261002-v1/{contract,profiles}.json`, `../q3m-monster-work-plan-x2-20261003-v1/{plan.json,processing-plan.sqlite}`. Aucun suivi reconstruit.
- `verification.json` : portée/résultats ciblés et SHA des sources. `runtime.json` : nouveau candidat, hérite des capacités/assets P7 existants ; nouveaux profils testés hors jeu. Aucun pointeur actif modifié.
- Build/fixtures/candidat local : `.work/q3m-monster-phase3-20261003-v1/` (ignoré). Candidat épinglé par SHA ; ne pas le reconstruire après scellement, utiliser une nouvelle destination.

## Implémentation

| Surface | Fichier / décision |
|---|---|
| Contrat fixe | `pipeline/scripts/palette_monster_contract.py` ; profils `2..7`, règle `2`, classes `0/1/2/3..255`, successeurs figés ; 2 024 candidats matière `I/F`, coût OKLab² f64 direct sur six fits, égalité → I puis F ; tables de candidats immuables en mémoire |
| Plan | `palette_monster_work_plan.py` ; SQLite RO épinglé, sélection IDs/refs, identité indexée/RGB/profil vérifiée ; guides relus depuis les V3 acquis avec SHA registre et plane ; aucun nouveau xBR |
| Cache | sous-classe du cache Character pour ZIP borné, verrou OS, écriture atomique ; namespace contrat + code encodeur/producteur/noyaux + backend/modèle/dépendances ; validation exacte guide/I/F/dep ; aucun hit par seule image ; corruptions refusées |
| Producteur | `palette_monster.py` ; `plan` CPU RO, `run` GPU explicite, `pack` feuilles V6 dans nouvelle destination ; modèle chargé seulement aux misses ; six palettes par profil, FP16 x4 fixed86/q32, float32 BOX x2, RGB transparent rempli par opaque proche ; lot borné 64 travaux, encodeur CPU asynchrone |
| Géométrie | fan-out de toutes les frames natives, y compris non référencées ; centres propres à chaque occurrence, représentants offsets x1, ordre/slots/cycles natifs, hash source propre à chaque resref |
| Writer | `palette_registry.py` : paramètres profil/règle par shard et composant, défaut Character inchangé ; refus profil/source/owner/ID/échelle incohérents ; V6 binaire inchangé, I/F u8, F zéro omissible, dep32, raw/XPRESS |
| Tables C++ | `generate_monster_palette_profiles.py` → `core/monster_palette_profiles.h` ; six successeurs/palettes, 39 identités BAM/SHA, trois owners/IDs autorisés ; `--check` sans écriture |
| Runtime | `core/palette_fraction.h`, `creature_sprite_x2.{cpp,h}`, `hooks.cpp` ; dispatch profil, dep et fingerprint, LUT CPU/GL commun ; owner de **toutes** les appartenances du composant vérifié ; palette native type0, 256 entrées, RGB source exact, octets alpha réservés 0/255 ; capture des RGBA réalisés live, alpha primaire, ombre native, paire matière F>0 à alpha inégal → repli natif |

Profils : MBEH G1/G2=`2/3`, NBOH=`4/5`, MGLC=`6/7` ; owner `3`, IDs `0x7F02/0x7F30/0x7F07`, x2 uniquement. Character=`1/1`, owner `1`, x2/x4 acquis. Pas de tramage, B ni Q8c.

Préservation : noyaux/recettes/cache Character inchangés ; catalogue actif des 78 animations, 81 paperdolls, shaders UI Nearest, configuration BOX monde et installation restent ceux acquis. Les signatures, budgets, capture palette et géométrie x1 existants sont conservés. Pas d'extension du catalogue actif avant phase 6.

## Vérification ciblée

- `pipeline/tests/test_palette_monster.py` : six tests ; oracle scalaire exhaustif, encodeur K6 indépendant, spéciaux/alpha/dep, V6/owner/SHA, cache corrompu et reprise all-hit sans processeur, dispatch six fits et BOX float32 via modèle CPU simulé, conservation des frames non référencées/centres/cycles.
- `pipeline/tests/test_palette_registry.py` : 11 tests passés pour l'extension du writer partagé. Pas de QA/recalcul Character global.
- `palette_monster_fixtures.py` + `tests/palette_monster_tests.cpp` : données synthétiques, **pas des assets produits** ; 18 cas acceptés (six profils × raw/compressé/F absent), 10 refusés, 985 608 pixels comparés (neuf palettes × trois encodages natifs), catalogue Character+Monster, alpha primaire Character acquis conservé. Source RGB/type/alpha réservés et paires live invalides refusés.
- MSVC 19.29 / VS2019 / Windows SDK 10.0.19041 / Release : cibles `iee_palette_monster_tests`, `InfinityEngine-Enhancer` compilées ; dépendances source spdlog/zlib/MinHook déjà locales réutilisées. Warnings du tiers fmt C4459 ; aucun échec final.
- Pas de capture réelle du jeu ni de validation visuelle. L'inférence CUDA reste à exercer en phase 4 ; le hook palette modifié est compilé et ses prédicats testés hors jeu.

## Commandes / étape suivante

```powershell
$monsterPython = (Get-Content config/workspace-paths.local.json -Raw | ConvertFrom-Json).paths.chainner_python
# Lecture seule ; commande exercée.
& $monsterPython -B pipeline/scripts/palette_monster.py plan --refs NBOHG1 NBOHG2
# Vérifications ciblées reproductibles, fixtures uniquement.
& $monsterPython -B -m unittest discover -s pipeline/tests -p test_palette_monster.py -v
& $monsterPython -B -m unittest discover -s pipeline/tests -p test_palette_registry.py -v
& $monsterPython -B pipeline/scripts/generate_monster_palette_profiles.py --check
# PHASE 4, non exécuté en phase 3 : lancer le pilote dans un nouveau cache.
& $monsterPython -B pipeline/scripts/palette_monster.py run --refs NBOHG1 NBOHG2 --cache sprite/.work/q3m-monster-pilot-x2-20261003-v1 --workers 4
# Après production complète des 272 travaux, feuilles nouvelles ; pas d'installation.
& $monsterPython -B pipeline/scripts/palette_monster.py pack --refs NBOHG1 NBOHG2 --cache sprite/.work/q3m-monster-pilot-x2-20261003-v1 --output sprite/.work/q3m-monster-pilot-x2-leaves-20261003-v1
```

Pilote phase 4 : `NBOHG1+NBOHG2`, 1 242 frames natives, 117 cycles, 2 331 slots ; 270 travaux modèle + deux marqueurs, 1 620 cibles K6. Produire, assembler isolément et vérifier le pilote avant Bodhi complète → MGLC → MBEH. L'installation finale doit prolonger le catalogue des 78 Character et conserver les paperdolls ; aucun remplacement actif n'est préparé ici.
