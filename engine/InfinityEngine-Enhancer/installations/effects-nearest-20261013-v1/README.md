# Effects x4 — défaut nearest, 2026-10-13

- Demande utilisateur : tous les effets nearest ; personnages nearest + silhouette AA conservés.
- Installation vérifiée : `result.json`, sauvegarde/restauration via le reçu référencé ; jeu/InfinityLoader fermés.
- Défaut permanent `effect_animation_x4_registry.cpp` : allocation, MIN/MAG NEAREST, niveau 0 seul ; pack rechargé après redémarrage. Startup log `filter=NEAREST`.
- `native_occlusion_bridge.cpp` : allocation et MIN/MAG NEAREST seulement pour `transferEffectRgb` (effects) ; branche personnages inchangée, RGB nearest/alpha silhouette AA conservés.
- DLL seule différente ; INI, fpDraw/fpSprite/fpSELECT, catalogue créatures, manifeste et registre effects identiques avant/après.
- 64 ressources effects couvertes ; les 10 médias 7B x4/Apollo30 restent installés. Aucun nouveau traitement d’image, QA/release non promues.
- 3 tests passés : `tests.log`. Test GPU réel 720 frames : pixels exacts + NEAREST min/mag + mip0 + cache<=64, allocation personnage possible après chaque frame.
- Build : `build/iee-effects-nearest-20261013-v1`, Release VS2019 ; registre eau généré byte-identique au build stable précédent.
- QA ingame : en attente utilisateur ; relancer via InfinityLoader, reprendre les mêmes CLUA.
