# Eau BG2EE — inventaire de solutions validées

Mémoire de diagnostic, à consulter par symptôme ou famille. Aucun ordre, préflight, audit ou lot
jour+nuit n'est imposé. Les valeurs ci-dessous sont des précédents réutilisables quand le cas est
compatible, pas des recettes universelles.

## Solutions par symptôme

| Symptôme | Cause observée | Solution utile |
|---|---|---|
| Crash au chargement | nom PVRZ > capacité resref, page mal nommée ou offsets WED non relocalisés | borner les resrefs à 8 octets ; recalculer pagination et offsets WED |
| Quadrillage/répétition WTPOOL | SeedVR amplifie la trame diagonale du 64×64 stock | bilinéaire x4 non génératif en contexte périodique 3×3, crop central |
| Eau propre mais figée | voie 1/q0 sans mouvement procédural perceptible | [30 FPS réels](TEMPORAL_30FPS_PIPELINE.md) (historique : 36 phases/15 Hz + blend) ; route2 exacte si souhaitée |
| Animation saccadée | seulement 6 frames ou absence d'interpolation temporelle | historique : 6→36 phases + blend 30 FPS ; actuel : [30 FPS réels](TEMPORAL_30FPS_PIPELINE.md) |
| 30 FPS « non ressenti », pop toutes les 0,4 s | ancres x4 SeedVR image par image (détail ×3), Apollo inadapté au miroitement, demi-fondu shader | interpolation trigonométrique x1 → SeedVR un seul chunk vidéo → 72 phases/4096, source=cible 30 ([AR1600 v2](AR1600_WATER_30FPS_V2_20260923.md)) |
| Traits noirs/bleus | RGB primaire contaminé ou padding incohérent | greffe RGB bornée depuis le secondaire de même coordonnée ; padding 4 px x4 |
| Frange sombre, cordes/gréement épais ou en escalier devant l'eau | alpha HD issu du masque x1 révèle le fond noir du RGB x4 | C : silhouette RGB x4 + liseré recoloré + **spline fit 1** (défaut 2026-09-25, [CONTOUR_MATTE_PIPELINE](CONTOUR_MATTE_PIPELINE.md)) ; exceptions par map AR0408/AR0703 |
| Art local, ombres ou reflets disparus | alpha central 0/255 ou passe secondaire perdue | restaurer l'alpha natif effectif et la composition primaire/secondaire |
| Marche de luminosité | opacités primaire/secondaire désaccordées | apparier les contributions ; AR0300N v10 utilise 160/160 localement |
| 30 FPS actif mais eau « qui grouille », micro-saccade | bouillonnement du détail SeedVR (65 % du pas) + cadence latente 4 images | `temporal_harmonics` 1,5 × clés + `equalize_detail` ([TEMPORAL_30FPS_PIPELINE](TEMPORAL_30FPS_PIPELINE.md)) |
| Ligne floue à chaque bord de tuile (tuile unique) | collier de raccord 8 px x4 lisse ~10 px de détail | `seedvr-torus` 1×1 à la place du collier |
| Lignes fines aux bords de cellules eau pure ↔ décor | interfaces A non réparées (pavage A–D) + matte C comptant l'eau pure comme objet | bases A par famille + C `central_water` (AR5000 5,69 → 3,14) |
| Bande claire au bord des tuiles d'un pavage lisse | rangée de bord native +1 amplifiée par SeedVR | `deridge_band_x1` (WT5000A–D) |
| Grille régulière sur un pavage A–D après SeedVR | raccords natifs des tuiles 64 px amplifiés (×1,2 → ×1,56) | recoller les bords en x1 avant interpolation ; `seedvr-torus` ([TEMPORAL_30FPS_PIPELINE](TEMPORAL_30FPS_PIPELINE.md)) |
| Map 30 FPS qui rame (FPS ÷5), CPU hook faible | scan DLL de toutes les tuiles overlay à chaque draw (multi-slots) | cache de correspondance overlay dans la DLL (build ≥ `ar5200-lava-torus-30fps-20260924-v1`) |
| Mosaïque sous pluie | seule la ressource sèche a été traitée | créer/router la ressource alternative pluie exacte |
| Pluie x4 active mais aucune flaque (page `…R00` jamais lue) | moteur 2.7.3 : une tuile PVRZ reçoit la page du wrapper **sec** même en état pluie (RVA 0x2A46AF..0x2A477C) ; seules les UV viennent du TIS pluie | DLL ≥ `ar0500-rain-q0-20260925-v2` : le hook lie la page de la ressource dessinée (log `TILE_RESOURCE_PAGE`) ; toutes les pluies x4 antérieures n'étaient jamais affichées |
| Flaques de pluie invisibles malgré la page pluie liée | q > 0 : P remplace 70 % de U (`mix(U, P, q)`), anneaux WTSWAMR effacés | pluie **q0** (timeline seule) ; essai q0,70 rejeté sur AR0500 |
| Route2 invisible | WED/TIS/page/nom GL non reconnu ou hash divergent | corriger l'identité exacte du registre ; garder q0 pour les cas non reconnus |
| Eau parfois brune | `CResPVR::texture` pris pour un nom GL au lieu d'un slot moteur | runtime avec résolution slot→descripteur→nom GL ; ne pas retraiter les PVRZ |
| Autre carte modifiée | remplacement global d'un overlay partagé | alias isolé et routage WED/registre limité aux identités ciblées |
| Eau intérieure artificielle | matériau lac propagé à une autre ambiance | qualifier un matériau/environnement distinct ou rester à q0 |

## Cas de référence

| Famille | Identité validée | Paramètres utiles | Portée |
|---|---|---|---|
| `lake-wtlake` | AR0900, AR0204 (AR1600 : historique, remplacé par la ligne 30 FPS) | WTLAKE x4 périodique ; 36 phases/15 Hz ; blend 30 FPS ; matériau 1 ; q0.70 | identités exactes |
| `lake-wtlake` nuit | AR0900N v5 | maîtres nuit, alpha128, raccords, cache WED renouvelé ; q0.70 | AR0900N |
| `lake-wtlake` nuit | AR0046N v7 | correction runtime slot PVRZ→nom GL | défaut runtime exact |
| `lake-wtlake` nuit | AR0300N v10 | RGB nocturne ; opacité primaire/secondaire 160 ; q0.70 | choix artistique local |
| `pool-wtpool` | AR1000 jour v5 | bilinéaire x4 périodique sans SeedVR ; 6→36 linéaire/15 Hz ; blend 30 FPS ; matériau 1 ; q0.70 | AR1000 jour ; AR1000N exclu |
| `pool-wtpool` standard | AR0408 v2 + AR0703 v1 (2026-09-23) | AR0408/AR0703 valident A → B ; bilinéaire x4 ; 72 phases/30 Hz ; matériau 1 ; **q0.70 sec**, pluie q0 ; C AR0703 historiquement validé mais désormais provisoire | contrat famille ; pluie non observée en intérieur AR0703 |
| `swamp-wtswam` standard | AR0500 + AR0500N (2026-09-24) | A SeedVR 7B x4 ; B trig x1 → SeedVR vidéo, 72 phases/30 Hz, cycle 2,4 s ; matériau 5 ; **q0.70 sec, pluie q0** | A/B validés ingame jour+nuit ; pluie validée AR0500 2026-09-25 (`ar0500-temporal-30fps-user-qa-20260925-v1.json`), AR0500N pluie q0 installée non observée ; **lot de 14 maps A→B→C validé 2026-09-25** (sans reprise) |
| `oil-wtoil` standard | AR0503 (2026-09-24) | A SeedVR x4 ; B `seedvr-torus` 1×1, 72 phases/2,4 s, harmoniques ≤ 9 + égalisation du détail ; matériau 1 **q0** ; C provisoire validé avec réserve | contrat famille ; pluie non observée ; AR0413 hors standard |
| `brown-wt5000` standard | AR5000 (2026-09-25) | A SeedVR x4 + interfaces par famille ; B `seedvr-torus` 2×2, 128 phases/4,27 s, recollage off, décrêtage x1, σ périodique 2, harmoniques ≤ 12 + égalisation ; C `central_water` | contrat famille ; pluie non observée |
| `lake-teal-wtlaka` standard | AR6300 (2026-09-25) | B `seedvr-torus` 2×2, 128 phases/4,27 s, recollage off, σ périodique 2, harmoniques ≤ 12 + égalisation, sans décrêtage ; C gaussien, alpha 160 | contrat famille ; AR3000 témoin historique ; pluie non observée |
| `lava-wtlava` standard | AR5200 (2026-09-24) | B `seedvr-torus` : recollage x1 des bords 64 px, trig 12 clés → 216 phases/7,2 s, SeedVR vidéo motif+marge enroulée, périodique+lisse σ8 ; matériau 1 **q0** ; C provisoire validé avec réserve | contrat famille ; autres maps lave : adjacences tore à vérifier ; pluie non observée |
| `swamp-wtswam` nuit | AR1000N v1 sec | réemploi WSWPIL x4 non génératif ; 36 phases/15 Hz ; blend 30 FPS ; matériau 5 ; q0.70 | AR1000N sec ; animation discrète acceptée ; pluie non observée |
| `sewage-wtsew` | AR0404 | x4 `none`/3×3 ; 6→36 Apollo-8 ; matériau 4 ; q0.70 | AR0404 |
| `sewage-wtsew` | AR2100 | état natif q0 | fallback courant |
| `swamp-wtswam` | AR1607, AR1800 | paire sèche/pluie isolée ; 36 phases ; matériau 5 ; q0.70 | ces deux cartes ; pluie PVRZ `WWPILR00` jamais affichée avant la DLL v2 (voir symptômes) |
| `lake-wtlake` 30 FPS | AR1600 v2 (2026-09-23) | alias `QBLKV0`/`R` ; 72 phases/30 Hz ; trig x1 + SeedVR vidéo ; page 4096 ; force 0 | AR1600 slot1 ; pluie non confirmée |

État historique au 2026-09-23 : AR1000 jour, AR1607, AR0404 utilisent les alias `Q9*` du lot spatial
([ESSAIS_FAMILLES_X4](ESSAIS_FAMILLES_X4_20260923.md), lookup native, q0) ; leurs lignes 36 phases/q0.70
ci-dessus sont des recettes acquises mais non installées. État standard courant :
[`manifests/water-standard-map-status-20260923-v1.json`](manifests/water-standard-map-status-20260923-v1.json).
Apollo est rejeté pour les overlays liquides ([TEMPORAL_30FPS_PIPELINE](TEMPORAL_30FPS_PIPELINE.md)).

AR0512 et AR1604 restent non qualifiées. Les familles goo et intérieures n'héritent
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
| 5 | WTSWAM | deep `(0.055,0.12,0.10)` ; shallow `(0.30,0.48,0.37)` ; foam `(0.30,0.40,0.31)` ; foam 0.25 ; spec 0.40 | 0.70 AR1607/AR1800 et AR1000N sec |

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
- AR1000N : `manifests/ar1000n-wtswam-route2-validated-20260912-v1.json`
- Lacs : `manifests/ar0204-ar1600-validated-installed-20260912-v1.json`
- AR0900N : `manifests/ar0900-night-validated-20260912-v5.json`
- AR0300N : `manifests/ar0300n-reflections-alpha160-validated-20260912-v10.json`
- Égouts : `manifests/wtsew-ar0404-ar2100-validated-20260912-v1.json`
- Marais : `manifests/wtswam-ar1607-ar1800-validated-20260912-v1.json`
- Marais standard jour/nuit : `manifests/ar0500-temporal-30fps-user-qa-20260924-v1.json`,
  `manifests/ar0500n-temporal-30fps-user-qa-20260924-v1.json`
- État machine : `release-tracking-v1.json`
