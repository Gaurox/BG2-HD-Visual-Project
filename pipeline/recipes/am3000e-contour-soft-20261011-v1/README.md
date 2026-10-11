# AM3000E — essais de contour/fondu, 2026-10-11

- Demande : contours lissés + fade transparent, préserver petites volutes ; proposer meilleure solution.
- Entrée : `animations/batches/lot45-final-20261011-v1/final-AM3000E-PLT_MAGE` ; ReboutCX x4 sur palette PLT_MAGE réalisée, Apollo8, RGB déjà prémultiplié.
- Ancien inner4 : max core loss15,16%, petites composantes94,18% ; évité pour cet essai.
- Méthode : filtre gaussien **RGBA prémultiplié**, limité à la bande du contour, transition vers noyau inchangé ; fondu des deux côtés de la silhouette. Aucun erode/contour unique, aucun composant explicitement retiré, aucune seconde prémultiplication.
- Variantes : `soft2` sigma2px x4, filtre entier jusqu'à4px intérieurs, noyau exact au-delà8 ; `soft3` sigma3, jusqu'à6, noyau exact au-delà12. Tronqué4sigma ; padding3px x1 (=12px x4) transparent ; centres+3 et dimensions+6 : placement monde inchangé, fade non coupé au canvas.
- Conservation :61frames stockées ; cycles/timelines/aliases byte-identiques aux métadonnées initiales,48/36/20phases,1,6/1,2/0,666667s à30FPS. Pas de nouvelle interpolation/inférence.
- Mesure61frames : variation absolue maximale de l'énergie RGB additive0,131% (soft2),0,290% (soft3). Noyau inchangé vérifié par égalité RGBA ; marge extérieure transparente ;61hashes distincts par variante ; packs validés par `validate_v2_pack`.
- Producteur : `python pipeline/recipes/am3000e-contour-soft-20261011-v1/build.py` ; sortie versionnée immuable `animations/batches/am3000e-contour-soft-20261011-v1/{soft2,soft3,comparison.png,comparison.gif,manifest.json}` ; résultats condensés `result.json`.
- Comparatif : gauche actuel, milieu soft2 recommandé pour conserver les détails, droite soft3 plus diffus ;3phases du cycle1 effectivement utilisé sur AR3000, plus petite pose pour vérifier l'apparition. GIF cycle1 complet,36phases/1,2s, ancre monde fixe.
- État courant : **soft2 v1 remplacé par correction native v2 acceptée** ; `../am3000e-contour-native-20261011-v2/README.md`. Padding v1 incompatible avec la résolution des sous-frames du runtime. Soft3 seulement en essai. Manifestes/reçus v1 historiques immuables ; v1 non acceptée. Release non sélectionnée ; suivi/commit du lot5 demandés.

## Installation soft2, 2026-10-11

- Demande : « ok installe celle du milieu ingame et redonne les clua » ; producteur `install.py`, jeu/InfinityLoader arrêtés.
- Pack historique remplacé : `animations/packs-par-zone/am3000e-contour-soft2-20261011-v1/AR3000` ; wrapper `animations/ressources/AM3000E/runs/am3000e-contour-soft2-20261011-v1` ; reçu `animations/batches/am3000e-contour-soft-20261011-v1/installation.json`, sauvegarde transactionnelle liée dans ce reçu.
- Payload installé vérifié byte-identique au nouveau pack ;8frères byte-identiques : AM3000A/AM3000H/BUTRFLY/FISH1L/FISH1S/FISH2L/FISH2S/FISH3S. DLL/INI/ARE inchangés ; cycles/aliases/durées conservés ; registre actualisé pour dimensions/centres du padding transparent, placement monde inchangé.
- CSV `à-valider`, nouveau wrapper sélectionné ; verrou AR3000 actualisé, signatures de reconstruction conformes. Ancien pack conservé pour rollback ; aucune autre zone modifiée.
- CLUA : batch `CLUA.md`,5DoorMist sur AR3000 ; coordonnées logiques x1 : (396,1169)/(640,1521)/(899,1853)/(447,2006)/(194,1670).
