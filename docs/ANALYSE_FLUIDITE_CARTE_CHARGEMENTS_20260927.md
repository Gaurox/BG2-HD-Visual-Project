# Fluidité du dézoom et des chargements — analyse indépendante, 2026-09-27

**Statut : analyse + proposition ; aucune correction exécutée ni validation ingame déduite.**

## 1. Décision proposée

Traiter séparément **les blocages de première apparition**, **le coût de la carte déjà chargée** et **la latence des chargements de zone**. Ordre recommandé :

1. Corriger la télémétrie PVR exécutée sur chaque demande de texture, y compris résidente ; conserver une mesure légère.
2. Préparer les pages nécessaires avant leur première utilisation, hors thread de rendu pour les lectures/décompressions, avec publication native sûre et uploads anticipés.
3. Mesurer à nouveau la carte chaude ; réduire ensuite le travail par tuile et, si nécessaire, regrouper les soumissions compatibles.
4. Appliquer la préparation anticipée aux animations de zone et payloads sprites ; réutiliser les composites GPU identiques.

**Ne pas considérer l'activation du prototype existant comme la correction.** Il reste limité, peut attendre son worker et ne couvre pas le coût du rendu chaud. Ne pas augmenter aveuglément les caches : cette session ne montre pas de saturation du cache GPU d'animations.

Objectif produit : conserver détail HD, filtrage, couleurs, transparence, occlusion, eau/animations, géométrie x1, brouillard et comportement des sauvegardes. Supprimer le travail évitable et les attentes dans l'animation ; dimensionner les ressources selon l'ensemble réellement utilisé. Les gains ci-dessous sont des objectifs, pas des résultats obtenus.

## 2. Périmètre et traçabilité

| Élément | Valeur / limite |
|---|---|
| Source primaire | `config://bg2ee_game_root/InfinityEngine-Enhancer.log` |
| Dernière session | **2026-09-27 00:13:39.221 → 00:13:48.699**, soit **9,478 s de logs** |
| Bornes exactes | Lignes **16652–16976**, 325 lignes ; départ au dernier `Infinity Engine Enhancer initializing...` |
| Zone | **AR0900**, WED 80×60, 5 overlays, une expansion de vue capturée |
| Distinction | La session précédente de 00:01:47 appartient au même fichier ; exclue des calculs ci-dessous |
| Log lu | 5 266 676 octets ; SHA256 `2E7F33317E45ABD1BC1887A225C37DEBA2E1EE7DB6089CBFD25EBC8F5AF4C0E1` |
| DLL présente | SHA256 `A51834A18CD1B1940C18672FC7B92F1279F98492C7F9A81B69C417BCBDE6B18B` ; manifeste local [runtime 20260926](../pipeline/runtime/manifests/iee-water-opacity-weather-black-creature-catalog-v2-20260926-v1.json) |
| Source déclarée par ce manifeste | `a0872c71f9beb795d6675ecb3600d8c8ffe2e47f` |
| Checkout analysé | `78dab9467b80cadac1239615f5b455a01cde1824` ; aucun diff de `src/iee/` entre ces deux commits |
| INI lu | `config://bg2ee_game_root/InfinityEngine-Enhancer.ini` ; SHA256 `47979DA9D49EF826014B675D4B0F495842509EED95A6574AFDF71D72B4204B08` ; modification antérieure à la session |
| Force de l'identification | DLL/INI présents cohérents avec la session ; le log ne fournit pas lui-même leur empreinte au démarrage |
| État dépôt initial | `git status --short` sans changement ; avertissement d'accès au fichier global Git ignore |

Méthode : logs récents + lecture du code correspondant ; analyses séparées du chemin carte et des autres chargements ; confrontation **ensuite** aux anciens essais. Aucun lancement de jeu, benchmark, build, installation, modification d'asset ou de release. Les anciennes preuves restent inchangées.

La dernière ligne n'est pas un marqueur de fermeture : ne conclure ni à un crash ni à une sortie normale. Une session de 9,5 s ne mesure pas la stabilité longue durée ni toutes les maps. Le log détecte une expansion de vue, pas la commande UI qui l'a déclenchée ; son association à l'ouverture de carte repose sur la reproduction décrite par l'utilisateur.

### Configuration pertinente

| Actif | Inactif |
|---|---|
| `PerformanceLogs`, `EnableTilePageDiagnostics`, `EnableNativeOcclusionProbe`, `DumpEngineShaders` | `EnableMapPagePrewarm`, `EnableMapPageOffframeProbe`, `EnableMapPageOffframeConsume` |
| Animations de zone, effets, sprites HD, eau route2, shader suite, `EnableNativeOcclusionBridge` | FXAA plein écran, SSAA2x plein écran |

Les options d'expérimentation carte sont donc **hors du chemin actif de cette session**. Leurs limites expliquent pourquoi elles ne constituent pas une solution prête à activer ; elles n'expliquent pas directement ce pic observé.

## 3. Mesures de la dernière session

### 3.1 Première expansion : 19 pages matérialisées en trois images

Source : événements `Map wide-view burst telemetry` et `Map PVR demand phase telemetry`, **00:13:45.966**, L16934–16935. Vue précédente 1155×612. Dimensions ci-dessous = étendue de vue monde rapportée, **pas résolution de l'écran**.

| Frame | Vue monde | Intervalle présentation | Tuiles dessinées | Pages nouvelles | DXT transféré¹ | Demand matérialisant | Upload GL CPU¹ | Résiduel Demand² |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 218 | 1958×1038 | 126,41 ms | 1 022 | 3 | 48 MiB | 114,553 ms | 3,244 ms | 111,287 ms |
| 219 | 4701×2491 | **423,64 ms** | 4 589 | 10 | 160 MiB | 389,713 ms | 10,232 ms | 379,341 ms |
| 220 | 8241×4368 | 273,96 ms | 7 295 | 6 | 96 MiB | 217,765 ms | 5,991 ms | 211,722 ms |
| 221–225 | 8241×4368 | **47,42–48,52 ms** | 7 295 / image | 0 | 0 | 0 mesuré³ | 0 | 0 mesuré³ |

- Trois premières images : **824,01 ms cumulés**, dont **722,031 ms de Demand matérialisant** ; ce n'est pas la durée complète de l'animation UI.
- **19 pages × 16 MiB = 304 MiB** de blocs compressés GPU ; environ **116,97 MiB** de lectures comptées dans leurs scopes.
- Résiduel : **702,350 ms**, soit **97,27 %** du Demand matérialisant. Uploads GL CPU : **19,467 ms** ; génération de noms de texture : 0,214 ms.
- Pages les plus lentes des trois frames : `A090015` 39,671 ms, `A090004` 41,370 ms, `A090002` 40,581 ms ; dimensions 4096×4096.
- Aucune suppression de texture dans les huit échantillons de cette rafale. Pas de preuve de cycle éviction/rechargement dans cette capture.

¹ Durée de l'appel côté CPU et octets soumis, pas durée GPU complète ni trafic PCIe physique mesuré. OpenGL peut exécuter le travail plus tard : [Khronos, Synchronization](https://wikis.khronos.org/opengl/Synchronization).

² `residualMs` = Demand − génération de noms − upload compressé. Il regroupe ressource, lecture, décompression, allocations et autres coûts internes ; **ce n'est pas un chronomètre zlib**.

³ `record_pvr_demand()` ne cumule les durées **que si une matérialisation a eu lieu**. Zéro ici ne signifie pas « demande résidente gratuite ».

**Diagnostic fort :** les premières pages nécessaires sont matérialisées synchroniquement pendant le dézoom. La priorité est le chemin ressource/lecture/préparation, avant une optimisation des seuls transferts GL. La répartition exacte disque / cache OS / zlib / allocation n'est pas encore mesurée.

### 3.2 Vue complète déjà chargée : un second problème

Sur les cinq échantillons 221–225 :

- Intervalle moyen **48,016 ms**, soit environ **20,8 présentations/s sur ce court extrait** ; aucune extrapolation à un plateau long.
- **7 295 tuiles** et **7 398 appels Demand** par image, sans nouvelle matérialisation PVR.
- CPU `RenderTexture` rapporté : **13,316 ms/image** en moyenne ; ordre de grandeur important par rapport à un budget total de 16,67 ms à 60 Hz.
- Le reste peut contenir moteur, diagnostics hors scope, autres draws, pilote, GPU et attente de présentation. Il n'est pas correctement attribué par le log actuel.

**Conséquence :** un cache chaud ou une décompression asynchrone ne suffit pas à garantir la fluidité en vue complète. Inversement, réduire les soumissions ne supprime pas les pages froides.

### 3.3 Chargement de zone, mémoire et caches

| Mesure | Valeur | Conclusion autorisée |
|---|---:|---|
| `LoadArea`, L16711 | natif **23,55 ms**, détour total **162,36 ms** | Charge additionnelle substantielle dans le hook ; pas durée totale du chargement de sauvegarde |
| Pack animations, L16708 | **89 fichiers / 215,16 MiB**, lecture **138,45 ms**, total **138,59 ms** | Lecture/préparation synchrone des pixels ≈85 % du détour LoadArea mesuré |
| Compteurs processus durant pack, L16709 | 55 127 lectures, 225 617 304 octets | À attribuer par fichier/thread ; pas 55 127 fichiers ni preuve de 55 127 accès disque physiques |
| Pages carte observées, L16967 | 27 grandes textures, **432 MiB** de niveau de base soumis | Empreinte logique élevée ; pas mesure de résidence VRAM physique |
| Cache GPU animations réel, L16970 | 222 requêtes, 144 hits, **78 misses / uploads**, **0 éviction** ; **209,65 MiB** résidents logiques | Pas de thrashing démontré ; cache 128 entrées suffisant sur cet extrait |
| Processus, L16969 | working set **875,93 MiB**, privé **1 881,78 MiB** ; delta privé ≈983 MiB | Deux mesures distinctes, à ne pas additionner ; pas preuve de fuite sur 9,5 s |
| Défauts de pages, même fenêtre | 213 541 | Pas preuve de swap disque : défauts mineurs et majeurs non séparés |
| Uploads non compressés, L16967 | 2 104 appels / 459 827 040 octets ; 726 suppressions | Compteurs transversaux, attribution sprites/occlusion/animations inconnue |

Les budgets CPU/GPU 64/96/128/256 MiB des lignes suivantes sont **des simulations**, pas la configuration des caches réels. Sur cette trace, 96–128 MiB GPU prédisent des rechargements ; 256 MiB contient les 78 frames observées. Ne pas généraliser ce seuil aux autres zones.

Le catalogue sprites annonce 14,67 milliards d'octets d'index répartis en 828 shards chargés progressivement : **ce volume n'est pas une allocation RAM de 14,67 Go**.

Les compteurs I/O sont ceux du processus ; les autres threads peuvent contribuer. Les fautes de pages incluent des défauts résolus sans lecture disque. Références : [Microsoft, IO_COUNTERS](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-io_counters), [Microsoft, Working Set](https://learn.microsoft.com/en-us/windows/win32/memory/working-set).

## 4. Causes et opportunités établies dans le code

Préfixe des chemins ci-dessous : `engine/InfinityEngine-Enhancer/source-patchee/src/iee/`. Les lignes se rapportent au checkout indiqué en §2.

| Priorité | Constat code | Référence | Portée de la preuve |
|---|---|---|---|
| **P0** | Chaque Demand instrumenté capture un resref et un snapshot processus avant le test du diagnostic détaillé | [hooks.cpp](../engine/InfinityEngine-Enhancer/source-patchee/src/iee/hooks.cpp), L4012–4031 | Actif avec `PerformanceLogs=true`, y compris page résidente |
| **P0** | Snapshot = `GetProcessMemoryInfo` + `GetProcessIoCounters` + `GetProcessHandleCount` | [process_resource_telemetry.cpp](../engine/InfinityEngine-Enhancer/source-patchee/src/iee/core/process_resource_telemetry.cpp), L12–39 | Jusqu'à trois interrogations système par appel ; environ 22 194 à chaque image chaude observée. Coût en ms non isolé |
| Mesure | Chrono Demand commence après snapshots/préparation ; cumul limité aux matérialisations | `hooks.cpp`, L4070–4079 ; [pvr_demand_telemetry.cpp](../engine/InfinityEngine-Enhancer/source-patchee/src/iee/core/pvr_demand_telemetry.cpp), L98–111 | Les temps affichés omettent le coût du hook autour du natif et les appels chauds |
| Mesure | Capture/hash des 128 entrées du cache uniquement lorsque pointeur initialisé par consume | `hooks.cpp`, L3573–3593, L4256 et L4345 | **Inactif ici**, car consume=false ; ne pas lui attribuer les 48 ms |
| **P1** | Logger synchrone et `flush_on(info)` | [logger.cpp](../engine/InfinityEngine-Enhancer/source-patchee/src/iee/core/logger.cpp), L20–29 | Surcoût possible, pas chronométré ; 71 traces occlusion et 26 traces pages dans cette session |
| **P1** | `prepare()` lit toutes les frames du pack avant publication | [area_animation_x4_registry.cpp](../engine/InfinityEngine-Enhancer/source-patchee/src/iee/area_animation_x4_registry.cpp), L178–194, L674–903, L1346 | Goulot LoadArea mesuré. `read_file()` demande déjà une lecture en bloc ; ne pas annoncer qu'un simple remplacement d'itérateur le corrige |
| **P2** | Payload sprite manquant : lecture, SHA256, décompression dans la composition, sous mutex | [creature_sprite_x2.cpp](../engine/InfinityEngine-Enhancer/source-patchee/src/iee/creature_sprite_x2.cpp), L1189–1268, L4289 | Code synchrone avéré ; part de la saccade non mesurée |
| **P2** | Composite Character : cache CPU 32 entrées / 4 MiB, mais nouvelle texture et upload pour le draw | Même fichier, L135–142, L1742, L4395, L4477 | Réutilisation GPU potentielle ; préserver durée de vie dans la file native |
| À profiler | Travail par tuile : décodage, contrôles, sélection page et rendu | [tile_render.cpp](../engine/InfinityEngine-Enhancer/source-patchee/src/iee/features/tile_render.cpp), L120 et suivantes | Multiplié par 7 295 draws ; ne pas enlever les contrôles de pluie/identité pour gagner du temps |

Des avertissements de composites sprites non encore compatibles apparaissent au démarrage ; le moteur conserve alors son rendu natif. Ils justifient une préparation plus précoce, pas une conclusion sur la cause principale PVR. Le bridge d'occlusion est configuré actif mais son coût effectif n'est pas isolé dans cette session ; **le désactiver changerait potentiellement le rendu**.

## 5. Travail antérieur : réutilisable, mais insuffisant

Références facultatives : [préparation off-frame](../engine/InfinityEngine-Enhancer/source-patchee/docs/map-page-offframe-preparation.md), [B2e](../engine/InfinityEngine-Enhancer/source-patchee/docs/validation/map-page-offframe-phase3b2e.md), [B2f](../engine/InfinityEngine-Enhancer/source-patchee/docs/validation/map-page-offframe-phase3b2f.md).

- **Prewarm natif :** appel `Demand` sur le thread de rendu après swap ; budget testé **après** une page (`map_page_prewarm.cpp`, L645–684). Un budget annoncé de 8 ms n'interrompt pas un appel de 40 ms ; il bloque l'image suivante.
- **Préparation CPU B2f :** quatre claims maximum par génération, une page prête maximum (`core/map_page_shadow.h`, L17–27). Le plafond est expérimental, pas une exigence produit.
- **Ouverture carte :** première expansion annule la préparation CPU (`map_page_prewarm.cpp`, L541–558). Protection contre concurrence ; aucune anticipation suffisante de la vue cible.
- **Collision :** le fallback peut attendre la fin du worker (`core/map_page_shadow.cpp`, L316–336) ; le fichier reste ouvert pendant l'inflate (L222–230). Cette attente précède le chrono Demand.
- **Travail doublé :** worker lit/décompresse ; natif conserve la demande ressource ; consommation remplace essentiellement zlib par validation CRC et copie. Pas de suppression générale des lectures natives.
- **Historique B2e :** 17 pages préparées pour quatre consommées ; deux attentes de retirement totalisant 67,59 ms. Un préchargement trop large peut aggraver le chemin critique.
- **Historique B2f :** un passage sur quatre zones, cache OS chaud ; quatre pages préparées avant chaque premier dézoom. Couverture 4/19 AR0900 et 4/81 AR0700N ; comportement d'ouverture immédiate non démontré. DLL corrigée après ce passage non retestée ingame selon le rapport.

Conserver : worker sans accès objets moteur/GL, identité des octets, ownership explicite, invalidation par génération, compatibilité native et replis sûrs. Reconcevoir : couverture, priorité, admission mémoire, publication et gestion des collisions. **Ne pas supprimer une attente ni augmenter un quota sans traiter sa raison d'existence.**

## 6. Plan d'action corrective

Les étapes ci-dessous sont des propositions pour une future implémentation autorisée. Chaque étape produit une modification autonome et une comparaison ciblée ; aucune compilation globale ou intervention release n'est nécessaire pour ce document.

### A — Corriger les diagnostics avant de choisir une architecture lourde

**Périmètre :** `hooks.cpp`, télémétrie PVR/processus, configuration des traces.

1. Déplacer resref, cache et snapshots détaillés dans une branche explicitement activée pour le diagnostic de matérialisation. Collecter les ressources processus périodiquement, pas par tuile.
2. Garder l'appel natif autoritatif sur le chemin résident ; l'optimisation initiale enlève le diagnostic superflu, **pas** les transitions/références natives.
3. Séparer `hookTotal`, `nativeDemandCold`, `nativeDemandResident`, préparation/attente, lecture, inflate/copie et upload CPU. Mesurer les hits par échantillonnage ou compteurs locaux agrégés ; éviter de remplacer trois appels système par une autre sonde coûteuse.
4. Profil de jeu : proposer `EnableTilePageDiagnostics=false`, `EnableNativeOcclusionProbe=false`, `DumpEngineShaders=false`. Conserver `EnableNativeOcclusionBridge`, shaders et assets. Réserver les traces détaillées aux essais courts.
5. Émission groupée/queue bornée des INFO ; erreurs critiques persistées immédiatement. Garder compteurs minimaux de sécurité quand les logs détaillés sont coupés. Découpler à terme activation des optimisations et `PerformanceLogs`.

**Livrable :** candidat runtime léger + mesure externe ou présentation agrégée peu intrusive. Comparer au même réglage visuel. Un A/B global `PerformanceLogs=false` peut estimer l'effet observateur, mais supprime les compteurs internes : il exige une mesure de frames indépendante.

**Critère :** zéro capture processus par hit résident ; coût instrumentation documenté ; comparer de nouveau les ≈48 ms chauds. Gain probable, amplitude inconnue. Cette étape n'enlève pas les 19 pages froides.

### B — Préparer la vue cible sans blocage dans le dézoom

**Solution principale :** anticipation des pages et résidence contrôlée, à qualité identique.

1. Construire les dépendances de la **variante actuellement active** : pages de la vue initiale, puis vue complète cible, overlays réellement nécessaires. Priorité spatiale/échéance ; pas simple ordre numérique de la table ni chargement de toutes les variantes jour/nuit.
2. Déclencher dès que la zone et sa variante sont connues, pendant le chargement existant et les marges disponibles ; capter l'intention d'ouverture carte avant sa première expansion. Un signal seulement après élargissement arrive trop tard.
3. Worker CPU borné : lecture → fermeture du handle → décompression/validation → résultat immuable. Commencer par un worker ; augmenter seulement si la mesure démontre un bénéfice sans contention.
4. Séparer états `lecture en cours`, `handle fermé`, `CPU prêt`, `upload soumis`, `texture utilisable`. Une page périmée n'est jamais publiée ; invalidation zone/variante/asset/contexte explicite.
5. Résoudre le conflit avec le lecteur natif : buffers privés, protocole de fermeture et ownership établis. Aucun `condition_variable.wait` sur le rendu pour une préparation facultative. Si la voie native requiert une coordination, l'achever avant le rendu ; ne pas retirer la protection actuelle seule.
6. Publication native/GL sur le thread et contexte autorisés. Préserver références, allocations/libérations, cache moteur et retour natif. Réutiliser d'abord la frontière zlib éprouvée ; suppression de la double lecture dans un second changement, après preuve du cycle de vie.
7. Planifier uploads par **octets et temps disponible**, avec marge de frame et coût récent par taille. Une limite d'une page/frame ou 8 ms après l'appel n'est pas un plafond de blocage. Les uploads monolithiques trop longs doivent être anticipés ; découpage compatible à étudier seulement si nécessaire.
8. Conserver les pages de la zone active pour les réouvertures tant que le budget le permet ; surveiller relectures, évictions et pression réelle. Réserve pour UI, sprites, effets et moteur.

**Ouverture immédiatement après chargement :** pas de garantie « instantané + zéro attente + pixels exacts » lorsque les données ne sont pas prêtes. Deux comportements compatibles avec la qualité : préparer la vue complète avant de rendre la zone interactive, ou conserver la vue courante réactive jusqu'à disponibilité puis lancer la transition. Mesurer cette latence explicitement ; ne pas déplacer 800 ms dans une attente cachée et appeler cela une accélération. Préférer le recouvrement avec le chargement déjà nécessaire.

**Critère :** parcours cible sans lecture/inflate/attente worker synchrone pendant l'animation ; aucune tuile absente, substitution x1, frame d'eau abandonnée ou texture obsolète. Chargement total et temps jusqu'à carte prête mesurés en plus des frames.

### C — Alternative complémentaire : cache persistant PVR déjà décompressé

À envisager si la mesure fine confirme un coût important de décompression ou si l'anticipation CPU reste trop tardive.

- Stocker en cache dérivé les payloads PVR contenant **les mêmes blocs DXT**, après décompression zlib ; aucune recompression avec perte ni conversion en RGBA nécessaire.
- Identité par contenu/version ; écriture atomique ; validation et repli sur source en cas de cache absent/périmé. Ne pas modifier directement les sources installées ou la release pour l'essai.
- Lecture en tâche de fond, puis même protocole de publication que B ; le fichier mappé à lui seul ne garantit pas l'absence de fautes de pages bloquantes.
- Compromis : stocker le résultat dézippé augmente généralement le volume à lire. Les 304 MiB de blocs et ≈117 MiB de lectures comptées donnent des ordres de grandeur, **pas un ratio de taille établi** : sommer les tailles réelles des 19 PVRZ et de leurs payloads pour le calculer. Peut accélérer un cas CPU limité et ralentir un stockage froid ; mesurer les deux.
- Borne disque/RAM et éviction par contenu ; pas de copie infinie de tous les assets.

**Position :** option mesurable, pas remplacement automatique de B. Le prototype zlib actuel ne suffit pas à éviter l'I/O native ; une adoption directe du cache exige un contrat natif établi.

### D — Rendu chaud : enlever le travail répété, puis réduire les soumissions

À décider avec les nouvelles mesures après A ; traiter en parallèle de B si le coût chaud persiste.

1. Profiler les 7 295 tuiles : décodage/contrôles, demandes résidentes, configurations texture, uniforms, soumissions et temps GPU. Utiliser des queries GPU lues ultérieurement si disponibles ; aucun `glFinish` systématique pour mesurer.
2. Mettre en cache par génération les informations **immutables** de tuile/page/UV ; invalider texture supprimée, réutilisation d'identifiant, changement de contexte/zone/variante. Garder les décisions dynamiques eau/pluie/portes/animation.
3. Regrouper les opérations consécutives compatibles en conservant ordre de rendu, shader, texture, blend, clips et masques. Pas de tri global des calques transparents. Dédupliquer seulement les états dont l'équivalence est démontrée.
4. Si le nombre de draws reste dominant : préparer une géométrie statique par blocs spatiaux, conserver couches dynamiques séparées et culling exact. Aucun objet encore visible ne doit disparaître parce que son centre sort du viewport.

**Alternative plus coûteuse :** cache de rendu du fond statique en blocs, réutilisable dans la vue carte. Exige invalidation portes/états de zone et superposition fidèle du brouillard, marqueurs, eau et animations. Maintenir précision et filtrage à chaque zoom ; une capture unique basse résolution ou figée ne satisfait pas l'exigence qualité. À retenir seulement si elle bat le regroupement de géométrie sans pic de préparation ni surcoût mémoire excessif.

**Critère :** coût chaud réduit à contenu identique ; mêmes contours, coutures, alpha, eau, pluie et fog. Ne pas promettre 60 Hz avant attribution du temps restant.

### E — Chargements généraux et réutilisation des ressources

| Chantier | Intervention proposée | Condition / critère |
|---|---|---|
| Animations de zone | Préparation CPU hors rendu, ordre première vue/prochaines phases, publication atomique par génération ; upload anticipé | Enlever les ≈138 ms de lecture du chemin interactif sans pack incomplet ni ralentissement d'animation |
| I/O animations | Mesurer fichier/thread/taille/durée ; conteneur indexé contigu seulement si bénéfice démontré | `read_file()` lit déjà en bloc au niveau C++ ; un conteneur seul ne prouve pas moins d'I/O système |
| RAM des animations | Éviter coexistence durable de copies CPU/GPU inutiles ; garder données nécessaires à rechargement/recréation de contexte | Mesurer pic à transition ; ne pas évincer des frames imminentes pour afficher un budget artificiellement bas |
| Payloads sprites | Étendre le worker existant aux frames probables ; publier buffers prêts ; garder identité, SHA et décodage inchangés | Pas de lecture/décompression sous mutex du rendu sur un hit préparé ; ne pas charger les 828 shards par défaut |
| Composites Character | Cache GPU immutable avec clé complète : couches, frames, palettes réalisées, géométrie, échelle, encodage, génération | Éviter création/upload/delete sur vrais hits ; aucune réécriture d'une texture encore référencée par la file native |
| Occlusion | Réutilisation buffers/ressources seulement si profil attribue un coût réel | Garder masque/alpha/dithering et ordre ; ne pas couper le bridge visuel |

Budget : cumuler explicitement bytes CPU, GPU logiques, staging et ressources natives ; limites d'entrées **et** d'octets. Sur cette seule zone, carte et cache animations représentent déjà ≈642 MiB de niveaux de base GPU logiques, avant les autres domaines. Un plafond GPU global de 128 MiB serait incompatible avec leur conservation intégrale. Ajuster au matériel et à la pression mesurés ; la session ne fournit ni capacité VRAM ni taux de saturation CPU/GPU.

## 7. Ordonnancement et critères de sortie

| Lot | Dépendance | Sortie attendue | Risque principal |
|---|---|---|---|
| **A : instrumentation légère** | Aucun | Candidat local + coût froid/chaud fiable | Perdre une observation utile ; garder compteurs minimaux |
| **B1 : préparation utile** | A | Toutes les pages de la vue cible prêtes selon politique explicite ; aucune attente worker dans rendu | Concurrence lecteur natif / publication périmée |
| **B2 : éviter travail doublé**, C optionnel | B1 + profil I/O/inflate | Lecture/décompression réellement évitée, chargement total amélioré | Ownership natif, invalidation, volume disque |
| **D : rendu chaud** | A ; B non bloquant | Coût par tuile et soumissions réduits | Réordonner des calques ou réutiliser un état devenu faux |
| **E : animations/sprites** | A ; livrables indépendants | Première apparition et transitions améliorées | Pop-in, mutex, durée de vie des textures |

### Protocole ciblé proposé pour les futurs candidats

- Base : même sauvegarde AR0900, résolution, zoom, assets et options visuelles. Distinguer premier accès du processus et cache OS réellement froid ; cette capture ne prouve pas que le cache OS était froid.
- Scénarios : ouverture immédiate après chargement ; ouverture après préparation ; fermeture/réouverture ; maintien de la carte complète ; retour au jeu ; recharge de la même zone ; transition de zone pour E. Autres maps/variantes seulement dans un essai distinct explicitement décidé.
- Relever par scénario : intervalle frame p50/p95/p99/max, nombre >33,3 / >50 / >100 ms, temps jusqu'à carte complète prête, latence de chargement totale, CPU par phase, temps GPU disponible, bytes lus/décodés/uploadés, pics mémoire, attente worker et réutilisations/évictions.
- Répéter suffisamment pour distinguer gain et variation de cache, par exemple cinq ouvertures immédiates indépendantes et dix réouvertures chaudes ; ne pas calculer une garantie p99 avec les seuls huit échantillons présents.
- Hypothèse cible à 60 Hz : budget nominal **16,67 ms** ; viser p95 ≤18 ms, p99 ≤25 ms et aucun blocage récurrent >50 ms dans le dézoom. Seuils proposés, à confirmer avec la présentation réelle de cette machine. Garder les animations prévues à 30 FPS.
- Contrôler qualité à temps/caméra identiques : captures du fond statique et de ses coutures ; séquence pour eau, sprites, fog, sélection, occlusion, portes et changements d'état. Aucun asset réduit ni délai d'animation ajouté pour obtenir les chiffres.
- Réussite = fluidité **et** chargement total documentés, mémoire bornée sans évictions cycliques ni croissance après cycles répétés. Tester la recréation de contexte si des textures/caches nouveaux la concernent.
- Repli indépendant par fonctionnalité et génération ; jeu/InfinityLoader fermés avant toute future installation. Les états production, QA, installation et release restent séparés.

## 8. Pistes écartées en première intention

| Piste | Motif |
|---|---|
| Activer simplement le prewarm / passer de 4 à N pages | Appels synchrones, collisions et couverture non résolus |
| Augmenter pool natif ou RAM sans mesure | Aucune preuve de saturation/éviction dans la rafale ; ne supprime pas le premier chargement |
| Baisser texture, filtre, eau, animation ou bridge | Contredit la qualité demandée |
| Ralentir le dézoom / imposer un FPS plus bas | Masque le symptôme et réduit la réactivité |
| PBO / contexte GL partagé comme première réponse | Upload CPU minoritaire dans le Demand mesuré ; complexité et mémoire supplémentaires. PBO utile seulement avec recouvrement réel et sans réutilisation prématurée du buffer : [Khronos, Pixel Buffer Object](https://wikis.khronos.org/opengl/Pixel_Buffer_Objects) |
| Découper automatiquement 4096² en 2048² | Peut réduire un pic par page mais multiplie entrées/gestion et modifie les assets ; capacité native à considérer |
| Précharger tout le catalogue ou toutes les maps | Travail inutilisé, concurrence I/O et empreinte mémoire disproportionnés |
| Accuser uniquement GPU, zlib, SSD ou swap | Les scopes disponibles ne permettent pas cette attribution exclusive |

**Premier changement recommandé pour une prochaine tâche : lot A.** Il enlève un défaut concret du chemin le plus fréquent, préserve le rendu et donne une base fiable pour dimensionner B, D et E.
