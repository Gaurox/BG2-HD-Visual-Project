# Tuilage RGBA des effets alpha.11

- Entrée `releases/BG2-HD-Upscale/release-inputs/effects/accepted-crop-20261121-v1`.
- Référence de comparaison `releases/BG2-HD-Upscale/release-inputs/effects/accepted-20261110-v1`. Chaque frame logique est comparée à son propre fichier RGBA avant déduplication, y compris les alias.
- `python -B effects/research/rgba-tiles-20261121-v1/build.py build` produit `pack/` et `results.json` après vérification. `verify` relit le pack déjà produit.
- Par rectangle, choisir le plus petit stockage entre RGBA dense et tuiles 4, 8, 16, 32 ou 64 px, bitmap compris. Tuiles de bord tronquées aux dimensions du rectangle. Suppression limitée aux blocs RGBA tous à zéro.
- `IEETILE1` lie le SHA-256 de `EffectCrops-X4.index`. En-tête `<8sII32s>` avec nombres de frames physique et logique. Enregistrements `<QIB3x>` dans l'ordre des rectangles canoniques, puis bitmaps little-endian. Les offsets des bitmaps sont relatifs à la fin des enregistrements. Le blob contient les pixels RGBA des tuiles présentes dans l’ordre de lecture des pixels du rectangle. Le mode 0 stocke le rectangle dense.
- Gain net calculé sur les octets écrits, avec le nouvel index de tuiles et l’index de rognage conservé. Le stockage omet les tuiles à zéro. La mutualisation du pack alpha.11 porte sur les frames RGBA sources.

## Candidat local

- `build.py build --live` lit le pack rogné local et vérifie chaque frame contre `config://bg2ee_game_root/iee-assets/effects-before-crop-20261121-v1`. Résultat dans `pack-live/` et `results-live.json`.
- Lecteur `src/iee/core/effect_tile_index.h`. Table et bitmaps lus à la demande. Expansion RGBA dans le tampon du cache, sans deuxième image complète. Bitmap maximal 15 017 octets par lecteur sur les deux packs.
- Test hôte `iee_effect_animation_x4_registry_tests.exe --metadata-mib 32 --streaming effects/research/rgba-tiles-20261121-v1/pack-live effects/installations/cow-sprite-bridge-20261109-v1/runtime-contracts.tsv`. Jeu local `metadataBytes=32071153`, 907 lectures au démarrage, 12 lectures à la demande, 2 304 contrats de phase, pic cache CPU 271 334 592 octets, zéro échec. Chargement du catalogue seul sans lecture RGBA.
- Relancer par `InfinityLoader.exe`. Chercher `Effect tile storage: physicalFrames=72563` puis `backend=streaming` dans `InfinityEngine-Enhancer.log`. Rejouer [COW, Boule de feu, Nuage mortel et le HUD](../rgba-crop-full-20261121-v1/README.md#parcours-en-jeu) avec le nouveau lecteur.
- Retour au pack rogné précédent après fermeture du jeu et d’InfinityLoader. Exécuter `Install-TiledEffects.ps1 -Action Restore` sous PowerShell 7.
