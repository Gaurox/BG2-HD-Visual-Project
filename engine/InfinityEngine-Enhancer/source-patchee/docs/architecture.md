# Architecture

## Frontières

- Une DLL EEex Windows ; adresses et capacités résolues depuis `build_manifest.*`.
- Hooks minces : résolution/validation, puis dispatch vers un module propriétaire.
- État borné et réinitialisé par zone ou contexte WGL.
- OpenGL et objets moteur mutables restent sur leur thread propriétaire ; voir
  [`threading-model.md`](threading-model.md).
- Une signature absente/ambiguë ou un format invalide désactive la fonction concernée.
- `ShutdownBindings` précède tout `FreeLibrary`; aucun teardown depuis `DllMain`.

## Modules

| Module | Responsabilité |
|---|---|
| `game/build_manifest.*` | identités d'exécutables, patterns, RVA de référence, offsets et callsites |
| `game/game_addrs.*` | scan PE et résolution unique des fonctions moteur |
| `hooks.*` | cycle de vie des hooks et dispatch `LoadArea`/rendu |
| `area_state.*` | zone active, transform, snapshot WED générationnel et file d'upload |
| `features/tile_render.*` | échelle des tuiles, cache par zone, signal final BRIDGE01 |
| `game/tile_upscale.*`, `tis_runtime.*` | détection d'échelle et vues runtime TIS/PVR |
| `game/tis_palette.*`, `tile_liquid.*` | transparence palette, classification et teinte des liquides |
| `game/area_texture.*` | masque R8 des cellules liquides |
| `game/dds_texture.*`, `water_textures.*` | validation DDS et objets GL des textures d'eau |
| `game/renderer.*` | points de dessin et cache borné de configuration texture |
| `shader_probe.*`, `shader_uniform_bridge.*` | hooks GL, classification de shader et uniforms |
| `game/shader_override.*` | validation du contrat de `fpSEAM.glsl` |
| `frame_hook.*` | frontière de frame et tick de récupération |
| `area_animation_x4_registry.*` | packs v1/v2/v3, timeline et cache des animations |
| `native_occlusion_bridge.*` | transfert borné de l'occlusion native vers le rendu x4 |
| `creature_sprite_x2.*` | catalogue/shards et composition palette des sprites pris en charge |
| `bridge_transition.*` | transition AR1300/BRIDGE01 |
| `map_page_prewarm.*` | télémétrie et prototype B2f, par défaut désactivé |
| `diagnostics.*`, `shader_diagnostics.*` | logs et preuves optionnelles |

Les structures disque/runtime exactes sont centralisées dans `game/file_formats.h`,
`runtime_types_x64.h` et `eeex_doc_layouts_x64.h`, au lieu d'être dupliquées dans les hooks.

## Contrats de rendu

- Header TIS prioritaire ; table PVR pour les wrappers sans header ; heuristique UV/id en dernier.
- Le masque liquide compact borne les cellules ; l'alpha de la tuile conserve le contour auteur.
- Les teintes PVRZ sont lues sur le thread de rendu depuis une identité WED/PVR vérifiée ; sinon le
  fallback exact-resref ou neutre s'applique.
- Les packs animation par zone se chargent après `LoadArea`; une zone absente retombe sur vanilla.
- Les textures sortantes sont retirées lors d'une passe GL, pas depuis le hook de chargement.
- Le chemin sprite échoue vers le sprite natif si une couche, palette, shard ou classe diverge.

## Graphe CMake

| Cible | Rôle |
|---|---|
| `iee_common` | code hôte testable hors Windows |
| `InfinityEngine-Enhancer` | DLL Windows, MinHook/psapi/OpenGL |
| `iee_tests` | tests hôte |
| `iee_bridge_worker_tests` | tests Windows du worker vidéo |
| `iee_map_page_shadow_preflight` | validation PVRZ hors jeu |
| `release_bundle` | layout complet du renderer |

`cmake --install` reproduit le layout du bundle. Les prototypes archivés ne participent ni au
build ni à l'état runtime.
