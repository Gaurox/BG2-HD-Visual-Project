# PVR diagnostics — candidat A1, 2026-09-27

- Origine : [analyse fluidité, lot A](ANALYSE_FLUIDITE_CARTE_CHARGEMENTS_20260927.md).
- État : **source corrigée, DLL Release compilée, tests hôte passés ; installé pour test utilisateur le 2026-09-27 à 00:34 Europe/Paris ; premier retour performance analysé ci-dessous, objectif de fluidité non atteint, aucune validation visuelle/release déduite**.
- Périmètre : première correction locale du lot A ; journal asynchrone, nouvelle instrumentation et préparation de pages restent hors de ce candidat.

## Correction

[`hooks.cpp`](../engine/InfinityEngine-Enhancer/source-patchee/src/iee/hooks.cpp), `detour_pvr_demand`, L4028–4034 :

- Déplacer `diagnostic_pvr_resref`, `capture_pvr_lifecycle_cache` et `capture_process_resource_snapshot` sous la condition existante `enableMapPageOffframeConsume && lifecycle`.
- Page déjà chargée : `ioCandidate=false`, donc `lifecycle` absent ; aucun snapshot processus dans ce chemin. Plus de `GetProcessMemoryInfo` / `GetProcessIoCounters` / `GetProcessHandleCount` inutiles via ce snapshot.
- Diagnostic consume actif et lifecycle présent : mêmes captures avant/après et même resref conservé entre entrée et retour.
- Appel natif, retour/LastError, scopes GL, compteurs PVR, relevés processus périodiques et mesures de présentation conservés.
- INI, shaders, assets, caches et prototype prewarm inchangés. Les lectures I/O des matérialisations restent instrumentées.

## Candidate

| Champ | Valeur |
|---|---|
| Base source | `78dab9467b80cadac1239615f5b455a01cde1824` + diff local `hooks.cpp` : 6 ajouts / 3 suppressions |
| DLL | `engine/InfinityEngine-Enhancer/source-patchee/build-pvr-diagnostics-a1-20260927-v1/Release/InfinityEngine-Enhancer.dll` |
| Taille / SHA256 | 1 883 648 octets / `10FBD4652DC6E6AD8BFA0FE5CB8F4950352970E438BC2FBBC47D554B28BD1FD2` |
| Toolchain | Visual Studio 16 2019, MSVC 19.29.30158, x64, Release |
| Registre eau conservé | `pipeline/water/requests/wtlake-ar0300n-q070-ar1604-fit1-safe-test-20260926-v1/registry-v3.json` |
| Header eau généré | Identique à la build installée ; SHA256 `554B77BF4D5639E81E61D1C36AD470C1128A00C8EED9F74259EB5AE5136DA3F0` |
| Dépendances | Sources locales spdlog/minhook/zlib de `build-cache128/_deps/*-src`, téléchargement désactivé |

Commandes exécutées depuis la racine du dépôt, après configuration du nouveau répertoire avec le registre ci-dessus :

```powershell
cmake --build engine/InfinityEngine-Enhancer/source-patchee/build-pvr-diagnostics-a1-20260927-v1 --config Release --target InfinityEngine-Enhancer iee_tests --parallel 4
ctest --test-dir engine/InfinityEngine-Enhancer/source-patchee/build-pvr-diagnostics-a1-20260927-v1 -C Release -R '^iee_tests$' --output-on-failure
git diff --check
```

- Résultats : build succès ; `iee_tests` **1/1 passé** (1,01 s) ; diff sans erreur d'espacement. Avertissements de dépendance fmt C4459 et dépréciation CMake MinHook observés.
- Couverture : test agrégé existant, incluant compteurs PVR froid/chaud, phases GL et remise à zéro ; le detour moteur lui-même n'est pas exécuté par ce test. Vérification du detour par relecture du diff et compilation Windows ; aucune validation ingame déduite.
- Prochaine comparaison : même sauvegarde AR0900 et même INI ; ouverture immédiate puis réouvertures, maintien carte complète. Comparer intervalles de présentation et rafales PVR. Ne pas couper simultanément les diagnostics pour attribuer le gain à A1.
- Limite : A1 supprime un coût par demande, mais ne déplace ni lecture ni décompression des pages froides hors rendu.

## Installation de test

- Destination : `config://bg2ee_game_root/InfinityEngine-Enhancer.dll` ; SHA256 installé vérifié `10FBD4652DC6E6AD8BFA0FE5CB8F4950352970E438BC2FBBC47D554B28BD1FD2`.
- Jeu et InfinityLoader fermés ; installation transactionnelle puis commande `verify` réussies.
- Reçu actif : [`backups/renderer/20260926T223441227748Z-ee1219f0/renderer-install-receipt.json`](../backups/renderer/20260926T223441227748Z-ee1219f0/renderer-install-receipt.json).
- Ancienne DLL sauvegardée dans le sous-dossier `before/` du reçu ; SHA256 `A51834A18CD1B1940C18672FC7B92F1279F98492C7F9A81B69C417BCBDE6B18B`.
- INI conservé octet pour octet : SHA256 `47979DA9D49EF826014B675D4B0F495842509EED95A6574AFDF71D72B4204B08`. Aucun asset ni manifeste runtime/release modifié.
- Retour arrière, jeu/InfinityLoader fermés, depuis la racine du dépôt :

```powershell
& ./.tmp/water-python/Scripts/python.exe -B engine/InfinityEngine-Enhancer/source-patchee/tools/install_renderer_candidate.py restore backups/renderer/20260926T223441227748Z-ee1219f0/renderer-install-receipt.json
```

## Premier retour utilisateur — 2026-09-27, 00:35

- Retour : « je ne vois pas de différence » ; observation de performance, pas décision de QA visuelle.
- Session : `00:35:48.390 → 00:35:57.361`, 320 lignes, L16977–17296 de `config://bg2ee_game_root/InfinityEngine-Enhancer.log` ; un événement wide-view capturé. Pas de statistiques longues ni de plusieurs réouvertures exploitables dans cette session.
- Log lu : 5 342 039 octets, SHA256 `0155202B3655691D8444DA9CF0CF9D4F3941DA90BE660D68803CFB72C52F4A82`. DLL et INI présents vérifiés identiques aux empreintes d'installation ci-dessus ; aucun processus jeu/loader actif lors de l'analyse.

| Mesure | Référence 00:13 | A1 00:35 |
|---|---:|---:|
| Trois premières images de l'expansion, somme | 824,01 ms | 814,81 ms |
| Image la plus lente | 423,64 ms | 495,58 ms |
| Nouvelles grandes pages / octets soumis | 19 / 304 MiB | 20 / 320 MiB |
| Demand matérialisant | 722,031 ms | 755,600 ms |
| Dont appels upload compressé, CPU | 19,467 ms | 22,121 ms |
| Résiduel ressource/lecture/décodage/etc. | 702,350 ms | 733,196 ms |
| Cinq images suivantes sans nouvelle page, moyenne | 48,016 ms | 41,878 ms |
| CPU RenderTexture moyen sur ces cinq images | 13,316 ms | 8,662 ms |
| Chargement pack animations / détour LoadArea | 138,59 / 162,36 ms | 138,07 / 162,16 ms |

- Événements A1 L17248–17249 : 21 matérialisations dont 20 grandes pages ; répartition des grandes pages 2/6/12 contre 3/10/6 avant. Le pic supérieur ne démontre pas une régression : charge et déclenchement différents.
- A1 : cinq images chaudes = 44,08 / 43,60 / 43,68 / 44,83 / 33,20 ms ; CPU = 8,57 / 8,27 / 8,88 / 9,21 / 8,38 ms ; toujours 7 295 tuiles et 7 398 Demand par image.
- Conclusion : baisse observée du CPU RenderTexture compatible avec A1, mais échantillon insuffisant pour quantifier un gain reproductible. La pause de première apparition reste ≈0,8 s sur les trois images capturées ; A1 ne résout pas le symptôme utilisateur.
- Décision proposée : passer au lot B1, préparation anticipée des pages utiles dès le chargement de zone, lecture/décompression CPU hors rendu puis publication/upload sûrs avant première utilisation. Séparer finement lecture/décompression uniquement sur les pages manquantes pour choisir le traitement du résiduel. Ne pas simplement activer le prototype quatre pages ni reporter son attente sur le rendu.
- Conserver pixels HD, animations et comportement natif ; mesurer aussi le temps jusqu'à carte prête et le chargement total pour détecter un simple déplacement de la pause. Aucune nouvelle correction/configuration/installation exécutée lors de cette analyse.
