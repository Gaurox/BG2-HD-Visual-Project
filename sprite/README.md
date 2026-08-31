# Sprites complexes — point d'entrée

> **Règle documentaire : écrire pour des agents IA — concis, factuel, opérationnel, non narratif. Éviter la verbosité et les répétitions. Toute nouvelle documentation ou modification doit privilégier la densité d’information, les listes/tableaux, les chemins et commandes précises. Éviter la prose longue, le contexte narratif, les répétitions et les explications principalement destinées à un lecteur humain.**

Ce domaine couvre les créatures et Characters composés (corps, arme, bouclier/offhand, casque et
palettes). Il ne dépend pas du pipeline maps.

## Sources de vérité

1. [`index/README.md`](index/README.md) : schema et requêtes.
2. `index/manifest.json` : snapshot du jeu et de l'inventaire.
3. `index/sprite-layout.json` : layout physique courant.
4. `index/path-migrations.json` : anciens chemins d'artefacts immuables uniquement.
5. Les quatre CSV d'`index/` : animations, familles, ressources et items.
6. `current-generation.json` et `active-test.json` du catalogue cumulatif.

`pipeline_ready=yes` prouve seulement les prérequis automatisés. Ce n'est ni un build, ni une
installation, ni une validation ingame.

## Méthode actuelle

```text
index normalisé
  → sélectionner une famille pipeline_ready
  → générer les jobs
  → run_creature_sprite_x2.py
  → vérifier le catalogue cumulatif
  → installer/restaurer transactionnellement
  → QA NEAREST
```

Conditions avant production : `runtime_supported=yes`, `pipeline_ready=yes`, `blocker` vide et
`override_collision` vide.

- Runner : `pipeline/scripts/run_creature_sprite_x2.py`.
- Inventaire : `pipeline/scripts/build_sprite_inventory.py`.
- Génération Character : `pipeline/scripts/generate_character_complete_x2_jobs.py`.
- Ajout de famille : [`FAMILY_APPEND.md`](FAMILY_APPEND.md).
- Contrat raster xBR2x : [`XBR2X_RASTER_CONTRACT.md`](XBR2X_RASTER_CONTRACT.md).
- Règles de placement : [`FOLDER_LAYOUT.md`](FOLDER_LAYOUT.md).
- Installation courante : scripts `Install/Restore-CreatureSprite-XN-Catalog-Test.ps1`.

Le baseline QA utilise `NEAREST`. `LINEAR` est uniquement un A/B d'affichage et n'est jamais une
preuve `validated-installed`. Les anciennes variantes AA et xBR4 direct sont archivées et ne font
plus partie du pipeline courant.

## Organisation

```text
sprite/
  index/                              # catalogues canoniques
  families/<classe>/<famille>/
    source/                           # extraction native, donnée ignorée
    jobs/                             # entrées opérationnelles
    runs/                             # artefacts immuables, ignorés
    research/                         # expérimental
  catalogs/creature-x2-nearest/
    jobs/                             # transactions/générations
    runs/                             # payloads cumulés, ignorés
  .work/                              # cache CMake reconstruisible, ignoré
```

Les anciens runbooks sont sous `archive/legacy/sprite-docs/`, hors du routage opérationnel.

Ne jamais modifier un fichier dans un run scellé. Les jobs mutables doivent utiliser le layout
courant directement ; `path-migrations.json` n'est pas un substitut pour corriger un job actif.
Ne pas supprimer une génération encore citée par `current-generation`, `active-test` ou un backup
de restauration.

Le job `qa-refresh-current-catalog-v1.json` est la recette historique exacte de la génération
active : son hash doit rester celui enregistré dans `current-generation.json`. La variante v2 est
le job mutable au layout courant pour les générations suivantes. Toute nouvelle génération de
catalogue embarque en outre les octets exacts de son job dans `build/provenance/job.json` et en
scelle le SHA-256 dans `build-manifest.json`; ce snapshot peut prouver la recette même si le job
de travail évolue ensuite. Les générations historiques dépourvues de ce champ restent vérifiées
selon leur contrat existant et ne doivent pas être réécrites pour l'ajouter.

## QA

Jeu et InfinityLoader fermés avant install/restore. Après installation autorisée, tester chaque
animation et préfixe représentatif du contrat QA : composition, palettes, équipement, orientations
et transitions. N'enregistrer un pass qu'après réussite des gates automatiques et acceptation
explicite de l'utilisateur.

## Tests légers

```powershell
python pipeline/scripts/test_changed.py --targeted
```

La commande prépare la question obligatoire « ciblés / tous / aucun » et n'exécute rien sans
`--run`. Voir [`../docs/TEST_SELECTION.md`](../docs/TEST_SELECTION.md).

L'index et les générateurs sélectionnent `sprite-inventory`; le runner et les formats sélectionnent
`sprite-formats`; seuls les scripts `Install/Restore-CreatureSprite-XN-Catalog-Test.ps1`
sélectionnent les transactions lentes `sprite-installation`.

Régénérer l'inventaire seulement lorsqu'un snapshot du jeu, le schema, une classification, une
limite runtime ou le mapping palette change.
