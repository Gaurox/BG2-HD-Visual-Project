# Prochain lot proposé — Character_old complet disponible, Q3m x2

- **Proposition uniquement**, aucune production/inférence/installation. Cible : Q3m V7 K6/quatre partenaires/huit niveaux, palette améliorée live, x2/CatmullRom, **sans SDF** ; owner6, profils8 fixe/9 rampes. Toutes frames/cycles/directions des ressources natives propres à la famille, CMNKINV auxiliaire inclus ; couches d'équipement partagées conservées sur leurs acquis.
- Famille restante la plus courte selon le plan source : **3 771 travaux uniques**, devant Monster_layered5 758, Monster_quadrant5 768, Monster_old6 701, Multi_new17 103, Monster_icewind81 499, Monster86 963, Character563 969. Références `sprite/index/q3m-work-tracking.json`, `q3m-source-work-plan.json`, `palette-work-plan.json` ; nombres source, pas coûts GPU mesurés.
- **7 IDs avec BAM sur8 définis ; six ensembles de sprites, dont cinq corps visibles +un ensemble transparent ; 99 BAM distincts/4 725 frames physiques**. Alias6405/6406 partage22BAM/936frames ; comptage par binding =121ressources/5 661frames. Pas de duplication de traitement de cet alias.

| IDs | Modèle natif / préfixe | Palette | BAM | Frames physiques | Travaux uniques | Cache compatible | Nouveaux travaux |
|---|---|---|---:|---:|---:|---:|---:|
| 6400 | Drizzt / UDRZ1 | Rampes | 12 | 656 | 656 | 288 | 368 |
| 6401 | Elminster / UELM1 | Fixe | 10 | 608 | 608 | 0 | 608 |
| 6402 | Moine / CMNK1 +CMNKINV | Rampes | 23 | 938 | 938 | 0 | 938 |
| 6403 | Squelette / MSKL1 | Rampes | 22 | 971 | 961 | 0 | 961 |
| 6404 | Sarevok / USAR1 | Fixe | 10 | 616 | 568 | 0 | 568 |
| 6405 +6406 | Garde funeste +variante Larger / MDGU1, **corps transparents natifs** | Rampes | 22 partagés | 936 | 40 | 0 | 40 |
| **Total physique** | **6 ensembles /7 IDs** | | **99** | **4 725** | **3 771** | **288** | **3 483** |

- **Absent** : 6621 `FIGHTER_FEMALE_HUMAN_BG1`, préfixe XHFF, aucun BAM ; exclu explicitement. **Présents mais transparents** : les22BAM MDGU1, toutes936frames ; ne pas inventer un corps pour6405/6406. Les deux INI diffèrent ellipse16→24/personal_space3→7 ; aucun agrandissement raster déduit du symbole `LARGER`.
- Déduplication : **954 répétitions entre BAM distincts** =936−40=896 MDGU +48 Sarevok +10 squelette. Deux groupes de BAM entiers identiques : `MDGU1A2/MDGU1A3/MDGU1A4`, mêmes suffixes E ; transparents. Géométries/cycles/resrefs source restent des bindings distincts. 936bindings répétés de l'alias comptés séparément.
- Cache acquis Q3m V7 : **288 hits Drizzt vérifiés** (plans/dimensions/profil/backend/model/kernels/deps SHA), **3 483 travaux manquants**, dont41travaux entièrement transparents sans inférence (40MDGU +un squelette). Aucun retraitement pour les hits ; autres coûts neuronaux à déterminer par le producteur selon le cache de cibles.
- Preuves de sélection : `analyze.py`, `selection.json`, `analysis.json` ; `breakdown.py`, `model-summary.json` donnent nombres physiques/logiques, alias/cache et22sources transparentes. Lecture seule des source SQLite/caches et oracle arithmétique palette natif ; aucun pack/dossier de production/installation créé.
