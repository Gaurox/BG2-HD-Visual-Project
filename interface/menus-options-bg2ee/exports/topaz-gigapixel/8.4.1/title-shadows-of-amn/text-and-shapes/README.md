# Essai Topaz Gigapixel — titre *Shadows of Amn*

Arborescence standardisée pour les exports de comparaison : `exports/<outil>/<version>/<ressource>/<modèle>/<facteur>/`.

- Outil : Topaz Gigapixel 8.4.1 local.
- Source : `source/TITLE-frame-00-original.png`, PNG RGBA extrait du jeu.
- Modèle : `Text & Shapes` (`-m text`).
- Réglages : x2 et x4, PNG RGBA, espace colorimétrique conservé, compression PNG 4 ; débruitage, netteté et correction de compression réglés au minimum (`1`).
- Résultats : `x2/` et `x4/`.

Validation technique : alpha préservé et dimensions correctes. Validation visuelle : le modèle évite les liserés rouges très visibles de SeedVR, mais redessine trop la calligraphie peinte ; ce test ne doit pas être intégré aux atlas. Le candidat Topaz suivant est `Art & CG`, à comparer sur le même titre et le médaillon.
