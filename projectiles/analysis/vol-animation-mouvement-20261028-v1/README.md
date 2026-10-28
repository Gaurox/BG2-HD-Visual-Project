# Vol : animation interpolée ≠ déplacement interpolé

- Question utilisateur : interpolation du déplacement du sort. Le correctif actuel **n’ajoute aucune interpolation des coordonnées du projectile** ; il conserve lespositions fournies par le moteur natif. La cadence du déplacement natif n’est pas mesurée parceslogs.
- RetestV9SPWI312 : TRAVEL12phases finalesdistinctes,6impaires réellement affichées,texturex4,cible30/1,médiane33.0253ms ; aucun rejet masque/composition. [Preuve](evidence.json),session15:48:40–15:48:57 figée. Cela valide l’animation desimages, pas le déplacement.
- `draw-position-code.txt` : rendu final conserve x/y ; seule exception horsprojectiles=BDFORCEW/mapplacement. Hooks CProjectileBAM/FXRender délèguent les coordonnées natives ; aucune position précédente/suivante n’est interpolée.
- Correction de portée : les messages précédents « interpolation du vol » désignaient l’animation du sprite etne répondaient pas au contrôle du déplacement. Ne pas promouvoir ce dernier enQApassée. Aucun retest utilisateur supplémentaire demandé pour lever cette distinction de code.
- La fluidification du trajet demanderait un mécanisme d’affichage distinct ; conserver vitesse, trajectoire, collisions ettempsd’impact natifs. Aucune modification de ce type autorisée/exécutée danscecontrôle.
