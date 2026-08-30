# BG2 Upscale

Workspace de production pour les cartes, animations de décor, sprites, interface et installateur
de Baldur's Gate II: Enhanced Edition. Le dépôt Git doit contenir le **plan de contrôle** : code,
tests, catalogues, manifests et documentation canonique. Les images intermédiaires, runs, builds,
backups et paquets générés constituent le **plan de données** et sont ignorés par défaut.

## Commencer ici

Choisir un seul domaine, lire son point d'entrée, puis rester dans ce domaine sauf dépendance
explicitement documentée.

| Tâche | Point d'entrée | Méthode actuelle |
|---|---|---|
| Maps TIS/PVRZ | [`pipeline/README.md`](pipeline/README.md) | préflight → SeedVR2 7B/LAB x4 → build → verify → QA |
| Animations BAM | [`animations/README.md`](animations/README.md) | x4 spatial, TimedTimeline 30 fps et registre par occurrence v3 |
| Sprites complexes | [`sprite/README.md`](sprite/README.md) | inventaire normalisé → job xN → catalogue cumulatif → install/restore |
| Interface/HUD | [`interface/README.md`](interface/README.md) | remplacement runtime d'atlas DXT5, Topaz Recovery v2 x4 validé pour les menus |
| Moteur/DLL | [`engine/InfinityEngine-Enhancer/source-patchee/README.md`](engine/InfinityEngine-Enhancer/source-patchee/README.md) | manifests de build, hooks fail-closed et tests C++ |
| Installer/release | [`releases/BG2-HD-Upscale/docs/INSTALLER_AND_UPSCALE_WORKFLOW.md`](releases/BG2-HD-Upscale/docs/INSTALLER_AND_UPSCALE_WORKFLOW.md) | manifests source → payload WeiDU → package, après autorisation explicite |
| Suivi transversal | [`docs/GLOBAL_ASSET_REGISTRY.md`](docs/GLOBAL_ASSET_REGISTRY.md) | projection générée à cinq axes depuis les sources métier, sans registre concurrent |
| Inventaire graphique complémentaire | [`docs/GRAPHICS_INVENTORY.md`](docs/GRAPHICS_INVENTORY.md) | KEY/BIF/WBM → autorités minimales → projection globale, sans upscale |
| Intégrité physique | [`docs/WORKSPACE_INTEGRITY.md`](docs/WORKSPACE_INTEGRITY.md) | disque ↔ autorités ↔ registre ↔ runs, avec index généré non autoritatif |
| Décisions et essais rejetés | [`docs/DECISIONS.md`](docs/DECISIONS.md) | mémoire technique concise |
| Blocages actuels | [`pipeline/PROBLEMES_A_RESOUDRE.md`](pipeline/PROBLEMES_A_RESOUDRE.md) | uniquement les problèmes non résolus |

Les portraits, vidéos et outils de publication sont des domaines auxiliaires. Lire leur README
local avant toute action ; ils ne font pas partie du pipeline maps par défaut.

La base [`BG2EE_Documentation_Modders_FR`](BG2EE_Documentation_Modders_FR/README.md) fournit la
référence technique générale BG2:EE/Infinity Engine. Elle se consulte ponctuellement depuis son
[`INDEX.md`](BG2EE_Documentation_Modders_FR/INDEX.md), selon la règle de lecture ciblée et l'ordre
d'autorité définis dans [`AGENTS.md`](AGENTS.md) ; elle ne fait pas partie des lectures initiales
systématiques.

## Architecture

```text
KEY/BIF/WED/TIS/BAM
        │
        ├─ maps          extraction x1 → upscale → reconstruction → QA
        ├─ animations    extraction BAM → frames x4/30 fps → pack runtime
        ├─ sprite        inventaire → familles/jobs → catalogue xN
        ├─ interface     éléments UI → atlas DXT5 → remplacement runtime
        ├─ engine        DLL, hooks, manifests de builds et tests natifs
        └─ releases      sélection validée → WeiDU → package distribuable
```

`pipeline/scripts/` reste volontairement plat pour préserver les imports et les jobs existants.
Son [`README.md`](pipeline/scripts/README.md) classe les points d'entrée par domaine. Ne déplacer
pas ces scripts sans migration explicite des imports, jobs JSON et installateurs.

## Sources de vérité

| Décision | Source canonique |
|---|---|
| État et run courant d'une map | [`areas.csv`](areas.csv) |
| Inventaire animations | `animations/index/manifest.json` et CSV adjacents |
| Validation spatiale animation | `animations/index/animation_upscale_registry.csv` |
| Validation temporelle d'un run | son `qa-approval.json` immuable |
| Éligibilité et layout sprites | `sprite/index/manifest.json`, `sprite-layout.json`, `path-migrations.json` et CSV |
| Génération sprite courante | `current-generation.json` et `active-test.json` du catalogue |
| Vidéos, HUD, UI complémentaire, polices, icônes, curseurs, effets et projectiles | index détaillés dans [`docs/GRAPHICS_INVENTORY.md`](docs/GRAPHICS_INVENTORY.md) |
| Compatibilité moteur | `engine/.../src/iee/game/build_manifest.*` et `docs/validation/` |
| État de la release | `releases/BG2-HD-Upscale/manifests/release.json` |
| Contenu généré du paquet | `releases/BG2-HD-Upscale/manifests/content.json` — ne jamais éditer à la main |
| Convention d'agrégation (non autoritative) | [`docs/ASSET_TRACKING_CONTRACT.md`](docs/ASSET_TRACKING_CONTRACT.md) |
| Vue globale générée (non autoritative) | [`asset-tracking/registry.json`](asset-tracking/registry.json), [vue CSV](asset-tracking/registry.csv), [couverture](asset-tracking/coverage.json) et [anomalies](asset-tracking/anomalies.json) |
| Vue physique générée (non autoritative) | [`asset-tracking/workspace-integrity.json`](asset-tracking/workspace-integrity.json), [index des runs](asset-tracking/runs.json) et [vue CSV](asset-tracking/runs.csv) |
| Décisions et échecs connus | [`docs/DECISIONS.md`](docs/DECISIONS.md) |

Ne jamais déduire un état courant depuis `override`, une capture, `runs/`, `proto/`, `backups/`,
`temp/`, `_rollback/` ou un package développé.

## Actif, expérimental, archive et généré

- **Actif** : points d'entrée ci-dessus, `pipeline/scripts`, `pipeline/tests`, index, catalogues,
  manifests, schemas et sources moteur.
- **Expérimental** : `proto/`, dossiers `research/`, variantes nommées `test`, `trial` ou
  `pending-qa`. Les travaux animation, même expérimentaux, vont sous `animations/runs/`; ils ne
  deviennent jamais une méthode courante sans gate et décision documentée.
- **Archive/legacy** : `archive/`, `docs/archive/` et dossiers `archive/`
  locaux. Ils sont exclus de la recherche initiale ; consulter d'abord `docs/DECISIONS.md`.
- **Généré/temporaire** : `runs/`, `.work/`, builds CMake, `temp/`, `tmp/`, `outputs/`, payloads,
  staging, ZIP et backups. Ces chemins sont ignorés par Git. Le registre `asset-tracking/` est une
  exception versionnée : il reste entièrement régénérable et ne constitue jamais une autorité.

Les snapshots d'installateur déplacés pendant l'assainissement sont conservés sous
`G:/AI/BG2_Upscale-artifacts/pre-cleanup-20260827/`. Les sorties et aperçus historiques sont sous
`G:/AI/BG2_Upscale-data/archive-pre-cleanup-20260827/`. Les runs et packs supersédés lors de la
finalisation sont sous `G:/AI/BG2_Upscale-data/archive-post-release-20260827/`; son `MANIFEST.csv`
permet une restauration ciblée. Ces emplacements locaux ne sont pas des sources de vérité.

## Gates communs

1. Lire `AGENTS.md`, ce README, puis le README du domaine.
2. Vérifier le statut dans le catalogue canonique et les problèmes ouverts.
3. Fermer le jeu et InfinityLoader avant toute installation ou restauration.
4. Travailler dans un nouveau run ; ne jamais modifier un artefact scellé.
5. Exécuter les tests légers du domaine et les vérifications de manifests.
6. Une capture, un fichier d'`override` ou un résultat `pending-qa` ne vaut pas
   `validated-installed`.
7. La mise à jour du catalogue et l'intégration au manifeste de release sont deux décisions
   distinctes.

## Tests légers

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s pipeline/tests -p "test_*.py"
```

Pour le moteur :

```powershell
cmake -S engine/InfinityEngine-Enhancer/source-patchee `
  -B engine/InfinityEngine-Enhancer/source-patchee/cmake-build-test `
  -DBUILD_TESTING=ON
cmake --build engine/InfinityEngine-Enhancer/source-patchee/cmake-build-test --target iee_tests
ctest --test-dir engine/InfinityEngine-Enhancer/source-patchee/cmake-build-test --output-on-failure
```

Ne pas lancer SeedVR, Topaz, un build complet de contenu ou un packaging pour un simple test de
structure.

## Blocages à ne pas masquer

Les sélections maps, les composants, les overlays et la compatibilité animation v2/v3 sont
désormais vérifiés par les manifests et la Phase 2. Les défauts ingame encore ouverts — eau,
WTPOOL, contours alpha et zones `pending-qa` — restent exclusivement dans
[`pipeline/PROBLEMES_A_RESOUDRE.md`](pipeline/PROBLEMES_A_RESOUDRE.md).
