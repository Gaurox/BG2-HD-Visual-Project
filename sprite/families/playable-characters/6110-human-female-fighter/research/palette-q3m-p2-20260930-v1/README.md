# P2 Q3m K6 — expérimental, hors jeu

État : **PASS**, écrivain/lecteur V6, DLL x64 et quatre packs disponibles localement.
`verification.json` = preuve finale ; `packs.json` = inventaire/input hashes ;
`provenance/source/` = sources figées. P0/P1 et pré-P2 restent immuables.
Date de fin : 2026-10-01 ; nom de run conservé depuis le démarrage 2026-09-30.

## Livrables

- DLL : `candidate/InfinityEngine-Enhancer.dll`, 1 924 608 octets,
  SHA256 `3d509d73aded7da2b946ea6f45afb1fef92f2c3d4e066b07f870ed08a78cd57b`.
- Packs : `packs/{x2-q0,x2-q3m-k6,x4-q0,x4-q3m-k6}/iee-assets/creature-sprites/`.
  Chaque pack contient catalogue V2 + une feuille V6, et `decoder-oracle.bin` à côté.
- Contrat binaire : `pipeline/PALETTE_Q3M_V6.md` ; APIs `palette_registry.py`.
- Registres/DLL/guides de travail ignorés par Git ; sources/preuves versionnables.
  Une reproduction écrit un nouveau run, sans remplacer celui-ci.

Scope identique des quatre packs : animation `0x6110`,
`CHFF4G11`, `CHFF4G12`, `WQNJ6G1`, `WQND3G1`, `WQNS1G1` ;
4230 frames/cycles natifs complets ; 84 frames P1 Q0 ou Q3m K6,
4146 frames xBR communes dont 756 placeholders.
Ce complément xBR permet la résolution native de toutes les tables sans nouvelle inférence.
Pas de paperdoll ni d'extension à d'autres familles.

| Pack | Octets feuilles | Pic I+F résident mesuré |
|---|---:|---:|
| x2-q0 | 4 172 692 | 3 574 388 |
| x2-q3m-k6 | 4 247 615 | 3 742 396 |
| x4-q0 | 5 721 069 | 14 297 552 |
| x4-q3m-k6 | 5 924 303 | 14 969 584 |

Métadonnées natives : 3 269 520 octets/pack. Ces compteurs excluent working set total,
inflation transitoire/CPU pixels/GL ; corpus majoritairement xBR, pas une projection globale.
Temps hôte vérification complète+SHA : 632/651/1468/1496 ms respectivement, pas des mesures FPS.

## Preuves réalisées

- 146 tests Python PASS ; 4 suites CTest Release PASS, baseline historique incluse.
- NPZ P1 épinglé, 32 832 couples palette/pixel distincts reproduits par le lecteur natif ;
  32 palettes alpha arbitraire supplémentaires ; RGBA/u8, BGRA/u8, BGRA/u32_8888_REV.
- 1 368 000 comparaisons pixel individuelles sur variantes brut/XPRESS/F absent/F0/V5.
  8 fixtures valides, 35 invalides à hashes/catalogues extérieurs cohérents.
- 304 560 reconstructions complètes de frames des quatre packs, 643 389 840 pixels,
  toutes identiques au SHA256 Python sur 18 palettes.
- Dépendances exactes, successeur absent des representatives, F0 sans lecture successeur,
  alpha primaire, palettes distinctes par couche/acteur, 16 pulsations simulées,
  cache hit sur couleur inutilisée, reset CPU et composition/bordures natives.
- Éviction : cinq frames I+F de 32 Mio, limite 128 Mio maintenue, ancien couple rechargé
  puis 16 777 216 pixels vérifiés. Valeurs F/flags/profils/codec/tailles/masks/troncatures,
  mauvais décodage XPRESS et owner non Character rejetés.
- Build VS2019/v142/MSVC19.29.30158, SDK10.0.19041, CMake4.0.2,
  Python3.11.5+NumPy `config://chainner_python`, dépendances épinglées vérifiées par archive.

Commandes exactes dans `verification.json`. CMake crée les fixtures de test dans le build.
Reproduction pack : `python -B pipeline/scripts/palette_p2.py packs --output <nouveau-run>`.
Vérification hôte : `iee_palette_fraction_tests.exe --pack <assets> <decoder-oracle.bin>`.
Build local : `build/palette-q3m-p2-20260930-v1/cmake` ; sources et test executables hashés.

## Frontière P3

**P3 non commencé ; aucune installation, QA ingame, production globale ou release.**
Le guide Claude disponible a été lu et hashé, sans modification.
V6 est désormais réservé ; F=u8/pixel 0..7 ; B et packing désactivés.
LUT ne remplit que les couples utilisés ; invalidation pulsée dépend des couleurs lues.
Repli courant = BAM natif ; Q0/xBR est un comparateur explicite, pas un fallback V5 automatique.

Restent pour une demande P3 : captures de palettes/alpha/effets réellement réalisés dans
BG2EE, queue/upload GL et reset WGL réel, FPS, QA visuelle et verticale équipement/paperdoll.
P1 garde la régression REF **+6,10% x2 / +11,59% x4** ; aucun arbitrage visuel acquis.
Les tests alpha arbitraire prouvent le contrat des octets, pas le comportement vivant des effets.
Changements P2 non committés à la clôture ; commit pré-P2 existant `f8c266fb`.
