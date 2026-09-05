# Pipeline des tuiles secondaires WED

Ce pipeline est requis lorsque le préflight trouve au moins une cellule WED dont `secondary` n'est
pas `0xFFFF`. Il couvre les portes, variantes de décor et masques de fontaine : ce ne sont pas
nécessairement des portes.

1. Produire et valider les deux maîtres x1 : primaire et secondaire.
2. Upcaler les deux rendus à la même échelle et avec le même protocole de découpe, choisi dans
   [`MAP_SPLITTING_POLICY.md`](MAP_SPLITTING_POLICY.md).
3. Si une correction locale est appliquée à une région commune, reporter le même masque sur les
   deux variantes ; documenter toute exception.
4. Fournir les deux images xN au builder. Il restaure l'alpha source sur les deux jeux de tuiles.
5. Si la cellule est liquide, appliquer aussi [WATER_MAP_PIPELINE.md](WATER_MAP_PIPELINE.md) :
   l'anti-aliasing de contour concerne désormais les secondaires des fontaines.

Une zone sans secondaire distincte conserve le rendu x1 secondaire pour l'intégrité, mais ne
requiert pas une seconde inférence ni une seconde image au build.
