# Audit technique — BG2 Upscale

Audit terminée en lecture seule. Aucun fichier, artefact scellé, installation ni manifeste n’a été modifié.

## Conclusion exécutive

Le lag à la première ouverture de la carte complète est réel et déjà observable sur la machine haut de gamme :

- Sur AR0700, le journal existant montre 87 premières rencontres de pages PVRZ sur 1,497 s, alignées avec une frame maximale de **1 154,78 ms**.
- AR1200 produit 92 premières pages sur 1,144 s ; AR1300, 90 sur 1,247 s ; AR2100, 87 sur 1,550 s.
- Ces observations proviennent d’un i7-13700KF, 63,8 Gio de RAM, RTX 5090 32 Gio, NVMe, 1440p/164 Hz. La puissance GPU ne supprime donc pas le problème.

La cause principale la plus probable est :

> La carte complète rend soudain presque toute la zone. Le moteur charge alors synchronement, depuis le thread de rendu, toutes les pages PVRZ x4 qui n’étaient pas encore résidentes, les décompresse en blocs BC, les envoie à OpenGL, puis seulement rend l’image.

Le patch ajoute deux amplificateurs certains :

1. un `LOG_INFO` synchrone et flushé pour chaque nouvelle page ;
2. des lectures de sécurité WTPOOL exécutées inutilement pour chaque tuile, même quand les options WTPOOL sont désactivées.

Le pic RAM/VRAM est cohérent avec les volumes de textures, mais sa répartition exacte entre cache fichier, mémoire transitoire CPU, pilote et VRAM n’est pas encore mesurée. Il serait incorrect d’affirmer que toutes les textures sont décompressées en RGBA8.

La release analysée reste un candidat bloqué, pas une release publiable : `release_status=blocked` et `payload_status=not-buildable` dans [release.json](G:/AI/BG2_Upscale/releases/BG2-HD-Upscale/manifests/release.json:18).

---

## Chemin de chargement identifié

```text
Ouverture de la carte
  → rendu de milliers de tuiles de toute la zone
  → Demand du TIS
  → première référence à chaque PVRZ absent
  → lecture du fichier loose + zlib
  → glCompressedTexImage2D
  → libération de la copie CPU moteur
  → configuration GL par le patch
  → TILE_PAGE_DIAG + flush du journal
  → rendu de la tuile
```

Il n’existe pas de hook propre à l’écran de carte : celui-ci emprunte le même `CVidTile::RenderTexture`, mais touche brutalement beaucoup plus de pages. Le commentaire source mentionne explicitement le diagnostic de la vue complète et les 88 pages d’AR0300 x2 contre 30 en vanilla dans [tile_render.cpp](G:/AI/BG2_Upscale/engine/InfinityEngine-Enhancer/source-patchee/src/iee/features/tile_render.cpp:211).

Le patch ne décode pas lui-même les PVRZ à cet endroit : il reçoit la texture déjà créée par le moteur et conserve une tuile écran de 64×64. La validation du moteur indique que `CResPVR::Demand` libère le bloc CPU après l’upload GL dans [phase0-gates.md](G:/AI/BG2_Upscale/engine/InfinityEngine-Enhancer/source-patchee/docs/validation/phase0-gates.md:385).

## Preuves runtime existantes

Ces valeurs sont des traces datées, pas un benchmark vanilla/patch contrôlé.

| Zone | Premières pages observées | Durée du burst | Observation |
|---|---:|---:|---|
| AR1200 | 92/102 | 1 144 ms | 12,57 ms/page en moyenne |
| AR1300 | 90/100 | 1 247 ms | 14,01 ms/page |
| AR0700 | 87 | 1 497 ms | frame maximale alignée : 1 154,78 ms |
| AR2100 | 87 | 1 550 ms | même signature séquentielle |

Pour AR0700, l’intervalle suivant montre ensuite :

- 2 940 109 appels au hook en cinq secondes ;
- 41,2 millions de hits `safe_read` ;
- coût patch moyen de 2,41 ms/frame, p95 3,53 ms, maximum 8,13 ms.

À 164 Hz, le budget total n’est que de 6,1 ms : le coût soutenu du hook sur la carte complète est donc également significatif, indépendamment du premier hitch.

## Amplification par le journal

Le journal installé mesure actuellement **1 143 211 979 octets**, sans rotation. Il contient notamment :

- 8 304 932 lignes `Enhanced tile texture` ;
- 14 036 lignes `TILE_PAGE_DIAG` ;
- 3 571 rapports de présentation ;
- 3 239 rapports du hook de tuiles.

La configuration installée a `VerboseLogs=true`, `PerformanceLogs=true` et plusieurs prototypes activés. Elle ne représente donc pas le profil de release, qui impose `VerboseLogs=false` et `PerformanceLogs=false` dans [runtime-compatibility.json](G:/AI/BG2_Upscale/releases/BG2-HD-Upscale/manifests/runtime-compatibility.json:71).

Cependant, `TILE_PAGE_DIAG` n’est pas conditionné par ces options. Il est émis une fois par page et réarmé à chaque `LoadArea`. Le logger utilise un sink fichier synchrone et `flush_on(info)` dans [logger.cpp](G:/AI/BG2_Upscale/engine/InfinityEngine-Enhancer/source-patchee/src/iee/core/logger.cpp:12). Cela force une écriture/vidage de flux sur le thread de rendu — pas nécessairement un `fsync` physique — pour environ cent pages sur une grande zone.

Conclusion causale :

- présence du surcoût : confiance élevée ;
- contribution exacte aux 1,1–1,5 s : inconnue sans A/B ;
- impact attendu : supérieur sur HDD, antivirus actif et journal déjà volumineux.

---

## Empreinte des ressources

Le manifeste canonique contient 287 TIS et 5 776 PVRZ pour 263 zones et 24 variantes nuit :

- payload maps : **6,439 Gio sur disque** ;
- blocs BC après décompression zlib, toutes zones cumulées : **16,410 Gio** ;
- équivalent RGBA8 : 95,969 Gio, uniquement comme borne de risque, jamais simultanément résident.

Répartition :

- 3 882 pages 2048² DXT1 ;
- 1 772 pages 2048² DXT5 ;
- 122 pages 4096² DXT5 ;
- un seul niveau de mipmap.

| Page | Stockage BC de base | Équivalent RGBA8 |
|---|---:|---:|
| 2048 DXT1 | 2 Mio | 16 Mio |
| 2048 DXT5 | 4 Mio | 16 Mio |
| 4096 DXT5 | 16 Mio | 64 Mio |

Principales zones témoins :

| Zone | Pages | Disque PVRZ | BC théorique si tout réside |
|---|---:|---:|---:|
| AR0602 | 45 × 2048 DXT1 | 37,71 Mio | 90 Mio |
| AR1300 | 100 × 2048 DXT1 | 138,38 Mio | 200 Mio |
| AR1200 | 102 × 2048 DXT5 | 143,57 Mio | 408 Mio |
| AR0300 jour | 107 × 2048 DXT5 | 133,54 Mio | 428 Mio |
| AR0300 nuit | 24 × 4096 DXT5 | 115,70 Mio | 384 Mio |
| AR0900 | 26 × 4096 DXT5 | 150,51 Mio | 416 Mio |

Ce sont des capacités BC théoriques, pas une mesure de VRAM. Le pilote peut conserver le BC natif ou employer des représentations internes supplémentaires.

Le builder ajoute une bordure de quatre pixels autour des cellules. Une page 2048 contient réellement 7×7, soit 49 tuiles, avec environ 30,6 % de sur-allocation par rapport aux pixels utiles. Une page 4096 contient 15×15, soit 225 tuiles, avec environ 13,8 % de sur-allocation. Le code est visible dans [build_upscaled_area.py](G:/AI/BG2_Upscale/pipeline/scripts/build_upscaled_area.py:359).

La documentation affirmant 225 tuiles pour une page 2048 est donc erronée : c’est un défaut documentaire mineur, mais susceptible de fausser les futurs budgets.

## Autres sources de RAM/VRAM

Elles n’expliquent pas directement l’ouverture tardive de la carte, mais peuvent aggraver l’état mémoire initial.

### Animations de zone x4

`prepare_for_area` lit synchronement toutes les frames RGBA de la zone dans la RAM :

| Zone | RAM CPU persistante approximative | Cache GPU, plafond des 64 frames |
|---|---:|---:|
| AR0516 | 385,9 Mio | 165,7 Mio |
| AR0900 | 215,1 Mio | 173,4 Mio |
| AR0602 | 101,5 Mio | 65,6 Mio |

Pendant une transition AR0516 ↔ AR0900, l’ancien et le nouveau pack peuvent brièvement coexister : environ **601 Mio CPU**, avant même le cache pilote et les cartes. Voir [area_animation_x4_registry.cpp](G:/AI/BG2_Upscale/engine/InfinityEngine-Enhancer/source-patchee/src/iee/area_animation_x4_registry.cpp:361).

### Interface x4

Les atlas DXT5 de BigLogo/MainMenu sont tous chargés en mémoire CPU à l’initialisation de la DLL et retiennent environ **144 Mio**, même hors de ces écrans : [biglogo_ui_upscale.cpp](G:/AI/BG2_Upscale/engine/InfinityEngine-Enhancer/source-patchee/src/iee/biglogo_ui_upscale.cpp:87).

### Cas secondaires

- Le tint PVRZ peut effectuer un `glGetTexImage` synchrone et réserver 16 ou 64 Mio RGBA, mais plutôt au premier passage Seam après `LoadArea` : [area_state.cpp](G:/AI/BG2_Upscale/engine/InfinityEngine-Enhancer/source-patchee/src/iee/area_state.cpp:151).
- Le hook appelle `CRes_Demand(TIS)` avant de savoir s’il délèguera au moteur, qui possède ensuite son propre `Demand`. La double invocation est certaine, son coût réel reste inconnu : [tis_runtime.cpp](G:/AI/BG2_Upscale/engine/InfinityEngine-Enhancer/source-patchee/src/iee/game/tis_runtime.cpp:89).
- `is_wtpool_page` effectue plusieurs `safe_read` pour chaque tuile même lorsque les deux options WTPOOL sont désactivées : [tile_render.cpp](G:/AI/BG2_Upscale/engine/InfinityEngine-Enhancer/source-patchee/src/iee/features/tile_render.cpp:107).
- Les mipmaps sont désactivées par défaut. Les activer ajouterait environ 33 % de stockage et un `glGenerateMipmap` au premier usage ; ce n’est pas une optimisation.

---

## Matrice de risque matériel

| Profil | Risque | Diagnostic |
|---|---|---|
| 4C/4T, 8 Gio, UMA/1 Gio, HDD, 1080p | Critique | pression mémoire, migrations, nombreux fichiers loose, journal concurrent |
| 4C/8T, 8–16 Gio, UMA/dGPU 2 Gio, SATA SSD | Élevé | 400+ Mio de carte plus animations/UI ; risque de mémoire partagée |
| 6C/12T, 16 Gio, GPU 6–8 Gio, NVMe | Moyen | capacité suffisante, mais première ouverture toujours synchrone |
| 8C/16T+, 32 Gio, GPU 12–16 Gio, NVMe | Faible à moyen | faible risque d’épuisement, hitch CPU/I/O toujours possible |
| RTX 5090, i7-13700KF, 64 Gio, NVMe | Faible capacité, fort signal logiciel | le hitch mesuré prouve que le plafond matériel n’est pas la cause principale |

La résolution n’affecte presque pas le nombre de pages requises par la carte complète. Elle influe surtout sur les FBO, l’interface et le fill-rate. En revanche, une fréquence de 164 Hz rend les coûts CPU répétés beaucoup plus visibles.

La release supportée est Windows x64/BG2EE 2.7.3. Les limites d’adressage 2/4 Gio des exécutables 32 bits ne s’appliquent pas ; un ancien build x86 constituerait un périmètre de compatibilité distinct.

---

## Recommandations priorisées

| Priorité | Mesure | Catégorie | Gain attendu | Risque / effort | Validation |
|---|---|---|---|---|---|
| P0 | Conditionner ou agréger `TILE_PAGE_DIAG`; journal rotatif/borné | Sans perte | ~100 écritures INFO supprimées par grande zone ; fin de la croissance illimitée | Faible | A/B ETW avec et sans ligne par page |
| P0 | Court-circuiter `is_wtpool_page` si les options WTPOOL sont fausses | Sans perte | Forte réduction des `safe_read` sur carte complète ; gain exact à mesurer | Très faible | compteur d’appels et p95 du hook |
| P0 | Baseline propre : Verbose/Performance/prototypes désactivés | Sans perte | Élimine le biais diagnostique et le flood de millions de lignes | Très faible | comparer INI au manifeste avant chaque run |
| P1 | Marqueurs carte + compteurs PVRZ/uploads/delete/mémoire | Diagnostic | Attribue enfin I/O, zlib, GL, VRAM et logging | Moyen | recouper ETW, PresentMon et compteurs internes |
| P1 | Charger les animations x4 à la demande avec budget en octets | Sans perte si correctement préchargé | AR0516 pourrait passer de 386 Mio persistants à un budget cible ≤128 Mio | Moyen/élevé | transitions, cycles, absence de frame manquante |
| P1 | Charger les atlas UI uniquement sur l’écran concerné | Sans perte | jusqu’à 144 Mio CPU libérés hors UI | Moyen | temps première ouverture UI et restauration contexte |
| P1 | Précharger progressivement les pages de carte pendant les temps morts | Sans perte visuelle potentielle | première carte chaude sans nouvel upload ; suppression de la frame d’une seconde | Élevé | budget ≤2 ms/frame, aucune régression exploration |
| P2 | Mesurer puis supprimer le double `Demand` et les invalidations GL globales | Sans perte | réduction CPU/refcount possible | Moyen, durée de vie moteur délicate | compteurs Demand/delete et test zones stock/x4 |
| P2 | Repack spatial ou 4096 sélectif par zone | Visuellement identique, QA lourde | moins de pages/fichiers et moins de padding | Élevé ; uploads unitaires de 16 Mio, compatibilité GPU | nouveau run, validation carte/occlusion/nuit |
| P3 | Profil faible mémoire : désactiver d’abord UI/animations x4, puis x2 sélectif si nécessaire | Compromis adaptatif | baisse substantielle RAM/VRAM | Nouvelle matrice de QA et manifests séparés | uniquement après preuve sur 1–2 Gio/UMA |

À éviter :

- précharger toutes les pages au `LoadArea` : cela déplace le hitch et augmente la résidence ;
- forcer 4096 partout : moins de fichiers mais allocations quatre fois plus grosses par page DXT5 ;
- convertir les textures en RGBA CPU ;
- activer les mipmaps comme prétendue optimisation ;
- effectuer des uploads OpenGL depuis un worker sans contexte partagé maîtrisé ;
- utiliser un RAM disk ou une exclusion antivirus comme « correctif » ;
- rétrograder globalement les cartes en x2 sans mesures et sans nouvelle QA.

---

## Protocole reproductible

### Variantes A/B

- **A — Vanilla strict** : moteur et ressources officiels.
- **B — Runtime témoin** : renderer BG2HD chargé, zone stock.
- **C — Patch exact** : runtime et contenu épinglé par `content.json`.
- **D — Build diagnostic isolé** : identique à C, sauf diagnostic par page agrégé/désactivé.
- **E — Télémétrie** : C avec `PerformanceLogs=true`, exclu des scores principaux.

Les ressources vanilla proviennent normalement des KEY/BIF, tandis que le patch installe les PVRZ séparément dans `override`. Le test doit donc compter les `Create/Open/Read` par `.PVRZ`, `.TIS`, `.BIF` et pour le journal.

Zones minimales : zone stock, AR0012, AR0602, AR1300, AR1200, AR0900 et AR0300 jour/nuit.

### États de cache

- **C0** : OS froid après redémarrage.
- **C1** : moteur froid, cache OS chaud.
- **C2** : zone froide dans une session chaude.
- **C3** : fermeture/réouverture immédiate de la carte.

Minimum recommandé : cinq répétitions C0, dix répétitions C1/C2/C3, ordre équilibré ABCCBA, même sauvegarde hashée, même caméra, heure, groupe, zoom et scripts.

### Instrumentation

WPR/WPA est adapté à la corrélation CPU, fichiers, défauts de page et GPU ; WPR repose sur ETW et accepte des marqueurs de scénario. [Documentation Microsoft WPR](https://learn.microsoft.com/en-us/windows-hardware/test/wpt/wpr-command-line-options)

```powershell
wpr -start GeneralProfile.Light -start GPU.Light -start FileIO.Light -filemode
wpr -marker "BG2_MAP_OPEN_BEGIN"
# ouverture puis fermeture contrôlées
wpr -marker "BG2_MAP_OPEN_END"
wpr -stop "<sortie>\trace.etl" "BG2HD map-open <run-id>" -compress
```

PrésentMon fournit une ligne par frame avec temps CPU/GPU/affichage et ciblage par PID. Il faut épingler la version et son SHA, puis cibler `BaldurReal.exe` par PID. [Documentation officielle PresentMon](https://github.com/GameTechDev/PresentMon/blob/main/README-ConsoleApplication.md)

```powershell
PresentMon.exe `
  --process_id <PID> `
  --output_file "<sortie>\presentmon.csv" `
  --qpc_time `
  --timed 90
```

GPUView permet ensuite de distinguer attente CPU, file GPU vide, migrations et activité du pilote à partir de l’ETL. [Documentation Microsoft GPUView](https://learn.microsoft.com/en-us/windows-hardware/drivers/display/using-gpuview)

Mesures à publier :

- clic → première image complète stable ;
- frametime p50/p95/p99/p99,9/max ;
- frames >16,7/33,3/50/100/250 ms ;
- octets, nombre et latence des lectures PVRZ/BIF ;
- écritures du journal pendant l’ouverture ;
- CPU busy/wait et piles du thread de rendu ;
- Private Bytes, Working Set Private, commit et hard faults ;
- mémoire GPU locale/non locale, migrations et évictions ;
- uploads/readbacks GL et suppressions de textures ;
- résidu RAM/VRAM après fermeture et changement de zone.

RAMMap peut documenter le cache fichier et les pages physiques, mais le redémarrage reste la référence formelle pour C0. [Documentation Microsoft RAMMap](https://learn.microsoft.com/en-us/sysinternals/downloads/rammap)

## Budgets d’acceptation proposés

Ce sont des objectifs, pas des résultats actuels.

| Mesure | Cible |
|---|---|
| Réouverture chaude, profils modestes+ | ≤100 ms |
| Première ouverture froide SSD | ≤250 ms et ≤1,25× vanilla |
| Première ouverture froide HDD | ≤1 s et ≤1,25× vanilla |
| 60 Hz | p95 ≤20 ms, p99 ≤33,3 ms, aucune frame chaude >100 ms |
| 164 Hz sur la machine locale | p95 ≤8,3 ms hors ouverture |
| Hook BG2HD seul | p95 ≤0,83 ms/frame, max ≤2 ms |
| Croissance sur cinq réouvertures | <16 Mio RAM et VRAM |
| Résidu après changement de zone | ≤128 Mio au-dessus du témoin sous 30 s |
| VRAM | payload BC attendu +15 %, sans migration chaude |
| Uploads à la réouverture chaude | zéro nouvelle page |
| Journal de production | zéro INFO/flush par page |

## Plan de mise en œuvre réversible

1. Capturer A/B/C avec la configuration propre, sans modifier le runtime.
2. Créer un nouveau build expérimental contenant uniquement l’agrégation des logs et le garde WTPOOL.
3. Rejouer AR1200, AR1300 et AR0900 sur NVMe puis HDD.
4. Ajouter ensuite les marqueurs et compteurs natifs manquants.
5. Ne traiter le chargement progressif et le cache d’animations qu’après attribution exacte.
6. Toute modification de contenu devra créer un nouveau run et repasser QA carte, nuit, occlusion, eau, sauvegardes et restauration.

Le dépôt est resté propre. Aucun test de build ou ingame n’a été lancé, puisqu’aucun code n’a été changé et que l’audit était en lecture seule. Aucun élément `validated-installed` n’a été produit : aucune intégration au manifeste de release n’est applicable.
