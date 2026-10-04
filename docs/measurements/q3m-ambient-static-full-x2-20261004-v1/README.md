# ambient_static complet — Q3m V7 x2 — 2026-10-04

- Demande : production complète + installation ingame ; QA visuelle utilisateur en attente.
- Scope : owner13, B000/B100/B200/B210/B300/B310/B400/B410/B500/B510/B600/B610/B700 ; 13 modèles, 26 BAM G1/G1E, 1 144 frames. Aucune source absente.
- Couleurs : K6, quatre partenaires/huit niveaux, V7 profile8 fixe (vache/cheval), profile9 rampes (11 figurants), rule3. Palettes natives live ; aucun SDF/alpha8 ; CatmullRom global conservé.
- Dédup : 1 064 sources/inputs/encodages compatibles ; 80 frames communes NBEGL/NSLVL, modèles distincts ; 26 SHA BAM distincts. Cache partagé `sprite/.work/q3m-family-witnesses-x2-20261003-v1` : 44 hits Cheval préservés, 1 020 nouveaux encodages, 6 120 nouvelles cibles. Reprise 1 064 hits sans import Torch.
- Production : `selection.json`, `produce.py`, `production.json`, `current-generation.json` ; pack `sprite/.work/q3m-ambient-static-full-x2-20261004-v1/{isolated,combined}`. Runs/encodages acquis non réécrits.
- Native isolé/combiné : 26 ressources/1 144 frames, 13 756 slots valides, K6 × trois encodages palette, 168 711 552 pixels comparés par passage. Centres/cycles/contrats vérifiés ; pas de QA ingame déduite.
- Catalogue parent Large16 V7 accepté : 91 IDs/50 273 routes préservés à l'identique ; actif 104 IDs/4 618 ressources/1 589 008 frames/50 299 routes. DLL Ankheg stable/shaders/INI/exe/UI/Large16 préservés : 120 fichiers contrôlés SHA.
- Installation : `installation-verification.json`, reçu local `ingame-installation/active-test.json`, backup local `work/before/CreatureSprites-XN.catalog`. 26 feuilles ajoutées, seul catalogue remplacé.
- CRE : 34 consommateurs existants, cinq modèles sans CRE stock (B210/B300/B310/B610/B700). Témoins `override/QMASB210.cre`, `QMASB300.cre`, `QMASB310.cre`, `QMASB610.cre`, `QMASB700.cre`, dérivés d'ARNMAN01 : seul uint16 animation à offset0x28 modifié. Aucun CRE existant remplacé. `creatures.json`, `CLUA-generiques.txt` : 13 commandes de test.
- Restauration, jeu/InfinityLoader fermés : `& ./docs/measurements/q3m-ambient-static-full-x2-20261004-v1/restore.ps1` ; authentifie catalogue/backup/120 fichiers/cinq CRE, restaure parent puis retire uniquement les cinq témoins. Feuilles non référencées conservées.
- Aucun asset d'autre famille retraité ; QA acquises intactes ; Character SDF en stock ; aucun payload/staging/content/TP2/archive/release modifié.
