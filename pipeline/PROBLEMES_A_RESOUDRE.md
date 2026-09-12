# Problèmes à résoudre

Ce fichier ne contient que les blocages ouverts. Les décisions durables sont dans
[`../docs/DECISIONS.md`](../docs/DECISIONS.md) et les preuves moteur dans
[`../engine/InfinityEngine-Enhancer/source-patchee/docs/validation/`](../engine/InfinityEngine-Enhancer/source-patchee/docs/validation/).

## WORKFLOW-PERF-001 — Délai des tâches locales

- Symptôme : une petite tâche peut dépasser 10 minutes.
- Causes mesurées : contrôles globaux répétés, fallback `full`, double déterminisme, tests sur le
  workspace réel et ~192 Gio/~466 k fichiers locaux dans le worktree.
- Mitigation active : tests/projections plan-only ciblés ; catalogue sprites avec preuve scellée,
  cache SHA/CRC par identité, lots provisoires, gate globale et reprise des seuls scopes
  échoués/modifiés.
- Travail restant : étendre ce modèle hors catalogue sprites ; séparation unitaires/intégration et
  data-root externe.
- Rapport : [`../docs/WORKFLOW_PERFORMANCE_AUDIT.md`](../docs/WORKFLOW_PERFORMANCE_AUDIT.md).

## MAP-PERF-001 — Chargement des cartes x4

- Cause mesurée : attente synchrone dans `CResPVR::Demand` lors des accès de pages PVRZ.
- Prototype courant : phase B2f, désactivée par défaut, un seul slot JIT et quatre revendications
  explicites.
- Preuve disponible : un passage quatre zones, `16/16` observations valides, documenté dans
  [`map-page-offframe-phase3b2f.md`](../engine/InfinityEngine-Enhancer/source-patchee/docs/validation/map-page-offframe-phase3b2f.md).
- Manque : campagnes A/B répétées, contrebalancées, binaire final et cache froid.
- Conséquence : ne pas qualifier ni publier la fonctionnalité à partir du passage actuel.

## MAP-QA-001 — Cartes installées en attente de QA

`areas.csv` reste l'autorité. État courant à traiter :

| Zone | Point à reprendre |
|---|---|
| AR2300 | crash de carte complète et incohérence d'eau ; reprise complète |

Ne jamais convertir `installed-pending-qa` en `validated-installed` sans décision explicite.

## MAP-OVERLAY-001 — Politique WTLAVA-D contradictoire

`releases/BG2-HD-Upscale/manifests/overlay-sources.json` sélectionne le package x4 pour `WTLAVA-D`,
alors que `audit_water_area.py` et `audit_area_preflight.py` le classent encore comme overlay stock.
La release suit son manifeste ; le préflight doit rester considéré ambigu tant que code et manifeste
ne sont pas réconciliés par une décision explicite.

## WATER-001 — Eau par spline

- Le pipeline spline reste le chemin retenu pour les grands contours.
- Des artefacts de diagonales et de raccord peuvent encore nécessiter un réglage par zone.
- Les masques polygonaux restent une solution de repli documentée dans
  [`GEOMETRIC_ALPHA_MASK_CLEANUP.md`](GEOMETRIC_ALPHA_MASK_CLEANUP.md).

## WATER-002 — Portage de la réparation eau native aux autres maps

- AR0900 jour entièrement corrigé et validé par l'utilisateur le 2026-09-12 : composition native,
  WTLAKE périodique, alpha128 central, bandes RGB/alpha des interfaces internes et marges.
- Notice technique et preuves : [`WATER_REPAIR_RUNBOOK.md`](WATER_REPAIR_RUNBOOK.md).
- Restent : orchestrateur paramétré, audits/builder legacy recommandant alpha0, qualification des
  autres structures/familles et variantes nuit. Ne pas généraliser les constantes du témoin.
- La configuration Core release impose encore `EnableWaterEffect=true`, contrairement au témoin ;
  intégration release distincte à décider, aucun bundle/payload à reconstruire implicitement.

## WATER-003 — WED timeline WTLAKE : offsets des polygones d'objets

- Cause : insertion60octets dans la timeline sans déplacer les offsets internes des portes.
- Producteurs corrigés par `scripts/water_wed.py` ; AR0204/AR1600 réinstallés et validés ingame
  le 2026-09-12.
- Restent installés hors périmètre de ce correctif : AR0300/N, AR0900/N, AR2300.
- AR0204 BRIDGE01 a0polygone : offset incohérent corrigé, pas de crash prouvé associé.
- Preuves, reçus et QA : [`water/AR0204_AR1600_REPAIR_20260912.md`](water/AR0204_AR1600_REPAIR_20260912.md).

## WTPOOL-001 — Piscines x4

- Limite observée : certaines petites piscines dépassent le coût visuel acceptable après
  reconstruction.
- AR1000 jour : v1 rejetée sur crash de nom de page ; v2 charge mais rejetée pour quadrillage.
  SeedVR x4 amplifie la faible trame diagonale source en reliefs rectangulaires répétés. V2 restaurée ;
  v3 non générative installée : bilinéaire x4 périodique3×3, interpolation cyclique linéaire
  6→36phases/15Hz, q0 ; énergie haute fréquence17,2763→1,4345. Q0 accepté sans quadrillage mais
  rejeté comme figé. Voie2 v5 installée sur identité AR1000 exacte : blend30FPS, matériau1, q0.70 ;
  validée ingame le2026-09-12. Base conforme ;37/37cellules avec secondaire, aucune correction alpha
  central ; nuit exclue. Cas AR1000 jour résolu ; aucune généralisation WTPOOL.
- Ne pas généraliser un masque ou un seuil depuis une seule zone.

## ALPHA-001 — Liserés de transparence

- Contrôler les bords prémultipliés, les pixels RGB cachés et le filtrage de redimensionnement.
- Une correction globale exige une preuve sur plusieurs familles d'assets.

## ANIMATION-QA-001 — Catalogue alpha historique introuvable

- Preuve requise : `animations/index/animation_alpha_corrections.csv`, SHA-256
  `71957CF367ADE35572DA2C2D3C20D89C1574AED3FB416C62C5E542F8B0E5D078`.
- Recherche négative au 2026-09-02 : branches et objets Git, six racines BG2 sous `G:/AI`,
  2 078 fichiers plausibles et cinq archives ZIP.
- Zones bloquées : `AR0309`, `AR0800`, `AR1100`, `AR1200`, `AR1700`, `AR1800`, `AR2000`,
  `AR3000`, `AR5500`, `AR6400`, `OH4000`, `OH6000`, `OH6100`, `OH6400`.
- Résolution : retrouver les octets exacts ou créer de nouvelles approbations QA pour les runs
  courants après contrôle ingame explicite. Ne jamais modifier les approbations scellées existantes.

## ANIMATION-LEGACY-001 — Sources proto de tests AR0602 absentes

- Six références historiques restent sans source : `AM0602C/D/E/G-eau-canvas-feather-x4`,
  `FLAME2S-flamme-luminance-fade-x4`, `FLAME2S-flamme-radial-fade-x4`.
- Elles sont citées uniquement par quatre packs d'essai du run `ar0602-eau-seedvr3b-lab-x4`.
- Ne pas les rediriger vers les prototypes alpha/radial actuels sans preuve d'identité.

## MAP-PROVENANCE-001 — Intermédiaires AR0016/AR0017 absents

- Sorties SeedVR x4 scellées manquantes : SHA-256 `DAA4CD48…` pour `AR0016` et `15CD116C…`
  pour `AR0017`; builds finaux présents.
- Aucune copie retrouvée sous les six racines BG2 ou dans les cinq ZIP inspectés au 2026-09-02.
- Résolution : retrouver les fichiers exacts ou produire de nouveaux runs/builds sans réécrire
  `upscale-01`.

## SPRITE-PROVENANCE-001 — Recettes historiques non snapshotées

- Cinq builds anciens citent des versions disparues de trois jobs mutables ; les générations
  courantes restent séparées et valides.
- Aucune copie correspondant aux cinq SHA-256 n'a été retrouvée dans les copies BG2 ni dans les
  objets Git au 2026-09-02.
- Résolution : retrouver les JSON exacts et les archiver comme snapshots de compatibilité ; ne pas
  modifier les builds historiques.

## SPRITE-SHADER-D7-001 — Portée x1 non qualifiée

- Candidat partiel : x2 `CreatureHD` validé ; zéro bind/draw `fpSprite`/`fpSELECT`, x1 sans différence.
- Cause : les contrats D7 étaient appliqués aux programmes seulement ; le chemin réel restait
  `fpDraw` et ne sélectionnait pas les slots 5/7 dans la scène observée.
- Correctif source : scopes propriétaires créature/objet au sol et mise en file du slot 5 au point
  commun ; HD, x2, tons spéciaux et absence de contrat restent neutres.
- Trace corrective : 64 routes objet au sol vers le slot 5, un draw `fpSprite`, six draws x2
  `CreatureHD`, aucune erreur shader/OpenGL. Le budget borné ne trace pas de propriétaire créature.
- QA utilisateur : effet x1 visible ; profil Dshaders initial rejeté au profit du rendu doux x2.
- Profil soft035/native tracé : 80 routes sol, 48 routes créature, quatre `fpSprite` actifs avec
  `Sharpen=-0.35`, sept `CreatureHD` actifs, aucune erreur. Le halo natif `fpSprite`
  (`uSpriteBlurAmount=5`) reste visible et est rejeté comme contour noir.
- Candidat courant : `d7-20260910-sprite-scope-catmull-x1-samplerfix`, correctif `a8eccd4` ;
  `fpSprite`/`fpSELECT` Catmull–Rom, `Stored`, `Sharpen=-0.35`, couleurs neutres ; `fpSprite`
  `OutlineMode=Dshaders` + rayon `0`, texture HD exclue. Build Release et validation offline 2.7.3
  réussis ; tests refusés. Candidat précédent restauré, installation et reçus vérifiés.
- Trace `21:01:57–21:02:25` : 64 routes créature, deux `fpSprite` en mode 2 et `-0.35`, dont un
  sampler `LINEAR` substitué ; zéro erreur de restauration/shader/OpenGL. Rendu x1 sans halo validé
  par l'utilisateur. Douceur supérieure au x2 expliquée par la résolution source et le rayon du
  noyau en texels, pas par un écart de profil.
- A/B `d7-20260911-all-sprites-soft025-outline071` rejeté : le contour Dshaders `0.71` produit un
  rendu noir incompatible avec les sprites upscalés ; l'effet des pixels de bord semi-transparents
  reste une hypothèse visuelle non démontrée.
- Candidat installé `d7-20260911-all-sprites-soft025-nooutline` : `Sharpen=-0.25`, couleurs neutres
  sur `CreatureHD`/`fpSprite`/`fpSELECT`, aucun contour shader (`fpSprite` Dshaders taille `0`, autres
  profils natifs). Installation vérifiée par le reçu
  `backups/renderer/20260911T154559944738Z-3fd749f7/renderer-install-receipt.json`, ensemble SHA-256
  `2B782BAAA4518BC617E19F3F6BEF6E10632A7BE73125808C1FB5623DA7F50602`. QA ingame en attente.
- Manque : draws Catmull–Rom objet au sol et `fpSELECT`, plus témoin `CreatureHD` dans la même
  session ; ne pas déclarer D7 terminé avant cette couverture.

## ENGINE-UI-001 — États UI personnalisés

Valider séparément survol, clic, disabled, clavier et résolutions prises en charge. Une capture du
menu au repos ne suffit pas.

## ENGINE-OCCLUSION-001 — Animations par occurrence

Le chemin v3 dépend du bridge moteur et de la couverture WED. Toute nouvelle zone doit fournir une
preuve d'identité hors occlusion et une QA in-game de l'occurrence ciblée.
