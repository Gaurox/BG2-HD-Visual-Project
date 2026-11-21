# Contrôle local des atlas partagés

- Lancer par InfinityLoader sur une sauvegarde de test. Conserver les réglages actuels de filtrage. L'essai couvre les marges de 4 pixels, avec mipmaps et anisotropie désactivées.
- Console Ctrl+Espace. `C:EnableCheatKeys()` une fois par session. `C:MoveToArea("AR0706")` change de zone. Remplacer le code pour chaque entrée. Console fermée, sélectionner un personnage, viser un sol libre et utiliser Ctrl+J. Ctrl+X donne les coordonnées logiques x1 sous la souris.

| Ordre | Comparaison | Raccord de pages x1 |
|---|---|---|
| 1 | AR0706 → AR0334 → AR1603 → AR2001 | autour de (480,384) et (544,384) |
| 2 | AR0708 → AR0531 → AR1612 | autour de (416,384) et (480,384) |
| 3 | AR0704 → AR2010 | autour de (672,512) et (672,704) |

Observer le sol et les contours voisins des deux côtés de chaque raccord. Faire défiler légèrement la caméra et varier le zoom habituel. Chercher trait, clignotement, carré noir ou couleur qui déborde. La première zone de chaque ligne sert de témoin.

Dans **AR0704** et **AR2010**, repérer `DOOR01` près de **(864,352)**. Les six cellules de porte se répartissent entre **x 800–928** et **y 288–416**. Ouvrir puis fermer la porte et vérifier la silhouette, le raccord au bâti et le passage dans les deux états. Recharger la sauvegarde de test pour comparer l'état initial si nécessaire.

## Validation locale

- 2026-11-21, décision utilisateur sur l'essai installé « test validés ». Pack `a8128396d0caf6edd8a733bac9008e5cae5d33930534e8c8c81b1ea3e7df04a3`.
- Journal `InfinityEngine-Enhancer.log`, session 18:33:58–18:35:52. Chargement x4 observé sur AR0706 et AR0334. La décision utilisateur porte sur l'essai local et le journal documente ces deux zones.

## Retour arrière

Fermer BG2EE et InfinityLoader. Depuis la racine du dépôt, exécuter `python -B pipeline/recipes/map-atlas-sharing-20261121-v1/install_test.py restore`. Le reçu et les sauvegardes des 14 PVRZ sont conservés dans `run/installation/`.
