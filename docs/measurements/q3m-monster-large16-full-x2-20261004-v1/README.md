# Large16 complet disponible — Q3m V7 x2 sans SDF

- Demande : produire/install ingame ; aucun commit/release ni QA ingame déduits.
- Famille native `monster_large16`, owner11, kind0 : `A000` wyverne, `A100` charognard rampant, `A200` wyverne blanche. Deux géométries, trois contrats couleur. `A201/A202` déclarés sans BAM ; exclus explicitement, pas produits.
- Source effective : `MWYV` six banques monde + `INV` (578 frames), `MCAR` six banques monde (536). **12 BAM monde / 1 112 frames**, + un BAM auxiliaire / deux frames ; aucune intégration UI revendiquée.
- Inventaire par préfixe = 25 BAM ; douze `MWYV G11..14/G21..24/G31..34` appartiennent au profil Quadrant partagé, hors appels Large16. Preuves : `native-scope.json`, `native-large16-constructor.asm` (exécutable épinglé, six cellules G1/G2/G3 et E). Inventaires source historiques inchangés.
- `A200` réutilise la géométrie MWYV mais remplace sa palette par **`MWYV_WS.BMP`** native : sept feuilles propres, palette RGB authentifiée. Pas de copie des couleurs de la wyverne normale. Total **20 feuilles / 1 692 frames / trois IDs**, V7 profile8/rule3, K6 quatre partenaires/huit niveaux ; aucun plan alpha8/SDF.
- Palette fixe : l'ombre native index1 est parfois colorée ; l'oracle natif applique aussi le tint à cet index. Attente scalaire corrigée localement dans `q3m_family_witnesses.py`, sans réécrire les preuves historiques.
- Doublons : 1 053 travaux source BAM originaux ; 1 567 sources sous contrats couleur / 1 570 encodages compatibles. **176 hits acquis inchangés + 1 388 encodages nouveaux + six spéciaux sans GPU** ; 8 328 cibles nouvelles. Reprise **1 570/1 570 hits**, import Torch bloqué. Cache partagé `sprite/.work/q3m-family-witnesses-x2-20261003-v1`.
- Production : `selection.json`, `production.json`, `current-generation.json`. Packs locaux `sprite/.work/q3m-monster-large16-full-x2-20261004-v1/{isolated,combined}` ; preuves scellées, ne pas rejouer les producteurs dans ce run.
- Vérification : `verification.json`, dix tests hôte ; sonde native stable isolée + combinée : 20 ressources / 1 692 frames / 7 441 slots / six palettes × trois formats ; centres/cycles/palette source contrôlés. Logs associés, pas preuve visuelle ingame.
- Installation : `installation-verification.json` ; reçu actif local `ingame-installation/active-test.json`. Catalogue parent `56be42fb…fcc8` → **`6fbb2f02…44c80`** ; 88 IDs / 50 253 routes hérités identiques ; actif **91 IDs / 4 592 ressources / 1 587 864 frames / 50 273 routes**. Ajout des seules vingt feuilles et du CRE témoin ; DLL/INI/trois shaders/exécutable/81 packs UI/12 feuilles Ankheg préservés (**99 fichiers**). Ankheg SDF stable accepté conservé, Character SDF toujours en stock. Filtre CatmullRom global conservé ; pas de recompilation/install du runtime V10 présent dans HEAD.
- Census `creatures.json` : onze CRE stock consommateurs (cinq A000, six A100), aucun A200. Témoin blanc `override/QMWYVW01.cre` dérivé de `WYVBAB01` : seul uint16 animation à offset `0x28`, A000 → A200 ; cible initialement absente. Source témoin conservée en `.work`, identité dans `creatures.json` ; install/restore contrôlent son SHA.
- QA **en attente utilisateur** ; aucun payload/staging/TP2/content/manifeste release modifié. Ogre/Flying/Ankheg acquis et décisions QA immuables.

```lua
C:CreateCreature("WYVBAB01") -- wyverne A000
C:CreateCreature("CARCRA01") -- charognard rampant A100
C:CreateCreature("QMWYVW01") -- témoin wyverne blanche A200
```

`CLUA-generiques.txt` : trois modèles/variantes ; `CLUA-tous-consommateurs.txt` : consommateurs stock, pas de traitement par CRE.

Retour au catalogue parent, jeu et InfinityLoader fermés :

```powershell
& ./docs/measurements/q3m-monster-large16-full-x2-20261004-v1/restore.ps1
```

`restore.ps1` authentifie le catalogue/backup/99 fichiers/CRE témoin avant restauration ; retire uniquement le CRE créé et référencé par SHA. Feuilles nouvelles non référencées conservées. Nouveau changement = nouveau run ; ne pas réécrire ces instantanés.

- 2026-10-04 : **V7 sans SDF validé ingame**, utilisateur « c'est propre ! » ; QA immuable `sprite/index/qa-decisions/monster_large16/2026-10-04-accepted-full-available-large16-q3m-v7-x2-catmullrom-v1.json`. Trois familles/neuf IDs acceptés. Les mentions en attente ci-dessus décrivent la remise initiale ; futur SDF = autre variante, QA distincte.
