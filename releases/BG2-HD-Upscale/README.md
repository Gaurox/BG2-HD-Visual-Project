# BG2 HD Upscale — release

> **Règle documentaire : écrire pour des agents IA — concis, factuel, opérationnel, non narratif. Éviter la verbosité et les répétitions. Toute nouvelle documentation ou modification doit privilégier la densité d’information, les listes/tableaux, les chemins et commandes précises. Éviter la prose longue, le contexte narratif, les répétitions et les explications principalement destinées à un lecteur humain.**

Source de l'installeur WeiDU `bg2hd` pour BG2EE Steam 2.7.3.0, Windows x64. Ce dossier n'est ni
l'`override` de développement ni un dépôt d'archives construites.

[`manifests/release.json`](manifests/release.json) est l'autorité de version, de cible et de statut.
La release courante reste `blocked` et son payload `not-buildable` tant que ses conditions ne sont
pas levées. Les quantités de fichiers/composants se lisent dans `content.json` et `components.json`;
elles ne sont pas recopiées ici.

## Lecture

- Utilisateur : [`README_FR.md`](README_FR.md) ou [`README_EN.md`](README_EN.md).
- Agent d'intégration :
  [`docs/INSTALLER_AND_UPSCALE_WORKFLOW.md`](docs/INSTALLER_AND_UPSCALE_WORKFLOW.md).
- Contrats : [`docs/MANIFESTS.md`](docs/MANIFESTS.md),
  [`docs/TESTING.md`](docs/TESTING.md),
  [`docs/DEPENDENCY_BOOTSTRAP.md`](docs/DEPENDENCY_BOOTSTRAP.md).
- Exploitation : [`docs/STEAM_INTEGRATION.md`](docs/STEAM_INTEGRATION.md),
  [`docs/RECOVERY.md`](docs/RECOVERY.md),
  [`docs/COMPATIBILITY.md`](docs/COMPATIBILITY.md).
- Diffusion : [`docs/LICENCES.md`](docs/LICENCES.md),
  [`docs/DISTRIBUTION_POLICY.md`](docs/DISTRIBUTION_POLICY.md).
- Suivi : [`CHANGELOG.md`](CHANGELOG.md), [`KNOWN_ISSUES.md`](KNOWN_ISSUES.md).

Payload, staging, `content.json` et archive ne sont reconstruits qu'après accord explicite prévu
par le workflow d'intégration.
