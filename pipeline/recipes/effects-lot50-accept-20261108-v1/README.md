# Acceptation lot50 · 2026-11-08

- Utilisateur valide explicitement les50installés, demande suivi+commit.
- Source exacte : `effects/batches/lot50-black-transparent-20261108-v1/production.json` ; reçu `effects/installations/lot50-current-20261108-v1/installation.json` ; vérifier manifest/registre actifs,100bindings normal/prémult et50VVC principaux avant acceptation.
- `accept.py` appelle `effect_workflow.accept_asset` pour50packs mono-BAM ;50QA immuables,50sélections. Source/versions7alpha révisées et LAVABUB2v2 exactes ; pas d'acceptation des parents remplacés.
- Sortie immuable : `effects/batches/lot50-accepted-20261108-v1/{acceptance,verification}.json` ; préserve installation/release et444autres lignes. Reprise permise uniquement si même décision/date/run exact déjà enregistré ; aucune réécriture d'acceptance.json existant.
- Aucun fichier installé ni release modifié. Vérification ciblée de liaison métadonnées ; pas de rehash global des anciens médias.
