# Sprites x2 — reprise de production et extension hors Character

État vérifié le 2026-10-02. Référence opérationnelle ; recettes adaptables, pas une checklist universelle.
Documentation uniquement : aucune nouvelle production/installation/release demandée par cette mise à jour.

## Lire selon le besoin

| Besoin | Référence utile |
|---|---|
| Continuer le lot Character, commandes exécutables | [PALETTE_PLAYABLE.md](PALETTE_PLAYABLE.md) |
| Identifier une autre créature/PNJ, déterminer ce qui existe | §Périmètre et §Commencer un lot ci-dessous ; `sprite/index/*.csv` |
| Ne pas recalculer des frames communes | §Déduplication et cache |
| Comprendre les calculs I/F et le runtime | [PALETTE_Q3M_V6.md](PALETTE_Q3M_V6.md), `palette_frac_encode.py` |
| Assembler/installer et conserver le monde actuel | §Assemblage et §Installation |
| Raisonner sur palettes/effets/couches | [Guide définitif, §3/8/13](../sprite/Etudes_Sprite_codex_claude/GUIDE_DEFINITIF_SPRITES_HD_BG2EE.md) |
| Reprendre un ancien candidat ReboutCX/Q0 de monstre | `docs/REBOUTCX_PIPELINE_BG2_CODEX.md`, job/génération de la famille concernée |

## Résultat disponible et sources de vérité

| État | Autorité / constat |
|---|---|
| Source Character | `sprite/index/palette-work-plan.json` → `docs/measurements/playable-palettized-frame-dedup-20261001-v1/processing-plan.sqlite` ; SHA `06b32c785aa4b946a3836275925fea587322b57485163b76bbb79104bd313e25` |
| Production x2 | [current-generation.json](../docs/measurements/playable-q3m-x2-ingame-20261002-v1/current-generation.json) : 78 IDs, 4 510 BAM, catalogue V2 / feuilles V6 |
| Installation | [reçu actif](../docs/measurements/playable-q3m-x2-ingame-20261002-v1/ingame-installation/active-test.json), local/ignoré par Git ; monde BOX, scope `0x0` |
| Vérification | [verification.json](../docs/measurements/playable-q3m-x2-ingame-20261002-v1/verification.json) : 78/78 IDs, 4 510 ressources, 1 564 054 frames natives ; aucun manquant ; SHA des 4 510 fichiers installés contrôlés |
| QA | `sprite/index/qa-decisions/` ; acquis `6110`/P4 et UI P7 conservés ; le contrôle de couverture des 78 IDs ne vaut pas une QA visuelle exhaustive |
| Release | candidats puis `content.json` ; aucune intégration release issue de cette installation |

- Pack conservé : `sprite/.work/q3m-playable-all-x2-pack-20261002-v1/` ; SHA catalogue `C26C03DFB45913EF69A87B7A85A1E2CA795BEE79C03088F5A12F7D91240A61DD`.
- Répertoire `.work` **scellé et référencé** par la génération : ne pas le nettoyer comme un essai jetable. SQLite/cache/pack/binaires/sauvegardes locaux ; scripts/pointeurs/bilans/preuves versionnés.
- Lots encodés : [humains/demi-orcs](../docs/measurements/human-half-orc-q3m-x2-20261002-v1/README.md) (26 IDs), [nains/gnomes](../docs/measurements/dwarf-gnome-q3m-x2-20261002-v1/README.md) (24), [elfes/demi-elfes](../docs/measurements/elf-half-elf-q3m-x2-20261002-v1/README.md) (16), [halfelins](../docs/measurements/halfling-q3m-x2-20261002-v1/README.md) (12). Leurs nombres de tâches/BAM ne s'additionnent pas : intersections partagées.
- 13 677 041 occurrences de frames par modèle → 1 564 054 frames dans les BAM distincts → **563 969 tâches complètes uniques**, dont 563 797 susceptibles d'inférence et 172 spéciaux. Aucun de ces nombres ne représente le nombre de monstres restant à calculer.
- Paperdolls : 81 BAM / 163 frames `6110` déjà installés/acceptés, UI Nearest/Bitmap natif. Autres paperdolls, portraits, effets/VVC/projectiles hors de ce lot.

## Périmètre : un PNJ n'est pas un profil d'animation

Résoudre `CRE.animation_id` → `sprite_animations.csv.engine_section/runtime_profile` → `sprite_families.csv` → `sprite_resources.csv` ; ne pas choisir le pipeline d'après le nom, la race ou le dossier d'un PNJ.

| Animation utilisée | Situation / suite |
|---|---|
| `character`, types `5000`/`6000`, false_color=1 | 78 IDs déjà couverts, y compris LOW, demi-orcs et PNJ utilisant ces IDs. Réutiliser les routes existantes ; ni refaire le corps ni retraiter l'équipement commun. Un nouvel asset moddé est un périmètre source distinct. |
| `character_old`, anciens PNJ/animations | 8 IDs / 99 BAM / 4 725 frames dans l'index ; exclus du plan Character. Vérifier classes, palette, géométrie, owner/hook avant d'étendre. |
| `monster`, `monster_old` | Sources et candidats xBR/ReboutCX peuvent déjà exister ; cela ne prouve pas une production Q3m. Déterminer palette fixe ou false-color depuis l'INI et les réalisations natives du profil. |
| `monster_icewind` | Vérifier le contrat de palette par animation ; absence de `false_color` renseigné ≠ palette fixe démontrée. |
| `multi_new`, `monster_quadrant` | Retenir quadrants, orientations, superpositions, centres et durées ; dédupliquer les pixels sans fusionner les tables d'assemblage. |
| `monster_layered`, `monster_ankheg`, `monster_large`, `monster_large16`, `flying` | Présence dans l'index ≠ remplacement runtime supporté. Lire `runtime_supported`, `runtime_profile`, blockers et le hook réellement disponible. |
| `ambient`, `ambient_static`, `town_static` | Profils séparés ; sleeping humains/nains/elfes/halfelins restent ici lorsque l'index le dit. |

Pour le bilan quantitatif du stock indexé : union des resrefs, jamais somme des familles/IDs. Character = 1 564 054 frames ; monstres (`monster*` + `multi_new`, sans Character) = 689 139 ; flying = 243 ; autres = 10 082 ; total = 2 263 518. Character = 69,10 % des frames de cet inventaire, hors assets UI. Les alias entre sections sont retirés ; les images identiques entre BAM de monstres ne sont pas encore analysées globalement. Les anciens candidats de monstres ne sont pas comptés comme résultats Q3m.

## Recette Character acquise

| Élément | Contrat implémenté |
|---|---|
| Source | BAM V1 indexé natif complet ; pas d'export PNG comme source de production |
| Guide | xBR2X indexé avec provenance ; classes/alpha/transparence/ombre issus du natif. Pas de blend ; indices RGBA égaux distingués par provenance. |
| Cibles | ReboutCX x4 FP16, batch **fixed86**, canvas **q32**, sorties float32 ; BOX float32 x4→x2 **avant** encodage. x4 direct séparé. |
| Ajustement | Q3m K6 : `REF`, `DEFAULT`, `LATIN1`–`LATIN4`, poids égaux, recherche exhaustive OKLab au carré, départages I puis F. Palettes exactes épinglées dans le plan, pas reconstruites à l'intuition. |
| Sémantique | Profil `character-bg2ee-2.7.3.0`, 0..3 spéciaux ; 7 gammes×12 indices + 21 mélanges×8. F=0 aux spéciaux/terminaux ; aucune fuite de classe. |
| Résultat pixel | `guide`, `I`, `F`, `dep` u8 ; F=0..7 vers le successeur de même classe ; `dep` exact, 32 octets |
| Décodeur | `ramp-lerp-srgb8-v1`, IDs profil/règle=1 ; `RGB=(P[I]*(8-F)+P[succ(I)]*F+4)>>3`, alpha de P[I] ; palette vivante par couche |
| Stockage | V6, I puis F optionnel u8 (pas de packing 3 bits), compression XPRESS_HUFF par plan si plus petite ; aucun B/tramage/Q8c |
| Filtre | BOX monde x2 choisi par l'utilisateur ; minification BOX, magnification Nearest, pas de mipmaps ; UI séparée |

Implémentation : `palette_complete.PixelProcessor` (calculs), `palette_playable.SharedPixelProcessor` (identité/cache partagé), `reboutcx_batch_p12.infer_float_crops`, `reboutcx_multipal.inference_context`, `palette_frac_encode`, `palette_registry`.
Configuration : `config://chainner_python`, `config://reboutcx_model`, `config://mmpx_scalepix`, `config://bg2ee_game_root`. Les chemins locaux passent par `config/workspace-paths.local.json`/`workspace_paths.get_path` ; ne pas copier les chemins machine dans une nouvelle recette portable.

## Déduplication et cache

### Identité exacte

`analyze_playable_frame_dedup.identities` :

- `input_key = SHA256(domaine + width + height + transparent_index + indices row-major)`.
- `work_key = SHA256(autre domaine + input_key + couples(index,RGB) des indices effectivement utilisés)` ; RGB transparent inclus car le guide xBR reçoit ce RGBA.
- Dimensions natives + indices + transparence exacts ; zéro tolérance, recadrage, miroir, rotation ou remappage. Les couleurs des indices inutilisés n'invalident pas un partage.
- Centres, cycles, resref, sexe/race, équipement, consommateur : **hors clé pixel**, mais stockés par occurrence et restaurés à l'assemblage.
- Le quatrième octet de palette est ignoré dans **ce** contrat Character : alpha dérivé de l'indice. Ne pas étendre cette hypothèse à un nouveau profil avec alpha natif variable.

`WorkPlan` ouvre le SQLite en lecture seule, après SHA/taille/sources/profil ; tables `models`, `families`, `model_resources`, `resources`, `inputs`, `work_items`, `frames`, `cycles`, `profile_palettes`. Vues `processing_queue`, `frame_map`. Le nom d'un BAM ne prouve pas qu'une frame est identique ; même corps ne signifie pas mêmes boucliers/casques/armures.

### Réutilisation et reprise

- Cache Character x2 : `sprite/.work/palette-q3m-shared/x2/15e582a92931128f728d9532113ba86a8a5958361d2989caadb7fbcb6dd20ae2/work/encoded/<work_key>.npz`.
- Identité réelle = **namespace profil/recette/échelle + work_key**, jamais work_key seul. Namespace intègre fits, encodeur/noyaux, modèle/contexte d'inférence, guide/scalepix et règles x2/x4.
- NPZ présent ≠ hit valide : `ResultCache.load` contrôle recette, ZIP/tailles, noms des 4 membres, dtypes/shape, guide, classes/spéciaux, F et dépendances. Corruption = arrêt explicite, pas comptage silencieux ni écrasement d'un résultat historique.
- Producteur sous verrou OS exclusif ; hits n'initialisent pas le GPU. Transparences/placeholder 1×1 indice 2 passent sans inférence. NPZ complet publié atomiquement, six cibles encodées en flux ; ne pas conserver des dizaines de Go de cibles RGB sans besoin.
- Deux niveaux distincts : inputs indexés peuvent être communs alors que RGB natifs utilisés diffèrent ; les tâches finales diffèrent. Un cache séparé de cibles neurales est décrit par l'analyse, **pas implémenté** par ce producteur.
- Nouvelle sélection : lire le suivi/cache existants, classer `reused / new_model / new_special`, produire uniquement les clés manquantes. Reprendre une sélection interrompue sous recette identique ; bilan final historique terminé → nouvelle version, pas réécriture.
- Changement de noyau/hash, fits, modèle ou règle : le profil actuel est épinglé et `validate_sources` peut refuser la reprise. Ne pas modifier `recipe.json`, les hashes du plan ou renommer un namespace pour forcer un hit. Si les calculs sont démontrés identiques, prévoir une adoption contrôlée avec preuve native/provenance (modèle `seed_verified_run`), pas une copie aveugle.
- Reprise après migration machine : conserver SQLite + cache + génération scellée + sources `sprite/ressources/` et dépendances P1/P3. `analyze_playable_frame_dedup.GOLDEN` = `palette-q3m-p1-20260930-v1/decoder-golden.npz`, `ANCHOR` = `palette-q3m-p3-20261001-v5-full-x4-6110/recipe.json`, sous `6110/.../research/`. `PixelProcessor` utilise aussi `experiment.json`/`target-index.json` P1. Un clone Git seul n'apporte pas tous ces assets locaux ; restaurer les dépendances, puis contrôler le profil/configuration. Plan absent seulement → reconstruction CPU vers nouvelle version, pas relance GPU automatique.

### Étendre aux monstres sans refaire Character — travail à implémenter

1. Nouveau plan source CPU pour les familles hors `character`, avec leurs profils ; ne pas modifier le SQLite/pointeur Character acquis. Commencer par index/extractions existants, décoder seulement les sources manquantes au plan demandé.
2. Réutiliser les identités exactes et la correspondance consommateur→resref/frame/centre/cycle. Enregistrer doublons internes au lot, entre monstres et avec les 563 969 tâches Character existantes ; comparer les octets sur égalité de hash.
3. Pour chaque intersection, décider **compatibilité de profil/recette**, indépendamment de la ressemblance ou de la seule work_key. Mêmes classes/décodeur/fits/guide/alpha/inférence/échelle vérifiés → résultat partageable ; contrat différent → namespace distinct, pas d'adoption du NPZ Character.
4. Bilan CPU avant GPU : IDs/familles/BAM/frames, tâches uniques, hits compatibles, nouveaux GPU, spéciaux, incompatibilités/blockers, liste exacte des correspondances. Ce bilan est l'entrée de production ; ne pas annoncer les 689 139 frames de monstres comme 689 139 nouvelles inférences.
5. Producteur du profil retenu : consume la queue exhaustive, reprend les résultats valides, garde centres/cycles hors cache pixel. Ne pas contourner le registre en créant une boucle d'inférence indépendante par famille.

Ces points sont une spécification d'extension, pas une commande existante `--all-monsters` : `analyze_playable_frame_dedup.load_inventory`, `WorkPlan.validate_sources` et `palette_playable.plan/run/pack` sont limités aux 78 Character.

## Commencer un lot hors Character — opérations disponibles

Premier périmètre utile : un ID/famille représentatif du profil demandé. Un lot demandé peut ensuite partager la même analyse entre tous ses consommateurs.

```powershell
$spritePython = (Get-Content -LiteralPath config/workspace-paths.local.json -Raw | ConvertFrom-Json).paths.chainner_python
$spriteAnimation = '0x7F00' # Exemple existant ; remplacer par l'ID du lot demandé.
Import-Csv sprite/index/sprite_animations.csv | Where-Object animation_id -eq $spriteAnimation |
    Select-Object animation_id,ids_symbol,engine_section,runtime_profile,false_color,runtime_supported,blocker
Import-Csv sprite/index/sprite_families.csv | Where-Object animation_id -eq $spriteAnimation |
    Select-Object family_id,layer_kind,resource_count,frame_count,pipeline_ready,blocker
# Plan d'extraction natif uniquement ; aucun GPU ni écriture sans --run.
& $spritePython -B pipeline/scripts/extract_sprite_sources.py --animation-id $spriteAnimation --list
# Si sources réellement manquantes et extraction demandée : même commande avec --run.
```

- `sprite/index/extractions.csv` : source_file/canonical_file, SHA BAMC/BAM, état verified ; `sprite/ressources/` dédupliqué par resref. Ne pas régénérer l'inventaire global s'il répond déjà à la question.
- `runtime_supported` / `pipeline_ready` concernent le pipeline existant, **pas** l'admissibilité Q3m V6. Palette fixe non false-color : indices consécutifs arbitraires, pas des nuances Character ; ne pas appliquer les six fits ni `succ(i)=i+1` Character.
- Baseline palette fixe : voie existante ReboutCX + quantification Q0/indexée V5 avec classes explicites du job (`semantic_classes_for_job`). Vérifier son job/profil ; ce candidat n'est pas du Q3m. Pour un résultat fractionnel de monstre, définir un contrat palette et un encodeur/lecteur adaptés ; aucun mélange B/Q8c acquis ou demandé.
- Faux-color hors Character : vérifier gammes, successeurs, indices spéciaux/alpha et palette Realize ; si incompatibles, nouveau profil/règle et nouvelles identités. L'extension ne consiste pas à retirer un test d'owner.

## Runtime, capacités et extension nécessaire

- DLL installée compatible Character : [manifeste P7 full UI](runtime/manifests/iee-sprite-p7-full-ui-q3m-20261002-v1.json), SHA `9EB0E2B9A9BD727F2A2D346852BFE9750DA85A8F9885327538537DB02184EFD3`. Rebuild seulement si contrat/hook/capacité réellement modifié.
- `creature_sprite_x2.cpp` : owners catalogue `1=Character`, `2=MonsterIcewind`, `3=Monster`, `4=MonsterQuadrant`, `5=MultiNew` ; `catalog_owner_matches_animation` décide les IDs admissibles. Pas de nouveau support déduit du classement CSV.
- `palette_registry.write_catalog` impose owner Character ; lecteur natif `load_catalog_shard_for_request` contrôle **tous** les memberships du composant V6 : si un owner n'est pas Character, quarantaine/repli natif. Un composant V6 partagé Character/Monster est donc aujourd'hui interdit, même avec pixels identiques.
- Catalogue V2 : V6 seul ou composants homogènes V5/V6 ; V3+V6 rejeté. Pour préserver un ancien composant V3 dans un catalogue contenant V6, prévoir une conversion V5 contrôlée sous son contrat inchangé, pas une simple concaténation.
- Extension Q3m hors Character : producteur/plan général, encodeur sémantique adapté, identités profil/règle, lecteur/décodeur, owner/hook/réalisation palette, écrivain catalogue, manifeste de capacités et installateur. Selon le profil démontré, réutiliser les briques identiques ; ne jamais annoncer l'extension livrée sur la seule réussite du writer Python.
- Vérification ciblée si ces contrats changent : oracle décodeur indépendant, zéro fuite/spécial modifié, géométrie/cycles, palettes et dépendances, rejet de profil inconnu/corruption, hook/calques natifs. QA ingame sur le périmètre nouveau ; pas de répétition des validations Character inchangées.

Bornes actuellement implémentées (pas un budget GPU global) :

| Objet | x2 / catalogue |
|---|---|
| Feuille V6 | fichier ≤128 Mio, I décodé ≤128 Mio, I+F décodés ≤256 Mio |
| Frame décodée | I+F ≤128 Mio ; géométrie Character actuelle `w*h<65535`, transparent=0 ; offsets representatives u16 |
| Caches résidents | payload I/F 128 Mio, métadonnées catalogue 128 Mio ; lazy/éviction |
| Catalogue | ≤512 IDs, 16 384 composants, 16 384 shards, 262 144 memberships, 32 768 ressources, 4 194 304 frames, 1 048 576 routes, 128 Gio physiques |

Valeurs : `palette_registry.maximum_decoded_shard_bytes`, `WorkPlan.frame`, `creature_sprite_x2.h`. Une grande frame/quadrant peut exiger un autre découpage/contrat ; ne pas réduire les dimensions ou supprimer des frames pour passer une borne.

## Assemblage natif

- Aucun GPU si cache complet. Un BAM natif = frames complètes dans l'ordre, y compris inutilisées/placeholders ; SHA source canonique, cycles/slots, centres signés x1, dimensions/transparence, representatives de chaque source. Ne jamais réutiliser le centre du représentant de déduplication comme centre de chaque occurrence.
- Partager I/F/dep par tâche ; matérialiser chaque BAM distinct une fois ; partager sa feuille/composant entre consommateurs compatibles. Nom de feuille = SHA des octets ; routes `(animation_id,resref)` uniques et ordinal exact ; memberships/owner natifs conservés.
- Character : `palette_playable.py pack --scale 2 --output <dossier-neuf>` séquentiel. `--workers` de cette CLI concerne la production, **ne parallélise pas pack**.
- [assemble.py du lot complet](../docs/measurements/playable-q3m-x2-ingame-20261002-v1/assemble.py) : 8 processus CPU, SQLite/NPZ en lecture seule, verrou tenu par le parent ; sortie mutable non scellée uniquement. Reprend feuilles nommées SHA, vérifie contrat source/cycles de chaque feuille, ne publie `pack.json` et catalogue qu'à complétude.
- Cet assembleur est **Character x2**, pas un packer universel de monstres. `pack.json`/catalogue existant → relancement refusé. Pour nouveau profil, nouvel assembleur ou adaptation versionnée, pas modification du run acquis.
- Contenu provisoire : `resource-*`, `parallel-*`, `.part` ne sont pas des feuilles cataloguées ; n'installer que les noms présents dans le catalogue scellé.
- Extension de catalogue : conserver le parent scellé et ses routes hors lot, ajouter/remplacer seulement les memberships demandés ; recalculer indices de composants/shards/routes et digests, vérifier les anciennes routes par identité de feuilles/ordinals. `build_catalog_delta` illustre l'ajout d'IDs disjoints ; `palette_p3_catalog.derive` est limité au parent V5/P3 et `6110`, donc **pas directement utilisable** pour le catalogue actuel des 78 IDs ou un nouveau monstre.

## Installation, vérification, restauration

- [install.ps1 du lot complet](../docs/measurements/playable-q3m-x2-ingame-20261002-v1/install.ps1) et [verify.py](../docs/measurements/playable-q3m-x2-ingame-20261002-v1/verify.py) : scripts **scopés au run du 2026-10-02**, 78 IDs/4 510 ressources/SHA et baseline 2 IDs codés ; conserver comme recette, pas les relancer pour un monstre.
- Baseline de ce run avant copie = uniquement `6100`, `6110`. Le remplacement autonome était justifié car le nouveau pack contenait les deux. **Le catalogue actif contient maintenant 78 IDs** : un catalogue monstre autonome les retirerait. Par défaut, produire une extension conservant ces 78 routes ; catalogue isolé seulement pour un essai demandé explicitement, avec restauration.
- Au remplacement : jeu et InfinityLoader fermés ; snapshot catalogue/INI/DLL/capacités, fichiers UI/shaders concernés ; copies sources/SHA vérifiés et atomiques, feuilles partagées présentes authentifiées ; vérifier baseline inchangée avant publication ; sauvegarder catalogue/INI, publier le catalogue après ses feuilles ; contrôler configuration et hashes copiés.
- Filtre actuel monde : `EnableCreatureSpriteUpscaleTest=true`, `EnableCreatureSpriteX2Test=false`, `EnableCreatureSpriteLinearFiltering=false`, `CreatureSpriteFilter=Box`, `CreatureSpriteFilterAnimation=0x0`. Scope 0 = toutes routes HD du catalogue, pas seulement Character ; toute nouvelle route HD ajoutée héritera de BOX sauf changement de périmètre choisi. Paperdolls Nearest séparés.
- Installateur catalogue générique `Install-CreatureSprite-XN-Catalog-Test.ps1` : format job/pointeur/manifeste différent et BOX hardcodé `0x6110` ; l'employer sans adaptation **ne reproduit pas** cette installation BOX globale. Réutiliser `ThinInstall.ps1` (`Assert-GameClosed`, `Copy-FileAtomic`, `Set-IniValue`, chemins confinés) ou adapter un installateur versionné au nouveau scope/capacités.
- Contrôle « aucun manquant » : set exact des IDs, owner/memberships, set resrefs attendu par ID, frames/cycles/centres complets, ordinals, feuilles présentes/taille/SHA, source/contrat et absence de collision non prévue. Copier seulement un corps sans armes/casques/boucliers ne couvre pas une animation Character.
- Conservation : 81 ressources UI P7, DLL/shaders si inchangés ; ni inférer une nouvelle QA de ces fichiers ni réécrire leurs preuves. Sauvegardes hors Git ; reçu actif local ; preuve finale de couverture versionnée.
- Si échec de publication : restauration catalogue/INI ; feuilles SHA ajoutées sans référence peuvent rester, jamais effacer un fichier partagé avec un autre pack. Si seuls les fichiers installés manquent, restaurer depuis la génération scellée ; ne pas relancer le GPU.

Restauration du **seul run complet Character actuel**, si demandée : `work/before/{InfinityEngine-Enhancer.ini,CreatureSprites-XN.catalog}` sous `docs/measurements/playable-q3m-x2-ingame-20261002-v1/`. Contrôler leurs SHA contre `baseline.json`, l'identité du jeu/reçu actif et l'absence de changement utilisateur depuis ce reçu ; fermer jeu/InfinityLoader ; restaurer ces deux fichiers avec `ThinInstall.Copy-FileAtomic`, vérifier les SHA restaurés, écrire un nouveau constat de restauration (preuves finales inchangées). Ne pas employer `Restore-CatalogInstallTransactionV2` directement : ce reçu scoped utilise un autre schéma. Pour le prochain lot, prévoir installateur et restauration pour son propre schéma plutôt qu'une seconde procédure manuelle non vérifiée.

## Prochaine unité de travail hors jouables

Demande de production d'un profil → résoudre ID/famille/PNJ et réutiliser ses sources/extractions → bilan CPU de partage avec Character et autres consommateurs → déterminer contrat palette/owner supporté → implémenter seulement l'extension nécessaire si Q3m indisponible → produire les tâches manquantes → assembler le lot → installer une extension conservant les 78 Character si demandé → vérification structurelle et QA visuelle de ce lot.

Ne pas confondre « documentation prête pour commencer l'extension » et « producteur/lecteur Q3m de tous les monstres déjà livré ». Aucune nouvelle QA, aucun calcul GPU, aucune finalisation release déclenchés par ce guide.
