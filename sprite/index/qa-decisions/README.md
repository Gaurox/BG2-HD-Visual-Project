# Décisions QA sprites

Autorité unique des décisions ingame immuables sur les sprites.

- Aucun fichier n'est créé avant une décision utilisateur explicite.
- Une revue technique de run ne constitue pas une décision ingame.
- Une décision cite le run sélectionné, son SHA-256, le catalogue testé, la génération installée,
  les scénarios et la date.
- Une décision de lot identifie exactement ses animations/assets par portée, nombre et SHA-256
  ordonné.
- Une correction crée une nouvelle décision ; elle ne modifie jamais une décision existante.
- Une acceptation reste acquise si les octets concernés et le contrat runtime sont inchangés.
- `active-test.json` décrit l'installation locale et ne peut ni créer, ni annuler une décision QA.
