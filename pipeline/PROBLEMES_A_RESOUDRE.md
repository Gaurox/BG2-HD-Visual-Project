# Problèmes à résoudre

Ce fichier ne contient que les blocages ouverts. Les décisions durables sont dans
[`../docs/DECISIONS.md`](../docs/DECISIONS.md) et les preuves moteur dans
[`../engine/InfinityEngine-Enhancer/source-patchee/docs/validation/`](../engine/InfinityEngine-Enhancer/source-patchee/docs/validation/).

## WORKFLOW-PERF-001 — Délai des tâches locales

- Symptôme : une petite tâche peut dépasser 10 minutes.
- Causes mesurées : contrôles globaux répétés, fallback `full`, double déterminisme, tests sur le
  workspace réel et ~192 Gio/~466 k fichiers locaux dans le worktree.
- Mitigation active : tests plan-only avec ciblage strict ; projections plan-only, mono-passe et
  scopes `graphics`/`registry`/`integrity` ; choix séparés avant `--run`.
- Travail restant : cache par hashes, scopes métier plus fins, séparation unitaires/intégration et
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
| AR0404 | WTSEW trop clair/propre ; nouvelle QA requise |
| AR1607 | WTSWAM brun et pause visible |
| AR1800 | WTSWAM brun et pause visible |
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

## WTPOOL-001 — Piscines x4

- Limite observée : certaines petites piscines dépassent le coût visuel acceptable après
  reconstruction.
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

## ENGINE-UI-001 — États UI personnalisés

Valider séparément survol, clic, disabled, clavier et résolutions prises en charge. Une capture du
menu au repos ne suffit pas.

## ENGINE-OCCLUSION-001 — Animations par occurrence

Le chemin v3 dépend du bridge moteur et de la couverture WED. Toute nouvelle zone doit fournir une
preuve d'identité hors occlusion et une QA in-game de l'occurrence ciblée.
