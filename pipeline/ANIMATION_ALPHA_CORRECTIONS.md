# Corrections alpha post-upscale — animations BAM

## But et garde-fous

Ce document ne remplace pas le pipeline standard. Il ne s'applique qu'après une
QA x4 où le RGB, les dimensions logiques, l'ancrage et la cadence sont déjà
validés, mais où un contour ou la bordure du canvas reste visible.

- ne modifier que l'alpha des PNG x4 et des buffers `.rgba` runtime ;
- préserver les trois canaux RGB octet pour octet ;
- ne jamais étendre le masque source : `alpha_final <= alpha_source` ;
- générer une variante isolée dans `proto/<RESREF>-.../`, jamais dans le run
  canonique ou son `03_runtime_pack` ;
- installer uniquement les assets concernés, jeu et `InfinityLoader` fermés ;
- sauvegarder les assets actifs, vérifier les SHA-256, puis faire une QA en jeu ;
- enregistrer chaque correctif retenu dans
  [`../animations/index/animation_alpha_corrections.csv`](../animations/index/animation_alpha_corrections.csv).
- mettre à jour aussi le `status`, le `correction_id` et la note du BAM dans
  [`../animations/index/animation_upscale_registry.csv`](../animations/index/animation_upscale_registry.csv).

## Choix du correctif

| Symptôme validé en jeu | Correction | Valeur de départ x4 | Effet et limite |
|---|---|---:|---|
| Liseré dur autour de l'objet | Fondu intérieur de silhouette | 8 px | Le bord devient transparent puis remonte progressivement à l'opacité source. Ne pas dépasser sans QA : cela adoucit l'objet. |
| Raccord objet/sol validé mais carré du canvas encore visible | Ajouter un fondu sur le bord du canvas | 32 px | Fondu sur les quatre bords du PNG. Il ne modifie pas le centre ni le RGB, mais adoucit un objet qui touche le bord du canvas. |
| Sol, halo ou silhouette doivent être séparés précisément | Masque manuel | — | Un masque x4 dédié est préférable. Blanc = conserver, noir = retirer, gris = transition. |
| Grande silhouette avec contour x4 en gros escaliers | Masque spline manuel | `fit-error 1.0` | Lisse la trajectoire du contour ; génération et QA explicitement manuelles dans [`SPLINE_ALPHA_MASK_PIPELINE.md`](SPLINE_ALPHA_MASK_PIPELINE.md). |
| Très petit effet, eau ou flamme mal interprétée | Désactiver ou refaire un prototype | — | Ne pas publier un fondu qui détruit la lisibilité. |

## Opérations autorisées

### 1. Fondu intérieur de silhouette

À partir de `alpha_source > 0`, calculer la distance au pixel transparent le plus
proche, en considérant l'extérieur du canvas comme transparent. Pour un rayon `r` :

```text
t = clamp((distance - 1) / r, 0, 1)
alpha_objet = alpha_source * smoothstep(t)
```

Le premier pixel de bord est `0`, le centre de la silhouette conserve l'alpha
source. Référence : `AM0602F`, `r = 8 px x4` = `2 px x1`.

### 2. Fondu du canvas complet

À ajouter après le fondu objet si la zone de décor intégrée à la frame crée encore
un rectangle visible. Calculer la distance au bord du canvas :

```text
d_canvas = min(x, largeur - 1 - x, y, hauteur - 1 - y)
t_canvas = clamp(d_canvas / r_canvas, 0, 1)
alpha_final = alpha_objet * smoothstep(t_canvas)
```

Référence validée : `AM0602F`, `r_canvas = 32 px x4` = `8 px x1`, sur les quatre
bords. Si une partie importante de l'objet touche un bord, tester d'abord un rayon
plus court, un fondu limité à certains côtés, ou un masque manuel.

Deuxième référence validée : `AM0205A`, 27 frames interpolées x4 de `480×700`
px, `r_canvas = 32 px x4` sur les quatre bords **sans** fondu intérieur. Le
RGB, la cadence de 15 FPS et le registre runtime sont inchangés.

## Production d'une variante de test

Entrées : les `rgba/frame_XXX.png` x4 terminés. Sorties minimales :

```text
proto/<RESREF>-<correctif>/
  rgba/frame_XXX.png       # RGB inchangé + alpha corrigé
  alpha/frame_XXX.png
  raw_rgba/AAX4-<RESREF>-frameXXX.rgba
  preview/frame_000-comparison.png
  manifest.json            # rayon, hashes, dimensions, inventaire
  Install-...ps1
  Restore-...ps1
```

Contrôles avant installation :

1. mêmes 3 canaux RGB que la frame x4 source ;
2. même taille PNG et `largeur × hauteur × 4` octets pour chaque buffer ;
3. aucun alpha final supérieur à l'alpha source ;
4. bord du canvas à alpha `0` pour un fondu de canvas ;
5. hashes de tous les assets source, de test et de sauvegarde ;
6. une seule variable visuelle modifiée par essai.

### Masque manuel sur un run `TimedTimeline` 30 fps

Ne jamais modifier le run temporel accepté ni son pack. Construire une dérivée complète avec
`build_manual_alpha_mask_30fps_v2.py`. Le run source doit couvrir le ou les resrefs masqués et
être basé sur le registre actuellement actif.

```powershell
python pipeline/scripts/build_manual_alpha_mask_30fps_v2.py `
  --temporal-run animations/runs/<run-30fps> `
  --resref <RESREF> `
  --mask proto/<RESREF>-manual-mask-x4/masks/frame_000.png `
  --output animations/runs/<resref>-manual-mask-30fps-v2
```

Le masque doit être monochrome, même dimensions x4 que les frames. Blanc conserve l'alpha source,
noir retire, gris multiplie l'alpha. Le RGB reste octet-identique. Ce mode répète le masque fourni
sur les anchors et les phases interpolées ; l'employer seulement pour une géométrie uniforme. Un
run temporal groupé peut être dérivé avec plusieurs paires `--resref` / `--mask` : chaque masque
reste limité à son resref et le pack conserve les autres ressources sans changement.

Le pack dérivé classe les anchors modifiés comme `replacement_assets` et les phases interpolées
comme `new_assets`. Après review et `approve`, installer avec
`Install-AreaAnimations-30fps-V2.ps1` ; il vérifie les hashes actifs, sauvegarde les anchors avant
écrasement et `Restore-AreaAnimations-30fps-V2.ps1` les restaure. Ne jamais copier les `.rgba` à la
main.

## Référence réutilisable : AM0602F

| Champ | Valeur |
|---|---|
| Ressource / zone | `AM0602F` / `AR0602` |
| Élément | Lanterne avec sol et halo intégrés dans les frames |
| Frames | 9 × `660×780` px x4 |
| Correctif retenu | fondu silhouette `8 px x4` + fondu canvas `32 px x4` sur 4 côtés |
| RGB | inchangé |
| Validation | utilisateur, 2026-08-20 |
| Prototype | `proto/AM0602F-lanterne-canvas-feather-x4/` |

Ce correctif est une **recette de prototype validée**, pas une modification
rétroactive du run canonique. Pour un autre BAM, repartir de ses frames x4 et
produire un nouveau prototype, puis ajouter une ligne au registre après QA.

## Référence complémentaire : AM0205A

| Champ | Valeur |
|---|---|
| Ressource / zone | `AM0205A` / `AR0205` |
| Élément | Premier pod au sol |
| Frames | 27 × `480×700` px x4, interpolées à 15 FPS |
| Correctif retenu | Fondu canvas seul `32 px x4` sur 4 côtés |
| RGB / registre | Inchangés |
| Validation | utilisateur, 2026-08-21 |
| Prototype | `proto/AM0205A-pod-canvas-feather-x4/` |

## Référence complémentaire : AM0205B

| Champ | Valeur |
|---|---|
| Ressource / zone | `AM0205B` / `AR0205` |
| Élément | Pod au sol, position 2027,401 |
| Frames | 27 × `600×580` px x4, interpolées à 15 FPS |
| Correctif retenu | Fondu canvas seul `32 px x4` sur 4 côtés |
| RGB / registre | Inchangés |
| Validation | utilisateur, 2026-08-21 |
| Prototype | `proto/AM0205B-pod-canvas-feather-x4/` |

## Référence complémentaire : AM0205C

| Champ | Valeur |
|---|---|
| Ressource / zone | `AM0205C` / `AR0205` |
| Élément | Pod au sol, position 3076,1586 |
| Frames | 27 × `620×520` px x4, interpolées à 15 FPS |
| Correctif retenu | Fondu canvas seul `32 px x4` sur 4 côtés |
| RGB / registre | Inchangés |
| Validation | utilisateur, 2026-08-21 |
| Prototype | `proto/AM0205C-pod-canvas-feather-x4/` |
| Particularité | Premier resref traité avec le pipeline `interpolate` automatisé (Topaz, boucle fermée) |

## Référence complémentaire : AM0205D

| Champ | Valeur |
|---|---|
| Ressource / zone | `AM0205D` / `AR0205` |
| Élément | Pod au sol, position 1295,2360 |
| Frames | 27 × `520×600` px x4, interpolées à 15 FPS |
| Correctif retenu | Fondu canvas seul `32 px x4` sur 4 côtés |
| RGB / registre | Inchangés |
| Validation | utilisateur, 2026-08-21 |
| Prototype | `proto/AM0205D-pod-canvas-feather-x4/` |
| Particularité | Pipeline `interpolate` automatisé ; série AM0205 (A à E) complète |
