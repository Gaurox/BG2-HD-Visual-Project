# SPDEATH3 — essai masque SDF Ankheg2026-10-18

- Demande : lisser seulement le masque de33SPDEATH3, méthode Ankheg pour commencer. **Aperçu uniquement ; version installée conservée.**
- [`result.json`](result.json), [`summary.json`](summary.json), [`comparatif`](review/index.html), [`détail`](review/detail.png) ;124phases/33masques distincts,2profils de62phases/2.066667s. Même timing/choix de phases que source, aucune inférence RGB.
- Formule originale réutilisée via l'adaptation des8effets : SDF borné sigma4/biais±2x4, quantification1/16x2, couverture8×8, topologie FG8/BG4 du champ x2 protégée. Inset0 ; lissage géométrique avec variations locales d'aire, pas d'érosion systématique.
-107208pixels alpha modifiés, masseA96.82–99.95% selon phase ; extension de bord≤2x4. RGB déjà visibles exacts ; nouveaux pixels de bord colorés depuis le premier plan voisin, zéro RGB siA0. Compagnons droits/prémultipliés hashés, aucune nouvelle phase vide.
- Marge d'aperçu4x4 transparente commune, dimensions224×384 ; ancrages relatifs avant/après identiques. Les crops natifs touchent le bord : marge nécessaire pour ne pas couper le masque lissé. Elle n'est pas installée ; future dérivation runtime doit adapter dimensions/carrier/centres de façon cohérente.
- Animation synchronisée avant/après, curseur de phase,2profils, fonds et alpha seul ; cliquer la vue déplace le détail. Aperçu à taille réelle x4. [`Recette`](../../../pipeline/recipes/effects-spdeath3-sdf-preview-20261018-v1/README.md).
- Source/manifeste installé inchangés, aucun registre métier/QA/release modifié ; version actuelle `Z33T33` reste le témoin installé. Validation visuelle de cette proposition en attente.
