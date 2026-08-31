# Contrat runtime des animations de zone

## Modèle

Le BAM natif garde la géométrie, les cycles et les centres logiques x1. Un pack externe fournit :

- `AreaAnimations-X4.registry` : resrefs, cycles, timeline et assets ;
- `AAX4-*.rgba` : textures RGBA physiques ;
- éventuellement des variantes v3 liées à une position ARE exacte.

Le moteur remplace seulement le rendu. Une entrée absente, invalide ou non appariée retombe sur le
chemin vanilla ; elle ne doit jamais recevoir une texture devinée.

## Versions de registre

| Version | Usage |
|---|---|
| v1 | géométrie native, textures xN |
| v2 | `Native` ou `TimedTimeline`, phases temporelles explicites |
| v3 | v2 + variantes par occurrence `(resref, x, y)` |

Les packs par zone sont chargés après `LoadArea`. Une zone sans pack libère les remplacements et
utilise les BAM natifs. Les textures OpenGL sortantes sont détruites sur le thread de rendu, jamais
depuis le hook de chargement.

## Invariants de production

- Une frame source produit une texture alignée sur son centre BAM.
- Largeur/hauteur physiques = dimensions logiques × échelle déclarée.
- L'interpolation conserve la durée du cycle ; une phase n'invente pas une nouvelle géométrie.
- RGB et alpha ont des provenances séparées et hashées.
- Une ressource `Blended` exige un RGB neutre sous alpha nul ; voir le guide dédié.
- Le payload brut d'un pack runtime est plafonné à 512 Mio. Au-delà, produire un pack d'auteur puis
  le découper par zone.
- L'occlusion WED du compositeur CPU n'est pas automatiquement appliquée à la texture GL de
  remplacement ; employer le bridge/registre v3 validé, jamais un override ARE livré.

## Chaîne

```text
index typé → run spatial immuable → timeline/correctif éventuel
→ pack validé → split/combinaison par zone → préflight installateur
→ installation réversible → QA ingame → décision de registre → décision release
```

Les commandes sont uniquement dans les guides `pipeline/ANIMATION_*.md`; ce document ne les
duplique pas.

## QA minimale

- forme, crop, taille, centre, couleur et alpha ;
- boucle dernière → première et vitesse ;
- pause/reprise, sortie/retour dans le champ ;
- changement de zone et retour ;
- occurrence masquée et occurrence non masquée si registre v3 ;
- zone sans pack : rendu vanilla intact.

Le runtime et ses tests sont sous
[`../engine/InfinityEngine-Enhancer/source-patchee/`](../engine/InfinityEngine-Enhancer/source-patchee/).
Les preuves de build ou de QA restent dans le run exact et `docs/validation/` du moteur.
