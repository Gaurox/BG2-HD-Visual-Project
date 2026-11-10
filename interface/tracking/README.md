# Suivi UI / HUD — périmètre réduit

- Autorité active : `../index/work-tracking.json` ; une ligne par resref MOS/BAM retenue.
- Source brute : `../index/`, `../gameplay-hud-bg2ee/index/`, `../fonts/index/` ; inventaires conservés, pas des listes de travaux.
- Sélection : `../analysis/large-surfaces-20261110-v1/decisions.json` ; dernière décision prévaut.
- Hors périmètre actif : `out-of-scope.csv` ; historique/exports/QA conservés, aucune suppression physique.
- Vue tabulaire : `resources.csv` ; chiffres site : `progress.json` ; projections de l’autorité active.

## États indépendants

| Axe | Valeurs courantes / règle |
|---|---|
| source | `resolved` + ressource native, frames, pages ; pas de QA |
| usage | `observed-selector-normal`, `static-reference`, `variant-to-qualify` |
| production | `complete-existing-x4`, `partial-existing-x4`, `not-assessed` ; complet = toutes frames natives |
| QA | `accepted-observed-normal`, `accepted-complete`, `not-reconciled` ; preuve et limites obligatoires pour une acceptation |
| installation | reçu daté / état non réconcilié ; ne pas déduire l’état live d’un reçu ancien |
| release | `confirmed-current-scope` ou `not-reconciled` ; aucun changement payload déduit |

Les deux groupes menus du suivi ancien restent dans `historical_groups`. Ne pas les convertir
en deux ressources, ni effacer leur QA. Quatre ressources du sélecteur ont une QA du démarrage
normal ; cette preuve n’accepte pas tous les survols. Le compteur public complet reste distinct.
Production non évaluée ≠ absente ; priorité : rapprocher les sorties existantes avant génération.

## Utilisation

Depuis la racine du dépôt :

```powershell
python -B interface/tracking/manage.py status
python -B interface/tracking/manage.py queue --limit 30
python -B interface/tracking/manage.py show DONATE
python -B interface/tracking/manage.py check
python -B interface/tracking/manage.py export
```

Modifier uniquement les axes réellement établis dans `../index/work-tracking.json` ; joindre
les chemins de preuves, le périmètre frames/états et la prochaine action. Puis `export`.
Ne jamais déduire QA/installation/release de la production ou de la sélection visuelle.
`initialize_20261110.py` = migration initiale, refuse d’écraser un suivi existant.

## Contrat de production conservé

- Topaz Gigapixel 8.4.1 Recovery v2 / Detail50 / x4 / couleurs préservées.
- Éléments complets séparés, recomposition DXT5 ; pas d’inférence d’atlas complet.
- `DONATE` : alpha progressif natif séparé, pas de contour dur/matte.
- `BIGLOGO` : frame 0 existante ; frames 1/2 à qualifier/compléter.
- Atlas mixtes : créer une variante réduite ; boutons exclus conservés en natif.
- Aucun nouveau traitement des trois médaillons sélecteur existants.

## Site

Checkout canonique : `config://website_checkout`, EN/FR synchronisés ; source `progress.json`.
204 resrefs retenues remplacent l’ancien dénominateur 1672. Les groupes historiques ne sont pas
des unités comparables. Zéro ressource release réconciliée n’affirme pas un payload vide.
Publication distincte ; règles : `../../docs/WEBSITE.md`.

Références absentes `GUIBG`/`GUINOTE` : `work-tracking.json:unresolved_references`, hors dénominateur 204, à qualifier avant tout ajout.
