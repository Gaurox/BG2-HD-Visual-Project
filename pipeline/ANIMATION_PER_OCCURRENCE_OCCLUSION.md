# Masque d'occlusion par occurrence

Une texture GL de remplacement contourne l'occlusion WED appliquée par le compositeur CPU vanilla.
Deux occurrences du même resref peuvent en outre exiger des masques différents. Un override ARE
n'est pas livrable : il change les données de zone et ne corrige pas de façon fiable les zones déjà
enregistrées dans une sauvegarde.

## Contrat v3

- clé de variante : resref + coordonnées brutes `(x, y)` de l'occurrence ARE ;
- appariement exact avant tout fallback non lié ;
- assets et registre régénérés dans un nouveau pack, jamais modifiés sur place ;
- une occurrence sans correspondance utilise le fallback déclaré ou le rendu vanilla ;
- le masque est projeté depuis le centre propre à chaque frame.

`merge_area_pack_resources.py --pack PATH::X,Y` lie un pack mono-ressource à une occurrence. Pour
un masque peint, `build_blended_rgb_neutral_pack.py` accepte `--mask-png`, `--mask-origin-x4` et
`--mask-anchor-x1 X Y`; le masque blanc conserve l'animation, le noir la retire.

## Chaîne

1. Relever resref, coordonnées et flags dans `animations/index/occurrences.csv`.
2. Construire chaque variante dans un nouveau split-root.
3. Lier les variantes aux coordonnées avec `merge_area_pack_resources.py`.
4. Combiner le lot complet selon [`ANIMATION_PACKS_PAR_ZONE.md`](ANIMATION_PACKS_PAR_ZONE.md).
5. Valider le registre v3 puis prévalider l'installation.

Les correctifs WED natifs expérimentaux restent séparés :
`build_wed_cover_animation_patch.py` corrige des flags de polygone existants et
`build_wed_mask_polygon_patch.py` crée un polygone borné lorsque la donnée manque. Leurs sorties
restent `pending-ingame` et ne remplacent pas le contrat v3 sans décision.

## QA obligatoire

- appariement exact de chaque occurrence ciblée ;
- identité visuelle hors zone masquée ;
- ressource partagée inchangée dans les autres zones/positions ;
- changement de zone, rechargement, pause/reprise et plusieurs cycles ;
- repli vanilla si pack ou variante absent.

Le code moteur et les preuves sont sous
[`engine/InfinityEngine-Enhancer/source-patchee/`](../engine/InfinityEngine-Enhancer/source-patchee/) ;
voir [`native-occlusion-phase1.md`](../engine/InfinityEngine-Enhancer/source-patchee/docs/native-occlusion-phase1.md)
et ses preuves de validation. Aucun résultat ne devient release sans entrée explicite dans le manifeste
des candidats.
