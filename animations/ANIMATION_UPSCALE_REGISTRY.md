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

Le script régénère les colonnes techniques et les zones, mais conserve par
`resref` les champs humains `status`, `correction_id` et `notes`. Corriger ces
trois champs directement dans le CSV après la QA. Chaque correctif alpha retenu
doit aussi être ajouté à
[`index/animation_alpha_corrections.csv`](index/animation_alpha_corrections.csv).

Le statut décrit toujours la validation spatiale x4. Pour une ressource passée par le pipeline
temporel [`../pipeline/ANIMATION_UPSCALE_30FPS_V2.md`](../pipeline/ANIMATION_UPSCALE_30FPS_V2.md),
noter dans `notes` le run V2, `TimedTimeline 15->30`, puis l'état de la QA ingame. Ne pas inventer
un nouveau statut CSV : l'approbation technique installable reste portée par le fichier immuable
`qa-approval.json` du run V2.
