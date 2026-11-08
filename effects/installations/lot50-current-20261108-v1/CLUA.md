# Lot50 — commandes CLUA

Relancer BG2EE via InfinityLoader ; console Ctrl+Espace. Une commande à la fois. Tests visuels sans dégâts, cycle0 répété pendant au moins4s. Les profils natifs once/loop sont conservés séparément.

29/31/35/36/41/42/50 utilisent le noir transparent corrigé en alpha normal. Mélange des autres tests choisi pour revue ; flags des vrais consommateurs non mesurés.

```lua
-- 01 FIM1YEL · lumineux · xBR4X
C:Eval('CreateVisualEffectObject("Z50T01",Player1)',0)
-- 02 FIM2YEL · lumineux · xBR4X
C:Eval('CreateVisualEffectObject("Z50T02",Player1)',0)
-- 03 FIRE_1B · lumineux · SeedVR7B
C:Eval('CreateVisualEffectObject("Z50T03",Player1)',0)
-- 04 FIRE_1C · lumineux · SeedVR7B
C:Eval('CreateVisualEffectObject("Z50T04",Player1)',0)
-- 05 FIRE_1GR · lumineux · SeedVR7B
C:Eval('CreateVisualEffectObject("Z50T05",Player1)',0)
-- 06 FIRE_1GS · lumineux · SeedVR7B
C:Eval('CreateVisualEffectObject("Z50T06",Player1)',0)
-- 07 FIRE_2 · lumineux · SeedVR7B
C:Eval('CreateVisualEffectObject("Z50T07",Player1)',0)
-- 08 FIRE_2A · lumineux · SeedVR7B
C:Eval('CreateVisualEffectObject("Z50T08",Player1)',0)
-- 09 FIRE_4BL · lumineux · xBR4X
C:Eval('CreateVisualEffectObject("Z50T09",Player1)',0)
-- 10 FIRE_4G2 · lumineux · xBR4X
C:Eval('CreateVisualEffectObject("Z50T10",Player1)',0)
-- 11 FIRE_4GR · lumineux · xBR4X
C:Eval('CreateVisualEffectObject("Z50T11",Player1)',0)
-- 12 FISM1YEL · lumineux · xBR4X
C:Eval('CreateVisualEffectObject("Z50T12",Player1)',0)
-- 13 FLLGBLU · lumineux · xBR4X
C:Eval('CreateVisualEffectObject("Z50T13",Player1)',0)
-- 14 FLLGBLUE · lumineux · xBR4X
C:Eval('CreateVisualEffectObject("Z50T14",Player1)',0)
-- 15 FLLGRED · lumineux · SeedVR7B
C:Eval('CreateVisualEffectObject("Z50T15",Player1)',0)
-- 16 FLM1PUR · lumineux · xBR4X
C:Eval('CreateVisualEffectObject("Z50T16",Player1)',0)
-- 17 FLM1RED · lumineux · xBR4X
C:Eval('CreateVisualEffectObject("Z50T17",Player1)',0)
-- 18 FLM2RED · lumineux · xBR4X
C:Eval('CreateVisualEffectObject("Z50T18",Player1)',0)
-- 19 FLMDBLU · lumineux · xBR4X
C:Eval('CreateVisualEffectObject("Z50T19",Player1)',0)
-- 20 FLML · lumineux · xBR4X
C:Eval('CreateVisualEffectObject("Z50T20",Player1)',0)
-- 21 FLSM1PUR · lumineux · xBR4X
C:Eval('CreateVisualEffectObject("Z50T21",Player1)',0)
-- 22 FLSM1RED · lumineux · xBR4X
C:Eval('CreateVisualEffectObject("Z50T22",Player1)',0)
-- 23 LAVAFIR1 · lumineux · SeedVR7B
C:Eval('CreateVisualEffectObject("Z50T23",Player1)',0)
-- 24 EXPLODE · lumineux · SeedVR7B
C:Eval('CreateVisualEffectObject("Z50T24",Player1)',0)
-- 25 SPBDBUR · lumineux · xBR4X
C:Eval('CreateVisualEffectObject("Z50T25",Player1)',0)
-- 26 SPBDBURS · lumineux · SeedVR7B
C:Eval('CreateVisualEffectObject("Z50T26",Player1)',0)
-- 27 SPBURNS1 · lumineux · SeedVR7B
C:Eval('CreateVisualEffectObject("Z50T27",Player1)',0)
-- 28 SPFBSMAL · normal · xBR4X
C:Eval('CreateVisualEffectObject("Z50T28",Player1)',0)
-- 29 SPFINODI · normal · SeedVR7B
C:Eval('CreateVisualEffectObject("Z50T29",Player1)',0)
-- 30 SPFIRE · normal · xBR4X
C:Eval('CreateVisualEffectObject("Z50T30",Player1)',0)
-- 31 SPFIRET · normal · xBR4X
C:Eval('CreateVisualEffectObject("Z50T31",Player1)',0)
-- 32 SPFLADOW · lumineux · SeedVR7B
C:Eval('CreateVisualEffectObject("Z50T32",Player1)',0)
-- 33 SPFLSTRI · lumineux · SeedVR7B
C:Eval('CreateVisualEffectObject("Z50T33",Player1)',0)
-- 34 SPFSTRMI · lumineux · SeedVR7B
C:Eval('CreateVisualEffectObject("Z50T34",Player1)',0)
-- 35 SPPFIRAI · normal · SeedVR7B
C:Eval('CreateVisualEffectObject("Z50T35",Player1)',0)
-- 36 SPPFIRXI · normal · SeedVR7B
C:Eval('CreateVisualEffectObject("Z50T36",Player1)',0)
-- 37 SPRDRAEX · lumineux · SeedVR7B
C:Eval('CreateVisualEffectObject("Z50T37",Player1)',0)
-- 38 SPMETSWN · lumineux · SeedVR7B
C:Eval('CreateVisualEffectObject("Z50T38",Player1)',0)
-- 39 DSTDVL2A · normal · SeedVR7B
C:Eval('CreateVisualEffectObject("Z50T39",Player1)',0)
-- 40 FALLMIST · normal · xBR4X
C:Eval('CreateVisualEffectObject("Z50T40",Player1)',0)
-- 41 STEAM1 · normal · SeedVR7B
C:Eval('CreateVisualEffectObject("Z50T41",Player1)',0)
-- 42 STEAM4 · normal · SeedVR7B
C:Eval('CreateVisualEffectObject("Z50T42",Player1)',0)
-- 43 SPSMOLD · normal · xBR4X
C:Eval('CreateVisualEffectObject("Z50T43",Player1)',0)
-- 44 SPSTINK · normal · SeedVR7B
C:Eval('CreateVisualEffectObject("Z50T44",Player1)',0)
-- 45 SPAGSCHO · normal · xBR4X
C:Eval('CreateVisualEffectObject("Z50T45",Player1)',0)
-- 46 SPGREACI · lumineux · SeedVR7B
C:Eval('CreateVisualEffectObject("Z50T46",Player1)',0)
-- 47 ACIDDTH · lumineux · xBR4X
C:Eval('CreateVisualEffectObject("Z50T47",Player1)',0)
-- 48 LAVABUB1 · normal · xBR4X
C:Eval('CreateVisualEffectObject("Z50T48",Player1)',0)
-- 49 LAVABUB2 · normal · xBR4X
C:Eval('CreateVisualEffectObject("Z50T49",Player1)',0)
-- 50 SPOUTA · normal · SeedVR7B
C:Eval('CreateVisualEffectObject("Z50T50",Player1)',0)
```

[150profils](CLUA-tous-profils.md) · [Comparaison normal/lumineux](CLUA-transparence.md).
