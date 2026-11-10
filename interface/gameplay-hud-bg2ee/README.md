# HUD de jeu — BG2EE

> **Séquence, mécanisme et critères de passage : [`../README.md`](../README.md).** Ce fichier ne
> décrit que le périmètre et l'état de cette branche.

Branche dédiée à la dernière passe d'amélioration du HUD affiché pendant le jeu.

Référence analysée : `captures/hud-gameplay-reference-20260815-185446.png` (2560×1440).

Périmètre réduit (demande utilisateur 2026-11-10) : colonnes décoratives gauche/droite conservées ;
boutons et petites icônes hors nouvelle production. Cadres/bandeaux horizontaux présentés
(`GMPWMSG0`, `GUWBTP10`, `GUWPKPC0`) finalement conservés après révision utilisateur.
Scène centrale, portraits et texte hors de cette passe.
Décisions : [`../analysis/large-surfaces-20261110-v1/README.md`](../analysis/large-surfaces-20261110-v1/README.md).

État : analyse terminée et production partielle. Le lot `GUILS10`/barre d'outils gauche existe sous
`upscale/x4-topaz-recovery-v2-d50/left-toolbar/`; le reste du HUD demeure non produit. Cette
présence ne vaut ni QA globale, ni installation courante, ni décision de release.
Ce lot historique de boutons est désormais hors du périmètre retenu ; ses fichiers restent conservés.

Les ressources et le plan d'intégration sont consignés dans [`analysis/HUD_RESOURCE_INVENTORY.md`](analysis/HUD_RESOURCE_INVENTORY.md). Les rendus de contrôle extraits depuis les BIF se trouvent dans `reference/`.

L'identité source courante, les hashes et les dépendances PVRZ sont désormais suivis dans
`index/manifest.json`, `index/resources.csv` et `index/dependencies.csv`. Cet inventaire ne modifie
pas l'état de production historique et n'implique aucune QA.

Arborescence prévue pour la production :

- `source/` — export original par texture.
- `upscale/x4-topaz-recovery-v2-d50/` — PNG, alpha et PVRZ de production.
- `integration/` — manifestes, DLL et sauvegardes de test réversibles.
- `comparison/` — captures avant/après.

## Suivi actif

Autorité des travaux retenus : [suivi UI/HUD](../tracking/README.md).
Les inventaires source et anciens packs restent historiques ; leurs boutons/icônes ne sont plus
des travaux actifs. États production, QA, installation et release séparés par ressource.
