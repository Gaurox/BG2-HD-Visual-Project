# Déduplication source de tous les profils sprites — 2026-10-03

- Portée : 14 profils hors `character`, 387 IDs définis / 257 avec BAM ; Character 78 IDs repris depuis son SQLite acquis en lecture seule. Effets/UI exclus.
- Résultat : **4 014 BAM / 699 374 frames → 194 573 travaux source distincts** ; 504 801 répétitions physiques et 1 016 183 répétitions entre consommateurs évitées.
- 192 248 rasters indexés distincts ; 194 158 travaux source candidats modèle / 415 autres. Ces catégories décrivent la source, pas les exceptions finales d'un profil encore inconnu.
- 212 BAM identiques décodés une seule fois, égalité des octets contrôlée ; 2 355 sources extraites existantes relues, 1 659 BAM manquants lus directement dans le KEY/BIF stock. Aucune extraction/ressource/installation historique modifiée.
- Intersection Character : 5 travaux source exacts, comparaison d'indices et RGB utilisés ; **aucune adoption I/F/dep par simple ressemblance**. Union tous personnages/créatures : 2 263 428 frames / 758 537 travaux source, effets exclus.
- Monster acquis : 39 BAM / 20 925 frames reliés aux 3 190 travaux du plan précédent. `known-monster-cache-resume.json` : 3 190/3 190 hits, aucun processeur/Torch, SHA des payloads inchangés.
- Cycle lookups hors table : 2 929 slots dans 88 BAM distincts ; valeurs natives conservées (dont sentinelles), aucun remplacement de frame inventé. Interprétation runtime à résoudre par profil, pas réparation implicite.
- Aucun GPU, nouveau guide, encodage, catalogue, QA, installation ou release.

## Contrat de partage

- Identités acquises : `analyze_playable_frame_dedup.identities`. Dimensions + transparence + indices row-major ; travail source = indices + RGB des indices utilisés. Chaque réutilisation de hash vérifie les octets.
- Centres signés, cycles/lookup, orientations/quadrants, calques et consommateurs restent par occurrence (`frame_map`, `cycles`, JSON source) ; aucune crop/rotation/miroir/tolérance/remap.
- Quatrième octet palette conservé intégralement. Identité RGB source ≠ alpha/runtime compatible.
- Travail Q3m final = profil/classes + successeurs/fits + alpha/guide + modèle/noyaux + échelle + clé source. Contrat inconnu → **pas de coût GPU final annoncé et pas d'adoption de résultat**.
- Une nouvelle sélection utilise l'union des clés de `animation_work`, jamais une somme par famille. Consommation GPU future : clé finale unique + cache commun verrouillé ; traiter les seules clés absentes compatibles. Runners Character/Monster acquis inchangés : leurs plans obligatoires, namespaces, verrou et validation cache assurent déjà ce contrat.
- Les changements de recette couleur, dont quatre partenaires, exigent leur contrat ; les résultats historiques ne deviennent pas automatiquement des hits.

## Artefacts / reprise

- `processing-plan.sqlite` : local ignoré Git ; frames/cycles complets, inputs compressés, source_work, relations animation↔BAM, intersections Character/Monster.
- `plan.json` : SHA/taille/source ; pointeur actif `sprite/index/q3m-source-work-plan.json`.
- `summary.json` : résultat CPU ; `animation-summary.csv` : compteurs par ID non-Character, **non additifs** pour les travaux partagés.
- `verification.json` : intégrité/relations/couverture et tests ciblés ; `known-monster-cache-resume.json` : reprise réelle sans GPU.
- Producteur d'analyse : `pipeline/scripts/analyze_sprite_frame_dedup.py`. Analyse source uniquement ; ne remplace ni le plan Character ni les profils Q3m Monster.

```powershell
$q3mPython=(Get-Content config/workspace-paths.local.json -Raw | ConvertFrom-Json).paths.chainner_python
# Lire les travaux uniques d'un lot, sans GPU et sans refaire l'analyse :
& $q3mPython -B pipeline/scripts/analyze_sprite_frame_dedup.py plan --animation-id 0x7F02 --animation-id 0x7F15
# Reconstruction seulement si le plan local manque ; destination neuve :
& $q3mPython -B pipeline/scripts/analyze_sprite_frame_dedup.py scan --output docs/measurements/<nouvelle-version>
```
