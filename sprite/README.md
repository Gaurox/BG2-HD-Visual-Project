# Sprites complexes — point d'entrée

> **Règle documentaire : écrire pour des agents IA — concis, factuel, opérationnel, non narratif. Éviter la verbosité et les répétitions. Toute nouvelle documentation ou modification doit privilégier la densité d’information, les listes/tableaux, les chemins et commandes précises. Éviter la prose longue, le contexte narratif, les répétitions et les explications principalement destinées à un lecteur humain.**

Ce domaine couvre les créatures et Characters composés (corps, arme, bouclier/offhand, casque et
palettes). Il ne dépend pas du pipeline maps.

## Sources de vérité

1. [`index/README.md`](index/README.md) : schema et requêtes.
2. `index/manifest.json` : snapshot du jeu et de l'inventaire.
3. `index/family-groups.csv` : macro-groupes et règles de rangement des familles.
4. `index/sprite-layout.json` : matérialisations physiques existantes ;
   `index/path-migrations.json` : anciens chemins d'artefacts immuables.
5. Les quatre CSV d'inventaire : animations, familles, ressources et items.
6. Production : `current-generation.json` et son `build-manifest.json`.
7. QA : décisions immuables sous `index/qa-decisions/`.
8. Installation : `ingame-installation/active-test.json`, sans autorité sur la QA.
9. Release : `releases/BG2-HD-Upscale/manifests/sprite-release-candidates.json` ; `approved` sélectionne,
   seul `content.json` prouve `integrated`.

`index/extractions.csv` est une projection des sources effectivement matérialisées. Son absence
signifie qu'aucune extraction centralisée n'a encore été exécutée.

`pipeline_ready=yes` prouve seulement les prérequis automatisés. Ce n'est ni un build, ni une
installation, ni une validation ingame.

## Méthode actuelle

Voie quotidienne : [`../docs/PRODUCTION_RAPIDE.md`](../docs/PRODUCTION_RAPIDE.md). Les documents
ci-dessous sont des recettes conditionnelles, pas une chaîne universelle.

Runbook opérationnel : [`PROCESSING.md`](PROCESSING.md). Publication catalogue, installation et QA :
[`FAMILY_APPEND.md`](FAMILY_APPEND.md). Spécificités ReboutCX :
[`../docs/REBOUTCX_PIPELINE_BG2_CODEX.md`](../docs/REBOUTCX_PIPELINE_BG2_CODEX.md).

| Mode raster | Rôle |
|---|---|
| xBR | base canonique déterministe ; ajoute les nouvelles familles/animations |
| ReboutCX | remplacements explicites dans un catalogue dérivé de xBR |

Un catalogue ReboutCX reste complet : composants ciblés en ReboutCX, tous les autres en xBR. Les
deux modes produisent les mêmes contrats runtime x2 ; aucun choix par créature ou hot-swap ingame.

```text
index normalisé
  → sélectionner une portée et des familles éligibles
  → planifier l'extraction native par portée explicite
  → extraire chaque BAM une fois dans ressources/<RESREF>/sources/<sha>/
  → générer les jobs
  → matérialiser source/ par liens physiques vers ressources/
  → produire xBR ou ReboutCX
  → publier le catalogue xBR canonique ou le dérivé ReboutCX
  → installer/restaurer transactionnellement
  → QA NEAREST
```

Conditions avant production : `runtime_supported=yes`, `pipeline_ready=yes`, `blocker` vide et
`override_collision` vide.

- Runners : `pipeline/scripts/run_creature_sprite_x2.py` (xBR),
  `pipeline/scripts/reboutcx_full.py` (ReboutCX).
- Inventaire : `pipeline/scripts/build_sprite_inventory.py`.
- Extraction native dédupliquée : `pipeline/scripts/extract_sprite_sources.py` ; plan-only sans
  `--run`, aucun décodage PNG ni upscale.
- Adaptateur de sources runner : `pipeline/scripts/materialize_sprite_sources.py` ; plan-only sans
  `--run`, puis manifeste local et liens physiques sans copie de BAM.
- Rangement : `pipeline/scripts/sprite_layout.py` + `index/family-groups.csv`.
- Génération Character : `pipeline/scripts/generate_character_complete_x2_jobs.py`.
- Traitement : [`PROCESSING.md`](PROCESSING.md) ; ajout catalogue :
  [`FAMILY_APPEND.md`](FAMILY_APPEND.md).
- Contrats raster : [`XBR2X_RASTER_CONTRACT.md`](XBR2X_RASTER_CONTRACT.md),
  [`../docs/REBOUTCX_PIPELINE_BG2_CODEX.md`](../docs/REBOUTCX_PIPELINE_BG2_CODEX.md).
- Catmull–Rom et suite graphique Dshaders : [`catmull-rom/README.md`](catmull-rom/README.md),
  D0–D6 terminés, D7 partiel ; plan/couverture dans
  [`catmull-rom/DSHADERS_SUITE.md`](catmull-rom/DSHADERS_SUITE.md), GPU/QA à réaliser.
- Règles de placement : [`FOLDER_LAYOUT.md`](FOLDER_LAYOUT.md).
- Installation courante : scripts `Install/Restore-CreatureSprite-XN-Catalog-Test.ps1`.

Activation ingame : jeu et InfinityLoader fermés, utiliser l'installateur transactionnel de
[`FAMILY_APPEND.md`](FAMILY_APPEND.md). Ne pas éditer l'INI à la main.

Le baseline QA utilise `NEAREST`. `LINEAR` est uniquement un A/B d'affichage et n'est jamais une
preuve QA. Les anciennes variantes AA et xBR4 direct sont archivées et ne font
plus partie du pipeline courant.

## Organisation

```text
sprite/
  index/                              # inventaire, règles et suivi
  ressources/<RESREF>/sources/<sha>/ # BAM natif/canonique dédupliqué, ignoré
  families/<macro>/<bucket>/<famille>/
    jobs/                             # entrées opérationnelles
    runs/                             # artefacts immuables, ignorés
    research/                         # expérimental
    source/                           # manifeste runner + liens vers ressources/, non canonique
  catalogs/
    creature-x2-nearest/jobs|runs/    # base xBR canonique
    creature-x2-reboutcx/jobs|runs/   # dérivés, remplacements explicites
  .work/                              # cache CMake reconstruisible, ignoré
```

Les anciens runbooks sont sous `archive/legacy/sprite-docs/`, hors du routage opérationnel.

Ne pas précréer les milliers de familles : matérialiser au premier job. Un BAM partagé reste une
seule charge utile physique ; les entrées de `source/` sont des liens physiques et les relations
multi-familles restent dans les CSV d'index. Conserver les anciennes extractions locales valides.

Ne jamais modifier un fichier dans un run scellé. Les jobs mutables doivent utiliser le layout
courant directement ; `path-migrations.json` n'est pas un substitut pour corriger un job actif.
Ne pas supprimer une génération encore citée par `current-generation`, `active-test` ou un backup
de restauration.

Dans le catalogue xBR, le job `qa-refresh-current-catalog-v1.json` est la recette historique exacte de la génération
active : son hash doit rester celui enregistré dans `current-generation.json`. La variante v2 est
le job mutable au layout courant pour les générations suivantes. Toute nouvelle génération de
catalogue embarque en outre les octets exacts de son job dans `build/provenance/job.json` et en
scelle le SHA-256 dans `build-manifest.json`; ce snapshot peut prouver la recette même si le job
de travail évolue ensuite. Les générations historiques dépourvues de ce champ restent vérifiées
selon leur contrat existant et ne doivent pas être réécrites pour l'ajouter.

## QA

Jeu et InfinityLoader fermés avant install/restore. Après installation autorisée, tester les seuls
nouveaux membres et préfixes représentatifs du contrat QA. Une acceptation explicite produit une
décision immuable sous `index/qa-decisions/`. Elle reste acquise tant que les octets concernés et le
contrat runtime ne changent pas ; toute réouverture doit être explicite.

## Tests légers

```powershell
python pipeline/scripts/test_changed.py --targeted --path pipeline/scripts/sprite_layout.py `
  --path pipeline/scripts/extract_sprite_sources.py `
  --path pipeline/scripts/materialize_sprite_sources.py
```

La commande affiche seulement les tests associés et n'exécute rien sans `--run`. Ne l'utiliser que
si ces tests apportent une information utile. Voir [`../docs/TEST_SELECTION.md`](../docs/TEST_SELECTION.md).

L'index et les générateurs sélectionnent `sprite-inventory`; le runner et les formats sélectionnent
`sprite-formats`; seuls les scripts `Install/Restore-CreatureSprite-XN-Catalog-Test.ps1`
sélectionnent les transactions lentes `sprite-installation`.

Régénérer l'inventaire seulement lorsqu'un snapshot du jeu, le schema, une classification, une
limite runtime ou le mapping palette change.
