# Prochain lot proposé — town_static complet disponible, 2026-10-04

- **Proposition uniquement ; aucune production/installation**. Cible : Q3m V7 K6 x2, couleurs améliorées, sans SDF, palettes natives live/CatmullRom ; owner14. 17 avatars à rampes profile9/rule3 ; femme-araignée fixe profile8/rule3.
- Plus courte famille native restante : 1 542 travaux source ; suivantes ambient2 406, character_old3 771. Ogre/Flying/Ankheg/Large16/Ambient_static déjà traités exclus ; Character acquis hors choix.
- 19 IDs définis ; **18 disponibles /18 modèles distincts /18 BAM /1 543 frames** ; couverture de tous les BAM/frames/cycles disponibles. Pas de modèle entièrement partagé/alias dans ce lot.
- Absent : `0x4001 NULL_ANIMATION`, préfixe `SNONE`, zéro BAM ; entrée nulle, aucun sprite à inventer. Aucun autre ID du lot sans ressource ; sélection validée contre inventaire.
- Exactement un doublon source : `SNOMM` frames0/4, mêmes indices/RGB ; 1 543→**1 542 encodages uniques compatibles** ; aucun doublon de BAM entier, aucun doublon inter-modèle.
- Cache commun V7 vérifié (modèle/dépendances/noyaux/profil/échelle/planes) : **huit hits LHFC** ; **1 534 nouveaux encodages**, plafond6×1 534=9 204 cibles K6 avant éventuelles réutilisations de cibles. Les huit hits ne constituent pas une QA ingame.
- Sources : `sprite/index/{q3m-work-items,sprite_animations,sprite_resources}.csv`, `q3m-source-work-plan.json` et SQLite en lecture seule. Recette d'analyse `analyze.py`, sélection `selection.json`, résultat détaillé `analysis.json` ; `source_plan` vérifie les octets/hashes/égalité du partage, aucun appel au producteur.

| ID | Modèle natif | BAM | Frames |
|---|---|---|---:|
| 4000 | Noble homme, chaise | SNOMC | 208 |
| 4002 | Noble homme, variante MATTE | SNOMM | 104 |
| 4010 | Noble femme, chaise | SNOWC | 208 |
| 4012 | Noble femme, variante MATTE | SNOWM | 104 |
| 4100 | Paysan, chaise | SSIMC | 208 |
| 4101 | Paysan, tabouret | SSIMS | 208 |
| 4102 | Paysan, variante MATTE | SSIMM | 104 |
| 4110 | Paysanne, chaise | SSIWC | 208 |
| 4112 | Paysanne, variante MATTE | SSIWM | 104 |
| 4200 | Clerc humain, chaise | SHMCM | 13 |
| 4300 | Femme-araignée | MSPLG1 | 18 |
| 4400 | Humain endormi | LHMC | 8 |
| 4410 | Humaine endormie | LHFC | 8 |
| 4500 | Homme corpulent endormi | LFAM | 8 |
| 4600 | Nain endormi | LDMF | 8 |
| 4700 | Elfe homme endormi | LEMF | 8 |
| 4710 | Elfe femme endormie | LEFF | 8 |
| 4800 | Halfelin endormi | LIMC | 8 |

- Variantes chaise/tabouret/MATTE et homme/femme utilisent des BAM distincts : conserver chaque modèle. Les différents CRE consommant un même ID/BAM ne multiplient pas le travail.
- Avant future installation : toutes poses/cycles à produire, compatibilité native owner14 et lecture des palettes à vérifier ; vigilance petits yeux/visages, sans transposer automatiquement le renforcement spécifique du cheval. Release hors périmètre.
