# Spline Fit 1 Multi-Contour / Per-Frame (Feather 4)

> Statut : recette validée le 2026-09-01 sur `CHIMSMK`. Réutilisable uniquement quand toutes les gates ci-dessous sont satisfaites ; chaque nouvel asset exige un run, une QA vidéo et une QA ingame explicites.

## Identifiant

- Nom court : `Spline Fit 1 Multi-Contour`
- Identifiant stable : `spline-fit1-multicontour-per-frame-feather4`

## Cible

- Animation `TimedTimeline` v2 dont les frames ont des géométries variables.
- Alpha 1 bit x4, plusieurs îlots possibles, silhouette coupée par le canvas.
- Ressource ARE `Blended` : RGB prémultiplié par l'alpha final.

Le script standard `build_manual_alpha_mask_30fps_v2.py` ne convient pas : il répète un masque unique et impose une géométrie uniforme.

## Recette

Pour chaque frame non vide : padding transparent, extraction de chaque composante 8-connexe, spline périodique `fit 1.0`, rasterisation ×4, recrop, feather intérieur. Les frames vides restent vides. La sortie respecte `alpha_final <= alpha_source`, conserve géométrie, centres, cycles et timeline.

```powershell
python pipeline/scripts/build_per_frame_spline_alpha_30fps_v2.py `
  --temporal-run <id-ou-chemin-run-v2> --resref <RESREF> `
  --run <nouveau-run> `
  --fit-error 1.0 --sample-spacing 1.5 --supersample 4 `
  --padding-x4 32 --inner-feather-x4 4
```

La sortie courante est `animations/ressources/<RESREF>/runs/<nouveau-run>/`. `--output` reste
réservé à une reprise legacy explicite.

### Variante validée : Oval Edge Fade 20/6

- Nom officiel : `Oval Edge Fade 20/6`
- Identifiant stable : `oval-edge-fade20x6`
- Usage : forme touchant le canvas avec coupe haut/bas visible ; 20 px x4 haut/bas, 6 px x4 côtés ; angles elliptiques.
- Validation : `CHIMSMK`, 2026-09-01. Toute autre valeur exige une QA propre.

```powershell
  --oval-top-bottom-fade-x4 20 --oval-side-fade-x4 6
```

### Variante validée : Spline Fit 1 Multi-Contour — Core Guard 16

- Nom officiel : `Spline Fit 1 Multi-Contour — Core Guard 16`
- Identifiant stable : `spline-fit1-multicontour-core-guard16`
- Usage : fumée dont le spline rogne des concavités internes ; conserver l'alpha source au-delà de 16 px x4 depuis le contour.
- Validation : `DSTDVL1A/B/C`, 2026-09-01. Toute autre épaisseur exige une QA propre.

```powershell
  --protect-source-core-x4 16
```

### Variante candidate : Timeline Active Fade 7/20/7

- Identifiant : `timeline-active-fade7-20-7`
- Usage : intervalle non vide unique de 34 phases dans une animation `TimedTimeline` mono-cycle.
- Courbe : `smoothstep` ; 7 phases d'entrée, 20 pleines, 7 de sortie.
- Coût : 14 textures clonées ; les phases vides et pleines restent partagées.

```powershell
  --active-fade-in-phases 7 `
  --active-fade-full-phases 20 `
  --active-fade-out-phases 7
```

## Gates

- Lire `spline-alpha-report.json` : aucune hausse d'alpha, composantes/frames rapportées.
- Contrôler `review-comparison-contact-sheet.png` et la boucle 30 fps.
- QA ingame explicite sur fond clair/sombre, boucle, pause et toutes les occurrences partagées.
- Tout nouvel asset doit conserver son run dérivé, son `qa-approval.json` et sa validation ingame ; l'intégration au manifeste de release reste une décision distincte.
