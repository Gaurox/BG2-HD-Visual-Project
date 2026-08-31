# BG2 Upscale

Workspace de production BG2EE pour maps, animations, sprites, interface, moteur et release. Git
contient le plan de contrôle (code, tests, catalogues, manifests, documentation) ; les médias,
runs, builds, backups et packages lourds constituent le plan de données.

Pour une reprise par agent IA, commencer par [`AGENTS.md`](AGENTS.md). Il définit les autorités,
les projections générées, les règles de provenance et les contrôles globaux.

## Domaines

| Tâche | Point d'entrée |
|---|---|
| Maps TIS/PVRZ | [`pipeline/README.md`](pipeline/README.md) |
| Animations BAM | [`animations/README.md`](animations/README.md) |
| Sprites complexes (`sprite/index/` est l'autorité) | [`sprite/README.md`](sprite/README.md) |
| Interface/HUD | [`interface/README.md`](interface/README.md) |
| Moteur/DLL | [`engine/InfinityEngine-Enhancer/source-patchee/README.md`](engine/InfinityEngine-Enhancer/source-patchee/README.md) |
| Installer/release | [`releases/BG2-HD-Upscale/docs/INSTALLER_AND_UPSCALE_WORKFLOW.md`](releases/BG2-HD-Upscale/docs/INSTALLER_AND_UPSCALE_WORKFLOW.md) |
| Contrat de suivi | [`docs/ASSET_TRACKING_CONTRACT.md`](docs/ASSET_TRACKING_CONTRACT.md) |
| Registre global | [`docs/GLOBAL_ASSET_REGISTRY.md`](docs/GLOBAL_ASSET_REGISTRY.md) |
| Inventaires graphiques complémentaires | [`docs/GRAPHICS_INVENTORY.md`](docs/GRAPHICS_INVENTORY.md) |
| Intégrité physique et runs | [`docs/WORKSPACE_INTEGRITY.md`](docs/WORKSPACE_INTEGRITY.md) |
| Décisions | [`docs/DECISIONS.md`](docs/DECISIONS.md) |
| Problèmes ouverts | [`pipeline/PROBLEMES_A_RESOUDRE.md`](pipeline/PROBLEMES_A_RESOUDRE.md) |

Les portraits et vidéos possèdent aussi un README local. La documentation générale des formats
BG2EE se consulte à la demande depuis
[`BG2EE_Documentation_Modders_FR/INDEX.md`](BG2EE_Documentation_Modders_FR/INDEX.md).

## Flux global

```text
sources BG2EE
  → autorités métier par domaine
  → productions/runs avec provenance
  → QA explicite
  → installation vérifiée
  → décision release séparée
  → projections jetables dans asset-tracking/
```

`pipeline/scripts/` reste plat pour préserver les imports et les jobs existants. Son
[`README.md`](pipeline/scripts/README.md) classe les points d'entrée.

## Commandes essentielles

```powershell
# Lecture seule : inventaires, registre, disque, runs, chemins et documentation
python pipeline/scripts/workspace.py check

# Régénération déterministe des inventaires complémentaires et projections
python pipeline/scripts/workspace.py refresh

# Suite commune
python -m unittest discover -s pipeline/tests -p "test_*.py"
```

Ne pas utiliser un run, `override`, une capture, `proto/`, `archive/`, `backups/`, `temp/` ou un
package comme source d'état. Ne pas lancer d'inférence ou de packaging pour un contrôle de
structure.
