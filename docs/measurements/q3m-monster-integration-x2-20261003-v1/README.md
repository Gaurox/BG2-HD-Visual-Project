# Phase 6 — catalogue Character + trois Monster Q3m x2

- État : **prêt à installer**, aucun octet installé modifié. Autorité production : `current-generation.json` ; contrôles : `verification.json` ; point d'arrêt : `checkpoint.json`.
- Parent acquis : `docs/measurements/playable-q3m-x2-ingame-20261002-v1/current-generation.json` → pack scellé 78 Character / 4 510 BAM / 1 564 054 frames ; catalogue actif SHA `C26C03DFB45913EF69A87B7A85A1E2CA795BEE79C03088F5A12F7D91240A61DD`.
- Delta acquis : phase 5, `MBEH/NBOH/MGLC`, 39 BAM / 20 925 frames, V6 profils `2..7`, règle `2`, owner `3`. Trois IDs disjoints, aucun resref commun avec Character, aucun BAM de ces familles dans `override`.
- Résultat : **81 IDs, 4 549 BAM, 1 584 979 frames**, 50 229 routes ; 4 549 composants/shards V6. Catalogue SHA **`7C2040D7F1AF6D412BEDD3EC919F9EF2E5775B1B9E9AC906FCBB592C307EA40B`**.
- Pack : `sprite/.work/q3m-character-monster-x2-pack-20261003-v1/{pack.json,iee-assets/creature-sprites/}`. Index parent lu avec `read_sealed_catalog_index`, aucun shard Character rehashé/décodé ; 4 510 hardlinks vers ses feuilles scellées. Les 39 feuilles Monster sont copiées et authentifiées ; aucun réencodage/inférence/compilation.
- Conservation exacte : préfixes composants/shards, memberships/owners des 78 IDs, **50 190 routes/ordinals**, digests logiques Character. Pas de partage d'un composant entre les contrats Character/Monster.
- Contrôle natif du nouveau binding : six ressources `MBEHG1/G2`, `MGLCG1/G2`, `NBOHG1/G2` ; lecteur/exécutable et oracles de phase 5 réutilisés, aucun oracle reconstruit. Toutes les palettes/encodages/frames de ces six ressources passent sous le catalogue mixte ; preuve pixels complète des 39 BAM acquise en phase 5. Pas de nouvelle QA Character.
- Runtime : manifeste scellé de phase 3, candidat DLL SHA `ade49a32a4685e490e773843519fd5f221b79aaffda10cbac02b56d94d4f6759`. DLL active baseline P7 SHA `9EB0E2B9A9BD727F2A2D346852BFE9750DA85A8F9885327538537DB02184EFD3` ; elle sera remplacée en phase 7. 81 paperdolls héritées (2 + 79), shaders inchangés ; sampler UI Nearest, monde BOX scope `0x0`.
- `baseline.json` : jeu, INI/DLL/catalogue actifs, héritage P7, configuration BOX, état des overrides. État actif toujours identique après intégration ; aucun suivi QA/release ni preuve historique réécrit.

```powershell
$q3mPython=(Get-Content config/workspace-paths.local.json -Raw | ConvertFrom-Json).paths.chainner_python
# Déjà exécuté ; sorties finales conservées. Pour nouveau candidat : nouvelle version/destination.
& $q3mPython -B docs/measurements/q3m-monster-integration-x2-20261003-v1/integrate.py --output sprite/.work/q3m-character-monster-x2-pack-20261003-v1
& $q3mPython -B docs/measurements/q3m-monster-integration-x2-20261003-v1/verify_binding.py
```

Phase 7 : jeu/InfinityLoader fermés → snapshot transactionnel catalogue/INI/DLL → copie des seuls 39 shards nouveaux + DLL candidate → catalogue publié après feuilles → contrôle hashes/configuration → test réel `BEHSPE01`, `BODHI`, `IGOLEM02` (golem AR0602 acteur 2). Rollback = restaurer catalogue/DLL/INI sauvegardés ; laisser les nouvelles feuilles non référencées. Aucune modification UI, source BAM, release/payload/TP2 ou QA globale.
