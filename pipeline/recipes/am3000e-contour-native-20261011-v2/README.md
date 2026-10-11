# AM3000E soft2 — correction fallback vanilla, 2026-10-11

- Symptôme utilisateur : AM3000E repassé vanilla après installation du fondu doux.
- Dernière session dans `config://bg2ee_game_root/InfinityEngine-Enhancer.log`,11/10/2026 16:20 : AR3000 chargé à16:20:30.604, pack v3 prêt9BAM/9timed/362frames/217,63MiB ; aucune composition AM3000E après ce chargement. Le fichier de pack est présent et chargé.
- Cause : v1 ajoute3px x1 de padding, dimensions+6. `engine/InfinityEngine-Enhancer/source-patchee/src/iee/area_animation_x4_registry.cpp:1064` exige dimensions exactes du dessin BAM ; `hooks.cpp:3782` laisse le rendu natif lorsque la résolution échoue. Compensation des centres seule insuffisante ; validateur offline du pack n'impose pas la géométrie BAM.
- Correction : recadrer12px x4 sur chaque bord de soft2 ; restaurer **dimensions/centres originaux de chaque frame**, mêmes cycles/aliases/FPS ; fondre uniquement la coupe canvas sur2px x4 en RGBA prémultiplié. Lissage doux sigma2 conservé ; pas de nouvelle interpolation/inférence, pas de changement moteur/BAM/ARE.
- Production : `build.py` → `animations/batches/am3000e-contour-native-20261011-v2/{final-assets,manifest.json}` ; installation `install.py` → pack `animations/packs-par-zone/am3000e-contour-native-20261011-v2/AR3000`, wrapper même ID sous AM3000E/runs.
- Reçu : batch `installation.json`, sauvegarde transactionnelle liée ; source remplacée `am3000e-contour-soft2-20261011-v1/AR3000` conservée comme historique du défaut.
- Vérifié :24/24géométries source natives directement contre `source.bam`,61rectangles/centres contre production sans padding, cycles48/36/20 et durées1,6/1,2/0,666667s conservés ; payload installé exact,8frères byte-identiques, signatures verrou conformes, DLL/INI/ARE inchangés. QA ingame non déduite ; nouveau CSV `à-valider`, release non sélectionnée.
- CLUA inchangées : AR3000,(396,1169)/(640,1521)/(899,1853)/(447,2006)/(194,1670), portrait0. Redémarrer le jeu pour tester le nouveau pack.

## QA acceptée

- Utilisateur : « ok. validé. on passe a FLM2PUR » ; dernière version native corrigée acceptée sur AR3000/5occurrences.
- `finalize.py` ; `acceptance.json` ; décision immuable `animations/index/qa-decisions/AM3000E/2026-10-11-accepted-am3000e-native-contour-v1.json` ; sélection `animations/index/selections/AM3000E.json` ; run `am3000e-contour-native-accepted-20261011-v1`.
- État courant CSV `validé-x4`, lineage vérifié, pack/installation/verrou byte-identiques ; aucune écriture jeu/release lors de l'acceptation. Lot5 intégralement accepté ensuite : `../lot5-acceptance-20261011-v1/acceptance.json` ; décision AM3000E acquise conservée.
