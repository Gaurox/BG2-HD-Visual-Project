# Suivi d’implémentation — audit performances cartes x4

Ce document suit les actions proposées par
[`../AUDIT_PERFORMANCES_CARTES_X4.md`](../AUDIT_PERFORMANCES_CARTES_X4.md). Il ne remplace pas les
sources de vérité du moteur, les manifests de build ou les preuves de validation ingame.

## État au 2026-08-29

Les deux mesures P0 ciblant le hot path ont été implémentées et validées ingame. Les tests manuels
n’ont relevé **ni amélioration perceptible ni régression**. Ils ne constituent pas une mesure de
frametime, d’I/O, de CPU ou de mémoire : aucune conclusion quantitative sur leur gain ne doit en
être tirée.

Le premier petit lot P1 de télémétrie a produit une première session ingame exploitable. Son
correctif de précision a été revalidé ingame sans erreur. Il reste opt-in via
`PerformanceLogs=true`.

Le deuxième petit lot P1 instrumente maintenant la préparation synchrone des packs d’animations
de zone. Il est compilé, installé et validé techniquement ingame sur AR0602, AR0516 et AR0900.
Le retrait des traces INFO émises une fois par frame d’animation est également validé ingame sur
ces trois zones.

Le troisième petit lot P1 mesure le cache GPU borné des animations. Il est validé ingame sur
AR0700, AR0516, AR0900 et AR0602 ; les trois dernières zones révèlent des évictions LRU répétées.

Le runtime expérimental courant est installé localement de manière réversible avec son état
distinct sous `bg2hd/state/animation-gpu-cache-telemetry-20260828T231509Z/`. Sa restauration
revient au build validé qui retire les logs INFO par frame, dont les états précédents conservent la
chaîne de retour jusqu’au build P0 de rotation des logs. Il n’est pas éligible à la release et
aucun manifeste de release n’a été modifié.

## Actions

| Priorité audit | Action | État | Résultat / prochaine gate |
|---:|---|---|---|
| P0 | Baseline propre : logs verbeux/performance et prototypes hors périmètre désactivés ; journal existant archivé | Fait localement | Aucun gain ni régression perceptible. Conserver cette configuration pour les futurs A/B. |
| P0 | Corriger le budget documentaire des pages 2048 | Fait | 2048 px = 7×7 = 49 tuiles ; 4096 px = 15×15 = 225 tuiles. Commit `3879c10`. |
| P0 | Court-circuiter `is_wtpool_page` si trace et bypass WTPOOL sont désactivés | Validé ingame | Les lectures protégées ne sont plus exécutées hors des deux diagnostics WTPOOL. Mesure objective des `safe_read` encore requise. |
| P0 | Rendre `TILE_PAGE_DIAG` opt-in | Validé ingame | Nouveau réglage `[Rendering] EnableTilePageDiagnostics=false`. Il reste indépendant de `PerformanceLogs`, afin de pouvoir mesurer le hook sans réactiver un flush INFO par page. |
| P0 | Journal rotatif/borné | Validé ingame | Rotation à 16 Mio avec trois sauvegardes, soit environ 64 Mio de nouvelles sorties conservées. Le sink reste synchrone et `flush_on(info)` est préservé. |
| P1 | Premier lot : marqueurs carte et compteurs table PVR/GL | Validé ingame | Mesure `LoadArea`, les pages de table distinctes et textures sources observées, ainsi que les appels GL upload/delete. Aucun timing I/O/zlib ni calcul mémoire exact dans ce lot. |
| P1 | Attribution précise I/O, zlib et mémoire | Premier sous-lot mesuré ingame | Les lectures synchrones des fichiers RGBA expliquent presque tout le temps ajouté sur AR0602 et AR0516 ; le pic brut mesuré atteint 600,99 Mio sur AR0516 → AR0900. La mémoire résidente du processus et le cache fichier restent à mesurer séparément. |
| P1 | Supprimer les flush INFO une fois par frame d’animation | Validé ingame | `Composing area animation` passe en DEBUG : aucune occurrence INFO sur AR0602, AR0516 et AR0900, contre 427 écritures synchrones dans la session de référence. Aucun changement de rendu ou de cache. |
| P1 | Mesurer le cache GPU des animations x4 | Validé ingame | Les invariants des compteurs sont cohérents et aucun échec GPU n’est observé. Le cache de 64 entrées évite toute éviction sur AR0700, mais provoque un churn important sur AR0516, AR0900 et AR0602. |
| P1 | Animations x4 à la demande avec budget mémoire | Différé | Chantier moyen/élevé ; ne pas l’entreprendre sans attribution mémoire. |
| P1 | Atlas UI chargés à la demande | Différé | Chantier moyen ; dépend d’une mesure du coût de première ouverture UI. |
| P1 | Préchargement progressif des pages de carte | Différé | Chantier élevé ; ne pas déplacer le hitch sans budget mesuré. |
| P2 | Double `Demand` et invalidations GL | Différé | Durée de vie moteur sensible ; nécessite les compteurs P1. |
| P2/P3 | Repack 4096, profil faible mémoire ou x2 sélectif | Non engagé | Implique contenu, QA et manifests distincts ; hors optimisation runtime rapide. |

## Correctif expérimental P0

- `EngineConfig::wtpool_page_check_enabled()` ne déclenche l’identification de la page WTPOOL que
  si `EnableWTPOOLTileTrace` ou `BypassWTPOOLTileRenderHook` est actif.
- `TILE_PAGE_DIAG` ne réalise plus ses lectures de snapshots ni son `LOG_INFO`/flush par page sans
  `EnableTilePageDiagnostics=true` explicite.
- Le réglage est parsé, sérialisé et documenté dans le modèle INI ; son défaut est `false`.

Validation automatisée du build expérimental :

- DLL Windows Release compilée ;
- `ctest -C Release` : 2/2 tests C++ réussis ;
- tests Python communs : 180/180 réussis.
- test natif de rotation : fichier actif et deux sauvegardes bornés, troisième sauvegarde absente.

La variante avec avertissements traités comme erreurs reste bloquée avant le code du projet par
`C4459` dans `spdlog/fmt` avec MSVC 2019. Le build normal compile le correctif avec cet
avertissement tiers connu.

## Premier lot expérimental P1

Avec `PerformanceLogs=true`, le runtime ajoute :

- un marqueur de génération et de resref de carte, ainsi que le temps passé dans le vrai
  `LoadArea` moteur et le temps total du détour ;
- un cumul par carte des tirages de tuiles décodés, des pages de table PVR distinctes par tileset
  et des identifiants de textures sources distincts ;
- un cumul des appels OpenGL `glTexImage2D`, `glTexSubImage2D`,
  `glCompressedTexImage2D` et `glDeleteTextures`, avec les octets connus ;
- un rapport agrégé toutes les cinq secondes, sans `TILE_PAGE_DIAG`, sans lecture protégée
  supplémentaire et sans log individuel par page.

Les compteurs OpenGL sont globaux à la fenêtre de la carte. En particulier, un upload compressé
S3TC n’est **pas** une preuve qu’une page PVRZ de carte a été chargée : BAM V2 et MOS V2 utilisent
également des PVRZ. `tablePagesObserved` représente les numéros effectivement lus dans les tables
TIS/PVR par le hook de tuiles ; `glLargeS3tcBaseLevel*` n’est qu’un bucket de corrélation pour les
textures S3TC d’au moins 2048×2048. Les compteurs sont bornés et remis à zéro à chaque chargement
de carte retenu. Les appels même-zone mesurés sous 1 ms sont fusionnés dans la génération active ;
les échantillons de page négatifs et ceux dépassant la capacité bornée sont comptés séparément.

### Première session P1

Session du 2026-08-28, sans erreur renderer et sans `TILE_PAGE_DIAG` :

| Carte | `LoadArea` moteur | Détour total | Pages table observées | Gros uploads S3TC |
|---|---:|---:|---:|---:|
| AR0700N | 125,07 ms | 822,57 ms | 100 | 100 |
| AR0602 | 67,06 ms | 1 058,26 ms | 45 | 45 |
| AR0400 | 51,47 ms | 127,11 ms | 33 | 33 |

Les pages de table, identifiants de textures sources et gros uploads S3TC correspondent 1:1 sur
ces trois cartes. Le temps hors moteur est fortement corrélé à la préparation synchrone du pack
d’animations de zone : 99,10 Mio bruts sur AR0700N, 104,30 Mio sur AR0602 et seulement 0,30 Mio
sur AR0400. Cette observation justifie l’analyse du chargement à la demande des animations, mais
ne constitue pas encore une mesure de mémoire résidente.

La session a aussi montré un à deux appels `LoadArea` même-zone quasi nuls après chaque chargement
réel. Le correctif de précision les fusionne désormais au lieu de créer une nouvelle génération.

### Revalidation du correctif de précision

Session du 2026-08-29, sans erreur renderer et sans `TILE_PAGE_DIAG` :

- AR0700N produit uniquement la génération 1 ; son appel même-zone quasi nul est compté dans
  `ignoredNoOpLoadAreaCalls=1` ;
- AR0400 produit uniquement la génération 2 ; ses deux appels même-zone quasi nuls sont comptés
  dans `ignoredNoOpLoadAreaCalls=2` ;
- après parcours caméra sur AR0400, les 519 échantillons de page négatifs sont séparés et
  `tablePageAboveCapacitySamples` reste à zéro ;
- les 60 pages de table, 60 identifiants de textures sources et 60 gros uploads S3TC observés sur
  AR0400 restent corrélés 1:1.

Les temps de chargement de cette session, vraisemblablement à cache chaud, ne sont pas comparés à
la première session et ne constituent pas un benchmark A/B.

## Deuxième petit lot expérimental P1

Avec `PerformanceLogs=true`, la préparation d’un pack d’animations de zone publie désormais :

- les octets du registre, le nombre de fichiers RGBA et leurs octets exacts ;
- les durées séparées de lecture du registre, lecture des frames, validation/allocation et échange
  du pack ;
- les octets RGBA bruts du pack sortant, du pack entrant devenu résident et leur pic temporaire de
  coexistence ;
- le nombre de textures sortantes mises en attente, puis le nombre effectivement supprimé au
  prochain passage OpenGL du monde.

Les mesures sont prises uniquement lorsque `PerformanceLogs` est actif. Elles ne modifient ni le
contenu chargé, ni le cache de 64 textures, ni la politique de remplacement. `peakRawBytes` compte
uniquement les buffers RGBA appartenant au runtime : il n’inclut pas l’overhead de l’allocateur, le
Working Set du processus, le cache fichier Windows ou des octets GPU estimés.

Validation automatisée et contrôle d’installation :

- DLL Windows Release compilée ;
- `ctest -C Release` : 2/2 tests C++ réussis ;
- tests Python communs : 180/180 réussis ;
- nouveaux tests des octets de registre/frames, de la résidence brute et du pic sortant + entrant ;
- DLL installée SHA-256
  `770642CA1FD0DA5E8FC97046BE4D7D959AF7E3DD02D92E48E87AAF52F829A835`, les autres fichiers
  renderer restant bit-identiques.

### Première session du deuxième lot P1

Session du 2026-08-29, sans erreur renderer et sans `TILE_PAGE_DIAG` :

| Carte | Fichiers RGBA | Lecture frames | Pack total | RGBA sortant | RGBA résident | Pic RGBA brut | Hors moteur `LoadArea` |
|---|---:|---:|---:|---:|---:|---:|---:|
| AR0602 | 178 | 70,89 ms | 71,05 ms | 0 Mio | 104,30 Mio | 104,30 Mio | 71,28 ms |
| AR0516 | 212 | 1 470,28 ms | 1 479,39 ms | 104,30 Mio | 385,89 Mio | 490,19 Mio | 1 479,57 ms |
| AR0900 | 80 | 704,57 ms | 725,46 ms | 385,89 Mio | 215,09 Mio | 600,99 Mio | hors détour mesurable |

Sur AR0602 et AR0516, l’écart entre le temps hors moteur et le temps total du pack n’est que de
0,23 ms puis 0,18 ms. La lecture synchrone des frames domine : le registre, la
validation/allocation et l’échange du pack sont secondaires. Les 64 noms de textures sortants ont
été mis en attente puis supprimés au passage OpenGL suivant.

AR0900 a révélé le cas le plus important : le moteur a publié la nouvelle zone après le retour du
détour `LoadArea`. La réconciliation depuis le thread de rendu a donc chargé le pack pendant le
premier passage monde, causant 725,46 ms de travail synchrone ; la fenêtre de présentation a relevé
un maximum de 1 027,10 ms et le hook `RenderTexture` un maximum de 726,50 ms. Ce n’est pas un coût
de parsing ou d’upload anticipé : la lecture des 80 fichiers RGBA en représente 704,57 ms.

L’avertissement de récupération du prologue EEex attendu et le fallback de tint liquide WLAKE00
sont les seuls avertissements de la session ; aucun `error` ou `critical` n’a été émis.

### Validation du retrait des logs par frame

Session du 2026-08-29 sur AR0602, AR0516 et AR0900 :

- aucune occurrence INFO de `Composing area animation`, contre 427 dans la session de référence ;
- les trois événements agrégés de télémétrie des packs sont toujours présents ;
- aucune erreur et aucun `TILE_PAGE_DIAG` ;
- rendu des animations et libération différée des textures sortantes fonctionnels ingame.

Les temps de lecture plus faibles observés pendant cette session proviennent vraisemblablement du
cache fichier Windows plus chaud. Ils ne sont donc pas attribués au retrait des logs et ne
constituent pas une mesure de gain de performances.

## Troisième petit lot expérimental P1

Avec `PerformanceLogs=true`, le cache GPU de 64 textures d’animations publie désormais des
compteurs cumulatifs pour la zone résidente :

- requêtes, hits et misses ;
- créations de noms de textures moteur et échecs de création ;
- tentatives d’upload, succès, échecs et octets RGBA8 de niveau de base uploadés ;
- évictions LRU, suppressions consécutives à un upload raté et noms invalidés avec le contexte ;
- nombre de textures résidentes, octets de niveau de base résidents et pic correspondant.

Un snapshot est produit toutes les cinq secondes, puis un dernier au changement de pack. Une
éviction LRU réutilise le nom de texture moteur existant et n’est donc pas comptée comme une
suppression OpenGL. Les octets décrivent le niveau de base RGBA8 demandé au pilote, sans prétendre
mesurer son allocation interne. Les compteurs restent inactifs lorsque `PerformanceLogs=false` et
ne changent ni la capacité, ni la sélection LRU, ni le rendu.

Validation automatisée :

- DLL Windows Release compilée ;
- `ctest -C Release` : 2/2 tests C++ réussis ;
- tests Python communs : 180/180 réussis ;
- tests natifs du démarrage à vide, de la capacité fixe, du reset au changement de pack et de la
  libération de zone.

Installation réversible :

- DLL active SHA-256
  `7898B87F57D747E5CA7DC76E11AA66FC106CC1E45F71467D98AE1D476E12BA35` ;
- les six autres fichiers renderer publiés restent bit-identiques au runtime précédent ;
- la restauration remet la DLL SHA-256
  `AACFBB8DC299DDAFC4DF76C093F5971B104D36CE23A6EA3E77806F1A0A36C201`.

### Première session du troisième lot P1

Session du 2026-08-29, parcours AR0700 → AR0516 → AR0900 → AR0602 :

| Zone | Requêtes | Hits | Misses / uploads | Taux de hit | Évictions LRU | Uploads cumulés | Résident final | Pic résident |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| AR0700 | 7 822 | 7 768 | 54 | 99,31 % | 0 | 45,23 Mio | 45,23 Mio | 45,23 Mio |
| AR0516 | 10 261 | 9 192 | 1 069 | 89,58 % | 1 005 | 1 697,52 Mio | 102,32 Mio | 113,08 Mio |
| AR0900 | 2 320 | 1 922 | 398 | 82,84 % | 334 | 1 070,05 Mio | 172,01 Mio | 172,41 Mio |
| AR0602, snapshot à 5 s | 4 318 | 3 903 | 415 | 90,39 % | 351 | 284,98 Mio | 44,08 Mio | 46,86 Mio |

Les invariants attendus sont vérifiés sur chaque snapshot : `requests = hits + misses`, chaque
miss aboutit à un upload réussi, puis `lruEvictions = successfulUploads -
textureNameCreations` une fois les 64 noms créés. Aucun échec de création ou d’upload, aucune
suppression consécutive à un échec et aucune invalidation de contexte n’ont été observés. Les trois
transitions ont également supprimé correctement les 54, 64 puis 64 noms sortants différés.

La session ne contient ni erreur, ni `TILE_PAGE_DIAG`, ni trace INFO par frame. Le seul
avertissement est la récupération attendue du prologue `RenderTexture` détourné par EEex.

Le cache de 64 entrées n’est donc pas seulement une borne mémoire : sur AR0516, AR0900 et AR0602,
il force des réuploads répétés dont le cumul dépasse largement la résidence instantanée. Les
octets publiés décrivent les niveaux de base RGBA8 envoyés au pilote, pas la VRAM réellement
allouée.

## Prochaine étape

Le P0, les trois lots de télémétrie P1 et le retrait des logs INFO par frame sont validés. La
prochaine gate prudente est une analyse en lecture seule d’un budget conjoint CPU/GPU pour les
frames. Augmenter aveuglément la capacité à toutes les frames supprimerait le churn, mais pourrait
conserver jusqu’à 385,89 Mio de niveaux RGBA8 sur AR0516 en plus du pack brut déjà résident. Le
chargement à la demande doit donc définir ensemble la résidence CPU, la résidence GPU et la
politique d’éviction, puis prévoir un A/B borné. Une mesure externe du Working Set, du cache fichier
et idéalement de la VRAM restera nécessaire pour quantifier le gain processus complet.
