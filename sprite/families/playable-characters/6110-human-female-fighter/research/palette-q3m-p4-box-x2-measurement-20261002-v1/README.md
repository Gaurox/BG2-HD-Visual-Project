# P4 — décision x2 + BOX, 2026-10-02 v1

- Décision `decision.json` : **x2 + BOX sur 0x6110**, sans mipmaps ; master x4 conservé, x4 option qualité. Préférence utilisateur BOX nette en dézoom ; préférence x2 légère/incertaine. Aucun verdict visuel quantifié ni QA transférée à 0x6100/release.
- Session Paris 2026-10-02 00:06:59–00:08:33, 94.219414 s ; CSV SHA256 `188B421DDB07B4B0CF4F2870A16791BC6523E6AD0E5D4A3C2EE4952E2171518B`, 30465 octets. Viewport 2528×1339, FBO=0 ; scale=2, mode=3, MIN=MAG=NEAREST, MAX_LEVEL=0 ; BOX explicite shader, aucune chaîne mip.
- 92 fenêtres ; 82 draw cible, 68 éligibles parseur, 24 ignorées ; 67 fenêtres comparatives + première entrée monde (488.6283 ms) retenue séparément/raw. Provenance composite=75, masque=7.

| Phase | Zoom x | Fenêtres | FPS | p95 fenêtre médian / max ms | CPU composition ms/frame | CPU masque ms/frame |
|---|---:|---:|---:|---:|---:|---:|
| initial_after_world_entry | 2.6865 | 6 | 59.988 | 16.9366 / 17.0297 | 0.1657 | 0.0000 |
| maximum_first | 4.9472 | 14 | 60.002 | 16.8955 / 17.0159 | 0.1452 | 0.0000 |
| habitual_static | 2.4809 | 14 | 60.003 | 17.0196 / 17.1722 | 0.1483 | 0.0000 |
| minimum | 0.8229 | 16 | 59.779 | 16.8961 / 18.3068 | 0.1472 | 0.0000 |
| habitual_return_movement_camera | 2.4809 | 17 | 59.851 | 17.2317 / 24.3560 | 0.1632 | 0.0867 |

- Totaux : 4 892/4 892 compositions et uploads ; 327/327 masques ; cache 3 670 hits (75.02 %) ; 909413280 octets RGBA base. Pics processus WS=858.047 MiB, privé=1.714 GiB ; ni mémoire sprites seule ni VRAM.
- Habituel **maximum −7 crans** : zoom 2.480864/2.479630, exact aux phases statique/mouvement x2 et BOX x4 ; CPU composition 0.148325 vs 0.279973 ms/frame ; trafic base 11.082 vs 44.269 MB/s ; FPS 60.003 vs 59.998. Sessions indépendantes, durées/poses/cache différents ⇒ observation comparative, pas GPU isolé.
- À ce zoom, x2 est en magnification Nearest (empreinte ~0.806 texel/pixel) ; BOX agit au minimum (zoom ~0.823, empreinte ~2.43). Dimensions logiques/géométrie inchangées.
- Retours exacts utilisateur : « tests fait. au passage je confirme que box est bien meilleur visuellement que mimpas a mesure qu'on dézoome » ; « J'ai un léger sentiment de préférer x2 bien que ce soit difficile à dire. ». Le nouvel avis BOX complète l'ancien « je vois pas de difference ingame » sans réécrire le bilan Mipmaps x4.
- Repli natif à 00:08:16.720 : `CHFB1G11 sequence=6 slot=10`. Shard x2 et BAM source vérifiés : cycle 6 possède 10 slots (0–9), tables identiques ; rejet avant filtre par garde existante. Même type de repli observé x4 BOX/Mipmaps ; cause de la demande native hors borne/effet visible non établi, warning une fois/processus.
- Warnings eau AR0900 et detour EEex récupéré conservés ; hors P4. Outliers conservés : entrée 1 513/489 ms, transitions jusqu'à 120 ms, palier minimum 66.7617 ms ; p95 fenêtre mouvement max 24.356 ms. Aucune attribution causale au filtre.
- Limites : paliers 14–17 s ; FPS scène et p95 par fenêtre ; CPU imbriqué pixels/upload, masque séparé ; phase marche/panoramique non instrumentée ; historique mémoire/session différent ; Mipmaps essayé x4 seulement.
- Installation actuelle vérifiée `iee-sprite-p4-box-x2-20261001-v1`, catalogue x2 partagé 0x6100/0x6110 ; **BOX seulement 0x6110, 0x6100 Nearest**. Aucun fichier installé remplacé pendant la mesure. P3 acquise conservée ; P4 choix échelle/filtre consigné, release inchangée. P5 frontières Q8c vs Q3m à engager sur demande.

Artefacts : `session.csv` copie exacte ; `summary.json` parseur commun ; `result.json` mesures/limites/repli ; `decision.json` choix daté ; `provenance.json` identités/hashes ; `runtime-excerpt.log` lancement/layers/marche/warnings ; `analyze.py` sortie exclusive.
