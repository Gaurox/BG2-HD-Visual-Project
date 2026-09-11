# Traitement des sprites — runbook agent

## Autorités

| Décision | Source |
|---|---|
| identité, familles, BAM, ITM, éligibilité | `index/sprite_*.csv`, `index/manifest.json` |
| classement | `index/family-groups.csv`, `sprite_layout.py` |
| cycle de vie | `index/processing.csv` |
| source native | `ressources/<RESREF>/sources/<sha>/` |
| génération/test actifs | `current-generation.json`, `active-test.json` |

Ne jamais déduire identité, préfixe, équipement, QA ou release depuis un nom ou un dossier.

## Gates

Exiger pour chaque famille non vide :

```text
runtime_supported=yes
pipeline_ready=yes
blocker=<vide>
override_collision=<vide>
resource_count>0
frame_count>0
```

Une famille vide reste exclue avec son blocker ; ne pas créer de job vide.
Profils automatisés actuels : `character-bg2ee-2.7.3.0` et
`monster-icewind-bg2ee-2.7.3.0`. Pour tout autre profil : inventaire seulement, arrêt.

## Chaîne courante

1. Lire les lignes cible dans `sprite_families.csv`, `sprite_resources.csv`, `sprite_items.csv` et
   `processing.csv`.
2. Planifier le job :
   - Character complet : `generate_character_complete_x2_jobs.py`, voir `FAMILY_APPEND.md` ;
   - MonsterIcewind unitaire : `generate_sprite_family_append.py member`, voir `FAMILY_APPEND.md`.
3. Publier le job seulement après revue : `--run` pour Character ; retirer `--dry-run` pour membre.
4. Planifier puis extraire les BAM une fois dans le store central :

```powershell
python pipeline/scripts/extract_sprite_sources.py <sélecteur>
python pipeline/scripts/extract_sprite_sources.py <sélecteur> --run
```

Sélecteurs usuels : `--animation-id 0xFFFF`, `--family-id <id>`, `--resref <BAM>`.

5. Planifier puis créer les manifestes/liens physiques attendus par le runner :

```powershell
python pipeline/scripts/materialize_sprite_sources.py --job <job-ou-agregat>
python pipeline/scripts/materialize_sprite_sources.py --job <job-ou-agregat> --run
```

6. Produire seulement sur demande explicite :

```powershell
python pipeline/scripts/run_creature_sprite_x2.py plan --job <job-ou-agregat>
python pipeline/scripts/run_creature_sprite_x2.py prepare --resume --job <job-ou-agregat>
python pipeline/scripts/run_creature_sprite_x2.py verify --job <job-ou-agregat>
```

Batch Character : ne pas vérifier chaque agrégat séparément. Utiliser :

```powershell
python pipeline/scripts/run_creature_sprite_x2.py prepare-data --resume `
  --defer-full-verify --job <agregat-character>
python pipeline/scripts/run_creature_sprite_x2.py prepare --resume `
  --defer-full-verify --job <catalogue>
python pipeline/scripts/run_creature_sprite_x2.py verify --full-verify `
  --keep-going --job <catalogue>
# Après correction :
python pipeline/scripts/run_creature_sprite_x2.py verify --resume `
  --keep-going --job <catalogue>
```

Seul `prepared-verified` est installable. Détails des preuves/checkpoints :
`catalogs/creature-x2-nearest/README.md`.

Ne pas utiliser `run_creature_sprite_x2.py extract` pour un nouveau workspace : ce chemin legacy
duplique les BAM et génère des PNG source.

## Suivi

- `sync_sprite_processing.py` : ajout conservateur de lignes, plan-only puis `--run` ; aucune
  promotion d'état.
- `index/extractions.csv` : projection écrite par l'extracteur ; ne pas éditer et ne pas confondre
  extraction avec production.
- Production : renseigner uniquement `production_*` depuis un build-manifest vérifié.
- Sélection : renseigner `selected_*` par décision distincte.
- QA, installation, release : renseigner uniquement depuis leur preuve explicite.
- Un même agrégat Character peut prouver plusieurs lignes famille ; conserver le préfixe exact.

## Interdictions

- Ne jamais modifier un job, run, build, reçu, décision QA ou catalogue scellé.
- Ne jamais précréer tout l'inventaire ni copier un BAM partagé par famille.
- Jeu et InfinityLoader fermés avant install/restore.
- `pending-qa` n'est pas validé ; release après `validated-installed` et accord explicite.
- Append catalogue, installation, QA et release : suivre `FAMILY_APPEND.md`.
