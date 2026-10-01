# Character : suppression du retour natif pendant le chargement

- Runtime : `pipeline/runtime/manifests/iee-character-cold-resolve-20261001-v1.json`.
- État : `installation-verification.json` = `installed-pending-manual-qa` ; aucune QA ingame déduite.
- Catalogue x4 courant : `sprite/catalogs/palette-q3m-human-fighters-x4-20261001-v1` ; mêmes 1 312 shards, mêmes routes `0x6100/0x6110`, mêmes octets catalogue/INI. `0x6010` / Sœur Garlena reste natif.
- Correctif commun x2/x4, Character + Catalog V2 uniquement : `resolve_frame(..., WaitForCharacterMetadata)` attend le worker existant sur la ressource demandée ; corps à l'entrée Render, trois équipements, nouvelle résolution lors de chaque Realize corrélé.
- Attente hors `g_mutex` ; réveil à la fin de la requête ou à l'arrêt du worker ; epoch contrôlé avant utilisation. Aucun ancien composite/frame conservé artificiellement.
- Attente maximale : 5 s par ressource ; dépassement = quarantaine du composant puis repli natif. Une pause est possible au premier accès à froid. Absence, corruption, bornes invalides : repli natif conservé.
- Géométrie, composition, palettes, profils Q3m/V5, XPRESS, budgets I/F et métadonnées inchangés. Payloads toujours lazy ; appels chauds sans accès fichier. Autres owners et découverte Catalog V1 : résolution non bloquante conservée.

## Preuves

- `verification.json` : DLL/source scellées, deux tests CTest réussis, 10 fixtures Q3m valides / 37 invalides ; helper Character sans polling/réessai.
- Régression dédiée : quatre couches à froid, x2 + x4, résolution au premier appel ; absence `0x6010`, resref absent, slot invalide, composant manquant, accès chauds.
- Packs réels : 657 frames × 18 palettes pour `0x6100` x2, `0x6100` x4 et `0x6110` x4 ; 594 129 744 pixels comparés, composition des quatre couches, éviction métadonnées sous 128 Mio ; aucun avertissement.
- `installation-baseline.json`, `installation-verification.json` : ancienne DLL sauvegardée, nouvelle DLL installée, adoption du runtime dans le reçu catalogue actif, 1 312 shards vérifiés ; aucune recopie de shard.
- Candidat immuable local : `build/creature-character-cold-resolve-20261001-v1/candidate/InfinityEngine-Enhancer.dll` ; SHA dans le manifeste. Génération/QA/release des assets inchangées.

## Commandes depuis la racine

```powershell
$runtime = 'pipeline/runtime/manifests/iee-character-cold-resolve-20261001-v1.json'
$state = '.tmp/iee-runtime-install/character-cold-resolve-20261001-v1'
$job = 'sprite/catalogs/palette-q3m-human-fighters-x4-20261001-v1/x4-q3m-k6.job.json'
# Lecture seule : runtime puis catalogue courant.
& pipeline/scripts/Install-IEE-Runtime-Test.ps1 -Mode Verify -Manifest $runtime -StateRoot $state
& pipeline/scripts/Install-CreatureSprite-XN-Catalog-Test.ps1 -JobFile $job -RuntimeManifest $runtime -CreatureSpriteFilter Nearest -VerifyOnly
# Repli vers l'installation antérieure ; jeu/InfinityLoader fermés.
& pipeline/scripts/Restore-CreatureSprite-XN-Catalog-Test.ps1 -JobFile $job
& pipeline/scripts/Install-IEE-Runtime-Test.ps1 -Mode Restore -StateRoot $state
```

- Test utilisateur restant : apparition, première marche/attaque/changement de direction et équipement ; vérifier disparition du flash vanilla et coût du premier accès. Catalogue ingame actuellement x4 ; x2 validé hors jeu avec la même source native.
