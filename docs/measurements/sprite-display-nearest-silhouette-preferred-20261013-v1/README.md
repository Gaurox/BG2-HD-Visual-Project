# Affichage sprites retenu — 2026-10-13

- Choix : nearest RGB intérieur + alpha bilinéaire uniquement au contact de la transparence, 4 taps.
- Source active : `engine/InfinityEngine-Enhancer/source-patchee/assets/shader-suite/creature-hd-common.glsl` ; `templates/fpSprite.glsl` évite le halo RGB natif sur cette voie.
- Génération : `python -B engine/InfinityEngine-Enhancer/source-patchee/tools/build_shader_suite.py --run` ; sorties `assets/override/{fpDraw,fpSprite,fpSELECT}.glsl`.
- Activation : `[Shaders] CreatureSpriteFilter=Nearest`, `[ShaderSuite] Enabled=true`, `[ShaderSuite.CreatureHD] Enabled=true` ; profil neutre conservé.
- Périmètre : RGBA HD x2/x4 enregistrés, gate shader/style actif ; géométrie x1, paperdolls et reconstruction SDF séparés.
- Vérification : `python -B engine/InfinityEngine-Enhancer/source-patchee/tools/test_sprite_minification_gl.py` ; GPU réel, fenêtre cachée, aucune entrée bureau.
- `preferred/` : octets approuvés ingame, immuables ; branches d'essai anciennes présentes dans cette archive seulement. `.gitattributes` préserve leurs SHA-256.
- `nearest-classic/` : référence native de comparaison/restauration, immuable.
- `decision.json`, `confirmation-20261013-v1.json`, reçus datés : faits historiques ; références aux essais non retenus supprimées du disque sur demande utilisateur 2026-10-13.
- Installation/source courantes : `project-integration-20261013-v1.json` ; comparaison GPU : `project-gpu-verification-20261013-v1.json`.
- Aucune production individuelle, DLL, QA historique ou release modifiée.
