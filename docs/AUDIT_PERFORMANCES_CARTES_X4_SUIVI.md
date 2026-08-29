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

Le quatrième petit lot P1 simule passivement quatre couples de budgets CPU/GPU sur la trace réelle
des frames. La première session ingame est techniquement valide et montre que le budget en octets
et la limite du nombre de textures doivent être étudiés séparément. Le cache réel de 64 textures
et le chargement intégral des packs restent inchangés. Une grille raffinée de cinq profils est
compilée, testée et mesurée ingame. Elle retient 256 Mio / 192 textures comme borne GPU candidate
et écarte le cache CPU de 192 Mio, sans encore modifier la politique réelle.

Le deuxième sous-lot d’attribution mémoire instrumente le Working Set, les octets privés, les
défauts de page et les compteurs d’I/O du processus. Il est compilé, testé, installé de manière
réversible et mesuré ingame. Il ne mesure pas directement les lectures physiques ni l’allocation
VRAM du pilote.

Le recoupement externe est également terminé sur deux passages consécutifs. Les compteurs du
volume confirment une session servie presque entièrement par le cache fichier Windows ; les
compteurs WDDM du processus et de l’adaptateur sont cohérents et ne montrent pas de migration
persistante vers la mémoire GPU non locale. Ces résultats valident les ordres de grandeur sur la
machine de test, pas un seuil matériel propre à tous les PC.

Le symptôme prioritaire a depuis été précisé : le pic survient principalement à l’ouverture de la
carte ingame, lorsque le dezoom augmente brutalement la vue monde et demande les tuiles de carte.
Le mini-lot carte 1 instrumente maintenant ce burst par frame. Il est compilé et couvert par les
tests natifs, puis installé de manière réversible et mesuré sur AR0602, AR0700N, AR0516 et AR0900.
Il confirme le burst synchrone PVRZ. Le raffinement 1c conserve l’historique fixe de seize frames
du détecteur progressif et ajoute une barrière de réarmement liée à la contraction de la vue. Son
retest sur deux ouvertures successives de chacune des quatre zones produit exactement deux
captures par zone, sans redéclenchement pendant un même dezoom. Il ne change aucun chargement.

Le mini-lot carte 2 instrumente maintenant le vrai `CResPVR::Demand` sur la cible 2.7.3 validée.
Son retest ingame attribue 95 à 98 % des frames de pic à cette demande synchrone. Les appels GL de
création et d’upload restent minoritaires ; l’essentiel demeure dans le résidu
ressource/lecture/préparation moteur. Les secondes ouvertures ne matérialisent plus aucune PVR.

Le mini-lot carte 3 prototype maintenant le préchauffage progressif opt-in des pages PVRZ de la
carte courante. Il est compilé, couvert par les tests natifs et mesuré ingame sur AR0700N, AR0516,
AR0602 et AR0900 : aucune éviction du cache natif n’est observée, et le pic de première ouverture
d’AR0700N tombe de 404,7–839,3 ms à 7,6 ms. Cette session n’est pas un A/B contrôlé : les mesures
de référence proviennent de sessions antérieures dont le cache fichier n’était pas maîtrisé, et
AR0900 n’a aucune ouverture de carte après préchauffage. Aucun chiffre de gain ne doit être publié
avant la campagne décrite en fin de document.

Le runtime expérimental courant est ce mini-lot 2, installé localement avec son état distinct sous
`bg2hd/state/map-pvr-demand-phase-telemetry-20260829T064935Z/`. Sa restauration revient au
raffinement 1c, puis la chaîne des états précédents permet de revenir jusqu’au build P0 de rotation
des logs. Il n’est pas éligible à la release et aucun manifeste de release n’a été modifié.

## Actions

| Priorité audit | Action | État | Résultat / prochaine gate |
|---:|---|---|---|
| P0 | Baseline propre : logs verbeux/performance et prototypes hors périmètre désactivés ; journal existant archivé | Fait localement | Aucun gain ni régression perceptible. Conserver cette configuration pour les futurs A/B. |
| P0 | Corriger le budget documentaire des pages 2048 | Fait | 2048 px = 7×7 = 49 tuiles ; 4096 px = 15×15 = 225 tuiles. Commit `3879c10`. |
| P0 | Court-circuiter `is_wtpool_page` si trace et bypass WTPOOL sont désactivés | Validé ingame | Les lectures protégées ne sont plus exécutées hors des deux diagnostics WTPOOL. Mesure objective des `safe_read` encore requise. |
| P0 | Rendre `TILE_PAGE_DIAG` opt-in | Validé ingame | Nouveau réglage `[Rendering] EnableTilePageDiagnostics=false`. Il reste indépendant de `PerformanceLogs`, afin de pouvoir mesurer le hook sans réactiver un flush INFO par page. |
| P0 | Journal rotatif/borné | Validé ingame | Rotation à 16 Mio avec trois sauvegardes, soit environ 64 Mio de nouvelles sorties conservées. Le sink reste synchrone et `flush_on(info)` est préservé. |
| P1 | Premier lot : marqueurs carte et compteurs table PVR/GL | Validé ingame | Mesure `LoadArea`, les pages de table distinctes et textures sources observées, ainsi que les appels GL upload/delete. Aucun timing I/O/zlib ni calcul mémoire exact dans ce lot. |
| P1 | Attribution précise I/O, zlib et mémoire | Mesuré ingame et recoupé | Les octets lus correspondent exactement aux registres et frames RGBA et le Working Set suit le delta brut attendu. Sur huit chargements, le volume ne lit que 0 à 1,32 Mio autour de packs logiques de 99,10 à 385,89 Mio : la session chaude est servie presque entièrement par le cache fichier. Le pic WDDM du jeu est de 868,35 Mio, sans pression non locale significative. |
| P1 | Supprimer les flush INFO une fois par frame d’animation | Validé ingame | `Composing area animation` passe en DEBUG : aucune occurrence INFO sur AR0602, AR0516 et AR0900, contre 427 écritures synchrones dans la session de référence. Aucun changement de rendu ou de cache. |
| P1 | Mesurer le cache GPU des animations x4 | Validé ingame | Les invariants des compteurs sont cohérents et aucun échec GPU n’est observé. Le cache de 64 entrées évite toute éviction sur AR0700, mais provoque un churn important sur AR0516, AR0900 et AR0602. |
| P1 | Simuler passivement différents budgets CPU/GPU | Raffinement mesuré ingame | 192 entrées éliminent le churn d’AR0602 ; 256 Mio GPU couvrent AR0700, AR0900 et AR0602, mais laissent 11 rechargements sur AR0516. Passer le cache CPU de 128 à 192 Mio n’apporte aucun gain sur la trace. |
| P1 | Animations x4 à la demande avec budget mémoire | Prêt à découper | L’attribution mémoire préalable est terminée. Chantier moyen/élevé à commencer par un A/B configurable et réversible, avec le chargement intégral actuel comme fallback. |
| P1 | Atlas UI chargés à la demande | Différé | Chantier moyen ; dépend d’une mesure du coût de première ouverture UI. |
| P1 | Attribuer par frame le burst d’ouverture de carte | Validé ingame | Deux ouvertures successives sur chacune des quatre cartes produisent exactement les événements 1 et 2. Aucun redéclenchement n’apparaît pendant le maintien de la carte ; la contraction réarme correctement le détecteur. |
| P1 | Attribuer les phases de `CResPVR::Demand` | Validé ingame | La demande PVR porte 95 à 98 % des frames de pic ; `glGenTextures` et l’upload compressé sont minoritaires face au résidu ressource/lecture/préparation moteur. Aucun changement de politique. |
| P1 | Préchargement progressif des pages de carte | Prototype mesuré ingame, incomplet | Mini-lot carte 3 implémenté et opt-in. Première session : zéro éviction sur les quatre zones ; le pic d’ouverture d’AR0700N passe de 404,7–839,3 ms à 7,6 ms. AR0900 n’a pas d’ouverture après préchauffage et les mesures « avant » ne sont pas toutes à froid : un A/B contrôlé en deux sessions reste requis avant toute conclusion. |
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

## Quatrième petit lot expérimental P1

Avec `PerformanceLogs=true`, chaque requête réelle de frame alimente désormais quatre simulations
hiérarchiques qui commencent vides à l’entrée de zone :

| Profil | Budget CPU | Budget GPU | Limite GPU |
|---|---:|---:|---:|
| faible | 64 Mio | 96 Mio | 128 textures |
| compact | 128 Mio | 128 Mio | 128 textures |
| équilibré | 128 Mio | 192 Mio | 128 textures |
| élevé | 192 Mio | 256 Mio | 128 textures |

Un hit GPU ne consulte pas le cache CPU simulé. Un miss GPU prédit un upload et consulte le cache
CPU indépendant ; seul un miss CPU prédit une lecture du fichier RGBA. Les modèles publient les
frames distinctes, hits, misses, évictions, frames trop grosses, octets prédits et résidences
instantanées/de pointe. Une perte de contexte vide uniquement leur résidence GPU. Un changement de
zone détruit tous les modèles.

Ce lot n’effectue aucune lecture, aucun hash, aucun upload et aucune éviction réelle. Il ne modifie
ni le chargement intégral des packs, ni le cache réel de 64 textures, ni le registre v1/v2/v3. Sa
capacité de métadonnées est bornée à 16 384 frames ; un pack dépassant cette borne désactive la
simulation sans désactiver le rendu x4.

Validation automatisée avant installation :

- DLL Windows Release compilée ;
- `ctest -C Release` : 2/2 tests C++ réussis ;
- tests Python communs : 180/180 réussis ;
- tests des budgets en octets, évictions multiples, limite de noms GPU, frame non cachable,
  indépendance CPU/GPU et perte de contexte ;
- DLL candidate SHA-256
  `D4542D29C59E2F51D87AED785676C6E35AAF4303862456FFA6FE3DD1E0406C86`.

Installation réversible :

- état :
  `bg2hd/state/animation-cache-budget-simulation-20260829T001508Z/` ;
- seule `InfinityEngine-Enhancer.dll` diffère du runtime précédent ;
- DLL active SHA-256
  `D4542D29C59E2F51D87AED785676C6E35AAF4303862456FFA6FE3DD1E0406C86` ;
- restauration vers la DLL SHA-256
  `7898B87F57D747E5CA7DC76E11AA66FC106CC1E45F71467D98AE1D476E12BA35` ;
- `PerformanceLogs=true` et `EnableTilePageDiagnostics=false` restent actifs pour la mesure.

### Première session du quatrième lot P1

Session du 2026-08-29, parcours AR0700 → AR0516 → AR0900 → AR0602. Les valeurs ci-dessous sont
les octets d’upload cumulés, réels pour le cache de 64 textures et prédits par chaque simulation :

| Zone | Frames distinctes | Cache réel 64 | 64/96 | 128/128 | 128/192 | 192/256 | Facteur limitant observé |
|---|---:|---:|---:|---:|---:|---:|---|
| AR0700, final | 57 | 50,48 Mio | 50,48 Mio | 50,48 Mio | 50,48 Mio | 50,48 Mio | Aucun dans ce parcours |
| AR0516, final | 137 | 361,62 Mio | 359,27 Mio | 328,81 Mio | 251,46 Mio | 233,71 Mio | Budget GPU ; limite de 128 atteinte |
| AR0900, final | 80 | 2 264,41 Mio | 2 264,41 Mio | 2 264,41 Mio | 2 242,69 Mio | 215,09 Mio | Budget GPU supérieur au jeu actif de 215,09 Mio |
| AR0602, snapshot à 10 s | 160 | 881,98 Mio | 438,36 Mio | 438,36 Mio | 438,36 Mio | 438,36 Mio | Limite de 128 textures, pas le budget en octets |

Les 56 snapshots des modèles respectent les invariants attendus : les hits et misses GPU couvrent
toutes les requêtes, chaque miss GPU consulte exactement une fois le modèle CPU et aucune frame
n’est déclarée non cachable. Aucun échec de création ou d’upload réel n’est observé. La seule
alerte de la session est la récupération attendue du prologue `RenderTexture` détourné par EEex.

AR0900 met en évidence un seuil net : ses 80 frames distinctes occupent 215,09 Mio. Les budgets
GPU de 96, 128 et 192 Mio renouvellent cycliquement presque tout le jeu actif, alors que 256 Mio
permettent un seul upload par frame. Cette observation dépend de la trace des frames mais pas de la
vitesse du disque ou du GPU de la machine de test.

AR0602 met en évidence un autre seuil : ses 160 frames distinctes n’occupent que 104,14 Mio côté
CPU simulé, mais les quatre profils restent limités à 128 noms GPU. Augmenter le seul budget en
octets ne réduit donc pas leurs 671 uploads prédits sur ce snapshot. AR0516 dépasse également
légèrement cette limite avec 137 frames distinctes.

Ce premier jeu de profils ne permet donc pas encore de retenir une politique générale. Il faut
d’abord isoler les variables avec au minimum un profil CPU 128 Mio / GPU 256 Mio / 192 textures,
accompagné d’un profil à 128 Mio GPU / 192 textures pour mesurer séparément l’effet de la limite
en nombre d’entrées. Le profil 192/256 actuel sert de contrôle haut, mais ne prouve pas que
192 Mio de cache CPU soient nécessaires.

### Raffinement ciblé des profils

La grille suivante remplace les quatre profils initiaux dans la DLL candidate :

| Rôle | Budget CPU | Budget GPU | Limite GPU |
|---|---:|---:|---:|
| contrôle faible | 64 Mio | 96 Mio | 128 textures |
| contrôle compact initial | 128 Mio | 128 Mio | 128 textures |
| isolation de la limite d’entrées | 128 Mio | 128 Mio | 192 textures |
| candidat généraliste | 128 Mio | 256 Mio | 192 textures |
| contrôle du budget CPU | 192 Mio | 256 Mio | 192 textures |

Les deux profils 128/128 ne diffèrent que par leur limite GPU ; les deux profils 128/256 et
192/256 ne diffèrent que par leur budget CPU. La comparaison ingame pourra donc attribuer les
écarts sans confondre ces deux variables. Le profil intermédiaire 128/192 initial est retiré :
AR0900 a déjà démontré avec seulement 80 frames que 192 Mio GPU restent sous son jeu actif de
215,09 Mio.

Validation et installation :

- DLL Windows Release compilée ;
- `ctest -C Release` : 2/2 tests C++ réussis dans les builds de test et DLL ;
- tests Python communs : 180/180 réussis ;
- seul l’avertissement tiers `C4459` déjà connu dans `spdlog/fmt` est émis ;
- DLL candidate SHA-256
  `BD9B2AC1D95A055A687A1FD9168E64A1AA4DA1A62E10F0053A2F52B889F1C87F`.

Installation réversible :

- état :
  `bg2hd/state/animation-cache-budget-profile-refinement-20260829T003323Z/` ;
- seule `InfinityEngine-Enhancer.dll` diffère du runtime précédent ;
- les sept fichiers renderer suivis correspondent à leurs hashes attendus ;
- DLL active SHA-256
  `BD9B2AC1D95A055A687A1FD9168E64A1AA4DA1A62E10F0053A2F52B889F1C87F` ;
- restauration vers la DLL SHA-256
  `D4542D29C59E2F51D87AED785676C6E35AAF4303862456FFA6FE3DD1E0406C86` ;
- `PerformanceLogs=true` et `EnableTilePageDiagnostics=false` restent actifs.

### Seconde session du quatrième lot P1

Session du 2026-08-29, parcours AR0700 → AR0516 → AR0900 → AR0602. AR0700, AR0516 et
AR0900 disposent d’un bilan final au changement de pack. AR0602 dispose de deux snapshots
périodiques identiques après activité ; ils sont suffisants pour comparer les profils, même sans
bilan de sortie de zone.

| Zone | Upload réel, cache 64 | Upload prédit 128/256/192 | Réduction prédite | Frames distinctes / misses candidat | Évictions candidat |
|---|---:|---:|---:|---:|---:|
| AR0700 | 50,48 Mio | 50,48 Mio | 0 % | 57 / 57 | 0 |
| AR0516 | 428,39 Mio | 317,97 Mio | 25,8 % | 171 / 182 | 36 |
| AR0900 | 1 519,58 Mio | 215,09 Mio | 85,8 % | 80 / 80 | 0 |
| AR0602, snapshot | 244,33 Mio | 103,56 Mio | 57,6 % | 159 / 159 | 0 |

Les 60 snapshots respectent tous les invariants du modèle et aucune frame n’est non cachable.
Aucun échec réel de création ou d’upload n’est observé. La seule alerte est la récupération EEex
attendue du prologue `RenderTexture`.

La comparaison 128 Mio GPU / 128 entrées contre 128 Mio GPU / 192 entrées isole correctement la
limite de noms. Sur AR0602, elle réduit les uploads prédits de 150,02 à 103,56 Mio et supprime les
96 évictions ; sur AR0516 et AR0900, le budget en octets est atteint avant la limite d’entrées et
les deux profils restent identiques.

La comparaison CPU 128 Mio contre 192 Mio, à GPU 256 Mio / 192 entrées, produit exactement les
mêmes lectures, uploads et misses sur les quatre zones. Le budget CPU de 192 Mio est donc écarté :
il conserve davantage de buffers sans éviter une seule lecture sur cette trace. Le budget CPU de
128 Mio reste une borne d’étude, pas encore une valeur de production ; les zéros hits observés avec
le candidat justifient de mesurer aussi la possibilité de libérer rapidement le buffer CPU après
upload.

Le candidat GPU de 256 Mio constitue un compromis borné, pas un cache capable de retenir toutes
les frames de toutes les zones. AR0516 dépasse encore cette borne : 171 frames distinctes donnent
182 misses, soit 11 rechargements, et 36 évictions. Augmenter immédiatement la borne jusqu’au pack
complet de 385,89 Mio poursuivrait le zéro-éviction au prix d’un réglage moins généraliste ; ce
troisième raffinement n’est pas retenu sans mesure mémoire externe.

## Cinquième petit lot expérimental P1

Avec `PerformanceLogs=true`, le runtime capture désormais les compteurs Windows du processus sans
modifier le contenu chargé ni le comportement du renderer :

- `WorkingSetSize`, `PeakWorkingSetSize` et `PrivateUsage` via `GetProcessMemoryInfo` ;
- défauts de page cumulés exposés par le même snapshot ;
- opérations et octets de lecture/écriture cumulés via `GetProcessIoCounters`.

La préparation de chaque pack prend trois snapshots : avant toute lecture, juste avant l’échange
quand l’ancien et le nouveau pack coexistent, puis après l’échange et la destruction du pack
sortant. Une ligne dédiée publie les trois valeurs de Working Set et de mémoire privée, ainsi que
les deltas de défauts de page et d’I/O sur toute la préparation.

Les rapports périodiques de cinq secondes publient la mémoire courante et les deltas depuis la
fenêtre précédente. Les appels système ne sont donc pas ajoutés au hot path par frame. Les
compteurs restent strictement derrière `PerformanceLogs=true` ; les plateformes non prises en
charge publient des indicateurs de disponibilité faux au lieu de valeurs inventées.

Limites d’interprétation :

- `PrivateUsage` représente l’engagement privé du processus, pas uniquement les buffers x4 ;
- le Working Set dépend des décisions de résidence de Windows et peut rester élevé après une
  libération logique ;
- `GetProcessIoCounters` agrège toutes les I/O attribuées au processus ; il n'est ni spécifique
  aux fichiers, ni capable de distinguer cache fichier et lecture physique ;
- le snapshot `PageFaultCount` ne sépare pas les différentes catégories de défauts de page ;
- aucune API OpenGL portable disponible dans ce runtime ne fournit l’allocation VRAM réelle du
  processus. Les octets de base GPU internes restent une estimation distincte.

Validation avant installation :

- DLL Windows Release compilée ;
- `ctest -C Release` : 2/2 tests C++ réussis dans les builds de test et DLL ;
- tests Python communs : 180/180 réussis ;
- tests des snapshots Windows, des trois gates du pack, des deltas signés bornés et des compteurs
  monotones ;
- seul l’avertissement tiers `C4459` déjà connu dans `spdlog/fmt` est émis ;
- DLL installée SHA-256
  `81A3F41D59F2355732DBDC9D206ADA55F7661DBF29248B045E4BA26EA025FEC0` ;
- rollback vérifié vers la DLL précédente SHA-256
  `BD9B2AC1D95A055A687A1FD9168E64A1AA4DA1A62E10F0053A2F52B889F1C87F` ;
- état réversible : `bg2hd/state/process-resource-telemetry-20260829T005859Z/`.

Mesure ingame du 29 août 2026 :

| Zone | Pack entrant | Pack sortant | Working Set avant | Coexistence | Après échange | Delta brut attendu | Delta WS observé | Chargement |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| AR0700 | 99,10 Mio | 0 Mio | 283,48 Mio | 381,58 Mio | 381,58 Mio | +99,10 Mio | +98,10 Mio | 588,33 ms |
| AR0516 | 385,89 Mio | 99,10 Mio | 427,12 Mio | 813,66 Mio | 716,32 Mio | +286,80 Mio | +289,20 Mio | 2 335,12 ms |
| AR0900 | 215,09 Mio | 385,89 Mio | 760,50 Mio | 975,78 Mio | 589,24 Mio | −170,80 Mio | −171,26 Mio | 1 214,78 ms |
| AR0602 | 104,30 Mio | 215,09 Mio | 590,64 Mio | 694,21 Mio | 478,93 Mio | −110,80 Mio | −111,71 Mio | 4 649,99 ms |

Les quatre mesures publient `memoryAvailable=true` et `ioAvailable=true`. Pour chaque zone,
`readTransferBytesDelta` est exactement égal à `registryBytes + frameBytes`, ce qui attribue la
lecture logique au chargement intégral du pack. L’écart maximal entre le delta brut attendu et le
delta du Working Set n’est que de 2,40 Mio : les buffers RGBA expliquent donc directement la
résidence RAM observée aux gates de chargement.

Le pic périodique de mémoire privée atteint 1 879,73 Mio, nettement au-dessus du pic de Working Set
de 975,78 Mio. Sa variation inclut le moteur, le pilote et les autres ressources ; elle ne doit pas
servir seule à dimensionner le cache x4. Le delta privé d’AR0602 est notamment de −360,02 Mio pour
un delta brut attendu de −110,80 Mio, preuve que d’autres libérations ont lieu pendant la
transition.

Cette session ne contient qu’un passage et n’est donc pas un A/B froid/chaud. Les durées de lecture
ne permettent pas de distinguer cache fichier et disque physique ; elles ne doivent pas être
interprétées comme une régression du diagnostic, dont le coût propre se limite à trois snapshots
Windows par chargement et un snapshot toutes les cinq secondes. Zéro erreur, zéro compteur
indisponible et zéro échec de chargement ou d’upload ont été relevés. L’unique avertissement est la
récupération attendue du prologue `RenderTexture` déjà détourné par EEex.

## Sixième petit lot passif P1

L’inventaire local trouve `wpr.exe` avec les profils `FileIO`, `GPU` et `ResidentSet`, mais pas WPA,
GPUView ni RAMMap. La session Codex n’est pas élevée ; une capture ETW formelle et l’installation du
Windows Performance Toolkit demanderaient donc une intervention administrateur. Avant cette étape
plus lourde, les compteurs de performances Windows déjà présents offrent un recoupement passif :

- `GPU Process Memory` : dédié, partagé, local, non local et engagement total par PID ;
- `GPU Adapter Memory` : usage dédié, partagé et engagement global ;
- `LogicalDisk` : lectures et écritures du volume du jeu ;
- `Memory` et `Cache` : cache système, listes standby, lectures de pages et taux de présence.

Le nouveau script
`engine/InfinityEngine-Enhancer/source-patchee/tools/Capture-BG2HD-ProcessResources.ps1` attend les
processus `Baldur`/`BaldurReal` appartenant au dossier du jeu, échantillonne depuis un processus
séparé, écrit CSV + métadonnées + statut, puis s’arrête après la fermeture du jeu. Il ne touche ni
au runtime ni aux fichiers installés.

Deux auto-tests de trois secondes réussissent. Le test avec un processus GPU réel publie des
compteurs non nuls et cohérents ; le coût stabilisé du helper est de 10,7 à 14,3 ms par seconde,
avec 56,9 ms au premier échantillon. Cette durée est mesurée dans le processus externe, pas dans le
thread de rendu. Le CSV l’enregistre à chaque ligne afin d’écarter une session trop intrusive.

Limite : Microsoft documente un ancien cas de surcomptage de `GPU Process Memory` sous Windows 10.
La capture doit donc comparer tendances, deltas et télémétrie interne ; elle ne constitue pas à
elle seule une preuve de fuite VRAM. WPR/WPA reste le recours si les compteurs se contredisent.

### Capture ingame externe

Capture du 29 août 2026, 156 échantillons à une seconde, avec ComfyUI laissé ouvert mais inactif
comme pendant les sessions précédentes. Le parcours AR0700 → AR0516 → AR0900 → AR0602 a été joué
deux fois dans le même processus. Le helper a consommé en moyenne 20,85 ms par échantillon, avec
27,72 ms au percentile 95 et 59,29 ms au maximum ; ce coût reste dans un processus séparé du
renderer.

| Zone | Pack logique | Chargement passage 1 | Chargement passage 2 | Lecture du volume autour du chargement, P1 / P2 |
|---|---:|---:|---:|---:|
| AR0700 | 99,10 Mio | 65,00 ms | 68,81 ms | 0,18 / 1,32 Mio |
| AR0516 | 385,89 Mio | 255,22 ms | 246,16 ms | 0 / 0,12 Mio |
| AR0900 | 215,09 Mio | 147,71 ms | 146,81 ms | 0,13 / 0 Mio |
| AR0602 | 104,30 Mio | 77,63 ms | 77,45 ms | 0 / 0 Mio |

Les huit deltas `readTransferBytesDelta` du processus restent exactement égaux aux registres et
frames des packs. En revanche, les fenêtres externes de trois à quatre secondes ne voient au plus
que 1,32 Mio lu sur le volume `G:`. Les taux de présence du cache par copie sont compris entre
81,43 et 100 %, avec 100 % sur cinq transitions. Le premier passage était donc déjà chaud ; le
second n’est pas systématiquement plus rapide et ne change jamais une durée de plus de 9,06 ms.
Cette session attribue solidement les temps observés à la copie/allocation de données mises en
cache, mais ne remplace pas un futur essai réellement froid sur une autre machine.

| Zone | WDDM dédié stable P1 | WDDM dédié stable P2 | Pic WDDM P1 / P2 | Pic interne animations P1 / P2 |
|---|---:|---:|---:|---:|
| AR0700 | 586,78 Mio | 591,34 Mio | 586,78 / 591,34 Mio | 50,48 / 50,48 Mio |
| AR0516 | 309,75 Mio | 310,70 Mio | 565,06 / 633,27 Mio | 112,73 / 113,40 Mio |
| AR0900 | 536,55 Mio | 648,36 Mio | 850,23 / 868,35 Mio | 172,93 / 172,71 Mio |
| AR0602 | 252,61 Mio | 258,44 Mio | 374,99 / 382,01 Mio | 50,44 / 48,66 Mio |

Le WDDM dédié mesure tout le processus BG2, alors que le compteur interne ne suit que les niveaux
de base des textures d’animations : leurs valeurs absolues ne doivent pas être soustraites ni
confondues. Le dédié et le local WDDM sont identiques pendant toute la capture ; le non-local et le
partagé culminent à 38,26 Mio. L’usage dédié global de l’adaptateur varie de 7 869,60 à
8 734,54 Mio, soit +864,94 Mio, à seulement 3,41 Mio du pic dédié attribué au jeu. Cela recoupe le
compteur par processus malgré ComfyUI et les autres consommateurs présents.

AR0900 termine 111,81 Mio plus haut au second passage, mais cet écart retombe à 5,83 Mio dès
AR0602 ; il ne s’agit donc pas d’une croissance persistante sur le parcours. Aucun échec de
chargement, création ou upload n’est relevé. Le seul avertissement de la session est la récupération
attendue du prologue `RenderTexture` déjà détourné par EEex.

Le recoupement n’apporte aucune contradiction nécessitant une capture ETW plus lourde. WPA,
GPUView et RAMMap ne sont donc pas installés à ce stade. La borne candidate 256 Mio / 192 textures
reste une limite explicite du futur cache d’animations, et non une valeur déduite des 32 Gio de la
carte de test.

## Mini-lot carte 1 — attribution du burst de dezoom

Avec `PerformanceLogs=true`, le runtime observe une fois par frame les dimensions de la vue monde.
Le build initial commence une capture si largeur et hauteur augmentent toutes deux d’au moins 25 %
entre deux observations. Ce seuil sert à isoler une ouverture/dezoom de carte sans dépendre d’une
résolution d’écran ou d’un modèle de GPU particulier.

Le runtime conserve en mémoire la frame déclencheuse et les sept frames de présentation suivantes.
Il n’écrit qu’une seule ligne INFO une fois la capture complète, sous le marqueur
`Map wide-view burst telemetry`. Chaque échantillon contient :

- l’index et le numéro de frame, les dimensions de vue, leur indicateur d’observation fraîche et
  l’intervalle de présentation ;
- le temps CPU cumulé dans `RenderTexture` pendant la frame ;
- les deltas de dessins de tuiles et de nouvelles pages de table/textures sources observées ;
- les appels et octets d’uploads compressés, le sous-ensemble des grandes bases S3TC, ainsi que les
  appels de suppression et noms de textures supprimés.

Les compteurs GL restent des données de corrélation : les chemins BAM V2 et MOS V2 peuvent produire
les mêmes appels. Ce lot ne retarde, ne précharge et n’évince aucune tuile ; il ne modifie ni TIS,
WED, PVRZ, packs, animations, budgets ni manifests. `PerformanceLogs=false` désactive entièrement
la collecte. Un changement de zone réinitialise la baseline par une requête atomique consommée sur
le thread de rendu.

Validation automatisée du source :

- build natif de `iee_tests` réussi ;
- `ctest -C Debug` : 2/2 tests réussis ;
- DLL Windows Release et bundle compilés ;
- DLL candidate SHA-256
  `7F41266DCF50C5253B65B7170EF31302E1C7D56F0540B6C601C494C4CFCD272E` ;
- seul l’avertissement tiers `C4459` déjà documenté dans `spdlog/fmt` subsiste.

Installation réversible :

- état : `bg2hd/state/map-wide-view-telemetry-20260829T051717Z/` ;
- seule `InfinityEngine-Enhancer.dll` diffère du runtime précédent ;
- DLL active SHA-256
  `7F41266DCF50C5253B65B7170EF31302E1C7D56F0540B6C601C494C4CFCD272E` ;
- restauration vers la DLL SHA-256
  `81A3F41D59F2355732DBDC9D206ADA55F7661DBF29248B045E4BA26EA025FEC0` ;
- `PerformanceLogs=true` et `EnableTilePageDiagnostics=false` restent actifs.

### Première session ingame

Session du 29 août 2026, AR0602 → AR0700N → AR0516 → AR0900. L’utilisateur signale la saccade la
plus forte sur AR0900. Les deltas ci-dessous sont ceux de la fenêtre où les pages supplémentaires
de la vue carte apparaissent ; les maxima excluent le chargement initial de la zone.

| Zone | Pages carte supplémentaires | Appels compressés supplémentaires | Upload compressé | Frame maximale | Capture détaillée |
|---|---:|---:|---:|---:|---|
| AR0602 | 34 | 37 | 68,50 Mio | 20,75 ms | Non |
| AR0700N | 85 | 85 | 340,00 Mio | 404,68 ms | Oui |
| AR0516 | 28 | 30 | 56,25 Mio | 14,35 ms | Non |
| AR0900 | 20 | 21 | 320,25 Mio | 374,57 ms | Oui |

La capture AR0700N attribue les trois frames lourdes à 84,01, 250,13 et 404,68 ms, avec 9, 27
et 45 nouvelles pages et respectivement 36, 108 et 180 Mio d’uploads compressés. La capture AR0900
mesure 150,60, 374,57 et 192,00 ms, avec 4, 10 et 5 nouvelles pages et 64, 160 et 80 Mio. AR0900
utilise donc moins de pages, mais chaque base PVRZ 4096 DXT5 représente 16 Mio dans l’appel GL ;
AR0700N répartit un volume total voisin sur davantage de pages 2048.

Le temps CPU propre au détour `RenderTexture` ne dépasse que 3,02 ms sur les trois frames lourdes
d’AR0700N et 5,33 ms sur celles d’AR0900. Il est très inférieur aux intervalles de présentation :
le hook de tuiles n’est pas la source principale du gel. Le corrélat dominant est la matérialisation
et l’upload compressé synchrones des pages demandées par le dezoom.

AR0900 présente aussi un amplificateur secondaire dans la même fenêtre de cinq secondes : 135
uploads de textures d’animations, 362,66 Mio de niveaux de base et 71 évictions LRU. AR0700N
n’ajoute qu’environ 48,92 Mio et aucune éviction. Ces compteurs ne permettent pas encore une
attribution par frame, mais ils sont cohérents avec le ressenti plus sévère sur AR0900 sans retirer
le rôle principal du burst PVRZ.

AR0602 et AR0516 sont visibles dans les deltas cumulatifs, mais ne produisent pas de ligne détaillée.
Leur dezoom s’effectue par incréments dont chacun reste sous le seuil de 25 % entre deux frames.
Le déclencheur doit donc comparer la vue à une baseline stable ou à une courte fenêtre, plutôt qu’à
la seule frame précédente. Aucun échec moteur n’est relevé ; les deux avertissements sont la
récupération attendue du prologue déjà détourné par EEex et le fallback de teinte WLAKE00 déjà connu.

### Raffinement 1b — dezoom progressif

Le déclencheur compare désormais la vue courante à l’observation qualifiante la plus récente parmi
les seize dernières frames de présentation. L’historique est un tableau fixe, sans allocation, et
les observations plus anciennes sont oubliées. Dès qu’une capture commence, la baseline antérieure
est supprimée. Le buffer de sortie reste limité à huit frames et le seuil reste à 1,25. Le retest
montre cependant que, si le dezoom continue après ces huit frames, les nouvelles vues peuvent
former une autre baseline et déclencher une capture supplémentaire.

Validation automatisée avant installation :

- expansion directe et expansion cumulative en trois incréments couvertes ;
- absence de redéclenchement lorsque la carte reste ouverte ;
- rejet d’une baseline âgée de plus de seize frames ;
- remise à zéro des compteurs sans sous-flux conservée ;
- `ctest -C Debug` : 2/2 tests réussis ;
- DLL Windows Release compilée, SHA-256
  `8E15A17614B0F9C607036CA02972DE61C7A1658C93F934965C41D43C101334ED` ;
- tests Python communs : 180/180 réussis après fermeture de BG2 et InfinityLoader ; leur premier
  passage avait été correctement refusé par onze tests d’installation pendant que le jeu tournait.

Installation réversible :

- état : `bg2hd/state/map-wide-view-cumulative-telemetry-20260829T054633Z/` ;
- seule `InfinityEngine-Enhancer.dll` diffère du runtime précédent ;
- DLL active SHA-256
  `8E15A17614B0F9C607036CA02972DE61C7A1658C93F934965C41D43C101334ED` ;
- restauration vers la DLL SHA-256
  `7F41266DCF50C5253B65B7170EF31302E1C7D56F0540B6C601C494C4CFCD272E` ;
- `PerformanceLogs=true` et `EnableTilePageDiagnostics=false` restent actifs.

### Retest ciblé du raffinement 1b

Session du 29 août 2026, AR0602 puis AR0516. Les deux dezooms progressifs sont désormais détectés,
mais chacun produit quatre événements pendant une seule ouverture :

| Zone | Événements | Intervalle premier-dernier | Frames couvertes | Nouvelles pages cumulées | Frame maximale |
|---|---:|---:|---:|---:|---:|
| AR0602 | 4 | 237 ms | 5547–5578 | 32 | 21,01 ms |
| AR0516 | 4 | 211 ms | 11810–11841 | 30 | 19,09 ms |

Les dimensions augmentent continûment d’un événement au suivant. Les trois premières captures de
chaque zone couvrent l’essentiel des nouvelles pages ; la quatrième n’en relève aucune sur AR0602
et une seule sur AR0516. Il ne s’agit donc ni de quatre ouvertures distinctes ni d’un faux marqueur
en vue monde stable : le détecteur se réarme implicitement lorsque son buffer de huit frames est
terminé alors que l’animation de dezoom continue. Aucun autre marqueur n’apparaît dans la fin de la
session. L’unique avertissement est la récupération attendue du prologue `RenderTexture` déjà
détourné par EEex ; aucune erreur ou alerte critique n’est émise.

Le raffinement 1b valide la fenêtre cumulative de seize frames pour la couverture, mais échoue la
gate « une capture par ouverture ». Il ne doit pas être considéré comme terminé.

### Raffinement 1c — verrou de réarmement

Après un déclenchement, le détecteur mémorise la vue pré-dezoom et reste désarmé pendant toute
l’expansion. Il ne reconstruit pas d’historique dans cet état. Le réarmement n’est autorisé que
lorsque largeur et hauteur se sont toutes deux contractées sous la baseline pré-dezoom multipliée
par le seuil existant de 1,25. Une seconde ouverture peut alors produire un nouvel événement.

Validation automatisée avant installation :

- un dezoom continu dépassant les huit frames du buffer ne produit qu’une capture ;
- une contraction complète suivie d’une seconde ouverture produit l’événement 2 ;
- les expansions directe et cumulative, la fenêtre fixe et les remises à zéro restent couvertes ;
- `ctest -C Debug` et `ctest -C Release` : 2/2 tests réussis ;
- tests Python communs : 180/180 réussis ;
- seul l’avertissement tiers `C4459` déjà documenté dans `spdlog/fmt` subsiste ;
- DLL Windows Release SHA-256
  `BBE9E9BEBAB1ED22D1009FD2F14948566DBB617A1B0B1324456E224C0002D71B`.

Installation réversible :

- état : `bg2hd/state/map-wide-view-rearm-telemetry-20260829T060046Z/` ;
- seule `InfinityEngine-Enhancer.dll` diffère du runtime précédent ;
- restauration vers la DLL 1b SHA-256
  `8E15A17614B0F9C607036CA02972DE61C7A1658C93F934965C41D43C101334ED` ;
- `PerformanceLogs=true` et `EnableTilePageDiagnostics=false` restent actifs.

### Retest ingame du raffinement 1c

Session du 29 août 2026, lancée via `InfinityLoader.lnk`, dans l’ordre AR0700N → AR0516 → AR0602
→ AR0900. Pour chaque sauvegarde : stabilisation de cinq secondes, ouverture de la carte pendant
cinq secondes, fermeture et contraction pendant cinq secondes, puis seconde ouverture de cinq
secondes et fermeture. Le jeu a ensuite été quitté sans écrire de sauvegarde.

| Zone | Événements | Pic présentation ouverture 1 | Nouvelles pages ouverture 1 | Upload compressé ouverture 1 | Pic présentation ouverture 2 |
|---|---:|---:|---:|---:|---:|
| AR0700N | 1, 2 | 431,91 ms | 82 | 328,25 Mio | 6,20 ms |
| AR0516 | 1, 2 | 15,11 ms | 9 | 18,00 Mio | 6,36 ms |
| AR0602 | 1, 2 | 8,04 ms | 7 | 14,00 Mio | 6,60 ms |
| AR0900 | 1, 2 | 303,69 ms | 18 | 288,00 Mio | 6,46 ms |

Chaque zone produit exactement deux marqueurs pour deux ouvertures. Aucun événement supplémentaire
n’apparaît pendant le maintien de la carte. Les quatre secondes ouvertures ne créent aucune page,
aucune texture source et aucun upload compressé dans la fenêtre capturée : le pic mesuré est donc
lié à la matérialisation initiale des pages demandées par le dezoom, tandis que leur réaffichage
depuis la résidence existante reste proche de 6 ms sur cette session.

Le classement des premières ouvertures n’est pas un benchmark froid : les zones ont été parcourues
dans un même processus et le cache fichier Windows était déjà chaud. Il confirme néanmoins deux
bursts lourds distincts, AR0700N à 431,91 ms et AR0900 à 303,69 ms. Le temps CPU maximal du détour
`RenderTexture` reste limité à 3,57 ms sur AR0700N et 5,57 ms sur AR0900, très loin des pics de
présentation.

La session ne contient aucune erreur ni alerte critique. Son seul avertissement est la récupération
attendue du prologue `RenderTexture` déjà détourné par EEex. Le correctif satisfait donc la gate
« une capture par ouverture » sans modifier les formats, les packs, les animations, les tuiles ou
les manifests.

## Mini-lot carte 2 — phases de `CResPVR::Demand`

Le binaire BG2EE 2.7.3 ciblé contient une implémentation unique de `CResPVR::Demand` à la RVA
`0x3F6DC0`. Cette adresse et son prologue validé sont maintenant portés par le manifeste de build.
Avec `PerformanceLogs=true`, et uniquement pour cette cible exacte, le runtime installe un détour
d’observation qui mesure :

- la durée totale de chaque demande PVR et si elle matérialise réellement une texture ;
- les deltas d’opérations et d’octets de lecture du processus pendant cette matérialisation ;
- les appels et durées imbriqués de génération de nom de texture puis d’upload compressé ;
- le résidu après retrait de ces deux phases GL, ainsi que la resref matérialisée la plus lente de
  chaque frame capturée.

Le résidu n’est volontairement **pas** nommé « décompression » : il contient encore la recherche
de ressource, le service des lectures, la préparation zlib/PVR et la comptabilité moteur. Les
deltas I/O sont une corrélation au niveau du processus, pas un chronométrage du fichier individuel.
La collecte utilise un scope local au thread et des buffers fixes. Un prologue, une version ou une
preuve de manifeste non conformes omettent le diagnostic et laissent le rendu natif continuer.

Ce mini-lot ne change ni l’ordre des demandes, ni le cache natif de 128 pages, ni les uploads, TIS,
WED, PVRZ, packs, animations, budgets ou manifests de contenu. `PerformanceLogs=false` conserve le
chemin intégral antérieur sans installer le détour.

Validation avant installation :

- validation hors ligne du binaire 2.7.3 et de la nouvelle signature réussie ;
- builds Debug et Release réussis ;
- `ctest -C Debug` puis `ctest -C Release`, exécutés séquentiellement : 2/2 tests réussis dans les
  deux configurations ;
- tests Python communs : 180/180 réussis ;
- DLL Windows Release SHA-256
  `E169E9B0D303C830314C0B0A88B3E67848AA68FB2287BAFF908F9C0A45D5A6AC`.

Installation réversible :

- état : `bg2hd/state/map-pvr-demand-phase-telemetry-20260829T064935Z/` ;
- phase `installed`, avec sauvegarde de la DLL précédente ;
- DLL active SHA-256
  `E169E9B0D303C830314C0B0A88B3E67848AA68FB2287BAFF908F9C0A45D5A6AC` ;
- restauration vers la DLL du raffinement 1c SHA-256
  `BBE9E9BEBAB1ED22D1009FD2F14948566DBB617A1B0B1324456E224C0002D71B` ;
- `PerformanceLogs=true` et `EnableTilePageDiagnostics=false` restent actifs.

### Session ingame des phases PVR

Session du 29 août 2026, lancée via `InfinityLoader.lnk`, dans le même ordre que le retest 1c :
AR0700N → AR0516 → AR0602 → AR0900. Chaque zone suit le protocole cinq secondes stable, cinq
secondes carte ouverte, cinq secondes fermée, puis une seconde ouverture et une seconde fermeture.
Le jeu est quitté sans sauvegarder.

| Zone | Pages carte ouverture 1 | Upload corrélé | Pic présentation | Matérialisations PVR | Lectures corrélées | `Demand` cumulé | Upload GL mesuré | Résidu cumulé | PVR la plus lente |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| AR0700N | 84 | 336,25 Mio | 839,29 ms | 85 | 111,57 Mio | 1 173,46 ms | 31,23 ms | 1 140,67 ms | `A0700N61`, 2048², 15,42 ms |
| AR0516 | 30 | 60,00 Mio | 82,24 ms | 30 | 21,69 Mio | 296,96 ms | 7,19 ms | 289,18 ms | `A051635`, 2048², 11,66 ms |
| AR0602 | 31 | 62,00 Mio | 102,26 ms | 31 | 25,31 Mio | 308,55 ms | 7,02 ms | 301,14 ms | `A060224`, 2048², 11,89 ms |
| AR0900 | 18 | 288,00 Mio | 414,77 ms | 18 | 102,92 Mio | 740,04 ms | 18,84 ms | 720,85 ms | `A090014`, 4096², 45,63 ms |

Le nombre de pages de carte et celui des matérialisations PVR ne sont pas des identités : les
premiers proviennent du hook TIS/table, les secondes couvrent toute demande PVR dans la fenêtre.
L’écart d’une unité sur AR0700N est donc conservé au lieu d’être artificiellement réattribué.

Sur la frame la plus lourde de chaque première ouverture, `CResPVR::Demand` représente environ 95 à
98 % du temps de présentation : 819,98/839,29 ms sur AR0700N, 78,14/82,24 ms sur AR0516,
98,09/102,26 ms sur AR0602 et 404,01/414,77 ms sur AR0900. La génération de noms GL est inférieure
à 1,2 ms par burst. L’upload compressé mesuré reste lui aussi minoritaire — 1,94 à 22,25 ms sur les
frames de pic — tandis que le résidu de `Demand` en porte 75,99 à 796,54 ms. Le gel est donc dans la
matérialisation synchrone en amont ou autour de l’upload, pas dans le hook de dessin et pas dans
`glGenTextures`.

AR0900 reste le cas structurel le plus coûteux par page : ses PVRZ 4096² demandent jusqu’à 45,63 ms
chacune, contre 11,66 à 15,42 ms pour les pages 2048² des autres zones. AR0700N produit toutefois le
plus gros pic agrégé de cette session, car il matérialise 85 PVR et passe en premier dans le
processus. Ce parcours à cache fichier non contrôlé ne doit pas servir de classement froid entre
zones ; il explique pourquoi le ressenti utilisateur sur AR0900 et le maximum agrégé d’AR0700N ne
sont pas contradictoires.

Les quatre secondes ouvertures ne matérialisent aucune PVR, ne lisent aucun octet corrélé et
restent entre 6,26 et 6,44 ms au pic. Le problème concerne donc l’arrivée initiale des pages dans la
résidence moteur, pas le simple affichage répété d’une carte déjà chaude.

La session ne contient aucune erreur ni alerte critique. Son seul avertissement est la récupération
attendue du prologue `RenderTexture` déjà détourné par EEex.

## Mini-lot carte 3 — préchauffage progressif des pages de carte

Ce lot répond directement à l’attribution du mini-lot 2 : si `CResPVR::Demand` porte 95 à 98 % des
frames de pic, le levier n’est pas de rendre la demande plus rapide mais de ne plus la subir en
bloc pendant la frame d’ouverture.

Le module `src/iee/map_page_prewarm.cpp` planifie les pages PVRZ de la carte courante et les demande
lui-même, quelques-unes par frame, **après** la présentation. Il ne change aucun format, aucun
contenu, ni la politique de cache du moteur.

Contrat retenu :

- opt-in strict : `[Rendering] EnableMapPagePrewarm=false` par défaut ; le lot exige en plus
  `PerformanceLogs=true`, car sa garde d’éviction s’appuie sur la télémétrie de suppression GL.
  Sans elle le module refuse de s’armer et le journalise ;
- exécution sur le thread de rendu après le swap, hors de tout dessin en cours ;
- plan borné à 96 pages sur les 128 entrées PVR natives relevées, soit **32 entrées laissées en
  réserve** au cache moteur. C’est la réponse à la réserve inscrite dans la version précédente de
  ce document : ne pas chasser la vue monde du cache natif ;
- `MapPagePrewarmDelayFrames=30`, `MapPagePrewarmPagesPerFrame=1`, `MapPagePrewarmBudgetMs=8.0`,
  tous configurables et bornés à la lecture de l’INI ;
- identité revalidée avant **et** après chaque `Demand` : wrapper de tuile, tileset, index de tuile
  et resref de page. Toute divergence annule le plan ;
- annulation sur changement de zone, de contexte GL, ou dès la **première éviction observée** ;
- toute page non planifiée ou non matérialisée suit le `Demand` natif synchrone, inchangé.

Validation automatisée : la DLL et la cible de test compilent ; `ctest -C Debug` passe 2/2. Les
réglages sont couverts par quatre blocs de tests natifs — analyse INI, bornes, valeurs par défaut
et aller-retour de sauvegarde.

### Première session ingame

Journal du 2026-08-29, DLL installée à 09:42:20, `EnableMapPagePrewarm=true`.

| Zone | Pages découvertes | Planifiées | Écartées | Demandes | Matérialisations | Évictions | `totalDemandMs` | `maximumDemandMs` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| AR0700N | 100 | 96 | 4 | 81 | 81 | **0** | 790,95 | 15,20 |
| AR0516 | 44 | 44 | 0 | 32 | 32 | **0** | 181,65 | 11,01 |
| AR0602 | 45 | 45 | 0 | 34 | 34 | **0** | 200,40 | 7,18 |
| AR0900 | 26 | 26 | 0 | 19 | 19 | **0** | 745,80 | 43,77 |

Aucun candidat invalide, aucune éviction, aucun plan annulé. La garde principale du lot n’a jamais
eu à se déclencher sur ces quatre zones.

Pic de présentation à la première ouverture de carte, événement 1 :

| Zone | Avant, pics observés | Pages chargées pendant le pic | Après | Pages |
|---|---|---:|---:|---:|
| AR0700N | 404,7 / 431,9 / 839,3 ms | 81 / 82 / 84 | **7,6 ms** | 17 |
| AR0516 | 19,1 / 15,1 / 82,2 ms | 9 / 9 / 30 | **6,3 ms** | 6 |
| AR0602 | 6,9 / 8,0 / 102,3 ms | 6 / 7 / 31 | **6,7 ms** | 7 |
| AR0900 | 374,6 / 369,9 / 303,7 / 414,8 ms | 19 / 18 / 18 / 18 | — | — |

### Limites de cette session

Ces chiffres décrivent une première session, pas un résultat validé :

- **ce n’est pas un A/B contrôlé.** Les mesures « avant » viennent de sessions antérieures dont le
  cache fichier Windows n’était pas maîtrisé. La dispersion le montre : AR0516 va de 15,1 à 82,2 ms
  et AR0602 de 6,9 à 102,3 ms selon que 9 ou 30 pages restaient à matérialiser. Seul AR0700N offre
  une comparaison froide non ambiguë, avec 81 à 84 pages avant contre 17 après ;
- **AR0900 est incomplète.** Le préchauffage y a bien tourné, mais aucune ouverture de carte n’a été
  capturée ensuite. C’est justement la zone la plus coûteuse par page ;
- **le budget de 8 ms est contrôlé après le retour de `Demand`.** Une page lente traverse donc
  encore la frame : `maximumDemandMs` atteint 43,77 ms sur AR0900, dont les PVRZ sont en 4096².
  Le pic est déplacé et fortement réduit, il n’est pas supprimé ;
- **le coût total n’est pas supprimé non plus**, il est étalé : les 790,95 ms de demande d’AR0700N
  sont répartis sur environ 1,1 s de frames au lieu d’une seule frame bloquante ;
- aucun instantané de restauration n’a été enregistré sous `bg2hd/state/` pour ce build, alors que
  chaque runtime expérimental précédent en possède un. Le dernier état documenté reste
  `map-pvr-demand-phase-telemetry-20260829T064935Z`, c’est-à-dire le build antérieur.

Ce lot n’est pas éligible à la release et aucun manifeste de release n’a été modifié.

## Prochaine étape

La campagne suivante doit produire l’A/B contrôlé qui manque, en une seule session par état et sur
la même machine, avec les quatre sauvegardes dédiées `AR0700N`, `AR0516`, `AR0602` et `AR0900` :

1. session de référence, `EnableMapPagePrewarm=false` : charger les quatre sauvegardes à la suite
   et dézoomer complètement dans chacune, en relevant l’événement 1 et l’événement 2 ;
2. session de mesure, `EnableMapPagePrewarm=true` : répéter exactement le même parcours, dans le
   même ordre, sans redémarrer la machine entre les deux ;
3. comparer par zone le pic de présentation, le nombre de pages matérialisées pendant le burst, les
   évictions et le `maximumDemandMs` du préchauffage.

L’ordre de passage doit être conservé entre les deux sessions : le cache fichier Windows favorise
la zone traitée en second, et c’est précisément ce biais qui rend la session actuelle non
concluante en dehors d’AR0700N.

Deux points restent à traiter ensuite, indépendamment du résultat :

- déplacer le contrôle du budget **avant** l’appel plutôt qu’après, ou borner le nombre de pages
  par frame en fonction du coût observé de la page précédente, afin que le cas 4096² d’AR0900 ne
  puisse plus produire une frame à 43,77 ms ;
- enregistrer un instantané de restauration sous `bg2hd/state/` pour ce build, afin de rétablir la
  chaîne d’états que le reste de ce document documente.

Pour le futur lot animations, les contraintes restent inchangées : chargement intégral actuel en
fallback, formats de packs et animations inchangés, budgets initiaux de 128 Mio CPU et 256 Mio /
192 textures GPU configurables. Ces bornes expérimentales ne doivent pas devenir des constantes
dépendantes de la RTX 5090 et ne sont pas transposées implicitement au cache de pages de carte.
