# COW188 — réemploi du sprite accepté

Relancer via InfinityLoader. Utiliser une partie de test non sauvegardée, deux personnages espacés.

## Image isolée sans dégâts —12secondes

```lua
C:Eval('CreateVisualEffectObject("ZCOWV",Player1)',0)
```

## Vrai projectile COW

Le sort stock SPWI299 lance PROJECTL188 / missile189 ; cible vivante éloignée, sort offensif.

```lua
C:Eval('ForceSpellRES("SPWI299",Player2)',0)
```

Source : ACOWG1 Q3m V7 x2 déjà accepté côté sprites.22frames/40cycles natifs ; support effet x4 par duplication2× exacte, aucune inférence ni interpolation ajoutée. Le déplacement reste natif. La QA du sprite n’est pas une QA du projectile COW.
