# Scripts — index opérationnel

Le dossier reste plat afin de ne pas casser les imports locaux, jobs JSON et installateurs. Pour
une tâche, utiliser seulement le groupe correspondant. Les scripts non listés sont des outils de
diagnostic ou des éléments `REVIEW`; rechercher leurs références avant emploi.

## Maps

- Bibliothèques : `bg2lib.py`, `mos_decode.py`, `area_decode.py`.
- Extraction : `batch_extract.py`, `batch_extract_secondary.py`, `render_secondary.py`.
- Qualification : `validate_x1_masters.py`, `audit_area_preflight.py`, `audit_water_area.py`.
- Upscale : `run_seedvr_comfyui.py`.
- Reconstruction : `build_upscaled_area.py`, `verify_upscaled.py`.
- Installation/restauration des builds TIS/PVRZ : `inject_build.py` prévalide l'inventaire complet,
  sauvegarde l'état initial dans un reçu hashé, installe atomiquement, retire les anciennes pages du
  même namespace et restaure en mode fail-closed. Utiliser d'abord `install ... --verify-only`, puis
  conserver le dossier `backups/maps/<transaction>/` jusqu'à la restauration vérifiée.
- Expérience de latence PVRZ : `repack_pvrz_compression.py` réécrit uniquement le flux Deflate
  dans un nouveau dossier, avec TIS et PVR décodés identiques. Le niveau doit être explicite ; la
  sortie reste `pending-ingame` et ne remplace jamais le build sélectionné par `areas.csv`.
- Repagination DXT exacte : `repage_pvrz_blocks.py` recopie les cellules DXT avec leur padding
  répliqué, réécrit uniquement les coordonnées/pages du TIS et refuse toute cellule divergente.
  La taille cible, le plafond de pages et le niveau zlib sont explicites ; la sortie reste
  `completed-pending-ingame` dans un nouveau dossier.
- Benchmark PVRZ hors jeu : `benchmark_pvrz_decode.py` précharge les flux, effectue un warm-up puis
  mesure plusieurs décompressions zlib en mémoire. Il sert à trier des candidats, jamais à
  remplacer une mesure de `CResPVR::Demand` ingame.
- Correction native ciblée des flags d'occlusion WED :
  `build_wed_cover_animation_patch.py` (sortie `pending-ingame`, installation réversible avec les
  scripts d'assets auxiliaires).
- Correction locale d'une donnée d'occlusion WED absente à partir d'un masque monde xN :
  `build_wed_mask_polygon_patch.py` (nouveau polygone natif strictement borné, sortie
  `pending-ingame`, source KEY/BIF et rollback vérifiés).
- Catalogue : `refresh_area_catalog.py`.
- Installation réversible d'assets auxiliaires : `Install-AreaOverrideAssets.ps1` et
  `Restore-AreaOverrideAssets.ps1`.

Le batch de 68 zones d'août 2026 est archivé sous `archive/batches/`; ses résultats ne décrivent
pas l'état courant.

## Animations de décor

- Inventaire ARE typé et extraction BAM : `extract_area_animations.py` ; export ciblé :
  `export_bam_frames.py`. L'inventaire distingue BAM/WBM/PVRZ et les palettes ARE externes.
- Spatial V1 : `upscale_animation_frames.py`, `run_animation_upscale.py`,
  `build_animation_runtime_pack.py`.
- Interpolation native : `run_animation_interpolation.py`.
- TimedTimeline V2 : `run_animation_upscale_30fps_v2.py`,
  `build_manual_alpha_mask_30fps_v2.py`.
- Packs par zone : `split_animation_pack_by_area.py`, `combine_area_pack_splits.py`,
  `merge_area_pack_resources.py`, `merge_v2_base_pack.py`.
- Correctifs alpha/RGB : `build_alpha_feather.py` (alpha seul, RGB préservé) ;
  `build_blended_rgb_neutral_pack.py` (RGB nul sous alpha nul, ressources à flag `Blended`).
- Registre : `sync_animation_upscale_registry.py`.
- Installation/restauration : scripts `Install-AreaAnimations-*`, `Restore-AreaAnimations-*` et
  `Set-AreaAnimations-X4-State.ps1`.

## Sprites

- Inventaire : `build_sprite_inventory.py`.
- Jobs : `generate_character_complete_x2_jobs.py`, `generate_sprite_family_append.py`.
- Production/catalogue : `run_creature_sprite_x2.py`.
- Installation/restauration courante : `Install-CreatureSprite-XN-Catalog-Test.ps1` et
  `Restore-CreatureSprite-XN-Catalog-Test.ps1`.

Les variantes AA/xBR4 direct ont été déplacées vers `archive/legacy/sprite-variants/` et ne font
plus partie des tests courants.

## Auxiliaires

Les extracteurs de portraits restent ici pour préserver leurs imports, mais leur procédure est
dans `portraits/README.md`. Les scripts d'analyse couleur, anciennes découpes et prototypes
d'horloge sans appel entrant sont dans `archive/legacy/pipeline-scripts/`.

## Suivi transversal

- `asset_tracking_contract.py` valide les projections jetables du contrat commun et sépare les
  statuts historiques connus. Il n'écrit dans aucun manifeste métier et ne constitue pas un
  registre d'assets.
- `build_global_asset_registry.py` agrège en lecture seule les sources métier déjà fiables, valide
  chaque entrée, puis génère `asset-tracking/registry.{json,csv}`, `coverage.json` et
  `anomalies.json`. Utiliser
  `--verify-determinism` pour régénérer et `--check` pour un contrôle strictement non destructif.
  Le format et les limites sont décrits dans `docs/GLOBAL_ASSET_REGISTRY.md`.
- `build_graphics_inventory.py` inventorie et, avec `--extract`, matérialise les sources stock des
  vidéos, HUD/UI, polices, icônes, curseurs, effets, projectiles et familles BAM complémentaires.
  Les granularités, autorités générées et lacunes conservatrices sont décrites dans
  `docs/GRAPHICS_INVENTORY.md`. Utiliser `--check` pour vérifier les sorties sans les modifier.

## Tests

```powershell
python -m unittest discover -s pipeline/tests -p "test_*.py"
```

Un nouveau script opérationnel doit être ajouté à ce fichier et au README de son domaine, avec un
test ou au minimum un smoke test `--help`.
