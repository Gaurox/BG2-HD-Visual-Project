# Projectiles3 — CLUA après relance via InfinityLoader

## Tests visuels isolés, sans dégâts

Une commande à la fois, dépausé ; chaque boucle dure12secondes. Ces tests vérifient les images et la transparence, pas le trajet/les conditions des PRO.

### BGLRYU — SeedVR7B

```lua
C:Eval('CreateVisualEffectObject("ZP3T01",Player1)',0)
```

### SPCL236U — SeedVR7B

```lua
C:Eval('CreateVisualEffectObject("ZP3T02",Player1)',0)
```

### SPGLYPHI — xBR4X

```lua
C:Eval('CreateVisualEffectObject("ZP3T03",Player1)',0)
```

## Vrais sorts / propriétaires natifs

Partie de test non sauvegardée ; cible vivante éloignée. Ces sorts peuvent infliger des dégâts.

```lua
-- BGLRY / BGLRYU : Éclair de gloire
C:Eval('ForceSpellRES("SPPR612",Player2)',0)
-- SPCL236 / SPCL236U : Rayon solaire
C:Eval('ForceSpellRES("SPCL236",Player2)',0)
-- TRAPGLYP / SPGLYPHI : Glyphe de garde
C:Eval('ForceSpellRES("SPPR304",Player2)',0)
```

Glyphe : apparition des fragments au déclenchement ; placer le glyphe puis faire entrer un ennemi vivant dans sa zone. TRAPGLPN partage la même image, sans sort stock direct identifié.

## Comparaisons alpha normal

À utiliser seulement si la transparence du test principal pose problème.

```lua
C:Eval('CreateVisualEffectObject("ZP3N01",Player1)',0)
C:Eval('CreateVisualEffectObject("ZP3N02",Player1)',0)
C:Eval('CreateVisualEffectObject("ZP3N03",Player1)',0)
```

Les14profils : [CLUA-tous-profils.md](CLUA-tous-profils.md).
