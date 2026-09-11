# Décisions QA sprites

Répertoire réservé aux décisions ingame immuables futures, indexées par `asset_key` de
`../processing.csv`.

- Aucun fichier n'est créé avant une décision utilisateur explicite.
- Une revue technique de run ne constitue pas une décision ingame.
- Une décision cite le run sélectionné, son SHA-256, le catalogue testé, la génération installée,
  les scénarios et la date.
- Une décision de lot identifie exactement les `asset_key` par portée, nombre et SHA-256 ordonné ;
  chaque ligne couverte de `processing.csv` référence le même fichier immuable.
- Une correction crée une nouvelle décision ; elle ne modifie jamais une décision existante.
