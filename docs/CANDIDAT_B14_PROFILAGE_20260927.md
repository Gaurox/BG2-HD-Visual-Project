# B1.4 — ventilation du coût natif et des lectures d'animations

- Base : `ad7b44e4` (B1.3). Motivation : `COMPARAISON_B13_B1_20260927.md` ; un Demand préparé coûte 28,926 ms, arrêt du plan à 8 ms ; `frameRead` animations passe de 139,56 à 1 152,19 ms sans ventilation.
- État : **compilé, tests C++ passants, installé le 27/09/2026 à 02:48:37 Paris ; essai ingame à effectuer par l'utilisateur**. Code local non committé.
- Consigne utilisateur persistante : aucune prise de contrôle du PC/de l'interface. L'utilisateur lance le jeu, manipule la carte et ferme le jeu ; l'agent prépare le code, les fichiers, les mesures et donne les instructions.
- Nature : candidat de diagnostic, pas nouvelle correction de performances. Budget 8 ms, une page/image, arrêt sur dépassement, plafond privé 128 MiB et rendu de B1.3 conservés. INI strictement identique.

## Mesures ajoutées

Préfixe `E = engine/InfinityEngine-Enhancer/source-patchee/`.

| Log | Champs / signification |
|---|---|
| `Map page B1.4 profiling enabled` | Deux hooks déjà documentés/validés par le manifeste : CRes::Demand et helper d'ouverture ; actifs seulement avec préchargement + PerformanceLogs |
| `Map page B1.4 phases` | Page, génération, frame, résultat substitution, durée Demand, durée CRes::Demand, ouvertures, CRC, copie, création texture, upload compressé CPU, résiduel arithmétique, compteurs I/O processus |
| `Map page B1.4 presentation` | Intervalle précédent/suivant, coût appel + état GL, pompe totale, occupation cache avant, validation après et génération encore courante |
| `Area-animation frame read phases` | Temps ouverture/taille/seek, allocation + initialisation du vector, lecture stream, fermeture ; nom/taille/temps du fichier de frame le plus lent |

- `hooks.cpp` : association thread-local au seul Demand proactif ; les appels PVR imbriqués masquent puis restaurent la trace. Mesure de la ressource externe sans double comptage récursif ; retours natifs et GetLastError conservés. Chemin naturel : pas de capture/process snapshot ni log B2c supplémentaire.
- `core/pvr_demand_telemetry.*` : résiduel = Demand − ressource − CRC − copie − création texture − upload. `fileOpenMs` **inclus dans** `resourceMs`, jamais soustrait deux fois. `residualValid=false` si mesures absentes, chronomètre invalide ou partition incohérente ; ne pas interpréter un zéro invalide comme absence de coût.
- `map_page_preload.*` : conserve une petite trace fixe ; écrit les deux nouvelles lignes après capture de l'intervalle suivant, hors des fenêtres chronométrées. L'écriture peut encore peser sur l'image ultérieure. Si fin du processus avant l'image suivante, ces lignes ne seront pas émises.
- `area_animation_x4_registry.*` : même lecture et mêmes octets ; sous-phases chronométrées uniquement lorsque `PackPreparationStats` est demandé. Une ligne agrégée par pack, pas 89 lignes par chargement. `frameRead` historique reste le conteneur des sous-phases.

## Limites d'interprétation

- CRes::Demand inclut récupération/lecture/allocation de ressource : ce n'est pas un chronomètre ReadFile isolé. Le helper d'ouverture est une sous-phase native, pas une mesure du périphérique.
- `streamReadMs` comprend attente OS, cache système et copie ; aucune preuve de débit physique disque. `allocateZeroMs` comprend allocation, initialisation et défauts de pages éventuels.
- I/O processus inclut toujours le worker B1 concurrent. Upload mesuré côté CPU, sans attente de fin GPU ajoutée.
- L'intervalle suivant comprend préchargement + travail de l'image suivante ; ne pas l'assimiler à la durée du préchargement. Le budget ne peut pas interrompre un Demand déjà commencé.
- Les hooks/timers ajoutent un petit coût non quantifié ingame ; comparaison B1.3/B1.4 = mesure instrumentée. Aucun seuil modifié pour faire artificiellement passer l'appel.

## Build / installation

- Build : `E/build-map-profile-b14-20260927-v1/`, VS2019 x64 / MSVC 19.29, Release, dépendances locales `build-cache128/_deps` ; aucune recompilation des assets ou release.
- Candidat : `E/build-map-profile-b14-20260927-v1/install-candidate-v1/`.
- DLL : 1 964 544 octets, SHA-256 `3E5914BFF600FA721B7213C9FD1BA4759A884DE8E3D176EBFA6940223BF88B6D`.
- INI : 5 950 octets, SHA-256 `0A56C32AADCEAAEDBD9CD52A85A6A3ADDC030C745547333C1423DBBD1C5D2A89`, identique B1.3 ; `PerformanceLogs=true`, préparation et préchargement actifs.
- Registre eau conservé : `pipeline/water/requests/wtlake-ar0300n-q070-ar1604-fit1-safe-test-20260926-v1/registry-v3.json` ; header généré SHA-256 `554B77BF4D5639E81E61D1C36AD470C1128A00C8EED9F74259EB5AE5136DA3F0` identique.
- Dépendances à conserver : cache privé `E/build-map-prepare-b1-20260927-v1/private-cache-ar0900-v1/` + bindings `E/build-map-preload-b13-20260927-v1/preload-bindings-ar0900-v1.index`. Pas de duplication des 155,59 MiB de cache privé.
- Reçu actif : `backups/renderer/20260927T004837469820Z-68d78d2a/renderer-install-receipt.json` ; sauvegarde de B1.3. Installateur : jeu/InfinityLoader fermés, deux fichiers gérés, installation vérifiée ; commande `verify` réussie séparément.
- Retour exact B1.3 : outil `E/tools/install_renderer_candidate.py restore` avec ce reçu, jeu/InfinityLoader fermés.

## Vérifications exécutées

- DLL + `iee_tests` compilés ; contrôle incrémental final sans recompilation nécessaire.
- `ctest --test-dir E/build-map-profile-b14-20260927-v1 -C Release -R '^iee_tests$' --output-on-failure` : **1/1 passant**, 0,68 s pour l'exécutable.
- Tests ajoutés : résiduel sans double soustraction de l'ouverture ; dépassement/overflow/chronomètre manquant rejetés ; sous-phases des lectures contenues dans la durée englobante ; nom/taille du fichier lent cohérents. Tests existants de parsing/rendu des packs conservés.
- INI comparé octet à octet par hash ; header eau identique ; bindings par hash et 27 fichiers privés présents aux tailles attendues ; `git diff --check` passant.
- Pas de nouvelle session jouée par l'agent, aucune validation visuelle déduite.

## Essai utilisateur

1. Lancer normalement le jeu ; charger la même sauvegarde AR0900.
2. Une fois la zone visible, attendre **5 secondes**, ouvrir la carte, la laisser affichée **5 secondes**, puis quitter complètement le jeu.
3. Relancer le jeu et refaire exactement le même essai, sans changer de sauvegarde ni de réglage. Cette répétition compare deux lancements ; elle ne garantit pas un premier cache OS froid.
4. Signaler la fin des deux essais. Lire les deux dernières sessions, comparer les nouvelles phases et les images d'expansion ; pas de purge de cache OS, redémarrage PC ou prise de contrôle nécessaire.

Décision après traces : ressource dominante → étudier lecture native restante et contrat de propriété ; copie/allocation dominante → éviter les opérations redondantes si contrat compatible ; upload dominant → examiner cadence/gestion GPU. Animations : allocation dominante → examiner initialisation des buffers ; ouverture/lecture dominante → étudier lecture anticipée ou stockage groupé à octets identiques. Ne pas augmenter le plafond de 8 ms sur la seule base d'un Demand plus long.
