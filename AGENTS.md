# Reprise agent IA — BG2 Upscale

> La documentation de ce dépôt est une mémoire de solutions, pas un workflow imposé.

## Principe de travail

- Partir de la demande utilisateur et du plus petit périmètre utile.
- Ne jamais exiger la lecture intégrale d'un document. Ouvrir uniquement la rubrique liée au
  symptôme, au format ou à l'outil rencontré.
- Les runbooks, recettes, audits, manifests historiques et commandes sont des aides facultatives.
  Ils ne définissent ni ordre obligatoire, ni préflight, ni gate, ni checklist universelle.
- Une solution connue peut être réutilisée directement si le cas est compatible. Une méthode peut
  être adaptée, remplacée ou ignorée si elle n'aide pas le problème courant.
- Ne produire une preuve, un reçu ou une mise à jour de suivi que lorsqu'elle sert le résultat
  demandé ou enregistre une décision finale. Les essais intermédiaires n'imposent aucune cérémonie.
- Tests, audits, reconstructions et projections ne sont exécutés que sur demande utilisateur ou
  lorsqu'ils sont techniquement nécessaires pour produire l'artefact demandé. Ne pas imposer de
  menu « ciblés / tous / aucun ».

## Démarrage rapide

1. Exécuter seulement `git status --short` pour repérer les changements à préserver.
2. Inspecter les fichiers et références strictement nécessaires au problème.
3. Appliquer la correction la plus directe et vérifier seulement son risque réel.

## Repères facultatifs

| Besoin | Référence |
|---|---|
| Décision ou essai déjà connu | [`docs/DECISIONS.md`](docs/DECISIONS.md) |
| Symptôme encore ouvert | [`pipeline/PROBLEMES_A_RESOUDRE.md`](pipeline/PROBLEMES_A_RESOUDRE.md) |
| Eau : symptôme → solution | [`pipeline/water/VALIDATED_WATER_RECIPES.md`](pipeline/water/VALIDATED_WATER_RECIPES.md) |
| Formats BG2EE | [`BG2EE_Documentation_Modders_FR/INDEX.md`](BG2EE_Documentation_Modders_FR/INDEX.md) |
| Cartes | [`areas.csv`](areas.csv) |
| Animations | [`animations/index/`](animations/index/) |
| Sprites | [`sprite/index/`](sprite/index/) |
| Release | [`releases/BG2-HD-Upscale/manifests/release.json`](releases/BG2-HD-Upscale/manifests/release.json) |

Les fichiers `asset-tracking/registry.*`, `coverage.json`, `anomalies.json`,
`workspace-integrity.json` et `runs.*` sont des projections facultatives et régénérables, jamais
des prérequis à une correction locale.

## Garde-fous irréductibles

- Préserver les changements utilisateur hors périmètre.
- Ne pas modifier une autre map, variante jour/nuit ou famille sans demande explicite.
- Fermer le jeu et InfinityLoader avant de remplacer des fichiers installés.
- Ne jamais déduire une validation ingame ou une intégration release.
- Ne pas modifier payload, staging, `content.json`, TP2, archive ou manifeste release sans demande
  explicite.
- Les artefacts déjà désignés comme preuves finales ou historiques restent immuables ; créer une
  nouvelle version seulement si leur remplacement est réellement nécessaire.

## Site public séparé

- URL : `https://bg2hd.gaurox.dev/`.
- Dépôt : `https://github.com/Gaurox/bg2-hd-website.git`.
- Checkout canonique : `config://website_checkout`.
- Ne pas recréer le site dans ce dépôt. Détails facultatifs : [`docs/WEBSITE.md`](docs/WEBSITE.md).
