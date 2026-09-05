# Animations `Blended` — RGB sous alpha

Avec le bit ARE `Blended`, le RGB peut contribuer même lorsque l'alpha vaut zéro. Les couleurs
cachées générées dans le fond transparent deviennent alors un rectangle ou un halo. Une correction
alpha seule ne résout pas ce défaut.

## Gate d'entrée

1. Vérifier le flag de chaque occurrence dans `animations/index/occurrences.csv`.
2. Mesurer le RGB des texels où `alpha == 0` dans le pack.
3. Si la ressource n'est pas `Blended`, diagnostiquer d'abord alpha, crop ou occlusion.

## Modes

| Alpha | Mode | Transformation RGB |
|---|---|---|
| strictement binaire | `zero` | RGB = 0 lorsque alpha = 0 |
| dégradé/feather | `premultiply` | RGB = RGB × alpha / 255 partout |

`premultiply` est obligatoire dès qu'un alpha intermédiaire existe.

## Build dérivé

```powershell
python pipeline/scripts/build_blended_rgb_neutral_pack.py `
  --split-root <lot-source> --output <nouveau-lot> `
  --resref <RESREF> --mode zero
```

Options ciblées :

- `--feather-proto <run>` ou `--inner-feather-x4 <rayon>` : alpha adouci, avec
  `--mode premultiply` ;
- `--mask-png <png> --mask-origin-x4 X Y --mask-anchor-x1 X Y` : masque monde lié à une occurrence ;
- répéter `--resref` pour plusieurs ressources ;
- `--resume` revalide la sortie existante.

Le script écrit un nouveau split-root, ne touche ni au jeu ni à l'entrée, et vérifie la provenance
du feather. Le masque blanc conserve l'animation ; le noir la retire.

## Vérification

- mode `zero` : alpha inchangé byte pour byte, RGB nul sous alpha nul ;
- mode `premultiply` : alpha conforme à la correction, aucun RGB non prémultiplié ;
- géométrie, timeline, resrefs non ciblés et hashes de packs inchangés ;
- installation par le workflow des packs par zone ;
- QA ingame sur fond clair/sombre, boucle, pause et occurrences partagées.

Ne pas utiliser ce traitement pour masquer un mauvais upscale du sujet : il ne restaure aucune
information RGB perdue.
