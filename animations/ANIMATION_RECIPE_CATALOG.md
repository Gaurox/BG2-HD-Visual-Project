# Catalogue court des recettes animation

But : choisir une base par **structure visuelle et alpha**, puis adapter cycles, pauses et canvas.
Une ressemblance de couleur seule ne suffit pas.

| Modèle | Assets adaptés | Recette de base | Exemples `validé-x4` |
|---|---|---|---|
| `FX-FIN-XBR-AURA` | Feu, éclair, filament, particules lumineuses ; petit sujet, contours fins/fragmentés, souvent `Blended` | `xBR2 ×2` → TimedTimeline v2 Apollo-8 15→30 → Contour Aura `12/5/0.9/14` → dilatation RGB nearest-opaque ; prémultiplier si `Blended` | `AM3011B` |
| `LIQUIDE-SEEDVR-SPLINE4` | Surface liquide large et organique : bassin, lave, acide, saumure ; silhouette arrondie stable | SeedVR2 7B INT8/LAB x4 → TimedTimeline v2 Apollo-8 15→30 → Spline Fit 1 multi-contours par frame → feather intérieur `4 px x4` | `AM3021D`, `AM3021E`, `AM3021F` |
| `MECANIQUE-SEEDVR-ALPHA-NATIVE` | Roue, ventilateur, cuve, machine ; arêtes rigides, rayons et trous à préserver | SeedVR2 7B INT8/LAB x4 → TimedTimeline v2 Apollo-8 15→30 → alpha source nearest ; RGB caché nearest-opaque ; **sans spline/feather** | `AM307TT1` |
| `FUMEE-SEEDVR-SPLINE4-EDGEFADE` | Fumée ou vapeur diffuse touchant le canvas ; multi-contours, `Blended` | SeedVR2 7B INT8/LAB x4 → TimedTimeline v2 Apollo-8 15→30 → Spline Fit 1 multi-contours par frame → feather `4 px x4` → Oval Edge Fade `20/6` → RGB prémultiplié | `CHIMSMK` |
| `PORTAIL-SEEDVR-SPLINE8` | Portail elliptique à silhouette fermée et alpha binaire | SeedVR2 7B INT8/LAB x4 → TimedTimeline v2 Apollo-8 15→30 → spline périodique Fit 1 → feather intérieur `8 px x4` ; RGB inchangé | `PORTL1A`, `PORTL1B`, `PORTL2A` |

## Règles de choix

- `Blended` : neutraliser le RGB transparent et prémultiplier par l'alpha final.
- Détails fins/branches/rayons : préférer xBR ou alpha nearest ; éviter une spline destructrice.
- Silhouette organique fermée : Spline Fit 1 + feather.
- Pauses, doublons et frames vides : TimedTimeline v2 doit suivre les lookups BAM, jamais l'ordre brut des frames.
- Bord du canvas touché : ajouter un fade/canvas seulement si la coupure est visible.
- `AMWRPGT1` : variante candidate `Safe Boundary 8/6 + Gaussian 3`; non validée. Le défaut cyan connu vient du PVRZ BC1, pas de l'asset.

Sources de décision : `index/animation_upscale_registry.csv`, `index/animation_alpha_corrections.csv`, `index/qa-decisions/`.
