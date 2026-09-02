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
| Revue technique/vidéo d'un run | `qa-approval.json` immuable du run exact ; jamais preuve suffisante de QA ingame |
| QA ingame et run final | `index/qa-decisions/<RESREF>/*.json` immuable et `index/selections/<RESREF>.json` courant |
| Candidats release | `../releases/BG2-HD-Upscale/manifests/animation-release-candidates.json` |
| Résolution du legacy | `index/path-migrations.json`, `index/qa-evidence-migrations.json` ; un snapshot d'un blob Git orphelin doit être versionné sous `index/qa-evidence-history/`, avec SHA-256 et id blob dans la migration |
| Rétention physique post-P3 | `index/post-p3-pack-retention-20260902.json` ; inventaire hashé sans implication QA/release |

Runs, packs, captures, backups et présence dans le jeu ne prouvent aucun statut.

## Routage

| Besoin | Guide |
|---|---|
| Upscale spatial | [`../pipeline/ANIMATION_UPSCALE_PIPELINE.md`](../pipeline/ANIMATION_UPSCALE_PIPELINE.md) |
| Petits sujets pixelisés xBR2 / 30 fps | [`../pipeline/ANIMATION_SMALL_SUBJECT_XBR2_30FPS.md`](../pipeline/ANIMATION_SMALL_SUBJECT_XBR2_30FPS.md) |
| Timeline 30 fps pause-aware | [`../pipeline/ANIMATION_UPSCALE_30FPS_V2.md`](../pipeline/ANIMATION_UPSCALE_30FPS_V2.md) |
| Interpolation mono-cycle | [`../pipeline/ANIMATION_INTERPOLATION_PIPELINE.md`](../pipeline/ANIMATION_INTERPOLATION_PIPELINE.md) |
| Packs par zone | [`../pipeline/ANIMATION_PACKS_PAR_ZONE.md`](../pipeline/ANIMATION_PACKS_PAR_ZONE.md) |
| Correctif alpha | [`../pipeline/ANIMATION_ALPHA_CORRECTIONS.md`](../pipeline/ANIMATION_ALPHA_CORRECTIONS.md) |
| Lissage alpha par frame, Core Guard, fade ovale | [`../pipeline/ANIMATION_PER_FRAME_SPLINE_ALPHA_30FPS_V2.md`](../pipeline/ANIMATION_PER_FRAME_SPLINE_ALPHA_30FPS_V2.md) |
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
- Créer un nouveau run mono-asset sous `animations/ressources/<RESREF>/runs/<run-id>/`; utiliser
  `animations/batches/<run-id>/` pour un lot. `animations/runs/` reste lisible en legacy.

## Parcours courant

```powershell
python pipeline/scripts/animation_workflow.py list --limit 20
python pipeline/scripts/animation_workflow.py status --resref <RESREF>
python pipeline/scripts/animation_workflow.py new-run --resref <RESREF> --stage spatial --recipe <recette>
```

Sans `--run`, `new-run` est strictement en lecture seule. Avec `--run`, il réserve atomiquement
l'identifiant sous `animations/ressources/<RESREF>/.<run-id>.reservation.json`, sans créer le dossier
feuille. Le producteur écrit au chemin retourné ; `finalize --run` vérifie le marqueur et le supprime
après validation du run terminé. Ne pas modifier ni supprimer ce marqueur pendant production/QA.

Après validation ingame explicite d'un résultat x4, préparer puis appliquer une seule transaction.
Répéter `--area` pour toutes les zones de l'inventaire du resref :

```powershell
python pipeline/scripts/animation_workflow.py finalize `
  --resref <RESREF> --final-run <run-final> --qa-pack <pack-index> `
  --area ARxxxx --decision-status accepted --qa-date YYYY-MM-DD `
  --decision "<résultat ingame>"
# Relire le plan, puis ajouter --run.
```

Pour un résultat conservé strictement natif, ne fournir ni run ni pack x4 :

```powershell
python pipeline/scripts/animation_workflow.py finalize `
  --resref <RESREF> --registry-status validé-natif `
  --area ARxxxx --decision-status accepted --qa-date YYYY-MM-DD `
  --decision "<résultat ingame>"
# Relire le plan, puis ajouter --run.
```

La branche native vérifie et scelle `animations/ressources/<RESREF>/source.bam` contre
`index/ressources.csv`.

La transaction crée la décision immuable, met à jour la sélection et le CSV, mais ne touche pas à
la release. Les écritures `finalize --run` et `animation_release.py --run` partagent le verrou
`.tmp/workflow-locks/animation-authority.lock`. Après interruption brutale, relancer `finalize --run` :
le journal `.tmp/workflow-transactions/animation-authority-active.json` est restauré. Pour
`animation-release-active.json`, relancer la même commande `animation_release.py --run`. Toute autre
commande métier/release refuse ces journaux. `validé-natif` s'arrête ici et reste absent des packs x4. Pour `validé-x4`,
après accord release distinct :

```powershell
python pipeline/scripts/animation_release.py --area ARxxxx --approve
# Relire le plan, puis ajouter --run. Ajouter --test-delta seulement après choix des tests.
```

Contrat de rangement commun : [`../docs/ASSET_LIFECYCLE.md`](../docs/ASSET_LIFECYCLE.md).

## Contrôles

```powershell
python pipeline/scripts/sync_animation_upscale_registry.py --check
python pipeline/scripts/test_changed.py --targeted
```

Le premier contrôle ne concerne qu'une modification du registre. La seconde commande ne lance rien
et prépare la question obligatoire « ciblés / tous / aucun ». Le groupe `animations` couvre inventaire,
spatial, interpolation, 30 fps, runtime et packs, sans tests maps ou sprites. Ne jamais exécuter un
autre groupe après un choix ciblé. Voir [`../docs/TEST_SELECTION.md`](../docs/TEST_SELECTION.md).

Une QA approuvée et une intégration release restent deux décisions distinctes.
