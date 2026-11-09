# Projectiles3 — production 2026-11-09

**Trois images validées ingame —2026-11-09** : [acceptation et versions exactes](../projectiles3-accepted-20261109-v1/README.md). BGLRYU/SPCL236U SeedVR ; SPGLYPHI xBR.497/497entrées effets clôturées ; QA image acquise, pas de validation de tous les propriétaires/profils déduite.

**Installé pour test —2026-11-09** : [CLUA principales et vrais sorts](../../installations/projectiles3-selected-20261109-v1/CLUA.md), [reçu](../../installations/projectiles3-selected-20261109-v1/transaction.json). BGLRYU/SPCL236U SeedVR, SPGLYPHI xBR ;6ressources ajoutées,374backings,742ressources/72541backings courants.736anciennes ressources/72167backings conservés ;DLL avec routage installée,5/5tests,2880contrats candidat+installé. INI/PRO natifs inchangés ; QA ingame en attente, aucune release.

- Sources : BGLRYU, SPCL236U, SPGLYPHI ; 90 frames / 7 cycles natifs. Une production SPGLYPHI partagée TRAPGLPN/TRAPGLYP.
- **Choix utilisateur confirmé : `current-production.json` → `production-current-v3.json`**. BGLRYU et SPCL236U en SeedVR7B INT8/LAB x4/Apollo30 ; SPGLYPHI en xBR4X/Apollo30. `version-choice-20261109-v1.json` conserve la décision et la correction du nom doublé. Planche sur « Choix retenus » par défaut ; comparatifs et productions v1/v2 conservés.
- [Planche animée](http://127.0.0.1:8800/) : xBR / SeedVR / deux versions, natif synchronisé, cycles once/loop, phase, vitesse, fonds, simulation lumineuse, compagnon noir neutre. Fichiers : `review-versions/index.html` ; comparatifs statiques `comparison.png` et `comparison-xbr.png`.
- **Par méthode : 360 phases / 14 profils / 720 contrats natifs** ; 3 encodages par asset (canonique prémultiplié, alpha normal, halo noir neutre) : 2160 contrats/méthode, **4320 contrats sur les deux méthodes**. Vérifications octets/alpha/ancrages/horloges et lecteur natif passantes. 15FPS source = compatibilité, pas mesure ingame.
- Pixels/palette source immuables ; carriers ajoutent seulement le padding transparent nécessaire, ancrages monde/cycles/slots conservés. Alpha source ×4 ; interpolation d'alpha entre slots ; aucun lissage RGB/feather supplémentaire. Compagnon noir neutre conserve l'énergie RGB à ≤1/255.
- **Choix des versions acquis sur planche ; QA propriétaire/runtime distincte, aucune installation/release.** Whitelist secondaire préparée dans `effect_secondary_scope.h` ; DLL active non compilée/remplacée. Choix du blend/compagnon selon propriétaire encore requis pour l'intégration ingame.

| BAM | Propriétaires / ANIMATE | Natif | Phases | Profils |
|---|---|---:|---:|---:|
| BGLRYU | BGLRY / 0101, fumée ; SPPR612 | 20 frames / 1 cycle | 80 | 2 |
| SPCL236U | SPCL236 / 0102, fumée ; SPCL236.SPL | 10 frames / 1 cycle | 40 | 2 |
| SPGLYPHI | TRAPGLPN/TRAPGLYP / 0410, fragments ; SPPR304 | 60 frames / 5 cycles | 240 | 10 |

- Packs xBR : `effects/ressources/<BAM>/packs/<bam>-xbr4x-apollo30-profiles-20261109-v1` ; compagnons `*-xbr4x-apollo30-normal-20261109-v1`, `*-xbr4x-apollo30-neutral-20261109-v1`.
- Packs SeedVR : `effects/ressources/<BAM>/packs/<bam>-x4-apollo30-profiles-20261109-v1` ; compagnons `*-x4-apollo30-normal-20261109-v1`, `*-x4-apollo30-neutral-20261109-v1`.
- Preuves : `verification/`, `runtime-verification/`, `contracts/` ; xBR sous `alternatives/xbr4x-20261109-v1/`. `production.json` = baseline SeedVR figée ; `production-current-v2.json` = ancien défaut technique xBR ; `production-current-v3.json` = choix utilisateur courant.
- Inventaire effets élargi uniquement de 494 à 497 : 494 anciennes lignes inchangées, 3 productions en attente visuelle. Ancienne clôture : `prior-effects-completion.json` ; courant `effects/index/completion.json` = 494 clôturées/497, 3 entrées de QA propriétaire/runtime non clôturées. Ne pas réinterpréter le100% historique494 comme une QA de ces3.
- `effects/index/projectile-animation-sources.json` maintient les4liens implicites lors des régénérations d'inventaire/consommateurs ; aucun changement des PRO natifs ni des IDs.
- Recette : `pipeline/recipes/projectiles3-production-20261109-v1/` : `prepare.py` → `produce.py` (SeedVR/Apollo) → `companions.py` → `finalize.py` ; alternative `faithful.py` → `publish_versions.py`. Runs scellés réutilisés, pas d'écrasement des images acceptées.
- Service de revue : `python -B -m http.server 8800 --bind 127.0.0.1 --directory effects/batches/projectiles3-production-20261109-v1/review-versions`. ComfyUI laissé ouvert pour l'utilisateur, modèles SeedVR déchargés après les90frames.
