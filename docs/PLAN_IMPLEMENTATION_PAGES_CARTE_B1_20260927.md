# Carte — conception du correctif B1, 2026-09-27

Statut : **analyse de code ; aucun nouveau correctif compilé/installé**. Base : A1 installé, SHA256 DLL `10FBD4652DC6E6AD8BFA0FE5CB8F4950352970E438BC2FBBC47D554B28BD1FD2`.

Références : [analyse initiale](ANALYSE_FLUIDITE_CARTE_CHARGEMENTS_20260927.md), [mesures A1, § Premier retour utilisateur](PVR_DIAGNOSTICS_A1_20260927.md). Ci-dessous, `E = engine/InfinityEngine-Enhancer/source-patchee` ; chemins et symboles priment sur numéros de ligne.

## 1. Décision technique

**Coder un nouveau chemin de préparation anticipée, distinct du prototype de diagnostic.** Réutiliser le parseur PVRZ, la validation de substitution et la frontière native zlib ; remplacer l'ordonnancement et la file qui attend le worker.

- Premier candidat : AR0900, variante active, préparation CPU dès publication d'une identité WED fiable ; consommation des pages prêtes aux demandes natives ; préchargement natif opportuniste seulement après validation de cette consommation.
- Entrées du worker : **copies privées indépendantes des PVRZ**, préparées hors jeu pour le candidat. Aucun accès du worker aux fichiers `override` utilisés par le moteur. Cache absent/périmé : chemin natif immédiat, aucune reconstruction pendant le rendu.
- Une file bornée couvre les dépendances de la zone ; suppression du quota expérimental de quatre consommations et de l'arrêt au premier dézoom **uniquement dans le nouveau mode**.
- Option C, ultérieure ou comparative : stocker les PVR déjà décompressés, avec exactement les mêmes blocs DXT. Ne pas imposer ce volume disque supplémentaire avant comparaison lecture/inflate.
- Opt-in séparé de `PerformanceLogs`, désactivé par défaut, incompatible avec l'ancien probe/consume pendant un même essai. Les options proposées dans ce document n'existent pas encore.

**Limite explicite : B1 seul ne garantit pas une ouverture immédiate sans saccade.** Un miss repasse immédiatement au natif, qui peut bloquer pour lire/décompresser. Le critère « aucune lecture/inflate pendant le dézoom » du rapport initial reste un objectif final, pas une propriété de ce premier candidat.

## 2. Constats qui déterminent le code

| Code / preuve | Conséquence |
|---|---|
| `E/src/iee/map_page_prewarm.cpp::build_plan` | Plan tardif, contexte GL obligatoire, uniquement `pTileSets[0]`/`tis[0]`, ordre de la table ; ne couvre pas explicitement tous les overlays/variantes actives |
| `::on_post_swap` | Dépend de PerformanceLogs, délai configuré de 30 frames, programmation JIT à une page ; budget vérifié après Demand |
| `::notify_wide_view_expansion` | Annule au premier élargissement déjà observé ; signal trop tardif pour anticiper l'ouverture |
| `E/src/iee/core/map_page_shadow.h` | Une seule page prête / 20 MiB ; quatre claims par génération |
| `map_page_shadow.cpp::prepare_pvrz_file` | Le `ifstream` reste ouvert pendant `prepare_pvrz_bytes`, donc pendant inflate |
| `::retire_not_ready_locked`, `::claim`, `::observe` | Fallback susceptible d'attendre le worker ; `inspect` prend aussi un mutex bloquant |
| `E/docs/validation/map-page-offframe-phase3b2c.md` | Collision de lecture documentée : native file-open échoue avec erreur 32, puis crash sur `A090010` |
| `E/docs/validation/map-page-offframe-phase3b2d.md` | L'attente a été introduite pour protéger ce fallback ; la retirer seule réintroduit le défaut |
| `E/src/iee/hooks.cpp::detour_pvr_uncompress` | Substitution limitée au callsite manifesté ; CRC de la source native puis memcpy vers le buffer alloué par le natif |
| `::detour_load_area` | Après l'appel moteur : `refresh_wed_cache`, puis `swap_area_animation_pack`, puis publication CPU de vue |
| `::publish_view_state` | Réévalue l'aire visible et son WED ; changement jour/nuit possible sans nouveau LoadArea ni changement du pointeur aire |
| `E/src/iee/game/wed_runtime.*` | `tintTileCandidates` est un échantillon borné destiné aux teintes, pas une carte complète cellule → page |

Dernière session A1 : trois premières images = 814,81 ms ; 755,60 ms de Demand matérialisants dont 22,12 ms d'upload CPU ; résiduel 733,20 ms. **Ce résiduel n'est pas une mesure isolée de zlib.** Cinq images chaudes : moyenne 41,88 ms. Deux problèmes restent distincts : arrivée des pages froides et coût du rendu de la vue complète.

## 3. Entrées privées : supprimer la cause du handshake

### Format du candidat

Nouvel outil `E/tools/map_page_cache_builder.cpp`, réutilisant `core::prepare_pvrz_file` ; cible CMake dédiée. Le petit outil `map_page_shadow_preflight.cpp` fournit déjà l'accès au parseur commun.

1. Jeu fermé : lire WED/TIS et PVRZ de la seule variante ciblée ; résoudre les dépendances réellement installées. Ne pas prendre une liste de pages déduite uniquement des logs comme inventaire complet.
2. Copier les PVRZ dans un répertoire dérivé neuf, hors `override`, résolu via configuration locale. Fichiers physiques indépendants : pas de hardlink, symlink ou jonction vers les sources.
3. Manifeste privé versionné : aire/WED/TIS, empreintes des fichiers de dépendances, page resref/numéro, nom privé, taille source, CRC du flux après le préfixe u32, taille décodée, dimensions/format, empreinte de contenu de la copie.
4. Construire dans un répertoire temporaire du candidat ; publier le manifeste en dernier. Aucun remplacement de cache ouvert par le runtime ; utiliser une nouvelle génération de répertoire.
5. Une limite disque et une sélection explicite de zone bornent le candidat. Aucun changement aux PVRZ/TIS/WED installés, aux sauvegardes ou à la release.

Runtime : charger l'index hors chemin par tuile ; vérifier les fichiers privés et leurs octets sur le worker. Conserver le contrôle CRC de la source **native** avant substitution : un cache ancien ne doit jamais changer les pixels de la version installée. CRC = garde de compatibilité existante, pas preuve cryptographique d'identité ; les empreintes du manifeste servent au contrôle du cache et de son installation.

Pourquoi cette duplication : fermer le handle avant inflate réduit la fenêtre de collision, mais ne protège pas la lecture elle-même. Les copies privées retirent le partage du même fichier de ce protocole. Elles ne suppriment ni concurrence sur le disque/cache OS, ni lecture native.

Alternative écartée pour B1 : injecter directement `CRes::pData`, détourner le lecteur natif ou alimenter le LRU à la main. Le contrat d'ownership nécessaire n'est pas établi ; aucun nouvel offset ne doit être inventé.

## 4. Plan CPU précoce et liaison native tardive

Séparer deux structures :

```cpp
// Noms proposés ; données CPU seulement, aucun pointeur moteur/GL au worker.
struct PageKey { Generation generation; Resref tis, page; int pageNumber; };
struct PageJob { PageKey key; PrivateCacheEntry entry; Priority priority; };
struct NativeBinding { PageKey key; void* wrapper; void* tis; void* pvr;
                       uint32_t tileIndex; ContextEpoch contextEpoch; };
```

- `detour_load_area` : invalider les anciennes intentions avant dispatch. Après `refresh_wed_cache`, proposer le snapshot WED publié **avant** `swap_area_animation_pack` ; viser le recouvrement avec son coût observé d'environ 138 ms, sans l'allonger volontairement.
- Cette première identité peut encore être celle de l'aire sortante. La traiter comme spéculative ; si aucune identité fiable n'est disponible, différer. Aucun cast arbitraire de `pAreaNameString` ; aucun accès GL dans LoadArea.
- `publish_view_state` : confirmer/remplacer le plan lorsque aire/WED/variante réellement visibles changent. Une proposition identique est idempotente ; pas de nouvelle génération à chaque frame.
- Utiliser les dépendances du manifeste privé pour soumettre les jobs avant que les wrappers natifs soient disponibles. La correspondance aux ressources natives n'est construite/validée que sur le thread moteur approprié.
- Première priorité : pages de la vue courante, puis union des pages de la vue complète ; overlays utilisés, portes/indices alternatifs et frames de tuiles inclus dans l'inventaire. Dédupliquer par identité de page, pas par pointeur de wrapper.
- Pour une priorité spatiale exacte : extraire le mapping complet WED → indices TIS → pages dans le builder ou un parseur CPU dédié. Réutiliser `tintTileCandidates` serait incorrect. Un premier ordre déterministe sans priorité spatiale est possible, mais doit être annoncé comme tel.
- Parcourir les ensembles actifs nécessaires, pas seulement overlay 0. Respecter le wrapper sec/pluie réellement sélectionné ; une variante non identifiée reste native. Ne pas préparer automatiquement jour et nuit ensemble.
- Aucune dépendance à `wglGetCurrentContext()` pour le plan CPU. La publication GPU garde cette exigence.

Invalider : changement aire/WED/variante, version du cache, reset du runtime. Recréation GL : invalider les bindings et états de résidence ; un buffer CPU n'est réutilisable qu'après nouvelle validation de son identité. Une ancienne génération ne publie jamais dans la nouvelle.

## 5. Nouvelle file : absence d'attente du rendu et mémoire bornée

Créer `E/src/iee/core/map_page_prepare_queue.{h,cpp}`. Ne pas changer silencieusement la sémantique de l'ancienne `MapPageShadowQueue` : ses tests de handshake protègent encore l'ancien mode.

API proposée :

```cpp
SubmitResult try_submit(PageJob);          // file pleine/occupée : différer
ClaimResult try_claim(PageKey) noexcept;   // Ready, NotReady, Busy, Stale, Missing
void request_generation(Generation) noexcept; // publication légère, pas de purge lourde
void request_stop() noexcept;
// Le worker peut attendre ; le thread de rendu ne le peut pas.
```

- Un worker, priorité basse existante ; réutiliser `ProcessLifetimeWorker` et son maintien en vie de DLL. Join seulement au shutdown explicite sûr, jamais dans DllMain ou pendant un changement de zone visible.
- Réserver les octets **avant** lecture/allocation. Comptabiliser compressé en vol + décodé en vol + prêts + claim détenu par le moteur + buffers périmés en attente de destruction. Les annulations ne rendent pas un crédit avant libération réelle.
- Valeur de départ proposée : 128 MiB supplémentaires CPU, 96 descripteurs maximum, limites existantes par page 32 MiB compressés / 20 MiB décodés. Ce sont des bornes de conception à mesurer, pas des réglages validés.
- Ne pas confondre budget CPU privé et mémoire native/GPU : les buffers d'allocation natifs et textures demandent un suivi distinct. Préserver une réserve dans le pool natif de 128 entrées ; 96 pages planifiées ne prouvent pas qu'il reste 32 entrées libres.
- Admission/backpressure côté worker. `try_claim` : `try_lock` ou slots atomiques à ownership explicite ; aucun `condition_variable.wait`, I/O, allocation de gros buffer ou journal synchrone. `Busy` se comporte comme un miss.
- Pool borné de buffers réutilisables : transfert d'ownership au claim ; retour dans une file de recyclage préallouée après Demand. Libération lourde hors rendu, hors mutex partagé. Dimensionner la file pour tous les buffers en circulation ; aucun fallback qui détruit plusieurs pages sous le verrou.
- Invalidation par génération atomique ; nettoyage différé. Si l'ancien job finit après invalidation, rejet puis recyclage sur worker. Tests dédiés aux changements de génération pendant read/publish/claim.
- Miss natif : invalider le résultat désormais inutile pour cette page, sans attendre sa lecture privée. Ne pas annuler les autres pages au premier dézoom. Ne pas relancer continuellement une page déjà devenue résidente.

La trace initiale compte 432 MiB de grandes textures soumises : conserver simultanément toutes leurs copies CPU ajouterait un volume comparable. Le budget proposé suppose un pipeline préparation → consommation → recyclage ; il ne peut garantir toute la carte prête en RAM avant usage.

## 6. Consommation : préserver le propriétaire natif

Nouveau module `E/src/iee/map_page_prepare.{h,cpp}` pour planification/bindings, appelé depuis `hooks.cpp`. Conserver le passage par `CResPVR::Demand` et son LRU, ses références, ses allocations et ses uploads.

```text
detour_pvr_demand(pvr):
    si mode inactif ou texture déjà résidente : original exactement une fois
    sinon : valider binding ; try_claim(page)
    installer le claim dans un scope TLS imbriquable
    appeler original exactement une fois
    restaurer le scope TLS précédent ; recycler le buffer ; agréger les compteurs

detour_pvr_uncompress(dst, capacity, src, size):
    sans claim / autre callsite : original zlib
    vérifier retour manifesté, ressource, ptr source natif + 4, tailles, génération
    vérifier CRC natif et stabilité du propriétaire ; copier les octets validés
    écrire taille produite ; retourner Z_OK
    au moindre rejet : original zlib, sans attendre de nouvelle préparation
```

- Réutiliser `PvrConsumeEvidence` et les validations mémoire existantes ; validation de build/callsite dans `game/build_manifest.*`, pas d'offset hors manifeste.
- TLS : restaurer l'ancien scope en cas de réentrance ; ne pas laisser un claim de page A servir à une demande B. Le claim reste vivant jusqu'au retour complet du natif.
- Distinguer activation fonctionnelle et traces. L'early return `!enablePerformanceLogging` de Demand doit laisser fonctionner le nouveau mode ; les hooks de lifecycle détaillés ne deviennent pas obligatoires.
- Supprimer les INFO par décision du nouveau chemin ; compteurs agrégés. Aucun snapshot processus ou scan du LRU à chaque demande résidente : préserver le bénéfice A1.
- La substitution supprime **inflate seulement** sur un hit. Restent lecture `CRes::Demand`, allocation native, CRC, memcpy, parsing PVR, upload. Ne pas annoncer « chargement hors thread principal » pour l'ensemble de cette chaîne.

## 7. Préchargement GPU et ouverture immédiate

Après validation de la consommation à la demande, ajouter une pompe `on_post_swap` du nouveau module :

1. Contexte/thread corrects, identité native revalidée, marge estimée disponible.
2. Acquérir réellement un claim prêt avant tout préchargement ; pas de test Ready suivi d'un Demand susceptible de perdre ce claim. Transmettre la réservation au scope de consommation.
3. Appeler le Demand natif pour au plus une page admise ; mesurer coût complet. Si aucune page prête, passer la frame. Un échec ultérieur de validation peut encore déclencher le fallback natif : le signaler et arrêter les préchargements spéculatifs de cette génération.
4. Estimer le coût par taille à partir des appels récents, vérifier la marge **avant** admission ; plafonner aussi les octets. Un appel natif monolithique reste non préemptible : ce budget est souple, pas une garantie de 8 ms.
5. Surveiller les évictions natives réelles, pas toutes les suppressions GL de l'application ; interrompre l'anticipation en cas de pression/identité douteuse. Aucun LRU privé concurrent du moteur.

Un travail après SwapBuffers consomme du temps avant la présentation suivante ; il n'est pas gratuit. N'utiliser ni attente active ni `glFinish` pour déclarer une page prête. Distinguer upload soumis et disponibilité selon le chemin natif ; les chronos GL CPU ne mesurent pas la fin GPU.

**Cas immédiat non résolu par simple anticipation :** 138 ms de travail existant ne garantissent pas le recouvrement de toutes les préparations. Aucun hook d'intention `CScreenMap`/`ScreenMap` n'a été trouvé dans `src/iee` lors de cette revue ; cela ne prouve pas son absence dans l'exécutable.

Pour garantir l'animation fluide si les pages sont encore manquantes : établir un signal pré-transition puis conserver la vue courante réactive jusqu'à disponibilité, ou terminer la préparation avant interactivité. Ce travail exige l'identification et la validation d'une nouvelle frontière native, avec latence visible mesurée. Ne pas ralentir arbitrairement le zoom, afficher du x1, figer l'eau ou cacher les tuiles.

## 8. Découpage d'implémentation recommandé

| Lot | Fichiers / changements | Résultat vérifiable |
|---|---|---|
| B1.1 | Builder privé, manifeste, `map_page_prepare_queue.*`, CMake, tests | Sources séparées ; mémoire bornée ; claim/miss/annulation sans attente du rendu |
| B1.2 | `map_page_prepare.*`, `hooks.cpp` aux frontières WED/Demand/zlib, `core/config.*` | Démarrage précoce AR0900 ; consommation opportuniste au-delà de quatre pages ; mode autonome des diagnostics |
| B1.3 | Pompe native de préchargement et politique d'admission | Pages prêtes rendues résidentes avant usage quand la marge existe ; coût imputé aux frames |
| C conditionnel | Cache privé PVR décompressé, même validation/conso | À comparer si zlib domine ou si le worker arrive trop tard ; plus de disque/read, moins de CPU inflate |
| B2 conditionnel | Contrat lecteur natif / ressources | À étudier si lecture+allocation+copie restent dominantes après hits préparés |
| Transition conditionnelle | Nouveau hook d'intention et readiness | Nécessaire si l'ouverture immédiate reste saccadée malgré anticipation ; aucune promesse avant preuve du hook |

**Premier candidat à tester : B1.1 + B1.2**, avant activation de B1.3, pour isoler le gain et le taux de préparation utile. B1.3 reste nécessaire pour retirer du dézoom les uploads/lectures natives des pages préchargées. Si le candidat manque sa fenêtre de préparation, le résultat est un diagnostic d'ordonnancement insuffisant, pas une validation de fluidité.

## 9. Vérification utile lors du codage

Tests hôte ciblés dans `E/tests/iee_tests.cpp` + outil builder :

- Source/copied bytes identiques ; rejet cache tronqué/corrompu/périmé/format non supporté ; résultat décodé identique au parseur actuel.
- Worker retenu artificiellement en lecture : `try_claim` retourne NotReady/Busy sans dépendre de sa libération ; l'ancien test de handshake reste valable pour l'ancien mode.
- Admission pleine, annulation en vol, claim vivant au changement de génération, recyclage saturé : plafond respecté, aucun résultat périmé publié, pas d'interblocage.
- Appel zlib non ciblé, CRC mismatch, tailles/pointeur/retour incorrects, réentrance : fallback exact et un seul original ; mode fonctionne avec PerformanceLogs false.
- Plan : overlays, duplications, variantes/portes et changements WED ; wrapper invalide → natif. Préchargement sans Ready → zéro Demand supplémentaire.

Validation ingame du candidat : même sauvegarde/INI visuel, ouvertures immédiates puis différées puis chaudes ; transitions/retour zone et jour/nuit/pluie seulement pour les variantes prises en charge. Comparer plusieurs passages à A1, sans prétendre rendre le cache OS froid par simple redémarrage.

Compteurs agrégés : temps première identité → première page prête → plan CPU terminé → pages natives résidentes ; coverage à première expansion ; hits/misses/busy/stale ; attente worker sur rendu (= 0) ; read/inflate worker, zlib natif, CRC/copie, Demand total et upload CPU ; pics mémoire privée et résidences logiques ; latence LoadArea et carte disponible ; intervalles de présentation et nombre >33,3/50/100 ms.

Lecture de résultat :

- Hits nombreux mais pause inchangée → isoler le résiduel natif, ne pas multiplier les workers.
- Misses nombreux à ouverture immédiate → ordonnancement/fenêtre trop courte ; comparer C puis signal pré-transition.
- Première ouverture améliorée mais vue complète toujours ~40 ms → lot D du rapport initial (travail répété par tuile/soumissions), distinct de B1.
- Gain obtenu par attente déplacée ou mémoire croissante → ne satisfait pas l'objectif utilisateur.

## 10. État à la fin de cette analyse

- Livrable : ce plan ; aucune source C++/INI/DLL modifiée par cette analyse.
- A1 reste installé ; aucune nouvelle validation ingame, aucun test/build lancé pour ce document.
- Prêt à coder B1.1 + B1.2 sur les frontières connues. La suppression garantie de toutes les saccades demande encore mesure de la couverture immédiate, traitement du résiduel natif et du rendu chaud.
