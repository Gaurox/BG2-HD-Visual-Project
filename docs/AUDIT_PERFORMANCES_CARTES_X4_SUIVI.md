# Suivi d’implémentation — audit performances cartes x4

Ce document suit les actions proposées par
[`../AUDIT_PERFORMANCES_CARTES_X4.md`](../AUDIT_PERFORMANCES_CARTES_X4.md). Il ne remplace pas les
sources de vérité du moteur, les manifests de build ou les preuves de validation ingame.

## État au 2026-08-28

Les deux mesures P0 ciblant le hot path ont été implémentées et validées ingame. Les tests manuels
n’ont relevé **ni amélioration perceptible ni régression**. Ils ne constituent pas une mesure de
frametime, d’I/O, de CPU ou de mémoire : aucune conclusion quantitative sur leur gain ne doit en
être tirée.

Le runtime expérimental courant est installé localement de manière réversible avec son état
distinct sous `bg2hd/state/log-rotation-experiment-20260828T211758Z/`. Sa restauration revient au
build expérimental précédent, lui-même réversible. Il n’est pas éligible à la release et aucun
manifeste de release n’a été modifié.

## Actions

| Priorité audit | Action | État | Résultat / prochaine gate |
|---:|---|---|---|
| P0 | Baseline propre : logs verbeux/performance et prototypes hors périmètre désactivés ; journal existant archivé | Fait localement | Aucun gain ni régression perceptible. Conserver cette configuration pour les futurs A/B. |
| P0 | Corriger le budget documentaire des pages 2048 | Fait | 2048 px = 7×7 = 49 tuiles ; 4096 px = 15×15 = 225 tuiles. Commit `3879c10`. |
| P0 | Court-circuiter `is_wtpool_page` si trace et bypass WTPOOL sont désactivés | Validé ingame | Les lectures protégées ne sont plus exécutées hors des deux diagnostics WTPOOL. Mesure objective des `safe_read` encore requise. |
| P0 | Rendre `TILE_PAGE_DIAG` opt-in | Validé ingame | Nouveau réglage `[Rendering] EnableTilePageDiagnostics=false`. Il reste indépendant de `PerformanceLogs`, afin de pouvoir mesurer le hook sans réactiver un flush INFO par page. |
| P0 | Journal rotatif/borné | Validé ingame | Rotation à 16 Mio avec trois sauvegardes, soit environ 64 Mio de nouvelles sorties conservées. Le sink reste synchrone et `flush_on(info)` est préservé. |
| P1 | Marqueurs carte, compteurs PVRZ/upload/delete/mémoire | À faire | Pré-requis pour attribuer précisément I/O, zlib, GL, logging et mémoire. |
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

## Prochaine étape

Le P0 est terminé. La prochaine action de code est le P1 de diagnostic : marqueurs de carte et
compteurs PVRZ, décompression, uploads, suppressions et mémoire. Les mesures A/B de frametime
restent nécessaires avant toute affirmation de gain de performance.
