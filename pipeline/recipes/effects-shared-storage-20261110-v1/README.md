# Mutualisation exacte des effets — 2026-11-10 v1

- Autorisation : correctif après analyse `effects/research/duplicate-analysis-20261110-v1/`.
- Périmètre : RGBA déjà identiques uniquement ; pas d'harmonisation SeedVR, rognage, compression ou mutualisation des BAM natifs.
- Pack source immuable : `releases/BG2-HD-Upscale/release-inputs/effects/accepted-20261110-v1/`.
- Nouveau pack : `.../accepted-shared-20261110-v1/` ; 71 971 images logiques → 65 849 fichiers RGBA. Registre, ressources et métadonnées logiques inchangés ; SHA de chaque résolution vérifié.
- `pack-receipt.json` : gain RGBA 2 588 515 136 octets ; index lié au registre exact 1 431 440 octets ; gain net stockage images **2 587 083 696 octets**.
- `projection-verification.json` / `staging.json` : 109 512 fichiers, 60 238 832 018 octets ; gain payload **2 587 083 262 octets** après croissance manifeste de 434 octets. 42 877 entrées hors effets strictement inchangées ; staging SHA-256 complet.
- `archive-delta.json` : gain des flux de fichiers DEFLATE6 **553 549 611 octets** (index/manifeste inclus ; conteneur et renderer exclus). L'écart entre deux estimations échantillonnées ne mesure pas ce gain. `size-estimate.json` : archive globale ~24,84Go, plage descriptive 23,28–26,12Go ; archive non construite.
- Moteur : `effect_storage_index.h`, lectures eager + streaming dans `effect_animation_x4_registry.cpp`. Index optionnel ; corruption/version/binding/bornes/chaînes/tailles rejetés. Caches logiques indépendants, palettes/centres/cycles conservés.
- Release locale alpha.9 / renderer alpha.11 ; jeu installé inchangé. Qualification ingame du nouveau stockage et cycle sur jeu propre restent en attente ; anciennes QA images conservées.
- Production : `build_shared_effect_storage.py --source <ancien> --output <nouveau> --receipt <nouveau-reçu>` ; validation : `effect_storage.py --pack <nouveau>`.
- Tests : `pipeline.tests.test_effect_storage`, `test_compose_effect_runtime_packs` ; cinq suites moteur existantes ; `native-loader.log` : 31 668 contrats, budget32Mio respecté (31 785 066 octets avec enveloppe temporaire).
- Finalisation : `prepare_release.py`, `hash_sources.py`, compilateur canonique avec `-PhysicalHashIndexPath`, `stage.py` ; ancien staging conservé sous `archive/payload-alpha8-before-shared-20261110-v1/`.
- `manifests-before.json`, source renderer figée et anciens packs conservés ; aucune installation jeu ni QA visuelle déduite.
- Bilan final : `docs/validation/effects-shared-storage-status-20261110-v1.json` ; écrire via `write_status.py` après succès Phase2. Garde installateur : `installer-guard-package-default.log` (manifeste embarqué par défaut ; absent/alpha.10 refusés, alpha.11 accepté).
