# Arbres — test éclairage dynamique

Relancer via InfinityLoader pour charger la nouvelle DLL. Coordonnées logiques x1, portrait0 ; fermer la console entre chaque saut.

```lua
C:MoveToArea("AR1400")
C:Eval('JumpToPoint([4460.200])',0)
C:Eval('JumpToPoint([4660.350])',0)
C:Eval('JumpToPoint([4930.460])',0)
C:Eval('JumpToPoint([3820.800])',0)
C:Eval('JumpToPoint([3740.1320])',0)
```

Sauts séparés : T001, T002, T003, T005, T004. Comparer AR1400 de jour puis de nuit, ainsi qu'un changement d'heure dans la même zone : assombrissement/teinte et absence de texture de jour en cache. Alpha, branches fines et raccords à surveiller.

```lua
C:MoveToArea("AR1404")
C:Eval('JumpToPoint([3820.800])',0)
```

AR1404 nuit permanente : T005 du screenshot ; mêmes cinq positions disponibles. Anciennes textures baked remplacées par cet essai dynamique.

Log `AREA_NATIVE_LIGHTING` : succès avec fingerprint/midRGB/flags ; `owner palette unavailable/incompatible; native BAM retained` signifie fallback vanilla, pas validation du rendu x4.
