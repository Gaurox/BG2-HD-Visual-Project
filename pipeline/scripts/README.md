# Scripts du pipeline

Les scripts restent dans ce dossier plat afin que les imports, tests et commandes historiques
restent stables. Utiliser `--help` comme référence lorsqu'il est disponible.

## Entrées principales

| Besoin | Script |
|---|---|
| Contrôle/régénération globale | `workspace.py` |
| Sélection de tests Git | `test_changed.py` |
| Interface optionnelle sur tout le worktree | `progress_ui.py` |
| Inventaires graphiques | `build_graphics_inventory.py` |
| Maîtres/préflight de carte | `validate_x1_masters.py`, `audit_area_preflight.py` |
| Extraction | `batch_extract.py`, `batch_extract_secondary.py`, `render_secondary.py` |
| Job SeedVR | `run_seedvr_comfyui.py` |
| Upscale vidéo SeedVR2 LAB 1080p | `run_video_upscale.py` |
| Interpolation vidéo Apollo 8 30 fps | `run_video_interpolation.py` |
| Reconstruction/audit de carte | `build_upscaled_area.py`, `verify_upscaled.py` |
| Eau et overlays | `audit_water_area.py`, `build_spline_map_alpha.py`, `render_liquid_overlay_mask.py`, `build_water_contour_feather.py` |
| Installation/restauration | `inject_build.py` |
| Inventaire animations | `extract_area_animations.py`, `list_animations.py` |
| Upscale animations | `run_animation_upscale.py`, `run_animation_upscale_30fps_v2.py` |
| Suivi animation, QA et sélection | `animation_workflow.py` |
| Promotion animation ciblée vers la release | `animation_release.py` |
| Interpolation | `run_animation_interpolation.py` |
| Packs par zone/occurrence | `split_animation_pack_by_area.py`, `combine_area_pack_splits.py`, `merge_area_pack_resources.py` |
| Essai transactionnel d'animation par zone | `Install-AreaAnimation-AreaTest.ps1`, `Restore-AreaAnimation-AreaTest.ps1` ; cœur `../area-animation-area-test/` |
| Migration d'un ARE embarqué dans une sauvegarde test | `patch_save_area_animation_resrefs.py` ; plan-only, sauvegarde complète obligatoire |
| Correctifs alpha/RGB | `build_alpha_feather.py` (silhouette, canvas, radial, gaussien local haut), `build_spline_top_reconstructed_alpha.py` (Fit 1 + bande haute), `build_manual_alpha_mask_30fps_v2.py`, `build_per_frame_spline_alpha_30fps_v2.py`, `build_blended_rgb_neutral_pack.py`, `build_joint_animation_rgb_seam.py`, `build_fused_area_animation_carrier.py` |
| Sprites | `build_sprite_inventory.py` (inventaire), `extract_sprite_sources.py` (sources BAM dédupliquées, plan-only), `sprite_layout.py` (rangement), `sync_sprite_processing.py` (autorité métier), `run_creature_sprite_x2.py` (production), `xbr2x_batch.js` |
| Release | `releases/BG2-HD-Upscale/tools/*.ps1` |

## Commandes communes

```powershell
python pipeline/scripts/<script>.py --help
python pipeline/scripts/test_changed.py --targeted --path pipeline/scripts/<script-modifié>.py
```

La commande planifie sans `--run` et isole le lot courant. `workspace.py refresh --changed` est
réservé aux jalons/projections/release. `progress_ui.py` reste disponible mais travaille sur tout le
worktree : ne pas l'utiliser pour isoler un lot. Contrats :
[`../../docs/TEST_SELECTION.md`](../../docs/TEST_SELECTION.md) et
[`../../docs/WORKSPACE_INTEGRITY.md`](../../docs/WORKSPACE_INTEGRITY.md).

Les chemins externes viennent de `config/workspace-paths.json` via `workspace_paths.py` ou
`WorkspacePaths.ps1`. Aucun nouveau chemin machine ne doit être codé dans un script ou un guide.

Les scripts archivés et leurs migrations sont décrits par les manifestes JSON sous `docs/`, pas par
une seconde liste narrative ici.
