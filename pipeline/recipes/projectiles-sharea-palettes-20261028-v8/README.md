# Raccord SHAREA V8

- `generate_palette_data.py` lit le BAM source etles6BMP natifs,écrit seulement constantesC++/fixtures ; `source-palettes.json` fige leursSHA. Aucune génération d’image.
- `core/effect_indexed_palette.h` : transfertRGB depuis palette réalisée,points source exacts/noir neutre,interpolation des autres couleurs ; alpha uniforme ; fingerprintcouleur/opacité. `effect_sharea_source_palette.h` lie la palette de base auSHA du BAM. ScopeSHAREA uniquement.
- `hooks.cpp` :capture palette par cellule réelle,scopesimbriqués préservés,gardeBlended/palette/mono-couche ; `EFX_PALETTE_BOUND` limité16fingerprints ettracephaseSHAREA. `effect_animation_x4_registry.*` :copieupload privée,cléGPU séparée,exclusion des transferts simultanés.
- Tests : sept palettes exactes aux255points opaques/noirs,encodages,identité,alpha,rejetgradientalpha ;OpenGLcouleurs3/5/6/3 vsneutre,cache/étatGL inchangés ; suitesprécédentesfumées/alias/masques.
- `install.py prepare|install` déjà exécuté ; reçu `engine/InfinityEngine-Enhancer/installations/projectiles-sharea-palettes-20261028-v8/`. DLLseule,pack/carriers/projetiles/gameplay préservés.
- [Prochaine QA](../../../projectiles/analysis/sharea-palettes-preparation-20261028-v1/README.md) : cinq commandes,aucunevalidation globale déduite.
