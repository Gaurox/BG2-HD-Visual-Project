# Instructions agents — BG2 Upscale

## Lecture obligatoire

1. Lire [`README.md`](README.md).
2. Lire uniquement le README du domaine concerné : `pipeline/`, `animations/`, `sprite/`,
   `interface/`, `engine/.../source-patchee/` ou `releases/BG2-HD-Upscale/`.
3. Consulter [`docs/DECISIONS.md`](docs/DECISIONS.md) et
   [`pipeline/PROBLEMES_A_RESOUDRE.md`](pipeline/PROBLEMES_A_RESOUDRE.md) avant de proposer une
   nouvelle méthode.

## Sources de vérité

- Maps : `areas.csv`.
- Animations : `animations/index/` et le `qa-approval.json` du run.
- Sprites : `sprite/index/`, `current-generation.json` et `active-test.json`.
- Moteur : `src/iee/game/build_manifest.*` et `docs/validation/`.
- Release : `manifests/release.json` et `manifests/content.json` généré.

Ne jamais déduire l'état depuis `runs/`, `proto/`, `archive/`, `backups/`, `override`, captures,
temporaires ou packages développés. Ces dossiers sont hors contexte initial.

## Avant une modification

- Rechercher les références textuelles, manifests, jobs et chaînes de restauration.
- Préserver les modifications utilisateur déjà présentes.
- Ne pas modifier un artefact scellé ; créer un nouveau run.
- Ne pas changer l'algorithme d'un pipeline validé pendant une tâche de rangement.
- Jeu et InfinityLoader fermés avant toute installation/restauration.
- Un élément `pending-qa`, x2, temporaire ou issu d'une capture n'est jamais éligible à la release.

## Tests

Tests Python communs :

```powershell
python -m unittest discover -s pipeline/tests -p "test_*.py"
```

Utiliser ensuite la commande de test indiquée dans le README du domaine. Ne pas lancer SeedVR,
Topaz, un build de contenu complet ou un packaging pour valider une modification documentaire.

## Décision d'intégration au manifeste

À la fin de chaque tâche de production ou de validation qui touche au contenu ingame, demander :

> La tâche `<nom>` est terminée. Veux-tu que j'intègre au manifeste de release les éléments
> validés par cette tâche ?

Cette décision est distincte de la mise à jour d'`areas.csv`. Sans accord affirmatif explicite, ne
pas modifier `$mapSpecs`, régénérer `content.json`, mettre à jour le staging ni reconstruire
l'archive. Si aucun élément `validated-installed` n'a été produit, le préciser et ne rien intégrer.
