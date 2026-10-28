# Boule de feu — retest V2, 2026-10-28

- Source figée : `runtime.log` ; extraits numérotés : `evidence.txt` ; mesures/SHA : `summary.json`. Session 09:13–09:15, sort observé 09:14:54–55, horodatages du log.
- DLL active SHA `2043B799AC90B32585AD09CFBFE89E32EF4ED744F8F94D25474AE86C959E81DB` = candidat V2 installé.
- Retour utilisateur : « boule de feu testée ca a l'air ok ». Acceptation visuelle générale ; ne pas en déduire une validation séparée de chaque composant ou des 124 PRO.
- **SPSMPUFF confirmé x4/interpolé au dessin final** : `EFX_BOUND_PHASE` 0,2–11 ; phases impaires 3/5/7/9/11, backings distincts ; 20×20→80×80, 19×18→76×72, 17×17→68×68, 16×14→64×56. Cible 30/1 ; intervalles phases 3–11 : médiane 33,337 ms, plage 32,151–33,992 ms. Palette native capturée, opacité 127/255. Ceci prouve l'application runtime, pas l'identité visuelle de la transparence avec la référence.
- SPFIREPI/SPFLAMES : étapes `0x8` (texture x4 liée) puis `0x20` (masque natif lié). Pas de trace finale par phase pour ces deux ressources ; interpolation finale non mesurée séparément.
- **FIREBAT non validé x4/interpolé en vol** : registre résolu 69×65, timeline phase0, texture x4 liée au canevas69×78 (`0x8`), puis **repli natif par occlusion `0x40`**. Aucun `EFX_BOUND_PHASE FIREBAT` dans la session. Les lignes `Native occlusion phase0 ... replacement=effect-animation` sont émises AVANT la décision de repli ; elles ne prouvent pas le rendu final HD.
- Autres lectures FIREBAT : rejet géométrique24×16 (`0x80000000`/`0x2`). Étapes journalisées une fois par clé, pas compteurs exhaustifs de tous les dessins.
- Décodage étapes : `hooks.cpp`, constantes `kEffectDiagnostic*` ; repli après `native_effect_occlusion_fallback_required`, avant `original(...)` et `EFX_BOUND_PHASE`. Cause exacte du transfert de masque indisponible non précisée par la trace streaming ; conserver comme point à corriger/instrumenter.
- Lecture seule du jeu ; aucune image, DLL, PRO, installation ou release modifiée. 124 cas toujours ouverts selon leur état individuel.
