# Monster : composition corps + équipements généralisée

- État : **installé, accepté ingame** ; utilisateur « validé. committe », 2026-10-11.
- QA immuable : `sprite/index/qa-decisions/runtime/2026-10-11-accepted-monster-composite-x2-v1.json`.
- Diagnostic : `../monster-composite-analysis-20261011-v1/README.md`.
- Sources modifiées : `src/iee/hooks.cpp`, libellé `creature_sprite_x2.cpp`, régressions
  `tests/iee_tests.cpp` dans `engine/InfinityEngine-Enhancer/source-patchee/`.
- Plus d'exception `0x7F09` : collecter les deux cellules supplémentaires de chaque Monster selon
  les conditions natives. Corps seul => voie monocouche ; cellule active => composition complète.
- Cellule active absente/non enregistrée/illisible => conserver le composite natif complet,
  y compris si son rectangle tient dans celui du corps. Équipement nul facultatif ignoré.
- Ordre, palettes, centres, union stricte et bordure natifs conservés ; diagnostic borné par ID.
- Périmètre : gestionnaire commun owner3 ; 8 IDs équipés supplémentaires identifiés, dont géants
  `0x7F3E` et Yaga-Shura `0x7F3F`. Aucun recalcul Q3m ni modification de catalogue/assets.

## Build / vérification

- Base : sources exactes de la DLL installée SPHINCT v7 ; corrections décor récentes conservées.
- `runtime.json` : candidat, provenance, delta ; `runtime-delta.patch` : 3 fichiers seulement.
- Tous les autres fichiers de la source parent comparés identiques ; aucune fusion d'un ancien
  runtime qui supprimerait les corrections récentes.
- DLL candidate SHA256 : `28651777499111be1d94cfd878947bcd67c0ad5062e2673f8991e153d6a46dcd`.
- Tests natifs : `native-tests.log`, `All InfinityEngine-Enhancer native tests passed`.
- Régressions nouvelles : MFIGG12/551 + marteau => 87x193 ; + hache => 87x196 ; offsets corps/arme.
- Tests existants : composition sahuagin, palettes, registres et géométrie native.
- Compilation MSBuild exécutée sur l'hôte Windows ; lancement sous sandbox bloqué à ZERO_CHECK.

## Installation / test utilisateur

- `installation.json` : état actif séparé du candidat et de la QA.
- Sauvegarde : `backups/renderer/20261011T090835037764Z-f8d1a2b6/renderer-install-receipt.json`.
- Ancienne DLL : `73730a6deb3efb5b7ff1284967cc019ff28b2402f57d5874da9ef0ba281fba24`.
- Jeu/InfinityLoader fermés vérifiés par l'installateur ; INI et catalogue vérifiés inchangés.
- Correction des retours vanilla des géants acceptée après test utilisateur ; contrat commun
  Monster accepté. Aucun retest individuel des 77 IDs/directions/équipements déduit.
- Diagnostic runtime : `Monster native composite scope animation=0x7F3E` et couches MFIG.
- Aucune QA historique réécrite ; aucune intégration release.

Restauration, après fermeture jeu/InfinityLoader :

```powershell
python engine/InfinityEngine-Enhancer/source-patchee/tools/install_renderer_candidate.py restore backups/renderer/20261011T090835037764Z-f8d1a2b6
```
