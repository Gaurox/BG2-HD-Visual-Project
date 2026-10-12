# PRAYER — CLUA ingame

QA ingame utilisateur validée le 2026-10-12 pour PRAYERB, PRAYERG et SPPRAYRI. Preuves : `qa-accepted-20261012.json`, `effects/index/selections/<RESREF>.json`.

- Installation : SeedVR2 3B x4, Apollo 30 FPS, gauss sigma 1.2 px x4, fondu interieur 12 px x4.
- 39 backings uniques/BAM : 38 lumineux + 1 vide ; 100 phases natives temporelles, duree 50/15 s.
- Relancer via InfinityLoader. Console Ctrl+Espace ; executer une commande, fermer la console, reprendre le jeu.
- Cible : Player1. Ces commandes jouent le visuel sans lancer de sort.

## Sur Player1

Violet — PRAYERB :
```lua
C:Eval('CreateVisualEffectObject("PRAYERB",Player1)',0)
```
Jaune/vert — PRAYERG :
```lua
C:Eval('CreateVisualEffectObject("PRAYERG",Player1)',0)
```
Bleu — SPPRAYRI, controleur VVC ICPRAYI :
```lua
C:Eval('CreateVisualEffectObject("ICPRAYI",Player1)',0)
```

## Appel direct du VVC par la console

```lua
C:CreateVEFVidCell("PRAYERB")
C:CreateVEFVidCell("PRAYERG")
C:CreateVEFVidCell("ICPRAYI")
```

## Recu et restauration

Recu : `effects/installations/prayer-seedvr3b-30fps-gauss12-feather12-20261012T192146Z/backups/20261012T192419714216Z-859e1dc5/renderer-install-receipt.json`.
```powershell
python -B engine/InfinityEngine-Enhancer/source-patchee/tools/install_renderer_candidate.py restore "effects/installations/prayer-seedvr3b-30fps-gauss12-feather12-20261012T192146Z/backups/20261012T192419714216Z-859e1dc5/renderer-install-receipt.json"
```
Fermer le jeu et InfinityLoader avant restauration. Aucun etat QA ingame deduit.

Sources : [console IESDP](https://gibberlings3.github.io/iesdp/appendices/clua/bgee.htm), [action CreateVisualEffectObject](https://gibberlings3.github.io/iesdp/scripting/actions/bgeeactions.htm).
