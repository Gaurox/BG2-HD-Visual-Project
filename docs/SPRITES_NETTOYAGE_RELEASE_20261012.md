# Sprites — nettoyage exécuté et release locale alpha.7
Date : 2026-10-12. Autorité utilisateur : `sprite/index/maintenance/20261012-cleanup-local-release-v1.json`.
Audit historique conservé : `docs/SPRITES_AUDIT_NETTOYAGE_RELEASE_20261012.md`.
État détaillé : `docs/validation/sprites-release-status-20261012-v1.json`.

## Résultat
- Rendu final xBR abandonné ; primitives xBR/ReboutCX internes Q3m conservées.
- Monde : **331 IDs / 15 familles**, Q3m x2 / Nearest ; 14 331 fichiers, 7 104 609 867 octets ; feuilles V6/V7/V9.
- UI : **81 paquets P7** V6, 2 119 276 octets ; corps humaine guerrière 0x6110 (4 variantes) + 77 équipements partagés. Autres corps natifs.
- Runtime : alpha.9, DLL `5D4EE06D84E0D6C6F6FB81797EAB0E9756B3ECE335EBF537E57C5597E0B40BCF` ; shaders live acquis conservés.
- Character V10 reste en réserve, non installé/non packagé. Source shader V10 et payload acquis restent distincts.
- Aucun calcul GPU, aucune nouvelle QA ingame, aucune modification du jeu, aucune publication.

## Archive et staging
- ZIP : `releases/BG2-HD-Upscale/dist-local/alpha7-sprites-q3m-20261012-v1/BG2HD-0.1.0-alpha.7-windows-local-alpha.zip`.
- Taille : **25,397,145,849 octets** ; stockage sans compression.
- SHA-256 : `3677905D7420DCDE694AC0AD8E45098BEA68DE6A1395F77011C346F864D9BA1A` ; sidecar `.zip.sha256`.
- Copie développée du package supprimée après validation ; ZIP, checksum et staging courant conservés.
- Staging courant : `releases/BG2-HD-Upscale/bg2hd/payload-allvalidated`.
- Staging précédent conservé : `releases/BG2-HD-Upscale/release-inputs/sprites-finalization-before-20261012-v1/payload-allvalidated`.
- **43,041 fichiers / 25,311,431,640 octets / 617 composants**. Les 28 629 entrées hors sprites sont strictement identiques au snapshot précédent.

| Domaine | Fichiers | Octets payload |
|---|---:|---:|
| overlay | 26 | 4,185,910 |
| ui | 15 | 150,994,944 |
| map | 8566 | 9,317,400,526 |
| area-animation | 19858 | 8,665,029,635 |
| effect | 164 | 67,091,482 |
| sprite | 14331 | 7,104,609,867 |
| paperdoll | 81 | 2,119,276 |

## Nettoyage et conservation
| Lot | Traitement exécuté | Mesure |
|---|---|---:|
| D0 | 2 copies V10 échouées, CMake, fixture P4, log jetable | 152,242 fichiers / 31,617,008,465 octets logiques |
| R + D1 | anciens rasters ReboutCX remplacés + sorties Ankheg spline/Large16 SDF refusées | 68,984 fichiers / 89,596,552,083 octets distincts |
| X | anciennes sorties raster xBR, après remplacement physique package ; sources/archives/rollback retenus | 12,955 fichiers / 170,217,140,469 octets distincts |
| Extras abandonnés | caches des 2 essais refusés + binaires/INI de la sonde P7 v1 jamais installée | 1,952 fichiers / 89,096,670 octets distincts |
| P | copies strictement identiques consolidées par liens physiques vers stockage accepté immuable | 1,297 copies / 1,966,206,306 octets distincts |

- Gain distinct mesuré R/D1/X/extras/P : **261,868,995,528 octets**, auquel s'ajoute D0. D0 compte les tailles logiques ; ne pas additionner comme mesure exacte de clusters NTFS.
- `targets/`, `guides/`, `encoded/`, `multipart-seams/` Q3m conservés pour éviter un recalcul GPU sur une reprise.
- Les `.npz/.npy` supprimés sont exclusivement les sorties des deux essais définitivement refusés ; caches de production retenue et P1/Character conservés.
- Natif BAM/BAMC, SQLite source, recettes, scripts/tests de régression, décisions QA et manifests historiques conservés.
- Les unités A non qualifiées, sauvegardes B, anciennes archives et 2 841 shards inertes du jeu restent conservés. Pas de purge globale de `.work`, `runs` ou des autres domaines.
- Inventaire des unités retirées : `sprite/index/maintenance/20261012-retired-raster-outputs-v1.json` ; plans/receipts par fichier dans `docs/measurements/sprites-cleanup-release-20261012-v1/`.
- Consolidation P : `sprite/accepted-storage/sha256/` ; noms, chemins et octets historiques préservés. Ne jamais modifier ces feuilles en place ; nouvelle version en cas de remplacement.

## Adaptations effectuées
- Candidats/schema v2 ; inventaires plats monde/UI sous `manifests/sprite-inventories/`, compilateur et miroirs package.
- 4200 conservé pour monde ; 4210 dédié aux paperdolls. Activations/rollback INI appartiennent à chaque composant ; sonde UI désactivée.
- Types x2 `paperdoll` acceptés par content/schema/staging/TP2 ; TP2 régénéré ; erreurs de configuration traduites de façon générique.
- Deux preuves CRLF remises aux octets LF acquis, hashes QA inchangés. 13 entrées Ambient_static de queue corrigées depuis leur QA existante.
- Release/changelog/known issues/guides actualisés ; maps/animations/effets/renderer conservés.
- Fixtures de validation placées sous le workspace après refus de renommage dans le répertoire temporaire système.

## Vérifications et prochaine passe
- 6 tests négatifs/positifs du vérificateur ; hashes physiques source puis staging ; schémas, TP2 déterministe, 9 langues, contrats composants/miroirs.
- Configuration : 4 cycles propriétaires/encodages, réglage utilisateur préservé ; 4 encodages INI existants ; installation/restauration renderer sur fixture.
- Phase4 payload/runtime, Phase6B ZIP/checksums et suite Phase5A sur fixtures : passées. Installation/désinstallation du catalogue monde et des 81 paperdolls incluse ; anciennes feuilles/INI restaurées.
- Statut public **blocked**. À faire sur installation Steam propre : qualification combinée monde/UI/maps/animations/renderer, chaîne de sauvegarde future vers vanilla, restauration complète et bootstrap EEex absent.
- Après cette qualification seulement : fermer les rollbacks devenus inutiles, nettoyer les shards inertes du jeu (jeu/InfinityLoader fermés) et décider des sauvegardes/archives anciennes.
- Limite observée : fixture imbriquée trop longue => WeiDU 249 `stat Unix_error(20)` sur un shard SHA-256. Reprise dans `.tmp/qaf7` ; harness futur sous `.tmp/qa-bg2hd`. Avant diffusion publique : préflight des chemins source complets (<260 caractères), et rollback configuration sans masquer une copie échouée avant création du journal. Archive locale inchangée ; choisir une racine de jeu courte.
- Publication distincte : contact/provenance/conditions de diffusion encore ouverts dans `manifests/release.json`. Ne pas publier cette archive locale.
