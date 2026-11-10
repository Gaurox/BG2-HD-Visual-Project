# Audit183 — réemploi et installation réelle,2026-10-28

Périmètre : les183lignes `effects/index/processing.csv:spatial_state=not-started`. Source/production/QA/installation séparées ; aucune génération ni modification des index/du jeu. Les2sources bloquées absentes sont hors de ces183.

## Résultat

| Décision | Entrées des183 | Travail |
|---|---:|---|
|Déjà installées sous leur nom dans effects|4|Suivi à rapprocher ; pas de nouvelle image ni liaison nécessaire|
|Production effects existante et vérifiée installée sous un autre nom|9|Ajouter une liaison/variante pour le nouveau RESREF, préserver contrat natif ; aucune nouvelle inférence|
|Production animations sélectionnée, vérifiée installée sur ses cartes|5|Réutiliser les images ; exporter/relier pour le consommateur VVC distinct, adapter le contrat ; ne pas déduire une couverture VVC du registre AREA|
|Pas de production achevée réutilisable identifiée|165|163BAM canoniques distincts ;162ensembles visuels complets distincts ; voir3paires ci-dessous|

**Charge nouvelle :162productions visuelles distinctes pour165RESREF. Réemplois existants :14, dont9alias effects et5ponts animations→effects. Déjà couverts effects :4.** Équation des entrées :162+3alias internes+14réemplois+4déjà couverts=183.

Ce compte reste celui de l'inventaire élargi, **pas162sorts actifs** : il comprend encore décors/créatures/ressources à usage non démontré. L'audit ne transforme pas une ressource inutilisée en besoin de production. Classement sémantique/usage natif indépendant ; pas d'exclusion arbitraire depuis un nom ou une vignette.

## Réemploi : listes exactes

Déjà installés dans effects : `BURNHAND`, `SPIPLARI`, `SPPRISM3`, `SPPRISMT`. Source canonique identique à la production liée ; fichiers actifs vérifiés.

| RESREF à relier | Production installée à réutiliser | Identité |
|---|---|---|
|SPARMOUR|OHNVIS1|BAM décompressé identique|
|SPFDETH3|SPFDEATH|BAM décompressé identique|
|SPFIRIMP|FIREH|BAM décompressé identique|
|SPFLMSTI|FLMSTRK|BAM décompressé identique|
|SPHLHI01|SPHLEFT|BAM décompressé identique|
|SPHLHI02|SPHRIGHT|BAM décompressé identique|
|SPICEIMP|COLDH|BAM décompressé identique|
|SPILUSIO|SPILLUS|BAM décompressé identique|
|SPSDRBUR|SPSDBUR|RGBA/géométrie/cycles identiques ; indices/palette1024octets/indice transparent également identiques ; sérialisation BAM différente|

| Réemploi animations | Présence actuelle vérifiée | Portée à ajouter si appel VVC |
|---|---|---|
|BDFORCEW|OH8100|VVC BDFORCEW,15FPS source déclaré,loop,blend1|
|OHDLPORT|OH5400/OH5500|VVC OHDLPORT,15FPS source déclaré,loop,blend1|
|OHHNECR|OH7300|VVC OHHNECR,15FPS source déclaré,loop,blend1|
|OHRSGATE|OH4220/OH4230|VVC OHRSGATE,15FPS source déclaré,loop,blend1|
|SPDIMNDR|AR6108|VVC SPDIMNDR,15FPS source déclaré,once,blend1|

Ces FPS/blend sont des métadonnées consommateurs, pas une nouvelle mesure ingame. Réutiliser ne signifie pas copier aveuglément un registre AREA dans effects : cadence/cycles/centres/alpha/normal-lumineux à conserver pendant l'adaptation.

## Doublons internes encore non produits

- `AMDEMGT` / `SP_DEMGT` : même BAM canonique ; une production, deux noms.
- `DEMB1A7` / `DEMB1A9` : même BAM canonique ; une production, deux noms. Sprite de créature, hors futur lot de sorts.
- `SPFLADOW` / `SPFLSTRI` : mêmes RGBA décodés, dimensions,centres et cycles ; indices/palettes diffèrent. Une production RGB/alpha réutilisable, **deux sources/carriers indexés distincts à conserver**. Pas de fusion des contrats de palette. Le lot50 proposé précédemment contient donc49ensembles visuels distincts, pas50 ; ne pas le lancer en l'état.

## Preuves et limites

- `audit.csv` :183décisions individuelles ; `audit.json` : correspondances,preuves sources/productions/installations/fichiers hashés.
- Croisement :494assets effects (canonique+RGBA décodé complet),246sources animations (idem) +sélections ; hashes canoniques inventaire sprite et répertoire du catalogue sprite actuellement installé (aucun match sprite).
- Empreinte visuelle stricte : enregistrements dans l'ordre, dimensions/centres,RGBA avec pixels transparents neutralisés, cycles/lookups. Pas de réemploi inféré depuis une simple ressemblance, un fragment de sprite ou une couleur.
- Registre effects actif522RESREF, manifest SHA256 `33EABE45E817E000E33BA9A96DD0B758E356FC1DAEC79BBF548774E669C60316` ; hash du registre conforme au manifest. Cadres et carriers des productions utiles lus/hashés.
- Registres AREA actifs parsés ; blocs des5ressources comparés aux packs sélectionnés et tous leurs fichiers associés hashés ;7liaisons ressource/carte. Registres peuvent contenir d'autres ajouts : comparaison ciblée des blocs, pas hypothèse d'identité du pack entier.
-3201fichiers vérifiés/1702399812octets. Jeu non lancé ; présence/intégrité offline vérifiées, aucune nouvelle QA ingame affirmée.
- Index effects/animations,INI,manifest effects,catalogue sprite inchangés par SHA256 avant/après. Aucune liaison ajoutée ; aucun traitement,installation,release,commit.
- Reproduction en lecture seule : `python -B pipeline/recipes/effects-remaining-audit-20261028-v1/audit.py` ; sorties de diagnostic locales remplaçables,aucune autorité métier écrite.

`cross183.json` conserve les recherches par hash canonique et équivalence RGBA ; `installed183.json` conserve les hits des répertoires actifs. La correction du suivi est une opération distincte non effectuée ici.
