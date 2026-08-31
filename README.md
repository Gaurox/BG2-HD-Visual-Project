# BG2 Upscale

> **Règle documentaire : écrire pour des agents IA — concis, factuel, opérationnel, non narratif. Éviter la verbosité et les répétitions. Toute nouvelle documentation ou modification doit privilégier la densité d’information, les listes/tableaux, les chemins et commandes précises. Éviter la prose longue, le contexte narratif, les répétitions et les explications principalement destinées à un lecteur humain.**

Workspace de production BG2EE. Git contient le plan de contrôle ; médias, runs, builds, backups et
packages lourds constituent le plan de données.

Pour une reprise par agent IA, commencer par [`AGENTS.md`](AGENTS.md). Il définit les autorités,
les projections générées, les règles de provenance et les contrôles globaux.

## Domaines

| Tâche | Point d'entrée |
|---|---|
| Maps TIS/PVRZ | [`pipeline/README.md`](pipeline/README.md) |
| Animations BAM | [`animations/README.md`](animations/README.md) |
| Sprites complexes (`sprite/index/` est l'autorité) | [`sprite/README.md`](sprite/README.md) |
| Interface/HUD | [`interface/README.md`](interface/README.md) |
| Vidéos WBM | [`video/README.md`](video/README.md) |
| Moteur/DLL | [`engine/InfinityEngine-Enhancer/source-patchee/README.md`](engine/InfinityEngine-Enhancer/source-patchee/README.md) |
| Installer/release | [`releases/BG2-HD-Upscale/docs/INSTALLER_AND_UPSCALE_WORKFLOW.md`](releases/BG2-HD-Upscale/docs/INSTALLER_AND_UPSCALE_WORKFLOW.md) |
| Décisions | [`docs/DECISIONS.md`](docs/DECISIONS.md) |
| Problèmes ouverts | [`pipeline/PROBLEMES_A_RESOUDRE.md`](pipeline/PROBLEMES_A_RESOUDRE.md) |

Les portraits et inventaires transversaux sont routés depuis `AGENTS.md`. La documentation des formats
BG2EE se consulte à la demande depuis
[`BG2EE_Documentation_Modders_FR/INDEX.md`](BG2EE_Documentation_Modders_FR/INDEX.md).
