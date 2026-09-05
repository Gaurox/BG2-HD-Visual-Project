# Contrat raster XBR2x

Ce contrat ne couvre que la transformation d'une frame. L'identité, la famille, les suffixes BAM,
le profil moteur et l'éligibilité viennent de `sprite/index/`.

## Transformation retenue

| Paramètre | Valeur |
|---|---|
| Algorithme | `xbr2X` |
| Échelle | x2 en une passe |
| Blend/anti-alias | désactivé ; production sans anti-alias |
| Entrée/sortie | PNG RGBA, dimensions exactement doublées |

Conserver le RGB sous alpha nul et ne jamais aplatir sur un fond. Traiter les frames séparément,
pas une planche.

## Exécution reproductible

Le point d'entrée est le runner, qui résout `config://mmpx_scalepix`, appelle
`pipeline/scripts/xbr2x_batch.js` par protocole binaire et vérifie la recette :

```powershell
python pipeline/scripts/run_creature_sprite_x2.py plan --job <job.json>
python pipeline/scripts/run_creature_sprite_x2.py build --job <job.json>
python pipeline/scripts/run_creature_sprite_x2.py verify --job <job.json>
```

Pour un nouveau job, déclarer `scalepix: "config://mmpx_scalepix"`; ne pas inscrire de chemin
machine. `xbr2x_batch.js` est un adaptateur interne, pas une CLI PNG autonome.

## Contrôles

- `family_id` existe dans `sprite/index/sprite_families.csv` ;
- `pipeline_ready=yes`, ou tous les blockers sont explicitement traités ;
- ordre, cycles, dimensions, centres, offsets et palette dynamique x1 préservés ;
- sortie exacte x2, alpha intact et aucune frame manquante ;
- inspection de plusieurs directions, armes, états et silhouettes ;
- QA runtime avec filtrage `NEAREST`.

La réussite raster ne vaut ni validation famille, ni installation, ni release.
