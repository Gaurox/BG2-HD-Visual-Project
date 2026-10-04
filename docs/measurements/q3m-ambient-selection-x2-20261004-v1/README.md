# Prochain lot proposé — ambient complet disponible, 2026-10-04

- **Proposition uniquement, aucun traitement/installation**. Cible Q3m V7 K6 x2/quatre partenaires/huit niveaux, palette améliorée, sans SDF, palette native live/CatmullRom ; owner12 ; cinq modèles animaux fixes profile8 +11 humanoïdes à rampes profile9, règle3.
- Plus courte famille native restante en travaux source : ambient2 406, character_old3 771, autres≥5 758 ; Ogre/Flying/Ankheg/Large16/Ambient_static/Town_static déjà traités exclus, Character acquis hors choix.
- 21 IDs définis ; **18 disponibles /16 modèles distincts /34 BAM**, dont deux INV auxiliaires (ARATINV/ASQUINV, deux frames chacun). Couvrir tous les BAM/frames/cycles disponibles, sans retraiter les acquis compatibles.
- **2 580 frames physiques dans les BAM distincts** ; 2 734 si l'on additionne les consommateurs d'animation, donc154 bindings répétés à ne pas traiter une seconde fois.
- Aliases complets : chauve-souris C000/C500 (ABATG1/ABATG1E,104frames) ; rat C300/CC04 (ARATG1/ARATG1E/ARATINV,50frames). Même sprite, même contrat Q3m compatible ; préserver leurs consommateurs/directions natifs.
- Déduplication entre BAM distincts : **174 répétitions**, dont10 poule G1/G1E, quatre écureuil G1/G1E, 160 mendiant/esclave ; ces deux humanoïdes restent des modèles distincts (32 autres frames chacun). Aucun BAM de nom différent entièrement identique.
- Travail final : 2 580−174=**2 406 encodages uniques compatibles** ; cache actuel **1 024 hits authentifiés** (48 rat +976 humanoïdes uniques), donc **1 382 nouveaux encodages** (406 fixes +976 à rampes). Sommes par modèle non additives pour mendiant/esclave ; `model-summary.json` contient les unions.
- Cache : mêmes profil/source/échelle/namespace encodeur ; modèles/dépendances/noyaux vérifiés, planes I/F/guide/deps validés et SHA1024fichiers enregistrés. Au plus8 292 nouvelles cibles K6 avant éventuels hits de cibles ; ne pas confondre hits de production et QA ingame.
- **Absents** : CC00/KEG1/MKG1, CC01/KEG2/MKG2, CC02/KEG3/MKG3 ; aucun BAM. Aucun sprite de remplacement inventé.

| IDs | Modèle disponible | BAM (suffixes inclus) | Frames physiques |
|---|---|---|---:|
| C000, C500 | Chauve-souris intérieur/extérieur, un modèle | ABATG1, ABATG1E | 104 |
| C100 | Chat | ACATG1, ACATG1E | 144 |
| C200 | Poule | ACHKG1, ACHKG1E | 100 |
| C300, CC04 | Rat intérieur/extérieur, un modèle | ARATG1, ARATG1E, ARATINV | 50 |
| C400 | Écureuil | ASQUG1, ASQUG1E, ASQUINV | 70 |
| C600 | Mendiant | NBEGHG1, NBEGHG1E | 192 |
| C610 | Prostituée | NPROHG1, NPROHG1E | 192 |
| C700 | Garçon | NBOYHG1, NBOYHG1E | 192 |
| C710 | Fille | NGRLHG1, NGRLHG1E | 192 |
| C800 | Homme corpulent | NFAMHG1, NFAMHG1E | 192 |
| C810 | Femme corpulente | NFAWHG1, NFAWHG1E | 192 |
| C900 | Paysan | NSIMHG1, NSIMHG1E | 192 |
| C910 | Paysanne | NSIWHG1, NSIWHG1E | 192 |
| CA00 | Noble homme | NNOMHG1, NNOMHG1E | 192 |
| CA10 | Noble femme | NNOWHG1, NNOWHG1E | 192 |
| CB00 | Esclave | NSLVHG1, NSLVHG1E | 192 |

- Inventaire : `sprite/index/{q3m-work-items,sprite_animations,sprite_resources}.csv`, `q3m-source-work-plan.json` ; SQLite et cache en lecture seule. `analyze.py`, `selection.json`, `analysis.json`, `breakdown.py`, `model-summary.json` : égalité des indices/RGB vérifiée par `source_plan`, aucune inférence/génération/catalogue/QA/installation.
- Native futur : owner12, aliases complets conservés dans les routes, INV séparés des appels monde ; toutes poses et petits visages à comparer, géométrie/cycles/ombres natifs conservés. Pas de retouche automatique héritée du cheval ; release hors périmètre.
