# Instructions de travail — BG2 Upscale

## Audience documentaire

Écrire les documents opérationnels pour un LLM ou agent de code. Utiliser des consignes techniques
directes, des sources de vérité, des gates vérifiables et des commandes reproductibles. Éviter le
texte promotionnel, les explications conversationnelles et les états dupliqués hors de leur index
ou manifeste canonique.

## Décision d'intégration au manifeste

À la fin de chaque tâche de production ou de validation qui touche au contenu
ingame (cartes, animations, interpolations, masques, build, injection ou QA),
l'agent doit demander explicitement à l'utilisateur, dans sa réponse de clôture :

> La tâche `<nom>` est terminée. Veux-tu que j'intègre au manifeste de release
> les éléments validés par cette tâche ?

Cette décision est distincte de la mise à jour du catalogue `areas.csv` et
nécessite un accord affirmatif explicite. Sans cet accord, l'agent ne modifie
pas `$mapSpecs`, ne régénère pas `content.json`, ne met pas à jour le staging
et ne reconstruit pas l'archive.

Si la tâche ne produit aucun élément `validated-installed`, l'agent le précise
dans la question et n'intègre rien. Un élément `pending-qa`, x2, provenant de
`override`, d'une sauvegarde, d'une capture ou d'un répertoire temporaire n'est
jamais éligible. Tout refus ou report est noté dans le compte rendu de fin.
