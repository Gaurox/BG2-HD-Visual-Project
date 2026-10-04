# Cheval B100 — analyse œil / candidat local v3, 2026-10-04

- Demande : comparer la pose capturée, voisines et symétriques à la source ; préparer une correction durable.
- État : **candidat local vérifié, non installé, aucune QA ingame déduite**. Q3m V7/K6 x2, profile8/rule3, couleurs améliorées, CatmullRom, sans SDF.
- Pack : `sprite/.work/q3m-horse-eye-directions-20261004-v3/candidate/` ; recette `analyze.py` ; identités `candidate.json` ; résultats `analysis.json`, `verification.json`.

## Diagnostic vérifié

- Capture `E:/Steam/userdata/5536307/760/remote/257350/screenshots/20261004131339_1.jpg` compatible avec `AHRSG1` frames0–3 ; frame exacte/slot impossible à déterminer depuis cette seule capture.
- Correctif installé précédent : `../q3m-horse-eye-x2-20261004-v1/` ; AHRSG1/AHRSG1E frames11–15 seulement. Pose capturée non couverte.
- Perte déjà présente dans les cibles neurales : frame0/paletteK0, contraste peau–iris natif39,939 → cible26,809 → Q3m installé27,886. Mesure avant filtre écran ; perte principale avant encodage Q3m.
- Diagnostic des cinq frames ×six palettes : `../q3m-horse-eye-directions-20261004-v2/pipeline-stage-comparison.json` ; cibles existantes réutilisées, zéro nouvelle inférence.
- 44 frames natives examinées ; 16 frames de repos ×direct/miroir =32 présentations comparées. Cycles0/1 G1 frames0–3 ; cycles2/3 G1 frames11–14 ; cycles4/5 G1E frames0–3 (dos, œil occulté) ; cycles6/7 G1E frames11–14.
- Direction native : seuil7 ; sans miroir G1 si d≤7 sinon G1E, cycle=`seq*8+floor(d/2)` ; mode miroir G1, d>7 : cycle=`seq*8+floor((15-d)/2)`, miroir actif. Les deux modes sont couverts ; mode effectif de la capture non établi.
- Disassembly : `../q3m-horse-eye-directions-20261004-v1/native-vtable-functions.asm`, `native-constructor.asm` ; constructeurRVA307df6, direction318630, render32be60 ; exeSHA256 `b51093a49140b2b8a7c046b4652bb8e535be24ebbc12b1d735e0b94217a14d57`.

## Recette retenue

- Delta sur l'installation précédente : **AHRSG1 frames0–4**, 134 pixels x2 I/F ; 39/44 frames inchangées. Correction antérieure des dix frames de profil conservée ; G1E identique à l'installation.
- Centres guidés par les pixels de l'iris natif : f0/f3 `(8,25),(9,25),(9,26)` ; f1 `(9,25),(8,26),(9,26)` ; f2 `(9,26),(9,27)` ; f4 `(9,25),(9,26)`.
- Centre x2=`(moyenne(ancres)+0.5)*2-0.5` ; voisinage elliptique rayons3,0×2,8 pixels x2 ; d²≤1 ; poids=`exp(-1.7*d²)`.
- Cible K6 locale = moyenne RGB du cœur natif ×0,40 ; mélange avec les couleurs Q3m précédentes selon le poids ; réencodage via `Profile.encode`, classes/palette live conservées. Assombrissement volontaire et transition arrondie ; ne pas présenter ce résultat comme copie couleur exacte de l'original.
- I/F hors voisinage identiques ; dépendances recalculées sur les cinq frames ; guide/classe, centres, géométrie, cycles, représentants, sourceSHA/profil inchangés. Contour/ombres et 12 modèles acceptés hors cheval préservés.
- 44 encodages du cache partagé vérifiés inchangés. Pas de nouveau modèle neural, pas de modification globale du décodeur/runtime/shaders.

## Choix mesuré après filtre

Contraste = luminance de trois pixels de peau voisins moins moyenne du cœur de l'iris. Échantillonnage CatmullRom prémultiplié conforme à `engine/InfinityEngine-Enhancer/source-patchee/src/iee/core/creature_sprite_filter_math.cpp` ; centres des pixels écran pris en compte.

| Variante | Cas sous contraste natif /1 440 | Rapport minimum au natif | Rapport médian |
|---|---:|---:|---:|
| Cœur natif exact | 1 253 | 0,7845 | 0,9366 |
| Ellipse ×0,85 | 1 095 | 0,8579 | 0,9684 |
| Ellipse ×0,70 | 97 | 0,9066 | 1,0691 |
| Ellipse ×0,55 | 27 | 0,9589 | 1,1704 |
| **Ellipse ×0,40 retenue** | **0** | **1,0250** | **1,2812** |

- 1 440 cas/variante =5 frames ×six palettesK6 ×zooms1/2/4 ×16 phases écran (x/y=0/0,25/0,5/0,75). Tous les cas retenus améliorent le contraste installé ; gain minimum5,412 points de luminance.
- Ne pas comparer les minima séparés comme s'ils correspondaient au même cas ; `contrast-cases.json` contient les paires natives/installées/candidates.
- Limites : palettes de test K6, zooms/phases énumérés ; éclairage/fond exacts de la capture non reproduits. Ce critère mesure le contraste local, ne démontre pas à lui seul la perception ou la validation ingame de toutes les poses.

## Vérification ciblée / comparatifs

- Native : deux ressources/44 frames/878 slots ; K6 ×trois formats ; 18 572 760 pixels décodés ; `native-candidate.log`, `verification.json`, `verify.py`.
- Miroirs : 3 072 comparaisons RGBA filtrées égales sur les 16 frames de repos, six palettes et positions fractionnaires ; atlas ci-dessous inspectés.
- `capture-pose-comparison.png` : original / actuellement installé / candidat, même pose et même palette, filtres simulés.
- `directions-comparison.png` : quatre vues source et leurs miroirs ; `idle-all-{AHRSG1,AHRSG1E}-bank{0,11}.png` : toutes les frames de repos, direct/miroir.
- Installation actuelle inchangée ; catalogue actif vérifié ; 149 fichiers installés préservés vérifiés par SHA256. Aucune release.
- Historique local : v1 essai à cœur natif anguleux, métrique écran initiale non retenue ; v2 ellipse plus étroite ; mesures finales =v3. Ne pas réécrire les essais ; futur changement/installation =nouveau run.

## Installation future

- Conserver le candidat local et ses SHA ; assembler un nouveau catalogue complet à partir du parent actif en remplaçant uniquement les deux feuilles du cheval, puis vérifier les routes hors périmètre.
- AHRSG1SHA256 : `B221818737CC7EAE2144BF85FCA77DDA242C661F546902A9DF493B3D5E4B36E9` ; AHRSG1ESHA256 : `5EC41CA22F52240D439D5A7EB6C7A7A7912CB1115AAB92CD14FD5A75FC69E0E0`.
- Jeu/InfinityLoader fermés avant remplacement ; nouveau reçu/restore. CLUA cheval : `C:CreateCreature("HORSE")` ; promenade : `C:MoveToArea("AR0700")`.
- QA ingame attendue : pose capturée et phases voisines, rotation/profils/miroirs, zoom usuel ; ne pas convertir automatiquement les tests locaux en QA acceptée.
