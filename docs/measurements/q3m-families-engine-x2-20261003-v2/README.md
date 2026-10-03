# Candidat Q3m V7 x2 — 15 familles

- Sélection : `sprite/index/q3m-family-witnesses.json` ; contrat `pipeline/PALETTE_Q3M_V7.md`.
- Candidat : `current-generation.json` ; pack/DLL locaux ignorés, identités vérifiées.
- Source : deux plans acquis en lecture seule ; BAM source, géométrie et cycles conservés.
- Production : **49 BAM / 11 586 frames / 2 730 sources / 2 731 encodages compatibles**.
- Couleurs : **4 partenaires × 8 niveaux, K6**, profils V7 fixe=8/rampes=9, règle=3.
- Cache : `cache-resume.json` ; reprise 2 731 hits, import Torch interdit, zéro inférence/encodage nouveau. `cache-sharing-proof.json` : 54 variantes de métadonnées inutiles regroupées après égalité des tableaux.
- Vérifications : `verification.json` ; DLL compilée, C++/Python identiques pour chaque frame × six palettes × trois encodages, centres x1 et slots natifs contrôlés ; tests V6 conservés.
- Analyse native : `native-analysis.json` ; exécutable épinglé, 15 vtables/parseurs, 465 appartenances, chemin MonsterMulti alternatif.
- QA ingame **0/15**, aucune installation/release. Moteur 90 % conservé comme estimation utilisateur.
- Couverture : BAM/actions/directions sélectionnés ; **aucune animation complète** ni autre équipement déclaré produit. Composites incomplets → rendu natif complet.
- UI 6110 et historiques V6/xBR/ReboutCX final première génération préservés ; aucune QA transférée à V7.
- `witnesses.png` : comparaison source/Q3m avec palette K6 #0 synthétique, **hors jeu** ; frames/centres/cycles dans `preview-frames.json`.

| Famille | Animation | Témoin | Palette / BAM retenus |
|---|---|---|---|
| character | 6110 | Guerrière humaine | Rampes ; CHFB1G1/G11..G15 |
| character_old | 6400 | Drizzt | Rampes ; UDRZ1G1/G1E |
| monster | 7F02 | Spectateur | Fixe ; MBEHG1/G11..G15 |
| monster_old | 7603 | Chien gris | Fixe ; MDOGG1/G1E |
| monster_icewind | EF10 | Esprit des eaux | Fixe ; MWWEWK/WKE ; arme éventuelle absente → composite natif |
| monster_quadrant | 1000 | Grande wyverne | Fixe ; MWYVG11..G14, quatre parties |
| multi_new | 1201 | Dragon noir | Fixe ; **MDR21100,MDR21200,...,MDR21900** ; neuf parties, banque 1/chunk 0/direction 0 |
| monster_layered | 2100 | Volo | Fixe ; UVOLG1/G1E + UVOLMG1/MG1E |
| monster_ankheg | 3000 | Ankheg | Fixe ; MAKHG1/G1E + MAKHDG1/DG1E ; dessins séparés |
| monster_large | 9000 | Ogre | Rampes ; MOGRG1/G1E |
| monster_large16 | A100 | Ver charognard | Fixe ; MCARG1/G1E |
| ambient | C300 | Rat | Fixe ; ARATG1/G1E |
| ambient_static | B100 | Cheval | Fixe ; AHRSG1/G1E |
| town_static | 4410 | Femme endormie | Rampes ; LHFC |
| flying | D400 | Oiseau intérieur | Fixe ; ABIRG1 |

## Résultat moteur

- V7 : table partenaires propre au BAM, palette vivante par couche, alpha/deps stricts, caches bornés ; lecteur V6 conservé.
- Dix owners supplémentaires par neuf hooks ; Large/Large16 distingués par vtable exacte malgré Render partagé.
- Cellules acquises au callsite Realize propriétaire ; composite complet CharacterOld/Layered/Icewind, contexte extérieur masqué si Render imbriqué non ciblé.
- Multipart : compte natif 9/4 strict, centres/directions/ordre conservés ; chemins MultiNew et MonsterMulti pour INI multi_new.
- V7 : dimensions texture natives bordées ou sans bord selon égalité exacte au BAM ; rectangles x1 inchangés.
- Restant : QA des 15 témoins en jeu, couleurs/effets, équipement, directions, ombres, occlusions. `Q3M_FAMILY_WITNESS` distingue premier fallback/premier remplacement des nouveaux owners.

## Correction du témoin multipart

`../q3m-families-engine-x2-20261003-v1/SUPERSEDED.md` : la première sélection contenait neuf
directions de la partie 1. Contrôle visuel source puis assemblage des neuf parties corrigés avant
finalisation. Cache conservé : 2 635 hits, 96 guides nouveaux, 13 travaux spéciaux, 83 encodages,
498 **nouvelles clés cible** ; aucun retraitement d'une cible identique. Test dédié rejetant l'ancienne sélection.

## Références persistantes

`production-summary.json`, `pack-summary.json`, `cache-sharing-proof.json`, `cache-resume.json`,
`verification.json`, `native-analysis.json`, `preview-frames.json`, `current-generation.json`.
Commandes de production/build/tests : `pipeline/PALETTE_Q3M_V7.md`.
