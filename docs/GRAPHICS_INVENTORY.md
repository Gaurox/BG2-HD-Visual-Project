# Inventaires graphiques

## Autorités

| Domaine | Index canonique |
|---|---|
| Vidéos | `video/index/manifest.json`, `resources.csv`, `processing.csv` |
| HUD | `interface/gameplay-hud-bg2ee/index/manifest.json`, `resources.csv`, `dependencies.csv` |
| Polices | `interface/fonts/index/manifest.json`, `resources.csv` |
| Interface transversale | `interface/index/manifest.json`, `resources.csv`, `dependencies.csv` |
| Menus | `interface/menus-options-bg2ee/reference/extraction-manifest.json` |
| Sprites UI x4 | `interface/menus-options-bg2ee/x4-topaz-recovery-v2-d50/sprite-manifest.json` |
| Sélecteur | `interface/menus-options-bg2ee/x4-topaz-recovery-v2-d50/selection-des-trois-jeux/assets/asset-manifest.json` |
| Icônes | `icons/index/manifest.json`, `resources.csv`, `usages.csv` |
| Curseurs | `cursors/index/manifest.json`, `resources.csv` |
| Effets | `effects/index/manifest.json`, `resources.csv`, `dependencies.csv` |
| Projectiles | `projectiles/index/manifest.json`, `resources.csv`, `dependencies.csv` |
| Compléments BAM | `graphics/index/supplemental-manifest.json`, `supplemental-assets.csv` |
| Portraits | `portraits/inventaire_portraits.csv` ; une base logique, tailles L/M/S dépendantes |

Animations, sprites et cartes conservent leurs autorités propres ; voir [`../AGENTS.md`](../AGENTS.md).
L'état de release provient exclusivement des manifestes sous `releases/BG2-HD-Upscale/manifests/`.

## Régénération et lecture

```powershell
python pipeline/scripts/workspace.py refresh --changed
```

La commande planifie sans écrire. Si `graphics` est proposé, demander le choix de reconstruction
avant `workspace.py refresh --scope graphics --run`; ajouter `registry`/`integrity` seulement s'ils
sont proposés ou demandés. Les inventaires sont déterministes et refusent les catégories inconnues.
`--verify-determinism` double le coût et reste explicite. Les quantités courantes se lisent dans
`asset-tracking/coverage.json` ; elles ne sont pas recopiées ici.
