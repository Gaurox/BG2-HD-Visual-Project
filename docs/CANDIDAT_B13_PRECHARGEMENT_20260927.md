# B1.3 — préchargement natif progressif des pages préparées

- Base committée : `603340c1` — B1 + analyse comparative A1/B1.
- État : code B1.3 local, DLL Release compilée, tests passants ; **non installé, non validé ingame**.
- Référence : `docs/COMPARAISON_B1_A1_20260927.md`. B1 retenait sept grandes pages prêtes sous 128 MiB ; huit substitutions utiles pendant la rafale, encore 504 ms de Demand cumulé.
- But : matérialiser progressivement les pages prêtes avant l'ouverture de carte ; libérer leurs buffers privés pour que le worker prépare les suivantes. Aucune réduction de résolution, filtrage, animations ou effets.

## Contrat implémenté

| Point | Comportement |
|---|---|
| Activation | `EnableMapPagePrepare=true` + nouveau `EnableMapPagePreload=true` ; B1.3 désactivé par défaut |
| Périmètre | AR0900 sec, overlays du cache B1 ; autres zones et pluie exclues |
| Références | Nouveau `MapPagePreloadBindings` : 27 couples page/TIS/première tuile, extraits du manifeste B1 existant ; aucune copie supplémentaire des 155,59 MiB privés |
| Résolution runtime | Relecture WED actif, TIS chargé, entrée de tuile, wrapper, nom PVR avant chaque appel ; aucun pointeur de tuile persistant |
| Thread | Après présentation, contexte GL courant ; aucun préchargement pendant `LoadArea`, y compris une présentation réentrante du chargement |
| Admission | Au plus un Demand natif par présentation ; page CPU effectivement réservée prête ; intervalle précédent connu et ≤35,33 ms ; durée de préparation de l'appel + estimation ≤8 ms |
| Cadence | L'intervalle de présentation comprend le limiteur 30 FPS : seuil de cadence, **pas mesure de marge CPU disponible**. Mesuré aussi lorsque les logs performance sont désactivés |
| Coût | Estimation initiale 6 ms, ajustée au coût observé ; arrêt de ce plan si durée totale >8 ms ou contrôle après appel invalide |
| Mémoire | Plafond privé B1 inchangé : 128 MiB avec entrée compressée/sortie/scratch ; allocations et destructions de payload uniquement sur worker |
| Cache natif | Refus à ≥96 entrées occupées sur 128 ; après appel, vérifier conservation de toutes les entrées présentes avant (ordre LRU libre) |
| GL | Capture/restauration unité active, texture 2D de l'unité zéro, paramètres d'unpack ; refus si PBO d'unpack actif |
| Substitution | Même contrôle CRC/contenu/génération que B1 ; moteur propriétaire de sa lecture, allocation, texture, upload et libération |
| Réservation | Miss spéculatif sans annulation du worker ; `defer()` rend la page disponible ; réservation consommée rend le buffer au worker ; invalidation de génération conservée |
| Repli | Absence de page prête → aucun Demand spéculatif ; échec pendant Demand → chemin natif B1 puis arrêt des tentatives B1.3 pour ce plan |

**Limites explicites :** Demand reste monolithique/non préemptible et relit la ressource native. Le seuil de 8 ms ne peut empêcher le premier dépassement ; il empêche sa répétition dans ce plan. Une estimation ultérieure trop coûteuse peut également différer les appels restants. Aucun gain garanti si ouverture immédiate, wrapper indisponible, cadence lente ou arrêt au premier appel. Résidence GPU avancée dans le temps, pas diminution démontrée de la VRAM. Pas de priorité spatiale ni correction des réactivations du même WED dans ce candidat.

## Fichiers

Préfixe `E = engine/InfinityEngine-Enhancer/source-patchee/`.

- `E/src/iee/map_page_preload.{h,cpp}` : revalidation runtime, pompe post-présentation, état GL, diagnostics.
- `E/src/iee/core/map_page_preload_policy.{h,cpp}` : métadonnées, admission, contrôle d'éviction.
- `E/src/iee/core/map_page_prepare_queue.{h,cpp}`, `E/src/iee/map_page_prepare.{h,cpp}` : réservation spéculative des buffers existants.
- `E/src/iee/hooks.cpp`, `E/src/iee/frame_hook.cpp`, `E/src/iee/core/config.{h,cpp}` : raccordement, garde LoadArea, configuration.
- `E/tools/write_map_page_preload_bindings.py` : sortie exclusive nouvelle ; contrôle manifeste/index et identité TIS/page.

## Candidat et dépendances immuables

Préfixe `B = E/build-map-preload-b13-20260927-v1/`.

| Fichier | Octets | SHA-256 |
|---|---:|---|
| `B/install-candidate-v1/InfinityEngine-Enhancer.dll` | 1954304 | `C8EAC3B0E6C8EBA27BBABC0B67C7061B745EB998EC6D8A9CB128E2CC951B7ECE` |
| `B/install-candidate-v1/InfinityEngine-Enhancer.ini` | 5950 | `0A56C32AADCEAAEDBD9CD52A85A6A3ADDC030C745547333C1423DBBD1C5D2A89` |
| `B/preload-bindings-ar0900-v1.index` | 766 | `DDCE805B631E31DB1BB708E75973BF7F35113851ECD6D71EF710F2D52F75AA27` |

- INI : exactement deux nouvelles clés par comparaison sémantique avec B1 ; toutes les autres valeurs identiques.
- Cache privé réutilisé : `E/build-map-prepare-b1-20260927-v1/private-cache-ar0900-v1/`. Chemins absolus de cache et de bindings dans l'INI : **conserver les deux builds** pendant les essais.
- Registre eau de compilation : `pipeline/water/requests/wtlake-ar0300n-q070-ar1604-fit1-safe-test-20260926-v1/registry-v3.json`.
- Header généré eau identique à B1 : SHA-256 `554B77BF4D5639E81E61D1C36AD470C1128A00C8EED9F74259EB5AE5136DA3F0`.
- Installation active attendue : B1, reçu `backups/renderer/20260926T230906729301Z-eeee7a15/renderer-install-receipt.json`. Aucun fichier de jeu remplacé pendant ce travail ; aucun payload/release modifié.

## Vérification exécutée

- MSVC 19.29 / VS2019 x64, Release : DLL + `iee_tests`, succès. Dépendances locales `build-cache128/_deps`, aucun téléchargement. Avertissements fmt/spdlog existants.
- `ctest --test-dir E/build-map-preload-b13-20260927-v1 -C Release -R '^iee_tests$' --output-on-failure` : 1/1 exécutable passant.
- Tests C++ ajoutés : miss sans annulation, buffer différé réutilisable par Demand naturel, exclusion des réservations imbriquées, invalidation/recyclage, plafond mémoire, métadonnées rejetées, admission à 30 FPS, cadence lente, réserve de slots, dépassement, conservation LRU.
- Python : `python -m unittest test_build_map_page_cache -v` depuis `E/tools/` : 8 tests passants, dont génération de bindings, immutabilité et rejet des incohérences.
- `git diff --check` : succès. Aucun test ingame ni preuve de gain B1.3 à ce stade.

## Prochain essai et lecture des logs

1. Installation explicite via `E/tools/install_renderer_candidate.py install B/install-candidate-v1`, après fermeture jeu + InfinityLoader ; produire le reçu de l'installateur. Ne pas déplacer le cache ni les bindings référencés.
2. Même sauvegarde AR0900 : répéter une ouverture immédiate puis une ouverture après quelques secondes ; vérifier carte, retour à la vue locale, eau, animations, transition/rechargement.
3. Chercher `Map page B1.3 configured`, puis `plan-start`, `progress`, `all-bindings-resident-or-processed`, `soft-budget-overrun` ou `native-validation-failed`.
4. `submitted` = substitutions préparées avec texture résidente et cache préservé ; `notReady`, `unresolved`, `budgetSkips` = observations cumulées, **pas nombre de pages uniques**. `totalMs`/`maximumMs` couvrent appel natif + état GL ; décision d'arrêt sur pompe complète, validations comprises.
5. Comparer les intervalles de présentation **avant et pendant** dézoom : le travail est déplacé vers les images précédentes. Demand télémétré inclut désormais ces appels post-présentation. Les `hits/misses` B1 restent ceux des demandes naturelles ; `consumed` comprend aussi B1.3. Ne pas comparer naïvement les ratios à la session B1 seule.
6. Réussite attendue à mesurer : davantage de pages résidentes avant expansion, moins de pics froids, aucune nouvelle série de saccades avant ouverture, aucun défaut visuel/cache. Si premier Demand préparé >8 ms : arrêt attendu, analyser son résiduel natif avant d'élargir le budget.

Retour au comportement B1 : `EnableMapPagePreload=false` (jeu/loader fermés) ; retour exact au binaire B1 via le futur reçu d'installation. La priorité spatiale, les chargements d'animations et le coût de rendu chaud restent des axes séparés.
