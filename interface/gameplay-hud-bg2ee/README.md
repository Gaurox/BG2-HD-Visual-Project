# HUD de jeu — BG2EE

> **Séquence, mécanisme et critères de passage : [`../README.md`](../README.md).** Ce fichier ne
> décrit que le périmètre et l'état de cette branche.

Branche dédiée à la dernière passe d'amélioration du HUD affiché pendant le jeu.

Référence analysée : `captures/hud-gameplay-reference-20260815-185446.png` (2560×1440).

Périmètre : les habillages, cadres et boutons entourant la zone de jeu. La scène centrale, les portraits de personnages, les icônes d'actions/objets et le texte ne sont pas inclus dans cette première passe.

État : analyse terminée et production partielle. Le lot `GUILS10`/barre d'outils gauche existe sous
`upscale/x4-topaz-recovery-v2-d50/left-toolbar/`; le reste du HUD demeure non produit. Cette
présence ne vaut ni QA globale, ni installation courante, ni décision de release.

Les ressources et le plan d'intégration sont consignés dans [`analysis/HUD_RESOURCE_INVENTORY.md`](analysis/HUD_RESOURCE_INVENTORY.md). Les rendus de contrôle extraits depuis les BIF se trouvent dans `reference/`.

L'identité source courante, les hashes et les dépendances PVRZ sont désormais suivis dans
`index/manifest.json`, `index/resources.csv` et `index/dependencies.csv`. Cet inventaire ne modifie
pas l'état de production historique et n'implique aucune QA.

Arborescence prévue pour la production :

- `source/` — export original par texture.
- `upscale/x4-topaz-recovery-v2-d50/` — PNG, alpha et PVRZ de production.
- `integration/` — manifestes, DLL et sauvegardes de test réversibles.
- `comparison/` — captures avant/après.
