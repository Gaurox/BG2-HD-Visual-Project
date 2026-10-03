# Pilote Q3m V7 x2 — 15 familles

- Sélection : `sprite/index/q3m-family-witnesses.json` ; contrat `pipeline/PALETTE_Q3M_V7.md`.
- Candidat : `current-generation.json` ; pack local ignoré, DLL locale, identités vérifiées.
- Source : deux plans acquis en lecture seule ; BAM source, géométrie et cycles conservés.
- Production : **49 BAM / 11 586 frames / 2 730 sources / 2 731 encodages compatibles**.
- Nouvelle couleur : **4 partenaires × 8 niveaux, K6**, profils V7 fixe=8/rampes=9, règle=3.
- Réutilisation : `cache-sharing-proof.json` ; reprise 2 731 hits, import Torch interdit, zéro inférence/encodage nouveau.
- Compilation DLL et tests hôte : `verification.json`. Décodage réel C++ comparé aux SHA Python : 1 458 851 832 pixels, six palettes × trois encodages natifs ; 24 530 slots valides, centres x1 contrôlés.
- Analyse native : `native-analysis.json` ; exécutable épinglé, 15 vtables/parseurs, 465 appartenances, chemin MonsterMulti alternatif.
- QA ingame : **0/15**, aucune installation/release effectuée. 90 % moteur conservé comme estimation utilisateur.
- La couverture du pilote concerne les BAM/actions retenus ; aucune animation complète, autre équipement ou direction absente du lot n'est déclarée traitée.
- Historiques V6 Character/Monster, QA UI 6110 et traitements finaux xBR/ReboutCX première génération préservés ; aucun acquis transféré à V7.

| Famille | Animation | Témoin | Contrat / BAM retenus |
|---|---|---|---|
| character | 6110 | Guerrière humaine | Rampes ; CHFB1G1/G11..G15 |
| character_old | 6400 | Drizzt | Rampes ; UDRZ1G1/G1E |
| monster | 7F02 | Spectateur | Fixe ; MBEHG1/G11..G15 |
| monster_old | 7603 | Chien gris | Fixe ; MDOGG1/G1E |
| monster_icewind | EF10 | Esprit des eaux | Fixe ; MWWEWK/WKE ; arme éventuelle manquante → composite natif |
| monster_quadrant | 1000 | Grande wyverne | Fixe ; MWYVG11..G14, quatre parties |
| multi_new | 1201 | Dragon noir | Fixe ; MDR21100..108, neuf parties ; deux Render natifs possibles |
| monster_layered | 2100 | Volo | Fixe ; UVOLG1/G1E + UVOLMG1/MG1E |
| monster_ankheg | 3000 | Ankheg | Fixe ; MAKHG1/G1E + MAKHDG1/DG1E ; dessins séparés |
| monster_large | 9000 | Ogre | Rampes ; MOGRG1/G1E |
| monster_large16 | A100 | Ver charognard | Fixe ; MCARG1/G1E |
| ambient | C300 | Rat | Fixe ; ARATG1/G1E |
| ambient_static | B100 | Cheval | Fixe ; AHRSG1/G1E |
| town_static | 4410 | Femme endormie | Rampes ; LHFC |
| flying | D400 | Oiseau intérieur | Fixe ; ABIRG1 |

## Résultat moteur

- Lecteur V7, table quatre partenaires propre au BAM, palette vivante par couche, alpha/deps stricts, caches bornés ; V6 inchangé.
- Dix owners supplémentaires par neuf hooks ; Large/Large16 distingués par vtable exacte malgré Render partagé.
- Cellules acquises au callsite Realize propriétaire, composite complet pour CharacterOld/Layered/Icewind ; aucun emprunt à un contexte Render extérieur.
- Multipart : compte natif strict, centres/directions/ordre conservés ; MonsterMulti accepte les animations INI multi_new connues, au-delà du seul 1200 historique.
- Dimensions texture V7 : contrat natif bordé ou sans bord selon égalité exacte au BAM, sans modification des rectangles x1.
- Validation restante : rendre les 15 témoins en jeu, couleurs/effets, équipement, directions, ombres et occlusions. Les logs `Q3M_FAMILY_WITNESS` distinguent le premier fallback du premier remplacement réussi pour les nouveaux owners.

## Fichiers persistants

`production-summary.json` = plan du lot + backend/encodeur ; `pack-summary.json` = catalogue/feuilles,
`cache-sharing-proof.json` = égalité et reprise, `verification.json` = tests,
`current-generation.json` = chemins et SHA du candidat. Les caches/pack/DLL restent locaux ignorés.
