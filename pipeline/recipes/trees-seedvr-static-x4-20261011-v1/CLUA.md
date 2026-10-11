# Vérification cinq arbres SeedVR

Lancer le jeu avec InfinityLoader ; portrait0, coordonnées logiques x1. Fermer la console après le saut. Contrôler détails d'écorce, branches fines, trous, contours et raccords avec la carte. QA non acquise.

## AR1400 — de jour

```lua
C:MoveToArea("AR1400")
C:Eval('JumpToPoint([4460.200])',0)
```

1400T001 (ancre4388,1).

```lua
C:Eval('JumpToPoint([4660.350])',0)
```

1400T002 (4556,203).

```lua
C:Eval('JumpToPoint([4930.460])',0)
```

1400T003 (4815,259).

```lua
C:Eval('JumpToPoint([3820.800])',0)
```

1400T005 (3695,611).

```lua
C:Eval('JumpToPoint([3740.1320])',0)
```

1400T004 (3635,1121).

## AR1404 — nuit permanente

```lua
C:MoveToArea("AR1404")
C:Eval('JumpToPoint([4460.200])',0)
C:Eval('JumpToPoint([4660.350])',0)
C:Eval('JumpToPoint([4930.460])',0)
C:Eval('JumpToPoint([3820.800])',0)
C:Eval('JumpToPoint([3740.1320])',0)
```

Exécuter les sauts séparément : même ordre T001/T002/T003/T005/T004. AR1404 T002 ancre4556,202 ; T0034816,261 ; autres identiques.

Éclairage précalculé par zone : AR1400LM jour / AR1404LM nuit. AR1400 la nuit reste une limite du renderer actuel, aucune correction DLL appliquée.
