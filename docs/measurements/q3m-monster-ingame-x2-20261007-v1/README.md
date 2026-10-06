# Monster — installation complète Q3m V7 x2, 2026-10-07

- Demande : installer le lot complet et rendre toutes les variantes testables. **62 modèles/77 IDs**, 25 IDs sans BAM exclus ; K6/quatre partenaires/huit niveaux/x2/Nearest sans SDF.
- [Production immuable](../q3m-monster-full-x2-20261006-v2/current-generation.json) : 1 037 feuilles/496 816 frames physiques, 1 040 liaisons/496 822 occurrences ; aucun recalcul.
- Parent : [Icewind installé et accepté](../q3m-icewind-accepted-x2-20261007-v1/README.md). Catalogue `e6b367b0…` ; 254 IDs/61 989 routes hors Monster conservés par resref/ordinal/SHA feuille/digest composant. Trois anciens pilotes 7F02/7F07/7F30 remplacés ; aucune ancienne feuille supprimée.
- Catalogue candidat : **331 IDs/14 330 feuilles/2 791 737 frames physiques/63 029 routes**. Indices de composants déplacés, octets et routes métier des autres familles conservés ; `catalog-proof.json`.
- Runtime inchangé : DLL Icewind `21a6f2e4…`, INI/Nearest, trois shaders et BaldurReal.exe SHA préservés. Aucun build DLL.
- [77 CLUA](CLUA.txt) : `QMON` +ID, ex. `C:CreateCreature("QMON7F45")`. CRE V1.0 dérivés d'ARNMAN01, EA128, zéro script/effet/item/état invisible ; `creatures.json`, 77 fixtures dédiées, dont les 12 sans CRE source.
- Vérification : hashes des 1 037 feuilles et équivalence exacte des 1 040 bindings de production ; réemploi de l'oracle natif exhaustif acquis, échantillon corps par chacun des 77 IDs +INV/grande frame sous catalogue combiné. `verification.json` ; aucune QA ingame déduite.
- Installation transactionnelle : `install.ps1 -DryRun`, `install.ps1`, `finish.py` ; reçu local `ingame-installation/active-test.json`, snapshot `installation-verification.json`, contrôle des fichiers installés `installed-verification.json`. Jeu/InfinityLoader fermés avant écritures.
- Restauration : `restore.ps1`, sauvegarde `work/before/CreatureSprites-XN.catalog` ; restitue le catalogue Icewind parent et retire seulement les nouvelles feuilles/fixtures créées. Les anciens fichiers physiques sont conservés.
- États : installation complète après reçu réussi ; **QA Monster en attente**, 77 IDs/62 modèles. Acquis QA : 176 IDs améliorés/13 familles, Character V6 inclus 254 IDs/14 familles ; aucune release.
