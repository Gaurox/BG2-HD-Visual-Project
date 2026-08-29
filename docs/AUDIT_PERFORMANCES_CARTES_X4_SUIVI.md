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
et le chargement intégral des packs restent inchangés.

Le runtime expérimental courant est installé localement de manière réversible avec son état
distinct sous `bg2hd/state/animation-cache-budget-simulation-20260829T001508Z/`. Sa restauration
revient au build validé de télémétrie du cache GPU, dont les états précédents conservent la chaîne
de retour jusqu’au build P0 de rotation des logs. Il n’est pas éligible à la release et aucun
manifeste de release n’a été modifié.

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
| P1 | Simuler passivement différents budgets CPU/GPU | Premier jeu de profils mesuré ingame | Les quatre modèles sont cohérents et sans erreur. AR0900 exige plus de 215 Mio GPU pour éviter le churn observé, tandis qu’AR0602 bute sur la limite de 128 textures malgré seulement 104 Mio distincts. Raffiner les profils avant de choisir un budget. |
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

## Prochaine étape

Le P0, les trois premiers lots de télémétrie P1 et le retrait des logs INFO par frame sont validés.
Le premier jeu de budgets est mesuré ingame. La prochaine gate prudente est un raffinement limité
du simulateur : relever la limite GPU à 192 textures sur des profils choisis et tester explicitement
le couple CPU 128 Mio / GPU 256 Mio. Un second parcours identique permettra de vérifier si ce
profil couvre les quatre zones sans surdimensionner le cache CPU. Aucune politique réelle de
chargement à la demande ne doit être activée avant cette mesure. Une mesure externe du Working Set,
du cache fichier et idéalement de la VRAM restera nécessaire avant l’A/B de l’implémentation réelle,
sans transformer les timings de cette machine en constantes universelles.
