# P4 — zoom réel et baseline x4, dernière session du 2026-10-01

- Session : 21:43:14–21:45:11 Europe/Paris, 116,127 s / 115 fenêtres. Dernier CSV explicitement autorisé par l'utilisateur ; session précédente non utilisée.
- Source exacte : `session.csv`, SHA256 dans `provenance.json` ; original sous `../palette-q3m-p4-probe-20261001-v1/captures/`, intact.
- Runtime : `iee-sprite-p4-probe-20261001-v1` ; catalogue x4 commun `0x6100/0x6110`, Nearest ; INI/catalogue inchangés depuis installation sonde. `runtime-excerpt.log` = preuves de démarrage.
- Viewport : **2528×1339**, FBO 0, constant pendant tous les dessins HD observés. Zoom = pixels écran / pixel logique ; légers écarts X/Y dus aux dimensions monde entières.

| Palier | Zoom X / Y | Durée stable | FPS | p95 médian des fenêtres | CPU composite 0x6110 / frame | CPU upload/setup inclus |
|---|---:|---:|---:|---:|---:|---:|
| Initial, habituel selon protocole | 2,6865 / 2,6834 | 18,16 s | 59,97 | 16,99 ms | 0,321 ms | 0,184 ms |
| Minimum tenu | 0,8229 / 0,8225 | 18,11 s | 59,68 | 16,97 ms | 0,305 ms | 0,185 ms |
| Maximum tenu | 4,9472 / 4,9410 | 18,16 s | 59,92 | 17,11 ms | 0,317 ms | 0,182 ms |

- Trois paliers Nearest de 18 fenêtres complètes ; menus/chargement, transitions, fenêtres partielles et échantillons LINEAR séparés dans `summary.json` / `result.json`. p95 maximal de ces fenêtres : 17,51 ms ; **aucun p95 global reconstitué**.
- `0x6110` : 6 435 compositions et 6 435 uploads, tous réussis ; cache pixels 4 728 hits / 6 435 appels (73,47 %). Trafic upload base ≈44,2–44,4 Mo/s sur les paliers, malgré les hits CPU ; textures transitoires.
- Processus entier : pic working set **941,08 Mio**, private commit **1,774 Gio**. Pas une mesure RAM sprites seuls ou VRAM résidente. CPU upload = soumission/setup pilote, pas temps GPU ; compteurs imbriqués, ne pas additionner. Passe d'occultation aval et résolution metadata à froid hors timer composite.
- Pics hors paliers : **772,58 ms** lors de l'entrée dans le monde (t=6,30 s), **82,86 ms** pendant dézoomage (t=26,48 s). Causes non attribuées.
- Retour après maximum : **2,3171 / 2,3166**, différent du zoom initial ; fin du parcours avec autres changements de zoom/caméra. Marche non certifiable par cette sonde sans état d'animation/position.
- LINEAR observé sur certains dessins : branche masquée du pont d'occultation déjà activé dans l'INI avant sonde. `native_occlusion_bridge.cpp:457` choisit LINEAR hors CatmullRom ; `creature_sprite_filter.cpp:121` transfère cette provenance. La sonde observe le premier dessin HD de chaque frame, pas exclusivement `0x6110`. Aucun changement de filtre utilisateur déduit.

## Conséquence P4

- Prérequis zoom réel acquis pour cette taille de fenêtre : plage observée ≈0,823–4,95 ; deux zooms joués identifiés ≈2,69 et ≈2,32.
- À 2,6865 : x4 réduit ≈1,49 texel/pixel écran ; x2 agrandi ≈1,34 pixel écran/texel. Au minimum : x4 ≈4,86 texels/pixel ; au maximum : x4 agrandi ≈1,24 pixel/texel.
- Préparer l'A/B avec exactement le même zoom/viewport/scène, conserver le pont d'occultation dans le contrat et séparer sa branche masquée. Ne pas changer ses règles comme effet secondaire d'un nouveau filtre.
- **Choix x2/x4 + filtre encore ouvert** : cette session mesure uniquement la baseline x4 actuelle ; aucun gain visuel, nouveau filtre, QA ou release déduit.
- Aucun fichier installé modifié pendant l'analyse. Sources/captures/proofs de préparation préservés.
