# Monster — Q3m V7 x2 — génération canonique v2

- État : **production complète et vérifiée sur hôte**. Installation/QA ingame/release séparées, non demandées.
- Sources : 62 modèles/77 IDs, 850 BAM/409 599 frames physiques ; 25 IDs sans BAM exclus. `selection.json`, `source-scope.json`.
- Recette : K6, quatre partenaires, huit niveaux, x2, sans SDF ; FP16 x4/fixed86/q32 → BOX float32 x2 ; palettes natives vivantes V7/8–9/rule3. `recipe.json` → recettes d'encodage/assemblage acquises v1.
- Travail unique : 102 824 clés source effectives/102 953 encodages ; 648 hits, 102 144 nouveaux encodages, 161 travaux spéciaux ; 612 848 cibles neurales neuves, 17 594 guides neufs. 67 836 guides historiques adoptés, namespaces exacts conservés. `production.json`, `plan.json` ; compteurs par ID non additifs.
- Pack : `sprite/.work/q3m-monster-full-x2-20261006-v2/isolated/` ; 1 037 feuilles/496 816 frames physiques → 1 040 liaisons/496 822 occurrences. Oracles pixel et représentants mutualisés par clé ; géométrie/cycles natifs par occurrence.
- Réemploi : reprise 102 953/102 953, zéro inférence/encodage ; empreintes cache inchangées, 187 feuilles du pack partiel identiques. Aucun groupe spatial natif Monster ; passage contextuel automatique : zéro contexte.
- Palettes : 15 BMP natives monde ; INV auxiliaires avec leur palette propre. `MFIEG3B` 252 entrées : queue native nulle conservée, aucun pixel BMP interprété comme couleur.
- Grandes frames : 45 `MKUOG2SL` 320×240 ; représentants u16 vérifiés avant conversion ; dimensions/centres/cycles natifs conservés.
- Correction catalogue seule : trois listes d'appartenances triées en indices strictement croissants ; 1 037 feuilles et oracle intégral inchangés. Parent v1/proof de rejet conservés. `catalog-repair.json` ; sérialiseur corrigé `pipeline/scripts/q3m_family_witnesses.py`.
- Contrôles acquis : 25 tests ciblés ; reprise sans import Torch ; 1 040 liaisons/496 822 frames vérifiées (I/F/dep, géométrie, cycles, profils, représentants). Contrôle natif K6×3 formats **réussi** : 496 822 frames, 869 792 positions de cycles, 48 220 685 712 pixels décodés. `native_validate.py`, 33 sous-lots ; `verification.json`.
- Comparatifs : cinq planches/77 variantes (`previews.json`), natif x2 Nearest / Q3m x2 ; [1](comparison-01.png), [2](comparison-02.png), [3](comparison-03.png), [4](comparison-04.png), [5](comparison-05.png). Rendu des cinq planches inspecté, aucune QA ingame déduite.
- Suivi final : Monster production seule, 77 lignes ; **213 IDs/13 familles produites**, 136 IDs/12 familles installés et acceptés inchangés. `finalize_tracking.py`.
