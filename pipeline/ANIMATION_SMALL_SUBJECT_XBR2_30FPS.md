# Petits sujets — xBR2 → Nearest2 x4 / Apollo30 RGB-Safe

> Statut : recette sans blend validée le 2026-09-01 sur `BUTRFLY`. Variante `--xbr-blend`
> validée le 2026-09-05 uniquement sur `BUBBLES2`. Chaque resref requiert son propre run, QA vidéo
> et QA ingame explicite.

## Identifiant

- Nom officiel : `Small Subject xBR2 → Nearest2 x4 / Apollo30 RGB-Safe`
- Identifiant stable : `small-subject-xbr2-nearest2-apollo30-rgb-safe`
- Référence : `BUTRFLY`, spatial `butrfly-xbr2x-nearest2-x4`, temporel
  `butrfly-xbr2x-nearest2-x4-30fps-v3-opaque-rgb-dilate`.

## Gates d'entrée

- BAM V1 à palette intégrée, frames séparables et centres/cycles exploitables.
- Sujet petit mais silhouette effectivement lisible à x1 ; conserver le natif sous ~2 px x1.
- Pixel art net : pas de lissage, pas de blend xBR, pas de reconstruction générative.
- Si `alpha=0` porte un chroma key ou une couleur parasite, utiliser `nearest-opaque-dilate` pour
  l'entrée Topaz ; sinon conserver `preserve-hidden-rgb`.
- Si l'occurrence ARE est `Blended`, appliquer la neutralisation RGB finale ; `zero` seulement si
  alpha strictement binaire, sinon `premultiply`.

## Recette figée

1. Extraire BAM, RGB et alpha séparés ; conserver source hash, dimensions, centres, cycles et ordre.
2. Spatial : `xBR 2x`, une passe, `xbr_blend=false`, sans AA ; agrandir ensuite `nearest 2x` vers
   x4. L'adaptateur raster approuvé est `pipeline/scripts/xbr2x_batch.js` avec le contrat
   [`../sprite/XBR2X_RASTER_CONTRACT.md`](../sprite/XBR2X_RASTER_CONTRACT.md). Le run spatial doit
   inscrire `XBR/xbr2X`, `xbr_scale=2`, `xbr_passes=1`, `xbr_blend=false`, `post_scale=2`,
   `post_scale_method=nearest`.
   Exception qualifiée : `BUBBLES2` utilise `--xbr-blend`; son alpha de bord devient non binaire et
   impose la prémultiplication RGB finale. Ne pas reporter cette exception sur un autre resref sans
   QA dédiée.
3. Construire le pack x4 puis exécuter TimedTimeline v2 à 30 fps depuis ce pack :

```powershell
python pipeline/scripts/run_animation_upscale_30fps_v2.py plan `
  --source-run <run-spatial> `
  --base-pack <pack-x4-complet> --resref <RESREF> `
  --run <run-30fps> --model apo-8 `
  --transparent-rgb-mode <preserve-hidden-rgb|nearest-opaque-dilate> > <plan.json>

python pipeline/scripts/run_animation_upscale_30fps_v2.py build `
  --source-run <run-spatial> `
  --base-pack <pack-x4-complet> --resref <RESREF> `
  --run <run-30fps> --approve-plan-sha256 <sha256-plan> `
  --transparent-rgb-mode <preserve-hidden-rgb|nearest-opaque-dilate> `
  --model apo-8
```

4. Split par zone, fusionner dans un split-root complet, puis neutraliser les ressources `Blended` :

```powershell
python pipeline/scripts/build_blended_rgb_neutral_pack.py `
  --split-root <lot-complet> --output <lot-final> `
  --resref <RESREF> --mode <zero|premultiply>
```

5. Contrôler frame source/xBR/30 fps, boucle, pause/reprise, toutes les occurrences, fond clair et
   sombre. Après décision utilisateur seulement : créer `qa-approval.json`, installer réversiblement,
   inscrire le registre/alpha catalogue et décider séparément l'entrée release.

## Invariants

- xBR ×2 seul ; ne pas remplacer par xBR ×4 direct, SeedVR ou interpolation spatiale lissée.
- `xbr_blend=false` reste le défaut ; `BUBBLES2` est l'unique exception validée.
- `nearest-opaque-dilate` ne modifie que l'entrée RGB de Topaz ; ancres x4, alpha et géométrie restent
  inchangés.
- La neutralisation RGB finale n'est pas un correctif alpha ; elle doit prouver alpha inchangé (`zero`)
  ou RGB prémultiplié (`premultiply`).
- Aucun spline, feather, fade ovale ou fade temporel par défaut : ajouter uniquement après une QA
  spécifique de l'asset.
