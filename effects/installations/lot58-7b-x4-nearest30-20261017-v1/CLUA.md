# Lot58 — commandes CLUA

Jeu lancé via InfinityLoader ; exécuter séparément. VVC Z58 : tests visuels isolés, sans dégâts. Boucles bornées à au moins 4 s ; période native conservée. Ils ne reproduisent pas le trajet/la dispersion des PRO.

## Incantations

```lua
-- 01 CGABJURA / cycle002-loop
C:Eval('CreateVisualEffectObject("Z580006",Player1)',0)
-- 02 CGALTERA / cycle002-loop
C:Eval('CreateVisualEffectObject("Z580012",Player1)',0)
-- 03 CGCONJUR / cycle002-loop
C:Eval('CreateVisualEffectObject("Z580018",Player1)',0)
-- 04 CGDIVINA / cycle002-once
C:Eval('CreateVisualEffectObject("Z580023",Player1)',0)
-- 05 CGENCHAN / cycle002-once
C:Eval('CreateVisualEffectObject("Z580029",Player1)',0)
-- 06 CGILLUSI / cycle002-loop
C:Eval('CreateVisualEffectObject("Z580036",Player1)',0)
-- 07 CGINVOCA / cycle002-loop
C:Eval('CreateVisualEffectObject("Z580042",Player1)',0)
-- 08 CGNECROM / cycle002-loop
C:Eval('CreateVisualEffectObject("Z580048",Player1)',0)
```

## Feu, explosions et souffles

```lua
-- 09 BDSFIREA / cycle003-loop
C:Eval('CreateVisualEffectObject("Z580056",Player1)',0)
-- 10 BDSFIREH / cycle000-once
C:Eval('CreateVisualEffectObject("Z580057",Player1)',0)
-- 11 BDSFIRET / cycle003-once
C:Eval('CreateVisualEffectObject("Z580065",Player1)',0)
-- 12 FDAWNA / cycle000-once
C:Eval('CreateVisualEffectObject("Z580077",Player1)',0)
-- 13 FIREBAT / cycle000-loop
C:Eval('CreateVisualEffectObject("Z580080",Player1)',0)
-- 14 FIREBGRR / cycle006-once
C:Eval('CreateVisualEffectObject("Z580095",Player1)',0)
-- 15 FIREBGRT / cycle000-loop
C:Eval('CreateVisualEffectObject("Z580120",Player1)',0)
-- 16 FIREBGRX / cycle000-loop
C:Eval('CreateVisualEffectObject("Z580124",Player1)',0)
-- 17 FIREBICR / cycle006-loop
C:Eval('CreateVisualEffectObject("Z580138",Player1)',0)
-- 18 FIREBICT / cycle000-loop
C:Eval('CreateVisualEffectObject("Z580162",Player1)',0)
-- 19 FIREBICX / cycle000-loop
C:Eval('CreateVisualEffectObject("Z580166",Player1)',0)
-- 20 FSEEDA / cycle001-loop
C:Eval('CreateVisualEffectObject("Z580170",Player1)',0)
-- 21 FSEEDX / cycle000-loop
C:Eval('CreateVisualEffectObject("Z580176",Player1)',0)
-- 22 HDFBRER / cycle000-loop
C:Eval('CreateVisualEffectObject("Z580178",Player1)',0)
-- 23 SPBDIMSP / cycle000-loop
C:Eval('CreateVisualEffectObject("Z580180",Player1)',0)
-- 24 SPBDRAE2 / cycle002-loop
C:Eval('CreateVisualEffectObject("Z580186",Player1)',0)
-- 25 SPBHANDI / cycle000-once
C:Eval('CreateVisualEffectObject("Z580187",Player1)',0)
-- 26 SPFIRSDI / cycle000-once
C:Eval('CreateVisualEffectObject("Z580189",Player1)',0)
-- 27 SPFIRSE2 / cycle004-loop
C:Eval('CreateVisualEffectObject("Z580199",Player1)',0)
-- 28 SPFIRSED / cycle004-once
C:Eval('CreateVisualEffectObject("Z580208",Player1)',0)
-- 29 SPFLAST1 / cycle000-once
C:Eval('CreateVisualEffectObject("Z580210",Player1)',0)
-- 30 SPFLMBLD / cycle000-once
C:Eval('CreateVisualEffectObject("Z580211",Player1)',0)
-- 31 SPINCINA / cycle004-once
C:Eval('CreateVisualEffectObject("Z580220",Player1)',0)
-- 32 SPRDRAE2 / cycle002-once
C:Eval('CreateVisualEffectObject("Z580226",Player1)',0)
-- 33 SPRDRAIM / cycle000-once
C:Eval('CreateVisualEffectObject("Z580228",Player1)',0)
-- 34 SPSCORCH / cycle004-loop
C:Eval('CreateVisualEffectObject("Z580239",Player1)',0)
-- 35 SPSDBUR / cycle003-loop
C:Eval('CreateVisualEffectObject("Z580247",Player1)',0)
-- 36 SPSETSH / cycle000-loop
C:Eval('CreateVisualEffectObject("Z580259",Player1)',0)
```

## Nuages et fumées magiques

```lua
-- 37 BDWOFOGA / cycle004-loop
C:Eval('CreateVisualEffectObject("Z580269",Player1)',0)
-- 38 SPCLOUDK / cycle002-once
C:Eval('CreateVisualEffectObject("Z580278",Player1)',0)
-- 39 SPCLOUDS / cycle002-once
C:Eval('CreateVisualEffectObject("Z580290",Player1)',0)
-- 40 SPDFOGA / cycle001-once
C:Eval('CreateVisualEffectObject("Z580300",Player1)',0)
-- 41 SPHORWIA / cycle002-once
C:Eval('CreateVisualEffectObject("Z580310",Player1)',0)
-- 42 SPHORWIL / cycle000-loop
C:Eval('CreateVisualEffectObject("Z580315",Player1)',0)
```

## Orbes, éclairs et énergie

```lua
-- 43 BGLRYT / cycle000-loop
C:Eval('CreateVisualEffectObject("Z580317",Player1)',0)
-- 44 MINORGLB / cycle000-loop
C:Eval('CreateVisualEffectObject("Z580318",Player1)',0)
-- 45 MSUMM1H / cycle002-once
C:Eval('CreateVisualEffectObject("Z580321",Player1)',0)
-- 46 OHBGOLD / cycle000-loop
C:Eval('CreateVisualEffectObject("Z580322",Player1)',0)
-- 47 SKYBOLT / cycle000-loop
C:Eval('CreateVisualEffectObject("Z580324",Player1)',0)
-- 48 SPBGBFST / cycle001-once
C:Eval('CreateVisualEffectObject("Z580326",Player1)',0)
-- 49 SPCHRORB / cycle000-loop
C:Eval('CreateVisualEffectObject("Z580330",Player1)',0)
-- 50 SPCL236 / cycle000-loop
C:Eval('CreateVisualEffectObject("Z580334",Player1)',0)
-- 51 SPCL239R / cycle000-loop
C:Eval('CreateVisualEffectObject("Z580336",Player1)',0)
-- 52 SPCOMETT / cycle003-once
C:Eval('CreateVisualEffectObject("Z580343",Player1)',0)
-- 53 SPENBLD / cycle000-loop
C:Eval('CreateVisualEffectObject("Z580348",Player1)',0)
-- 54 SPGLYPTI / cycle000-loop
C:Eval('CreateVisualEffectObject("Z580350",Player1)',0)
-- 55 SPLIGHTB / cycle000-loop
C:Eval('CreateVisualEffectObject("Z580352",Player1)',0)
-- 56 SPSKULLT / cycle003-once
C:Eval('CreateVisualEffectObject("Z580367",Player1)',0)
-- 57 SPSPEART / cycle000-once
C:Eval('CreateVisualEffectObject("Z580379",Player1)',0)
-- 58 SPSTURNI / cycle000-once
C:Eval('CreateVisualEffectObject("Z580389",Player1)',0)
```

## Contrôleurs natifs VVC

```lua
-- SPFIRSDI
C:Eval('CreateVisualEffectObject("FIRENC01",Player1)',0)
-- SPFIRSDI
C:Eval('CreateVisualEffectObject("ICFIRSDI",Player1)',0)
-- SPFIRSDI
C:Eval('CreateVisualEffectObject("SPFIRSD2",Player1)',0)
-- SPFLAST1
C:Eval('CreateVisualEffectObject("SPFDAWN",Player1)',0)
-- SPFLMBLD
C:Eval('CreateVisualEffectObject("SPFLBLAD",Player1)',0)
-- SPFLMBLD
C:Eval('CreateVisualEffectObject("SPFLMBLD",Player1)',0)
-- MINORGLB
C:Eval('CreateVisualEffectObject("MINORGLB",Player1)',0)
-- MSUMM1H
C:Eval('CreateVisualEffectObject("MSUMM1H",Player1)',0)
-- OHBGOLD
C:Eval('CreateVisualEffectObject("OHBGOLD",Player1)',0)
-- SPBGBFST
C:Eval('CreateVisualEffectObject("SPBGBFS1",Player1)',0)
-- SPBGBFST
C:Eval('CreateVisualEffectObject("SPBGBFS2",Player1)',0)
-- SPBGBFST
C:Eval('CreateVisualEffectObject("SPBGBFST",Player1)',0)
-- SPSTURNI
C:Eval('CreateVisualEffectObject("SPSTURNI",Player1)',0)
```

Tous les cycles et modes : [CLUA-tous-profils.md](CLUA-tous-profils.md). Les VVC natifs persistants conservent leur durée stock.
