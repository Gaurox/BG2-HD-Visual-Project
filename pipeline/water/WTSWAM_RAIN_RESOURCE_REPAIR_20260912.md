# WTSWAM — ressource pluie manquante, reprise v4

État : `validated-installed`, décision utilisateur du 2026-09-12, AR1607/AR1800 à q0.70.
QA courante : `manifests/wtswam-ar1607-ar1800-validated-20260912-v1.json`.

## Diagnostic révisé

- QA utilisateur v3 rejetée : mosaïque au déclenchement pluie ; AR1800 persistante.
- Le diagnostic v3 « fpTone cause de la pluie » était insuffisant : aucun draw fpTone route2 dans
  la session14:43, alors que fpSEAM AR1607 est positif à14:43:16 (`q0.7`, timeline active).
- KEY : `WTSWAMR`, pluie, distinct de `WTSWAM` ; `data/ARMisc.bif`,6 entrées palette5120octets,
  SHA256 `F127DCE6A09F2F26C61E169533E9F1FEB5A349D441F6F44EFF01CE87F9F76403`.
  Le pilote demandait36frames par WED mais seule la ressource sèche avait été traitée.
- Preuve native BG2EE2.7.3 : RVA0x2A44C7 sélectionne l'état ; états2/4 lisent l'élément de
  `CInfTileSet::pResTiles` puis sa ressource alternative+0x20 à0x2A44DF..0x2A44ED ;
  autres états suivent l'élément primaire. `CVidTile` reçoit ce pointeur à0x2A4505.
- Le hook xN refuse les entrées palette, et la reconnaissance route2 précédente ne parcourait
  que les ressources sèches. Double omission : production pluie et identité runtime pluie.
- Log source : `build/wtswam-rain-20260912-v4/evidence/InfinityEngine-Enhancer.log`, SHA256
  `63F7D99119A84615279A5646AC4452F403696A43ED79B0DB98C0F4DE06C8E4FE`.

## Correctif isolé

| Usage AR1607/AR1800 | TIS | PVRZ | Production |
|---|---|---|---|
| Sec | WSWPIL | WWPIL00 | Copie exacte de WTSWAM36/WSWAM00 déjà installés |
| Pluie | WSWPILR | WWPILR00 | WTSWAMR stock → SeedVR2 x4 none, contexte3×3 → Apollo8 36phases15Hz |

- WED : seuls les8octets du resref overlay1 sont remplacés ;5octets diffèrent par WED.
  Timeline36, vitesse1, géométrie, ombres/alpha des bases inchangés.
- Aucune modification des fichiers partagés WTSWAM/WTSWAMR ni des autres utilisateurs.
- Registre19 entrées :15 antérieures identiques,2 identités sèches renommées,2 pluie nouvelles.
  Le nom d'overlay WED reste sec ; l'identité TIS pluie est distincte et hash-validée.
- Runtime : lecture des deux ressources possédées par le wrapper et des TIS du tileset ; aucune
  déduction de nom par suffixe dans le matcher. Validation TIS/page/count/WED/GL conservée.
- Diagnostics : budgets séparés sec/pluie ; `WATER_ROUTE2 draw ... weather=true ...` pour pluie.
- q0.70 et renderer30FPS pour les4 identités ; alpha100 AR1607 /128 AR1800 conservés.
- Sources : `pipeline/scripts/build_wtswam_rain_repair.py --output <nouveau-run> [--run]`.
  Le producteur exige l'état parent exact, ne se relance pas sur v4 installée.
- Run : `maps/technical-overlays/WTSWAMR/runs/seedvr-none-apollo36-isolated-rain-20260912-v4`.
  SeedVR raccords moyens x/y1.3117/1.1337 ; Apollo36frames. Cela ne vaut pas QA ingame.

## Installation / reprise

- Sélection/reçus : `manifests/wtswam-rain-installed-20260912-v4.json`.
- Build neuf : `build/iee-wtswam-rain-20260912-v4`, Release x64, `BUILD_TESTING=OFF`.
- Tests préparés (`test_water_rain_routing.py`, groupe moteur), aucun exécuté.
- QA : redémarrer via InfinityLoader ; AR1607 et AR1800, sec→pluie→sec, raccords en pause/mouvement,
  transparence/art local, absence de pop/crash. Relever pages WWPIL00/WWPILR00 et
  `weather=true`, `q=0.7`, `temporal=true`. Procédure de reprise, non exécutée par l'agent.
- État installé validé explicitement par l'utilisateur ; aucune intégration release demandée.
