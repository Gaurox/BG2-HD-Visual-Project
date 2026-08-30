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

La campagne cache OS chaud contrebalancée A-B-B-A du 2026-08-30 est maintenant terminée sur les
quatre zones. Elle confirme le levier : les médianes de première ouverture passent de 454,11 à
6,08 ms sur AR0700N et de 299,62 à 6,90 ms sur AR0900 ; aucune matérialisation PVR n’apparaît dans
les bursts B1/B2, contre 83 et 18 dans les bursts A1/A2 correspondants. Les deux parcours B ne
produisent aucune éviction du préchauffage. Cette validation porte uniquement sur la campagne
chaude de cette machine ; le candidat reste expérimental et non éligible à la release tant que le
pic unitaire 4096² d’AR0900 et la restauration transactionnelle ne sont pas traités.

Le runtime expérimental courant est le mini-lot carte 3. Le DLL installé localement est le candidat
ingame exact SHA-256
`9FCE57D11ACF2DD6539B7A263B6DE1A70C44F6F41981181793CA6AA785FCC98E`, avec
`PerformanceLogs=true`, `EnableTilePageDiagnostics=false` et `EnableMapPagePrewarm=true`. Son
dernier instantané est
`bg2hd/state/map-page-prewarm-wed-identity-20260829T094250Z/`. Il n’est pas éligible à la release
et aucun manifeste de release n’a été modifié.

## Gel technique du candidat — 2026-08-30

La reprise de l’étape 1 a été effectuée jeu et InfinityLoader fermés, sur le commit dépôt
`cffc1d129a99df7bf0100b01f97a5fd41ab9cb05`. Le sous-arbre moteur n’a pas changé depuis le commit
qui a introduit le prototype,
`dbc724b063825b309f784cc8a5acd19dcf3fe56b`. L’identité de référence pour le futur A/B est :

- **binaire réellement mesuré et encore installé** : 1 434 112 octets, SHA-256
  `9FCE57D11ACF2DD6539B7A263B6DE1A70C44F6F41981181793CA6AA785FCC98E`, horodaté localement le
  2026-08-29 à 09:42:20 ;
- **configuration réellement mesurée** : 2 238 octets, SHA-256
  `B7B391539DA4A31DA71684D9809AD416E6BDFAEE21AAFE89A0482A7AC4EDE8B5` ;
- **source moteur** : commit `dbc724b063825b309f784cc8a5acd19dcf3fe56b`, identique dans le
  commit de reprise `cffc1d129a99df7bf0100b01f97a5fd41ab9cb05` ;
- **reconstruction propre du 2026-08-30** : Visual Studio 2019 Build Tools, générateur CMake
  `Visual Studio 16 2019`, plateforme x64, toolset v142, SDK `10.0.19041.0`, DLL Release de
  1 434 112 octets, SHA-256
  `25648942F6DBF0DF9CC52CDF7488DD2D026C417DF891E2B94C75A448A8580BD3`.

Le SHA de la reconstruction propre diffère du DLL installé. Cette différence interdit de présenter
la reconstruction comme le binaire exact de la première session : le candidat A/B reste donc gelé
par le SHA `9FCE…`, tandis que `2564…` constitue uniquement la preuve qu’un build propre du même
sous-arbre source réussit. Aucun DLL n’a été réinstallé pendant cette reprise.

Gates rejouées sur la reconstruction propre :

- builds Debug et Release réussis ;
- `ctest -C Debug` et `ctest -C Release` : 2/2 tests réussis dans chaque configuration ;
- tests Python communs : 180/180 réussis ;
- validation hors ligne de `BaldurReal.exe` réussie : 7 202 696 octets, SHA-256
  `b51093a49140b2b8a7c046b4652bb8e535be24ebbc12b1d735e0b94217a14d57`, signatures, onze
  callsites et offsets attendus conformes au manifeste moteur.

### Chaîne de restauration vérifiée hors ligne

Les hashes des fichiers actifs, des sauvegardes et du dernier état transactionnel donnent la chaîne
LIFO suivante :

| DLL à retirer | Instantané à appliquer | DLL restaurée |
|---|---|---|
| `9FCE57D1…` | `map-page-prewarm-wed-identity-20260829T094250Z` | `2F8A030F…` |
| `2F8A030F…` | `map-page-prewarm-diagnostic-20260829T093741Z` | `AA2A09FB…` |
| `AA2A09FB…` | `map-page-prewarm-rearm-20260829T093256Z` | `A9EC0998…` |
| `A9EC0998…` | `map-page-prewarm-prototype-20260829T072353Z` | `E169E9B0…` |
| `E169E9B0…` | état transactionnel `map-pvr-demand-phase-telemetry-20260829T064935Z` | `BBE9E9BE…` |

Les quatre instantanés `map-page-prewarm-*` contiennent des copies brutes DLL/INI, sans
`renderer-files.json`, phase transactionnelle ni outil de restauration dédié. Leur présence, leur
intégrité et leur ordre sont vérifiés, mais une restauration réelle n’a volontairement pas été
simulée dans le dossier du jeu : elle ne serait pas fail-closed comme l’état renderer précédent.
Avant toute réinstallation du candidat, il faut donc créer un état transactionnel propre ou figer
une procédure LIFO avec contrôles de SHA avant et après chaque copie. L’installation courante est
restée inchangée.

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
| P1 | Préchargement progressif des pages de carte | A/B chaud validé ingame, non promu | Campagne A-B-B-A sur les quatre zones : aucune matérialisation PVR dans les bursts B1/B2 et zéro éviction du préchauffage. Médianes A/B : AR0700N 454,11/6,08 ms ; AR0516 16,21/6,25 ms ; AR0602 8,09/6,17 ms ; AR0900 299,62/6,90 ms. Restent le pic unitaire 4096² à ~44 ms et la restauration transactionnelle avant toute promotion. |
| P2/P3 | Réduire l'unité PVRZ atomique d'AR0900 | Repagination 2112² mesurée puis rejetée | 90 pages block-exact sous le plafond de 96 ; `maximumDemandMs` 43,97 → 15,22 ms et ouvertures à 6,33/6,63 ms sans matérialisation. La gate 8 ms reste manquée et aucune page carrée uniforme plus petite ne tient sous le plafond. État antérieur restauré. |
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

Validation automatisée initiale : la DLL et la cible de test compilent ; `ctest -C Debug` passe
2/2. Les réglages sont couverts par quatre blocs de tests natifs — analyse INI, bornes, valeurs par
défaut et aller-retour de sauvegarde. La reprise du 2026-08-30 a ensuite rejoué avec succès les
builds et les 2/2 tests en Debug puis en Release, ainsi que les 180 tests Python communs et la
validation hors ligne du manifeste moteur.

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

| Zone | Références : pics observés | Références : nouvelles pages table | Session préchauffée : pic | Session préchauffée : nouvelles pages table |
|---|---|---:|---:|---:|
| AR0700N | 404,7 / 431,9 / 839,3 ms | 81 / 82 / 84 | **7,6 ms** | 17 |
| AR0516 | 19,1 / 15,1 / 82,2 ms | 9 / 9 / 30 | **6,3 ms** | 6 |
| AR0602 | 6,9 / 8,0 / 102,3 ms | 6 / 7 / 31 | **6,7 ms** | 7 |
| AR0900 | 374,6 / 369,9 / 303,7 / 414,8 ms | 19 / 18 / 18 / 18 | — | — |

Les deux colonnes « nouvelles pages table » reprennent `newTablePages` du détecteur de burst. Elles
ne comptent ni des lectures disque, ni des uploads, ni des matérialisations PVR pendant la frame et
ne doivent plus être nommées « pages chargées ». Les traces de phases PVR restent la source pour
compter les matérialisations réelles.

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
- un instantané existe finalement sous
  `bg2hd/state/map-page-prewarm-wed-identity-20260829T094250Z/`. Il restaure le DLL
  `2F8A030F…`, et trois instantanés bruts supplémentaires permettent de revenir au DLL
  transactionnel `E169E9B0…`. Ces quatre états intermédiaires n’ont toutefois ni manifeste, ni
  phase, ni restauration automatisée fail-closed ; leur chaîne est vérifiée par SHA mais reste à
  formaliser avant une opération réelle.

Ce lot n’est pas éligible à la release et aucun manifeste de release n’a été modifié.

### Point d’arrêt historique du 2026-08-29 — mesure AR0900 bloquée

La campagne ci-dessus n’a pas pu être lancée et la mesure manquante d’AR0900 n’a pas été prise.
Le blocage est d’accès, pas technique : l’agent n’a pas obtenu le contrôle de la fenêtre de jeu
(quatre demandes refusées, la réponse revenant immédiatement, ce qui évoque un refus mémorisé
plutôt qu’une décision prise à chaque appel) et l’opérateur pilotait depuis un téléphone, sans
possibilité de manipuler le jeu. Aucun contournement n’a été tenté.

État de la machine au moment de l’arrêt, à conserver pour la reprise :

- BG2EE tourne sans interruption depuis le 2026-08-29 09:43:06 (`BaldurReal`, `InfinityLoader`),
  avec le build du mini-lot carte 3 installé à 09:42:20 ;
- `EnableMapPagePrewarm = true` et `PerformanceLogs = true` dans l’INI du jeu, tel que laissé par
  la session de mesure. L’INI a été basculé sur `false` puis **restauré à l’identique** ; il n’a
  de toute façon aucun effet sur une session déjà lancée ;
- repère dans le journal : 11 039 311 octets. Tout événement postérieur est nouveau. Ce repère
  devient caduc si la rotation à 16 Mio se déclenche ; le critère robuste reste l’horodatage, toute
  ouverture de carte AR0900 postérieure à 09:43 étant postérieure à l’installation du préchauffage.

Manipulation minimale qui complète la matrice actuelle, sans rien réinstaller ni relancer :

1. charger la sauvegarde dédiée `AR0900` ;
2. **attendre environ trois secondes** avant toute action. Le préchauffage démarre 30 frames après
   le chargement puis traite une page par frame ; dézoomer plus tôt mesurerait un état partiel ;
3. dézoomer à fond, ce qui produit l’événement 1 ;
4. rezoomer puis redézoomer à fond, ce qui produit l’événement 2, contrôle interne « carte déjà
   chaude ».

Cette manipulation ne remplace pas l’A/B en deux sessions décrit ci-dessus : elle complète la
première session, avec les mêmes réserves de cache fichier non maîtrisé.

Une inference circule et ne doit pas être confondue avec une mesure : le préchauffage d’AR0900 a
matérialisé 19 pages sur 19 sans éviction, et les trois autres zones dans cet état ont donné 6,3 à
7,6 ms au pic. AR0900 tomberait donc vraisemblablement dans cette plage, contre 303,7 à 414,8 ms
avant. **Ce raisonnement n’est pas un résultat** : le tableau conserve son tiret tant que la frame
n’a pas été observée.

Enfin, un rappel pour la reprise : jeu ouvert, la suite Python commune rapporte 18 échecs qui sont
tous environnementaux. Chacun de ces tests appelle un installateur qui refuse fail-closed sur un
processus BG2EE vivant. Fermer le jeu avant d’exécuter la gate, sous peine de diagnostiquer un faux
défaut.

### État revalidé le 2026-08-30

- `Baldur`, `BaldurReal` et `InfinityLoader` sont fermés ; la session historique décrite ci-dessus
  est donc terminée ;
- le DLL `9FCE57D1…` et l’INI `B7B39153…` sont toujours installés sans modification ;
- la mesure AR0900 reste absente. La manipulation « sans rien réinstaller ni relancer » n’est plus
  applicable ; AR0900 doit désormais entrer dans la campagne A/B complète ;
- les gates C++, Python et manifeste moteur passent jeu fermé ; les 18 échecs environnementaux ne
  se reproduisent pas.

## Campagne chaude contrebalancée A-B-B-A — 2026-08-30

La campagne demandée a été exécutée via `InfinityLoader.lnk` avec le DLL candidat inchangé,
SHA-256 `9FCE57D11ACF2DD6539B7A263B6DE1A70C44F6F41981181793CA6AA785FCC98E`.
Un passage de chauffe explicite a précédé quatre nouveaux processus, dans l’ordre A-B-B-A, avec
les zones toujours parcourues dans l’ordre AR0700N → AR0516 → AR0602 → AR0900. Chaque zone a été
stabilisée, ouverte en carte dézoomée, refermée, puis ouverte et refermée une seconde fois.

Les preuves brutes sont conservées hors dépôt sous
`G:\AI\BG2_Upscale-data\performance-audit\map-page-prewarm-abba-hot-cache-20260830T110700\`.
Les journaux sont cumulatifs ; les bornes ci-dessous sont donc les débuts de session à utiliser,
et non le début physique de chaque fichier :

| Parcours | Réglage | Borne de session | Fin observée | SHA-256 du journal | SHA-256 de l’INI |
|---|---|---|---|---|---|
| A1 | `false` | 11:07:37.929 | 11:19:59.229 | `47DB639C5900D122B3DD21E8E0F4CBB65046F88A3BD47F8D6EAA86B2055FC01F` | `77676158CD7B8F498F328EBB9A507F3A04EC6F479120B4B8D1F7BCFD7C028684` |
| B1 | `true` | 11:20:52.255 | 11:31:48.310 | `04802F5E0E7384ED0BAF8779A6DB03BA9D0AF18A4E0AF689AF7DA8AD29476F93` | `B7B391539DA4A31DA71684D9809AD416E6BDFAEE21AAFE89A0482A7AC4EDE8B5` |
| B2 | `true` | 11:33:27.158 | 11:45:23.378 | `BB2F2B99D8D6CA2369F719160D078D2F1F9F1F3FC71E1A11BFFD2A6115E87084` | `B7B391539DA4A31DA71684D9809AD416E6BDFAEE21AAFE89A0482A7AC4EDE8B5` |
| A2 | `false` | 11:46:20.444 | 11:58:51.886 | `092FFF1CE800B61D6BCA20F079EED342810DB68EDFDFAA4E40D879D0C8555FC6` | `77676158CD7B8F498F328EBB9A507F3A04EC6F479120B4B8D1F7BCFD7C028684` |

Le passage de chauffe est lui aussi archivé : journal
`51534E4F930A8AA0DE1E0E0132697520F7B023043C1AFBE74D80B8464FA6FFAA`, INI `true`
`B7B39153…`. Après la campagne, le jeu et InfinityLoader sont fermés et l’INI actif est restauré
à `EnableMapPagePrewarm=true`, SHA-256 `B7B39153…`.

Deux déviations opératoires sont explicitement conservées. Au début d’A1, une sauvegarde rapide a
été écrasée accidentellement ; les quatre sauvegardes dédiées AR0700N, AR0516, AR0602 et AR0900
sont restées intactes et tous les chargements mesurés utilisent ces sauvegardes nommées. A2
contient aussi un troisième événement chaud sur AR0602 après les deux ouvertures prévues. Cet
événement 3, exclu des tableaux, culmine à 6,09 ms et compte zéro nouvelle page de table, zéro
matérialisation PVR et zéro suppression de nom de texture. Les événements 1 et 2 d’AR0602 avaient
déjà été capturés intégralement ; aucun autre parcours ni aucune autre zone ne présente
d’événement supplémentaire.

### Résultat sur la première ouverture

Le pic est le maximum des huit frames du marqueur `Map wide-view burst telemetry`, et les
matérialisations viennent du marqueur `Map PVR demand phase telemetry` correspondant. La réduction
compare les médianes des deux A et des deux B ; avec deux échantillons, la « dispersion » indiquée
est simplement l’écart absolu entre les deux parcours.

| Zone | A1 | A2 | Médiane A | B1 | B2 | Médiane B | Réduction médiane | Matérialisations A1/A2 → B1/B2 | Dispersion A / B |
|---|---:|---:|---:|---:|---:|---:|---:|---|---:|
| AR0700N | 433,46 ms | 474,75 ms | **454,11 ms** | 6,11 ms | 6,05 ms | **6,08 ms** | **98,66 %** | 83 / 83 → 0 / 0 | 41,29 / 0,06 ms |
| AR0516 | 16,60 ms | 15,81 ms | **16,21 ms** | 6,08 ms | 6,41 ms | **6,25 ms** | **61,46 %** | 9 / 9 → 0 / 0 | 0,79 / 0,33 ms |
| AR0602 | 8,19 ms | 7,99 ms | **8,09 ms** | 6,25 ms | 6,08 ms | **6,17 ms** | **23,79 %** | 7 / 7 → 0 / 0 | 0,20 / 0,17 ms |
| AR0900 | 293,42 ms | 305,81 ms | **299,62 ms** | 6,02 ms | 7,78 ms | **6,90 ms** | **97,70 %** | 18 / 18 → 0 / 0 | 12,39 / 1,76 ms |

Les secondes ouvertures de tous les parcours comptent zéro matérialisation PVR et zéro suppression
de nom de texture. Leurs pics restent proches du plancher de présentation : 6,02 à 6,43 ms, sauf
A2/AR0602 à 6,73 ms et A2/AR0900 à 8,92 ms. Le dernier écart ne contient toujours aucune
matérialisation PVR ; il ne remet donc pas en cause l’attribution du gel initial.

Les `newTablePages` de B restent non nuls — 16/17 sur AR0700N, 6/6 sur AR0516, 7/6 sur AR0602 et
3/3 sur AR0900 — mais les marqueurs de phase prouvent qu’elles ne matérialisent aucune PVR et
n’effectuent aucun upload compressé. Comme établi plus haut, ce compteur observe les nouvelles
pages rencontrées par le hook TIS/table ; il ne mesure pas leur résidence.

### Coût déplacé dans le préchauffage

| Zone | Matérialisations B1/B2 | Évictions B1/B2 | `totalDemandMs` B1 / B2 | Médiane totale | `maximumDemandMs` B1 / B2 | Médiane maximale |
|---|---:|---:|---:|---:|---:|---:|
| AR0700N | 81 / 81 | **0 / 0** | 856,19 / 816,75 ms | 836,47 ms | 16,10 / 16,26 ms | 16,18 ms |
| AR0516 | 32 / 32 | **0 / 0** | 188,14 / 185,58 ms | 186,86 ms | 10,69 / 10,63 ms | 10,66 ms |
| AR0602 | 34 / 34 | **0 / 0** | 194,12 / 190,04 ms | 192,08 ms | 7,12 / 6,44 ms | 6,78 ms |
| AR0900 | 19 / 19 | **0 / 0** | 745,41 / 746,69 ms | 746,05 ms | 43,85 / 44,09 ms | **43,97 ms** |

Le coût PVR n’est donc pas supprimé : il est déplacé après le chargement de zone et étalé sur des
frames successives. Aucun candidat invalide, aucune annulation de plan et aucune éviction du cache
natif ne sont relevés. Chaque session contient zéro erreur et une seule alerte, identique et déjà
attendue : récupération du prologue `RenderTexture` détourné par EEex.

### Verdict et prochaines étapes

La gate de performance cache OS chaud est **validée ingame**. Le préchauffage élimine de manière
répétée le burst PVR de première ouverture, y compris sur AR0900, sans éviction observée. Le gain
est structurel sur AR0700N et AR0900, significatif sur AR0516, et logiquement plus faible sur
AR0602 dont la référence chaude était déjà proche du plancher de présentation.

Ce verdict ne rend pas le prototype éligible à la release. Les prochaines étapes sont :

1. créer un nouveau candidat qui contrôle le budget **avant** la demande suivante, ou adapte le
   nombre de pages à partir du coût de la page précédente, afin de borner le cas 4096² d’AR0900 qui
   atteint encore 43,97 ms en médiane maximale pendant le préchauffage ;
2. remplacer la chaîne d’instantanés bruts par une installation/restauration transactionnelle et
   fail-closed pour le DLL exact, sans écraser l’état renderer historique ;
3. revalider le nouveau candidat au minimum sur AR0900, puis sur les quatre zones pour la
   non-régression, avec le chargement natif synchrone conservé comme fallback ;
4. si une preuve cache OS froid est requise, mener une campagne distincte et contrebalancée sur
   plusieurs redémarrages de la machine, sans la mélanger aux résultats chauds ci-dessus.

Pour le futur lot animations, les contraintes restent inchangées : chargement intégral actuel en
fallback, formats de packs et animations inchangés, budgets initiaux de 128 Mio CPU et 256 Mio /
192 textures GPU configurables. Ces bornes expérimentales ne doivent pas devenir des constantes
dépendantes de la RTX 5090 et ne sont pas transposées implicitement au cache de pages de carte.

## Étape 3 — repack Deflate stocké d’AR0900 — 2026-08-30

L’analyse du candidat de préchauffage corrige d’abord l’hypothèse formulée à l’étape précédente.
Avec `MapPagePrewarmPagesPerFrame=1`, l’ordonnanceur espace déjà les pages au maximum. Le budget est
nécessairement constaté après le retour de `CResPVR::Demand`, qui reste un appel synchrone et
atomique. Contrôler le budget avant la page suivante ou adapter le nombre de pages à partir de la
précédente peut éviter d’enchaîner plusieurs demandes, mais ne peut pas borner la demande 4096²
elle-même. Aucun faux correctif d’ordonnancement n’a donc été produit.

L’essai a porté à la place sur l’encapsulation PVRZ. Le nouvel outil opt-in
`pipeline/scripts/repack_pvrz_compression.py` copie le TIS à l’identique, décompresse chaque PVRZ,
réécrit seulement son flux zlib au niveau demandé, puis refuse la sortie si le PVR décodé n’est pas
strictement identique. La source n’est jamais modifiée et le dossier de sortie doit être absent.

Une incohérence de source a été détectée avant l’installation. `areas.csv` désigne encore
`05_build/x4-water-alpha-antialias-page4096/` comme build actif d’AR0900, mais les 27 fichiers de
l’`override` correspondaient exactement, SHA-256 par SHA-256, au sous-build
`05_build/x4-water-alpha-antialias-page4096-spline-fit1.0/`. Le premier candidat, créé depuis le
chemin déclaré par le catalogue, a été rejeté sans installation. Le candidat mesuré a été recréé
depuis le sous-build réellement installé. Le catalogue n’a pas été modifié pendant cet essai.

### Qualification hors ligne

Le candidat correct conserve :

- `AR0900.TIS` octet pour octet, SHA-256
  `4671AE969FDAC1AF919D1D4B887E8581BC4DC6513A727CD73775A1D1E14696F8` ;
- les 26 PVR décodés octet pour octet ;
- 5 752 tuiles, zéro référence hors limites, une image rendue de 20 480 × 15 360 et le PSNR de
  contrôle à 34,75 dB.

Le niveau zlib 0 remplace les blocs comprimés par des blocs stockés. Sur les 26 pages, il fait
passer le payload PVRZ de 151,73 à 416,03 Mio, soit +264,30 Mio, ×2,7419 ou +174,19 %. Un benchmark
séquentiel hors jeu, à cache fichier chaud, passe de 1 308,76 à 342,05 ms au total ; la médiane par
page passe de 45,86 à 12,51 ms et le maximum de 83,75 à 18,93 ms. Ces valeurs orientent l’essai mais
ne remplacent pas la mesure moteur.

Le manifeste exact est conservé sous
`G:\AI\BG2_Upscale-data\performance-audit\map-page-prewarm-stored-deflate-20260830T121938\candidate-active-spline-fit1.0\repack-manifest.json`,
SHA-256 `ECE44A20FA330BDBA08A78E0AFCD421A19B59455904ACB0BD385AD177E2C4382`.

### Mesure ingame ciblée

Jeu et InfinityLoader fermés, l’injection a sauvegardé les 27 fichiers actifs sous
`G:\AI\BG2_Upscale\backups\maps\AR0900-20260830-122401\`, puis vérifié zéro divergence entre le
candidat et l’`override`. La session a été lancée via InfinityLoader, la sauvegarde dédiée AR0900
a été chargée, le préchauffage a été laissé finir, puis la carte entièrement dézoomée a été ouverte
et refermée deux fois.

| Mesure AR0900 | Référence B1/B2, médiane | Deflate stocké | Évolution |
|---|---:|---:|---:|
| `totalDemandMs`, 19 matérialisations | 746,05 ms | 228,97 ms | −69,31 % |
| `maximumDemandMs` | 43,97 ms | 12,77 ms | −70,96 % |
| Pic événement 1 | 6,90 ms | 6,10 ms | aucune matérialisation PVR |
| Pic événement 2 | 6,02–8,92 ms dans la campagne | 6,33 ms | aucune matérialisation PVR |
| Évictions du préchauffage | 0 | 0 | inchangé |

Le log confirme 26 pages découvertes et planifiées, 7 déjà résidentes, 19 demandes et 19
matérialisations, sans candidat invalide ni éviction. Les deux ouvertures comptent zéro lecture,
zéro matérialisation PVR et zéro upload PVR compressé dans leur burst. Aucune anomalie graphique
n’a été observée. La session contient zéro erreur et uniquement l’avertissement déjà connu de
récupération du prologue `RenderTexture` détourné par EEex.

Le journal complet est archivé sous
`G:\AI\BG2_Upscale-data\performance-audit\map-page-prewarm-stored-deflate-20260830T121938\post-run\InfinityEngine-Enhancer.log`,
borne de session `2026-08-30 12:24:50.135`, SHA-256
`D96AF8BD8A9AF0C43EB432B141D49869FD105E44B1F66A7DD12538497D4352F3`.

### Verdict et restauration

L’essai est **rejeté comme solution globale**. Il prouve que la décompression Deflate porte une
part importante du résidu de la demande 4096², mais il manque encore la cible de 8 ms de 4,77 ms
et son surcoût de 174,19 % ne concerne que la variante jour d’une seule zone. Une régression sur
AR0700N, AR0516 et AR0602 n’aurait testé aucun octet différent : ni le moteur ni leurs fichiers
n’ont changé. Elle n’a donc pas été lancée après l’échec de la gate AR0900.

Après fermeture du jeu et d’InfinityLoader, les 27 fichiers de la sauvegarde ont été restaurés.
Le contrôle final donne zéro divergence avec la sauvegarde et zéro divergence avec le sous-build
actif antérieur ; le seul fichier encore identique au candidat est le TIS, volontairement inchangé
par le repack. L’INI reste à son SHA-256 antérieur `B7B39153…`. Le candidat et ses preuves restent
hors dépôt, sans statut `validated-installed`. Aucun manifeste de release, staging ou package n’a
été modifié.

Les suites utiles sont maintenant :

1. formaliser l’installation/restauration transactionnelle et fail-closed des candidats moteur et
   maps, y compris un reçu de hashes avant toute copie ;
2. mesurer un candidat qui réduit réellement l’unité atomique sous 8 ms, par exemple une
   pagination plus petite ou hybride compatible avec la limite de resref nocturne, la réserve de
   32 entrées et le plafond actuel de 96 pages ;
3. si le moteur doit dépasser cette voie de contenu, isoler puis déplacer la lecture/décompression
   hors de la frame avant de réintégrer l’upload GL sur le thread propriétaire du contexte ;
4. ne relancer la matrice des quatre zones qu’après réussite de la gate ciblée AR0900.

## Étape 3b — installation transactionnelle des builds maps — 2026-08-30

La chaîne d'injection TIS/PVRZ a été remplacée par un installateur/restaurateur fail-closed dans
`pipeline/scripts/inject_build.py`. Cette sous-étape est une modification de tooling testée sur des
fixtures isolées : aucun fichier de l'installation réelle du jeu n'a été écrit et aucun candidat
n'a reçu de statut de QA.

Le nouveau contrat impose, avant toute copie :

- jeu et InfinityLoader fermés ;
- un TIS V1 au nom exact de la zone et l'ensemble exact des PVRZ qu'il référence ;
- la validation des flux zlib et de leur taille PVR décodée ;
- l'inventaire de toutes les pages déjà présentes dans le namespace de la zone, y compris celles
  qui deviendront obsolètes.

Un dossier unique sous `backups/maps/` contient `install-backup.json` et la copie vérifiée de chaque
fichier initialement présent. Le reçu enregistre les SHA-256 individuels, les empreintes agrégées des
états initial et installé, ainsi que les pages retirées. Il est publié avec le statut `prepared`
avant la première mutation de l'`override`. Les copies passent par un fichier temporaire puis un
remplacement atomique ; chaque cible est revérifiée juste avant sa mutation et l'inventaire complet
est revérifié après installation.

En cas d'échec, le rollback automatique remet l'état initial. Une interruption pendant
l'installation ou la restauration laisse un statut reprenable (`prepared`, `restoring` ou
`recovery-required`). La restauration refuse un reçu altéré, une sauvegarde corrompue, une autre
racine de jeu ou une cible dont le hash n'est ni l'état initial ni l'état installé attendu. Elle ne
dépend pas de la présence du build source.

Neuf tests automatisés couvrent l'aller-retour exact avec retrait d'une page obsolète, l'inventaire
source incomplet, la divergence de cible ou de namespace, le rollback après échec partiel, la reprise
d'installation, la reprise de restauration, l'altération du reçu et le refus lorsque le jeu ou
InfinityLoader est actif.

Cette étape ferme le risque transactionnel pour les **builds maps**. Elle ne transforme pas les
quatre sauvegardes brutes du DLL moteur en reçus ; ce travail reste distinct avant une promotion du
candidat moteur. La prochaine expérience de contenu peut maintenant construire puis prévalider un
candidat AR0900 à pages plus petites ou hybrides, sous le plafond de 96 pages et les contraintes de
resref nocturne, avant toute installation contrôlée.

## Étape 3c — repagination DXT exacte 2112² d'AR0900 — 2026-08-30

Le nouvel outil opt-in `pipeline/scripts/repage_pvrz_blocks.py` repagine un build TIS/PVRZ sans
décoder ni réencoder son image. Pour chaque entrée TIS, il copie les blocs DXT de la tuile avec son
padding répliqué de quatre pixels, puis réécrit uniquement le numéro de page et les coordonnées du
TIS. La sortie est relue avant publication et chaque cellule est comparée octet pour octet à sa
source. Le dossier source reste en lecture seule et la sortie doit être absente.

AR0900 contient 5 752 tuiles de 256 px. Avec le padding, une cellule occupe 264 px ; une page de
2 112 px contient donc 8 × 8 cellules, soit 64 tuiles, et la zone tient en 90 pages. Ce choix est le
plus petit carré compatible avec le plafond actuel de 96 pages : 1 848 px ne contient que 7 × 7
cellules et exigerait 118 pages. Les dimensions 2112² n'étant pas une puissance de deux, la
compatibilité a été traitée comme une gate ingame obligatoire.

### Qualification hors ligne

Le candidat a été créé depuis le sous-build réellement installé
`x4-water-alpha-antialias-page4096-spline-fit1.0`, pas depuis le chemin divergent encore déclaré
par `areas.csv`. Il conserve :

- les 5 752 cellules DXT, padding inclus, octet pour octet ; empreinte agrégée
  `791C69E51FB469FF32C95D5430C432902FEFA4DBF1008A5B0F0043B7ED009E82` ;
- 5 752 tuiles, zéro référence hors limites, un rendu de 20 480 × 15 360 et le PSNR de contrôle à
  34,75 dB ;
- un inventaire fermé de 90 pages 2112², sous le plafond de 96 et sous la capacité de nommage.

Le payload PVRZ passe de 159 103 866 à 155 778 416 octets, soit 151,73 à 148,56 Mio (-2,09 %).
Le benchmark Python zlib à cache mémoire chaud, sept itérations après warm-up, fait passer la
médiane d'une page de 59,24 à 15,63 ms. Le maximum par itération est trop bruité pour servir de
gate moteur, mais passe de 115,59 à 52,06 ms. Une dérivée zlib niveau 1 a été écartée hors jeu :
165,21 Mio (+11,2 %) et une médiane par page d'environ 18,51 ms, contre 15,71 ms pour le niveau 9
dans la même série.

La prévalidation de l'installateur transactionnel a accepté les 91 fichiers du candidat sans
écriture. Le manifeste exact est conservé sous
`G:\AI\BG2_Upscale-data\performance-audit\map-page-repage-2112-20260830T130630\candidate-ar0900-day\repage-manifest.json`,
SHA-256 `3F895C65101EA0F5863C5A015C46C68EE781F84FFA2B9696F906B4C83821CF8A`.

### Mesure ingame ciblée

Jeu et InfinityLoader fermés, l'installation transactionnelle a sauvegardé les 27 fichiers actifs,
installé 91 fichiers et vérifié l'état complet de l'`override`. La sauvegarde dédiée AR0900 a été
chargée via InfinityLoader. Après la fin du préchauffage, la carte a été ouverte et refermée deux
fois. Les pages non puissance de deux ont été acceptées par le moteur ; aucune couture, corruption
ou anomalie de rendu évidente n'a été observée.

| Mesure AR0900 | Référence 4096² | Candidat 2112² | Évolution |
|---|---:|---:|---:|
| Pages découvertes / planifiées | 26 / 26 | 90 / 90 | plafond 96 respecté |
| Pages initialement résidentes | 7 | 18 | information de session |
| Demandes / matérialisations du préchauffage | 19 / 19 | 72 / 72 | aucune éviction |
| `totalDemandMs` | 746,05 ms | 864,56 ms | +15,89 % au total |
| `maximumDemandMs` | 43,97 ms | 15,22 ms | -65,39 % |
| Pic événement 1 | 6,90 ms | 6,33 ms | zéro matérialisation PVR |
| Pic événement 2 | 6,02–8,92 ms | 6,63 ms | zéro matérialisation PVR |

La session contient zéro erreur et un seul avertissement, la récupération déjà connue du prologue
`RenderTexture` détourné par EEex. Le journal complet est archivé sous
`G:\AI\BG2_Upscale-data\performance-audit\map-page-repage-2112-20260830T130630\post-run\InfinityEngine-Enhancer.log`,
borne de session `2026-08-30 13:16:58.763`, SHA-256
`244540412F0C619BD929F2E141A2525AB354E98DEF648DF90ECF450D91B91857`.

### Verdict et restauration

L'essai valide la compatibilité ingame des pages 2112² et confirme que réduire l'unité atomique
réduit fortement son coût. Il est néanmoins **rejeté comme solution finale** : 15,22 ms manque la
gate de 8 ms de 7,22 ms, et la multiplication des pages augmente le coût cumulé du préchauffage.
Une page carrée uniforme plus petite ne peut pas rester sous le plafond de 96 ; une disposition
rectangulaire de 60 cellules ne réduirait l'unité que de 6,25 %, insuffisant au regard de la mesure.

Après fermeture du jeu et d'InfinityLoader, la transaction
`backups/maps/AR0900-20260830T111545270887Z-36dba8d0/` a été restaurée et revérifiée. Les 27
fichiers actifs correspondent de nouveau, SHA-256 par SHA-256, au sous-build antérieur et aucune
page `A090026` à `A090089` ne subsiste. Le candidat reste hors dépôt avec le statut
`completed-pending-ingame` de son manifeste de génération ; il n'a produit aucun élément
`validated-installed`. `areas.csv`, les manifests de release, le staging et les packages restent
inchangés.

La suite de la phase 3 doit désormais sortir de la seule repagination uniforme : préparer la
lecture et la décompression hors de la frame, ou démontrer une politique de cache réversible au-delà
de 96 pages, puis rendre le résultat au thread GL avec le `Demand` natif comme fallback. La
transaction du DLL expérimental doit être formalisée avant toute nouvelle installation moteur.

## Étape 3d — transaction DLL/INI des candidats moteur — 2026-08-30

Le prérequis de sécurité laissé ouvert par les quatre snapshots bruts `map-page-prewarm-*` est
maintenant traité par
`engine/InfinityEngine-Enhancer/source-patchee/tools/install_renderer_candidate.py`. Le helper de
release existant n'a pas été réutilisé : il possède un bundle figé de huit fichiers et ne doit pas
être détourné pour publier un candidat local limité au DLL et à sa configuration d'essai.

Le nouvel outil possède exactement `InfinityEngine-Enhancer.dll` et
`InfinityEngine-Enhancer.ini` à la racine du jeu. Son contrat impose :

- jeu et InfinityLoader fermés avant installation ou restauration ;
- dossier candidat fermé contenant uniquement les deux noms canoniques ;
- DLL x64 PE32+ marquée DLL et INI UTF-8 non vide avec section ;
- racine de jeu portant `BaldurReal.exe` ou `Baldur.exe`, sans cible liée ;
- racine de sauvegarde hors de l'installation du jeu.

Avant la première mutation, une transaction unique sous `backups/renderer/` stage une copie hashée
des deux fichiers candidats et de chaque fichier antérieur présent, puis publie
`renderer-install-receipt.json` avec le statut `prepared`. Les deux publications utilisent une
copie temporaire vérifiée puis un remplacement atomique. La restauration ne dépend donc ni du
dossier de build ni du dossier candidat d'origine.

Le reçu suit les états `prepared`, `installing`, `installed`, `restoring`, `restored`,
`rolled-back` et `recovery-required`. Une panne d'installation déclenche le rollback automatique ;
une restauration interrompue peut être reprise avec le même reçu. Chaque cible doit correspondre
soit à l'état initial, soit au candidat exact : toute troisième empreinte est laissée intacte et
fait échouer l'opération. Un fichier initialement absent n'est supprimé que s'il porte encore le
hash candidat attendu.

Dix tests sur jeux factices couvrent l'aller-retour exact indépendant de la source, les fichiers
initialement absents, `--verify-only` sans écriture, l'inventaire et le PE invalides, le refus des
processus actifs, une divergence externe, le rollback après échec de copie, la reprise après
restauration interrompue, l'altération du payload ou de la sauvegarde, l'altération du reçu et le
refus d'une autre racine de jeu.

La validation complète passe également : 207 tests Python, puis les deux tests natifs CTest en
Debug et les deux mêmes tests en Release. La compilation des cibles `iee_tests` Debug et Release
réussit avant leur exécution.

Une prévalidation réelle en lecture seule a ensuite utilisé la DLL Release existante
`cmake-build-test/Release/InfinityEngine-Enhancer.dll`, SHA-256
`6FAB82316454C882329119419BEDF2CE9C72682ECB8CEAA74F3E90A9AD53D377`, et une copie de l'INI actif,
SHA-256 `B7B391539DA4A31DA71684D9809AD416E6BDFAEE21AAFE89A0482A7AC4EDE8B5`. Le candidat de preuve est
conservé sous
`G:\AI\BG2_Upscale-data\performance-audit\renderer-transaction-preflight-20260830T134500\candidate\`.
`install --verify-only` accepte les deux fichiers sans créer `backups/renderer/`. Les fichiers du
jeu restent au DLL actif `9FCE57D1…` et à l'INI `B7B39153…` ; aucune installation n'a eu lieu.

Cette sous-étape ne construit ni n'installe un nouveau DLL. L'installation réelle reste inchangée,
aucun candidat ne reçoit de statut QA et aucun manifeste de release n'est modifié. La gate suivante
est le prototype moteur de préparation lecture/décompression hors frame, à concevoir avec données
CPU immuables, publication bornée et upload GL exclusivement sur le thread propriétaire.

### Contrat de l'étape 3e

La lecture du code courant confirme que `CResPVR::Demand` ne peut pas être déplacé tel quel sur un
worker : il regroupe la préparation de ressource, la comptabilité native, la création de texture et
l'upload GL, puis publie `CResPVR::texture`. Le contrat détaillé est conservé dans
`engine/InfinityEngine-Enhancer/source-patchee/docs/map-page-offframe-preparation.md`.

Le premier jalon 3e-A sera donc un préparateur *shadow* sans mutation moteur : le thread GL publie
des identités copiées et versionnées ; un worker unique lit et décompresse un PVRZ borné vers un
buffer CPU immuable ; le thread GL mesure si ce résultat était prêt avant le `Demand` natif, sans le
consommer. Les changements de zone/contexte et l'arrêt invalident la génération. Le `Demand` natif
reste le seul chemin de rendu et le fallback intégral.

Cette étape doit d'abord démontrer l'adressage des ressources, le respect des limites mémoire, la
bonne annulation et un taux de préparation anticipée suffisant sur AR0900. La consommation réelle
3e-B reste bloquée tant que la frontière native entre zlib, ownership des buffers, cache PVR et
upload GL n'est pas établie pour le build manifesté 2.7.3.

## Étape 3e-A — préparateur PVRZ *shadow* hors frame — 2026-08-30

Le premier jalon du contrat est maintenant implémenté derrière
`EnableMapPageOffframeProbe=false`. Il exige également `PerformanceLogs=true`, réutilise le plan
borné de la carte courante et ne change pas le chemin de rendu. Le thread GL publie uniquement une
identité copiée et versionnée. Un worker unique lit un PVRZ explicite de l'`override`, décompresse
son flux zlib et valide l'enveloppe PVR v3 ainsi que la taille exacte des blocs DXT1/DXT5 dans un
buffer CPU privé. Une ressource disponible uniquement via KEY/BIFF est un *miss* propre.

Le worker n'appelle ni le moteur, ni `CResPVR::Demand`, ni WGL/OpenGL, ni un callback de log. Juste
avant une demande native nécessaire, le thread de rendu mesure si le buffer correspondant était
prêt puis le détruit ; le `Demand` natif demeure intégralement autoritaire. Les changements de
génération annulent les jobs, et l'arrêt réveille puis joint le worker avant de libérer la référence
au DLL.

Les bornes fixes sont de 32 Mio comprimés et 20 Mio décodés par page, 96 jobs en attente, quatre
résultats terminés et 72 Mio de buffers terminés cumulés. Les doublons sont coalescés et le worker
attend si le handoff terminé est plein. zlib 1.3.2 est lié statiquement depuis le commit complet
`da607da739fa6047df13e66a2af6b8bec7c2a498`.

### Qualification hors ligne

- compilation DLL, tests et outil de préflight réussie en Debug et Release ;
- `ctest` : 2/2 en Debug et 2/2 en Release ;
- tests Python communs rejoués seuls : 207/207 ;
- `BaldurReal.exe` 2.7.3 validé hors ligne, SHA-256
  `b51093a49140b2b8a7c046b4652bb8e535be24ebbc12b1d735e0b94217a14d57`, trois signatures et onze
  callsites conformes ;
- tests natifs du parseur et des queues : DXT1/DXT5 valides, enveloppe, format, flux tronqué et
  tailles invalides rejetés, capacités/coalescence, résultat prêt, annulation, génération périmée,
  réveil à l'arrêt et libération des buffers.

Le préflight Release utilisant le parseur de production accepte les 26/26 pages jour d'AR0900.
Elles représentent 151,73 Mio lus et 416,00 Mio décodés. L'exécution séquentielle totalise
971,40 ms, avec 18,05 ms minimum, 39,38 ms de médiane et 41,94 ms maximum par page. Ce résultat
prouve le support exact des fichiers installés et dimensionne le travail ; il ne prouve pas encore
qu'un buffer sera prêt avant sa demande native.

La gate suivante définie avant l'essai était une seule session AR0900 installée via la transaction
DLL/INI : vérifier l'absence d'erreur, deadlock, mutation native/GL et résultat périmé accepté,
relever les pics de queues/mémoire ainsi que `readyBeforeDemand` contre `notReadyBeforeDemand`, et
confirmer le rendu inchangé.

### Gate ingame AR0900

Une première exécution a confirmé le rendu mais révélé deux défauts d'observabilité du prototype :
le résumé n'était émis que lors d'un reset de zone ou du hook d'arrêt, non atteint par la fermeture
normale observée, et les sept pages déjà résidentes étaient soumises au worker. Leurs quatre
résultats terminés pouvaient remplir la queue sans jamais rencontrer de `Demand` natif, puis
retarder les pages réellement absentes. Le journal de cette tentative est conservé hors dépôt sous
`G:\AI\BG2_Upscale-data\performance-audit\map-page-shadow-20260830T000000\post-run-incomplete-observability\InfinityEngine-Enhancer.log`,
SHA-256 `8E9E67F22C5F8F4C7E354F6C4FF7C50ADC72CF282CD62C2A7F7F92763536850F`.

La correction exclut désormais du *shadow* les pages résidentes lors de la construction du plan et
émet une fois le résumé dès que toutes les demandes planifiées ont été observées. Les suites
Debug/Release sont restées vertes. Le candidat corrigé avait les identités suivantes :

- DLL Release : 1 494 528 octets, SHA-256
  `F7A5600DC729B5A8804FBE37EC21AA0D40E55FAF6BB9F2CE0A7EC5E24CBDD334` ;
- INI de test : SHA-256
  `3EAAA2002BF3A0D6E4272BCFAE8B6143F9B9921472EFF05717A924E27573C746` ;
- reçu transactionnel :
  `backups/renderer/20260830T123341078087Z-2f0bdcb6/renderer-install-receipt.json`.

La sauvegarde AR0900 a été chargée via InfinityLoader. Après le délai de 30 frames, la carte a été
ouverte jusqu'à sa vue entièrement dézoomée. L'affichage est resté correct, sans couture,
corruption, crash ni blocage. La session bornée ne contient aucune erreur ; son unique avertissement
est la récupération déjà connue du prologue `RenderTexture` détourné par EEex.

| Mesure *shadow* AR0900 | Résultat |
|---|---:|
| pages du plan | 26 |
| pages déjà résidentes, non soumises | 7 |
| pages soumises | 19 |
| prêtes avant `Demand` natif | 16 (84,21 %) |
| non prêtes avant `Demand` natif | 3 (15,79 %) |
| manquantes / I/O en échec / invalides / rejetées / périmées | 0 / 0 / 0 / 0 / 0 |
| préparation terminée | 16 pages, 95,63 Mio comprimés, 256,00 Mio décodés |
| temps CPU de préparation | 616,52 ms total ; 42,81 ms maximum |
| pic de queue en attente | 18 pages |
| pic de résultats terminés | 4 pages, 64,00 Mio |

Le pic de 64,00 Mio respecte la borne cumulée de 72 Mio. Le temps de queue élevé observé
(`maximumQueueMs=14102,53`) correspond au lancement anticipé pendant l'attente avant l'ouverture de
la carte ; il n'est pas un temps de blocage de la frame. Le résumé complet est archivé hors dépôt
sous
`G:\AI\BG2_Upscale-data\performance-audit\map-page-shadow-20260830T000000\post-run-v2\InfinityEngine-Enhancer.AR0900-shadow-v2.log`,
SHA-256 `84C03761DD799EBAD1B2BDE3AD0D1C77C5BC172167377B739E3B5BD50B0B9DEE`.

La gate 3e-A est donc **validée ingame** : la préparation CPU bornée est assez souvent disponible
avant la demande native pour justifier l'étude d'un consommateur. Elle ne réduit encore aucun temps
de frame, puisque les buffers CPU ont tous été observés puis détruits et que le `Demand` natif est
resté intégralement inchangé.

Après fermeture du jeu et d'InfinityLoader, la transaction a été restaurée. Le DLL actif est revenu
au SHA-256 `9FCE57D11ACF2DD6539B7A263B6DE1A70C44F6F41981181793CA6AA785FCC98E`
et l'INI au SHA-256 `B7B391539DA4A31DA71684D9809AD416E6BDFAEE21AAFE89A0482A7AC4EDE8B5`.
3e-B reste bloquée tant que la frontière native de consommation n'est pas établie. Aucun élément
`validated-installed` n'est produit et `areas.csv`, les manifests de release, le staging et les
packages restent inchangés.

## Étape 3e-B0 — frontière native de consommation — 2026-08-30

L'analyse statique du `BaldurReal.exe` manifesté a été étendue au corps complet de
`CResPVR::Demand`. Elle porte sur le fichier de 7 202 696 octets, SHA-256
`b51093a49140b2b8a7c046b4652bb8e535be24ebbc12b1d735e0b94217a14d57`. La fonction est délimitée
par les données d'unwind à `RVA 0x3F6DC0..0x3F6F7F`.

La fonction native gère successivement l'éviction de texture, la LRU de 128 `CResPVR*`, le
chargement des octets PVRZ via `CRes`, la création et le binding de texture, l'allocation du buffer
décodé, zlib, la publication des champs PVR, l'upload DXT puis la libération du buffer décodé. Une
réimplémentation complète de `Demand`, une publication dans `CRes::pData` ou un saut au milieu de la
fonction sont donc rejetés : chacun dupliquerait ou contournerait un propriétaire natif.

Une frontière plus étroite est en revanche prouvée. À `Demand+0x15F` (`RVA 0x3F6F1F`), le moteur
appelle son wrapper `uncompress` unique à `RVA 0x4000F0`. À cet instant :

- les octets PVRZ bruts ont déjà été chargés par le `CRes` natif ;
- la destination décodée a déjà été allouée par le moteur ;
- aucun champ PVR ni upload n'a encore été publié ;
- après le retour à `Demand+0x164`, le moteur parse le PVR, publie format/largeur/hauteur, appelle
  l'upload compressé puis libère sa propre destination.

Le futur consommateur 3e-B1 peut donc, sur le thread de rendu uniquement, copier le PVR déjà décodé
dans cette destination, écrire la longueur produite et retourner `Z_OK`. Il ne doit jamais conserver
le pointeur natif. La substitution exige l'adresse de retour exacte `RVA 0x3F6F24`, un scope
`CResPVR::Demand` actif, l'identité/génération/resref de la page, `source == pData+4`,
`sourceLength+4 == nSize`, la taille décodée exacte, les bornes 3e-A et un CRC32 du flux compressé
identique. Tout écart appelle le zlib original.

L'outil `validate_build.py` localise maintenant exactement une signature `Demand` et une signature
du wrapper zlib, puis décode les neuf callsites natifs suivants :

| Phase | Offset `Demand` | Cible RVA |
|---|---:|---:|
| suppression texture évincée | `+0xA9` | `0x413270` |
| décalage LRU | `+0xC1` | `0x4FA710` |
| chargement `CRes` | `+0xDC` | `0x402A00` |
| création texture | `+0x12E` | `0x413350` |
| binding texture | `+0x138` | `0x413140` |
| allocation destination | `+0x143` | `0x502678` |
| handoff `uncompress` | `+0x15F` | `0x4000F0` |
| upload compressé | `+0x198` | `0x413240` |
| libération destination | `+0x1A0` | `0x4FDAB8` |

La fenêtre native post-décompression à `Demand+0x164` est également signée dans le manifeste C++.
La validation hors ligne passe sur l'exécutable installé. La preuve détaillée est conservée dans
`engine/InfinityEngine-Enhancer/source-patchee/docs/validation/map-page-offframe-phase3b0.md`.

3e-B0 est **terminée** : une frontière respectant l'ownership natif existe. Elle n'active toutefois
aucun consommateur et ne produit aucun gain ingame à elle seule. La prochaine étape est 3e-B1 : une
option séparée, `false` par défaut, limitée d'abord à une seule page consommée par génération AR0900,
avec toutes les autres pages et tous les échecs sur `uncompress` natif. Aucun élément
`validated-installed` ni changement de release n'est produit.

## Étape 3e-B1 — canari d'une page consommée — 2026-08-30

Le consommateur étroit défini en 3e-B0 est maintenant implémenté derrière
`EnableMapPageOffframeConsume=false` par défaut. Il exige également `PerformanceLogs=true`. Le
préparateur worker reste limité aux octets CPU d'override ; il calcule désormais le CRC32 du flux
zlib exact et publie toujours au plus quatre buffers / 72 Mio.

Pour chaque génération de zone, le hook extérieur `CResPVR::Demand` ne peut revendiquer qu'un seul
résultat prêt. Cette revendication déplace le buffer hors de la file, sans seconde copie de 16 Mio.
Un scope TLS associe ensuite ce buffer au `CResPVR*` exact pendant l'appel natif. Tout `Demand`
imbriqué remplace ce scope, même sans candidat, et ne peut donc pas consommer la page de son appelant.

Le hook global du wrapper zlib n'effectue la copie que si l'adresse de retour vaut exactement
`moduleBase+0x3F6F24`, si le propriétaire natif et le scope sont identiques, si
`source == pData+4`, si les tailles source/ressource/destination/préparée concordent, si les plages
mémoire ont les protections attendues et si le CRC32 recalculé sur le thread de rendu est identique.
Une seconde lecture de `pData/nSize` protège la fenêtre entre CRC et copie. En cas de réussite, les
octets PVR validés sont copiés dans la destination déjà allouée par le moteur, la taille 32 bits est
écrite et `Z_OK` est retourné. Le moteur reprend à `Demand+0x164` pour publier les champs, uploader
le DXT et libérer sa destination. Aucun champ `CResPVR`, aucune LRU et aucun appel GL n'est possédé
par le prototype.

Tout manque, retard, résultat périmé, appel inattendu, imbrication, adresse, taille, source, CRC ou
protection mémoire divergente rappelle le wrapper zlib original avec ses arguments d'origine. Une
revendication rejetée ne peut pas être retentée dans la même génération. La télémétrie distingue
revendiqué, consommé, chaque famille de fallback, temps CRC/copie et durée totale du `Demand` natif.
Le teardown enlève d'abord le hook zlib, puis le hook `Demand`, puis l'état worker.

Les gates hors ligne passent : CTest Debug 2/2, CTest Release 2/2, DLL Windows x64 Release,
207/207 tests Python et validation exacte du `BaldurReal.exe` manifesté. Le candidat deux fichiers a
passé `install_renderer_candidate.py install --verify-only` sans écriture dans le jeu :

- dossier :
  `G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b1-20260830\candidate-b1-offline-v1` ;
- DLL : 1 508 352 octets, SHA-256
  `DAE3173054F0A7BCBCD168B6361551EE96706A2CE61EBD3A36702F51797C1111` ;
- INI : 2 450 octets, SHA-256
  `8C20DF91B6A991F6716A92C42A6D439DCE74088EC351D65397BB89C4FB842B5A`.

Le jeu restait sur la DLL `9FCE57D1...FCC98E` et l'INI `B7B39153...EDE8B5` après cette seule
prévalidation. Le candidat était alors prêt pour sa gate ingame.

### Gate ingame AR0900 — une page consommée

Le candidat exact a ensuite été installé par la transaction
`backups/renderer/20260830T140726573407Z-93391f5e/renderer-install-receipt.json`, jeu et
InfinityLoader fermés. InfinityLoader a lancé BG2EE, puis la sauvegarde solo `AR0900` a été chargée.
Après le délai de 30 frames, une et une seule page préparée a été consommée :

```text
area=AR0900, page=A090001, generation=3, outcome=consumed,
compressedMiB=6.84, decodedMiB=16.00, crcMs=1.09, copyMs=2.12,
nativeDemandMs=9.89; native cache/upload/free path retained
```

| Mesure canari AR0900 | Résultat |
|---|---:|
| pages du plan / déjà résidentes / soumises | 26 / 7 / 19 |
| préparées avant `Demand` / non prêtes | 18 / 1 |
| revendications / consommations | 1 / 1 |
| fallbacks originaux et familles de mismatch/erreur | 0 |
| préparation worker | 18 pages ; 99,90 Mio comprimés ; 288,00 Mio décodés |
| temps CPU worker | 674,71 ms total ; 43,35 ms maximum |
| pic de résultats terminés | 4 pages ; 64,00 Mio |
| préchauffage natif | 19 matérialisations ; 709,90 ms total ; 43,69 ms maximum |

Le premier relevé natif périodique suivant confirme 35 matérialisations, 35 créations de textures et
35 uploads compressés pour l'aire ; la ligne canari confirme explicitement la poursuite du chemin
cache/upload/libération natif après la substitution. La vue de jeu puis la carte d'AR0900 entièrement
ouverte sont restées correctes, sans couture ou corruption visible, crash ni deadlock. La session
bornée de 411 lignes ne contient aucune erreur et un seul avertissement, la récupération EEex du
prologue `RenderTexture` déjà documentée.

Le journal complet et le reçu copié sont conservés hors dépôt sous
`G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b1-20260830\ingame-ar0900-one-page`.
Le log fait 15 602 022 octets, SHA-256
`7CBB269CCFD2CB79B2D3DA1FC3B3733E5EE92A7F83EADB49F6F70AA133006C12` ; la copie du reçu fait
1 899 octets, SHA-256 `26487BA801A065ECB1E41F8784BBBE8A7C02E05F260DDAB78CAFB5610D81330C`.

Après sortie du jeu, aucun processus `Baldur`, `BaldurReal` ou `InfinityLoader` ne restait actif.
La restauration et la vérification du reçu ont passé. Le jeu porte de nouveau exactement le DLL
`9FCE57D11ACF2DD6539B7A263B6DE1A70C44F6F41981181793CA6AA785FCC98E` et l'INI
`B7B391539DA4A31DA71684D9809AD416E6BDFAEE21AAFE89A0482A7AC4EDE8B5`.

3e-B1 est donc **validée ingame pour une page**. La gate suivante est un candidat AR0900
multi-page séparé, toujours désactivé par défaut et borné par une limite fixe annoncée avant
l'essai, avec les mêmes contrôles stricts, fallback zlib natif, télémétrie, rendu complet, sortie
stable et restauration exacte. La campagne des quatre zones reste ultérieure. Ce résultat ne
produit aucun élément `validated-installed` et ne modifie ni `areas.csv` ni les manifests de
release.

## Étape 3e-B2 — consommation bornée à quatre pages — 2026-08-30

Le verrou 3e-B1 d'une seule revendication par génération est remplacé par un compteur compile-time
fixé à quatre. Seul un résultat déjà prêt consomme un slot. Une tentative revendiquée consomme son
slot même si un contrôle ultérieur bascule vers le zlib original, ce qui interdit qu'une entrée
malformée rende l'essai non borné. La cinquième revendication est refusée jusqu'au reset explicite
de génération. Les pages tardives ou absentes restent sur le `Demand` natif synchrone.

La frontière prouvée en B1 ne change pas : scope TLS sur le `CResPVR*` exact, adresse de retour,
source, tailles, protections mémoire, CRC32 et seconde lecture propriétaire doivent tous concorder.
Le moteur conserve l'allocation de destination, la LRU de 128 entrées, la publication des champs,
l'upload GL et la libération. La file worker reste bornée à quatre résultats / 72 Mio et un seul
buffer revendiqué peut être actif à la fois pendant le `Demand` synchrone.

La télémétrie expose maintenant `claim=N/4`, `consumeClaims`, `claimLimit=4` et le mode
`bounded-four-page-consume`. Le test natif impose explicitement la limite quatre, accepte les
revendications 1 à 4, refuse la cinquième et les générations étrangères, puis vérifie le réarmement
au changement de zone.

Les gates hors ligne passent : CTest Debug 2/2, CTest Release 2/2, DLL Windows x64 Release,
207/207 tests Python et validation exacte du `BaldurReal.exe` 2.7.3 manifesté. Le candidat fermé
DLL+INI a passé `install_renderer_candidate.py install --verify-only` sans écriture dans le jeu :

- dossier :
  `G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b2-20260830\candidate-b2-four-page-offline-v1` ;
- DLL : 1 509 888 octets, SHA-256
  `2030519385A9922E43A597CA290AE74FEE8533003BEA651FAB243ABF10AF8D89` ;
- INI : 2 452 octets, SHA-256
  `B1587B7B6164050577537A31517B88811F30DC53025CCE638C32A8D182D9C178`.

La prévalidation seule a laissé le jeu exactement sur la DLL
`9FCE57D11ACF2DD6539B7A263B6DE1A70C44F6F41981181793CA6AA785FCC98E` et l'INI
`B7B391539DA4A31DA71684D9809AD416E6BDFAEE21AAFE89A0482A7AC4EDE8B5`.

3e-B2 est donc **qualifiée hors ligne**, mais cela ne préjuge pas de sa gate ingame.

### Gate ingame AR0900 — échec après trois consommations

Le candidat exact a été installé par transaction, puis la sauvegarde solo AR0900 a été chargée via
InfinityLoader. Le plan a découvert et planifié 26 pages, dont sept déjà résidentes. Trois
substitutions ont terminé le chemin natif cache/upload/libération : `A090001` en 10,17 ms
(`crcMs=1,12`, `copyMs=2,18`), `A090008` en 9,64 ms (`1,05` / `2,30`) et `A090009` en 7,08 ms
(`0,99` / `2,33`).

Le processus a ensuite levé `0xC0000005` avant tout quatrième résultat et avant le résumé de zone.
Le minidump situe l'accès nul dans `BaldurReal.exe` à la RVA `0x3F6EFD`, soit
`CResPVR::Demand+0x13D`, instruction `mov ecx, dword ptr [rsi]` avec `rsi=0`. La ressource native
active est `A090010`; son état capturé indique `pData=0`, `nSize=0`, `bLoaded=false`. Cette adresse
se place après la création/bind de texture mais avant l'allocation du buffer décodé à `+0x143` et
avant le handoff `uncompress` à `+0x15F`. Le dump ne permet donc pas d'affirmer qu'une quatrième
substitution a été atteinte. La vue monde avait été affichée, mais la carte complète et la sortie
stable n'ont pas pu être validées.

Le journal, les dumps big/small, le log de crash et les reçus avant/après restauration sont archivés
dans
`G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b2-20260830\ingame-ar0900-four-page`.
Le journal fait 15 625 331 octets, SHA-256
`5CAFE3A853FD2741D00CBA803E042DE1BC9E48A71AB2DB36BA8D0A28455D833D`; le petit dump fait
94 168 846 octets, SHA-256
`AD41F082096C469C7DEF0F94CCDB0DA7A26646C30E19FF55B2D97E7958217822`; le grand dump fait
1 541 952 903 octets, SHA-256
`BB2F6C825F2758245D8371C64829D35EFD0F1D48F6263518C5677D9A5441D49A`.

Après fermeture du dialogue de crash, aucun processus jeu/loader ne restait. La restauration et la
vérification du reçu passent ; la racine jeu retrouve exactement la DLL
`9FCE57D11ACF2DD6539B7A263B6DE1A70C44F6F41981181793CA6AA785FCC98E` et l'INI
`B7B391539DA4A31DA71684D9809AD416E6BDFAEE21AAFE89A0482A7AC4EDE8B5`.

3e-B2 est donc **rejetée ingame dans cet état**. À ce stade, B1 reste la dernière frontière de consommation
prouvée. La prochaine gate est un candidat diagnostic/correctif distinct qui explique ou élimine
l'état natif nul avant `Demand+0x13D`, puis repasse AR0900 avec chaque tentative comptabilisée,
carte complète correcte et sortie stable. La gate des 8 ms et la campagne des quatre zones restent
bloquées. Aucun élément `validated-installed`, `areas.csv` ou manifeste de release n'est modifié.

## Étape 3e-B2a — discrimination du quatrième claim — 2026-08-30

3e-B2a fixe la limite compile-time à trois, soit exactement le nombre de consommations terminées en
B2. Elle ajoute une décision explicite par page (`prepared-claim`, fallback non prêt ou fallback
limite atteinte) et manifeste l'appel direct `CRes::Demand` à `CResPVR::Demand+0xDC`, cible RVA
`0x402A00`. Un detour transparent journalise avant/après `pData`, `nSize`, `bLoaded`, la texture et
la valeur de retour, sans modifier aucun champ ni résultat natif.

Les gates hors ligne passent : CTest Debug 2/2, CTest Release 2/2, DLL Windows x64 Release,
207/207 tests Python, validation exacte du binaire et prévalidation transactionnelle sans écriture.
Le candidat fermé est conservé sous
`G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b2a-20260830\candidate-b2a-three-claim-diagnostic-v1` :

- DLL : 1 516 032 octets, SHA-256
  `B720C6F3DC45C35ED85232CA6B1FB9AA6A5DCF2AB63CE6E123CC2876180090B2` ;
- INI : 2 461 octets, SHA-256
  `BB4EE37E468FC9E55B8CEC9799C9039CB29F69D24FEC97B0B1BA2DB41A2A1876`.

### Gate ingame AR0900 — diagnostic concluant, validation échouée

Le candidat a été installé par la transaction
`backups/renderer/20260830T153716160757Z-2b5576dd/renderer-install-receipt.json`, puis la sauvegarde
solo AR0900 a été chargée via InfinityLoader. Après un fallback natif réussi sur `A090000`, les
trois slots ont consommé `A090001`, `A090008` et `A090009` :

| Claim | Page | retour `CRes::Demand` / taille | CRC | copie | `CResPVR::Demand` |
|---:|---|---:|---:|---:|---:|
| 1/3 | `A090001` | vrai / 7 172 686 octets | 1,00 ms | 2,20 ms | 9,75 ms |
| 2/3 | `A090008` | vrai / 6 874 805 octets | 0,96 ms | 2,35 ms | 10,37 ms |
| 3/3 | `A090009` | vrai / 6 489 575 octets | 0,89 ms | 2,38 ms | 6,80 ms |

La page suivante est tracée sans ambiguïté : `A090010`, `queueStatus=not-ready`,
`action=native-fallback-claim-limit`, `claims=3/3`, puis `activeClaim=false`, `claim=0/3`.
`CRes::Demand` entre avec la ressource vide et renvoie `false`, toujours avec `pData=null`,
`nSize=0`, `bLoaded=false` et texture nulle. Le processus crashe immédiatement après.

Le flux d'exception du petit dump confirme `0xC0000005`, lecture de l'adresse zéro, à
`0x1403F6EFD`, donc RVA `0x3F6EFD` / `CResPVR::Demand+0x13D`. Le crash reste situé avant
l'allocation décodée `+0x143` et le handoff zlib `+0x15F`.

La conclusion diagnostique est acquise : **aucune quatrième substitution n'a été tentée**. Le
chargement natif échoue après les trois consommations précédentes et le moteur déréférence ensuite
le pointeur nul. B2a ne permet pas encore de séparer un effet cumulatif des substitutions, un effet
de la télémétrie/timing ou une interaction de comptabilité ressource ; elle interdit en revanche
d'attribuer le crash à la copie d'un quatrième buffer ou de corriger en écrivant les champs natifs.

Les preuves sont archivées sous
`G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b2a-20260830\ingame-ar0900-three-claim-diagnostic` :

- journal : 15 662 426 octets, SHA-256
  `2F6CBFE019F3907003239B41C2AF29D12AEF123E7A2D80F4CC1116D885C7C965` ;
- petit dump : 94 164 875 octets, SHA-256
  `4374C0A63ED9F6832A5DBF2A2F7094300160C43C0FF28E97F133D4516F8FFF0E` ;
- grand dump : 1 487 612 074 octets, SHA-256
  `DE8A668A109FC2A0745E3BBFAD74771C77562103E19157FC4A6951E282131671`.

Après le crash, aucun processus jeu/loader ne restait. La restauration et la vérification passent ;
la racine jeu retrouve exactement la DLL
`9FCE57D11ACF2DD6539B7A263B6DE1A70C44F6F41981181793CA6AA785FCC98E` et l'INI
`B7B391539DA4A31DA71684D9809AD416E6BDFAEE21AAFE89A0482A7AC4EDE8B5`.

La prochaine gate est d'abord un contrôle à une revendication avec cette même télémétrie, pour
revalider B1 sans confondre un effet du nouveau detour. S'il passe, un candidat exactement deux
revendications doit discriminer le seuil et ajouter `CRes::nCount`/`bWasMalloced` aux états
entrée/retour. Aucun essai quatre zones avant ces deux preuves. B1 reste la dernière frontière
ingame prouvée (frontière ensuite étendue à deux par B2b) ; aucun élément `validated-installed`, `areas.csv` ou manifeste de release n'est
modifié.

## Étape 3e-B2b — contrôle une revendication et seuil deux/trois — 2026-08-30

Les deux discriminateurs prévus par B2a ont été construits, qualifiés hors ligne, installés par la
transaction renderer, exécutés sur la sauvegarde solo AR0900 via InfinityLoader, puis restaurés
exactement. CTest Debug/Release passent 2/2, la DLL Windows x64 Release est construite, les 207 tests
Python passent, tout comme le validateur exact du binaire 2.7.3 et le préflight transactionnel.

Le contrôle B2b1 limite le prototype à une revendication. `A090001` est consommée avec succès
(`crcMs=0,98`, `copyMs=2,10`, `nativeDemandMs=9,69`), puis `A090008` et toutes les pages suivantes
suivent le fallback natif avec `CRes::Demand=true`. La carte complète est correcte, reste stable
plus de 22 secondes et la sortie est propre. Le nouveau detour de télémétrie est donc transparent à
la frontière B1.

Le discriminateur B2b2 limite ensuite le même code à exactement deux revendications :

| Claim | Page | retour `CRes::Demand` / taille | CRC | copie | `CResPVR::Demand` |
|---:|---|---:|---:|---:|---:|
| 1/2 | `A090001` | vrai / 7 172 686 octets | 1,03 ms | 2,13 ms | 9,99 ms |
| 2/2 | `A090008` | vrai / 6 874 805 octets | 1,08 ms | 2,08 ms | 9,68 ms |

`A090009`, `A090010` et toutes les pages suivantes choisissent alors
`native-fallback-claim-limit` et leurs deux appels natifs renvoient vrai. La carte complète reste
correcte et stable plus de 22 secondes, puis le jeu quitte proprement. Le résumé confirme
`consumeClaims=2`, `claimLimit=2`, `consumed=2` et zéro erreur/mismatch.

La matrice contrôlée borne maintenant le seuil : une et deux substitutions sont stables ; avec
trois substitutions, B2a consomme encore `A090009`, puis le premier chargement natif suivant
(`A090010`) renvoie faux et crashe. **L'échec devient donc observable après la troisième
substitution réussie**, et non pendant une quatrième copie. Cela ne prouve pas encore si la cause
est une opération de cycle de vie manquante, la comptabilité/cache ou une allocation native.

La lecture proposée de `nCount` n'est pas exploitable : B2b1 journalise, sur des chargements PVR
pourtant réussis, des valeurs impossibles et persistantes telles que `538976288`, `1213408043`,
`1717989152` et `1969448306`, alors que B2b2 obtient zéro sur la même famille. Ce champ modélisé ne
doit ni servir de compteur de référence ni être écrit. `bWasMalloced` reste descriptif seulement,
faute de validation indépendante de son layout et de sa durée de vie.

Les candidats et preuves sont archivés sous :

- `G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b2b1-20260830` ;
- `G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b2b2-20260830`.

Le détail des hashes, reçus et sessions est dans
[`../engine/InfinityEngine-Enhancer/source-patchee/docs/validation/map-page-offframe-phase3b2b.md`](../engine/InfinityEngine-Enhancer/source-patchee/docs/validation/map-page-offframe-phase3b2b.md).
Après chaque essai, aucun processus jeu/loader ne reste ; la racine jeu retrouve exactement la DLL
`9FCE57D11ACF2DD6539B7A263B6DE1A70C44F6F41981181793CA6AA785FCC98E` et l'INI
`B7B391539DA4A31DA71684D9809AD416E6BDFAEE21AAFE89A0482A7AC4EDE8B5`.

La prochaine gate est **3e-B2c** : comparaison A/B deux claims stables contre trois claims en échec,
avec une télémétrie sans champs natifs devinés. Elle doit manifester les frontières exactes
demande/libération et cache PVR, puis tracer les identités de pointeurs, décision
zlib-original/substitution, mouvements des 128 slots, texture, libérations appariées, mémoire
processus et mémoire des queues. Aucune valeur/retour natif ne doit être modifié. La première
divergence avant l'échec de `A090010` définira l'unique invariant à corriger ; le candidat corrigé
devra d'abord passer trois revendications sur AR0900. La campagne quatre zones reste bloquée.
Aucun élément `validated-installed`, `areas.csv` ou manifeste de release n'est modifié.

## Étape 3e-B2c — cycle de vie cache/fichier et première divergence — 2026-08-30

B2c remplace les champs natifs devinés par des frontières manifestées sur le
`BaldurReal.exe` 2.7.3 exact : cache PVR de 128 pointeurs à la RVA `0x721B70`, référence depuis
`CResPVR::Demand+0x19`, routine de libération à la RVA `0x3F70B0` et appel du helper d'ouverture
fichier depuis `CRes::Demand+0xE2` vers la RVA `0x408430`. Le validateur hors ligne et
l'installation runtime échouent fermés si une signature, un call edge ou une référence RIP ne
correspond pas. La télémétrie ne lit que pointeurs, tailles et champs déjà validés ; elle n'écrit
aucun slot, champ ou retour natif.

Les gates hors ligne passent : CTest Debug 2/2, CTest Release 2/2, DLL Windows x64 Release et son
CTest 2/2, 207 tests Python, validateur exact du binaire et préflight de transaction. Le contrôle
AR0900 limité à deux claims repasse : `A090001` et `A090008` consomment les buffers préparés,
`A090009`, `A090010` et les pages suivantes chargent nativement, la carte complète est correcte et
reste stable plus de 25 secondes avant une sortie propre. Les 19 ouvertures PVR observées
réussissent et aucune libération de cache n'est attendue sous le plafond de 128.

Le discriminateur à trois claims reproduit ensuite le crash différé. Les trois substitutions
elles-mêmes terminent normalement :

| Claim | Page | ouverture | `CRes::Demand` | texture |
|---:|---|---|---|---:|
| 1/3 | `A090001` | vrai / erreur 0 | vrai / 7 172 686 octets | 40 |
| 2/3 | `A090008` | vrai / erreur 0 | vrai / 6 874 805 octets | 41 |
| 3/3 | `A090009` | vrai / erreur 0 | vrai / 6 489 575 octets | 42 |

La page immédiatement suivante est la première divergence : `A090010` est connue par la queue
mais `not-ready`, choisit `native-fallback-claim-limit`, puis son helper d'ouverture renvoie
**`false`, `GetLastError=32` (`ERROR_SHARING_VIOLATION`)**. `CRes::Demand` propage `false` avec
`pData=null`/`nSize=0`, aucun retour `CResPVR::Demand` n'est journalisé et InfinityLoader capture
`0xC0000005`.

Cette frontière exclut les hypothèses cache/mémoire : `A090010` vient d'être insérée une seule fois
au slot 127, l'occupation n'est que de 36/128, aucune routine de libération n'a été appelée, le
nombre de handles reste à 795 et la mémoire processus a déjà baissé par rapport au claim précédent.
La queue montre simultanément 14 jobs en attente et l'identité `A090010` connue mais absente de la
deque : le worker unique a donc pris ce job en vol. Le code retire l'identité et entre aussitôt dans
le fallback natif, sans acquittement de fin du lecteur shadow. La collision de durée de vie du
handle fichier est la première cause démontrée ; rien n'indique une corruption du buffer décodé,
de la LRU ou de la texture.

Les candidats, logs, reçu installé/restauré, crash log et petit dump sont archivés sous :

```text
G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b2c-20260830
```

Le détail complet et les hashes sont dans
[`../engine/InfinityEngine-Enhancer/source-patchee/docs/validation/map-page-offframe-phase3b2c.md`](../engine/InfinityEngine-Enhancer/source-patchee/docs/validation/map-page-offframe-phase3b2c.md).
Après les deux essais, aucun processus jeu/loader ne reste et la racine jeu retrouve exactement la
DLL `9FCE57D11ACF2DD6539B7A263B6DE1A70C44F6F41981181793CA6AA785FCC98E` et l'INI
`B7B391539DA4A31DA71684D9809AD416E6BDFAEE21AAFE89A0482A7AC4EDE8B5`.

La source est revenue à la frontière de contrôle de deux claims. La prochaine gate est
**3e-B2d** : représenter explicitement l'identité détenue par le worker et obtenir son acquittement
de fermeture avant qu'un fallback natif ouvre la même PVRZ. Un job encore en attente peut être
retiré sans attente ; un job déjà en vol doit fermer puis signaler sa libération. Ce protocole doit
avoir un test de concurrence déterministe, conserver tous les retours natifs autoritaires, puis
passer le test trois claims sur AR0900 avec carte complète, stabilité prolongée et sortie propre.
La campagne quatre zones reste bloquée. Aucun élément `validated-installed`, `areas.csv` ou
manifeste de release n'est modifié.

## Étape 3e-B2d — acquittement du lecteur shadow en vol — 2026-08-30

B2d corrige uniquement la collision de durée de vie démontrée par B2c. La queue expose maintenant
l'identité détenue par le worker. Si le rendu demande cette même page avant sa publication, il
retire l'identité, attend que le worker ferme le fichier et acquitte sa libération, puis seulement
entre dans le fallback natif. Un job encore pending est retiré sans attente. Le worker signale la
fin de possession avant publication et jette le résultat si l'identité a été annulée.

Un test de concurrence déterministe bloque le worker sur `A090010`, lance l'observateur natif sur
un second thread, vérifie qu'un waiter est présent, puis ne laisse le fallback continuer qu'après
l'acquittement et la destruction du résultat annulé. Les métriques ajoutées comptent les identités
en vol, waiters, attentes et durées totale/maximale.

La gate trois claims AR0900 passe. La première page `A090000` exerce précisément le nouveau
protocole : `not-ready`, attente de 42,04 ms, `queueInFlight=0`, puis ouverture native vraie avec
`GetLastError=0`, `CRes::Demand=true` (7 015 358 octets) et `CResPVR::Demand=true` (texture 39).
Les trois revendications préparées suivantes réussissent sur `A090001`, `A090008` et `A090009`.
`A090010` et toutes les pages ultérieures passent par le fallback natif après limite sans échec.

Le résumé final compte 19 jobs soumis, 18 préparés, un résultat en vol annulé/jeté, une attente
native de 42,04 ms, trois consommations, zéro famille de mismatch/erreur et aucun état résiduel
pending/in-flight/waiter/completed. Il n'existe aucun retour faux de l'ouverture fichier,
`CRes::Demand` ou `CResPVR::Demand`. La carte complète reste correcte et stable plus de 30 secondes
avant une sortie propre.

Le candidat, le log et les reçus installé/restauré sont archivés sous :

```text
G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b2d-20260830
```

Le détail complet et les hashes sont dans
[`../engine/InfinityEngine-Enhancer/source-patchee/docs/validation/map-page-offframe-phase3b2d.md`](../engine/InfinityEngine-Enhancer/source-patchee/docs/validation/map-page-offframe-phase3b2d.md).
Après l'essai, aucun processus jeu/loader ne reste et la racine jeu retrouve exactement la DLL
`9FCE57D11ACF2DD6539B7A263B6DE1A70C44F6F41981181793CA6AA785FCC98E` et l'INI
`B7B391539DA4A31DA71684D9809AD416E6BDFAEE21AAFE89A0482A7AC4EDE8B5`.

La prochaine gate est un candidat **quatre claims AR0900** conservant le handshake B2d inchangé.
Il doit prouver quatre consommations préparées, tous les fallbacks ultérieurs, une carte complète
stable, une sortie propre et une restauration exacte. La campagne quatre zones reste bloquée
jusqu'à cette preuve. Aucun élément `validated-installed`, `areas.csv` ou manifeste de release
n'est modifié.

## Étape 3e-B2e — gate quatre claims AR0900 — 2026-08-30

B2e ne change que la borne compile-time de trois à quatre consommations préparées par génération.
Le handshake B2d, les retours natifs, la propriété cache/ressource, les bornes mémoire et l'option
default-off restent identiques. Le test de borne attend maintenant quatre claims et le test de
concurrence déterministe du lecteur en vol reste actif.

Toutes les gates hors ligne passent : CTest commun Debug 2/2, CTest commun Release 2/2, build DLL
Windows x64 Release et son CTest 2/2, validateur exact du `BaldurReal.exe` 2.7.3, préflight
transactionnel et 207/207 tests Python en 96,793 secondes.

La gate ingame AR0900 passe. `A090000`, non prête et déjà détenue par le worker, attend 43,58 ms
l'acquittement avant de réussir sa demande native. Les quatre consommations préparées sont :

| Claim | Page | Décision |
|---:|---|---|
| 1/4 | `A090001` | `prepared-claim` |
| 2/4 | `A090008` | `prepared-claim` |
| 3/4 | `A090009` | `prepared-claim` |
| 4/4 | `A090010` | `prepared-claim` |

Après la limite, `A090011` exerce une seconde attente de lecteur en vol de 24,01 ms puis charge
nativement. Tous les fallbacks suivants réussissent. La section de log compte 19/19 ouvertures
fichier vraies, 51/51 retours `CRes::Demand` vrais, 19/19 retours `CResPVR::Demand` vrais et zéro
ligne `error`/`critical`.

Le résumé final compte 19 jobs soumis et démarrés, 17 préparés, deux résultats annulés/jetés,
17 pages prêtes avant demande et deux non prêtes. Les quatre claims sont consommés
(`consumeClaims=4`, `claimLimit=4`, `consumed=4`). Les deux attentes totalisent 67,59 ms, avec un
maximum de 43,58 ms. La préparation représente 93,81 Mio compressés, 272,00 Mio décodés,
655,05 ms au total et 45,06 ms au maximum. Le pic de résultats complétés est de quatre pages /
64,00 Mio. Toutes les familles mismatch/erreur sont à zéro et il ne reste aucun état pending,
in-flight, waiter ou completed.

Le préchauffage natif découvre 26 pages, en trouve sept résidentes et en matérialise 19 en
675,06 ms au total, maximum 84,80 ms. La carte complète est correcte, reste stable plus de
30 secondes et le jeu sort proprement par son dialogue normal.

Le candidat, le log et les reçus installé/restauré sont archivés sous :

```text
G:\AI\BG2_Upscale-data\performance-audit\map-page-offframe-phase3b2e-20260830
```

Le détail complet et les hashes sont dans
[`../engine/InfinityEngine-Enhancer/source-patchee/docs/validation/map-page-offframe-phase3b2e.md`](../engine/InfinityEngine-Enhancer/source-patchee/docs/validation/map-page-offframe-phase3b2e.md).
Après l'essai, aucun processus jeu/loader ne reste et la racine jeu retrouve exactement la DLL
`9FCE57D11ACF2DD6539B7A263B6DE1A70C44F6F41981181793CA6AA785FCC98E` et l'INI
`B7B391539DA4A31DA71684D9809AD416E6BDFAEE21AAFE89A0482A7AC4EDE8B5`.

La gate de correction quatre claims est close et la campagne quatre zones est rouverte. La suite
est une campagne contrebalancée de performance et robustesse sur AR0700N, AR0516, AR0602 et
AR0900, avec le même candidat transactionnel, le handshake inchangé et les métriques par zone de
claims, fallbacks/attentes, préparation et ouverture de carte. Toute campagne cache OS froid reste
séparée. Le prototype demeure non éligible à la release : aucun élément `validated-installed`,
`areas.csv` ou manifeste de release n'est modifié.
