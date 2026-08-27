# Correction locale WED AR0516 — SPHINCT inférieur

**Statut : validée ingame le 2026-08-27 sur la sauvegarde `planar-test`, installée localement,
non intégrée au manifeste de release.**

## Verdict

Le défaut restant à gauche du `SPHINCT` inférieur n'était pas une régression du bridge Phase 1,
un agrandissement du remplacement x4 ou une extension de son alpha. Le WED vanilla d'AR0516 ne
contenait aucun polygone `Cover animations` sur la pointe verticale et la branche désignées par
l'utilisateur.

La correction validée ajoute un polygone WED natif local. Le masque Photoshop n'est ni cuit dans
les 51 frames, ni référencé par le registre x4, ni chargé au runtime. Il sert uniquement à authorer
le contour, ensuite quantifié en 29 sommets logiques x1 et conservé dans
`maps/wed-corrections/AR0516/lower-sphinct-cover.json`.

## Preuves de cause racine

- Les traces de la session négative montrent un appel natif réussi et un bridge actif pour les
  deux occurrences `SPHINCT` d'AR0516 : le chemin moteur n'est pas contourné.
- La comparaison des 51 phases x4 aux 17 frames BAM vanilla ne trouve aucun pixel logique x4
  nouveau hors de l'alpha natif. Le remplacement x4 est un sous-ensemble du masque vanilla ; il
  n'est pas affiché plus grand.
- Le polygone 65, voisin visuellement et de type `0x05`, a une intersection de **zéro pixel** avec
  l'alpha du `SPHINCT` inférieur. L'essai isolé `0x05 -> 0x0D` ne pouvait donc pas agir ; son
  override a été restauré avant le second test.
- Sur cette occurrence, seul le polygone 48 de type `0x09` intersecte l'alpha, sur 64 pixels
  logiques situés ailleurs. Aucun contour WED ne couvre la pointe peinte par l'utilisateur.

Ces mesures confirment une omission d'authoring WED locale. Le bridge global réapplique exactement
les données natives disponibles, mais ne peut pas inventer un premier plan absent.

## Correction installée

| Élément | Valeur validée |
|---|---|
| WED source | `data/AREA050B.bif`, 41 384 octets |
| SHA-256 source | `877A102212E3BCDBD34FAEDD01446287342A6448205CE45E8671B3ED7CDEE19D` |
| Masque d'authoring | 640×480 x4, origine monde x1 `(1452,1392)` |
| SHA-256 du masque | `5D62A9AD602CCEA51FAD8B14C117C48A560C863454D81ABDEA8E4653DFD153CC` |
| Polygone | slot vide 49, 29 sommets, boîte `(1452,1450)–(1485,1512)` |
| Sémantique | flags `0x09` : `Shade wall + Cover animations`, hauteur 255 |
| Indexation | wall group 23 uniquement, une entrée lookup ajoutée |
| Fidélité x4 | IoU 0,950373 ; 229 faux négatifs et 416 faux positifs de bord |
| Intersection animation | 1 539 pixels physiques sur chacune des 51 phases |
| WED produit | 41 502 octets, soit +118 octets |
| SHA-256 installé | `8A0AA3CA4C5D7A9BD42DDD0F55F6CA5ED57241A5F4B141C3CBE7D18D9AA2DB1A` |

Le builder vérifie avant génération le hash WED, les 18 octets exacts du slot vide et la plage
lookup `23:123:20`. Il conserve tous les anciens sommets octet-identiques, décale l'offset de leur
table de deux octets, ajoute une référence de wall group et annexe les 29 nouveaux sommets.

## Validation

- tests ciblés des deux builders WED : 10/10 ;
- suite Python commune après ajout des tests : **176/176** en 96,736 s ;
- `git diff --check` : réussi ;
- installation avec jeu et InfinityLoader fermés ;
- hash de l'override installé identique au manifeste ;
- verdict utilisateur ingame : **validé** sur `planar-test`.

Le backup de restauration est
`maps/AR0516/test-native-wed-occlusion-20260827-painted-mask-p49/install-backups/override-backup-20260827-170033`.
Avant rollback, le script vérifie que l'override installé porte toujours le hash attendu ; comme
`AR0516.WED` était absent auparavant, la restauration le supprime et revient au WED KEY/BIF.

## Compatibilité et portée

- x1 et x4 utilisent les mêmes coordonnées WED logiques ; aucun TIS/PVRZ n'est modifié ;
- aucune identité de ressource BAM, donnée ARE ou sauvegarde n'est modifiée ;
- aucun payload texture n'est ajouté, donc la limite de 512 Mio reste inchangée ;
- les packs v1/v2/v3 existants restent octet-identiques ;
- le bridge global et ses DLL/INI ne changent pas.

Cette validation ne signifie pas que toutes les cartes doivent être corrigées une par une. Le
bridge reste la correction générale. Une intervention WED map par map est réservée aux défauts
résiduels dont l'absence ou l'erreur de géométrie native est démontrée avec la même méthode.

Rejouer cette QA locale si le WED source change de hash, si un mod fournit son propre AR0516.WED,
si le contour ou le wall group est modifié, ou avant intégration à une release. Une nouvelle
matrice globale n'est requise que si le bridge, la famille de rendu ou l'exécutable change.
