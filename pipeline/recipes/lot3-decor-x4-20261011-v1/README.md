# Lot3 — production et installation, 2026-10-11

État courant : **lot3 accepté ingame le 2026-10-11**, 4assets/10cartes, 128frames runtime ; AM0902L SeedVR remplace ReboutCX. QA immuables sous `animations/index/qa-decisions/{AM0902L,AM1001A,AM1512PA,AM2008A}/2026-10-11-accepted-<ref>-lot3-final-v1.json` ; sélections courantes séparées. Release non sélectionnée. Rapport : `acceptance.json`, producteur `finalize.py`. Analyse native : `../lot3-decor-analysis-20261011-v1/README.md`.

| Asset | Recette finale | Structure / durée conservée |
|---|---|---|
| AM0902L | **SeedVR2 7B INT8/LAB x4** contextuel, seed20261011/pad32 ; 8poses assemblées x1, fill après montage, correction RGB des seules bandes partagées `clip((4-distance)/3,0,1)` ; Apollo8 sur montage complet ; inner2 sur silhouette complète, puis redécoupe native | 4cycles ×16phases, 64frames ; centres/dimensions/lookup natifs conservés ; 0,533333s/cycle ; aucun fondu interne |
| AM1001A | SeedVR2 7B INT8/LAB x4 ; Potrace alphamax0,8/opt0,2/SS8/band6, angles conservés ; inner4 ; Apollo8 | 7→14phases ; 0,466667s ; jet/éclaboussures conservés ; pas de LowerEdgeCover arbitraire |
| AM1512PA | Même spatial/contour sharp-corner/inner4 ; suppression des holds uniformes ×2 **avant** Apollo8, entrée7,5FPS →30FPS | 5poses /10slots natifs →20phases ; 0,666667s ; lookup natif `[0,0,1,1,2,2,3,3,4,4]` conservé au registre |
| AM2008A | ReboutCX x4 ; Apollo8 sur canvas aligné selon centres ; inner16 choisi parmi4/8/12/16 ; prémultiplication RGB unique | 15géométries →30phases ; 1s ; perte énergétique moyenne0,703%, perte du cœur max0,000053%, aucun petit composant lumineux effacé |

Doublons : aucun doublon RGBA stocké dans les sources ; 8poses complètes distinctes pour AM0902L. Les5 répétitions du lookup AM1512PA ne sont pas des frames BAM additionnelles : interpoler les5 poses à7,5FPS conserve les10/15s d'origine. `verify.py` concerne la production initiale ReboutCX ; preuve de la variante SeedVR dans `animations/batches/am0902l-seedvr7b-x4-trial-20261011-v1/manifest.json` (16montages distincts, durée inchangée). `finalize.py` authentifie les10 feuilles installées retenues.

## Sélection finale / retrait ReboutCX

- Pack QA exact : `animations/packs-par-zone/lot3-four-decors-accepted-20261011-v1/` ; combine les9 cartes initiales avec AR0902 SeedVR sans changer les octets ingame.
- Runs finaux : `animations/ressources/<REF>/runs/<ref>-lot3-four-decors-accepted-20261011-v1/` ; décisions et CSV `validé-x4` sur toutes les occurrences.
- AM0902L installation active : `animations/batches/am0902l-seedvr7b-x4-trial-20261011-v1/installation.json` ; production `../am0902l-seedvr7b-x4-trial-20261011-v1/README.md`.
- ReboutCX écarté pour AM0902L seulement ; aucun rejet d'AM2008A. **6 sorties autonomes supprimées, 396409166octets libérés**, liste/reçu dans `acceptance.json` ; contrôle automatique initial refusé, puis confirmation utilisateur « Oui, supprimer ces six dossiers » et suppression réalisée. Archives mixtes conservées pour les autres assets et reçus historiques immuables.
- Les chemins et commandes ci-dessous décrivent la production historique ; ne pas relancer sur ces sorties. Le registre/sélections/QA ci-dessus font autorité pour le résultat courant.

## Fichiers / commandes exécutées

- Spatial : `animations/batches/lot3-seedvr7b-lab-x4-20261011-v1` (AM1001A/AM1512PA, seed20261011, workflow `pipeline/comfyui/workflows/SeedVR-Image-BG2-Pipeline-7B.api.json`, x4 pad32) ; `animations/batches/lot3-reboutcx-x4-20261011-v1` (AM0902L/AM2008A, `config://chainner_python`, modèle `config://reboutcx_model`).
- Contextes/temporal/final : `animations/batches/lot3-decor-x4-20261011-v1/{context-spatial,context-base,base-*,temporal-*,recut-AM0902L,final-assets}`.
- `config://chainner_python context.py` → `python build.py prepare` → `python build.py recut` → `python build.py finish` → `python verify.py` → `python install.py`. Chemins scripts = ce répertoire ; ne pas relancer les producteurs sur ces sorties historiques.
- Preuves ciblées : même batch `{preparation,feather-sweep,verification,checks,baseline,installation}.json` ; `preview.png`, `CLUA.md`.
- Wrappers production : `animations/ressources/<REF>/runs/<ref-minuscule>-lot3-decor-x4-20261011-v1/manifest.json`, parents SHA256 et feuilles installables SHA256.
- Packs : `animations/packs-par-zone/lot3-decor-x4-20261011-v1-{assets,complete}` ; sauvegardes/récépissés transactionnels `backups/animations/area-tests`.

## Installation / tests utilisateur

- AM0902L : AR0902 (1171,811), contrôler montage4parties et raccords en mouvement.
- AM1001A : AR0905/AR1001/AR1006/AR1007/AR1009 (915,533), contrôler5 raccords bassin/carte. FLAME2S antérieurs byte-identiques.
- AM1512PA : AR1512 (208,487), contrôler angles/durée/occlusion. FIRE_4 antérieur byte-identique.
- AM2008A : AR1010/AR2008 (593,503), OH5120 (780,480). FIRE_4 antérieur byte-identique sur les2 premières. OH5120 `Fiery_Boil` **désactivée nativement** ; `C:Eval('AmbientActivate("Fiery_Boil",1)')` pour QA temporaire, ARE/quête non modifiés.
- Sauts : `C:MoveToArea("AR0902")` puis `C:Eval('JumpToPoint([1171.811])',0)` ; coordonnées logiques x1 même avec cartes x4. Toutes les commandes exactes dans le `CLUA.md` du batch.
- Installation10/10 vérifiée par hashes ; DLL/INI/ARE et ressources antérieures conservés. Pont d'occlusion natif existant, pas de masque WED cuit ni de modification runtime.
- Registre4lignes `validé-x4`, QA acquise par la demande utilisateur « on valide SeedVR. tu peux valider tout le lot 3 » du 2026-10-11. Installation initiale historique conservée ; sélection actuelle AM0902L SeedVR.
