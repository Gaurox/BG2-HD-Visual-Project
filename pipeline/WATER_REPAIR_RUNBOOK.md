# Eau BG2EE — solutions assets/WED (voie 1)

Index facultatif de réparations. Il ne prescrit aucune séquence et n'oblige pas à traiter la nuit,
la météo, la voie 2, les audits ou le suivi lorsqu'ils sont hors périmètre. Utiliser directement la
rubrique correspondant au défaut constaté.

## Diagnostic direct

| Défaut | Élément à regarder | Correction connue |
|---|---|---|
| Crash de map après nouveau TIS | resrefs de pages et offsets WED | resref ≤8 octets ; pagination compatible ; relocation complète des tables |
| Quadrillage sur petites frames | sortie SeedVR | abandonner SeedVR pour ce cas ; bilinéaire périodique 3×3 |
| Coutures entre tuiles | contexte/padding/RGB interne | contexte périodique, crop central, padding 4 px ; greffe RGB locale |
| Centre opaque ou art disparu | format et alpha primaire | reproduire l'alpha ARE/runtime seulement sur les primaires éligibles |
| Faux contour secondaire | alpha calculé depuis fond noir | corriger uniquement les interfaces internes prouvées par WED/source |
| Animation 6 frames visible | table WED/TIS | produire 36 phases à durée de cycle conservée |
| Pluie en mosaïque | ressource alternative | traiter et router séparément sec/pluie |

## Repères de format

| Objet | Repère |
|---|---|
| WED | overlays à `0x08`, table à `0x10`, 24 octets par overlay |
| Overlay WED | largeur/hauteur `+0/+2`, resref TIS `+4`, tilemap/lookup `+16/+20` |
| Cellule | 10 octets, `<HHHB3x>` : start, frame count, secondaire, flags |
| TIS | `TIS V1  ` ; count, entrySize, headerSize, tileDimension à `+8` |
| Entrée PVRZ | `<3I>` : page, x, y |
| Sentinelles | secondaire `0xFFFF` ; page `0xFFFFFFFF` |

Une modification de longueur dans un WED peut déplacer murs, portes, polygones, sommets et tables
suivantes. Un reparse local de ces sections est utile uniquement lorsqu'un WED a été réécrit.

## Solutions réutilisables

### Alpha et composition

- DXT1 opaque → DXT5 sur une primaire exclusivement eau sans secondaire : l'alpha texture peut
  reproduire l'alpha de dessin natif.
- Valeurs confirmées : AR0900/AR1800=128 ; AR1607=100.
- L'alpha d'une source partielle, d'un secondaire ou d'une tuile partagée reste celui de sa source.
- `RGB=(0,0,0)` n'identifie pas à lui seul une zone transparente.

### Raccords

- Donneur RGB : maître secondaire x4 de la même coordonnée et variante.
- Paramètres validés : bande 8 px x4 ; garde de rive 1 px x1 ; poids
  `[1,1,1,1,.75,.5,.25,0]` ; padding 4 px.
- Les corrections locales peuvent recopier uniquement les octets RGB DXT5 concernés afin de garder
  l'alpha intact.

### Animation et périodicité

- WTPOOL AR1000 : bilinéaire x4, contexte 3×3, crop central, 6→36 phases linéaires à 15 Hz.
- WTLAKE historique : sortie wavelet périodique déjà validée ; aucune nécessité de la régénérer.
- WTSEW : 6→36 Apollo-8 validé sur AR0404.
- WTSWAM : paire sèche/pluie isolée validée sur AR1607/AR1800.

### Runtime plutôt qu'asset

Une teinte brune intermittente avec `engineSlot != glName` vient du runtime :
`CResPVR::texture` est un slot de table moteur, pas un nom OpenGL. La solution validée résout le
slot vers son descripteur et son nom GL avant lecture. Modifier les PVRZ ne corrige pas cette cause.

## Outils disponibles

Ces scripts sont des aides ponctuelles, sans enchaînement imposé :

- `pipeline/scripts/audit_water_area.py`
- `pipeline/scripts/audit_area_preflight.py`
- `pipeline/scripts/build_water_route1_batch.py`
- `pipeline/scripts/repair_water_secondary_alpha_seams.py`
- `pipeline/scripts/build_ar1000_wtpool_route2_candidate.py`

Leurs recommandations anciennes peuvent être incompatibles avec un cas récent ; les mesures du cas
courant priment. En particulier, `--transparent-full-water-base` ne convient pas à la composition
native réparée décrite ci-dessus.

## Limites utiles

- Jour, nuit et météo sont des identités distinctes lorsqu'elles sont réellement dans le périmètre.
- SeedVR n'est pas un passage obligé ; AR1000 prouve qu'un upscale non génératif peut être meilleur.
- Voie 1 et voie 2 sont indépendantes : inspecter ou appliquer directement celle qui répond au
  symptôme, et combiner les deux seulement si le résultat le demande.
- Fermer le jeu et InfinityLoader avant remplacement de fichiers installés.
- Ne pas toucher aux fichiers de release sans demande explicite.
