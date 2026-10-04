# Ankheg SDF x2 : attente des métadonnées HD

- Demande : installer le correctif proposé après analyse des retours temporaires vanilla x1.
- Analyse/proposition : `../q3m-ankheg-sdf-stability-analysis-20261004-v1/{README.md,proposed-fix.patch}`.
- Code : `engine/InfinityEngine-Enhancer/source-patchee/src/iee/{creature_sprite_x2.h,creature_sprite_x2.cpp,hooks.cpp}`.
- Périmètre : catalogue V2 authentifié, animation `0x3000`, owner `9`, 12 ressources corps/terre, tous cycles/directions. Le lecteur commun demande `WaitForAnkhegMetadata`; worker existant, attente conditionnelle ≤5 s, payloads paresseux, quarantaine/fallback natif conservés sur erreur.
- Première utilisation : courte attente possible; test à froid : 12/12 résolutions immédiates HD, 0 miss; attente maximale mesurée 69,013 ms, somme 325,638 ms. Valeurs de cette machine, pas garantie de cadence ingame.
- Généralisation : personnages jouables owner `1` conservent `WaitForCharacterMetadata`; autres familles monstre/PNJ conservent `NonBlocking`. Appliquer un contour SDF ne suffit pas à activer cette politique. Étendre ensuite par contrat de famille validé.
- Production inchangée : `../q3m-ankheg-sdf-ingame-x2-20261004-v1/{production.json,current-generation.json}`; V9, couleurs Q3m K6, 516 frames. Aucun nouveau traitement neural/encodage/masque.
- Runtime : `runtime.json` décrit uniquement le delta; capacités/shaders hérités du runtime SDF précédent. `current-generation.json` référence la même génération d'assets et la nouvelle DLL.
- Installation : `install.ps1`, jeu/InfinityLoader fermés; seule `InfinityEngine-Enhancer.dll` remplacée; sauvegarde locale `work/before/`; catalogue, INI, exécutable, shaders, 81 packs UI et 12 feuilles Ankheg vérifiés à l'identique (`baseline.json`, 99 fichiers).
- Preuves : `verification.json` : build Release natif, suite core, 12 chargements à froid liés aux vrais objets compilés, 516 frames × K6 ×3 formats palette, 1485 slots, 241492248 pixels décodés, 48 compositions corps/terre. Contrat GPU/shaders inchangé : preuve GPU SDF précédente réutilisée.
- QA finale : acceptée par l'utilisateur le 2026-10-04, « validé, committe ». Décision immuable : `sprite/index/qa-decisions/monster_ankheg/2026-10-04-accepted-full-ankheg-q3m-v9-sdf-stable-x2-catmullrom-v1.json`; 12 ressources/516 frames, DLL/shaders/SDF/attente identifiés. Les preuves de génération/installation conservent leur état au moment de leur capture. Release inchangée.
- Test : `C:CreateCreature("ANKHEG01")`; vérifier apparition, marche, attaques, enfouissement/sortie et changements de direction depuis une nouvelle session.
- Retour : `restore.ps1` rétablit uniquement l'ancienne DLL SDF. Pour retirer ensuite le SDF, exécuter le restore de l'essai SDF précédent; ordre nécessaire pour les gardes SHA.

```powershell
$stablePython=(Get-Content config/workspace-paths.local.json -Raw|ConvertFrom-Json).paths.chainner_python
# Nouveau run déjà scellé : ne pas rejouer seal.py ni écraser les preuves.
# Compilation utilisée : VS2019 x64, BUILD_TESTING=ON, IEE_BUILD_WINDOWS_DLL=ON,
# dépendances FetchContent locales build-vs2019-30fps-multicycle/_deps/{minhook,spdlog,zlib}-src.
& 'C:/Program Files/CMake/bin/cmake.exe' --build engine/InfinityEngine-Enhancer/source-patchee/build-q3m-sdf-stable-20261004-v1 --config Release --target InfinityEngine-Enhancer iee_palette_partner_tests iee_tests --parallel 6
# seal.py baseline -> native -> install.ps1 -> seal.py track (preuves immuables).
```
