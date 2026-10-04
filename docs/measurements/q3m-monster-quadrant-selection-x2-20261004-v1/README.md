# Proposition — Monster_quadrant complet disponible, Q3m x2

- État : **proposition seulement**, aucune inférence/production/installation/release. Deux modèles géométriques, sept variantes natives ; famille disponible complète (7/9 IDs). Palette améliorée Q3m K6 V7 x2, CatmullRom, sans SDF.

| ID | Créature | Modèle partagé | Palette native | BAM natifs | Frames | Encodages uniques | Hits acquis |
|---|---|---|---|---:|---:|---:|---:|
| `1000` | Grande wyverne | `MWYV` | BAM | 12 | 1280 | 1240 | 200 |
| `1003` | Grande wyverne blanche | `MWYV` | `MWYV_WH` | 12 | 1280 | 1240 | 0 |
| `1004` | Wyrmling albinos | `MWYV` | `MWYV_AL` | 12 | 1280 | 1240 | 0 |
| `1100` | Tanar’ri | `MTAN` | BAM | 24 | 2272 | 2189 | 0 |
| `1102` | Fiélon bleu | `MTAN` | `MTAN_BL` | 24 | 2272 | 2189 | 0 |
| `1103` | Fiélon vert | `MTAN` | `MTAN_GR` | 24 | 2272 | 2189 | 0 |
| `1104` | Fiélon rouge | `MTAN` | `MTAN_RD` | 24 | 2272 | 2189 | 0 |

- Source physique utile : **36 BAM distincts /3 552 frames /3 427 sources uniques** ;125 répétitions de frames, aucun BAM entier identique. Géométrie/cycles partagés entre1000/1003/1004 et entre1100/1102/1103/1104. Palettes BMP disponibles/authentifiées ; couleurs différentes = contrats propres.
- Avec palettes : **132 bindings BAM /12 928 frames liées →12 476 encodages uniques** ;200 hits compatibles du pilote SHA vérifiés →**12 276 travaux nouveaux**, dont29 spéciaux sans GPU, soit**12 247 travaux avec inférence /73 482 cibles K6**. Aucun nouveau travail effectué.
- Sources absentes : **1101 DRAGON_WHITE et1105 DRAGON_GREEN_IWD**, préfixe `MWDR` sans BAM dans CHITIN.KEY ni override. Ne pas fabriquer ces animations.
- CRE :57 consommateurs stock (7 wyvernes1000,50 démons1100). Aucun CRE stock/override pour1003/1004/1102/1103/1104 ; ces cinq variantes disposent de BAM/palettes, mais nécessiteront des CRE témoins neutres à la production. Census `creatures.json` ; témoins source `C:CreateCreature("WYVERN01")`, `C:CreateCreature("TANARI01")` (scripts natifs).
- Scope natif : factory330EB4→ctor314350, vtable5AA460/render3305A0/parser341010, owner4 déjà hooké. Nom=`prefix+G1/G2/G3+part1..4`; E seulement si extend_direction=1 (MTAN). `ctor.asm`, `factory.asm`, `parser.asm`; trois banques/quatre quadrants, toutes actions/directions.
- Inventaire par préfixe :69 BAM/5 954 frames ;**33 hors appels Quadrant exclus** :7 MWYV Large16/INV déjà acquis +26 MTAN ancien format. Liste exacte dans `analysis.json`; aucune famille voisine modifiée.
- Prérequis production ciblés : étendre le validateur complet aux exclusions natives prouvées ; préserver**21 déclarations physiques 0×0 (65 occurrences couleur)**, dont certaines cyclées, sans pixels inventés ni changement de centres/cycles. Le producteur courant rejette cette géométrie ; adaptation nécessaire au futur lot. Analyse CPU tolérante locale seulement, aucun code canonique modifié.
- Plan `selection.json`; oracle source/profil/cache `analysis.json`, `plan-summary.json`. Compteurs dédupliqués sur l’union exacte ; pas de somme des compteurs globaux par ID.
