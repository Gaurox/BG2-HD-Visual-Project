# Test 1400T005 nuit

Relancer via InfinityLoader pour charger la DLL. Commandes séparées, portrait0, fermer la console après le saut.

```lua
C:MoveToArea("AR1404")
C:Eval('JumpToPoint([3820.800])',0)
```

AR1404 = nuit permanente ; T005 central du screenshot, ancre3695,611. Comparer sa teinte au décor.

```lua
C:MoveToArea("AR1400")
C:Eval('JumpToPoint([3820.800])',0)
```

AR1400 : comparer de jour puis de nuit, y compris transition dans la même zone. Jour inchangé ; nuit plus sombre, rouge/vert atténués. Log `AREA_TREE_NIGHT_COLOR resref=1400T005 gainsRGB=0.60,0.55,0.85` confirme activation réelle de la correction nocturne ; aucune validation visuelle déduite du log.
