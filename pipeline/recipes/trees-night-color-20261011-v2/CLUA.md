# T002/T003 — contrôle nocturne

Relancer via InfinityLoader. Nuit permanente, commandes séparées ; fermer la console après chaque saut.

```lua
C:MoveToArea("AR1404")
C:Eval('JumpToPoint([4660.350])',0)
C:Eval('JumpToPoint([4930.460])',0)
```

Premier saut = T002 branches suspendues ; second = T003 grand tronc. En AR1400, mêmes positions pour comparaison jour/nuit : `C:MoveToArea("AR1400")`. Jour inchangé.

T005 validé conservé : `C:Eval('JumpToPoint([3820.800])',0)`. Logs `AREA_TREE_NIGHT_COLOR resref=1400T002`, `1400T003`, `1400T005` confirment activation nocturne avec gains0.60/0.55/0.85 ; aucune QA visuelle déduite du log.
