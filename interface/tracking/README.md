# Suivi UI / HUD — périmètre réduit

- Autorité active : `../index/work-tracking.json` ; une ligne par resref MOS/BAM retenue.
- Source brute : `../index/`, `../gameplay-hud-bg2ee/index/`, `../fonts/index/` ; inventaires conservés, pas des listes de travaux.
- Sélection : `../analysis/large-surfaces-20261110-v1/decisions.json` ; dernière décision prévaut.
- Hors périmètre actif : `out-of-scope.csv` ; historique/exports/QA conservés, aucune suppression physique.
- Vue tabulaire : `resources.csv` ; chiffres site : `progress.json` ; projections de l’autorité active.
- Clôture utilisateur 2026-11-22 : 204/204 sorties complètes. Contribution UI au résultat visible du site à 100 %. QA complète et présence alpha attestées pour 133/204, suivies séparément.

## États indépendants

| Axe | Valeurs courantes / règle |
|---|---|
| source | `resolved` + ressource native, frames, pages ; pas de QA |
| usage | `observed-selector-normal`, `static-reference`, `variant-to-qualify` |
| production | `complete-existing-x4`, `complete-selected-x4`, `complete-awaiting-review-x4`, `partial-existing-x4`, `not-assessed` ; complet = toutes frames natives |
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

Exception retenue 2026-11-11 : `INVENTOR`, `QUESTBAK`, `GUIREC2`, `STONEOPT` utilisent SeedVR2 7B x4 LAB ; recette et PNG exacts dans leurs états production. La recette Topaz demeure celle des autres ressources.

`complete-awaiting-review-x4` : sorties générées complètes, compteur `candidate_production` distinct des sorties retenues ; QA/installation/release inchangées.

## Consolidation 2026-11-11

- 21/204 ressources avec sortie complète retenue ; 1 BIGLOGO partiel ; 182 à rapprocher de l’existant.
- 5 ressources des quatre menus SeedVR acceptées sur le rendu observé ; 4 ressources sélecteur observées au démarrage normal, états/survols non extrapolés.
- 10 nouvelles ressources installées, QA ingame en attente : `../integration/next-ten-seedvr7b-x4-20261111-v1/`.
- 15 ressources SeedVR retenues au total ; recettes/PNG/SHA/QA/reçus par resref dans l’autorité.
- Snapshot site FR/EN mis à jour localement depuis `progress.json`, pas publié ; script `update_website_20261111.py`.
- Boutons/petites icônes hors file active ; 3B du comparatif quatre menus supprimés (168 418 512 octets), métadonnées historiques conservées.
- Aucun payload ni statut release modifié ; aucun nouveau résultat ingame déduit de l’installation.

## Lot 4 et validations cumulées

- Troisième lot validé : `../integration/third-ten-seedvr7b-x4-20261111-v1/qa-accepted-20261111-v1.json`.
- 31 ressources retenues complètes ; 29 observées en jeu (25 menus/illustrations + 4 démarrage sélecteur) ; 10 nouveaux candidats installés, dont DONATE2 et INNROOMS8 frames.
- Lot4 : `../integration/fourth-ten-seedvr7b-x4-20261111-v1/` ; guide/QA indépendants de la release.
- Site FR/EN : `sync_website.py` lit les compteurs actuels, actualise les pages et `assets/ui-progress.json`, sans commit/push/déploiement.

## Lot 5 — résultats affichés dans le chat

- Validation des planches lot4 : `../experiments/fourth-ten-seedvr7b-x4-20261111-v1/preview-accepted-20261111-v1.json` ; hors jeu, pas de nouvelle observation ingame déduite.
- 41 sorties complètes retenues ; 10 nouvelles candidates création/personnalisation produites en 7B x4, pas installées ; 1 BIGLOGO partiel.
- Lot5 : `../experiments/fifth-ten-seedvr7b-x4-20261111-v1/` ; dimensions/alpha/SHA vérifiés.
- QA `accepted-offline-awaiting-ingame` distincte des acceptations `accepted-observed-*` et `accepted-complete` ; les dix ressources du lot4 restent installées pour test.

## Lot 5 installé / lot 6 produit

- Lot5 validé sur images puis installé à la demande utilisateur : `../integration/fifth-ten-seedvr7b-x4-20261111-v1/` ; QA ingame distincte.
- 51 sorties complètes retenues, 10 nouvelles candidates menus généraux/multijoueurs : `../experiments/sixth-ten-seedvr7b-x4-20261111-v1/`, non installées.
- 29 ressources observées en jeu ; 20 ressources installées des lots4/5 en attente de confirmation ingame ; pas d’extrapolation depuis une validation de planches.
- Recettes, sorties, SHA256, validations, installations et release suivis séparément par resref. Portraits/expériences hors interface inchangés.

## Lot 6 validé / lot 7 produit

- Lot6 installé : `../integration/sixth-ten-seedvr7b-x4-20261111-v1/installed-20261111-v1.json` ; validation observée utilisateur : `qa-accepted-20261111-v1.json` (9 ressources). GUIDLC conserve sa validation hors jeu : route tactile non exposée sur PC.
- 61 sorties complètes retenues ; 38 ressources observées en jeu, couverture limitée ; 21 installées en attente (lots4/5 + GUIDLC tactile).
- Lot7 : `../experiments/seventh-ten-seedvr7b-x4-20261111-v1/` ; dix candidates 7B x4, non installées, planches/zooms à valider. Variantes historiques : usage runtime à qualifier séparément.
- Icônes GMPCARBB et poignées GMWMSGA0/9 conservées en natif exact ; alpha natif x4 préservé ; résultats/identités SHA par resref.
- Site FR/EN synchronisé localement, sans publication ; aucune modification release.

## Lot 7 installé — accès historique non établi

- `../integration/seventh-ten-seedvr7b-x4-20261111-v1/README.md` : dix compositions retenues/installées ; validation des planches seulement. 14 atlas /16 fichiers, 57 anciens fichiers non remplacés vérifiés inchangés.
- `route-audit.json` et `TEST_INGAME.md` : aucun des dix noms dans UI.menu actif / exécutables racine ; pas de guide d'accès inventé, aucun routage forcé. Prochaine action `qualify-runtime-usage-seventh-ten`.
- Compteurs courants : 71/204 ressources complètes retenues (34,8 %), 1 partielle, 132 productions à rapprocher/qualifier ; 38 ressources observées en jeu avec couverture limitée. Les candidats installés/hors jeu ne deviennent pas QA ingame.
- Alpha DXT5 natif préservé ; icônes/poignées intégrées rétablies en blocs natifs exacts. Renderer : cinq empreintes ajoutées ; 71 pages gameplay testées.
- Site FR/EN synchronisé localement ; aucune publication ni modification release.
