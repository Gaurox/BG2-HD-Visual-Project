# Scripts du pipeline

Les scripts restent dans ce dossier plat afin que les imports, tests et commandes historiques
restent stables. Utiliser `--help` comme référence lorsqu'il est disponible.

## Entrées principales

| Besoin | Script |
|---|---|
| Contrôle/régénération globale | `workspace.py` |
| Sélection de tests Git | `test_changed.py` |
| Inventaires graphiques | `build_graphics_inventory.py` |
| Maîtres/préflight de carte | `validate_x1_masters.py`, `audit_area_preflight.py` |
| Extraction | `batch_extract.py`, `batch_extract_secondary.py`, `render_secondary.py` |
| Job SeedVR | `run_seedvr_comfyui.py` |
| Reconstruction/audit de carte | `build_upscaled_area.py`, `verify_upscaled.py` |
| Eau et overlays | `audit_water_area.py`, `build_spline_map_alpha.py`, `render_liquid_overlay_mask.py`, `build_water_contour_feather.py` |
| Installation/restauration | `inject_build.py` |
| Inventaire animations | `extract_area_animations.py`, `list_animations.py` |
| Upscale animations | `run_animation_upscale.py`, `run_animation_upscale_30fps_v2.py` |
| Interpolation | `run_animation_interpolation.py` |
| Packs par zone/occurrence | `split_animation_pack_by_area.py`, `combine_area_pack_splits.py`, `merge_area_pack_resources.py` |
| Correctifs alpha/RGB | `build_alpha_feather.py`, `build_blended_rgb_neutral_pack.py` |
| Sprites | `run_creature_sprite_x2.py`, `build_sprite_inventory.py`, `xbr2x_batch.js` |
| Release | `releases/BG2-HD-Upscale/tools/*.ps1` |

## Commandes communes

```powershell
python pipeline/scripts/<script>.py --help
python pipeline/scripts/test_changed.py --changed --list
python pipeline/scripts/test_changed.py --changed
python pipeline/scripts/test_changed.py --full
```

Les chemins externes viennent de `config/workspace-paths.json` via `workspace_paths.py` ou
`WorkspacePaths.ps1`. Aucun nouveau chemin machine ne doit être codé dans un script ou un guide.

Les scripts archivés et leurs migrations sont décrits par les manifestes JSON sous `docs/`, pas par
une seconde liste narrative ici.
