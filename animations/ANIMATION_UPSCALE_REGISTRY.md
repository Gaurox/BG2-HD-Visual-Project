# Registre des animations de zone

Fichier canonique de suivi :
[`index/animation_upscale_registry.csv`](index/animation_upscale_registry.csv).

Une ligne = un `resref` BAM, jamais une occurrence. La colonne `areas` liste toutes
les zones qui utilisent cet élément et `occurrences` en donne le nombre total.

## Statuts autorisés

| Statut | Sens |
|---|---|
| `validé-x4` | Upscale x4 vu et validé en jeu par l'utilisateur. |
| `validé-natif` | Décision explicite validée : BAM source conservé en l'état ; compte comme traité, sans produit x4. |
| `à-valider` | Upscale x4 et pack runtime terminés ; validation visuelle en jeu requise. |
| `à-corriger` | Un x4 existe mais une correction ciblée est requise avant validation. |
| `à-arbitrer` | Une décision est requise : autre modèle, masque, désactivation ou abandon. |
| `à-compléter` | Prototype partiel ; toutes les frames ou le runtime ne sont pas terminés. |
| `écarté` | Décision explicite : ne pas upscaler cet élément. |
| `non-traité` | Aucun traitement ni décision enregistrés. |

Ne passer à `écarté` qu'après une décision explicite. Une hypothèse telle que
« probablement à désactiver » reste `à-arbitrer`.

## Mise à jour

Après une régénération de `ressources.csv` ou `occurrences.csv` :

```powershell
python pipeline/scripts/sync_animation_upscale_registry.py
python pipeline/scripts/sync_animation_upscale_registry.py --check
```

Le script régénère les colonnes techniques et les zones, mais conserve par `resref` les champs de
suivi. Il tient le verrou animation partagé et refuse toute transaction interrompue. Ne pas éditer
séparément une QA acceptée : `animation_workflow.py finalize` met à jour en une
transaction `status`, `selected_run`, `qa_decision`, `qa_date`, `correction_id`, `notes`, la décision
immuable et la sélection courante. Chaque correctif alpha retenu doit aussi être ajouté à
[`index/animation_alpha_corrections.csv`](index/animation_alpha_corrections.csv).

Le statut décrit la décision spatiale : résultat x4 ou conservation native. Pour une ressource passée par le pipeline
temporel [`../pipeline/ANIMATION_UPSCALE_30FPS_V2.md`](../pipeline/ANIMATION_UPSCALE_30FPS_V2.md),
le `qa-approval.json` du run ne vaut que revue technique/vidéo. La QA ingame définitive exige une
décision sous `index/qa-decisions/`, référencée par `index/selections/` et par les colonnes du CSV.

`validé-natif` suit le même mécanisme sans run ni pack x4 : la décision et la sélection scellent le
hash de `ressources/<RESREF>/source.bam` contre `index/ressources.csv`. La release animation x4 est
alors `not-applicable` ; l'absence du resref dans le pack laisse le moteur charger le BAM vanilla.
