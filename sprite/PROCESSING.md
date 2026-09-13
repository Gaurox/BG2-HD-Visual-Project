# Traitement des sprites — chemin court

## Autorités indépendantes

| État | Source |
|---|---|
| identité et éligibilité | `index/sprite_*.csv`, `index/manifest.json` |
| production courante | `catalogs/.../current-generation.json` + `build-manifest.json` |
| QA ingame | décision immuable sous `index/qa-decisions/` |
| installation locale | `catalogs/.../ingame-installation/active-test.json` |
| release | `releases/BG2-HD-Upscale/manifests/sprite-release-candidates.json`, puis `content.json` |

Ne jamais propager un état entre ces sources. Une installation `pending` n'annule pas une QA
existante. Une QA acceptée reste acquise tant que ses octets et son contrat runtime sont inchangés.

## Production locale

Une famille non vide est traitable si :

```text
runtime_supported=yes
pipeline_ready=yes
blocker=<vide>
override_collision=<vide>
resource_count>0
frame_count>0
```

Profils automatisés : `character-bg2ee-2.7.3.0`, `monster-bg2ee-2.7.3.0`,
`monster-icewind-bg2ee-2.7.3.0`.

1. Lire seulement les lignes cible de `sprite_families.csv`, `sprite_resources.csv` et, si utile,
   `sprite_items.csv`.
2. Créer le membre ou agrégat avec `generate_sprite_family_append.py` ou
   `generate_character_complete_x2_jobs.py`.
3. Extraire et matérialiser uniquement sa portée :

```powershell
python pipeline/scripts/extract_sprite_sources.py --family-id <family_id> --run
python pipeline/scripts/materialize_sprite_sources.py --job <job> --run
python pipeline/scripts/run_creature_sprite_x2.py prepare --resume --job <job>
```

4. Ajouter le lot au catalogue courant selon [`FAMILY_APPEND.md`](FAMILY_APPEND.md).
5. Installer et tester seulement le delta.

`prepare` vérifie le delta. `verify` quotidien lit les métadonnées. Le scan complet
`verify --full-verify` appartient uniquement à la finalisation explicitement demandée.

## Enregistrement minimal

- Production : le pointeur de génération et le manifeste scellé suffisent.
- QA : un fichier immuable identifie la portée, la génération, les hashes, le verdict et la note
  utilisateur. Ne jamais modifier une ancienne décision.
- Installation : le reçu décrit seulement les fichiers actuellement installés et leur rollback.
- Release : ajouter uniquement le candidat accepté ; différer TP2, staging, miroirs et package.

Les runs de travail non référencés restent jetables. Aucun registre global, synchronisation de
cycle de vie ou réconciliation installation→QA n'est autorisé.
