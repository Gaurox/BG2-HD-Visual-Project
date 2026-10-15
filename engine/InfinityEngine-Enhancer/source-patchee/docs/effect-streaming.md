# Effets : cache mémoire streaming — 2026-10-15

Référence : [`docs/EFFETS_STREAMING_MEMOIRE_2026-10-15.md`](../../../../docs/EFFETS_STREAMING_MEMOIRE_2026-10-15.md), base `ec030f51` / productions `bf664e60`.
Périmètre : sources moteur, compositeur, tests hôte, candidat local DLL+INI. Aucun asset, fichier installé, preuve, acceptation ou fichier release modifié. Aucune exécution du jeu/InfinityLoader.

## Points d'entrée

| Responsabilité | Fichier / symbole (relatif à `source-patchee/`) |
|---|---|
| Catalogue v1/v2/v3, index RESREF, génération du pack | `src/iee/effect_animation_x4_registry.cpp::prepare` |
| Pixels partagés, admission, deux lecteurs | `src/iee/core/effect_frame_cache.{h,cpp}` |
| Fenêtres, profils ponctuels, petites ressources | `prefetch_resource`, `prefetch_window` |
| Identités, construction/destruction/session | `hooks.cpp::detour_effect_*`, `begin_occurrence`, `begin_session` |
| Réemploi d'adresse / retrait des horloges | `core/area_animation_timeline.*::occurrenceSerial`, `forget` |
| Cache GPU, queue native, descripteurs différés | `bind_frame_texture_locked`, `observe_gpu_retirements`, `release_gpu` |
| État GL brut autour du flush/upload | `game/scoped_effect_gl_state.h` |
| Budget des sorties masquées | `native_occlusion_bridge.cpp`, `reserve_scratch` / `track_scratch` |
| Configuration au démarrage | `core/config.*`, `dll_main.cpp` |
| Vérification PE hors jeu | `tools/verify_effect_streaming_abi.py` |
| Candidat sans installation | `tools/prepare_effect_streaming_candidate.py` |

## Contrats conservés

- RGBA lus exactement depuis `EFX4-<RESREF>-frame%03zu.rgba` ; taille exacte contrôlée sur le worker ; aucune transformation, interpolation, compression ou empreinte du payload au rendu.
- Catalogue résident, recherche RESREF canonique O(1), handle `{resourceIndex, frameIndex, generation}` ; catalogue et pixels ont des plafonds distincts.
- Dimensions/centres/cycles natifs, contrôleurs VVC, cadence QPC, alpha, clipping décor, NEAREST effets, shaders/AA personnages conservés.
- Tables v3 ponctuelles distinctes (`SPFLESHS`, `SPMETSWA`) ; phases v2 limitées à `ceil(nativeSlots × targetRate / nativeRate)`, queues inaccessibles exclues des fenêtres.
- Choix eager/streaming au démarrage ; pas de double payload ni de bascule à chaud. Eager conserve ses limites 512 ressources / 8 Gio.
- `InitBindings` attend catalogue + workers + débuts sous quota. Préallocation des trampolines avant pixels ; barrière hors `DllMain` et refresh de première carte conservés.

## Budgets et ordonnanceur

Clés `[Shaders]` ; `EnableEffectAnimationX4` reste le commutateur principal existant.

| Clé | Défaut | Portée |
|---|---:|---|
| `EnableEffectAnimationStreaming` | `true` | `false` = eager au prochain démarrage |
| `EnableEffectStreamingTrace` | `false` | Détails bornés ; agrégats publiés même sans détails |
| `EffectCpuCacheMiB` | 768 | Pixels prêts, réservations, lectures, leases/retraits inclus |
| `EffectInFlightMiB` | 32 | Sous-plafond inclus dans CPU ; frame trop grande => préparation refusée |
| `EffectHeadCacheMiB` | 256 | Deux premières phases de chaque cycle/profil, dédupliquées, sous quota |
| `EffectGpuCacheMiB` | 288 | Stockage retenu, au plus 64 descripteurs |
| `EffectMetadataMiB` | 16 | Catalogue, index, descripteurs CPU et enveloppes des structures bornées |
| `EffectPackGiB` | 512 | Payload déclaré admissible ; aucune réservation de cette taille |
| `EffectMaxResources` | 8192 | Indépendant des 64 slots GPU |
| `EffectPrefetchMs` | 500 | Horizon demandé, réduit si l'union épinglée ne tient pas |

- Queue 4096 jobs ; 4096 fenêtres d'occurrence ; 128 backings/fenêtre ; au plus 32768 pixels résidents. Tous configurés/bornés avant mise en route.
- Réservation avant allocation ; sorties chargées une seule fois ; `shared_ptr<const Pixels>` pendant upload. Le rendu ne lit aucun RGBA et n'attend aucun worker.
- Ordre : réparation courante P0, fenêtres P1 avec deadlines, signaux natifs P2, débuts/promotion P4. Déduplication des requêtes/lectures. Éviction LRU non épinglée, leases exclues ; libération des gros buffers hors mutex.
- Fenêtre remplacée atomiquement ; réduction de l'horizon puis demande courante si refus. Les petites ressources ≤8 Mio sont promues sans épinglage obligatoire.
- Pause : phase courante seule. Fenêtre sans observation depuis 2 s : désépinglée par worker, sans lire de pointeur natif ; renouvelée au retour à l'écran. L'identité et l'horloge de l'occurrence restent indépendantes.
- Session, destruction et reconfiguration invalident les intentions ; résultats obsolètes jetés avant publication. Échec de fichier mis en quarantaine pour cette génération de pack.
- Arrêt explicite : producteurs désactivés, génération invalidée, `CancelSynchronousIo`, join hors verrou/loader lock, puis buffers/catalogue. Un lease survivant reste compté ; redémarrage du cache refusé tant qu'il existe.
- Plafonds logiciels d'allocations contrôlées ; ils ne prétendent pas borner le working set global, le cache Windows ou les allocations internes du pilote.

## Hooks / GPU

Offsets/signatures uniquement dans `game/build_manifest.*`. Build BG2EE 2.7.3 étudié : SHA-256 `B51093A49140B2B8A7C046B4652BB8E535BE24EBBC12B1D735E0B94217A14D57`.

| Signal | RVA | Action |
|---|---:|---|
| `CVidCell` construction | `0x410E10` | RESREF copié, débuts anticipés, serial neuf avant appel original ; couvre BAM VVC/projectile |
| `CVidCell` destruction | `0x411200` | Retrait fenêtre + horloge du serial |
| VVC configuration | `0x254010` | Anticipation RESREF avant appel original |
| VVC direction/séquence | `0x2551F0` | Fenêtre après sélection native effective |
| `CInfGame::DestroyGame` | `0x272A20` | Nouvelle génération session |
| `wglDeleteContext` | export OpenGL | Retrait sur contexte propriétaire ; invalidation seulement après destruction réussie |

- Signatures et entrées `.pdata` vérifiées statiquement ; hook incompatible => échec fermé. Aucun détournement du decode projectile EEex ; API native utilisée pour éviter ce conflit.
- `DrawBindTexture` / `DrawEnd` ne prouvent pas un flush. Avant mutation d'un slot existant : état GL brut + `DrawPushState`, `DrawFlush_GL` (`0x42B350`), `DrawPopState`, restauration GL.
- Réemploi LRU des mêmes slots ; sous pression en octets, anciennes textures réduites à 1×1 après flush vérifié. Pas de `glFinish`, fences ou readback pour synchroniser.
- Table native 512 × `0x28`, slots 1…511 ; vérification nom GL / `deletePending` avant sélection d'une victime. Slots pending conservés et exclus du réemploi jusqu'à collecte native observée ou destruction du contexte.
- Changer de contexte ne prouve pas sa destruction : aucun ID de l'ancien contexte réutilisé silencieusement.
- Scratch effets : plafond séparé 64 Mio, sortie + masque comptés conservativement jusqu'à collecte du descripteur de sortie. Les sorties masquées ne sont pas partagées entre occurrences.
- Échec de masque => texture native découpée ; jamais exposition du backing non découpé. Tout fallback reste un échec de validation du scénario, sans modification du temps pour le cacher.

## Mesures

- Agrégats `Effect streaming CPU/GPU` : toutes les 5 s sur worker ; octets/pics, prêts/in-flight/épinglés/débuts/retraits, queue, hits/misses, déduplication, annulations, refus, expirations, durées queue/ouverture/lecture/publication, retard/avance minimale des fenêtres, uploads/durée CPU, flushs, slots pending, scratch, misses au premier submit.
- Détails `EFX_STREAM_ROW` sous `EnableEffectStreamingTrace=true` : buffer 4096 lignes, drops comptés ; epoch/QPC, serial/génération, RESREF/cycle, ponctuel/boucle, pause, slot/phase/backing, HD/masqué et résultat.
- `outcome` : 0 HD, 1 CPU non prêt, 2 fichier défaillant, 3 GPU refusé, 4 masquage refusé.
- Les lignes `swap=true` corrèlent les soumissions à un retour de swap réel. `firstSubmit` mesure une soumission, pas une preuve visuelle de première présentation ; cadence/visibilité et coût GPU réel exigent une QA utilisateur.
- Les timings de lecture incluent allocation/ouverture/lecture pour `readNs` ; `openNs`/`storageReadNs` détaillent le stockage ; `minReadyLeadNs` concerne les demandes P0/P1, pas le bootstrap P4.

## Vérification ciblée / reproduction

Depuis la racine du dépôt, build local : `build/iee-effect-streaming-20261015-v1` (VS 2019 x64 Release, dépendances locales spdlog/zlib/MinHook réutilisées).

```powershell
$env:MSBUILDDISABLENODEREUSE='1'
cmake --build build/iee-effect-streaming-20261015-v1 --config Release --target InfinityEngine-Enhancer iee_effect_frame_cache_tests iee_effect_animation_x4_registry_tests iee_effect_texture_cache_tests iee_tests iee_bridge_worker_tests iee_startup_barrier_tests iee_hook_preallocation_tests --parallel 4 -- /nodeReuse:false
ctest --test-dir build/iee-effect-streaming-20261015-v1 -C Release --output-on-failure -R '^(iee_tests|iee_effect_frame_cache_tests|iee_effect_animation_x4_registry_tests|iee_effect_texture_cache_tests|iee_bridge_worker_tests|iee_startup_barrier_tests|iee_hook_preallocation_tests)$'
python -B -m unittest pipeline.tests.test_compose_effect_runtime_packs pipeline.tests.test_prepare_effect_streaming_candidate -v
python -B engine/InfinityEngine-Enhancer/source-patchee/tools/verify_effect_streaming_abi.py
```

Contrôle réel du catalogue **sans lecture RGBA**, débuts désactivés par ce mode de test :

```powershell
build/iee-effect-streaming-20261015-v1/Release/iee_effect_animation_x4_registry_tests.exe --catalogue-only effects/installations/lot64-7b-x4-nearest30-20261015-v1/candidate/iee-assets/effects effects/installations/lot64-7b-x4-nearest30-20261015-v1/runtime-contracts.tsv
```

Couverture : stockage lent/injecté, sharing et leases, budgets/in-flight, suppression et génération pendant lecture, arrêt concurrent, fichier absent, débuts, culling ; 4999 réemplois d'adresse ; 1000 ressources synthétiques / 15,625 Gio déclarés sans RGBA ; tables v3 et queues v2 ; faux moteur avec queue/suppressions différées sur contexte WGL caché, >64 backings dans un batch, tailles différentes, pression en octets, 400 slots natifs occupés + allocation Character, pixels GPU exacts/NEAREST/sans mip, scratch pending. Les tests WGL sont des exécutables hôte distincts du jeu.

Résultats locaux 2026-10-15 : DLL Release compilée ; sept cibles CTest ci-dessus réussies (test GPU relancé après adaptation de sa réservation à une frame synthétique plus grande) ; six tests Python réussis ; cinq prologues PE vérifiés ; catalogue réel 161 ressources / 15501 backings / 8208516864 octets déclarés, métadonnées comptées 11623801 octets, 33548 contrats résolus, zéro lecture RGBA en mode catalogue seul. Pas de mesure ingame déduite.

## Candidat et retour arrière

```powershell
python -B engine/InfinityEngine-Enhancer/source-patchee/tools/prepare_effect_streaming_candidate.py --dll build/iee-effect-streaming-20261015-v1/Release/InfinityEngine-Enhancer.dll --output build/iee-effect-streaming-20261015-v1/candidate
```

- Lit l'INI installé comme référence ; écrit exclusivement un nouveau dossier candidat local : DLL, INI, `candidate.json`, README. Autres réglages, shaders personnages, budgets existants, BOM et fins de ligne conservés. Refuse un dossier non vide.
- Candidat produit localement : `build/iee-effect-streaming-20261015-v1/candidate/` (ignoré Git), DLL 3426816 octets, SHA-256 `824A74D8FC107BE4C23D66A416C535199D217B11CC5CB6903B641ADEB33006D1` ; INI SHA-256 `11C3DAF0FFF2BE7830A531CA5FE61E22F3CF26FCE34185D9EECB41601418AFE0`. Ces empreintes portent exclusivement sur les nouveaux fichiers candidat.
- Installation éventuelle : transactions de `tools/install_renderer_candidate.py`, seulement après demande explicite et fermeture du jeu/InfinityLoader par l'utilisateur. Ce document ne déclenche aucune installation.
- Retour backend : `EnableEffectAnimationStreaming=false`, prochain démarrage ; ancienne DLL possible avec pack ≤512 ressources / 8 Gio. Bibliothèque future plus grande : restaurer aussi un snapshot de catalogue compatible.
- Non validés ingame : premier affichage, zéro fallback dans une scène supportée, cadence réelle, marge upload, transitions carte/sauvegarde, coexistence réelle avec EEex. Aucun résultat hôte ne vaut acceptation visuelle/release. Conteneur compressé différé jusqu'à bénéfice de stockage mesuré.
