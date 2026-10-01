# Guerriers humains 0x6100 + 0x6110 — test ingame Q3m K6 x2

- État courant : catalogue x4 rétabli le 2026-10-01 à 17:52 UTC, preuve `restoration-verification.json` ; reçu x2 retiré. Pack x2 disponible pour réinstallation. `installation-verification.json` conserve l'installation initiale historique ; aucun lancement du jeu ni acceptation visuelle déduite.
- Catalogue produit : V2 x2 ; 2 animations Character, 1 312 composants/shards V6, 1 312 routes, 358 697 frames (mâle 180 337, femelle 178 360).
- Par modèle : 656 BAM, 4 corps/armures, 18 casques, 12 boucliers, 31 armes ; absences natives conservées. Garlena `0x6010` reste native ; aucun autre acteur ajouté.
- Recette : Q3m K6, six fits P1, F=0..7 u8/pixel, x2 BOX du réseau x4 ; aucun B/tramage. Régression REF P1 connue +6,10 % x2, paramètres conservés.
- Assemblage uniquement : `prepare_catalog.py` reprend les V6 existants, SHA de chaque shard et routes identiques aux sources ; aucune inférence ni réencodage. Le parent féminin de 195 animations est filtré sur `0x6110` avant fusion avec `0x6100`.
- Sources : mâle `../../families/playable-characters/6100-human-male-fighter/research/palette-q3m-series-20261001-v1/x2-verification.json` ; femelle `../../families/playable-characters/6110-human-female-fighter/research/palette-q3m-p3-20261001-v3-full-6110/verification.json`. Preuves intégrales antérieures conservées car octets V6 inchangés.
- Contrôle du catalogue commun : deux working sets natifs, chacun 657 frames × 18 palettes, première résolution sans polling, rechargement après éviction, composition réelle à quatre couches ; 132 211 080 pixels comparés. Métadonnées et I/F résidents ≤ 128 Mio. Résultats et identités dans `verification.json`.
- Pack x2 : 601 827 124 octets (601,83 Mo), catalogue + 1 312 registres ; fichiers x2/x4 conservés sur disque. Catalogue x2 SHA `5F0596DDAC14ECDBFD1915978736C160DF1F7F465156472FD410A8705CDC6044`.
- Runtime : `pipeline/runtime/manifests/iee-character-cold-resolve-20261001-v1.json`, DLL corrigée SHA `D79B72B97BF48F3D743325F2FFF2BE39D0A008FCE1DA37239476B0018FFC6C74`, inchangée. Limite déclarée I+F x2 256 Mio ; borne conservative requise `2 × max(index_bytes)` = 219 509 144 octets. Géométrie/composition inchangées.
- INI inchangé : CreatureHD actif, Nearest, filtrage linéaire désactivé, fpSprite/fpSELECT x1 et trace palettes désactivés. L'échelle vient du catalogue ; `EnableCreatureSpriteX2Test=false` désigne l'ancien chemin de test.
- Installation transactionnelle via `install_and_verify.ps1` : jeu/InfinityLoader fermés ; 656 nouveaux shards copiés, 656 déjà présents ; tous les SHA source/installés vérifiés. Sauvegardes catalogue x4/INI vérifiées ; DLL non remplacée.
- QA restante : continuité marche/attaque/directions, changements d'équipement/palette, effets pulsés, ombres/transparence et rendu GL. Alpha d'oracle synthétique ; aucune QA ingame déduite des tests hôte.

Depuis la racine du workspace :

```powershell
$q3mRun = 'sprite/catalogs/palette-q3m-human-fighters-x2-20261001-v1'
$q3mRuntime = 'pipeline/runtime/manifests/iee-character-cold-resolve-20261001-v1.json'
# Lecture seule : catalogue x2, DLL, INI et tous les shards actifs.
& pipeline/scripts/Install-CreatureSprite-XN-Catalog-Test.ps1 -JobFile "$q3mRun/x2-q3m-k6.job.json" -RuntimeManifest $q3mRuntime -CreatureSpriteFilter Nearest -VerifyOnly
# Retour exact au catalogue x4 sauvegardé, même DLL ; jeu/InfinityLoader fermés.
& pipeline/scripts/Restore-CreatureSprite-XN-Catalog-Test.ps1 -JobFile "$q3mRun/x2-q3m-k6.job.json"
# Réinstaller x2 après restauration ; jeu/InfinityLoader fermés.
& pipeline/scripts/Install-CreatureSprite-XN-Catalog-Test.ps1 -JobFile "$q3mRun/x2-q3m-k6.job.json" -RuntimeManifest $q3mRuntime -CreatureSpriteFilter Nearest
```
