# Inventaire normalisé des sprites BG2EE — contrat agent

Utiliser cet index comme source de vérité pour toute identité de sprite, famille BAM, variante
Character, équipement et diagnostic automatisable du pipeline x2/x4. Ne pas remplacer ces relations
par une déduction depuis un nom de PNJ ou un dossier historique.

Le scanner sépare les ressources présentes de leur compatibilité avec le pipeline actuel. Il lit
les ressources stock depuis `chitin.key` et les BIF ; il ne lit dans `override` que les noms de
fichiers nécessaires au signalement des collisions et n'écrit jamais dans le jeu.

## Régénération

Régénérer depuis la racine du dépôt après changement du jeu, du schéma, des règles de résolution,
des suffixes acceptés, du remappage palette ou des limites runtime :

```powershell
python pipeline/scripts/build_sprite_inventory.py
```

Le test ciblé `python -m unittest pipeline.tests.test_sprite_inventory` sert après modification du
scanner, de son schéma ou de ses règles. Une simple régénération d'inventaire ne l'impose pas.

La provenance exacte de l'installation analysée, ses hashes, les limites appliquées, l'usage des
animations par les CRE stock, les totaux et les projections déterministes de registry-set x2/x4 sont dans
[`manifest.json`](manifest.json).

Lire `manifest.json` pour toute décision courante. Un document peut conserver un instantané daté de
benchmark ou de capacité s'il le marque `non canonique` et fournit sa commande de reproduction ; il
ne doit jamais utiliser cet instantané comme gate opérationnel.

## Tables

- [`q3m-work-tracking.json`](q3m-work-tracking.json) et [`q3m-work-items.csv`](q3m-work-items.csv) : nouvelle queue Q3m de tous les profils personnages/créatures ; xBR/ReboutCX historiques exclus des compteurs. Inventaire des 15 familles, règles couleur et estimation moteur : [`../SUIVI_Q3M.md`](../SUIVI_Q3M.md). Suivi de travail uniquement ; production, QA, installation et release gardent leurs autorités indépendantes.
- Mémoire du chat 2026-10-03/04 : [`../SUIVI_Q3M.md`](../SUIVI_Q3M.md#mémoire-du-chat--décisions--preuves) ; trois familles complètes, deux validées (Flying, Ankheg SDF stable). **Character CHFB1 SDF V10 en stock, non installé** : [décision](../../docs/measurements/q3m-6110-chfb1-sdf-ingame-x2-20261004-v1/stock-decision.json), [restauration vérifiée du runtime Ankheg accepté](../../docs/measurements/q3m-6110-chfb1-sdf-ingame-x2-20261004-v1/restoration-verification.json). Queue `stocked_contour_solutions` distincte des essais actifs ; aucune validation/release implicite.
- [`q3m-source-work-plan.json`](q3m-source-work-plan.json) : analyse exacte des 14 profils hors Character, reliée au plan Character acquis ; doublons entre BAM/IDs et intersections vérifiées par octets. [Résultat et lecture de la queue unique](../../docs/measurements/all-creature-source-dedup-20261003-v1/README.md). Source identique ne prouve pas la compatibilité d'un résultat Q3m entre profils.
- [`family-groups.csv`](family-groups.csv) : autorité manuelle de classement des
  `engine_section`; macro-groupe, dossier, layout et règle de bucket.
- `extractions.csv` : projection générée des BAM réellement présents sous
  `sprite/ressources/`; ne pas l'éditer. Elle reste absente avant la première extraction explicite.
- [`palette-work-plan.json`](palette-work-plan.json) : pointeur source SHA vers le plan exhaustif
  de frames Q3m uniques ; entrée `pipeline/scripts/palette_playable.py`. Le SQLite local peut être
  reconstruit sur CPU ; sources, géométrie et palettes restent régies par les CSV. Contrat et
  commandes : [`../../pipeline/PALETTE_PLAYABLE.md`](../../pipeline/PALETTE_PLAYABLE.md).
- Processus complet Q3m x2 et reprise hors Character (monstres/PNJ, compatibilité des doublons, cache, owner/runtime, installation conservant les 78 IDs) : [`../../pipeline/SPRITES_PRODUCTION_Q3M_X2.md`](../../pipeline/SPRITES_PRODUCTION_Q3M_X2.md). La présence dans ces CSV n'implique pas un profil Q3m V6 disponible.
- [`qa-decisions/`](qa-decisions/) : décisions ingame immuables.
- Production : pointeur `current-generation.json` et manifeste scellé du catalogue.
- Installation : `ingame-installation/active-test.json`, sans autorité QA.
- Q3m x2 complet, 78 `Character` (2026-10-02) : [production](../../docs/measurements/playable-q3m-x2-ingame-20261002-v1/current-generation.json), [reçu de l'installation initiale BOX](../../docs/measurements/playable-q3m-x2-ingame-20261002-v1/ingame-installation/active-test.json), [couverture vérifiée, aucun manquant](../../docs/measurements/playable-q3m-x2-ingame-20261002-v1/verification.json). QA visuelle de ce catalogue complet encore distincte ; filtre global courant CatmullRom, contrats QA historiques conservés.
- Diagnostics couleur, six frames Spectateur/Bodhi/golem (2026-10-03) : [cinq essais archivés, PNG et mesures](../../docs/measurements/q3m4partners-colour-comparison-x4-20261003-v1/README.md) — ancien x2, Q3m x2/x4, SeedVR 7B, 16 niveaux et quatre partenaires. Hors production/QA/installation/release ; variantes expérimentales incompatibles V6.
- Release : `releases/BG2-HD-Upscale/manifests/sprite-release-candidates.json`, puis `content.json`.

Ces quatre états sont indépendants. Aucun registre global ne les fusionne ni ne les réconcilie.

- [`sprite_animations.csv`](sprite_animations.csv) : une ligne par ID de l'union `ANIMATE.IDS` et
  des INI numériques. Elle conserve le symbole, la classe moteur, toutes les clés qui pilotent les
  variantes Character ou Monster et le profil runtime actuellement disponible. Les colonnes
  fréquentes sont exposées directement ; `ini_sections_json` conserve sans perte toutes les autres
  clés propres aux classes moteur (sons, quadrants, armes superposées, etc.).
- [`sprite_families.csv`](sprite_families.csv) : une ligne par couple animation/calque/préfixe BAM.
  Pour Character, les corps sont déclinés par code d'armure et les équipements par type et code
  d'animation ITM. Cette table porte la décision `pipeline_ready` et ses motifs détaillés.
- [`sprite_resources.csv`](sprite_resources.csv) : une ligne par BAM relié à une famille. Le BAM est
  réellement décodé pour mesurer cadres, cycles, dimensions, centres, pixels, coût exact estimé du
  registre V2 x2, plus grosse frame native et doublons d'indices RGBA effectivement utilisés dans
  une même frame. Le champ de
  coût conserve volontairement sa sémantique x2 ; le manifeste fournit la formule de projection x4
  sans créer les pixels et décrit les limites du registre-set.
- [`sprite_items.csv`](sprite_items.csv) : une ligne par ITM stock. Elle relie type `ITEMCAT.IDS`,
  code d'animation, calque visuel, préfixes Character candidats, familles résolues et familles
  actuellement traitables.
- [`manifest.json`](manifest.json), bloc `stock_cre_usage` : usage des animations par toutes les
  ressources CRE du KEY/BIF stock. Le scanner lit le type `0x03F1`, vérifie la signature/version CRE
  et extrait l'ID `u16-le` à l'offset `0x28`. Les listes `fully_pipeline_ready_*`,
  `runtime_supported_without_bam_*`, `runtime_supported_blocked_*` et `runtime_unsupported_*` sont
  générées depuis les mêmes tables et règles que les CSV. Les champs `nonzero_*` excluent la valeur
  spéciale `0x0000` sans masquer le nombre de CRE qui l'utilisent. Les blocs `with_bam_*` et
  `without_bam_*` empêchent de confondre un ID référencé par un CRE avec une animation possédant des
  assets stock.

Les relations utilisent `animation_id`, `family_id`, `bam_resref` et `item_resref`. Les listes dans
une cellule sont séparées par `;` ; le fichier CSV lui-même reste séparé par des virgules et encodé
en UTF-8 avec BOM.

## Lecture des diagnostics

Interpréter `runtime_supported=yes` comme la capacité du hook moteur à reconnaître cette classe
d'animation (`Character 0x5000/0x6000` ou `MonsterIcewind 0xE000`).
`pipeline_ready=yes` exige en plus : ressources présentes et décodables, suffixes acceptés,
provenance d'indice palette vérifiable, aucune collision `override`, et respect des limites de 128 ressources,
4 096 frames par BAM et 128 Mio par registre x2. Le format xN applique un plafond centralisé
équivalent de 512 Mio en x4 afin de conserver la même capacité logique malgré le coût pixel ×4.
Plusieurs shards V3 peuvent appartenir à un même
`CreatureSprites-XN.set` ; ses plafonds, son ordre de priorité et sa politique fail-closed sont dans
`manifest.json`. Une projection n'est valide que si sa plus grosse frame upscalée tient aussi dans
le cache lazy borné à 128 Mio.

Les principales valeurs de `blocker` sont :

- `runtime-profile-unsupported` : assets inventoriés, mais classe moteur non branchée ;
- `no-bam-resources` : INI connu mais ressources absentes de cette installation ;
- `missing-required-suffixes` ou `unexpected-character-suffixes` : contrat Character incomplet ;
- `resource-limit`, `per-resource-frame-limit` ou `registry-size-limit` : limite de registre ;
- `*-override-collision` : une ressource de même identité existe dans `override`.

`duplicate_used_rgba_frames` et ses exemples restent des diagnostics. xBR propage la provenance
d'indice ; ReboutCX quantifie dans la classe sémantique du guide xBR. Des indices de même RGB mais
de classes différentes ne sont jamais fusionnés.

Ne jamais traduire `pipeline_ready=yes` en validation ingame ni en profil ReboutCX démontré. Cette
valeur couvre uniquement les prérequis automatisables communs. Utiliser ensuite le mode adapté dans
[`../PROCESSING.md`](../PROCESSING.md) et [`../FAMILY_APPEND.md`](../FAMILY_APPEND.md).

## Extraction

Planifier sans écrire ; une portée est obligatoire :

```powershell
python pipeline/scripts/extract_sprite_sources.py --macro-group monsters
python pipeline/scripts/extract_sprite_sources.py --family-id '<family_id>' --list
python pipeline/scripts/extract_sprite_sources.py --animation-id 0xFFFF
```

`extract_sprite_sources.py --run` extrait uniquement les BAM natifs/canoniques. Il ne crée aucune
frame PNG, aucun run de production, aucune installation et aucune décision QA. Ne pas utiliser
`--all-ready --run` sans décision explicite sur cette portée globale.

Après création d'un job, raccorder ses sources au runner :

```powershell
python pipeline/scripts/materialize_sprite_sources.py --job <job-ou-agregat>
python pipeline/scripts/materialize_sprite_sources.py --job <job-ou-agregat> --run
```

La première commande est en lecture seule. `--run` exige toutes les sources centrales, crée un
manifeste par job feuille et des liens physiques sous son `source/`, puis vérifie les octets contre
le jeu courant. Aucun PNG, upscale, build, installation ou état QA n'est produit.

## Requêtes de décision

```powershell
$a = Import-Csv sprite/index/sprite_animations.csv
$f = Import-Csv sprite/index/sprite_families.csv
$r = Import-Csv sprite/index/sprite_resources.csv
$i = Import-Csv sprite/index/sprite_items.csv

$a | Where-Object animation_id -eq '0xFFFF'
$f | Where-Object animation_id -eq '0xFFFF'
$f | ForEach-Object { $_.blocker -split ';' } | Where-Object { $_ } |
  Group-Object | Sort-Object Count -Descending
$r | Where-Object blocker -ne ''
$i | Where-Object item_resref -eq 'ITEMREF'

$m = Get-Content sprite/index/manifest.json -Raw | ConvertFrom-Json
$m.stock_cre_usage | Select-Object cre_resource_count, animation_id_count, `
  with_bam_animation_id_count, without_bam_animation_id_count, `
  without_bam_nonzero_animation_id_count, `
  fully_pipeline_ready_animation_id_count, fully_pipeline_ready_cre_resource_count, `
  fully_pipeline_ready_cre_coverage_percent, runtime_supported_without_bam_animation_id_count, `
  runtime_supported_blocked_animation_id_count, runtime_unsupported_animation_id_count, `
  runtime_unsupported_nonzero_animation_id_count
```

## Large16 Q3m x2 sans SDF — 2026-10-04

- `q3m-work-tracking.json`, `../SUIVI_Q3M.md` : quatrième famille disponible complète installée, dix IDs complets ; QA acquises toujours deux familles/six IDs.
- `../../docs/measurements/q3m-monster-large16-full-x2-20261004-v1/README.md` : trois IDs, deux modèles/trois palettes, scope natif 12 BAM monde + INV auxiliaire ; vingt feuilles / 1 692 frames. Les 25 BAM de l'inventaire par préfixe restent une donnée source, douze quadrants hors appels Large16. A201/A202 explicitement sans source.
- Production/installation prouvées séparément ; QA ingame en attente ; Character SDF en stock, Ankheg stable conservé.

- 2026-10-04 : **V7 sans SDF validé ingame**, utilisateur « c'est propre ! » ; QA immuable `sprite/index/qa-decisions/monster_large16/2026-10-04-accepted-full-available-large16-q3m-v7-x2-catmullrom-v1.json`. Trois familles/neuf IDs acceptés. Les mentions en attente ci-dessus décrivent la remise initiale ; futur SDF = autre variante, QA distincte.

- Large16 essai SDF historique retiré : `../../docs/measurements/q3m-large16-sdf-ingame-x2-20261004-v1/README.md`, dix-huit feuilles monde/1 688frames, rejeté : contour trop lisse. **V7 sans SDF accepté et réinstallé** ; CSV décrit cet acquis V7, essai dans `historical_contour_trials`, restauration `restoration-verification.json` du run SDF.

- Ambient_static **complet installé et accepté ingame**, 13 IDs/13 modèles/26 BAM/1 144 frames, Q3m V7 x2 amélioré sans SDF +cheval œil v3 : [QA exacte des feuilles et du runtime](qa-decisions/ambient_static/2026-10-04-accepted-full-ambient-static-horse-eye-v3-q3m-v7-x2-catmullrom-v1.json), [production initiale](../../docs/measurements/q3m-ambient-static-full-x2-20261004-v1/current-generation.json) **avec [remplacement cheval requis](../../docs/measurements/q3m-horse-eye-ingame-x2-20261004-v1/current-generation.json)**. Cinq familles/23 IDs installés, quatre familles/22 IDs acceptés ; Ogre QA en attente. Prochain lot [town_static proposé, non produit](../../docs/measurements/q3m-town-static-selection-x2-20261004-v1/README.md).

- Town_static **complet disponible produit et installé**, 18 IDs/modèles/BAM, 1 543 frames, Q3m V7 K6 x2 amélioré sans SDF ; [production et installation](../../docs/measurements/q3m-town-static-full-x2-20261004-v1/README.md), [18 CLUA](../../docs/measurements/q3m-town-static-full-x2-20261004-v1/CLUA-generiques.txt), QA ingame en attente. Huit hits/1 534 encodages nouveaux, six familles/41 IDs installés ; quatre familles/22 IDs acceptés conservés. Les mentions « proposé » ci-dessus décrivent la sélection antérieure.

- Town_static **famille complète disponible acceptée ingame**, [QA exacte](qa-decisions/town_static/2026-10-04-accepted-full-available-town-static-q3m-v7-x2-catmullrom-v1.json), 18 IDs/18 BAM/1 543 frames ; preuves d'installation antérieures conservées. Six familles/41 IDs installés, cinq familles/40 IDs acceptés ; Ogre QA en attente. Nouveau lot [ambient proposé, non traité](../../docs/measurements/q3m-ambient-selection-x2-20261004-v1/README.md), 18 IDs/16 modèles/34 BAM ; 1 382 encodages nouveaux après cache/déduplication.

- Ambient **famille disponible complète produite et installée**, 18 IDs/16 modèles/34 BAM/2 580 frames physiques, Q3m V7 K6 x2 amélioré sans SDF ; [production/installation](../../docs/measurements/q3m-ambient-full-x2-20261004-v1/README.md), [18 CLUA](../../docs/measurements/q3m-ambient-full-x2-20261004-v1/CLUA-generiques.txt). Chauve-souris/rat intérieur et extérieur partagés ; 1 024 hits acquis, 1 382 nouveaux travaux dont une frame spéciale. Sept familles/59 IDs installés ; QA ingame en attente, cinq familles/40 IDs acceptés conservés.

- Ambient **famille complète disponible acceptée ingame**, [QA exacte](qa-decisions/ambient/2026-10-04-accepted-full-available-ambient-q3m-v7-x2-catmullrom-v1.json), 18 IDs/16 modèles/34 BAM/2 580 frames physiques ; sept familles/59 IDs installés, six familles/58 IDs acceptés. Nouveau lot [Character_old proposé, non traité](../../docs/measurements/q3m-character-old-selection-x2-20261004-v1/README.md) : sept IDs/six ensembles/99 BAM, 3 483 travaux nouveaux après cache/déduplication ; XHFF absent, MDGU transparent natif.

- Character_old **famille disponible complète produite et installée**, sept IDs/six ensembles/99 BAM/4 725 frames, Q3m V7 K6 x2 amélioré sans SDF ; [production/installation](../../docs/measurements/q3m-character-old-full-x2-20261004-v1/README.md), [sept CLUA](../../docs/measurements/q3m-character-old-full-x2-20261004-v1/CLUA-generiques.txt). Drizzt/Elminster/moine/squelette/Sarevok et deux gardes partageant un corps natif transparent ; XHFF sans BAM exclu. Huit familles/66 IDs installés ; QA ingame en attente, six familles/58 IDs acceptés conservés.

- Character_old : [correction du fallback vanilla](../../docs/measurements/q3m-character-old-runtime-fix-x2-20261004-v1/README.md), ombres/équipements natifs Q3m V7 x2 ajoutés ; référence courante `docs/measurements/q3m-character-old-runtime-fix-x2-20261004-v1/current-generation.json`. Corps conservés ; QA ingame en attente.

- Override SDF **6405/6406 seulement** : [run](../../docs/measurements/q3m-doom-guard-sdf-ingame-x2-20261004-v1/README.md), 974 BAM partagés, CSHD ajouté ; corps natifs transparents conservés. Cinq autres Character_old restent V7 sans SDF ; QA ingame en attente.

- Character_old complet **accepté ingame**, sept IDs, Q3m V7 sans SDF6400–6404 +V9 SDF6405/6406 : [QA/décision](../../docs/measurements/q3m-character-old-accepted-x2-20261004-v1/README.md). 1 066 BAM natifs/2 018 feuilles variantes ; XHFF6621 absent.

- Monster_layered **complet produit/installé, QA ingame en attente** : [run](../../docs/measurements/q3m-monster-layered-full-x2-20261004-v1/README.md), [sept CLUA](../../docs/measurements/q3m-monster-layered-full-x2-20261004-v1/CLUA.txt). Sept modèles, 65 BAM/6 422 frames Q3m V7 x2 palette améliorée sans SDF ; 65 feuilles ajoutées au catalogue, dont quatre Volo identiques au pilote local acquis. Sirine MSIRG2BE orphelin exclu ; hook type2000 ajouté, type8000 déjà couvert. Neuf familles/73 IDs complets installés, sept familles/65 IDs acceptés inchangés.

- Monster_layered complet **validé ingame**, sept modèles/65 BAM/6 422 frames Q3m V7 x2 palette améliorée/CatmullRom sans SDF : [QA/décision](../../docs/measurements/q3m-monster-layered-accepted-x2-20261004-v1/README.md). Volo visible : `SARVOLO`; fixture QLYR2100 masquée nativement, à éviter. Huit familles/72 IDs acceptés ; neuf familles/73 IDs installés.

- Monster_quadrant complet disponible **produit/installé, QA ingame en attente** : [run/sept CLUA](../../docs/measurements/q3m-monster-quadrant-full-x2-20261004-v1/README.md), deux modèles/sept palettes natives, 36 BAM/132 feuilles/12 928 frames Q3m V7 x2 amélioré sans SDF. MWDR1101/1105 absents ;65 déclarations0×0 préservées. Dix familles/80 IDs installés ; huit familles/72 IDs acceptés.

- Monster_quadrant : [raccords contextuels Q3m installés, état avant validation](../../docs/measurements/q3m-monster-quadrant-seam-fixed-x2-20261004-v1/README.md), sept palettes ;bandes4px natifs, aucune modification hors bandes, DLL/CLUA acquis conservés.

- Monster_quadrant complet **validé ingame**, deux modèles/sept palettes, 132 feuilles/12 928 frames Q3m V7 x2 contextuel amélioré/CatmullRom sans SDF : [QA/décision](../../docs/measurements/q3m-monster-quadrant-accepted-x2-20261004-v1/README.md). Dix familles/80 IDs installés ; neuf familles/79 IDs acceptés.
- Gros sprites divisés spatialement : [pipeline contextuel systématique](../../pipeline/SPRITES_Q3M_MULTIPART.md), intégré au producteur `q3m_family_witnesses.py` (plan/run/pack).

- Monster_old **complet disponible installé, QA en attente** : [run](../../docs/measurements/q3m-monster-old-full-x2-20261004-v1/README.md), [46 CLUA neutres](../../docs/measurements/q3m-monster-old-full-x2-20261004-v1/CLUA.txt). 18 modèles/46 palettes natives,79 BAM/217 feuilles/17 752 frames physiques (218 liaisons/17 754 frames liées) Q3m V7 K6 x2 amélioré sans SDF ;huit IDs7D01–7D08 absents. Onze familles/126 IDs installés ;neuf familles/79 IDs acceptés conservés.

- MultiNew complet installé, QA en attente : [run](../../docs/measurements/q3m-multi-new-full-x2-20261005-v1/README.md), [10 CLUA](../../docs/measurements/q3m-multi-new-full-x2-20261005-v1/CLUA.txt). Quatre modèles/10 IDs, 30 palettes par banque, contextes natifs quatre/neuf parties ; douze familles/136 IDs installés, neuf familles/79 IDs acceptés conservés.
- Runtime MultiNew corrigé : [stabilité des chargements](../../docs/measurements/q3m-multi-new-frame-stability-20261005-v1/README.md), nouveau `current-generation.json`/reçu actif référencés par le suivi ; mêmes sprites x2, zéro repli temporaire sur 580 groupes natifs, QA ingame en attente.
