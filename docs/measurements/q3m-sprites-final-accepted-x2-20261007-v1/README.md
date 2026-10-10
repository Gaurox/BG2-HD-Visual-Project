# Sprites — acceptation finale utilisateur — 2026-10-07

- Décision : **« c'est bon confirmé »**, après demande de confirmation des animations Character et de l'attaque QMON7313 sur le correctif commun installé. Aucun nouveau log de session revendiqué ; autorité QA = utilisateur.
- **15 familles /331 IDs produits, installés, acceptés ingame** : 14 familles Q3m amélioré/253 IDs +Character V6 retenu/78 IDs. Sources absentes et IDs hors périmètre retenu exclus ; aucun lot ni retest restant de ce périmètre.
- Monster : **77 IDs /62 modèles**, acceptation cumulative75 acquis +7312/7313 G2 corrigés. [QA complète](../../../sprite/index/qa-decisions/monsters/2026-10-07-accepted-full-monster-q3m-v7-x2-nearest-v4.json), [inventaire exact](accepted-monster-asset-scope.csv).
- Runtime partagé : [QA](../../../sprite/index/qa-decisions/runtime/2026-10-07-accepted-common-sprite-playback-x2-v1.json), DLL `70a2745b…bb6d09`, catalogue `2ad7838c…00b289c`. Confirmation du correctif général ; aucun retest individuel des331 IDs dans une nouvelle session déduit. Acquis familiaux et preuves hôte conservés.
- Aucune installation/inférence/reconstruction nouvelle ; reçus historiques et décisions QA immuables. Seul reçu actif local du runtime passe à `installed-ingame-accepted`. Suivi métier/queue mis à jour ; autres familles inchangées.
- [Résumé scellé](acceptance-summary.json). `accept.py` enregistre cette décision une fois ; ne pas réexécuter/remplacer les preuves finales.
- [Cohérence des15 variantes acceptées](closure-verification.json), `verify_closure.py` : Ankheg utilise sa variante V9 SDF stable acquise ; son ancienne production sans SDF garde son état historique, sans promotion. Corps/équipements Character V6 retenus ; essais stock non installés exclus.
- **Release inchangée** : pas de payload/staging/content.json/TP2/archive modifié, aucune intégration release déduite.
