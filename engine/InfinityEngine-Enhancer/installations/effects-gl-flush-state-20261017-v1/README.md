# Effects : cohérence GL après flush natif — 2026-10-17

- Statut : **installé, vérifié hors jeu ; QA visuelle en attente**. Autorisation : « corrige le bug, puis installe-le ingame ».
- Diagnostic historique immuable : `effects/research/white-stripes-20261017-v1/REPORT.md` ; session14:43–14:52,3124flushes GPU, zéro miss/échec. Défaut reproduit ; lien exact avec le symptôme ingame encore à confirmer.
- Cause : garde GL capturé avant `DrawFlush_GL`, restauré après. Le flush actualise le cache natif d'état appliqué ; `DrawPush/PopState` ne conserve que l'état logique désiré. Restauration de l'ancien shader => cache/GL incohérents ; prochain draw peut omettre `glUseProgram`, zéro erreur GL.
- Correction : `src/iee/effect_animation_x4_registry.cpp`, garde restauré avant flush puis recréé depuis l'état post-flush ; `release_gpu` flush avant capture. Flush avant mutation des dimensions/pixels, cache64 et filtreNEAREST conservés. Contrat du garde précisé dans `src/iee/game/scoped_effect_gl_state.h`.
- Régression : `tests/effect_texture_cache_tests.cpp`, uploader de production + WGL réel invisible + cache natif de shaders simulé d'après le PE ; readback d'une bande rouge/blanche. Aucun lancement du jeu.

| Vérification | Résultat / preuve |
|---|---|
| Avant correction | `regression-before-fix.log` : sortie1 attendue ; shader réel3/cache6 ; pixel255,255,255 ; erreurGL0 |
| Après correction | `regression-after-fix.log` : sortie0 ; LRU/libération/réduction mémoire : shader6/cache6 ; pixel255,0,0 ; erreurGL0 |
| Cache GPU | même test :720images exactes,400slots natifs occupés, allocation Character toujours possible, <=64textures effets, NEAREST sans mips ; refus allocation/échec upload injectés et récupération |
| Registry/streaming | `registry-tests.log` : sortie0 ; avertissements attendus des fixtures invalides |
| Catalogue actif | `active-catalogue-check.log` :221RESREF,27479backings,59264contrats natifs,15470842octets métadonnées, zéro lectureRGBA |
| Build | `build-fix-v1.json` / `.log` : CMake/MSBuild sortie0 ; nouveau build isolé `build/iee-effects-gl-flush-state-20261017-v1` ; dépendances locales |

## Installation / reprise

- Autorité : [`installation.json`](installation.json), transaction [`renderer-install-receipt.json`](backups/20261017T131615101741Z-c8e28643/renderer-install-receipt.json).
- DLL active SHA256 `FEA4B2B153653461D465B67EB9CC5A762CC97785E511EEBBF5C776348268C246` ; ancienne `824A74D8FC107BE4C23D66A416C535199D217B11CC5CB6903B641ADEB33006D1` sauvegardée.
- Jeu et InfinityLoader arrêtés lors de la transaction ; cible `config://bg2ee_game_root`. Candidat limité DLL+INI ; INI identique, seul DLL remplacé. Staging/sauvegardes/cibles revérifiés par l'installateur canonique.
- `before.json` / `installation.json` : identités INI/exécutable/shaders/catalogue personnages/manifest+registre effets inchangées. Assets, contrôleurs VVC, profils, cadence et release non modifiés.
- Recette : `pipeline/recipes/effects-gl-flush-state-20261017-v1/{run_check.py,install.py}` ; `install.py prepare` puis `install.py install` utilisés. Les reçus existent : ne pas relancer pour les écraser.
- Retest utilisateur : mêmes CLUA58 /397profils dans `effects/installations/lot58-7b-x4-nearest30-20261017-v1/` ; enchainer plusieurs invocations pour exercer le recyclage. Aucune QA d'asset déduite.
- Retour arrière, jeu/InfinityLoader arrêtés :

```powershell
python -B engine/InfinityEngine-Enhancer/source-patchee/tools/install_renderer_candidate.py restore engine/InfinityEngine-Enhancer/installations/effects-gl-flush-state-20261017-v1/backups/20261017T131615101741Z-c8e28643/renderer-install-receipt.json
```
