# Lot54 — CLUA

Relancer via InfinityLoader après installation. Ctrl+Espace ; exécuter une commande, fermer la console, reprendre le jeu. Cible : Player1. Ces appels jouent les visuels sans lancer les sorts. QA ingame à décider par asset.

## Flashes et halos

ABJURH → ABJURH
```lua
C:Eval('CreateVisualEffectObject("ABJURH",Player1)',0)
```

OHRSHFIE → OHRSHFIE
```lua
C:Eval('CreateVisualEffectObject("OHRSHFIE",Player1)',0)
```

SPGFLSH1 → SPGFLSH1
```lua
C:Eval('CreateVisualEffectObject("SPGFLSH1",Player1)',0)
```

BDFAVSPI → BDFAVSPI
```lua
C:Eval('CreateVisualEffectObject("BDFAVSPI",Player1)',0)
```

BDRSPIRI → BDRSPIRI
```lua
C:Eval('CreateVisualEffectObject("BDRSPIRI",Player1)',0)
```

SPRAISEI → ICRAISEI
```lua
C:Eval('CreateVisualEffectObject("ICRAISEI",Player1)',0)
```

COLDH → COLDH
```lua
C:Eval('CreateVisualEffectObject("COLDH",Player1)',0)
```

FIREH → FIREH
```lua
C:Eval('CreateVisualEffectObject("FIREH",Player1)',0)
```

MMAGICH → ICMAGICH
```lua
C:Eval('CreateVisualEffectObject("ICMAGICH",Player1)',0)
```

SPSHKIMP → SPSHKIMP
```lua
C:Eval('CreateVisualEffectObject("SPSHKIMP",Player1)',0)
```

FDAWNX → FDAWNX
```lua
C:Eval('CreateVisualEffectObject("FDAWNX",Player1)',0)
```

GRNDGLOW → FIRECOLD
```lua
C:Eval('CreateVisualEffectObject("FIRECOLD",Player1)',0)
```

SPCCMDSI → ICCCMDSI
```lua
C:Eval('CreateVisualEffectObject("ICCCMDSI",Player1)',0)
```

SPUNHOLY → SPUNHOLY
```lua
C:Eval('CreateVisualEffectObject("SPUNHOLY",Player1)',0)
```

SPDISPMA → SPDISPMA
```lua
C:Eval('CreateVisualEffectObject("SPDISPMA",Player1)',0)
```

SPHEALIN → SPHEALIN
```lua
C:Eval('CreateVisualEffectObject("SPHEALIN",Player1)',0)
```

SPHOLLYW → SPHOLY
```lua
C:Eval('CreateVisualEffectObject("SPHOLY",Player1)',0)
```

BDSPLOCK → BDSPLOCK
```lua
C:Eval('CreateVisualEffectObject("BDSPLOCK",Player1)',0)
```

## Auras et buffs lumineux

CSHIELDH → CSHIELDH
```lua
C:Eval('CreateVisualEffectObject("CSHIELDH",Player1)',0)
```

CURSEH → CURSEH
```lua
C:Eval('CreateVisualEffectObject("CURSEH",Player1)',0)
```

SPBLESHI → ICBLESAI
```lua
C:Eval('CreateVisualEffectObject("ICBLESAI",Player1)',0)
```

GARMORH → 1WDGARMR
```lua
C:Eval('CreateVisualEffectObject("1WDGARMR",Player1)',0)
```

SARMORH → 1WDSARMR
```lua
C:Eval('CreateVisualEffectObject("1WDSARMR",Player1)',0)
```

SPARMORI → ICARMOR
```lua
C:Eval('CreateVisualEffectObject("ICARMOR",Player1)',0)
```

PARALH → PARALH
```lua
C:Eval('CreateVisualEffectObject("PARALH",Player1)',0)
```

SPDHRMNY → SPDHRMNY
```lua
C:Eval('CreateVisualEffectObject("SPDHRMNY",Player1)',0)
```

SPCHMPSI → ICCHMPSI
```lua
C:Eval('CreateVisualEffectObject("ICCHMPSI",Player1)',0)
```

SPSTRENI → ICSTRENI
```lua
C:Eval('CreateVisualEffectObject("ICSTRENI",Player1)',0)
```

SPSTRONE → ICSTRONE
```lua
C:Eval('CreateVisualEffectObject("ICSTRONE",Player1)',0)
```

SPPOWATK → SPPOWATK
```lua
C:Eval('CreateVisualEffectObject("SPPOWATK",Player1)',0)
```

SPSDIMPA → SPSDIMPA
```lua
C:Eval('CreateVisualEffectObject("SPSDIMPA",Player1)',0)
```

SPTRUSEE → SPTRUSEE
```lua
C:Eval('CreateVisualEffectObject("SPTRUSEE",Player1)',0)
```

SPUSEANY → SPUSEANY
```lua
C:Eval('CreateVisualEffectObject("SPUSEANY",Player1)',0)
```

SPFDEATH → SPDEATH3
```lua
C:Eval('CreateVisualEffectObject("SPDEATH3",Player1)',0)
```

## Anneaux et sceaux

ASUMM1X → ASUMM1X
```lua
C:Eval('CreateVisualEffectObject("ASUMM1X",Player1)',0)
```

BDSHSUM → BDSHSUM
```lua
C:Eval('CreateVisualEffectObject("BDSHSUM",Player1)',0)
```

MSUMM1X → MSUMM1X
```lua
C:Eval('CreateVisualEffectObject("MSUMM1X",Player1)',0)
```

SPFRACTI → ICFRACTI
```lua
C:Eval('CreateVisualEffectObject("ICFRACTI",Player1)',0)
```

BDSPWARD → BDSPWARD
```lua
C:Eval('CreateVisualEffectObject("BDSPWARD",Player1)',0)
```

SPROTECT → SPROTECT
```lua
C:Eval('CreateVisualEffectObject("SPROTECT",Player1)',0)
```

SPFLSRIN → SPFLSRIN
```lua
C:Eval('CreateVisualEffectObject("SPFLSRIN",Player1)',0)
```

SPSETTIH → SPSETTIH
```lua
C:Eval('CreateVisualEffectObject("SPSETTIH",Player1)',0)
```

OHRDARK → OHRDARK
```lua
C:Eval('CreateVisualEffectObject("OHRDARK",Player1)',0)
```

SPPOWWRD → SPPOWWRD
```lua
C:Eval('CreateVisualEffectObject("SPPOWWRD",Player1)',0)
```

BDETHER → BDETHER
```lua
C:Eval('CreateVisualEffectObject("BDETHER",Player1)',0)
```

SHAREAW → SHAREAW
```lua
C:Eval('CreateVisualEffectObject("SHAREAW",Player1)',0)
```

## Etoiles et particules

BDSPCLAR → BDSPCLAR
```lua
C:Eval('CreateVisualEffectObject("BDSPCLAR",Player1)',0)
```

EXALTAH → EXALTAH
```lua
C:Eval('CreateVisualEffectObject("EXALTAH",Player1)',0)
```

GLDUSTH → GLDUSTH
```lua
C:Eval('CreateVisualEffectObject("GLDUSTH",Player1)',0)
```

OHRMJAR → OHRMJAR
```lua
C:Eval('CreateVisualEffectObject("OHRMJAR",Player1)',0)
```

SPNWCHRM → SPNWCHRM
```lua
C:Eval('CreateVisualEffectObject("SPNWCHRM",Player1)',0)
```

SPHLYBLS → SPHLYBLS
```lua
C:Eval('CreateVisualEffectObject("SPHLYBLS",Player1)',0)
```

SPPLANAR → SPPLANAR
```lua
C:Eval('CreateVisualEffectObject("SPPLANAR",Player1)',0)
```

SPSPMAZE → SPSPMAZE
```lua
C:Eval('CreateVisualEffectObject("SPSPMAZE",Player1)',0)
```
