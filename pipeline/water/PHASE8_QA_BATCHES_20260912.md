# Phase 8 — candidats et preuves QA — 2026-09-12

## Livraison

- Racine locale : `maps/water-batches/runs/qa-candidates-20260912-v1`.
- 8 lots familiaux, chacun avec `batch-manifest.json` et `candidate-receipt.json`.
- 2 renderers : `q0-native` et `q1-ar0900-reference`.
- Matrice suivie : `manifests/liquid-target-matrix-v1.json`.
- Index suivi : `manifests/qa-batches-20260912-v1.json`.

| État | Identités |
|---|---:|
| corrected | 1 |
| candidate-installable-pending-qa | 59 |
| already-conform | 5 |
| blocked | 33 |

Total : 98 identités, 67 WED, 8 familles. Absence/divergence/non-approbation route2 : `q=0`.
Seule AR0900 jour/WTLAKE est approuvée à `q=1.00`.

## Contrat des lots

- Fichiers carte : candidats voie1 de phase7, liens physiques vérifiés par hash.
- WTLAKE : package x4 périodique validé, inchangé.
- WTPOOL et WTLAKA–D : packages x2 canoniques validés.
- WTSWAM, WTSEW, WTOIL : actions transactionnelles de retrait d'override pour retour stock.
- WTLAVA–D : package historique conservé, mais cibles bloquées par composition/periodicité.
- WT5000A–D : stock conservé ; cibles bloquées par classifieur et matériau manquants.
- Reçus produits : assemblage uniquement, statut `assembled-not-installed`.

## QA ingame future

1. Fermer Baldur's Gate II EE et InfinityLoader ; revérifier les processus.
2. Installer un seul lot familial transactionnel avec sauvegarde et contrôle des préconditions live.
3. Installer `renderer/q0-native` ; redémarrer le jeu. Ne pas réutiliser une session déjà ouverte.
4. Tester une seule carte et variante à la fois : centre animé, art local, ombres/reflets,
   transparence, rives, raccords internes, padding, bordures, zoom/pan/pause et cycle complet.
5. Vérifier les transitions jour/nuit et vers une carte exclue ; toute identité non approuvée doit
   rester native avec `q=0`.
6. Enregistrer captures, logs, décision et reçu d'installation séparément par carte/variante/famille.
7. Restaurer/vérifier la transaction avant le lot familial suivant.
8. `q1-ar0900-reference` ne sert qu'au témoin AR0900 jour. Toute nouvelle entrée q1 exige une QA
   familiale, un nouveau registre versionné et un nouveau build ; ne jamais éditer v1/v2.

## Frontières

- Aucun test exécuté, conformément au choix utilisateur.
- Aucun fichier du jeu installé ou supprimé.
- Aucune QA nouvelle déduite.
- Aucun manifeste release, payload, staging, `content.json` ou archive modifié.
