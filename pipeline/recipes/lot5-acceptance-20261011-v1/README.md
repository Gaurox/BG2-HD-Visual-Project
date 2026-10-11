# Lot5 — acceptation finale, 2026-10-11

- Demande : « ok je valide tout le lot. maj le suivi et committe. » ; **3assets/4variantes de palette/20cartes/68occurrences**.
- AM3000E / AR3000 /5occurrences : ReboutCX PLT_MAGE + Apollo8, contour sigma2x4/canvas2px, géométrie native corrigée ;36phases/1,2s utilisées. Décision acquise `2026-10-11-accepted-am3000e-native-contour-v1` conservée.
- FLM2PUR / AR1008+OH4210 /13occurrences : ReboutCX + Apollo8 ; embarqué inner4 conservé, PLT_PURP soft2/étincelles protégées/canvas1px retenu ;32phases/1,066667s. Décision `2026-10-11-accepted-flm2pur-lot5-final-v1`.
- AMWRPGT1 /17cartes/50occurrences : SeedVR2 7B LAB + Apollo8 safe inner8/outer6/gauss3 existant byte-identique ;24phases/0,8s. Décision `2026-10-11-accepted-amwrpgt1-lot5-final-v1` ; QA antérieures AR3011/AR3016/AR3017 conservées.
- Sources de vérité : `animations/index/qa-decisions/<REF>/`, `animations/index/selections/<REF>.json`, CSV `validé-x4`, verrou `animations/index/area-pack-lock.json` ; chemins exacts dans `acceptance.json`.
- `finalize.py` exécuté : vérification20payloads installés/signatures verrou, lineage des3sélections, FPS/durées, émission des2nouvelles décisions immuables. Ne pas rejouer sur ces IDs.
- Aucune régénération/écriture jeu/suppression lors de l'acceptation ; aucun changement release.
