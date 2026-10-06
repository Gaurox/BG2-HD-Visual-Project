# Character — une frame V6 / V7, x2

- Demande : comparatif PNG sans perte, agrandi, deux rendus côte à côte ; aucune migration Character.
- Sélection : `0x6110`, corps CHFB1 sans calques d'équipement ; `CHFB1G12`, frame5, cycle18/slot0 ; géométrie native23×63, centre11/55.
- Résultats acquis : V6 complet `playable-q3m-x2-ingame-20261002-v1` ; V7 témoin `q3m-families-engine-x2-20261003-v2`. Catalogues/feuilles lus et SHA contrôlés ; même source, géométrie et cycles ; métadonnées profil V7 vérifiées.
- Palette commune : K6 Character synthétique #0, alpha0 transparent/128 ombre/255 corps ; simulation hors jeu, sans SDF. Aucune capture ni QA ingame.
- `comparison-v6-v7-nearest-x6.png` : gauche V6, droite V7 ; rendu x2 agrandi ×6 entier Nearest, PNG RGB sans perte. `v6-x2.png`, `v7-x2.png` : RGBA x2 non agrandis, transparence conservée.
- Contrôles : alpha identique ; agrandissement égal à la répétition exacte des pixels ; relecture PNG égale au canvas. 1 732/3 074 pixels du corps diffèrent ; écart maximal15/255 par canal. `comparison.json` : identités et hashes.
- Réemploi intégral : zéro inférence, zéro nouvel encodage ; aucun changement installation, QA, suivi ou release. Choix de pose : planche locale ignorée `sprite/.work/q3m-character-frame-v6-v7-x2-20261006-v1/candidates.png`.
- Reproduction : Python `config://chainner_python`, `PYTHONPATH=pipeline/scripts;sprite/.work/q3m-runtime-tools-20261003-v1` ; `compare.py` (valeurs par défaut ci-dessus).
