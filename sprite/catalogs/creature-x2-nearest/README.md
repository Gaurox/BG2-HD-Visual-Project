# Catalogue créatures x2 NEAREST

Les nouveaux descripteurs sont `jobs/append-<family>-vN.json`, au schéma
`bg2-upscale-creature-sprite-xn-catalog-delta-job-v1`. Ils épinglent le manifeste et le petit index
de la génération acceptée ; `members` et `qa.animations` ne décrivent que le nouveau lot.

## Production quotidienne

```powershell
python pipeline/scripts/run_creature_sprite_x2.py prepare --resume --job <catalogue>
python pipeline/scripts/run_creature_sprite_x2.py install --job <catalogue> --creature-sprite-filter Nearest
```

`prepare` vérifie le nouveau lot, crée ses shards, relie les shards parents sans les lire et publie
le pointeur installable. Le runtime stable est installé séparément. `install` crée une installation
provisoire restaurable ; aucun scan cumulatif n'est déclenché.

## Finalisation

```powershell
python pipeline/scripts/run_creature_sprite_x2.py verify --full-verify --job <catalogue>
```

Sans `--full-verify`, `verify` ne contrôle que l'identité et les métadonnées. La finalisation relit
une fois l'ensemble des shards ; elle n'entretient plus de cache ou de graphe de preuves.
