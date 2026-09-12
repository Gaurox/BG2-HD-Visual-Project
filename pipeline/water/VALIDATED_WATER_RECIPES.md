# Eau BG2EE — inventaire de solutions validées

Mémoire de diagnostic, à consulter par symptôme ou famille. Aucun ordre, préflight, audit ou lot
jour+nuit n'est imposé. Les valeurs ci-dessous sont des précédents réutilisables quand le cas est
compatible, pas des recettes universelles.

## Solutions par symptôme

| Symptôme | Cause observée | Solution utile |
|---|---|---|
| Crash au chargement | nom PVRZ > capacité resref, page mal nommée ou offsets WED non relocalisés | borner les resrefs à 8 octets ; recalculer pagination et offsets WED |
| Quadrillage/répétition WTPOOL | SeedVR amplifie la trame diagonale du 64×64 stock | bilinéaire x4 non génératif en contexte périodique 3×3, crop central |
| Eau propre mais figée | voie 1/q0 sans mouvement procédural perceptible | 36 phases/15 Hz + blend renderer 30 FPS ; route2 exacte si souhaitée |
| Animation saccadée | seulement 6 frames ou absence d'interpolation temporelle | interpolation cyclique 6→36 phases et blend 30 FPS |
| Traits noirs/bleus | RGB primaire contaminé ou padding incohérent | greffe RGB bornée depuis le secondaire de même coordonnée ; padding 4 px x4 |
| Art local, ombres ou reflets disparus | alpha central 0/255 ou passe secondaire perdue | restaurer l'alpha natif effectif et la composition primaire/secondaire |
| Marche de luminosité | opacités primaire/secondaire désaccordées | apparier les contributions ; AR0300N v10 utilise 160/160 localement |
| Mosaïque sous pluie | seule la ressource sèche a été traitée | créer/router la ressource alternative pluie exacte |
| Route2 invisible | WED/TIS/page/nom GL non reconnu ou hash divergent | corriger l'identité exacte du registre ; garder q0 pour les cas non reconnus |
| Eau parfois brune | `CResPVR::texture` pris pour un nom GL au lieu d'un slot moteur | runtime avec résolution slot→descripteur→nom GL ; ne pas retraiter les PVRZ |
| Autre carte modifiée | remplacement global d'un overlay partagé | alias isolé et routage WED/registre limité aux identités ciblées |
| Eau intérieure artificielle | matériau lac propagé à une autre ambiance | qualifier un matériau/environnement distinct ou rester à q0 |

## Cas de référence

| Famille | Identité validée | Paramètres utiles | Portée |
|---|---|---|---|
| `lake-wtlake` | AR0900, AR0204, AR1600 | WTLAKE x4 périodique ; 36 phases/15 Hz ; blend 30 FPS ; matériau 1 ; q0.70 | identités exactes |
| `lake-wtlake` nuit | AR0900N v5 | maîtres nuit, alpha128, raccords, cache WED renouvelé ; q0.70 | AR0900N |
| `lake-wtlake` nuit | AR0046N v7 | correction runtime slot PVRZ→nom GL | défaut runtime exact |
| `lake-wtlake` nuit | AR0300N v10 | RGB nocturne ; opacité primaire/secondaire 160 ; q0.70 | choix artistique local |
| `pool-wtpool` | AR1000 jour v5 | bilinéaire x4 périodique sans SeedVR ; 6→36 linéaire/15 Hz ; blend 30 FPS ; matériau 1 ; q0.70 | AR1000 jour ; AR1000N exclu |
| `sewage-wtsew` | AR0404 | x4 `none`/3×3 ; 6→36 Apollo-8 ; matériau 4 ; q0.70 | AR0404 |
| `sewage-wtsew` | AR2100 | état natif q0 | fallback courant |
| `swamp-wtswam` | AR1607, AR1800 | paire sèche/pluie isolée ; 36 phases ; matériau 5 ; q0.70 | ces deux cartes |

AR0512 et AR1604 restent non qualifiées. Les familles huile, lave, goo et intérieures n'héritent
pas automatiquement des paramètres lac/piscine/marais.

## Composition connue

```text
U  = RGB overlay natif animé
P  = RGB matériau procédural animé
A  = art local de la base
a  = alpha effectif de A
U2 = mix(U, P, q)
C2 = a*A + (1-a)*U2
alpha(U2) = alpha(U)
```

Repères techniques :

- `q=0` correspond au chemin natif pour les identités ordinaires ; AR0300N v10 est une exception
  artistique dont le repli natif complet exige la paire assets/runtime v9.
- L'identité route2 utile lie WED/variante, hashes WED et TIS, slot overlay, page PVRZ, matériau et q.
- Une identité absente ou divergente retombe à q0 ; ce comportement évite les effets de bord.
- Le cycle validé le plus courant est 6 frames à 2,5 Hz vers 36 phases à 15 Hz, puis blend 30 FPS.
- Le contexte périodique 3×3 évite les coutures avant crop central.

## Paramètres de matériaux connus

| ID | Famille | Paramètres | q observé |
|---:|---|---|---:|
| 1 | WTLAKE / WTPOOL qualifié | matériau eau, teinte issue de l'art | 0.70 |
| 4 | WTSEW | deep `(0.10,0.075,0.03)` ; shallow `(0.24,0.19,0.075)` ; foam `(0.34,0.29,0.12)` ; foam 0.18 ; spec 0.08 | 0.70 AR0404 |
| 5 | WTSWAM | deep `(0.055,0.12,0.10)` ; shallow `(0.30,0.48,0.37)` ; foam `(0.30,0.40,0.31)` ; foam 0.25 ; spec 0.40 | 0.70 AR1607/AR1800 |

## Détails de réparation réutilisables

- Tuile monde x1 : 64 px ; tuile x4 : 256 px ; padding atlas habituel : 4 px x4.
- Raccord RGB validé : bande 8 px x4, garde vraie rive 1 px x1, poids
  `[1,1,1,1,.75,.5,.25,0]`.
- L'alpha central vient du chemin ARE/runtime réel : AR1607=100 ; AR1800 et AR0900=128. Il ne
  s'agit pas d'une constante globale.
- Une croissance de table d'animation WED déplace les offsets absolus suivants ; les symptômes
  utiles sont portes/polygones cassés ou crash intermittent.
- Une ressource partagée peut être isolée par alias lorsque ses consommateurs ne sont pas tous
  compatibles.

## Références finales

- AR1000 : `manifests/ar1000-wtpool-route2-validated-20260912-v5.json`
- Lacs : `manifests/ar0204-ar1600-validated-installed-20260912-v1.json`
- AR0900N : `manifests/ar0900-night-validated-20260912-v5.json`
- AR0300N : `manifests/ar0300n-reflections-alpha160-validated-20260912-v10.json`
- Égouts : `manifests/wtsew-ar0404-ar2100-validated-20260912-v1.json`
- Marais : `manifests/wtswam-ar1607-ar1800-validated-20260912-v1.json`
- État machine : `release-tracking-v1.json`
