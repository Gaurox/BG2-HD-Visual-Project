# P4 BOX x4 — mesure 2026-10-01 v1

- Session autorisée : `tests faits. tu peux vérifier la session` ; Paris 22:36:36–22:39:33, 177.665602 s ; SHA256 CSV `6971BDAF36E8825D1B51E2D39C116CC20AE69BF20622D57B375AB20EB0F91334`.
- Installation vérifiée : `iee-sprite-p4-filters-20261001-v1`, BOX x4, `0x6110` ; viewport 2528×1339, FBO=0 ; mode=3, MIN=MAG=NEAREST, MAX_LEVEL=0. BOX effectif au shader ; aucun mipmap attendu.
- 175 fenêtres : 162 avec draw cible, 130 éligibles, 45 ignorées par critères existants du parseur. Scinder les phases contiguës ; ne pas confondre les deux passages au zoom habituel.

| Phase | Zoom x | Fenêtres | FPS | p95 fenêtre médian / max ms | CPU composition ms/frame | CPU masque ms/frame |
|---|---:|---:|---:|---:|---:|---:|
| initial_static | 2.6865 | 12 | 59.915 | 17.0345 / 18.9895 | 0.3209 | 0.0000 |
| maximum_first | 4.9472 | 20 | 59.993 | 17.1144 / 17.3552 | 0.2864 | 0.0000 |
| habitual_static | 2.4809 | 20 | 59.998 | 17.0770 / 17.3570 | 0.2800 | 0.0000 |
| minimum | 0.8229 | 26 | 59.969 | 16.9558 / 17.2638 | 0.2806 | 0.0000 |
| maximum_return | 4.9472 | 18 | 59.992 | 17.1510 / 17.6862 | 0.2939 | 0.0000 |
| habitual_return_movement_camera | 2.4809 | 34 | 59.990 | 17.1592 / 17.6954 | 0.3135 | 0.0803 |

- Totaux : 9 649/9 649 compositions et uploads, 448/448 masques ; cache pixels 7 208 hits (74.70 %) ; 6.686 GiB trafic RGBA base. Pics processus : WS 981.875 MiB, privé 1.808 GiB ; ni mémoire sprites seule, ni VRAM.
- Composition 3/3 : `CHFB1G12` + `WQNJ8G1` + `WQNFSG1` ; phases marche avec coordonnées monde variables et caméra mobile observées. Provenance composite=1 (153 fenêtres), masque=2 (9).
- Comparaison baseline Nearest `../palette-q3m-p4-measurement-20261001-v1/result.json` : p95 médian au zoom initial/min/max ≈ +0.267 % / −0.098 % / +0.046 %. Chaque statistique < +5 % ; observation scène/cadence, pas coût GPU isolé ni preuve globale de non-régression.
- Zoom habituel confirmé utilisateur : **maximum −7 crans**, x=2.480864, y=2.479630 ; répété exactement au retour. Différent du zoom habituel Nearest précédent (2.6865) : reprendre −7 aux essais suivants.
- Retour utilisateur exact : « ca semble plus joli en dézoom. j'ai compté 7 crans depuis le zoom max ». Préférence BOX en réduction ; aucun verdict explicite contours/halo/scintillement.
- Avertissement cible à 22:39:00.710 : `CHFB1G11 sequence=6 slot=-1`, rendu natif conservé. Slot négatif rejeté avant filtrage par garde existante dans HEAD ; warning limité à une occurrence/processus ⇒ nombre réel de replis inconnu. Effet visible non établi ; à surveiller en Nearest/Mipmaps.
- Autres warnings : eau `AR0900/WTLAKE` en repli natif et prologue RenderTexture EEex récupéré ; déjà présents au lancement 21:58 ; hors périmètre P4, aucune correction ici.
- Outliers conservés dans `result.json` : démarrage/chargement 1 461/836 ms ; transitions zoom ≈49–51 ms ; frame isolée 52.2784 ms dans palier initial stable. Aucun retrait rétrospectif de cette fenêtre stable.
- Limites : FPS globaux ≈60 ; p95 calculé par fenêtre, pas global ; CPU imbriqué composition/pixels/upload, masque séparé ; session plus longue/poses/cache différents ; frontière marche/panoramique non instrumentée.
- **P4 ouverte** : BOX mesuré + retour visuel positif ; Mipmaps et x2 restant à comparer avant décision datée échelle/filtre. P3 acceptée conservée ; aucune modification installation/release pendant la mesure.

Artefacts : `session.csv` copie exacte ; `summary.json` parseur commun ; `result.json` phases/totaux/limites ; `provenance.json` hashes/identités ; `runtime-excerpt.log` lancement/layers/marche/warnings ; `analyze.py` calcul exclusif (refuse d'écraser les sorties).
