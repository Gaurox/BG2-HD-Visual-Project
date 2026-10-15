# Effets HD — architecture mémoire et prompt de passation

- Date : 2026-10-15.
- Base analysée : commit `bf664e60` ; dépôt propre avant et après la recherche.
- Statut : **analyse et proposition uniquement**, aucune implémentation ni validation ingame nouvelle.
- Recherche : code, métadonnées et désassemblage statique de l'exécutable exact ; aucun lancement/contrôle du jeu ou d'InfinityLoader, aucune reconstruction ni lecture globale des RGBA.
- Conservation : note complète et prompt autonome de la réponse de recherche ; liens locaux rendus relatifs au dépôt. Les numéros de ligne désignent la base analysée, pas une garantie pour les versions suivantes.
- Unités : Mio = 2^20 octets ; Gio = 2^30 octets.

**Recommandation : cache hybride — catalogue résident, images RGBA partagées chargées par fenêtres temporelles, préchargement anticipé et cache GPU borné en octets comme en descripteurs.** Les packs actuels peuvent être conservés intégralement.

Dépendance importante : **la réutilisation GPU doit respecter la file de dessins différés du moteur**. `DrawBindTexture` ne la vide pas ; le commentaire actuel ne constitue donc pas une garantie suffisante pour développer le streaming.

## A. Diagnostic vérifié et limites actuelles

Dans cette note :

- **Vérifié** : code, métadonnées ou désassemblage de l'exécutable exact.
- **Historique** : reçu, diagnostic ou validation utilisateur conservés.
- **Proposé** : architecture à implémenter.
- **À vérifier** : propriété que les éléments disponibles ne démontrent pas.

### État de référence

Le [reçu d'installation](../effects/installations/lot64-7b-x4-nearest30-20261015-v1/installation.json) (L2), le registre et le manifeste candidat concordent :

| Mesure | Valeur |
|---|---:|
| Ressources | 161 |
| Images RGBA stockées | 15 501 |
| Octets RGBA déclarés | 8 208 516 864 |
| Volume | 7,6448 Gio |
| Registre binaire | 239 840 octets |
| Cycles natifs / profils cumulés | 323 / 325 |
| Phases accessibles cumulées | 16 774 |
| Marge sous le plafond de 8 Gio | 363,748 Mio |

Les 226 cycles et 228 profils mentionnés dans l'acceptation du lot64 concernent **ce nouveau lot**, pas les 161 ressources cumulées.

Ces calculs vérifient la cohérence des métadonnées, pas une nouvelle intégrité physique des gigaoctets installés. L'acceptation utilisateur des productions reste celle enregistrée.

### Le plafond CPU actuel n'est pas un budget de cache

Dans [effect_animation_x4_registry.cpp](../engine/InfinityEngine-Enhancer/source-patchee/src/iee/effect_animation_x4_registry.cpp) (L24–64) :

- `kMaxRawBytes = 8 Gio` limite le **volume cumulé autorisé du pack**.
- Chaque `Frame` possède son `std::vector<std::byte> replacement`.
- `prepare()` lit toutes les images.
- Aucun mécanisme ne retire une image CPU devenue inutile.
- `release()` libère le registre entier.

La consommation dépend donc de toute la bibliothèque installée. Elle ne dépend presque pas des effets réellement visibles.

Deux autres limites sont indépendantes :

- `kMaxResources = 512` : limite du catalogue, également présente dans le compositeur Python.
- `kTextureCacheLimit = 64` : limite du nombre d'entrées GPU, sans compteur d'octets.

### Mémoire et opérations actuelles

| Élément | Durée de vie / coût |
|---|---|
| RGBA CPU | Tous conservés jusqu'à `release()` |
| Tables cycles/profils | Résidentes avec le registre |
| Registre binaire brut | Temporaire pendant `prepare()` |
| Cache GPU | Jusqu'à 64 backings ; remplacement LRU |
| Masquage décor CPU | Copies x1 avant/après clipping et transfert calculé pendant le rendu |
| Masquage décor GPU | Texture x4 transitoire, masque et ressources de composition |
| Cache de fichiers Windows | Distinct des buffers privés du renderer |
| Allocations internes du pilote | Non comptabilisées par le cache actuel |

Le chargement utilise des déplacements de vecteurs : **il ne crée pas systématiquement une seconde copie complète de 7,64 Gio**. En revanche, appeler `prepare()` alors qu'un ancien registre existe conserverait l'ancien ensemble pendant la construction du nouveau. Ce serait un pic proche de deux payloads ; le démarrage courant ne constitue pas ce scénario.

Les 7,64 Gio désignent les allocations RGBA conservées, pas une mesure du working set physique. Windows peut paginer ces allocations. Un buffer « présent dans le cache applicatif » n'est donc pas une garantie absolue d'absence de défaut de page. [Microsoft — Working Set](https://learn.microsoft.com/windows/win32/memory/working-set).

### Blocages possibles aujourd'hui

Le thread de rendu effectue notamment :

- plusieurs prises de `g_mutex` et recherches linéaires par resref ;
- allocations de textures et `glTexImage2D` lors des misses GPU ;
- vérifications d'état OpenGL ;
- allocations et copies du masque d'occlusion ;
- journalisation, avec logger synchrone et flush sur les messages INFO.

`bind_frame_texture()` conserve `g_mutex` pendant les opérations OpenGL : [registre](../engine/InfinityEngine-Enhancer/source-patchee/src/iee/effect_animation_x4_registry.cpp), L663–701. Le [logger](../engine/InfinityEngine-Enhancer/source-patchee/src/iee/core/logger.cpp), L17–29, peut également écrire et flusher depuis ce chemin.

Il n'y a pas de lecture explicite des fichiers RGBA pendant le rendu actuel. Il existe néanmoins des attentes possibles liées au pilote, aux mutex, à la journalisation et à la pagination.

## B. Chemins d'exécution et durées de vie

### Parcours complet actuel

| Étape | Fonction / comportement vérifié |
|---|---|
| Initialisation | `InitThread` identifie le build et résout les API natives |
| Réservation des trampolines | `prepare_core_hooks()` crée **LoadArea et RenderTexture**, encore désactivés |
| Préparation effets | `effect_animation_x4::prepare()` lit registre, tables et tous les RGBA |
| Publication | Déplacement vers `g_resources`, puis `g_ready=true` |
| Installation | Validation des signatures et installation des scopes projectile/VVC/FX |
| Identification de l'owner | Entrée du rendu projectile ou VVC ; conservation temporaire de l'owner et de sa cellule |
| Résolution | Resref, séquence, slot natif, dimensions, profil ponctuel/boucle |
| Phase intermédiaire | Horloge QPC limitée au slot natif courant, sensible à la pause |
| Texture | Hit GPU ou allocation/réutilisation et upload RGBA |
| Masquage | Transfert du clipping natif vers le backing HD, si applicable |
| Dessin | Appel original avec géométrie native |
| Restauration | Restauration du binding ; suppression demandée des textures transitoires |
| Fin | Désactivation des hooks et libération globale CPU |

Références principales :

- [dll_main.cpp](../engine/InfinityEngine-Enhancer/source-patchee/src/iee/dll_main.cpp), L126 : initialisation.
- [effect_animation_x4_registry.cpp](../engine/InfinityEngine-Enhancer/source-patchee/src/iee/effect_animation_x4_registry.cpp), L330 : préparation.
- [hooks.cpp](../engine/InfinityEngine-Enhancer/source-patchee/src/iee/hooks.cpp), L1280 : résolution ; L1422 : phase intermédiaire ; L3946 : substitution finale ; L4038 : masquage et dessin original.

### VVC, projectiles et partage

**VVC.** Le hook observe la cellule primaire à `owner+0x248`. Le profil dépend des flags et des séquences natives `+0x78`, `+0xC0/+0xC4/+0xC8`. La règle est centralisée dans [effect_playback_profile.h](../engine/InfinityEngine-Enhancer/source-patchee/src/iee/core/effect_playback_profile.h), L5.

Il faut distinguer :

- introduction ;
- séquence maintenue/bouclée ;
- fin ;
- orientations ;
- séquences continues ;
- cellules primaire, ombre et alpha.

`+0xCC` correspond aux séquences continues, pas au flag boucle. Les formats et layouts primaires confirment ces distinctions. [IESDP VVC](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/vvc_v1.htm), [EEex CVEFVidCell](https://eeex-docs.readthedocs.io/en/latest/EE%20Game%20Structures%20(x64)/CV/index.html#cvefvidcell).

**Projectiles.** Le hook actuel observe `CProjectileBAM::Render`, cellule `+0x1B8`. Un projectile peut associer voyage, ombre, traînées, explosion, projectile secondaire et VVC. Il ne faut pas traiter cet ensemble comme les frames successives d'un unique BAM. D'autres classes de projectiles ont des layouts différents. [IESDP PRO](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/pro_v1.htm), [EEex CProjectileBAM](https://eeex-docs.readthedocs.io/en/latest/EE%20Game%20Structures%20(x64)/CP/index.html#cprojectilebam).

Le scope projectile sélectionne aujourd'hui `onceProfile=false`. Cela signifie « table de base », **pas une preuve que tous les projectiles bouclent**.

**Partage.** Plusieurs consommateurs peuvent utiliser les mêmes backings avec des horloges différentes. Le partage doit porter sur les images ; la temporalité, le mode et la durée de vie appartiennent à chaque occurrence.

### Ce qui est disponible avant le premier dessin

Les trois points effets actuellement manifestés sont des fonctions de rendu : [EffectAnimationRuntime](../engine/InfinityEngine-Enhancer/source-patchee/src/iee/game/build_manifest.h), L311.

| Point | Disponibilité |
|---|---|
| Entrée `CProjectileBAM::Render` | Disponible, mais sans avance temporelle garantie |
| Entrée `CVEFVidCell::Render` | Disponible, même limite |
| `CInfinity::FXRender` final | Disponible, déjà trop tard pour une lecture froide garantie |
| Création/reconfiguration VVC | Candidats natifs identifiés ; nouveaux hooks à valider |
| Décodage projectile EEex | API existante ; raccord au renderer à concevoir |
| Destruction/session | Signal EEex existant pour session ; durée de vie individuelle à compléter |

EEex expose `EEex_Projectile_RegisterGlobalMutator`, avec callbacks avant/après décodage. Les scripts installés confirment ces points. Ils constituent une piste réelle de préchargement, mais **ne prouvent ni un délai suffisant, ni la couverture des VVC créés directement**. L'ordre avec les autres mutateurs doit être vérifié. [EEex Projectile](https://eeex-docs.readthedocs.io/en/latest/EEex%20Functions/Projectile/index.html#eeex-projectile-registerglobalmutator).

Les VEF peuvent annoncer des enfants différés ; un graphe typé VEF/VVC/BAM/PRO peut exploiter cette avance, avec récursion et fan-out bornés. [IESDP VEF](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/vef_v1.htm).

### Nouvelles observations statiques VVC

Exécutable inspecté : `config://bg2ee_game_root/BaldurReal.exe`, empreinte :

`B51093A49140B2B8A7C046B4652BB8E535BE24EBBC12B1D735E0B94217A14D57`

| RVA | Observation | Statut pour l'implémentation |
|---|---|---|
| `0x254010` | Copie des données VVC et création/recréation des cellules | Candidat init/reconfiguration |
| `0x2547C0` | Usine liée à une ressource ; appelle l'initialisation | Candidat création |
| `0x254440` | Routine d'update et transitions | Candidat observation des phases |
| `0x2551F0` | Sélection séquence/direction | Candidat anticipation |
| `0x253AA0` | Destruction des cellules et de l'objet | Candidat fin d'occurrence |

**Correction utile pour la passation :** les repères historiques « constructeur `0x254000` » et « update `0x2544C0` » ne doivent pas devenir des adresses de detour. Le premier est une courte routine distincte ; le second est intérieur à la fonction commençant à `0x254440`.

Ces observations ne remplacent pas la validation ABI, des signatures, des callsites et de la coexistence avec EEex.

### Pause, disparition, carte, sauvegarde, pointeurs

Le [scheduler](../engine/InfinityEngine-Enhancer/source-patchee/src/iee/core/area_animation_timeline.cpp), L55 :

- conserve les slots natifs comme autorité ;
- choisit seulement une phase intermédiaire dans le slot courant ;
- gèle la progression en pause ;
- conserve une sélection identique pour plusieurs dessins du même epoch.

Deux limites supplémentaires sont vérifiées :

1. **1024 occurrences mémorisées sans suppression individuelle.** La table accumule les couples pointeur/resref jusqu'au changement de génération. Saturée, elle abandonne l'interpolation pour les nouvelles entrées ; le backing HD du slot natif reste disponible.
2. **Réemploi de pointeur ambigu.** Même adresse, même resref, même séquence et même slot ne garantissent pas une nouvelle occurrence.

Références : [table d'occurrences](../engine/InfinityEngine-Enhancer/source-patchee/src/iee/core/area_animation_timeline.h), L39 ; [recherche et reset](../engine/InfinityEngine-Enhancer/source-patchee/src/iee/core/area_animation_timeline.cpp), L34 et L100.

L'absence de rendu pendant 250 ms dans `EffectPresentationTrace` est une **heuristique de diagnostic**, pas une preuve de destruction. Un effet peut être hors écran ou masqué.

`LoadArea` change la génération effets. Aucun hook spécifique effets `LoadGame/DestroyGame` n'est câblé. EEex fournit un listener de destruction de session, notamment lors d'un retour au menu ou d'un chargement de sauvegarde. [EEex GameState](https://eeex-docs.readthedocs.io/en/latest/EEex%20Functions/GameState/index.html#eeex-gamestate-adddestroyedlistener).

### Point critique : les dessins GPU sont différés

L'analyse statique du même exécutable établit :

| Fonction | Comportement |
|---|---|
| `DrawBindTexture`, `0x413140 → 0x42A840` | Modifie l'identifiant dans l'état natif ; aucun flush |
| `DrawEnd`, `0x4132D0 → 0x42B220` | Ajoute/agrège les commandes dans une file |
| `TexImage`, `0x4135E0 → 0x42D030` | Modifie dimensions et stockage de texture ; aucun flush natif |
| `DrawFlush_GL`, `0x42B350` | Relit les descripteurs courants puis soumet les dessins GL |
| `DrawDeleteTexture`, `0x413270 → 0x42B030` | Positionne `deletePending` |
| Collecte, `0x42B2C0` | Flush, puis suppression réelle des textures marquées |
| `DrawGenTexture`, `0x42BBD0` | Cherche un slot libre parmi 1…511 ; ne collecte pas les suppressions en attente |

Conséquence : **écraser les pixels ou les dimensions d'un descripteur encore référencé par la file native peut modifier un dessin antérieur**.

Le LRU actuel exclut seulement le binding précédent. Il ne suit pas les autres références en attente. C'est un risque établi dans le code, pas une régression visuelle démontrée sur les assets acceptés.

`DrawFlush_GL` est déjà [manifesté](../engine/InfinityEngine-Enhancer/source-patchee/src/iee/game/build_manifest.cpp), L322, et [utilisé après le rendu d'aire](../engine/InfinityEngine-Enhancer/source-patchee/src/iee/hooks.cpp), L5133. Sa réutilisation exige le bon pass/FBO et une restauration correcte des états. `DrawPushState/DrawPopState` existent, mais ne sauvegardent pas à eux seuls tout l'état GL externe.

## C. Comparaison des architectures

| Option | Atouts | Limites dans ce projet | Décision |
|---|---|---|---|
| Cache par ressource complète | Simple ; peu de décisions pendant la lecture | Une seule ressource atteint 466 Mio ; pics au premier usage ; charge des cycles inutilisés | Promotion opportuniste des petites ressources |
| Cache par frame, LRU seul | Mémoire bornée ; compatible RGBA actuels | Découvre trop tard les besoins ; multiplication des lectures ; aucune garantie premier affichage | Insuffisant seul |
| Fenêtres temporelles | Charge les phases utiles ; partage entre instances | Dépend des deadlines, transitions et anticipations | Composant principal |
| Hybride fenêtres + débuts préparés + petites ressources complètes | Réduit misses et relectures avec budget explicite | Plus d'états et d'instrumentation | **Recommandé** |
| Fichiers mappés | Accès indexé ; possibilité d'éviter certaines copies privées | Défauts de page sur accès ; résidence contrôlée par Windows ; nombreux mappings avec fichiers actuels | Backend éventuel, pas solution principale |
| Conteneur indexé sans perte | Moins d'ouvertures ; lectures regroupées ; compression possible | Nouveau stockage/index ; décompression ; migration supplémentaire | Deuxième étape, si mesures utiles |

Un mapping ne rend pas l'accès non bloquant. `PrefetchVirtualMemory` reste une indication au système, peut échouer partiellement sous pression et ne place pas directement les pages dans le working set du processus. [Microsoft — PrefetchVirtualMemory](https://learn.microsoft.com/en-us/windows/win32/api/memoryapi/nf-memoryapi-prefetchvirtualmemory).

Pour un conteneur compressé, utiliser des unités indépendamment décodables et un index d'offsets. Une archive monolithique obligeant à décompresser une ressource entière contredirait l'objectif. Zstandard fournit un format seekable fondé sur des frames indépendantes ; leur taille reste un compromis entre accès aléatoire et compression. [Zstandard seekable format](https://github.com/facebook/zstd/blob/dev/contrib/seekable_format/README.md).

## D. Architecture recommandée

### 1. Séparer catalogue, stockage, occurrences et caches

**Catalogue immuable**

Conserver en mémoire :

- resrefs normalisés ;
- dimensions logiques et taille exacte attendue ;
- cycles natifs ;
- tables de phases v2/v3 ;
- profils ponctuels ;
- description du stockage.

Construire un index resref → ressource, pour supprimer les recherches linéaires répétées.

**Clé des pixels**

`FrameKey = {packGeneration, resourceId, backingIndex}`

Ne pas utiliser l'index global renuméroté du JSON comme identité durable. Cycle, direction et profil résolvent un backing ; ils ne créent pas automatiquement une nouvelle copie de pixels.

**Identité d'occurrence**

`OccurrenceKey = {sessionGeneration, ownerSerial, ownerKind}`

L'adresse native sert à retrouver l'occurrence pendant sa vie, pas à garantir son identité. Une reconfiguration de cellule/resref invalide les intentions précédentes.

**Workers**

Ils reçoivent uniquement des données copiées : clé, taille, chemin/offset, génération et priorité. Aucun pointeur natif à déréférencer ultérieurement.

### 2. Préchargement par échéances

Ordre proposé :

| Priorité | Besoin |
|---|---|
| P0 | Image courante requise et réparation d'un manque |
| P1 | Prochaines phases d'occurrences visibles |
| P2 | Apparitions annoncées par création/décodage ; transitions connues |
| P3 | Raccord de boucle, fin VVC, orientations probables |
| P4 | Débuts fréquemment utilisés et petites ressources conservées opportunément |

Les demandes identiques sont fusionnées. L'échéance d'un backing partagé est la plus proche parmi ses consommateurs.

À chaque observation native :

1. confirmer resref, profil, cycle et slot ;
2. sélectionner la frame avec la logique actuelle ;
3. demander l'union de la fenêtre nécessaire ;
4. retirer les intentions devenues inutiles ;
5. anticiper uniquement les transitions connues.

Pour une boucle, précharger le retour vers le début avant d'atteindre la fin. Pour un ponctuel, ne pas boucler artificiellement. Pour une direction inconnue, préparer les branches plausibles dans le budget, sans charger systématiquement toutes les orientations.

Les fenêtres doivent suivre les **tables de backings**, jamais supposer que les numéros de fichiers sont chronologiquement contigus.

La fin inutilisée d'une table v2 doit être exclue : sur le catalogue courant 15→30 FPS, les phases accessibles d'un cycle correspondent à `2 × nombre de slots natifs`.

### 3. États CPU et GPU distincts

État CPU proposé :

`Absent → Queued → Reading → Ready`

Branches supplémentaires :

- `Failed` : fichier absent, taille invalide, lecture interrompue ;
- `Cancelled/Stale` : demande sans consommateur ou génération obsolète ;
- `Retiring` : buffer retiré du cache mais encore détenu par une opération.

L'état GPU est indépendant :

- absent ;
- prêt dans une génération de contexte ;
- référencé par des dessins natifs non flushés ;
- en attente de suppression native.

Une image peut être présente en GPU et absente du cache CPU, ou l'inverse.

### 4. Concurrence et comptabilité

Proposition initiale : **deux workers de lecture**, concurrence configurable après mesure.

Règles :

- réserver les octets avant toute allocation de sortie ;
- compter les sorties en cours dans le budget des données ;
- déplacer le buffer vers le cache sans recopie ;
- publier via une file bornée ;
- ne jamais conserver le verrou du cache pendant une lecture ;
- ne jamais attendre un worker depuis le chemin de dessin ;
- maintenir une référence forte au buffer pendant l'upload ;
- différer les grosses destructions de buffers hors du chemin critique.

Les demandes, résultats prêts, buffers épinglés et résultats en attente de consommation doivent tous être bornés. Borner seulement la table des frames « prêtes » laisserait les queues contourner le plafond.

Le budget d'un buffer partagé est compté une fois. Ses différents consommateurs possèdent des intentions ou des références, pas des duplications.

### 5. Générations et annulations

Conserver séparément :

- génération du pack ;
- génération de session ;
- génération de carte/intention ;
- serial de l'occurrence ;
- génération du contexte GPU ;
- version de la requête.

Un changement de carte supprime les intentions de l'ancienne scène. Il n'impose pas forcément de jeter des pixels encore valides dans le même pack : ils peuvent rester dans la partie évictable du cache.

Un résultat ancien :

- ne doit jamais satisfaire une nouvelle occurrence par réemploi d'adresse ;
- peut être abandonné ;
- peut être conservé comme donnée partagée seulement si son pack est toujours valide et sa conservation est volontairement admise.

La disparition d'un consommateur ne doit pas annuler un chargement encore utile à un autre.

En pause, maintenir les besoins courants ; suspendre l'anticipation inutile. Une absence d'observation ne doit pas être assimilée à une destruction.

### 6. Upload et sûreté GPU

Toutes les opérations natives de textures et OpenGL restent sur le thread possédant le contexte. Un contexte WGL ne peut être courant que sur un thread à la fois. [Microsoft — wglMakeCurrent](https://learn.microsoft.com/en-us/windows/win32/api/wingdi/nf-wingdi-wglmakecurrent).

Chemin proposé :

1. résoudre les métadonnées sans lecture disque ;
2. rechercher d'abord un hit GPU ;
3. sinon acquérir une lease sur le buffer CPU prêt ;
4. choisir un descripteur réutilisable ;
5. protéger les dessins natifs qui le référencent encore ;
6. uploader ;
7. conserver géométrie x1, NEAREST, alpha et masquage actuels ;
8. libérer la lease après le retour de l'upload sans PBO.

L'API actuelle refuse un pixel-unpack buffer lié. Sans PBO, la mémoire client n'est plus nécessaire après le retour du transfert ; un futur chemin PBO demanderait une gestion distincte des buffers et fences. [Khronos — Pixel Buffer Object](https://wikis.khronos.org/opengl/Pixel_Buffer_Object).

**Protection des dessins différés :**

- épingler les descripteurs utilisés jusqu'à une frontière native de flush vérifiée ;
- ne pas écraser un descripteur encore référencé ;
- si nécessaire, effectuer un flush natif sûr avant réutilisation ;
- préserver les états natifs et GL nécessaires ;
- ne pas utiliser `glFinish` pour remplacer cette gestion ;
- reporter les préuploads spéculatifs lorsqu'aucun slot sûr n'est disponible.

Plus de 64 frames distinctes entre deux flushs peuvent nécessiter plusieurs lots. Cela doit être traité par des frontières sûres, pas par une hausse du nombre de descripteurs.

Les suppressions restent comptées jusqu'à la collecte réelle. `DrawDeleteTexture` ne rend pas immédiatement le slot disponible.

### 7. Éviction

Ordre d'éviction proposé :

1. préchargements spéculatifs sans demande active ;
2. anciennes fenêtres ;
3. ressources complètes conservées opportunément ;
4. débuts peu utiles, dans leur quota.

Ne jamais libérer :

- un buffer encore détenu par un upload ;
- une sortie worker dont l'ownership n'a pas été transféré ;
- un backing déclaré indispensable à une échéance admise sans traiter explicitement cette perte.

Une ressource active ne doit pas nécessairement rester entière : seules ses fenêtres et ses besoins partagés sont protégés.

Le `release()` actuel, qui oublie les identifiants GPU, ne doit pas devenir une primitive d'éviction à contexte vivant. La comparaison de valeurs `HGLRC` ne prouve pas non plus la destruction de l'ancien contexte.

### 8. Miss, erreur et dépassement

Aucune architecture ne peut garantir simultanément :

- bibliothèque non résidente ;
- budget fixe ;
- effet imprévisible ;
- stockage de latence non bornée ;
- zéro attente, zéro frame manquante et zéro retour natif.

Un callback de construction peut précéder le dessin de quelques instructions seulement. Un premier dessin peut aussi arriver à un slot avancé après culling : les seules premières frames ne suffisent alors pas.

**Politique recommandée :**

- fonctionnement normal : aucune lecture synchrone dans le dessin ;
- miss : demande P0 et diagnostic explicite ;
- erreur disque : quarantaine de l'entrée, sans boucle de retry à chaque draw ;
- dépassement : retirer la spéculation, puis réduire l'horizon seulement si les deadlines restent tenables ;
- si l'image exacte reste indisponible : conserver le chemin natif sûr, déjà existant, et compter un échec du contrat de streaming.

Ce dernier repli protège l'affichage, mais **ne satisfait pas l'objectif « aucun changement de rendu »**. Il doit rester un cas d'erreur, jamais un fonctionnement normal présenté comme réussi.

Répéter la dernière image HD modifierait la cadence ; attendre la lecture provoquerait une saccade ; ne rien dessiner créerait une disparition. Aucun de ces compromis ne doit être dissimulé.

### 9. Dimensionnement calculé

Source : [manifeste candidat](../effects/installations/lot64-7b-x4-nearest30-20261015-v1/candidate/iee-assets/effects/manifest.json) et registre associé. **Artefacts locaux ignorés par Git : leur disponibilité n'est pas garantie dans un autre clone.** Le [reçu suivi par Git](../effects/installations/lot64-7b-x4-nearest30-20261015-v1/installation.json) et les agrégats ci-dessous conservent les références de cette analyse ; ne pas reconstruire les productions pour simplement consulter la note.

Quelques ressources complètes :

| Ressource | RGBA complets |
|---|---:|
| SPCMWOUI | 466,212 Mio |
| SPSUMMON | 291,533 Mio |
| SPCL239X | 218,665 Mio |
| FLMSTRK | 203,058 Mio |
| SPCAGEMZ | 192,865 Mio |

Plus gros backing : **SPCOMEXP, 7,332 Mio**, soit 1640×1172×4 octets.

Pour un horizon futur `h`, les calculs suivants utilisent :

`nombre de phases = 1 + ceil(30 × h)`

Ils prennent l'union des backings uniques et la pire fenêtre de chaque ressource. Les sommes représentent des **enveloppes synthétiques**, pas des scènes observées.

| Ressources distinctes lourdes | Courante + 250 ms | Courante + 500 ms | Courante + 1 s |
|---|---:|---:|---:|
| 8 | 267,239 Mio | 441,246 Mio | 723,729 Mio |
| 16 | 421,657 Mio | 704,353 Mio | 1 175,039 Mio |

Préparer les débuts de tous les cycles/profils actuels coûte :

| Préparation | Backings uniques | RGBA |
|---|---:|---:|
| Première phase | 312 | 96,197 Mio |
| Deux premières phases | 631 | 196,508 Mio |
| Huit premières phases | 2 557 | 965,126 Mio |

**Budget initial proposé :**

| Budget | Proposition et portée |
|---|---|
| Données CPU | **768 Mio**, incluant buffers prêts, épinglés et sorties de lecture réservées |
| Sorties en cours | Sous-plafond initial **32 Mio**, inclus dans les 768 Mio |
| Débuts préparés | Quota maximal **256 Mio**, inclus dans les 768 Mio |
| Métadonnées | Budget séparé, initialement **16 Mio** pour le catalogue courant ; coût réel à instrumenter |
| Scratch workers | Séparé ; faible pour RGBA brut, à borner explicitement si compression |
| GPU backings | Proposition initiale **288 Mio et 64 descripteurs maximum** |
| GPU transitoires effets | Enveloppe distincte proposée **64 Mio**, comprenant les suppressions en attente ; à valider avec le bridge |
| Cache fichiers Windows | Hors budgets privés ; surveillé séparément |
| Pilote / ressources natives | Hors comptabilité exacte du cache ; mesures nécessaires |

Justification CPU, sans retrancher les recouvrements :

`196,508 + 441,246 + 32 = 669,754 Mio`

Il reste **98,246 Mio** dans un plafond de 768 Mio pour ce scénario de huit ressources lourdes avec 500 ms d'avance.

Avec le quota de débuts entièrement rempli à 256 Mio, il reste **38,754 Mio**. Cela interdit de promettre une réserve illimitée pour d'autres frames épinglées.

Seize ressources lourdes avec 500 ms dépassent le budget ; avec 250 ms, l'enveloppe redevient compatible. La réduction d'horizon n'est acceptable que si le stockage et les uploads tiennent encore les échéances.

Justification GPU :

- les 64 plus gros backings distincts actuels totalisent **262,829 Mio** ;
- 288 Mio couvrent ce cas avec une marge limitée ;
- le pool transitoire doit compter les textures encore `deletePending` ;
- cette comptabilité ne constitue pas une borne exacte de la VRAM physique du pilote.

**Partager change fortement le résultat.** Des occurrences synchronisées d'un même backing utilisent une seule image CPU/GPU. Des occurrences déphasées demandent l'union de leurs fenêtres, plafonnée par le profil ou la ressource complète.

**Le débit reste une contrainte indépendante.** Pour huit ressources lourdes, la somme des pires profils moyens représente environ **614 Mio/s bruts** à 30 FPS sans hits ni réutilisation. Cette valeur n'est pas une mesure ; elle montre pourquoi un budget RAM suffisant ne prouve pas la fluidité.

### 10. Plusieurs centaines ou milliers de ressources

Extrapolation au poids moyen courant, sans prétendre prédire les futures productions :

| Ressources | RGBA totaux | Registre sérialisé |
|---|---:|---:|
| 500 | 23,742 Gio | 0,710 Mio |
| 1 000 | 47,483 Gio | 1,421 Mio |
| 5 000 | 237,415 Gio | 7,103 Mio |

Avec l'architecture proposée :

- le stockage augmente avec la bibliothèque ;
- les métadonnées augmentent avec le catalogue ;
- les pixels résidents restent bornés par les budgets ;
- le quota des débuts ne grandit pas automatiquement ;
- les coûts par draw doivent dépendre des occurrences actives, pas d'un parcours de toute la bibliothèque.

Le plafond 512 devra être remplacé par des limites explicites et cohérentes côté lecteur/compositeur. Ne pas simplement le supprimer : conserver contrôles de débordement, taille du registre, nombres de frames/tables et budget des métadonnées.

À 5 000 ressources extrapolées, environ 481 000 descripteurs de frames coûteraient déjà 29,4 Mio à 64 octets chacun. Le budget de métadonnées initial de 16 Mio ne serait donc pas garanti ; il faudrait un index compact ou un plafond augmenté explicitement.

## E. Incertitudes et vérifications minimales

| Incertitude | Vérification minimale future |
|---|---|
| Avance réelle des signaux VVC/projectile | Mesurer événement → premier draw, avec resref/profil/slot réellement utilisés |
| ABI et couverture VVC | Signatures et callsites des candidats sur l'exécutable exact ; ordre avec EEex |
| Destruction et reconfiguration | Tracer serials, changement de cellule et fin logique ; ne pas confondre disparition visuelle et destruction |
| Flush sûr au point de substitution | Vérifier pass/FBO, primitive terminée, restauration des états, récursion et masque |
| Débit et latence du stockage | Lectures ciblées hors jeu sur un échantillon représentatif ; aucun besoin de relire tout le catalogue |
| Coût upload et pics pilote | Mesures pendant des scénarios lancés exclusivement par l'utilisateur |
| Contexte GL | Vérifier les notifications de destruction/recréation et le réemploi éventuel du handle |
| Chargement de sauvegarde | Confirmer l'invalidation session sur les chemins qui ne seraient pas couverts par LoadArea |
| Intégrité actuelle des pixels installés | Non revérifiée globalement ; exploiter les reçus et vérifier au chargement les tailles, puis les erreurs rencontrées |

Les nouveaux hooks ne doivent être activés que sur un build identifié et des signatures validées. Les noms historiques ou layouts EEex ne suffisent pas à établir une ABI de detour.

## F. Plan d'implémentation et migration

| Étape | Fichiers / fonctions | Dépendance et risque principal |
|---|---|---|
| 1. Séparer métadonnées et pixels | `effect_animation_x4_registry.{h,cpp}` : `prepare`, `Frame`, résolveurs | Garder le backend eager comme référence ; mêmes résultats v1/v2/v3 |
| 2. Sécuriser les durées de vie GPU | API texture, `bind_frame_texture_locked`, hooks de dessin/flush | File native différée, état GL, suppressions en attente |
| 3. Ajouter stockage brut et cache borné | Nouveaux composants dédiés de stockage/cache/workers | Réservations, leases, queues bornées, annulations |
| 4. Identifier les occurrences | `hooks.cpp`, `effect_playback_profile.h`, scheduler effets | Pointeurs réutilisés, cellules remplacées, table 1024 |
| 5. Ajouter les signaux anticipés | `game/build_manifest.*`, raccord EEex ou hooks validés | ABI, coexistence EEex, couverture des créations |
| 6. Ajouter fenêtres et admission | Résolution des tables/profils ; ordonnanceur du cache | Boucles, directions, transitions, deadlines |
| 7. Intégrer démarrage/arrêt | `dll_main.cpp`, `startup_barrier.h`, worker de durée de vie module | Loader lock, arrêt concurrent, libération après join |
| 8. Exposer configuration et métriques | `core/config.*`, traces et compteurs | Budgets distincts et diagnostics non bloquants |
| 9. Préparer un candidat réversible | `tools/install_renderer_candidate.py` | DLL+INI seulement au premier palier ; installation ultérieure explicite |
| 10. Évaluer un conteneur | Producteurs/compositeur, uniquement si bénéfice mesuré | Nouvelle génération de stockage, octets décodés identiques |

### Compatibilité des productions

Les fichiers actuels suffisent à la première implémentation :

- conserver les RGBA exacts ;
- conserver les indices de backings ;
- conserver les tables natives et v3 ;
- conserver les dimensions et centres natifs ;
- conserver les carriers BAM ;
- conserver les contrôleurs VVC ;
- conserver les 97 anciens effets et les 64 acceptés ;
- conserver l'exception transparente constante de SPCOMEXP.

Le [producteur](../pipeline/scripts/build_effect_runtime_pack.py), L937, déduplique en tenant compte de l'identité d'image et de la géométrie. Le [compositeur](../pipeline/scripts/compose_effect_runtime_packs.py), L204, conserve les indices locaux des ressources.

**Aucune évolution obligatoire du registre pour charger à la demande les RGBA existants.** Un index de stockage séparé ou un nouveau conteneur pourra venir ensuite.

Les frames masquées restent propres au contexte de dessin : elles ne doivent pas être partagées entre owners simplement parce que leur backing RGBA est identique.

Les branches personnages, leurs shaders et le contrat `NearestRGB-SilhouetteAlphaAA` restent inchangés.

### Réparations de démarrage à conserver

- Réserver les trampolines avant les allocations importantes. La réparation actuelle couvre précisément LoadArea et RenderTexture ; réserver également assez tôt les nouveaux hooks nécessaires.
- Conserver la barrière dans `InitBindings`, hors `DllMain`.
- Attendre catalogue, service de chargement et préchauffage indispensable ; ne plus attendre tout le payload.
- Conserver le refresh natif de la première carte.
- Maintenir le plafond de 64 descripteurs d'effets.

Les historiques montrent que le refresh seul pouvait laisser apparaître brièvement la mosaïque ; barrière et refresh remplissent des fonctions complémentaires. [Réparation des trampolines](../engine/InfinityEngine-Enhancer/installations/hooks-startup-repair-20261014-v1/README.md), L4 ; [barrière de démarrage](../engine/InfinityEngine-Enhancer/installations/renderer-startup-barrier-20261014-v1/README.md), L8.

### Arrêt

Ordre proposé :

1. arrêter les producteurs de demandes ;
2. invalider les générations ;
3. annuler/réveiller les workers ;
4. terminer les accès GPU dans le contexte approprié ;
5. joindre les workers sans verrou du cache ;
6. libérer buffers et catalogue ;
7. terminer le retrait des hooks et références module.

Aucun join depuis `DllMain`. Le projet possède déjà une [primitive de worker liée à la durée de vie du processus](../engine/InfinityEngine-Enhancer/source-patchee/src/iee/core/process_lifetime_worker.h), L14.

### Retour arrière

Prévoir un choix **au démarrage** entre backend historique et streaming. Ne pas faire cohabiter deux chargements complets ni basculer à chaud.

Premier candidat : DLL+INI uniquement, via les transactions et reçus de l'[installateur existant](../engine/InfinityEngine-Enhancer/source-patchee/tools/install_renderer_candidate.py), L808. Retour possible à l'ancienne DLL tant que le catalogue respecte ses limites.

Une bibliothèque future dépassant 8 Gio ou 512 ressources ne sera pas lisible par l'ancien backend : son rollback devra restaurer aussi le snapshot de catalogue compatible. Les preuves historiques restent immuables.

## G. Instrumentation et critères d'acceptation

### Mesures indispensables

**CPU / stockage**

- octets prêts, épinglés, réservés, en cours et retirés ;
- pics et refus d'admission ;
- hits/misses par backing ;
- durée queue, ouverture, lecture, publication ;
- avance restante à la fin du chargement ;
- annulations et résultats obsolètes ;
- lectures dédupliquées ;
- misses au premier dessin, séparés des misses ultérieurs.

**GPU**

- octets retenus, transitoires et en attente de suppression ;
- descripteurs détenus, utilisés par une queue non flushée, `deletePending` ;
- uploads, octets transférés, durée CPU de l'upload ;
- flushs provoqués par le cache ;
- échecs d'allocation, de masquage et changements de contexte.

**Présentation**

- owner serial, resref, cycle, profil, slot, phase, backing ;
- première présentation réellement HD ;
- fallback et raison ;
- intervalles de présentation ;
- maintien/saut de phase ;
- pause et reprise.

Les traces doivent être bornées et publiées hors du chemin critique. Le [traceur existant](../engine/InfinityEngine-Enhancer/source-patchee/src/iee/core/effect_presentation_trace.h), L9, fournit une base, mais son périmètre SPIMPFR et ses limites de captures ne couvrent pas un test général de concurrence.

La [télémétrie processus existante](../engine/InfinityEngine-Enhancer/source-patchee/src/iee/core/process_resource_telemetry.cpp), L12, expose working set, private bytes, I/O et défauts de page. Son compteur de défauts de page ne distingue pas à lui seul les fautes dures des fautes douces.

### Critères d'acceptation

| Domaine | Critère |
|---|---|
| Budget | Aucun dépassement des allocations contrôlées, y compris buffers encore détenus |
| Scalabilité | Ajouter des ressources inactives ne charge pas leurs pixels hors quota explicite |
| Thread de rendu | Aucune lecture disque, attente worker ou décompression |
| Premier affichage | Zéro miss visible et zéro fallback dans les scénarios déclarés supportés |
| Cadence | Même sélection native, phases intermédiaires et durée ; aucune phase répétée pour masquer un miss |
| Boucles/profils | Raccord correct ; SPFLESHS/SPMETSWA ponctuel et boucle distincts |
| Partage | Une copie par backing ; horloges indépendantes pour les instances déphasées |
| GPU | Aucun écrasement avant flush ; pas de croissance des descripteurs/suppressions après disparition |
| Masquage | Même découpe décor, sans exposer un backing non masqué en cas d'erreur |
| Personnages | Aucun retour vanilla ni modification de l'AA validé |
| Démarrage/cartes | Première carte correcte ; réparations barrière/refresh conservées |
| Cycle de vie | Aucun résultat appliqué après changement de session ou réemploi d'adresse |

Tests ciblés futurs :

- faux stockage lent, absent ou corrompu ;
- cancellation pendant lecture, destruction pendant upload et shutdown ;
- faux renderer reproduisant **queue différée et suppression différée** ;
- plus de 64 backings utilisés avant une frontière de flush ;
- plus de 1024 occurrences successives ;
- pointeur réutilisé avec mêmes resref/slot/séquence ;
- pause, hors écran, changement de direction et de profil ;
- sauvegarde/carte changée pendant des lectures.

Les seuils de coût d'upload et de temps de frame doivent être fixés à partir de la marge mesurée face au renderer de référence. Aucun chiffre de latence disque/GPU n'a été inventé ici. Les essais ingame restent exclusivement lancés et contrôlés par l'utilisateur.

## H. Prompt autonome de passation

Le bloc suivant est destiné au modèle chargé de l'implémentation. L'enregistrement de ce document ne déclenche pas cette mission.

```text
Tu travailles dans G:\AI\BG2_Upscale, sur le BG2 HD Visual Project. Implémente, lorsque cette mission d'implémentation est explicitement confiée, un streaming mémoire des effets préservant les productions acceptées au commit bf664e60.

Commence par git status --short, lis les AGENTS applicables et préserve les changements existants. Ne lance ni ne contrôle le jeu ou InfinityLoader. Ne modifie aucun fichier installé sans demande explicite. Ne modifie pas la release, les preuves historiques ni les acceptations. Ne relance aucune inférence/interpolation.

Note technique de référence : docs/EFFETS_STREAMING_MEMOIRE_2026-10-15.md. Consulter les sections et sources utiles ; ne pas imposer de relecture exhaustive du dépôt.

Base : 161 ressources, 15 501 backings RGBA, 8 208 516 864 octets ; registre v3 de 239 840 octets. Le backend actuel conserve tous les pixels. Son plafond de 8 Gio est un plafond de payload, pas un cache. Le catalogue est limité à 512 ressources ; le GPU à 64 descripteurs dans une table native partagée de 512 entrées, dont slots allouables 1…511.

Architecture décidée : catalogue immutable résident ; index resref ; stockage initial utilisant exactement les RGBA actuels ; cache partagé par {packGeneration, resourceId, backingIndex} ; fenêtres temporelles par occurrence ; débuts préparés sous quota ; promotion opportuniste de petites ressources complètes. Aucun changement de format obligatoire au premier palier.

Budget de départ à instrumenter : données CPU 768 Mio, incluant sorties réservées/en cours ; sous-plafond in-flight 32 Mio ; quota des débuts 256 Mio ; métadonnées séparées. Les deux premières phases de tous les profils actuels coûtent 196,508 Mio. Huit ressources lourdes, frame courante +500 ms, demandent au pire 441,246 Mio ; total avec in-flight 669,754 Mio. Ce dimensionnement ne garantit pas seize ressources lourdes avec le même horizon.

Workers : seulement fichiers et buffers propres ; aucune lecture différée de pointeur natif, aucune API moteur/OpenGL. Réservation avant allocation, queues bornées, publication par déplacement, leases pendant upload, annulation par générations. Aucun disque ni attente worker dans le dessin.

Occurrences : utiliser génération session et serial propre, pas seulement adresse/resref. Traiter création, reconfiguration, destruction, pause, culling et load/save. La table temporelle actuelle garde 1024 couples historiques sans retrait individuel ; corriger ce problème en conservant les mathématiques de cadence et le comportement des animations d'aire.

Préchargement : signaux anticipés VVC/projectile, puis confirmation au rendu ; fenêtres basées sur les vraies tables, y compris raccords de boucle et profils ponctuels. Les hooks de rendu actuels ne garantissent aucune avance. EEex fournit les callbacks projectile avant/après décodage et un listener de destruction de session.

Point GPU critique : DrawBindTexture ne flush pas. DrawEnd met les dessins en queue ; DrawFlush_GL relit ensuite les descripteurs courants. DrawDeleteTexture marque seulement pending, et DrawGenTexture ne collecte pas. Protéger les descripteurs jusqu'à un flush réel avant réupload ; comptabiliser suppressions différées. Conserver 64 slots et ajouter budget en octets. Le flush doit respecter pass/FBO/état natif et GL ; ne pas considérer DrawPushState/PopState comme sauvegarde de tout GL. Tester avec un faux moteur différé.

Exécutable statiquement étudié : config://bg2ee_game_root/BaldurReal.exe, SHA256 B51093A49140B2B8A7C046B4652BB8E535BE24EBBC12B1D735E0B94217A14D57. Flush natif RVA 0x42B350, déjà manifesté. Candidats VVC : init 0x254010, usine 0x2547C0, update 0x254440, séquence/direction 0x2551F0, destructeur 0x253AA0. Ce sont des candidats à valider, pas des hooks prêts. Ne pas utiliser les anciens libellés 0x254000/0x2544C0 comme entrées de fonctions.

Préserver taille native, centres, cycles, contrôleurs VVC, timings, alpha, clipping décor, NEAREST effets et NearestRGB-SilhouetteAlphaAA personnages. SPFLESHS et SPMETSWA possèdent des alternatives ponctuelles v3. Ne pas précharger les queues inaccessibles des tables v2 comme des phases jouées.

Préserver préallocation des trampolines avant gros buffers, barrière InitBindings hors loader lock, refresh natif de première carte et shutdown explicite des workers. Backend eager/streaming sélectionné au démarrage, sans double chargement.

Fichiers principaux : src/iee/effect_animation_x4_registry.{h,cpp}, hooks.cpp, core/area_animation_timeline.*, core/effect_playback_profile.h, core/effect_presentation_trace.h, frame_hook.cpp, dll_main.cpp, core/startup_barrier.h, game/build_manifest.*, core/config.*, tools/install_renderer_candidate.py, sous engine/InfinityEngine-Enhancer/source-patchee/.

Autorités : effects/installations/lot64-7b-x4-nearest30-20261015-v1/installation.json, candidat/registre associés, effects/batches/lot64-accepted-20261015-v1/acceptance.json. Le sous-dossier candidate est un artefact local ignoré par Git ; sa disponibilité n'est pas garantie dans un autre clone. Pipeline : pipeline/scripts/build_effect_runtime_pack.py, pipeline/scripts/compose_effect_runtime_packs.py.

Livrer progressivement : séparation catalogue/pixels, sûreté GPU, cache/worker testé, identité et signaux natifs, préchargement, instrumentation, candidat réversible. Tests ciblés seulement. Tout miss visible/fallback est un échec du scénario de validation ; ne pas masquer une lecture manquante en modifiant le temps ou en répétant une image. Ne pas promettre zéro miss universel sans résidence préalable ou avance et débit suffisants.
```

**Recommandation finale : commencer par le cache hybride sur les fichiers RGBA existants, avec séparation des budgets et sécurisation du recyclage GPU. Le conteneur compressé vient ensuite, seulement si les mesures ciblées montrent qu'il améliore les lectures. Aucun retraitement des productions validées n'est nécessaire pour cette architecture.**
