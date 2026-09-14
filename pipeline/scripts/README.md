# Scripts du pipeline

Les scripts restent dans ce dossier plat afin que les imports, tests et commandes historiques
restent stables. Utiliser `--help` comme référence lorsqu'il est disponible.

## Entrées principales

| Besoin | Script |
|---|---|
| Tests locaux par convention de nom | `test_changed.py` |
| Inventaires graphiques | `build_graphics_inventory.py` |
| Maîtres/préflight de carte | `validate_x1_masters.py`, `audit_area_preflight.py` |
| Extraction | `batch_extract.py`, `batch_extract_secondary.py`, `render_secondary.py` |
| Job SeedVR | `run_seedvr_comfyui.py` |
| Upscale vidéo SeedVR2 LAB 1080p | `run_video_upscale.py` |
| Interpolation vidéo Apollo 8 30 fps | `run_video_interpolation.py` |
| Build/contrôle map | `build_upscaled_area.py`, `verify_upscaled.py` (structure uniquement) |
| Eau et overlays | `orchestrate_water_batch.py` (plan-only), `build_water_route1_batch.py`, `repair_water_secondary_alpha_seams.py`, `assemble_water_qa_batches.py`, `audit_water_area.py`, `audit_water_ingame_tracking.py`, `build_spline_map_alpha.py`, `render_liquid_overlay_mask.py`, `build_water_contour_feather.py` |
| Installation/restauration | `inject_build.py` |
| Inventaire animations | `extract_area_animations.py`, `list_animations.py` |
| Upscale animations | `run_animation_upscale.py`, `run_animation_upscale_30fps_v2.py` |
| Suivi animation, QA et sélection | `animation_workflow.py` |
| Acceptation candidat animation | `animation_release.py` ; projections différées par défaut |
| Interpolation | `run_animation_interpolation.py` |
| Packs par zone/occurrence | `split_animation_pack_by_area.py`, `combine_area_pack_splits.py`, `merge_area_pack_resources.py` |
| Essai transactionnel d'animation par zone | `Install-AreaAnimation-AreaTest.ps1`, `Restore-AreaAnimation-AreaTest.ps1` ; cœur `../area-animation-area-test/` |
| Migration d'un ARE embarqué dans une sauvegarde test | `patch_save_area_animation_resrefs.py` ; plan-only, sauvegarde complète obligatoire |
| Correctifs alpha/RGB | `build_alpha_feather.py` (silhouette, canvas, radial, gaussien local haut), `build_spline_top_reconstructed_alpha.py` (Fit 1 + bande haute), `build_manual_alpha_mask_30fps_v2.py`, `build_per_frame_spline_alpha_30fps_v2.py`, `build_blended_rgb_neutral_pack.py`, `build_joint_animation_rgb_seam.py`, `build_fused_area_animation_carrier.py` |
| Sprites xBR | `run_creature_sprite_x2.py`, `generate_sprite_family_append.py`, `xbr2x_batch.js` |
| Sprites ReboutCX | `reboutcx_full.py` (composant), `reboutcx_catalog.py` (catalogue dérivé) |
| Installation sprites | `Install-CreatureSprite-XN-Catalog-Test.ps1`, `Restore-CreatureSprite-XN-Catalog-Test.ps1` |
| Runtime de développement | `Install-IEE-Runtime-Test.ps1` ; indépendant des assets |
| Finalisation release | `releases/BG2-HD-Upscale/tools/Compile-BG2HD-Release.ps1` |

## Catalogues sprites

xBR est la base canonique. `generate_sprite_family_append.py catalog-append` ajoute de nouveaux IDs
par delta. ReboutCX ne modifie pas cette base : `reboutcx_catalog.py` construit un catalogue complet
dérivé et remplace seulement les couples `(animation_id, component_index)` déclarés. Les
appartenances non ciblées restent xBR.

### Ajout xBR incrémental

Un nouveau lot utilise `bg2-upscale-creature-sprite-xn-catalog-delta-job-v1` et ne contient que
ses nouveaux `members`/`qa.animations`. `parent` épingle la génération acceptée :

```json
"parent": {
  "build_manifest": "<generation>/build/build-manifest.json",
  "build_manifest_sha256": "<SHA256>",
  "catalog_sha256": "<SHA256 du catalogue>"
}
```

`build` lit l'index parent, crée seulement les nouveaux shards, relie les anciens sans les lire et
écrit directement le pointeur installable. Un ID d'animation parent ne peut pas être remplacé par
un delta. Contrôle quotidien : `verify` (métadonnées). Scan de tous les shards, réservé à la
finalisation : `verify --full-verify`.

Créer le delta avec `generate_sprite_family_append.py catalog-append`; répéter `--member-job` pour
grouper un lot. Sans `--catalog-job`, le générateur reprend le `current-generation.json` canonique
et son job de provenance scellé. Il ne consulte jamais l'installation active.

## Commandes communes

```powershell
python pipeline/scripts/<script>.py --help
python pipeline/scripts/test_changed.py --targeted --path pipeline/scripts/<script-modifié>.py
```

La commande planifie sans `--run`, isole le lot courant et ne possède aucun fallback global.
Contrat : [`../../docs/TEST_SELECTION.md`](../../docs/TEST_SELECTION.md).

Les chemins externes viennent de `config/workspace-paths.json` via `workspace_paths.py` ou
`WorkspacePaths.ps1`. Aucun nouveau chemin machine ne doit être codé dans un script ou un guide.

Les scripts archivés et leurs migrations sont décrits par les manifestes JSON sous `docs/`, pas par
une seconde liste narrative ici.
