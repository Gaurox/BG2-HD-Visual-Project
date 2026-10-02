# Personnages jouables Q3m x2 — installation complète

- Périmètre : 78 IDs `Character`, 4 510 BAM distincts, 1 564 054 frames natives.
- Source : `sprite/index/palette-work-plan.json` → SQLite existant ; aucune nouvelle analyse des BAM ni inférence GPU.
- Cache : `sprite/.work/palette-q3m-shared/x2/15e582a92931128f728d9532113ba86a8a5958361d2989caadb7fbcb6dd20ae2/work/encoded/`.
- Pack : `sprite/.work/q3m-playable-all-x2-pack-20261002-v1/{pack.json,CreatureSprites-XN.catalog,CreatureSprites-XN-*.registry}`.
- Production courante : `current-generation.json`, SHA du pack et du catalogue ; ces sorties scellées restent conservées malgré leur emplacement `.work`.
- `assemble.py` : 8 processus CPU ; reprend uniquement les feuilles d'un assemblage non scellé. Chaque resref écrit une fois, partagé entre IDs ; contrôle source SHA, toutes géométries/centres/transparences/cycles, codec V6, I/F/dep, bornes runtime.
- `baseline.json` : catalogue actif avant remplacement = seulement `0x6100`, `0x6110` ; DLL P7, 81 paperdolls et 3 shaders conservés.
- `install.ps1` : jeu/InfinityLoader fermés ; sauvegardes `work/before/` ; copie et SHA256 de chaque shard ; publication atomique catalogue/INI ; rollback catalogue/INI en cas d'erreur. Anciens shards conservés.
- Filtre : `Box`, `CreatureSpriteFilterAnimation=0x0` (tous les acteurs du catalogue). UI existante conserve son sampler `Nearest`.
- `native-coverage.json` : correspondance exacte des 78 IDs et ressources avec le suivi existant.
- `ingame-installation/active-test.json` : reçu de copie/hashes/configuration, état installation uniquement.
- `verification.json` : contrôle après installation, manquants explicites ; aucune validation visuelle ingame déduite.
- Release/payload/TP2 inchangés. Animations statiques anciennes/sleeping et nouvelles paperdolls d'autres personnages hors de ce lot `Character`.

```powershell
$py = (Get-Content config/workspace-paths.local.json -Raw | ConvertFrom-Json).paths.chainner_python
# Déjà exécuté : verify.py --snapshot ; snapshot immuable.
& $py -u -B docs/measurements/playable-q3m-x2-ingame-20261002-v1/assemble.py --output sprite/.work/q3m-playable-all-x2-pack-20261002-v1 --workers 8
& $py -B docs/measurements/playable-q3m-x2-ingame-20261002-v1/verify.py
& docs/measurements/playable-q3m-x2-ingame-20261002-v1/install.ps1
& $py -B docs/measurements/playable-q3m-x2-ingame-20261002-v1/verify.py --installed
```
