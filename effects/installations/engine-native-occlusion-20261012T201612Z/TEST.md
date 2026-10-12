# Effets — occlusion native WED

- Portee : chemins communs VVC + ProjectileBAM, ressources presentes/futures du registre.
- Capture native avant/apres FXRenderClippingPolys, transfert visibilite RGB + alpha, geometrie native conservee ; aucun masque bake/map/asset.
- Capture impossible ou GPU indisponible apres clipping : dessin natif masque conserve.
- Installation moteur uniquement ; INI identique ; 441 fichiers du pack effets identiques.
- Correctif valide ingame utilisateur le 2026-10-12 sur 1WDCSDAM ; preuve : `qa-accepted-20261012.json`. Suites natives : 3 passees ; shader GPU : 4 cas x2/x4 passes.
- Relancer via InfinityLoader ; console Ctrl+Espace ; se placer derriere le decor puis fermer la console et reprendre le jeu.

```lua
C:Eval('CreateVisualEffectObject("1WDCCDAM",Player1)',0)
C:Eval('CreateVisualEffectObject("1WDCLDAM",Player1)',0)
C:Eval('CreateVisualEffectObject("1WDCMDAM",Player1)',0)
C:Eval('CreateVisualEffectObject("1WDCSDAM",Player1)',0)
C:Eval('CreateVisualEffectObject("PRAYERB",Player1)',0)
C:Eval('CreateVisualEffectObject("ICPRAYI",Player1)',0)
```

- Log : `InfinityEngine-Enhancer.log`, `owner=VVC` / `ProjectileBAM`, `replacement=effect-animation`, `stage=native-occlusion-bound`.
- Repli : `Effect native occlusion fallback: resref=...` ; trace bornee par resref.
- Recu : `effects/installations/engine-native-occlusion-20261012T201612Z/backups/20261012T201613670764Z-346aa40e/renderer-install-receipt.json`. Fermer jeu/InfinityLoader avant restauration.

```powershell
python -B engine/InfinityEngine-Enhancer/source-patchee/tools/install_renderer_candidate.py restore "effects/installations/engine-native-occlusion-20261012T201612Z/backups/20261012T201613670764Z-346aa40e/renderer-install-receipt.json"
```
