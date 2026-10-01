# P4 Mipmaps x4 — mesure 2026-10-01 v1

- Session désignée par utilisateur : `test fait. controle la derniere session` ; Paris 23:34:56–23:36:10, 73.771247 s ; SHA256 CSV `EECBE09C314FBEE1746D667B3BB005482694FD05A411777C8441D95125027A9F`.
- Runtime installé vérifié : `iee-sprite-p4-filters-20261001-v1` ; x4, `0x6110`, viewport 2528×1339, FBO=0 ; mode=4, MIN=9987 (LINEAR_MIPMAP_LINEAR), MAG=9728 (NEAREST), MAX_LEVEL=8 ⇒ **9 niveaux effectifs**. 65 fenêtres avec draw cible, provenance composite=61 / masque=4.
- 72 fenêtres : 53 éligibles au parseur, 19 ignorées ; `summary.json` conserve les groupes bruts. Comparaisons ci-dessous : phases contiguës, 51 fenêtres au total avec le zoom intermédiaire et la marche ; première fenêtre monde/dernière fenêtre avant sortie conservées séparément.

| Palier | Zoom x | Durée Mips s | FPS Mips | p95 médian fenêtres ms | CPU composition Mips / BOX ms/frame | CPU upload Mips / BOX ms/frame |
|---|---:|---:|---:|---:|---:|---:|
| maximum_after_initial_world_entry | 4.9472 | 12.07 | 59.99 | 16.9828 | 2.088 / 0.286 | 1.951 / 0.178 |
| habitual_static | 2.4809 | 8.04 | 59.79 | 16.9263 | 4.258 / 0.280 | 4.124 / 0.174 |
| minimum | 0.8229 | 11.08 | 59.86 | 16.8611 | 1.769 / 0.281 | 1.664 / 0.173 |

- Même zoom exact BOX/Mips aux trois paliers statiques ; p95 médian voisin, cadence ≈60. Au zoom habituel : composition **4.258 vs 0.280 ms/frame**, upload **4.124 vs 0.174 ms/frame** ; augmentation CPU nette mesurée, sans attribution à une opération/GPU isolée.
- Coût upload Mips inclut prémultiplication, génération de chaîne et soumission pilote ; pixels/upload imbriqués dans composition. Ne pas les additionner. Masque mesuré séparément.
- Marche/caméra : retour à **2.672304 / 2.672655**, différent du zoom statique habituel **2.480864 / 2.479630** (maximum −7 crans) et du retour BOX. 18.145 s hors sortie partielle ; FPS 59.74, p95 médian 17.1322 ms / max 34.8330 ms ; CPU composition 2.174, masque 0.510 ms/frame. Pas de comparaison contrôlée de mouvement avec BOX.
- Totaux : **3 802/3 802 compositions et uploads, 248/248 masques** ; 2 817 hits pixels (74.09 %) ; trafic RGBA base 2.640 GiB (hors octets mips générés GPU). Pics processus WS 1125.922 MiB / privé 1.764 GiB ; ni mémoire sprites seule, ni VRAM.
- Layers 3/3 : `CHFB1G12`, `WQNJ8G1`, `WQNFSG1` ; marche `CHFB1G1/CHFB1G11`, coordonnées monde variables observées.
- Repli natif à 23:35:53.312 : `CHFB1G11 sequence=5 slot=10`. Shard installé SHA256 `18A66DCB6984F6B4A418607E94ABDBA28D33D4EB95A425E0108936EC420154F4` vérifié ; cycle 5 = 10 slots valides **0–9**. La demande 10 est hors cycle, rejetée avant filtrage par garde existante ; protection fail-closed. Warning une fois/processus ⇒ total replis non mesuré. Même cycle longueur 10 dans BAM source canonique SHA256 `F9C476D8828BCFB7151FAC470A91891E40728C49628DEE0989DC39376A73CE70` ; pas une frame manquante introduite par génération mipmaps.
- Autres warnings : eau `AR0900/WTLAKE` en repli natif, prologue RenderTexture EEex récupéré ; déjà observés avec BOX, hors périmètre.
- Outliers conservés : chargement 1 480/698 ms ; transitions zoom 59–85 ms ; palier habituel statique frame max **41.2176 ms** ; marche frame max **49.3138 ms**, p95 fenêtre **34.8330 ms**. La première fenêtre monde (19 vues) et la sortie partielle (16/59 vues) ne sont pas utilisées dans les comparaisons statiques/marche, mais restent dans CSV, groupes bruts et `result.json`.
- Limites : paliers 8–12 s, plus courts que BOX et que les 20 s demandées ; contexte cache/poses différent ; zoom marche différent ; FPS global autour de 60 ne mesure pas un coût GPU isolé. Aucun retrait des pics dans les phases stables.
- Retour utilisateur exact : **« je vois pas de difference ingame »** (Mipmaps vs BOX). Aucun verdict explicite d'absence de halos/scintillement déduit.
- Recommandation provisoire : **BOX x4**, coût CPU inférieur sans gain Mips perçu. **P4 reste ouverte** : comparaison x2 et décision finale utilisateur ; P3 acceptée conservée. Mipmaps reste installé, aucune bascule ni modification release pendant cette mesure.

Artefacts : `session.csv` copie exacte ; `summary.json` parseur commun ; `result.json` phases/comparaisons/limites + contrôle cycle natif ; `provenance.json` hashes ; `runtime-excerpt.log` lancement/layers/marche/warnings ; `analyze.py` calcul exclusif, refuse tout écrasement historique.
