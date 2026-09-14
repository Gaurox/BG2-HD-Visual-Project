# ReboutCX — runbook sprites BG2EE

> Projet : `Gaurox/BG2-HD-Visual-Project`. P0–P4 réalisées ; P5 testée sur sélection, réserves ci-dessous. P7.2 Character retenue non inférieure ; audit P8 `0x6100` terminé.
> Alternative ReboutCX **x2**, xBR récupérable, runtime indexé existant, validation par phase.

## 0. Règles

- Commencer par `git status --short` ; lire `AGENTS.md`, puis seulement les références utiles.
- Une phase autorisée à la fois ; résultat testable puis accord utilisateur avant la suivante. Généralisation après prototype accepté seulement.
- Jobs/runs/preuves/QA xBR intacts ; nouveaux chemins candidats, aucun `--force` sur run scellé.
- `source != production != QA != installation != release`. Réutiliser jobs/manifests, `current-generation.json`, `active-test.json`, `sprite/index/qa-decisions/` ; aucun suivi supplémentaire.
- Acceptation offline ≠ QA ingame. Ne pas rouvrir la QA des composants dont octets et contrat runtime restent inchangés.
- Jeu + InfinityLoader fermés avant install/restore. TP2/staging/payload release/`content.json`/archives/manifeste release hors périmètre sans demande distincte.
- Annoncer les actions ; aucun contrôle GUI/clavier/souris ni lancement/fermeture du jeu sans autorisation. Les essais ingame sont effectués par l'utilisateur.
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
- Installation : transaction/contrôle disque renforcés en P4 ; voir résultats P4.1–P4.5. Reçu de catalogue et reçu d'installation DLL restent distincts ; vérifier les octets actifs des deux.

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
- Inférence par frame/calque, aucune spritesheet/composition aplatie. QA assemblée ensuite aux centres natifs, redimensionnement uniforme seulement ; association `(resref, frame_index)` vérifiée.
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
- Invariants : `used` propre à la **frame source**, `unique(out) ⊆ used`, classe du guide conservée, transparence exacte, représentants source valides, géométrie/cycles/ordre/identité BAM inchangés. Preview reconstruite depuis les indices finaux ; ne pas élargir les candidats à toute l'animation pour masquer un scintillement.

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

**Implémentation :** `reboutcx_catalog.py` réutilise lecteurs/écrivains du runner ; `catalog-append` reste réservé aux nouveaux IDs. Contrat runtime commun, provenance par composant, contrats xBR historiques inchangés.

```text
base = génération xBR immuable + manifest/catalogue SHA
replacement = (animation_id, ancien composant/digest attendu, nouveau composant/digest)
derived = base - appartenances remplacées + composants ReboutCX
```

- Unité visée : composant complet d'une animation ; mêmes resrefs/sources/hashes/frames/cycles/centres/profil propriétaire. **Code actuel : `load_replacement()` exige que ce composant soit l'unique appartenance de l'animation** ; adapter en P7 pour Character, pas de suppression du contrôle seule. ID/digest inconnu, doublon ou portée différente → rejet.
- Préserver tous les IDs/composants hors remplacement. Composant partagé : modifier seulement les appartenances ciblées ; autres utilisateurs inchangés.
- Une seule résolution par `(animation_id, resref)` ; mêmes resrefs dans des animations distinctes possibles selon contrat existant.
- Réutiliser shards scellés inchangés ; construire seulement les nouveaux composants. Recalculer memberships/directory/digests/totaux ; aucun upscale/repack global du parent.
- Nouveau job/manifeste sous `creature-x2-reboutcx` : base, remplacements, provenance par composant, `scale=2`, hashes/snapshot du job. Ne pas étiqueter une recette mixte comme xBR/ReboutCX homogène.
- Publier le pointeur ReboutCX après contrôles ; xBR canonique intact, noms runtime standards dans le pack.

```powershell
python pipeline/scripts/reboutcx_catalog.py build sprite/catalogs/creature-x2-reboutcx/jobs/catalog-reboutcx-validated-v1.json
python pipeline/scripts/reboutcx_catalog.py verify sprite/catalogs/creature-x2-reboutcx/jobs/catalog-reboutcx-validated-v1.json
```

`build` refuse une génération existante ; `verify` est la reprise normale. Nouvelle sélection/entrée/code → nouveau job/run, jamais réécriture du run scellé.

**Tests :** données hors remplacement identiques ; résolutions uniques ; sources/métadonnées égales ; mauvais ID/digest/resref refusé ; partage préservé ; lecture catalogue V2/shards V5 compatible ; déterminisme ; échec avant publication conserve le pointeur. Contrôler index/nouveaux payloads, réutiliser preuves scellées du parent, pas de scan global implicite.
**Validation :** catalogue complet, diff limité aux remplacements, xBR intact. QA xBR non héritée par ReboutCX.
**Rollback :** ancien pointeur expérimental si nécessaire ; aucune installation à restaurer.

**Résultat P3 :** `reboutcx_catalog.py`, `test_reboutcx_catalog.py`. Prototype `catalog-reboutcx-mbeh-v1` : génération `D82D2182...`, catalogue `BFC8C633...`, 194/195 animations inchangées, 451 shards xBR hardlinkés + 1 ReboutCX. Catalogue validé `catalog-reboutcx-validated-v1` : génération `2A732E53...`, manifeste `2E083A69...`, catalogue `CE6546CE...`, contenu logique `55BD0105...` ; 195 animations/439 composants/452 shards/52 984 entrées, 192 animations inchangées, shards xBR 403/419/420 remplacés par `672272F9...`/`CE54CC2E...`/`AFB96C31...`, 449 autres hardlinkés. Contrats resrefs/sources/géométrie/centres/représentants/cycles identiques ; V2/V5, x2 et inventaire global vérifiés ; nouveaux shards relus intégralement, parent scellé réutilisé sans scan global. Pointeur xBR canonique SHA `71DE2662...` inchangé ; aucun fichier jeu/runtime/install/release modifié.

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

Transaction validée hors ligne ; exécution réelle différée à P4.4 :

1. Jeu/InfinityLoader fermés, verrou d'installation. Hasher le catalogue actif, comparer reçu/base attendue ; divergence → arrêt.
2. Vérifier build, catalogue cible, capacités et shards requis **même déjà présents**. Nom SHA ≠ contenu vérifié ; preuve d'intégrité réutilisable seulement selon son contrat.
3. Sauvegarder octets/hashes catalogue, INI, reçu ; enregistrer la transaction récupérable dans le reçu existant avant mutation active.
4. Copier/publier atomiquement les nouveaux shards ; vérifier hashes. Anciens shards autorisés : seule l'absence de composants concurrents **référencés** compte.
5. Préparer INI, remplacer atomiquement le catalogue, contrôler fichiers actifs, finaliser reçu. Plusieurs fichiers ≠ atomicité globale ; interruption récupérable au prochain appel, jeu fermé.
6. `status` contrôle le disque ; `already-installed` exige génération/catalogue, intégrité requise et quatre clés conformes. Reçu seul insuffisant.
7. Erreur : restaurer catalogue/INI/reçu exacts, vérifier hashes. Restore contrôlé par transaction/état actif ; répétition sans dérouler un backup antérieur.

**Tests :** xBR→ReboutCX→xBR, hashes initiaux retrouvés ; reçu périmé/autre profil ; shard absent/corrompu ; hash catalogue faux ; panne copie/commit et reprise ; restore répété ; autres clés intactes. Shards inertes conservés.
**Validation :** switch bidirectionnel, état fondé sur disque, rollback exact ; installation technique seulement.

**Checkpoint P4.1 :** l'installateur normalise jobs/pointeurs/manifests xBR et dérivés, épingle job/manifeste/catalogue ReboutCX puis remonte au job xBR parent pour `game_root`/compatibilité. `-VerifyOnly` testé sur faux jeu ; installation dérivée exige `-EnableDerivedInstall`. Runtime, installation réelle et reçu actif non lus/modifiés.

**Checkpoint P4.2 :** xBR et dérivé résolvent l'unique reçu sous le run xBR parent ; manifeste runtime omis repris du reçu actif. `-VerifyOnly` hash catalogue source/actif, tous shards sources et tout shard cible déjà présent, DLL ; il lit les valeurs effectives `EnableCreatureSpriteUpscaleTest=true`, `EnableCreatureSpriteX2Test=false`, `EnableCreatureSpriteLinearFiltering=false`, `CreatureSpriteFilter=<reçu>`. `already-installed` exige génération + catalogue + filtre + tous shards conformes au disque. Corruptions catalogue/shards source/cible et INI divergente refusées.

**Checkpoint P4.3 :** sauvegardes catalogue/INI/reçu précédent hashées avant publication ; catalogue/INI cibles revérifiés avant finalisation. Etat `installing` : `-VerifyOnly` reste sans écriture et signale la reprise ; prochain install jeu fermé restaure d'abord exactement la transaction. Restore limité au job/génération actifs, donc répétable sans dérouler le backup antérieur ; shards ajoutés conservés inertes. 16 tests sur faux jeu : xBR→ReboutCX→xBR octet exact, reçu partagé exact, restore répété, interruption/reprise, backup corrompu bloqué avant écriture, compatibilité xBR/legacy. Installation réelle/runtime/reçu réel non lus/modifiés.

**Checkpoint P4.4 :** préflight réel `-VerifyOnly` réussi le 2026-09-14. Actif xBR génération `912AE8AE...`, catalogue `434E50C4...` ; cible ReboutCX génération `2A732E53...`. DLL, INI, catalogue actif et 452 shards sources vérifiés ; 449 shards cibles déjà présents/conformes, 3 absents attendus : `672272F9...`, `CE54CC2E...`, `AFB96C31...`. Aucune écriture/processus lancé ou fermé. P4.5 = switch réel court avec `-EnableDerivedInstall`, jeu/InfinityLoader fermés et autorisation explicite.

**Résultat P4.5 :** switch réel autorisé/réussi le 2026-09-14 ; statut `installed-pending-qa`, génération `2A732E53...`, catalogue actif `CE6546CE...`, 3 shards copiés puis 452 sources/installés revérifiés. Runtime `iee-creature-multi-new-0x1200-firkraag-v1` inchangé ; `CreatureSpriteFilter=Nearest`. Transaction `20260914T114609.2463717Z-cc84ee3e7a6c49b4968e94b3b6109434` ; backup catalogue xBR `434E50C4...`, INI et reçu précédent hashés. Jeu non lancé ; restore réel non déclenché, chemin testé P4.3 disponible.

## P5 — QA ingame statique

- Profils P4 en `Nearest`, même taille/zoom/contexte. Familles remplacées : idle/marche/attaque/cast/mort, directions, ombre/occlusion, fonds clairs/sombres, effets palette/performance.
- Vérifier centres/cycles, halo/flicker/détails ; témoins hors remplacement inchangés.
- Acceptation utilisateur : décision immuable `sprite/index/qa-decisions/`, portée, génération/catalogue/composants, recette et contrat runtime. Aucune release.

**Validation :** rendu accepté ingame, aucun défaut bloquant sur la portée.
**Rollback :** rejet → xBR via P4 ; conserver P1–P4. P6 sur accord distinct.

**Bilan P5 / reprise après `c1f55c78` (2026-09-14) :**

- `BEHOLD01`/MBEH : rendu ReboutCX accepté. `BODHI`/NBOH : correcte, scintillements sur certaines animations. `CSJON`/NIRE : effet jugé discutable. Installation réussie ≠ acceptation générale des trois rendus ; conserver le choix xBR/ReboutCX par animation/composant dans le catalogue, sans hot-swap ingame ni sélection par instance CRE.
- `FIRKRA02`/`0x1200/MDR1` : accepté après correction runtime + préchargement ; décision immuable `sprite/index/qa-decisions/multi-new/2026-09-14-accepted-1200-mdr1-firkraag-reboutcx-x2-v1.json`. Portée : rencontre testée, pas tous les dragons ni toutes les frames.
- Reprise Firkraag : jobs `sprite/families/composite-monsters/multi-new/12xx/1200-mdr1-dragon-red/jobs/reboutcx-{prototype,full}-v1.json` ; catalogue `sprite/catalogs/creature-x2-reboutcx/jobs/catalog-reboutcx-mdr1-test-v1.json`, génération `65566299...`, SHA catalogue `E43155A8...`, DLL `289E132B...`. Hashes complets et rollback : décision QA ; relire l'installation courante avant P7.
- **INI/owner catalogue ≠ classe C++ ni preuve HD.** MDR1 sérialisé owner `5`, rendu réel `MonsterMulti` (`0x32F8D0`), 9 dessins sans bordure. Correctif x2 limité à `0x1200` ; ne pas le transposer à Character. Détails : `engine/InfinityEngine-Enhancer/source-patchee/docs/creature-sprite-0x1000.md`.
- Diagnostic : établir sélection frame/palette, substitution effective, géométrie puis aspect visuel. `6/6` dessins HD parmi 9 parties enregistrées n'est pas un échec. Catalogue chargé/hook installé seuls ne prouvent pas une substitution.
- Distinguer scintillement du modèle/quantification, attente de métadonnées et échec de dessin. MDR1 précharge ses 5 shards sur worker, sans précharger indices/textures ni modifier les budgets ; aucune généralisation de ce préchargement aux 65 composants Character.

## P6 — Character false-color : humain guerrier

**But :** mêmes indices x2 sous plusieurs couleurs moteur ; body avant équipements.

**P6.1 — Audit ciblé, sans inférence.** Cible `0x6100/FIGHTER_MALE_HUMAN`, profil `character-bg2ee-2.7.3.0`, racine `sprite/families/playable-characters/6100-human-male-fighter/`. Choisir un body/une armure via index/jobs existants ; `generate_character_complete_x2_jobs.py` sert de référence, ne pas lancer la génération complète. `6100-minsc` intact.

- Démontrer mapping profil/calque : indices réservés, rampes simples, **combinaisons de couleurs et leurs poids/opérations**, effets de palette. Même ensemble de couleurs dépendantes ne suffit pas : mélanges de rapports différents à distinguer ; niveaux d'une même rampe regroupables si leur transfert de recoloration est démontré. Singleton si nécessaire ; inconnue → composant bloqué.
- Ne pas recopier les classes MBEH `3..255=matière`, ni son `null_frame_marker=2`. Confirmer transparence/ombre/frames nulles sur Character ; adapter le court-circuit seulement au cas démontré.
- `CVidPalette::Realize` donne la palette réalisée, pas sa sémantique. Référence indépendante à établir à partir du comportement moteur/documentation et de palettes témoins ; tests contre le seul nouveau mapping insuffisants. Pas de table/plage devinée.
- Écart actuel : `reboutcx_batch.py::prepare_inference_rgb`, quantification et previews de `reboutcx_batch.py`/`reboutcx_full.py` utilisent `frame.palette` BAM. Pour Character, définir une palette effective de référence **fixe**, commune à l'entrée modèle et à la quantification ; conserver indices/BAM originaux et guide xBR de provenance.
- Livrable minimal dans job/manifeste + tests : classes/version, référence palette, témoins de réalisation, règle frames nulles. Réutiliser `reboutcx_quantize.py`, sans fork des runners ; toute déduplication doit inclure profil/calque, recette/classes et palette de référence si ces données peuvent différer à BAM identique.

**Résultat P6.1 — 2026-09-14, audit offline uniquement :**

- Base code vérifiée : `c1f55c78`. Ajouts antérieurs non commités du guide conservés. Aucun contrôle GUI, lancement du jeu, modèle chargé, run produit, job xBR modifié, installation ou changement release.
- Composant retenu : `0x6100:body:armor-code:1:CHMB1`, `character-bg2ee-2.7.3.0`. Référence existante : `6100-human-male-fighter/chmb1/jobs/human-male-fighter-chmb1-xbr2x.json` sous `sprite/families/playable-characters/`. Les autres armures/calques et `6100-minsc` restent hors portée.
- Sources : `chmb1/source/manifest.json`, SHA256 `A8CECFE3FBA43A5CCD9927836B417CB0BAFD9F61136CFC2DC4556FE07966A26D` ; 23 BAM, 10 323 frames, 1 170 cycles. Hashes des 23 BAM canoniques **et** BAMC vérifiés contre ce manifeste ; aucun override BAM correspondant. `6100.INI`, `data/Patch2.bif`, locator `0x0BD00057`, SHA `EB9C3D7A65F8EFCD4738780392E0BED037FE98C0D7D26DE01F59EAF22762BA28`, sans override : `false_color=1`, `resref=CHMB`, armures B/B/B/F, `split_bams=1`.
- 214 indices source utilisés, 31 classes utilisées sur 32 ; aucun indice non classé. Palette RGB BAM identique sur les 23 ressources, SHA des 768 octets RGB `49459680B1BBAE76D855AE41ED9D45C0752AA60BB85BF06A8BB120CC6E7FEFF3`. Cette palette d'auteur n'est pas la palette moteur : `2/3` orange, mélanges différents de ceux du moteur.

**Sémantique démontrée (indices décimaux).** Référence principale : lecture/désassemblage statique de `config://bg2ee_game_root/BaldurReal.exe`, SHA `B51093A49140B2B8A7C046B4652BB8E535BE24EBBC12B1D735E0B94217A14D57`. Noms des fonctions ci-dessous identifiés par comportement ; RVAs propres à cet exécutable.

| Indices | Contrat CHMB1 |
|---|---|
| `0` | Transparence, singleton. Octet RLE header = 0 et unique vert pur BAM à l'indice 0 dans les 23 BAM. Cette coïncidence est vérifiée ici, pas postulée pour tous les BAM. |
| `1` | Ombre, singleton. RGB réservé noir ; alpha traité séparément du corps. Wrapper `0x42D2F0` : slot global initial 1, alpha `floor(128 * transparency / 255)` ; état effectif à capturer lors d'un essai moteur. |
| `2`, `3` | Deux singletons réservés, RGB moteur noir (`SetType 0x422250`, constructeur `0x421010`), pas de recoloration de matière. `3` absent des frames CHMB1. Ne fusionner ni avec l'ombre, ni avec un noir de rampe. |
| `4..87` | Sept classes de 12 nuances : métal `4..15`, mineure `16..27`, majeure `28..39`, peau `40..51`, cuir `52..63`, armure `64..75`, cheveux `76..87`. `SetRange 0x4221C0` copie les 12 pixels d'une ligne de palette vers `4+12*r`. |
| `88..255` | 21 classes de 8 nuances, une par paire `(a,b)`, `0<=a<b<7`, ordre lexicographique. Classe distincte de chacune des deux rampes et de toute autre paire. |

Formule native : `B[r,t] = gradient[color[r],t]`, puis `P[88+8*k+t] = floor((B[a,t+2]+B[b,t+2])/2)`, `t=0..7`, canal par canal sur les octets RGB ; aucun mélange en lumière linéaire. Boucle `RealizeRange 0x421F7B..0x42201D` : départ source `+0x18` = indice 6, destination `+0x160` = indice 88, incréments des rampes `+0x30`, addition entière puis `shr 1`. Aucun ratio variable ni mélange de trois couleurs dans cette boucle. Les niveaux d'une même rampe/paire sont regroupables ; aucun regroupement interpaire.

- Effets : `Realize 0x421430` distingue palette ressource/type 0 et range/type 1 ; type 1 passe par `0x42D2F0 → 0x421450`. Transformations de range et globales appliquées aux 12 nuances **avant** les mélanges : tint, complément/multiplication pour add, lumière avec saturation, flags gris/effet coloré. Les opérations/arrondis ne commutent pas avec la moyenne. Branche `0x421EE0` : recalcul des mélanges si `flags & 0x0FFF0000` ou sous-plages invalides, sinon copie des sous-plages déjà calculées. L'absence d'effet définit la référence du prototype ; le helper RGB ne prétend pas émuler tous les flags, phases, gamma ou alpha.
- Concordance indépendante : [iwd2-re `CVidPalette.cpp`, révision `87f97b4`](https://github.com/alexbatalov/iwd2-re/blob/87f97b4ee314d4b0ae829d01c2925291ac2b6672/src/CVidPalette.cpp), `CalculateSubRanges`/`SetRange` ; formule confrontée au binaire BG2EE, pas transposée sur confiance. Ordre des sept couleurs/calques : [IESDP opcode 7](https://gibberlings3.github.io/iesdp/opcodes/bgee.htm#op7).
- **Faux oracle écarté :** [Near Infinity `SpriteUtils.interpolateColors`, révision `5e65c55`](https://github.com/Argent77/NearInfinity/blob/5e65c55ffcfc2776ee38f6e58e2059cd0f0e164c/src/org/infinity/resource/cre/decoder/util/SpriteUtils.java) prend les niveaux `floor(12*t/8) = 0,1,3,4,6,7,9,10`, au lieu de `2..9`. [GemRB `SetupPaperdollColours`, révision `8637952`](https://github.com/gemrb/gemrb/blob/8637952eaa12bec845cde2ca0ef8b4c7085558a0/gemrb/core/CharAnimations.cpp) copie des rampes pour ces sous-plages : pas un oracle BG2EE non plus.
- Contre-exemple source concret : `156=204=220=(104,104,104)` dans la palette BAM ; classes respectives `mineure/cuir`, `majeure/cheveux`, `peau/armure`. Sous la référence ci-dessous : `(99,37,27)`, `(110,125,116)`, `(130,104,92)` ; fusion RGB interdite.

**Frames de remplissage.** Zéro dimension brute nulle, zéro frame entièrement transparente. 7 578 frames ont exactement `(width,height,center_x,center_y,indices)=(1,1,0,0,[2])` ; 2 745 autres frames, dont 142 utilisent aussi l'indice 2. `reboutcx_batch.is_null_frame(frame,2)` est donc réutilisable **sur ce prédicat exact** : conserver l'indice 2 en `2×2`, aucune inférence, aucun remplacement par 0, aucun changement de géométrie. Ce prédicat n'affirme pas que le pixel est invisible ingame. `bam_export.decode_bam` normalise une dimension zéro en indice 0/centre 0 ; cas absent de CHMB1, aucune adaptation du décodeur nécessaire.

**Référence fixe / témoins.** `RANGES12.BMP` = `MPALETTE.BMP` octet pour octet : `data/Default.bif`, locators `0x00000189` / `0x0000012E`, BMP RGB `12×256`, SHA `7A9A654D5CBC4CEE0CA211BE05D24FB54BF8298A781C074882000D5F829D66DD`, sans override. Lire les lignes dans l'ordre image haut→bas après décodage BMP. Couleurs résolues explicites, aucune entrée aléatoire `RANDCOLR.2DA` (`200..255`) dans les témoins.

| Usage | Lignes `(métal,mineure,majeure,peau,cuir,armure,cheveux)` | SHA256 palette, 256×3 octets RGB ordre indices |
|---|---|---|
| Référence fixe v1 | `30,47,57,12,39,21,3` | `54A3141583B8395FB23B0792D9768857D08BAFECBDB94E583BA773F3F7CBB2EA` |
| Témoin B | `21,57,47,8,66,30,0` | `2CC296F8479CD10EC38F5B95C72F88C8C3D545002B3DD788368EBAE0C0DFB10E` |
| Témoin C | `19,63,66,15,39,26,4` | `1BB2918E8F7380603D25071AAE5E2637A51B8B81B5C5BFE247A45B2027D5B2F3` |

Témoins **calculés offline, pas capturés ingame** : interprétation bornée des instructions du bloc natif `[0x421F7B,0x42201E)` (163 octets, SHA `C8E05C9238F186AA07D72AAC38CC793BFC74CDCA588FCD691271A6A5CCC645B4`), 3 557 instructions par cas ; aucun appel ni exécution du jeu. Précondition : scratch BGRA de 256 entrées, `0=vert`, `1..3=noir`, sept rampes copiées en `4..87`. Les trois palettes ci-dessus concordent avec le helper ; deux témoins synthétiques supplémentaires (rampes linéaires puis discontinues à sommes paires/impaires) sont figés dans les tests. La boucle constitue l'oracle des mélanges, pas celui de `Realize` complet.

- Code préparatoire unique : `reboutcx_quantize.py::{character_chmb1_classes,character_chmb1_palette_rgb}` ; versions `bg2ee-2.7.3.0-character-chmb1-32-classes-v1` / `bg2ee-2.7.3.0-character-chmb1-neutral-rgb-v1`. Helpers purs, non branchés aux runners. Validation : `python -m unittest pipeline.tests.test_reboutcx_pipeline pipeline.tests.test_reboutcx_full` → **12 tests OK** ; témoins natifs, sept variations isolées, mélanges/arrondi/sommes sans débordement, doublons interclasses, mêmes indices sous trois palettes, déterminisme, candidats par frame et prédicat indice 2.
- Intégration P6.2 : `reboutcx_batch.py` accepte maintenant le profil Character épinglé ; même référence pour entrée modèle, quantification et previews, palette/RGBA BAM conservés pour le guide xBR. `reboutcx_full.py` reste volontairement inchangé avant P6.3. Déduplication full actuellement limitée au couple de SHA BAM/BAMC, à compléter si profil/calque/recette/classes/palette varient.
- Restent non établis : gain visuel/scintillement après inférence ; palettes RGBA effectives avec éclairage/effets/translucidité et composition ingame (aucune capture dans cet audit). Aucun de ces états n'est déclaré validé.
- Essai P6.2 autorisé et exécuté ci-dessous : `CHMB1A1`, frames `0..5` (cycle 0) et `60..65` (cycle 4), soit 12 frames réellement référencées, deux directions. BAM SHA `86BBACFC9A799BC4DAA069B80F49DC15BCE41631558A1B962E15330ADC581C07`. Sortie partielle offline non installable.

**P6.2 — Petit body offline.** Courte séquence consécutive + directions/contours, recette x4→BOX x2 de P0, classes auditées ; composants partiels non installables.

```text
G = guide xBR2x vérifié
class[p] = semantic_class(profile, layer, G[p])
allowed[p] = indices source utilisés de même classe, hors transparent
out[p] = nearest contraint selon §2
```

- Le guide impose classe/masque ; jamais nearest interclasses. RGB identiques sous une palette ne justifient aucune fusion d'indices.
- Quantifier **une fois** ; reconstruire les mêmes indices sous ≥3 palettes contrastées, puis variations d'une couleur à la fois. Vérifier aussi les combinaisons, les couleurs égales puis séparées, les tons très sombres/clairs et les rampes. Comparer xBR/ReboutCX à palette réalisée identique ; ne pas réinférer/requantifier pour faire passer chaque témoin.
- Vérifier temporalité à vitesse normale après quantification : changement de nuance/candidats d'une frame à l'autre peut scintiller malgré des classes correctes. Si bénéfice perdu ou recoloration fausse, corriger la recette sur ce prototype ; aucun lissage temporel ni assouplissement sémantique implicite.

**Résultat P6.2 — 2026-09-14, en attente de revue humaine :**

- Job : `6100-human-male-fighter/chmb1/jobs/reboutcx-p6-2-v1.json` sous `sprite/families/playable-characters/` ; run local scellé `chmb1/runs/reboutcx-p6-2-v1/`, manifeste `8334EFD6320BB4158CD56B5FFD030020351C4AB67EE52CD16F718DEF567A925B`. Statut `completed-pending-human-review`, `installable=false` ; aucune installation, lancement du jeu, modification xBR/full/release ni contrôle GUI.
- `12` frames (`0..5`, `60..65`) inférées une fois sous la référence fixe puis quantifiées une fois. Les mêmes indices reconstruisent référence, B, C et sept variations isolées ; `22` GIF à `100 ms/frame`. Guide xBR source conservé séparément ; comparaisons xBR/ReboutCX utilisent la même palette réalisée. Vérification : `85` fichiers et registre partiel `D8B97C54A08204C46F7757E3A2BDC61C6A66949C34BB3E9EF0351887E7B0E726` conformes.
- Contraintes respectées : aucune sortie interclasse, hashes des indices guide/sortie consignés, répétition de quantification identique. Erreur OKLab par frame : moyenne `0,03173..0,03579`, p95 `0,08823..0,09166` ; métrique descriptive, pas seuil d'acceptation visuelle. Tests : **15 OK**.
- Couverture : `27/32` classes présentes. Absentes de cet échantillon : `reserved_3`, `mix_metal_armor_half`, `mix_metal_hair_half`, `mix_major_hair_half`, `mix_leather_hair_half`. Les sept couleurs simples et leurs mélanges présents réagissent aux variations isolées ; la revue humaine doit encore juger gain, contours et scintillement aux vitesses fournies.
- Revue reçue : passage à P6.3 autorisé le 2026-09-14 ; le prototype P6.2 demeure partiel, non installable.

**P6.3 — Body + arme offline, puis complétude ciblée après accord.** Conserver les calques séparés, assembler uniquement les previews aux centres x1, à l'échelle uniforme ; aucune inférence aplatie. Comparer body ReboutCX + arme xBR puis body + arme ReboutCX. Produire tous les BAM/cycles/frames des seuls composants retenus avant P7.

- Runtime existant : `hooks.cpp::detour_character_render` capture les palettes/calques dans l'ordre des `Realize` puis remplace **un dessin composite final** via `bind_composite_texture()`. Limite `kMaximumCompositeLayers=8` ; union des centres + bordure logique 1 pixel. Aucun chemin `Unbordered` ni boucle 9 parties MDR1.
- Composition de référence : copie du pixel réalisé non nul, alpha conservé (`overwrite_nontransparent_pixel`), pas un alpha-blend RGBA générique. `reconstruct_rgba()` offline n'émule pas à lui seul ombre/translucidité moteur. Une couche native dessinée non enregistrée/capture invalide rend le composite incomplet et maintient le rendu natif ; garder les équipements xBR référencés même pour un test body ReboutCX.

**Tests :** dépendances simples/combinées ; doublons interclasses ; source-only/transparence ; ≥3 palettes sans rebuild ; déterminisme ; centres/couverture/composition.
**Validation :** body puis au moins body+arme convaincants offline, recoloration correcte. Guide trop contraignant → travail distinct, aucune classe relâchée silencieusement.
**Rollback :** runs isolés, aucune installation ; inconnue sémantique bloque le composant concerné.

**Résultat P6.3 — 2026-09-14, prototype body + arme en attente de revue humaine :**

- Arme retenue : `SW1H01/WQLS0A1`, mêmes frames `0..5` et `60..65` que `CHMB1A1`. Source `sw1h01-wqls0/source/manifest.json`, SHA `755F092FB07EAC289EF055A5E0FD8BD181D0270089297760276919F9F1E9BA65` ; palette BAM identique à CHMB1 (`49459680...FEFF3`). Sur les 12 frames : 6 classes seulement (`transparent`, métal, cuir, armure, mélanges métal/cuir et métal/armure), aucune sortie interclasse ni frame marqueur. Le composant complet emploie 8/32 classes sur 11 BAM/2 907 frames ; il reste hors prototype.
- Ordre/centres vérifiés dans le runtime : `hooks.cpp` capture body/weapon/offhand/helmet dans l'ordre des palettes réalisées puis `creature_sprite_x2.cpp` compose aux centres natifs en écrasant par tout pixel réalisé non transparent. Corroboration externe épinglée : [GemRB `CharAnimations.cpp`, `811ace6`](https://github.com/gemrb/gemrb/blob/811ace66479e79d390f35ffe85c587d0b0f347c1/gemrb/core/CharAnimations.cpp), palettes `PAL_MAIN`/`PAL_WEAPON`, `zOrder_Mirror16`; elle ne remplace pas l'oracle BG2EE.
- Arme : job `sw1h01-wqls0/jobs/reboutcx-p6-3-v1.json`, run local scellé `sw1h01-wqls0/runs/reboutcx-p6-3-v1/`, manifeste `47235B3543C40A22E1C8EDAE0B174355ED99D5C903D00265EA3989C764C0E8CB`, registre `005C6AFD84F351131BDCA8EDDD537127A3C98D949C24B7E8382D23B1E8B7BBF9`. Une inférence CUDA/FP16 annoncée avant exécution : 12 frames, `0,71 s` modèle, puis GPU libéré. Erreur OKLab moyenne `0,01952..0,04146`, p95 `0,03937..0,14057` ; métrique descriptive.
- Composition CPU : `reboutcx_character_composite.py` relit les deux registres partiels scellés, revérifie les guides xBR, reconstruit les palettes sans réinférence/requantification et produit trois panneaux : xBR+xBR, ReboutCX body+xBR arme, ReboutCX+ReboutCX. Le run v1 est conservé mais remplacé pour la revue : son cadrage par frame masquait le diagnostic temporel. Candidat v2 : job `chmb1/jobs/reboutcx-p6-3-body-sw1h01-v2.json`, run `chmb1/runs/reboutcx-p6-3-body-sw1h01-v2/`, manifeste `73F4815B7FB927746275F45C12FE50C0854B0561835E983F275D23434CAC1ABE`, 12 GIF (2 directions × référence/B/C/métal/cuir/armure), bornes fixes par séquence. Les 12 poses contrôlées montrent centres stables, arme devant au cycle 0 et derrière au cycle 4, recoloration cohérente ; le gain sur l'arme fine reste subtil.
- Vérification : deux runs enfants et composition v2 relus par hashes ; **16 tests OK** couvrant indices/centres/transparence/ordre de couche. Statut `completed-pending-human-review`, `installable=false`. Limites : alpha/ombre/éclairage/effets et ordre réellement capturé restent à confirmer ingame ; autres cycles, composants complets, offhand/helmet et 24 classes absentes du composant arme complet non couverts. Aucune installation, jeu, GUI, xBR/full/catalogue/release modifiés.
- Prochaine étape minimale : visionner les GIF v2 cycle 0/4, puis B/C et profils isolés. Après acceptation explicite, produire les composants complets CHMB1 + WQLS0 (inférence lourde, GPU annoncé avant lancement), puis P7.1. Vérification ingame possible seulement après catalogue P7.1 validé et installation transactionnelle P7.2 explicitement autorisée, jeu et InfinityLoader fermés manuellement.

**Complétude P6.3 — 2026-09-14, autorisée après le prototype :**

- `reboutcx_full.py` accepte le contrat Character versionné : palette RANGES12 de référence pour entrée modèle/quantification/QA, guide xBR issu de la palette BAM conservé, profil et calque source vérifiés. La déduplication inclut désormais un digest profil/calque/classes/palette/recette ; aucun partage par seuls hashes BAM/BAMC entre contrats différents.
- Body : `chmb1/jobs/reboutcx-p6-3-full-v1.json` → `chmb1/runs/reboutcx-p6-3-full-v1/`, manifeste `667885EF8F6A9B7B4835E0EF8B7DE85A2D02670C089BF2C3FB67341619B7C486`. Couverture exacte : 23 BAM, 10 323 frames, 1 170 cycles/29 808 slots, 7 578 marqueurs court-circuités, 2 610 inférences uniques, 23 composants/25 753 204 octets. Erreur pondérée hors frames court-circuitées `0,03382`, pire p95 `0,11846`.
- Arme : `sw1h01-wqls0/jobs/reboutcx-p6-3-full-v1.json` → `sw1h01-wqls0/runs/reboutcx-p6-3-full-v1/`, manifeste `8B999C72DF9C3BD0F0CAF5DB8DB849BEEEBC3B52F26C028F3A414C73618E1D6D`. Couverture exacte : 11 BAM, 2 907 frames, 279 cycles/6 354 slots, 2 749 inférences uniques, 11 composants/4 029 872 octets. Erreur pondérée `0,02451`, pire p95 `0,31578` sur une frame de 48 pixels visibles ; inspection des principaux outliers : écarts localisés aux bords/petites armes, aucune rupture de silhouette observée.
- Les 12 frames CHMB1A1 et 12 WQLS0A1 des prototypes sont identiques octet pour octet dans les composants complets. Les deux `verify` relisent géométrie, centres, représentants, indices et cycles natifs : 31 + 21 fichiers vérifiés ; **17 tests OK**. Les deux exécutions CUDA/FP16 ont été annoncées avant lancement (`96,95 s` body + `98,55 s` arme de temps modèle), puis GPU libéré. Statut `completed-pending-human-review`, `installable=false` ; aucune installation, jeu, GUI, xBR/catalogue/release modifiés.
- Restent inconnus avant ingame : alpha/ombre/éclairage/effets réalisés, ordre effectivement capturé par BG2EE et jugement temporel humain sur toutes les actions. Étape suivante minimale : revue des GIF full body/arme ; accord distinct requis avant P7.1. L'essai ingame ne devient possible qu'après P7.1 puis installation P7.2 explicitement autorisée.

## P7 — Installation / QA Character

- **P7.1 — Catalogue offline.** `reboutcx_catalog.py::load_replacement/assemble_catalog/validate_diff` à adapter après prototype accepté : `0x6100` possède 65 appartenances dans la génération `65566299...`, contre l'exigence actuelle d'une seule. Remplacer un composant complet identifié par digest/resrefs ; préserver les autres appartenances de `0x6100` et les utilisateurs des composants partagés. Tester deux remplacements dans le même ID, resref ambigu refusé, équipement xBR inchangé ; ne pas aplatir les 65 composants.
- Nouveau catalogue épinglé : base xBR + sélection explicite de remplacements Character et créatures conservées ; aucun append dans le catalogue canonique. Réutiliser les composants ReboutCX scellés choisis, sans nouvelle inférence/repack du parent. Les décisions QA MBEH/Firkraag ne sont pas à refaire si leurs octets/contrats restent identiques.

**Résultat P7.1 — 2026-09-14 :**

- Sélection indexée par `(animation_id, old_component_index)` ; contrat parent = owner + digest physique/logique + shards + resrefs exacts. Un resref présent dans deux composants du même ID est refusé. Les hashes de code historiques sont conservés comme preuves scellées avec état de correspondance courant ; composants, géométrie/cycles et contrats restent revérifiés octet par octet.
- Job `sprite/catalogs/creature-x2-reboutcx/jobs/catalog-reboutcx-character-6100-test-v1.json` : parent xBR canonique `912AE8AE...`, pointeur `71DE2662...`, plus MBEH/Bodhi/Irenicus/Firkraag explicitement reconduits. Génération `AF3B86681AEE3FF9D0BDBC3E52CEC81ADBA9A60901430F45BAB70CAED094E148`, catalogue `EA923B4E3885093BEDC4E917527BB40FDA29BFFCD5CEF99AC82B8860AF1DEA4F`.
- `0x6100` reste à `65` appartenances : WQLS0 `66→436` (11 resrefs), CHMB1 `151→437` (23 resrefs), `63` appartenances xBR inchangées. Vérification globale : `6` remplacements/5 animations, `5 007` appartenances non ciblées préservées, `444` shards parent hardlinkés, `10` shards ReboutCX vérifiés ; inventaire resrefs, owners, métadonnées et round-trip catalogue exacts, pointeur xBR inchangé.
- Tests unitaires : deux composants d'un même ID, composant partagé, appartenance équipement non ciblée, cible dupliquée et resref ambigu ; `7` tests catalogue OK. Construction CPU uniquement, aucune inférence/GPU, installation, jeu, GUI, xBR canonique ou release modifiés.
- Ingame encore impossible : P7.2 doit installer transactionnellement cette génération après accord explicite et fermeture manuelle du jeu/InfinityLoader.

- **P7.2 — Installation/QA.** Réutiliser P4, `CreatureSpriteFilter=Nearest`, DLL/manifest de capacités réellement actifs vérifiés ; aucune nouvelle DLL si le runtime Character actuel suffit. Première invocation équipée : contrôler palettes capturées, composite HD effectif, attente des shards et temps de première frame avant de diagnostiquer le modèle.
- Préflight P7.2 : actif `65566299...`/`E43155A8...`, INI `Nearest`, DLL réellement active et acceptée `289E132B...` issue de `c1f55c78`. Le reçu catalogue conservait l'ancien runtime `50F7A4F9...` ; `Install-CreatureSprite-XN-Catalog-Test.ps1` accepte désormais l'adoption d'un runtime différent seulement avec `-RuntimeManifest` explicite et hash de la DLL active exact, sans copier la DLL. Manifeste `pipeline/runtime/manifests/iee-character-6100-firkraag-c1f55c78-v1.json` ; 17 tests transactionnels OK. `-VerifyOnly` réel : 454/454 shards sources, cible `AF3B8668...`/`EA923B4E...`, deux shards Character absents attendus (`298033FD...`, `F77CFEDA...`).
- Installation réelle autorisée : transaction `20260914T163442.1930540Z-e0ff51955ad44bfab7dc34db3f942dfe`, deux shards copiés, 454/454 sources et fichiers actifs revérifiés, statut `installed-pending-qa`. Catalogue précédent `E43155A8...`, INI `E5A737BE...` et reçu précédent `EF9DFDD1...` sauvegardés ; DLL inchangée, runtime adopté `iee-character-6100-firkraag-c1f55c78-v1`. Jeu non lancé par l'agent.
- Audit logs ingame `2026-09-14 18:39:39–18:41:40` : catalogue attendu `195/441/454`, hook Character installé, shard ReboutCX CHMB1 chargé et compositions `CHMB1G1/G11/G12/G17` effectives. Les `255` événements `owner=Character, subject=0x6100` utilisent `replacement=creature-sprite` ; aucune erreur/critique. Un composite incomplet a conservé le BAM natif une fois, puis reprise 27 ms après et `103` remplacements ultérieurs. `WQLS0` absent de la session ; `WQLS1/WQLJ6` xBR observés. Intégration body techniquement confirmée ; arme et verdict visuel encore ouverts.
- Audit arme cible `2026-09-14 18:58:38–18:59:14` : shards ReboutCX CHMB1 `450` et WQLS0 `449` chargés ; `WQLS0G1` et `CHMB1G18` composés en `1/2` puis `2/2`. Les `129` événements Character `0x6100` utilisent tous le remplacement, dont `100` clips réussis. Un repli natif transitoire a récupéré 32 ms plus tard ; aucune erreur Character/critique. Intégration body + arme techniquement confirmée ; verdict visuel humain encore ouvert.
- A/B réel : profil xBR `65566299...`/`E43155A8...`, shards CHMB1/WQLS0 `152/66`, puis retour ReboutCX `AF3B8668...`/`EA923B4E...`, shards `450/449`, 454/454 vérifiés. Verdict utilisateur : ReboutCX au moins aussi bon, préférence non tranchée, poursuite ReboutCX autorisée. Décision exacte : `sprite/index/qa-decisions/playable-characters/2026-09-14-accepted-noninferior-6100-chmb1-wqls0-reboutcx-x2-v1.json`.
- QA : body/arme, actions/directions, armures/couches incluses, ≥3 couleurs joueur, changement sans rebuild/réinstallation, save/load, ombre/halo/flicker/alignement, retour xBR. Anciens shards inertes autorisés ; contrôle du hash du catalogue actif dans les deux sens.
- Acceptation : décision QA immuable de portée exacte ; rejet : profil précédent vérifié. Retour xBR pur toujours disponible.

**Validation :** Character accepté ingame, recoloration/composition et A/B corrects.
**Hors périmètre :** extension, Recommended, choix menu/INI, hot-swap, release : demande distincte.

## P8 — Couverture ReboutCX complète de `0x6100`

- Portée autorisée : terminer les 65 appartenances de l'humain guerrier avant toute extension globale. Conserver xBR canonique et les composants CHMB1/WQLS0 scellés ; aucune modification des autres animations, installation ou release pendant la production offline.
- Orchestration bornée : `pipeline/scripts/reboutcx_character_family.py`, job `sprite/families/playable-characters/6100-human-male-fighter/family-runs/complete-reboutcx-p8-v1/jobs/human-male-fighter-complete-reboutcx-p8-v1.json`. Une famille source en mémoire à la fois ; production GPU future strictement sérielle.
- Audit CPU `audit.json`, SHA `276F1B3803B5E6F9EFFDE2935F3F231AF6616D26C20C2F283D2129113D061E00` : 65 composants = 4 body + 18 helmet + 12 shield + 31 weapon ; 656 ressources/180 337 frames, 28 850 marqueurs exacts, 142 540 inférences restantes après CHMB1/WQLS0. Transparence 0 et couverture des 256 indices par le contrat Character vérifiées ; 12 palettes BAM sources restent guides xBR, palette réalisée RANGES12 fixe pour ReboutCX.
- Les 65 composants xBR sont partagés avec d'autres animations : le catalogue final doit remplacer seulement `(0x6100, old_component_index)`. Estimation issue des deux runs validés : `86,7 min` de temps modèle restant, hors xBR/quantification/IO. Aucun GPU lancé à ce checkpoint.
- Stabilité Windows : les trois arbres `.BG2HD-Installer-Windows*.tmp/` (40 725 fichiers non suivis) déclenchaient les rescans Git de fond puis des crashs répétés de Git 2.54 en `0xc00000fd`. Exclusion durable commit `13717755` ; P8 lance un seul composant par processus, sortie enfant en fichier, zéro concurrence et libération RAM/VRAM entre composants.
- Suite P8 : `prepare` génère les 63 jobs/témoins ; `build` reprend et vérifie chaque run dans un processus séparé ; `catalog` produit puis vérifie le catalogue dérivé 65/65 sans installation. Annoncer le GPU avant `prepare` et `build`.

## 3. Vérifications / reprise

- Tests adaptés au risque : raster/formats P1–P2, catalogue P3, transactions P4, sémantique P6. Pas de C++ si runtime inchangé.
- `python pipeline/scripts/test_changed.py --targeted --path <fichier> --run` ; nouveau module non associé → test ciblé explicite ou association. Sélection vide ≠ validation.
- Code commun xBR modifié → fixtures de non-régression octets/contrats ; aucun rebuild des générations validées. `verify --full-verify`/build release global : finalisation explicitement demandée seulement.
- Reprise : résultat accepté + job/provenance + accord utilisateur. Retour : artefact, vérification, inconnue bloquante ; aucun journal supplémentaire.

Références externes ciblées : [CLI chaiNNer](https://github.com/chaiNNer-org/chaiNNer/wiki/05--CLI) (expérimentale, vérifier localement), [BAM V1](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/bam_v1.htm), [INI animations](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/ini_anim.htm), [false-color/opcode 7](https://gibberlings3.github.io/iesdp/opcodes/bgee.htm#op7).
