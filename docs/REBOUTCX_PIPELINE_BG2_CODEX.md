# ReboutCX — runbook sprites BG2EE

> Projet : `Gaurox/BG2-HD-Visual-Project`. P0–P2 validées ; P3–P7 non exécutées.
> Alternative ReboutCX **x2**, xBR récupérable, runtime indexé existant, validation par phase.

## 0. Règles

- Commencer par `git status --short` ; lire `AGENTS.md`, puis seulement les références utiles.
- Une phase autorisée à la fois ; résultat testable puis accord utilisateur avant la suivante. Généralisation après prototype accepté seulement.
- Jobs/runs/preuves/QA xBR intacts ; nouveaux chemins candidats, aucun `--force` sur run scellé.
- `source != production != QA != installation != release`. Réutiliser jobs/manifests, `current-generation.json`, `active-test.json`, `sprite/index/qa-decisions/` ; aucun suivi supplémentaire.
- Acceptation offline ≠ QA ingame. Ne pas rouvrir la QA des composants dont octets et contrat runtime restent inchangés.
- Jeu + InfinityLoader fermés avant install/restore. TP2/staging/payload release/`content.json`/archives/manifeste release hors périmètre sans demande distincte.
- Chemins internes relatifs au dépôt ; outils externes via `config://`. Modèle/exécutables hors Git ; licence à vérifier avant toute redistribution.
- Échec : pas de publication ; diagnostic dans le run ; restaurer l'état modifié seulement.

## 1. Architecture vérifiée / références

Chemins de scripts abrégés ci-dessous : sous `pipeline/scripts/`.

| Besoin | Référence |
|---|---|
| Domaine/layout | `sprite/README.md`, `sprite/FOLDER_LAYOUT.md`, `sprite_layout.py` |
| Identité/éligibilité | `sprite/index/sprite_animations.csv`, `sprite_families.csv`, `sprite_resources.csv`, `sprite/index/manifest.json` |
| Baseline | `sprite/XBR2X_RASTER_CONTRACT.md`, `sprite/PROCESSING.md` |
| Sources | `bam_export.py::decode_bam`, `extract_sprite_sources.py`, `materialize_sprite_sources.py` |
| Raster/formats | `run_creature_sprite_x2.py` : `SourceFrame`, `load_source_frames`, `run_xbr`, `xbr_provenance_indices`, `map_output`, `inspect_registry` |
| Catalogue | même runner : `catalog_source_collection`, `read_sealed_catalog_index`, `write_registry_catalog_index`, `build_catalog_delta` ; `generate_sprite_family_append.py` |
| Installation | `Install-CreatureSprite-XN-Catalog-Test.ps1`, `Restore-CreatureSprite-XN-Catalog-Test.ps1`, `ThinInstall.ps1` |
| Runtime | `engine/InfinityEngine-Enhancer/source-patchee/src/iee/creature_sprite_x2.*`, `core/config.*` ; `pipeline/runtime/manifests/` |
| Paths | `config/workspace-paths.json`, `config/workspace-paths.example.json`, `workspace_paths.py` |

Contrats existants :

- xBR : `XBR/xbr2X`, x2, 1 passe, `antialias=false`, `xbr_blend=false`. `map_output()` refuse les couleurs étrangères ; provenance d'indice vérifiée pour les doublons RGBA.
- BAM V1 : 256 indices. Registre : indices HD + représentants source ; dimensions/centres/cycles logiques x1. Runtime : indices → palette active `CVidPalette::Realize`, sans palette RGB HD nouvelle.
- Feuilles V2 legacy ou xN V3 ; catalogue courant V2 + shards V5, `XPRESS_HUFF-or-raw-per-frame-v1`. Réutiliser formats/limites du code ; versions catalogue et shard distinctes.
- `upscale_contract`, `load_job`, `verify_build` imposent xBR/hashes. Matérialisation couplée à ces jobs : ReboutCX non accepté directement.
- Catalogue : méthode commune parent/membres imposée ; delta = nouveaux IDs uniquement ; création d'une racine vierge refusée par `build_catalog`. **Append actuel ≠ remplacement.**
- `prepare` feuille extrait, construit le pack **et le runtime** : ne pas l'utiliser pour le prototype offline.
- Installation actuelle : copies atomiques par fichier, shards conservés ; `already-installed` ne vérifie pas le hash actif et `status` lit le reçu. A/B à renforcer en P4.

Pointeur canonique : résoudre `generate_sprite_family_append.py::DEFAULT_CATALOG_POINTER`, actuellement :

```text
sprite/catalogs/creature-x2-nearest/runs/catalog-x2-nearest/runs/catalog-xbr2x-x2/current-generation.json
```

## 2. Contrat ReboutCX

### Raster / palette

```text
BAM + métadonnées
  ├─ RGBA source original → xBR2x vérifié → guide_index_x2
  └─ RGB préparé selon P0 → ReboutCX x4 → réduction contrôlée x2 → RGB cible
RGB cible + guide + classes autorisées → quantification → indices x2 → registre existant
```

- **`target_scale=2` obligatoire**, `2W × 2H`. Confirmer le modèle x4 (`4W × 4H`) en P0 ; autre échelle = recette à faire accepter, cible inchangée.
- Réduction RGB **avant** quantification. Fixer filtre, espace couleur, arrondi, alignement, padding/crop et RGB sous transparence ; aucun auto-crop/déplacement des centres.
- Frames indépendantes, aucune spritesheet/composition aplatie. Association `(resref, frame_index)` ordonnée ; nombre/identité/dimensions vérifiés.
- Guide xBR calculé sur RGBA original, RGB sous alpha nul compris ; reconstruire son RGBA et vérifier l'égalité avec la sortie xBR avant usage.
- `alpha_mode=xbr2x-mask-v1` : masque `0/255` dérivé du guide. Masque offline seulement ; ombre/translucidité restent appliquées par la palette moteur.
- **`false_color=0` ne suffit pas** : auditer INI complet, palette effective, indices ombre/réservés, substitutions et usages source. `Realize` ne documente pas à lui seul ces classes.

```text
used = unique(source_indices) ; T = transparent confirmé
C(i) = classe de comportement palette démontrée pour le profil/calque ; G = guide xBR x2

G[p] == T : out[p] = T
sinon :
  allowed[p] = {i ∈ used : i != T et C(i) == C(G[p])}
  out[p] = argmin(distance_OKLab(RGB_cible[p], palette_reference[i]), i)
```

- Indices ordinaires interchangeables : classe commune. Indice spécial à conserver exactement : singleton. Ombre jamais candidate pour un pixel de matière.
- Classe/palette inconnue ou candidats vides pour pixel visible → arrêt ; aucun nearest global ni plage inventée.
- `palette_reference` = palette BAM si absence de substitution confirmée ; sinon palette effective à identifier avant traitement. Adressage/indices moteur conservés.
- OKLab euclidien v1 : conversion sRGB→linéaire→OKLab et précision versionnées ; **sans dithering** ; égalité départagée par indice croissant dans la classe. RGB identique ≠ classe identique. Pas de `PIL.quantize()` libre.
- Frame transparente : court-circuit modèle. Dimensions nulles : auditer la normalisation du décodeur avant toute assertion de géométrie.
- Invariants : `unique(out) ⊆ used`, classe du guide conservée, transparence exacte, représentants source valides, géométrie/cycles/ordre/identité BAM inchangés. Preview reconstruite depuis les indices finaux.

### Recette / chemins

Provenance minimale dans job/manifeste existants :

```text
source BAM/manifest SHA ; sélection resref/frame ; profil palette/classes/version
provider=chainner ; version chaiNNer ; backend/versions effectives (PyTorch/Spandrel/CUDA si utilisés)
model SHA ; chaîne .chn SHA ; overrides ; device/précision ; tiles/overlap ; padding
model_scale mesurée ; target_scale=2 ; réduction ; préparation RGB ; alpha_mode
quantizer/code/paramètres ; dither=false ; guide : Scalepix/adapter SHA ; hashes pixels/indices
```

Hashes ≠ déterminisme GPU. RGB fixé → indices identiques ; inférence répétée en P0. Tolérance RGB chiffrée, variations d'indices signalées. Recette/source/code pertinent changé → nouveau run, cache invalidé.

```text
sprite/research/reboutcx/chains/                       # .chn communes
sprite/families/monsters/7fxx/7f02-mbeh-beholder/
  jobs/reboutcx-p1-v2.json                             # prototype P1
  jobs/reboutcx-p2-mbeh-v2.json                        # famille complète P2
  research/reboutcx/                                  # témoins minimaux
  runs/reboutcx-p1-v2/                                # distinct de x2-nearest-v1
  runs/reboutcx-p2-mbeh-v2/                           # composants/QA P2 non installables
sprite/catalogs/creature-x2-reboutcx/
  jobs/                                              # base + remplacements
  runs/<run>/                                        # générations + current-generation.json
```

Sources : `sprite/ressources/` + manifests existants, sans duplication BAM. Runs/PNG déjà ignorés : exceptions ciblées pour témoins utiles seulement. Reçu commun : P4.

## P0 — Caractérisation chaiNNer/ReboutCX + audit MBEH

**But :** recette reproductible et indices autorisés démontrés ; aucune installation.

1. Épingler génération xBR, manifest/catalogue SHA, contrat runtime. Contrôler séparément reçu, catalogue installé, INI et manifeste de capacités de la DLL installée.
2. Cible : `0x7F02:body:base-resref:MBEH:MBEH`, profil `monster-bg2ee-2.7.3.0`. Index : runtime/pipeline ready, blockers/collisions vides. Repère 2026-09-14 : 13 BAM, 6 831 frames, `false_color=0`.
3. Réutiliser `sprite/families/monsters/7fxx/7f02-mbeh-beholder/source/stock/` ; si absent, extraction/matérialisation ciblée via contrat existant, descripteur ReboutCX séparé.
4. Auditer indices utilisés, doublons RGB, ombres/réservés, palette effective ; définir `C` dans la recette. Confirmer par documentation/profil moteur/source, pas par aspect visuel.
5. Transparence : `decode_bam` utilise l'octet RLE ; l'IESDP distingue index RLE et transparence. Vérifier leur concordance sur les BAM retenus ; divergence → suspendre le cas sans modifier xBR.
6. Retrouver modèle/chaîne exacts ; relever versions/backend/paramètres. Déclarer `chainner_exe`, `reboutcx_model`, `reboutcx_chain` dans `config/workspace-paths.json` **et** l'exemple ; valeurs machine dans override local/variables déclarées.
7. Sur un témoin : confirmer x4→x2, fixer réduction et préparation RGB sous transparence. Propagation éventuelle sans wrap entre bords ; tester petites dimensions/padding.
8. Vérifier `chainner --help`, `chainner run --help`, même témoin GUI/CLI. Syntaxe à confirmer : `chainner.exe run <chaine.chn> --override <inputs.json>`. Chaîne inchangée ; contrôler exit code et fichiers, pas seulement console.
9. Répéter le témoin ; comparer pixels bruts/réduits décodés, tolérance éventuelle chiffrée. Conserver source/brut/réduction/recette ; mesurer temps par frame. Déterminisme des indices : P1.

**Validation/livrable :** recette épinglée, témoin x2 reproductible, classes/transparence MBEH démontrées, CLI utilisable. CLI non validée → prototype manuel uniquement après accord explicite. Inconnue palette/modèle/resize → P1 suspendue.
**Rollback :** jeu/xBR inchangés ; conserver seulement témoin et recette utiles.

**Résultat P0 :** `sprite/families/monsters/7fxx/7f02-mbeh-beholder/jobs/reboutcx-p0-v1.json`. ReboutCX réel SHA épinglé ; chaîne chaiNNer 0.25.1 valide ; CUDA/FP16 ; x4 natif → BOX 50 % x2 ; trois CLI + GUI identiques. MBEH : index `0` transparent, `1` noir/ombre singleton, `2` marqueur exclusif des 5 184 frames nulles `1x1@(0,0)` à court-circuiter, `3..255` matière ; deux palettes, RLE/transparence concordants. Catalogue installé et `active-test.json` correspondent à la génération xBR canonique ; `CreatureSprites-XN.catalog-owner.json` est ancien et contradictoire, donc non fiable avant réparation transactionnelle P4.

## P1 — Prototype offline MBEH

**But :** bénéfice après quantification sur quelques frames, avant production complète.

- Nouveaux `reboutcx_batch.py`, `reboutcx_quantize.py` ; orchestration séparée, réutilisation décodeur/source/guide/lecteurs, aucun fork du runner complet.
- Écrivain commun à extraire seulement si nécessaire, avec non-régression xBR ciblée. Jamais de faux `algorithm=XBR/...` pour passer un validateur.
- Échantillon : courte séquence consécutive + directions/états, contours/ombre/détails. Appliquer §2 ; modèle chargé par lot, mémoire bornée.
- Livrer indices/comparaison : natif x2 NEAREST / xBR / brut réduit x2 / quantifié. Manifeste : indices utilisés, erreur moyenne/p95, temps/hashes ; métriques informatives.
- Petit registre au format existant : sérialisation/relecture exacte, **non installable** si partiel ; aucune complétude famille revendiquée.

**Tests :** déterminisme RGB fixé ; dimensions/alpha/représentants/classes ; doublons ; transparent/petites frames/bords ; sorties manquantes/dupliquées/tronquées ; changement de hash recette ; round-trip indices/métadonnées.
**Validation :** quantifié x2 accepté, invariants vérifiés. Bénéfice perdu/flicker → nouvelle recette ou rejet, aucune palette custom/runtime alternatif implicite.
**Rollback :** candidat isolé ; xBR intact. Généralisation seulement après ce prototype réel accepté.

**Résultat P1 :** `jobs/reboutcx-p1-v2.json` ; `reboutcx_batch.py`, `reboutcx_quantize.py`, `test_reboutcx_pipeline.py`. 29 frames/3 BAM, deux runs indépendants identiques pixels/indices/registre/QA ; manifeste v2 vérifié, 123 fichiers ; registre V3 x2 brut non installable, round-trip exact, SHA `6B87F4B3...`. Quantification `oklab-euclidean-f64-classed-no-dither-v1`, moyenne `0,03655`, pire p95 `0,07785`. Séquences/directions animées dans `runs/reboutcx-p1-v2/qa/`. Accepté pour passage P2 le 2026-09-14.

## P2 — Animation complète + petit échantillon

- Produire MBEH complet selon index/source épinglés : tous BAM/frames/cycles/directions. Sous-ensemble ≠ famille installable.
- Comparer animations x2, centres natifs alignés, plusieurs fonds/vitesse normale : silhouette, détails, ombre, halo, flicker, directions ; mesurer temps/volumes.
- Si MBEH complet convaincant : au plus deux familles contrastées, portée acceptée et audit palette propre. Candidats `false_color=0` : Bodhi `0x7F30/NBOH`, Irenicus `0x7F37/NIRE` ou `0x7F3A/NIRO`. Golem de pierre à identifier ; aucune assimilation implicite au golem d'argile.
- Verdict dans le run : préférence ReboutCX/xBR, équivalence ou rejet.

**Validation :** couverture complète vérifiée, MBEH + petit échantillon acceptés, défauts temporels tolérables.
**Rollback :** runs isolés ; aucune installation ni modification du catalogue xBR.

**Résultat P2 :** `reboutcx_full.py`, `test_reboutcx_full.py` ; traitement borné, cycles natifs exacts, composants V3 x2 bruts par resref sous la limite 128 MiB, doublons rendus une fois puis clonés/vérifiés. MBEH final : `jobs/reboutcx-p2-mbeh-v2.json`, `runs/reboutcx-p2-mbeh-v2/`, manifeste `9D88635B...` ; 13 BAM/6 831 frames/5 184 nulles/765 cycles/15 939 slots, 9 sources uniques/1 107 inférences, 13 composants/117 604 200 octets, 18 GIF ; second run identique composants/QA/couverture/métriques. Erreur pondérée `0,03540`, pire p95 `0,08823`.

Échantillon complet : Bodhi `0x7F30/NBOH`, job/run `reboutcx-p2-sample-v1`, manifeste `2A3ED34E...` ; 13 BAM/8 100 frames, 17 286 400 octets, erreur `0,02877`, pire p95 `0,10139`, 10 GIF. Irenicus `0x7F37/NIRE`, job/run homonyme, manifeste `3265A5C7...` ; 13 BAM/7 776 frames, 17 781 704 octets, erreur `0,02363`, pire p95 `0,10154`, 10 GIF. Audit confirmé pour les deux : `0` transparent, `1` noir/ombre, `2` marqueur exclusif `1x1@(0,0)`, `3..255` matière. NIRO écarté : resrefs partagés avec `0x7F42/RED_WIZARD`, `new_palette=NIRO_RD`. Trois runs `verify` réussis ; rendu GIF MBEH/NBOH/NIRE validé humainement le 2026-09-14. Aucun catalogue/install/runtime modifié.

## P3 — Catalogue dérivé : base xBR + remplacements ReboutCX

**But :** catalogue complet séparé ; aucune famille hors sélection ne perd son xBR.

**À implémenter :** assembleur limité réutilisant le runner ; `catalog-append` insuffisant. Contrat runtime commun, provenance par composant ; adaptation minimale des lecteurs/validateurs, contrats xBR historiques inchangés.

```text
base = génération xBR immuable + manifest/catalogue SHA
replacement = (animation_id, ancien composant/digest attendu, nouveau composant/digest)
derived = base - appartenances remplacées + composants ReboutCX
```

- Unité : composant complet d'une animation ; mêmes resrefs/sources/hashes/frames/cycles/centres/profil propriétaire. ID/digest inconnu, doublon ou portée différente → rejet.
- Préserver tous les IDs/composants hors remplacement. Composant partagé : modifier seulement les appartenances ciblées ; autres utilisateurs inchangés.
- Une seule résolution par `(animation_id, resref)` ; mêmes resrefs dans des animations distinctes possibles selon contrat existant.
- Réutiliser shards scellés inchangés ; construire seulement les nouveaux composants. Recalculer memberships/directory/digests/totaux ; aucun upscale/repack global du parent.
- Nouveau job/manifeste sous `creature-x2-reboutcx` : base, remplacements, provenance par composant, `scale=2`, hashes/snapshot du job. Ne pas étiqueter une recette mixte comme xBR/ReboutCX homogène.
- Publier le pointeur ReboutCX après contrôles ; xBR canonique intact, noms runtime standards dans le pack.

**Tests :** données hors remplacement identiques ; résolutions uniques ; sources/métadonnées égales ; mauvais ID/digest/resref refusé ; partage préservé ; lecture catalogue V2/shards V5 compatible ; déterminisme ; échec avant publication conserve le pointeur. Contrôler index/nouveaux payloads, réutiliser preuves scellées du parent, pas de scan global implicite.
**Validation :** catalogue complet, diff limité aux remplacements, xBR intact. QA xBR non héritée par ReboutCX.
**Rollback :** ancien pointeur expérimental si nécessaire ; aucune installation à restaurer.

## P4 — Installation A/B réversible

**But :** profils séparés, un catalogue actif, aucun rebuild runtime.

Renforcer les scripts d'installation §1 et commandes runner, sans second installateur. Résoudre les capacités de la DLL installée ; défaut historique `-RuntimeManifest` non fiable, aucune substitution DLL pour le satisfaire.

Réutiliser **un emplacement** `ingame-installation/active-test.json` pour cette installation du jeu, résolu depuis l'état existant et indépendant du profil source. Profil/génération/hashes/transaction/rollback dans ce reçu ; pointeurs de production séparés, aucun nouveau registre global.

```ini
[Shaders]
EnableCreatureSpriteUpscaleTest=true
EnableCreatureSpriteX2Test=false
EnableCreatureSpriteLinearFiltering=false
CreatureSpriteFilter=Nearest
```

Dernière clé prioritaire sur l'ancien booléen. Modifier seulement ces quatre valeurs ; DLL/autres clés conservées.

Transaction à implémenter :

1. Jeu/InfinityLoader fermés, verrou d'installation. Hasher le catalogue actif, comparer reçu/base attendue ; divergence → arrêt.
2. Vérifier build, catalogue cible, capacités et shards requis **même déjà présents**. Nom SHA ≠ contenu vérifié ; preuve d'intégrité réutilisable seulement selon son contrat.
3. Sauvegarder octets/hashes catalogue, INI, reçu ; enregistrer la transaction récupérable dans le reçu existant avant mutation active.
4. Copier/publier atomiquement les nouveaux shards ; vérifier hashes. Anciens shards autorisés : seule l'absence de composants concurrents **référencés** compte.
5. Préparer INI, remplacer atomiquement le catalogue, contrôler fichiers actifs, finaliser reçu. Plusieurs fichiers ≠ atomicité globale ; interruption récupérable au prochain appel, jeu fermé.
6. `status` contrôle le disque ; `already-installed` exige génération/catalogue, intégrité requise et quatre clés conformes. Reçu seul insuffisant.
7. Erreur : restaurer catalogue/INI/reçu exacts, vérifier hashes. Restore contrôlé par transaction/état actif ; répétition sans dérouler un backup antérieur.

**Tests :** xBR→ReboutCX→xBR, hashes initiaux retrouvés ; reçu périmé/autre profil ; shard absent/corrompu ; hash catalogue faux ; panne copie/commit et reprise ; restore répété ; autres clés intactes. Shards inertes conservés.
**Validation :** switch bidirectionnel, état fondé sur disque, rollback exact ; installation technique seulement.

## P5 — QA ingame statique

- Profils P4 en `Nearest`, même taille/zoom/contexte. Familles remplacées : idle/marche/attaque/cast/mort, directions, ombre/occlusion, fonds clairs/sombres, effets palette/performance.
- Vérifier centres/cycles, halo/flicker/détails ; témoins hors remplacement inchangés.
- Acceptation utilisateur : décision immuable `sprite/index/qa-decisions/`, portée, génération/catalogue/composants, recette et contrat runtime. Aucune release.

**Validation :** rendu accepté ingame, aucun défaut bloquant sur la portée.
**Rollback :** rejet → xBR via P4 ; conserver P1–P4. P6 sur accord distinct.

## P6 — Character false-color : humain guerrier

**But :** mêmes indices x2 sous plusieurs couleurs moteur ; body avant équipements.

- Cible `0x6100/FIGHTER_MALE_HUMAN`, `character-bg2ee-2.7.3.0` ; famille/armure via index et `generate_character_complete_x2_jobs.py`. `6100-minsc` intact.
- Auditer mapping profil/calque puis module de classes **unique et testé**. `Realize` fournit les couleurs réalisées, pas la sémantique complète.
- Classes : réservés, plages simples, **combinaisons de couleurs**, comportement des rampes/interpolations. Pas seulement sept classes ; singleton si nécessaire ; inconnue → rejet.

```text
G = guide xBR2x vérifié
class[p] = semantic_class(profile, layer, G[p])
allowed[p] = indices source utilisés de même classe, hors transparent
out[p] = nearest contraint selon §2
```

- Classe = même dépendance de recoloration, pas RGB similaire. Le guide impose classe/masque ; jamais nearest interclasses.
- Petit body sous ≥3 palettes contrastées : modifier une couleur affecte uniquement ses indices dépendants, **classes combinées incluses**. Comparer à une réalisation de référence ; tester son propre mapping contre lui-même ne le valide pas.
- Après acceptation body : arme, puis autres couches utiles séparément ; centres x1, composition moteur, jamais inférence aplatie. Produire ensuite tous les cycles/frames des seuls composants retenus ; réutiliser P1/P3.

**Tests :** dépendances simples/combinées ; doublons interclasses ; source-only/transparence ; ≥3 palettes sans rebuild ; déterminisme ; centres/couverture/composition.
**Validation :** body puis au moins body+arme convaincants offline, recoloration correcte. Guide trop contraignant → travail distinct, aucune classe relâchée silencieusement.
**Rollback :** runs isolés, aucune installation ; inconnue sémantique bloque le composant concerné.

## P7 — Installation / QA Character

- P3 : nouveau catalogue épinglé avec remplacements Character acceptés ; autres appartenances et candidats ReboutCX conservés selon sélection explicite.
- P4 : même installation/switch/restore. QA : body/arme, actions/directions, armures/couches incluses, ≥3 couleurs joueur, changement sans rebuild/réinstallation, save/load, ombre/halo/flicker/alignement, retour xBR.
- Acceptation : décision QA immuable de portée exacte ; rejet : profil précédent vérifié. Retour xBR pur toujours disponible.

**Validation :** Character accepté ingame, recoloration/composition et A/B corrects.
**Hors périmètre :** extension, Recommended, choix menu/INI, hot-swap, release : demande distincte.

## 3. Vérifications / reprise

- Tests adaptés au risque : raster/formats P1–P2, catalogue P3, transactions P4, sémantique P6. Pas de C++ si runtime inchangé.
- `python pipeline/scripts/test_changed.py --targeted --path <fichier> --run` ; nouveau module non associé → test ciblé explicite ou association. Sélection vide ≠ validation.
- Code commun xBR modifié → fixtures de non-régression octets/contrats ; aucun rebuild des générations validées. `verify --full-verify`/build release global : finalisation explicitement demandée seulement.
- Reprise : résultat accepté + job/provenance + accord utilisateur. Retour : artefact, vérification, inconnue bloquante ; aucun journal supplémentaire.

Références externes ciblées : [CLI chaiNNer](https://github.com/chaiNNer-org/chaiNNer/wiki/05--CLI) (expérimentale, vérifier localement), [BAM V1](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/bam_v1.htm), [INI animations](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/ini_anim.htm), [false-color/opcode 7](https://gibberlings3.github.io/iesdp/opcodes/bgee.htm#op7).
