# Sélection des tests

## Commandes

```powershell
python pipeline/scripts/test_changed.py --changed --list
python pipeline/scripts/test_changed.py --changed
python pipeline/scripts/test_changed.py --full
```

`--changed` est le défaut. Il lit les modifications suivies, indexées et non suivies. `--base <ref>`
compare aussi `ref...HEAD` pour la CI. `--list` n'exécute rien. `--json` fournit le plan structuré.

## Groupes

| Groupe | Déclencheurs principaux |
|---|---|
| `smoke` | toujours : commande workspace et résolution des chemins |
| `documentation` | Markdown et points d'entrée agent |
| `maps`, `map-diagnostics` | cartes, WED, injection, PVRZ diagnostique |
| `animations` | inventaire, upscale, timeline, packs et transactions animation |
| `sprite-inventory` | index et générateurs de jobs/familles |
| `sprite-formats` | runner, registres et catalogues |
| `sprite-installation` | installateur/restaurateur du catalogue cumulatif |
| `graphics-inventory` | UI, portraits, vidéos, icônes, curseurs, effets, projectiles |
| `registry`, `integrity` | contrat global, projections, runs, hashes, migrations |
| `renderer-transaction` | candidat renderer transactionnel |
| `release`, `engine` | Phase 2 release et CTest moteur |

Le sélecteur travaille au niveau module : aucun test individuel n'est retiré d'un groupe.

## Fallback complet

Suite complète obligatoire pour : chemin inconnu, rename/delete, dépendance ou configuration
transversale, infrastructure de tests/CI, runtime moteur, Core, release, packaging ou classification
ambiguë. La CI l'exécute aussi chaque semaine, manuellement et sur tag.

`--full` exécute tous les tests Python, puis `workspace.py check --after-full-tests` en mono-passe :
les modules d'inventaire, registre et intégrité ont déjà vérifié leur déterminisme. Phase 2 et CTest
sont ensuite exécutés. Les gates de staging/archive restent soumises à l'autorisation explicite du
workflow release.
