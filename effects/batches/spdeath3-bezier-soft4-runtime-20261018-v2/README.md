# SPDEATH3 — dérivé runtime Bézier/sigma4

- Demande : choisir sigma4, installer SPDEATH3 seulement, fournir CLUA. [`production.json`](production.json), [`geometry-verification.json`](geometry-verification.json), [`batch.json`](batch.json). Choix du fondu visuellement approuvé, aucune acceptation ingame/release déduite.
-124phases exactes du comparatif soft4 dans les deux encodages ; courbes Bézier +alpha continu +fondu gaussien prémultiplié limité au bord, cœur exact≥16x4. Aucun nouveau modèle lancé, durées once/loop62phases/31/15s inchangées.
- Run `spdeath3-bezier-soft4-20261018-v2`, pack `spdeath3-7b-bezier-soft4-apollo30-20261018-v2`. Géométrie64×104x1/centre33,60/256×416x4 ; marge transparente commune5x1,30frames BAM source conservées en pixels/palette/cycles/lookup/coordonnées monde.
-123backings par encodage ; IDs de stockage recalculés sans altérer la chronologie. La v1 non scellée reste conservée, erreur d'encodage JSON int64 corrigée.
- Installation distincte : [`SPDEATH3 sigma4`](../../installations/spdeath3-bezier-soft4-20261018-v1/README.md), testZ33T33. Source/production/QA/install/release séparées ; état `installed:false` du reçu de production historique n'infère pas l'état ultérieur de l'installation.
