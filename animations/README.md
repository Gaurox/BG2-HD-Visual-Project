# Animations de décor — point d'entrée

Les animations BAM sont indépendantes des pixels de maps. Leur géométrie logique reste x1 ; le
moteur charge des textures physiques x4 et, lorsque le registre le demande, une timeline visuelle
30 fps.

## Sources de vérité

- `index/manifest.json` : snapshot de l'inventaire.
- `index/occurrences.csv` : chaque occurrence ARE d'un BAM.
- `index/ressources.csv` et `index/zones.csv` : ressources et zones dédupliquées.
- `index/animation_upscale_registry.csv` : validation spatiale par resref.
- `index/animation_alpha_corrections.csv` : correctifs alpha approuvés ou expérimentaux.
- `qa-approval.json` du run : seule approbation temporelle.
- `releases/BG2-HD-Upscale/manifests/animation-release-candidates.json` : candidats release.

`runs/`, `packs-par-zone/`, `proto/`, backups et captures ne décrivent jamais à eux seuls l'état
courant.

## Méthodes actives

| Besoin | Procédure | Entrée principale |
|---|---|---|
| Upscale spatial x4 | [`../pipeline/ANIMATION_UPSCALE_PIPELINE.md`](../pipeline/ANIMATION_UPSCALE_PIPELINE.md) | `run_animation_upscale.py` |
| Interpolation d'un cycle natif | [`../pipeline/ANIMATION_INTERPOLATION_PIPELINE.md`](../pipeline/ANIMATION_INTERPOLATION_PIPELINE.md) | `run_animation_interpolation.py` |
| 15 → 30 fps pause-aware | [`../pipeline/ANIMATION_UPSCALE_30FPS_V2.md`](../pipeline/ANIMATION_UPSCALE_30FPS_V2.md) | `run_animation_upscale_30fps_v2.py` |
| Correctif alpha | [`../pipeline/ANIMATION_ALPHA_CORRECTIONS.md`](../pipeline/ANIMATION_ALPHA_CORRECTIONS.md) | builders alpha spécialisés |
| Packs par zone | [`../pipeline/ANIMATION_PACKS_PAR_ZONE.md`](../pipeline/ANIMATION_PACKS_PAR_ZONE.md) | `split_animation_pack_by_area.py` |
| Masque différent par occurrence | [`../pipeline/ANIMATION_PER_OCCURRENCE_OCCLUSION.md`](../pipeline/ANIMATION_PER_OCCURRENCE_OCCLUSION.md) | registre v3 lié aux coordonnées ARE |
| Contrat runtime complet | [`UPSCALE_ANIMATIONS_ZONE.md`](UPSCALE_ANIMATIONS_ZONE.md) | registre + DLL |

TimedTimeline v2 est la méthode retenue pour la timeline 30 fps. Le registre v3 conserve cette
timeline et ajoute le routage par occurrence. Les prototypes d'horloge antérieurs sont archivés.

## Organisation

```text
animations/
  index/                 # catalogues canoniques
  ressources/            # sources BAM et planches, données ignorées par Git
  runs/                  # runs immuables, données ignorées
  packs-par-zone/        # packs matérialisés et backups, données ignorées
```

Traiter chaque frame RGB et alpha séparément. Ne jamais upscaler une planche concaténée. Un pack
global dépassant 512 Mio doit être découpé par zone.

## Promotion

La release accepte les registres v2 et v3 avec le renderer `iee-0.1.0-alpha.5`. AR0602 v2 reste
le témoin de rétrocompatibilité ; AR0900 v3 est le témoin du routage par occurrence. Toute autre
zone doit être ajoutée explicitement à `animation-release-candidates.json` avec sa version, ses
hashes et son approbation.

QA et intégration release restent deux décisions distinctes. Un run `pending-qa`, un prototype ou
un pack présent dans l'override n'est pas éligible.

## Tests légers

```powershell
python -m unittest `
  pipeline.tests.test_animation_upscale_pipeline `
  pipeline.tests.test_animation_interpolation_pipeline `
  pipeline.tests.test_animation_upscale_30fps_v2 `
  pipeline.tests.test_animation_runtime_pack `
  pipeline.tests.test_animation_pack_area_split `
  pipeline.tests.test_combine_area_pack_splits
```
