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

Le runtime expérimental courant est installé localement de manière réversible avec son état
distinct sous `bg2hd/state/map-telemetry-correction-20260828T220405Z/`. Sa restauration revient à
la première DLL P1 testée, dont l’état séparé revient au build P0 de rotation des logs. Il n’est pas
éligible à la release et aucun manifeste de release n’a été modifié.

## Actions

| Priorité audit | Action | État | Résultat / prochaine gate |
|---:|---|---|---|
| P0 | Baseline propre : logs verbeux/performance et prototypes hors périmètre désactivés ; journal existant archivé | Fait localement | Aucun gain ni régression perceptible. Conserver cette configuration pour les futurs A/B. |
| P0 | Corriger le budget documentaire des pages 2048 | Fait | 2048 px = 7×7 = 49 tuiles ; 4096 px = 15×15 = 225 tuiles. Commit `3879c10`. |
| P0 | Court-circuiter `is_wtpool_page` si trace et bypass WTPOOL sont désactivés | Validé ingame | Les lectures protégées ne sont plus exécutées hors des deux diagnostics WTPOOL. Mesure objective des `safe_read` encore requise. |
| P0 | Rendre `TILE_PAGE_DIAG` opt-in | Validé ingame | Nouveau réglage `[Rendering] EnableTilePageDiagnostics=false`. Il reste indépendant de `PerformanceLogs`, afin de pouvoir mesurer le hook sans réactiver un flush INFO par page. |
| P0 | Journal rotatif/borné | Validé ingame | Rotation à 16 Mio avec trois sauvegardes, soit environ 64 Mio de nouvelles sorties conservées. Le sink reste synchrone et `flush_on(info)` est préservé. |
| P1 | Premier lot : marqueurs carte et compteurs table PVR/GL | Validé ingame | Mesure `LoadArea`, les pages de table distinctes et textures sources observées, ainsi que les appels GL upload/delete. Aucun timing I/O/zlib ni calcul mémoire exact dans ce lot. |
| P1 | Attribution précise I/O, zlib et mémoire | À analyser après mesures | Ne pas l’engager avant d’avoir exploité les premiers journaux sur plusieurs cartes. |
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

## Prochaine étape

Le P0 et le premier petit lot P1 sont validés. La prochaine étape d’étude est l’attribution du coût
de la préparation synchrone des animations de zone et de sa mémoire résidente avant d’envisager un
chargement à la demande. Des relevés complémentaires sur AR1200, AR1300 et AR0900 resteront utiles
pour élargir l’échantillon. Les mesures A/B de frametime restent nécessaires avant toute
affirmation de gain de performance.
