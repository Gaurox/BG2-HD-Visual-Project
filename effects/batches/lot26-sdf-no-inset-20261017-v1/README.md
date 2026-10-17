# Lot26 — SDF sans retrait

- Validation ultérieure : [26/26 acceptés ingame](../lot26-accepted-20261017-v1/README.md), avec OHRFEAR remplacé par le dérivé facefill et tests09/26décalés. `production.json` reste la preuve historique de cette étape.

- Demande2026-10-17 : annuler le retrait intérieur ; conserver le lissage SDF du comparatif8787, installer les26 pour test.
- Base : `../lot26-seedvr7b-apollo30-20261017-v2/batch.json` ; SeedVR7B x4/LAB, Apollo30, doublons sources retirés avec durée native conservée.
- 8 dérivés /404phases : SPHEART, SPHANDAT, SPRAISED, GLPHWRDT, SKLT, SPTRAPBB, TRAPGR, TRSPEART. Alpha raster SDF Ankheg adapté : inset0, sigma4/biais±2 équivalents x4, couverture8×8, topologie protégée sur grillex2. Le biais borné de reconstruction ne constitue pas une érosion.
- `sdf-verification/*.json` : RGBA droits identiques au comparatif sans retrait ; prémultiplication unique pour les packs lumineux ; timings/carriers conservés.
- 18 autres productions v2 inchangées ; 26productions/27RESREF sources, 2620phases/60profils. TRAPGR statique conservé.
- `production.json`, `checks/*.json` = production ; état d’installation distinct dans [le reçu](../../installations/lot26-sdf-no-inset-20261017-v1/installation.json). QA ingame en attente ; aucune sélection acceptée ni release modifiée.
- Recette : `pipeline/recipes/effects-lot26-sdf-install-20261017-v1/` ; anciens essais SplineFit1 et retraits1/2px conservés, non retenus.
