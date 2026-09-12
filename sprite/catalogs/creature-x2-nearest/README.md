# Catalogue créatures x2 NEAREST

Les nouveaux descripteurs sont `jobs/append-<family>-vN.json`. Le `job_id` et le `run_dir` actifs
restent stables pour préserver la restauration.

## Production quotidienne

```powershell
python pipeline/scripts/run_creature_sprite_x2.py prepare-data --resume --job <agregat-character>
python pipeline/scripts/run_creature_sprite_x2.py prepare --resume --job <catalogue>
python pipeline/scripts/run_creature_sprite_x2.py install --job <catalogue> --creature-sprite-filter Nearest
```

`prepare` produit `built-unverified`. `install` contrôle seulement les sorties publiées et crée une
installation provisoire restaurable pour la QA. Aucun scan cumulatif n'est déclenché.

## Finalisation

```powershell
python pipeline/scripts/run_creature_sprite_x2.py verify --full-verify --keep-going --job <catalogue>
```

Après erreur, `verify --resume --keep-going` reprend uniquement les scopes invalidés. Les preuves et
caches sous `verification-cache/<generation-id>/` sont des détails internes, pas des étapes de travail.
