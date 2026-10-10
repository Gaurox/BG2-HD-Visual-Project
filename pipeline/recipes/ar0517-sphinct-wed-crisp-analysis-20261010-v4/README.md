# AR0517 / SPHINCT — diagnostic contour net

- Demande : screenshot `E:/Steam/userdata/5536307/760/remote/257350/screenshots/20261010181413_1.jpg`, bord branche mélangé après installation v3.
- Diagnostic : 49 frames jeu = reconstruction exacte du v3 ; RGB source conservé ; alpha source=255 sur toute la bande de transition ; registre position-bound => bridge natif contourné. Cause : fondu explicite8px x4 + retrait8px x4, pas double masque.
- Comparaison : v3 g8/f8 ; Fit1 g8/f0, g4/f0, g0/f0. Même frame8, même carte, source non masquée ; phases0/16/32/48 supplémentaires.
- Proposition : spline fermée du polygone3 en coordonnées monde x4, Fit1, couverture sous-pixel SS4/BOX ; garde0/fondu0. Pas de multiplication par la marche native x1 : conserver celle-ci réintroduirait les escaliers. RGB/placement/cycles restent ceux de la source.
- Limite : composites hors jeu, sans personnage/éclairage runtime ; raccord à revalider ingame si installé. Aucun fichier jeu ni suivi QA modifié.
- Sorties : `animations/batches/ar0517-sphinct-wed-crisp-analysis-20261010-v4/{analysis.json,comparison.png,before-after.png,edge-detail.png,spline-on-background.png,phase-*.png,*-coverage.png}`.
- Reproduction : `python -X utf8 pipeline/recipes/ar0517-sphinct-wed-crisp-analysis-20261010-v4/preview.py`.
