# Lot26 — acceptation utilisateur 2026-10-17

- Décision : « ok les 09 et 26 sont visibles avec le décalage et le 12 est corrigé. tout est validé, mets à jour le suivi et committe. » **26/26 acceptés ingame**.
- `acceptance.json` :26packs mono-BAM finaux,28RESREF runtime liés à leurs manifests/run/encodage ; SPIPLARI canonique et X26PLAA normal réutilisent SPIPLAAI sans production indépendante.15ressources normales et alias droit liés séparément du pack prémultiplié.
- Versions finales :8SDF sans retrait (`lot26-sdf-no-inset-20261017-v1`), OHRFEAR facefill (`ohrfear-face-fill-20261017-v1`),17autres v2. SplineFit1 et retraits1/2px non retenus ; anciens essais/preuves conservés.
-09TRVENTAA /26TRSPEART : visibilité confirmée par utilisateur avec contrôleurs X=64, Z26V09/Z26V26 ; mêmes images/alpha/blend/cycle/durée que Z26T09/Z26T26. Validation des tests décalés ; aucune modification des consommateurs natifs ni mesure fine d’occlusion déduite.
-12OHRFEAR : trou central comblé avant feather12 ;90phases/3s, contour extérieur et RGB existants préservés ; correctif accepté.
- SeedVR7B x4/LAB, Apollo30/NEAREST, doublons sources retirés avec durée native conservée ;2620phases/60profils. TRAPGR statique conservé. Validation visuelle distincte d’une mesure instrumentée de cadence.
- Runtime installé accepté :245productions/253RESREF,32927backings ; manifest `44A63CBDDC7609D9C89921C0BEBE148A577847AB28D2B400DB8AEDF91C34E924`.70888contrats natifs vérifiés à l’installation ; métadonnées32Mio. Correctif bandes blanches et profil personnages conservés.
- `verification.json` :26sélections/décisions cohérentes, autres lignes et autorités installation/release inchangées ; `processing-before.csv` = état avant acceptation.
- [26commandes validées](CLUA.md), incluant09/26décalés ; [60profils historiques](../../installations/lot26-sdf-no-inset-20261017-v1/CLUA-tous-profils.md), pas de validation individuelle de chaque profil déduite.
- Reçus historiques `qa_accepted:false` /`pending-user-test` immuables : cette décision enregistre leur validation ultérieure. Aucune nouvelle installation ni release.
- Recette : `python -B pipeline/recipes/effects-lot26-accept-20261017-v1/accept.py`, refuse de réécrire la décision finale.
