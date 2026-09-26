# Carte — candidat B1.1 + B1.2, 2026-09-27

État : **codé, compilé, tests hôte passés, cache privé préparé ; non installé, non testé ingame**. A1 reste installé. Référence : [plan B1](PLAN_IMPLEMENTATION_PAGES_CARTE_B1_20260927.md).

`E = engine/InfinityEngine-Enhancer/source-patchee` ; `B = E/build-map-prepare-b1-20260927-v1`.

## Périmètre livré

- AR0900 jour uniquement ; identité WED + ensemble d'overlays actifs correspondent au manifeste privé. Autres zones/variantes : natif.
- Anticipation après `refresh_wed_cache`, avant chargement du pack d'animations ; confirmation lors de la publication de vue. Pas de délai de 30 frames ni arrêt au premier dézoom.
- Un worker CPU à priorité basse ; lecture/décompression des **copies privées**, jamais des PVRZ natifs dans `override`.
- 27 pages : 26 pages `A090000..A090025` + eau `YU4T600`, inventoriées depuis les TIS `AR0900`/`YFU4T6` référencés par le WED installé. Entrées alternatives/animation incluses via parcours complet des TIS.
- Ordre déterministe overlay puis première occurrence TIS ; **pas encore de priorité spatiale**.
- 96 emplacements maximum ; admission buffers privés ≤128 MiB, incluant lecture compressée, décodé en cours/prêt/emprunté et marge de travail de 1 MiB. Pas un plafond de mémoire totale du jeu/du pilote/du cache OS.
- Emprunt atomique du buffer prêt ; miss immédiat ; recyclage/destruction sur worker uniquement. Pas de quota quatre pages. Les annulations et les buffers encore empruntés restent comptabilisés jusqu'à destruction.
- Pages déjà résidentes écartées via lecture des 128 entrées du cache natif, une fois par génération sur le rendu ; aucun scan par tuile, aucune écriture du LRU.
- Au callsite zlib déjà manifesté : génération, propriétaire, adresse source, tailles et CRC natif contrôlés ; copie des octets PVR exacts dans l'allocation native. Demand, retours, cache, publication GL et libérations restent natifs.
- Nouvelle option indépendante de PerformanceLogs ; rejet de coexistence avec les anciens prewarm/probe/consume. Diagnostics B2c détaillés non installés par B1 ; logs B1 agrégés sur worker toutes les deux secondes.
- A1 conservé. Aucun changement aux assets installés, shaders, réglages visuels, sauvegardes ou release.

## Adaptations du plan

| Proposition | Implémentation retenue / raison |
|---|---|
| Builder C++ | `E/tools/build_map_page_cache.py` pour inventaire/copie/SHA/manifeste ; validation PVR déléguée à `iee_map_page_shadow_preflight.exe`, donc parseur C++ existant |
| File de jobs/recyclage | Emplacements fixes + états atomiques ; le worker est seul propriétaire des allocations ; le rendu emprunte puis marque Retired |
| Bindings de wrappers conservés | Aucun pointeur natif persisté pour la consommation : CResPVR courant fourni par Demand, resref puis contrat source/CRC dans zlib ; pas de pointeur de wrapper à réutiliser après changement de zone |
| Priorités spatiales | Différées ; premier candidat mesure le taux de préparation utile en ordre déterministe |
| Préchargement GPU B1.3 | Non activé ; aucun Demand spéculatif supplémentaire |

## Sources modifiées

| Fichier sous `E` | Rôle |
|---|---|
| `src/iee/core/map_page_prepare_queue.{h,cpp}` | Admission, générations, emprunts, suppression des préparations devenues inutiles, recyclage |
| `src/iee/map_page_prepare.{h,cpp}` | Index privé borné, lecteur Windows, worker/lifetime, sélection WED, scan de résidence et compteurs |
| `src/iee/hooks.cpp` | Déclencheurs de zone/vue, scope emprunté, substitution zlib existante, installation/arrêt des hooks |
| `src/iee/map_page_prewarm.h` | Pointeur de page empruntée dans le contrat partagé ; ancienne file inchangée |
| `src/iee/core/config.{h,cpp}` | `EnableMapPagePrepare`, `MapPagePrepareCache` ; défaut inactif |
| `CMakeLists.txt` | Nouveaux modules core/runtime |
| `tests/iee_tests.cpp` | Tests concurrence/mémoire/générations/résidence/configuration |
| `tools/build_map_page_cache.py`, `tools/test_build_map_page_cache.py` | Builder override-only et tests du contrat de copie/inventaire |

## Artefacts du candidat

| Artefact | Valeur |
|---|---|
| Dossier prêt pour installateur | `B/install-candidate-v1` : DLL + INI uniquement |
| DLL | 1 934 848 octets ; SHA256 `05F1C2AC1F7811A39795D24A33F6F954D06738DC25B7307BD4DD9A562A97C143` |
| INI | 5 764 octets ; SHA256 `92ADEA786228C2782875CE629DE98BC68F8DE32429D0F7C665FE1940E867F960` |
| Diff INI / installé | Deux ajouts dans `[Rendering]` : activation B1 et chemin absolu vers le cache ci-dessous ; autres valeurs conservées |
| Cache privé | `B/private-cache-ar0900-v1` : 27 fichiers `.b1pvrz`, `manifest.json`, `pages.index` |
| Volume PVRZ privé | 163 143 209 octets ≈155,59 MiB sur disque |
| Volume décodé cumulé | 452 986 236 octets ≈432 MiB ; **pas conservé intégralement en RAM** |
| Intégrité | SHA256 de chaque copie = SHA source enregistré au build ; fichiers indépendants, un lien physique chacun |
| Registre eau | `pipeline/water/requests/wtlake-ar0300n-q070-ar1604-fit1-safe-test-20260926-v1/registry-v3.json` |
| Header eau généré | SHA256 `554B77BF4D5639E81E61D1C36AD470C1128A00C8EED9F74259EB5AE5136DA3F0`, identique A1 |
| Toolchain | MSVC 19.29.30158 / VS16 2019, x64 Release ; dépendances locales de `build-cache128/_deps` |

L'INI pointe vers le cache dans le workspace : garder ce répertoire en place pendant l'essai. L'installateur DLL/INI ne déplace pas ce cache. Le cache n'est ni un payload ni un staging release. Un cache absent/corrompu ne doit pas être reconstruit pendant une frame : repli natif.

## Vérifications exécutées

```powershell
cmake --build engine/InfinityEngine-Enhancer/source-patchee/build-map-prepare-b1-20260927-v1 --config Release --target InfinityEngine-Enhancer iee_tests iee_map_page_shadow_preflight --parallel 4
ctest --test-dir engine/InfinityEngine-Enhancer/source-patchee/build-map-prepare-b1-20260927-v1 -C Release -R '^iee_tests$' --output-on-failure
.tmp/water-python/Scripts/python.exe -m unittest discover -s engine/InfinityEngine-Enhancer/source-patchee/tools -p test_build_map_page_cache.py -v
git diff --check
```

- Compilation finale réussie ; tests natifs agrégés **1/1**, 0,67 s ; builder **5/5** ; diff sans erreur d'espacement.
- Tests B1 : reader retenu → miss sans attendre ; claim conservé lors d'invalidation ; annulation pendant lecture ; admission pleine ; CRC privé incorrect ; pages dupliquées ; six claims successifs ; page résidente ne bloque pas les suivantes ; libération différée et crédit mémoire.
- Tests builder : TIS x4 + overlay + doublons/indices négatifs ; copies indépendantes ; absence de commit d'index si dépendance absente/enveloppe invalide ; refus cache dans override et jeu actif.
- Cache réel : les 27 copies acceptées par le parseur C++ partagé ; hashes recontrôlés après création. Builder exécuté jeu/loader fermés, avec vérification avant chaque copie.
- Warnings observés : fmt C4459 existant, dépréciation CMake de MinHook. Aucune erreur de compilation.
- Les tests hôte **n'exécutent pas le detour dans BG2EE**, ne prouvent pas le gain de FPS ni la qualité visuelle ingame. La lecture Windows privée et l'intégration des hooks restent à éprouver en jeu.

## Installation et essai suivant

- État installé vérifié en fin de préparation : DLL A1 `10FBD4652DC6E6AD8BFA0FE5CB8F4950352970E438BC2FBBC47D554B28BD1FD2`, INI `47979DA9D49EF826014B675D4B0F495842509EED95A6574AFDF71D72B4204B08` ; inchangés.
- Installer le dossier candidat avec `tools/install_renderer_candidate.py`, jeu et InfinityLoader fermés ; conserver le reçu de cette future transaction pour restauration. Aucune installation B1 effectuée dans ce tour.
- Essai : même sauvegarde AR0900 ; ouverture immédiate après chargement, puis ouverture après quelques secondes, puis réouvertures chaudes et retour dans la zone.
- Relever lignes `Map page B1` : generation, prepared/hits/misses/consumed/rejected/failures, reservedBytes/peakBytes, crcMs/copyMs. Compteurs cumulatifs sur la durée du worker, pas remis à zéro à chaque zone ; `renderWorkerWaits=0` décrit l'absence de chemin d'attente dans cette file.
- Corréler aux traces `Map wide-view burst telemetry` et Demand. Des buffers préparés ne prouvent pas qu'ils l'étaient avant leur première demande.

## Limites à conserver lors de l'évaluation

- Les misses restent synchrones dans le moteur. Les hits évitent inflate, mais conservent lecture/allocation natives, CRC, memcpy et upload. Aucun gain chiffré revendiqué avant mesure.
- Une réserve bornée peut être insuffisante pour la rafale immédiate ; l'ordre sans priorité spatiale et le temps disponible avant demande peuvent limiter fortement la couverture.
- Retrait d'une page résidente : si elle est ensuite évincée dans la même génération, B1 laisse son rechargement natif ; pas de réarmement continu.
- Aucun objet GPU/binding natif conservé par B1 ; une recréation de contexte peut provoquer des reloads natifs sans nouvelle anticipation. Aucun résultat graphique validé par cette analyse.
- La vue complète chaude autour de 40 ms/frame demeure un sujet séparé, lot D. B1 ne réduit pas les milliers de demandes/soumissions par image.
