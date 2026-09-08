# Spline Fit 1 Multi-Contour / Per-Frame (Feather 4)

> Statut : recette validée le 2026-09-01 sur `CHIMSMK`. Réutilisable uniquement quand toutes les gates ci-dessous sont satisfaites ; chaque nouvel asset exige un run, une QA vidéo et une QA ingame explicites.

## Identifiant

- Nom court : `Spline Fit 1 Multi-Contour`
- Identifiant stable : `spline-fit1-multicontour-per-frame-feather4`

## Cible

- Animation `TimedTimeline` v2 dont les frames ont des géométries variables.
- Alpha 1 bit x4, plusieurs îlots possibles, silhouette coupée par le canvas.
- Ressource ARE `Blended` : `--rgb-policy premultiplied` (défaut), RGB prémultiplié par l'alpha final.
- Ressource ARE alpha strict (bit `Blended` absent) : `--rgb-policy preserve`, RGB conservé et seul alpha modifié.

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

Pour un raccord horizontal entre deux BAM superposés, restaurer l'alpha source aux deux bords
en contact :

```powershell
  # BAM supérieur
  --bottom-seam-protected-depth-x4 8 --bottom-seam-transition-x4 16
  # BAM inférieur
  --top-seam-protected-depth-x4 8 --top-seam-transition-x4 16
```

### Variante candidate : raccord RGB conjoint B/C

- Usage : deux BAM `TimedTimeline` 30 fps adjacents dans le monde, alpha strict conservé mais
  discontinuité de couleur/texture sur leur bord commun.
- Outil : `build_joint_animation_rgb_seam.py`; batch multi-ressources, jamais réécriture des runs
  parents. Il vérifie les positions ARE, la géométrie, les cycles et la timeline identique.
- Effet standard : RGB modifié uniquement où les deux alphas sont au moins au seuil ; alpha,
  centres, tailles et cycles sont bit à bit identiques. Le mode `symmetric-midpoint` converge des
  deux côtés ; `continue-top-into-bottom` conserve le haut et prolonge sa texture dans le bas.
- Correctif spline borné : avec `--bottom-alpha-reference-pack`, seules les composantes connexes
  supprimées de taille au moins `--restore-removed-component-min-pixels` sont restaurées depuis
  l'alpha de référence. Les autres pixels alpha restent identiques au pack traité.
- Finition par recouvrement : `--bottom-top-overlap-x1 2` ajoute 2 lignes natives en haut du BAM
  inférieur, décale son centre Y de 2 pour conserver la pose monde, copie les dernières lignes RGB
  du BAM supérieur et applique un fade alpha `smoothstep`. Le BAM dérivé de `--bottom-source-bam`
  est obligatoire et sort dans `override-assets/` avec son manifeste installable.
- Recouvrement bilatéral : `--bilateral-extension-x1 8` étend le BAM supérieur de 8 px x1 vers
  le bas et le BAM inférieur de 8 px x1 vers le haut. Les deux images partagent le même RGB monde
  dans les 16 px x1 communs et leurs alphas suivent deux `smoothstep` complémentaires. Les deux
  BAM natifs dérivés sont obligatoires ; le centre Y inférieur reçoit `+8`, le supérieur reste fixe.

```powershell
python pipeline/scripts/build_joint_animation_rgb_seam.py `
  --top-pack <AM2805B-pack> --top-position 483,368 `
  --bottom-pack <AM2805C-pack> --bottom-position 483,553 `
  --output animations/batches/<nouveau-batch> `
  --seam-depth-x4 32 --alpha-threshold 128 `
  --blend-mode continue-top-into-bottom `
  --bottom-alpha-reference-pack <AM2805C-pack-avant-spline> `
  --restore-removed-component-min-pixels 10000 `
  --bottom-top-overlap-x1 2 --bottom-source-bam <AM2805C-source.bam> `
  --area AR2804
# Relire le plan, puis ajouter --run.
```

Pour remplacer le recouvrement unilatéral par la variante bilatérale :

```powershell
  --bilateral-extension-x1 8 `
  --top-source-bam <AM2805B-source.bam> `
  --bottom-source-bam <AM2805C-source.bam> `
  --area AR2804
```

Le fondu bilatéral suppose que la ressource basse est dessinée après la ressource haute. Il partage
le même champ RGB entre les deux assets et calcule les deux alphas pour conserver exactement la
couleur et l'opacité du composite source-over ; des alphas simplement complémentaires créent une
baisse d'opacité pouvant atteindre 25 % au centre et laissent transparaître la couleur de la map.

### Variante candidate : porteur fusionné Blended

- Usage : deux occurrences `Blended` se recouvrent et le moteur additionne deux RGB, même après
  correction des alphas.
- Outil : `build_fused_area_animation_carrier.py`, plan-only sans `--run`.
- Principe : composite source-over x4 hors ligne, RGB final prémultiplié, une seule occurrence
  `Blended` porte le résultat. L'autre occurrence pointe vers un BAM noir transparent. Une
  occurrence alpha stricte distincte peut rester sur son resref d'origine.
- Sorties : pack runtime du porteur, ARE avec seuls les deux resrefs modifiés, BAM porteur/null et
  BAM sources d'origine restaurés. Une sauvegarde ayant déjà visité la zone peut conserver son ARE.

```powershell
python pipeline/scripts/build_fused_area_animation_carrier.py `
  --top-pack <AM2805B-pack-recouvrement> --bottom-pack <AM2805C-pack-recouvrement> `
  --top-position 483,368 --bottom-position 483,553 `
  --top-source-bam animations/ressources/AM2805B/source.bam `
  --bottom-source-bam animations/ressources/AM2805C/source.bam `
  --area AR2804 --output animations/batches/<nouveau-batch>
# Relire le plan, puis ajouter --run.
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
