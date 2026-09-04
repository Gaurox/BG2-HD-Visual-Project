# Masques d'occlusion peints à la main

Ce dossier est **suivi par git**, contrairement au reste de `animations/`. C'est délibéré.

## Pourquoi il existe

Le plan de données du dépôt exclut `animations/ressources/`, `animations/runs/`,
`animations/batches/` et `animations/packs-par-zone/` : tout ce qui s'y trouve est reproductible
en relançant la chaîne. Les masques d'occlusion ne le sont pas. Ils sont peints à la main, à la
souris, occurrence par occurrence, en suivant le décor de chaque carte. Une chaîne relancée les
consomme, elle ne les recrée pas.

Ils vivent donc ici, à côté des autres autorités du domaine, et non dans les dossiers jetables.

## Ce qu'un masque corrige

Le WED de chaque zone porte un polygone qui masque l'animation, avec le flag `Cover animations`
actif : le jeu d'origine occulte donc correctement. Une texture x4 de remplacement contourne cette
occlusion. Le pont natif ne peut pas la rattraper sur une ressource **`Blended`** (flag ARE bit 1),
parce qu'il transfère la visibilité dans l'alpha, que le chemin `Blended` ignore — c'est le RGB qui
est additionné à la scène. Un masque peint fonctionne, lui, parce qu'il est cuit dans le RGB.

Sur une ressource non `Blended`, le pont natif suffit et il n'y a pas de masque à peindre.

## Contrat du PNG

**Niveaux de gris aplatis, alpha opaque partout : blanc conserve, noir retire**, le gris est une
transition. C'est la luminance qui porte le signal, et l'outil **refuse** un masque dont la forme
vit dans le canal alpha plutôt que de l'inverser en silence.

> **Erratum.** Le champ `mask_contract` de `FPIT1S/masques.json` annonce l'inverse
> (« canal alpha = couverture »). C'est une erreur de rédaction du 2026-09-03, corrigée depuis
> partout ailleurs. Le fichier est conservé tel quel parce qu'il est haché par le manifeste d'un
> run scellé et qu'on ne réécrit pas un hachage sous une décision QA. Se fier au contrat ci-dessus,
> qui est celui du décodeur.

Le reste des paramètres de pose — `anchor_x1`, `mask_origin_x4`, `mask_size_x4` — est dans le
`masques.json` de chaque ressource, une entrée par occurrence.

## Organisation

Un dossier par resref. Chaque fichier est nommé par son occurrence :
`ZONE[-gauche|-droite]-xNNN-yNNN.png`, les coordonnées étant celles, brutes, de l'ARE. C'est cette
paire `(x, y)` qui lie une variante à son occurrence en registre v3, et c'est pour ça qu'elle est
dans le nom : deux feux sur une même carte portent deux masques différents.

`manifest.json` donne le SHA-256 de chaque fichier, le run dont ce dossier est la copie conforme,
et la liste des occurrences **volontairement sans masque**, pour qu'une absence ne se lise jamais
comme une perte.

## Remettre un masque en jeu

La pose se fait avec `build_blended_rgb_neutral_pack.py` (`--mask-png`, `--mask-origin-x4`,
`--mask-anchor-x1`, `--mode premultiply` imposé sur une ressource `Blended`), puis
`merge_area_pack_resources.py --pack CHEMIN::X,Y` pour lier chaque masque aux coordonnées de son
occurrence sur les cartes qui en portent plusieurs.

Voir [`../../pipeline/ANIMATION_PER_OCCURRENCE_OCCLUSION.md`](../../pipeline/ANIMATION_PER_OCCURRENCE_OCCLUSION.md).
