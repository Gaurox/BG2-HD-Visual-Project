# Audit des runs restants — 2026-10-11

Autorité de cet audit : `reviewed-audit.json` ; inventaire exhaustif : `runs-reviewed.csv`.
Lecture seule sur production/QA/installation/release ; aucune suppression ou modification de statut.

| Classe finale | Runs | Gio | Décision |
|---|---:|---:|---|
| Inutilisés, sans validation ni dépendance retenue | 43 | 0,978 | Candidats suppression ; `candidats-suppression.csv` |
| Réservations anciennes sur runs terminés | 22 | 0,297 | À clarifier ; marqueurs non supprimés |
| Provenance historique seule | 7 | 0,311 | À clarifier ; preuves historiques conservées |
| Approbations techniques déclarées hors dépendances courantes | 10 | 0,397 | Conserver ; aucune QA ingame déduite |
| QA/sélections/installation/release et dépendances | 655 | 55,682 | Conserver |

- Périmètre : 737 racines, 57,664 Gio ; `animations/runs/*`, `animations/batches/*`, `animations/ressources/*/runs/*`. Aucun autre parent `runs` dans `animations/` lors de l'inventaire.
- Contrôles : 1 265 manifests QA/sélection présents et SHA exacts ; 234 zones installées = verrou = registre ; 54 BAM des candidats identiques à des `animations/ressources/<REF>/source.bam` canoniques.
- Graphe conservateur : toutes QA immuables, sélections, registre/alpha, verrou, manifests release, migrations ; fermeture par métadonnées. Un BAM présent ou un nom `final` ne suffit pas à valider/utiliser un run.
- Réservations : runs `completed` datés 2026-09-05 à 2026-09-11 ; anciens marqueurs `reserved` encore présents. Ils ne prouvent pas un processus en cours. Liste et SHA dans `reviewed-audit.json`, `a-revoir.csv`.
- Historique : six runs AR2804 retenus seulement par inventaire P3 ; ancien BUBBLES2 source de sept descriptors archivés, manifest SHA toujours exact. Ne pas purger ces preuves sans résoudre leur conservation.
- `audit.json`/`runs.csv` : premier résultat du graphe, avant contrôle externe. `external-reference-check.json` : 4 001 fichiers de `docs/pipeline/archive/releases/asset-tracking` examinés ; ancien inventaire/source BUBBLES2 et log informatif AR0700 retrouvés. Plans/archives du nettoyage précédent et cet audit exclus comme auto-références administratives.
- Recettes : `audit.py` puis `finish_review.py` ; écritures exclusives de nouveaux reçus. Ne pas rejouer au même chemin. `candidate-paths.txt` est la liste provisoire de 44, remplacée par `candidats-suppression.csv` (43).
- Suppression future : recontrôler SHA des autorités et empreintes des candidats ; préserver diagnostics immuables ; protéger sources canoniques, réservations et historique. Aucun pack, payload, staging, TP2 ou fichier jeu inclus dans la liste.
