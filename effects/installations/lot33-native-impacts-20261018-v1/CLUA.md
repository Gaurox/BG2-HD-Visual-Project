# Lot33 — commandes CLUA

Relancer via InfinityLoader ; console Ctrl+Espace. Une commande à la fois. Tests visuels sans dégâts ; boucles bornées à au moins4s. SeedVR7B x4/Apollo30 ; durée des cycles natifs conservée sur base15FPS de compatibilité.

Modes de test : lumineux pour feu/froid/rayons et SPHORPUF ; normal pour les autres fumées/matériaux/sang. Ces choix ne prouvent pas les flags natifs des vrais sorts.

```lua
-- 01 SPBOOM / cycle000-once / blended
C:Eval('CreateVisualEffectObject("Z33T01",Player1)',0)
-- 02 SPBRNHND / cycle004-once / blended
C:Eval('CreateVisualEffectObject("Z33T02",Player1)',0)
-- 03 SPBURN / cycle000-once / blended
C:Eval('CreateVisualEffectObject("Z33T03",Player1)',0)
-- 04 SPMETSWM / cycle001-once / blended
C:Eval('CreateVisualEffectObject("Z33T04",Player1)',0)
-- 05 SPRDRASI / cycle003-once / blended
C:Eval('CreateVisualEffectObject("Z33T05",Player1)',0)
-- 06 SPCCOLDL / cycle002-once / blended
C:Eval('CreateVisualEffectObject("Z33T06",Player1)',0)
-- 07 SPICESTM / cycle002-once / blended
C:Eval('CreateVisualEffectObject("Z33T07",Player1)',0)
-- 08 SPSCORIC / cycle002-once / blended
C:Eval('CreateVisualEffectObject("Z33T08",Player1)',0)
-- 09 HLYMITE / cycle000-once / blended
C:Eval('CreateVisualEffectObject("Z33T09",Player1)',0)
-- 10 SHAREA / cycle000-once / blended
C:Eval('CreateVisualEffectObject("Z33T10",Player1)',0)
-- 11 SHEARTH / cycle000-once / blended
C:Eval('CreateVisualEffectObject("Z33T11",Player1)',0)
-- 12 SHWATER / cycle000-once / blended
C:Eval('CreateVisualEffectObject("Z33T12",Player1)',0)
-- 13 SPGENHLA / cycle000-once / blended
C:Eval('CreateVisualEffectObject("Z33T13",Player1)',0)
-- 14 SPHLYSM2 / cycle000-once / blended
C:Eval('CreateVisualEffectObject("Z33T14",Player1)',0)
-- 15 SPHLYSM3 / cycle000-once / blended
C:Eval('CreateVisualEffectObject("Z33T15",Player1)',0)
-- 16 SPUNHBL2 / cycle000-once / blended
C:Eval('CreateVisualEffectObject("Z33T16",Player1)',0)
-- 17 SPUNHBL3 / cycle000-once / blended
C:Eval('CreateVisualEffectObject("Z33T17",Player1)',0)
-- 18 SPCSPRA2 / cycle000-once / blended
C:Eval('CreateVisualEffectObject("Z33T18",Player1)',0)
-- 19 SPCSPRA3 / cycle000-once / blended
C:Eval('CreateVisualEffectObject("Z33T19",Player1)',0)
-- 20 SPPRISM2 / cycle000-once / blended
C:Eval('CreateVisualEffectObject("Z33T20",Player1)',0)
-- 21 SPSPARKS / cycle000-once / blended
C:Eval('CreateVisualEffectObject("Z33T21",Player1)',0)
-- 22 SPHORPUF / cycle000-once / blended
C:Eval('CreateVisualEffectObject("Z33T22",Player1)',0)
-- 23 SPRING / cycle000-once / normal
C:Eval('CreateVisualEffectObject("Z33T23",Player1)',0)
-- 24 SPSMKJET / cycle000-once / normal
C:Eval('CreateVisualEffectObject("Z33T24",Player1)',0)
-- 25 SPSMPUFF / cycle000-once / normal
C:Eval('CreateVisualEffectObject("Z33T25",Player1)',0)
-- 26 STNKCLDD / cycle000-once / normal
C:Eval('CreateVisualEffectObject("Z33T26",Player1)',0)
-- 27 BLOODCR / cycle000-once / normal
C:Eval('CreateVisualEffectObject("Z33T27",Player1)',0)
-- 28 BLOODL / cycle000-once / normal
C:Eval('CreateVisualEffectObject("Z33T28",Player1)',0)
-- 29 BLOODM / cycle000-once / normal
C:Eval('CreateVisualEffectObject("Z33T29",Player1)',0)
-- 30 BLOODS / cycle000-once / normal
C:Eval('CreateVisualEffectObject("Z33T30",Player1)',0)
-- 31 SPBLOOD / cycle003-once / normal
C:Eval('CreateVisualEffectObject("Z33T31",Player1)',0)
-- 32 SPCHUNKS / cycle004-once / normal
C:Eval('CreateVisualEffectObject("Z33T32",Player1)',0)
-- 33 SPDEATH3 / cycle000-once / normal
C:Eval('CreateVisualEffectObject("Z33T33",Player1)',0)
```

[Tous les182profils](CLUA-tous-profils.md) ; [comparaison normal/lumineux pour les33](CLUA-transparence.md). BURNHAND réutilise SPBRNHND ; SPPRISM3/SPPRISMT réutilisent SPPRISM2. Ces tests VVC passent par un owner pris en charge ; les chemins natifs des vrais sorts restent à observer.
