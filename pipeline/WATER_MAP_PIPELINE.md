# Maps avec eau ou liquide — branche active

Cette branche complète [`README.md`](README.md). Elle traite l'alpha et les cellules de liquide de
la zone ; elle ne décide pas automatiquement quelle version d'un overlay global doit être
installée ou publiée.

## Gate préalable

```powershell
python pipeline/scripts/audit_water_area.py `
  ARxxxx maps/ARxxxx/runs/<run>/00_water_audit/ARxxxx-water-audit.json
```

Lire le rapport, puis exiger :

- liste exacte des resrefs de liquide ;
- nombre de cellules concernées ;
- politique d'overlay explicitement reconnue ;
- besoins `transparent-full-water-base` et lissage de contour ;
- distinction primaire/secondaire et jour/nuit.

La politique globale est `releases/BG2-HD-Upscale/manifests/overlay-sources.json` : WTLAKE,
WTPOOL et WTLAKA-D sont publiés en x2 ; WTLAVA-D en x4 ; WTSWAM, WTSEW et WTOIL restent stock.
Ne jamais déduire une échelle depuis l'override, un backup ou la présence d'un run. Une modification
exige une nouvelle QA par resref, puis la mise à jour explicite des tailles et SHA-256 du manifeste.

## Traitement de la zone

1. Upscaler les rendus de la zone en x4 selon `areas.csv` et le préflight.
2. Conserver l'alpha source ; le builder applique le rééchantillonnage bilinéaire des masques.
3. Utiliser `--transparent-full-water-base` uniquement si l'audit le demande.
4. Conserver DXT5 dès qu'une transparence existe ; ne jamais forcer DXT1.
5. Construire primaire et secondaire selon le WED, puis jour et nuit indépendamment.
6. Vérifier `0 resampled`, `0 OOB`, dimensions exactes, inventaire PVRZ et resrefs sur huit
   caractères.
7. Installer uniquement les TIS/PVRZ de zone. Un overlay partagé exige sa propre transaction et
   sa propre décision.

## Autres liquides et corrections de contour

- WTOIL, WTSEW, WTSWAM et lave : suivre aussi
  [`OTHER_LIQUID_MAP_PIPELINE.md`](OTHER_LIQUID_MAP_PIPELINE.md).
- Contour alpha en marches : appliquer
  [`GEOMETRIC_ALPHA_MASK_CLEANUP.md`](GEOMETRIC_ALPHA_MASK_CLEANUP.md), puis éventuellement
  [`SPLINE_ALPHA_MASK_PIPELINE.md`](SPLINE_ALPHA_MASK_PIPELINE.md) sur un essai isolé.
- Le cas AR0413 valide un delta TIS ciblé de sentinelles et une spline `fit 1.0`; il ne généralise
  pas automatiquement ces réglages aux autres zones. Voir [`../docs/DECISIONS.md`](../docs/DECISIONS.md).

## QA minimale

- rive proche et grande étendue de liquide ;
- primaire et secondaire ;
- jour/nuit si présents ;
- pause, reprise, transition de zone et rechargement ;
- comparaison avec le reçu d'installation et les SHA-256.

Une eau visible en pause, un cycle WTPOOL figé, une couleur marron ou un contour en marches doit
rester dans [`PROBLEMES_A_RESOUDRE.md`](PROBLEMES_A_RESOUDRE.md). Ces défauts ne sont jamais
« résolus » par la seule réussite du build.
