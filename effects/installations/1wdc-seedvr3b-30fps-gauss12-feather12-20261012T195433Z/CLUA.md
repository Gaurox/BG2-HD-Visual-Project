# 1WDC — test ingame

- SeedVR2 3B x4 ; Apollo 30 FPS ; 40 phases uniques/asset ; sigma 1.2 px x4 ; fondu interieur 12 px x4.
- Relancer via InfinityLoader ; console Ctrl+Espace ; executer une commande, fermer la console et reprendre le jeu.
- Visuels seuls sur Player1 ; QA ingame en attente.

## 1WDCCDAM

```lua
C:Eval('CreateVisualEffectObject("1WDCCDAM",Player1)',0)
```

## 1WDCLDAM

```lua
C:Eval('CreateVisualEffectObject("1WDCLDAM",Player1)',0)
```

## 1WDCMDAM

```lua
C:Eval('CreateVisualEffectObject("1WDCMDAM",Player1)',0)
```

## 1WDCSDAM

```lua
C:Eval('CreateVisualEffectObject("1WDCSDAM",Player1)',0)
```

## Appel direct VVC

```lua
C:CreateVEFVidCell("1WDCCDAM")
C:CreateVEFVidCell("1WDCLDAM")
C:CreateVEFVidCell("1WDCMDAM")
C:CreateVEFVidCell("1WDCSDAM")
```

## Restauration

Recu : `effects/installations/1wdc-seedvr3b-30fps-gauss12-feather12-20261012T195433Z/backups/20261012T195820952749Z-18eb517e/renderer-install-receipt.json`. Fermer jeu et InfinityLoader.

```powershell
python -B engine/InfinityEngine-Enhancer/source-patchee/tools/install_renderer_candidate.py restore "effects/installations/1wdc-seedvr3b-30fps-gauss12-feather12-20261012T195433Z/backups/20261012T195820952749Z-18eb517e/renderer-install-receipt.json"
```
