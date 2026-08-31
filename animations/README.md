# Animations de décor

> **Règle documentaire : écrire pour des agents IA — concis, factuel, opérationnel, non narratif. Éviter la verbosité et les répétitions. Toute nouvelle documentation ou modification doit privilégier la densité d’information, les listes/tableaux, les chemins et commandes précises. Éviter la prose longue, le contexte narratif, les répétitions et les explications principalement destinées à un lecteur humain.**

Les animations BAM restent en géométrie logique x1 ; le moteur affiche leurs textures physiques
x4 et, si le registre le demande, une timeline 30 fps.

## Sources de vérité

| Information | Autorité |
|---|---|
| Occurrences ARE typées | `index/occurrences.csv` |
| Ressources BAM extraites | `index/ressources.csv` |
| Synthèse par zone | `index/zones.csv` |
| Snapshot d'inventaire | `index/manifest.json` |
| Validation spatiale par resref | [`ANIMATION_UPSCALE_REGISTRY.md`](ANIMATION_UPSCALE_REGISTRY.md) et `index/animation_upscale_registry.csv` |
| Correctifs alpha | `index/animation_alpha_corrections.csv` |
| QA temporelle d'un run | `qa-approval.json` immuable du run exact |
| Candidats release | `../releases/BG2-HD-Upscale/manifests/animation-release-candidates.json` |
| Résolution du legacy | `index/path-migrations.json`, `index/qa-evidence-migrations.json` |

Runs, packs, captures, backups et présence dans le jeu ne prouvent aucun statut.

## Routage

| Besoin | Guide |
|---|---|
| Upscale spatial | [`../pipeline/ANIMATION_UPSCALE_PIPELINE.md`](../pipeline/ANIMATION_UPSCALE_PIPELINE.md) |
| Timeline 30 fps pause-aware | [`../pipeline/ANIMATION_UPSCALE_30FPS_V2.md`](../pipeline/ANIMATION_UPSCALE_30FPS_V2.md) |
| Interpolation mono-cycle | [`../pipeline/ANIMATION_INTERPOLATION_PIPELINE.md`](../pipeline/ANIMATION_INTERPOLATION_PIPELINE.md) |
| Packs par zone | [`../pipeline/ANIMATION_PACKS_PAR_ZONE.md`](../pipeline/ANIMATION_PACKS_PAR_ZONE.md) |
| Correctif alpha | [`../pipeline/ANIMATION_ALPHA_CORRECTIONS.md`](../pipeline/ANIMATION_ALPHA_CORRECTIONS.md) |
| Ressource `Blended` | [`../pipeline/ANIMATION_BLENDED_RGB_NEUTRALISATION.md`](../pipeline/ANIMATION_BLENDED_RGB_NEUTRALISATION.md) |
| Masque par occurrence | [`../pipeline/ANIMATION_PER_OCCURRENCE_OCCLUSION.md`](../pipeline/ANIMATION_PER_OCCURRENCE_OCCLUSION.md) |
| Contrat moteur | [`UPSCALE_ANIMATIONS_ZONE.md`](UPSCALE_ANIMATIONS_ZONE.md) |

## Invariants

- Ne traiter que les occurrences typées `BAM`; WBM et PVRZ suivent leur pipeline propre.
- Exporter et traiter chaque frame, RGB et alpha séparément ; jamais une planche concaténée.
- Conserver cycles, centres, durées, ordre et source hashée.
- TimedTimeline v2 est la méthode temporelle courante ; le registre v3 ajoute le routage par
  coordonnées ARE sans réécrire l'ARE.
- Découper par zone avant installation dès qu'un pack global dépasse le budget runtime de 512 Mio.
- Créer tout nouveau travail sous `animations/runs/`; ne pas recréer les anciens chemins `proto/`.

## Contrôles

```powershell
python pipeline/scripts/sync_animation_upscale_registry.py --check
python pipeline/scripts/test_changed.py --changed
```

Le groupe `animations` couvre inventaire, spatial, interpolation, 30 fps, runtime et packs. Il ne
sélectionne aucun test maps ou sprites. Une modification release/runtime déclenche `--full`.

Une QA approuvée et une intégration release restent deux décisions distinctes.
