# Lot26 — commandes CLUA

Lancer le jeu via InfinityLoader. Une commande à la fois ; tests visuels sans dégâts, boucles bornées à au moins4s. Les contrôleurs isolés ne reproduisent pas les trajectoires PRO. SDF sans retrait pour les8désignés ; les18autres v2 conservés.

```lua
-- 01 OHBENVLP / cycle001-once
C:Eval('CreateVisualEffectObject("Z26T01",Player1)',0)
-- 02 SPHEART / cycle000-loop
C:Eval('CreateVisualEffectObject("Z26T02",Player1)',0)
-- 03 SPINSECT / cycle000-loop
C:Eval('CreateVisualEffectObject("Z26T03",Player1)',0)
-- 04 SPIPLAAI / cycle000-once
C:Eval('CreateVisualEffectObject("Z26T04",Player1)',0)
-- 05 SPIPLAUI / cycle000-loop
C:Eval('CreateVisualEffectObject("Z26T05",Player1)',0)
-- 06 SPMELBD1 / cycle000-once
C:Eval('CreateVisualEffectObject("Z26T06",Player1)',0)
-- 07 TRGOOYAA / cycle001-once
C:Eval('CreateVisualEffectObject("Z26T07",Player1)',0)
-- 08 TRGOOYBB / cycle001-once
C:Eval('CreateVisualEffectObject("Z26T08",Player1)',0)
-- 09 TRVENTAA / cycle002-once
C:Eval('CreateVisualEffectObject("Z26T09",Player1)',0)
-- 10 TRVENTBB / cycle001-once
C:Eval('CreateVisualEffectObject("Z26T10",Player1)',0)
-- 11 WRITHING / cycle001-loop
C:Eval('CreateVisualEffectObject("Z26T11",Player1)',0)
-- 12 OHRFEAR / cycle000-once
C:Eval('CreateVisualEffectObject("Z26T12",Player1)',0)
-- 13 SPANISUM / cycle000-once
C:Eval('CreateVisualEffectObject("Z26T13",Player1)',0)
-- 14 SPHANDAT / cycle000-once
C:Eval('CreateVisualEffectObject("Z26T14",Player1)',0)
-- 15 SPPROIMG / cycle000-once
C:Eval('CreateVisualEffectObject("Z26T15",Player1)',0)
-- 16 SPRAISED / cycle000-once
C:Eval('CreateVisualEffectObject("Z26T16",Player1)',0)
-- 17 SPSUMGTE / cycle000-once
C:Eval('CreateVisualEffectObject("Z26T17",Player1)',0)
-- 18 GLPHWRDT / cycle000-loop
C:Eval('CreateVisualEffectObject("Z26T18",Player1)',0)
-- 19 SKLT / cycle000-once
C:Eval('CreateVisualEffectObject("Z26T19",Player1)',0)
-- 20 SPBLBBTM / cycle000-loop
C:Eval('CreateVisualEffectObject("Z26T20",Player1)',0)
-- 21 SPBLBTOP / cycle000-loop
C:Eval('CreateVisualEffectObject("Z26T21",Player1)',0)
-- 22 SPGLBBLD / cycle000-loop
C:Eval('CreateVisualEffectObject("Z26T22",Player1)',0)
-- 23 SPSTONES / cycle000-once
C:Eval('CreateVisualEffectObject("Z26T23",Player1)',0)
-- 24 SPTRAPBB / cycle000-once
C:Eval('CreateVisualEffectObject("Z26T24",Player1)',0)
-- 25 TRAPGR / cycle000-loop
C:Eval('CreateVisualEffectObject("Z26T25",Player1)',0)
-- 26 TRSPEART / cycle000-once
C:Eval('CreateVisualEffectObject("Z26T26",Player1)',0)
```

SPIPLARI réutilise SPIPLAAI ; son alias natif est installé. [Tous les cycles/modes](CLUA-tous-profils.md).
