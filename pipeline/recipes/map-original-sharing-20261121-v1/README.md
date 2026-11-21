# Décors x4 communs par identité d'origine

- `build.py` compare les TIS x1 décodés et la grille WED des 400 variantes d'origine. Les 54 ARE qui pointent vers le WED d'une autre zone sont recensés dans `results.json`.
- Donneur x4 au sein de chaque famille. Préférence à la variante binaire la plus utilisée, puis au plus petit build déjà sélectionné. Les trois donneurs validés de l'essai précédent ont priorité.
- TIS, WED, indices, masques BC3 et ressources eau restent propres à la zone. Pages sèches partagées telles quelles après contrôle de l'alpha BC1. Pour les pages dont les masques BC3 diffèrent, partager les blocs couleur et restituer l'alpha de chaque destinataire bit à bit.
- `run/shared-original-maps-test.zip` contient les blocs mutualisés. `run/restored/override` restitue tous les noms natifs et `results.json` lie les empreintes des pages, TIS et WED. Mesure incrémentale après déduplication exacte des PVRZ de l'alpha.11, atlas de l'essai précédent compris.
- `install.py install` établit des liens physiques pour les PVRZ finaux identiques, y compris les témoins. `run/installation/` conserve la sauvegarde et le reçu. Les dépendances de chaque zone restent accessibles sous leurs resrefs d'origine.
- `python -B pipeline/recipes/map-original-sharing-20261121-v1/install.py restore` restaure l'état local précédent après fermeture du jeu et d'InfinityLoader. Restaurer cet essai avant toute restauration de l'essai à trois atlas.

## QA locale

- Installation 2026-11-21. 447 noms PVRZ sur 220 fichiers physiques, 96 WED/TIS contrôlés et retour arrière testé sur une copie intégrale des pages.
- Blocs couleur x4 modifiés sur 12 variantes à contrôler en jeu. AR0703, AR2602, AR5005, AR5006, AR5009, AR5010, AR5012, AR5015, AR5016, AR6008, AR6012 et AR6111.
- Décors secs avec changement de build. Comparer les donateurs et destinataires AR1005/AR5006, AR0332/AR5005 et les groupes listés dans `results.json`.
- Eau et alpha privés. Comparer AR0408/AR0703, AR0506/AR5010, AR1003/AR2011, AR0310/AR6008, AR1601/AR1004 et AR2210/AR2602. Vérifier contours, couche liquide et occlusion en condition sèche puis sous pluie si la zone la supporte.
- Portes. Rejouer au besoin [les témoins AR0704/AR2010](../map-atlas-sharing-20261121-v1/TEST_INGAME.md). Statut des nouveaux décors `installed-awaiting-ingame-test`.
