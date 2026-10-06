# MFIE7314 — palette-v2 / trace ciblée — 2026-10-07

- Session observée : **2026-10-07 00:56:57**, `session-evidence.txt` ; DLL Monster stabilité-v1 `a9eeccad…16b99`, catalogue `86e6b4d5…534c928`.
- MFIE : métadonnées MFIEG12 prêtes, owner Monster::Render atteint ; `target Realize=1 /foreign=0 /captured=0`. **Toujours vanilla selon utilisateur**. La lecture252 de v1 ne suffit pas ; aucun nombre/type/couleurs live dans ce journal, cause exacte non déterminable depuis le log.
- MGCL7F0B /NSOL7F2C /NSHD7F36 : compositions HD G12 puis G1/(NSOL G11) confirmées ; **retests explicitement validés par utilisateur**. QA immutable additionnelle `../../../sprite/index/qa-decisions/monsters/2026-10-07-accepted-three-monster-stability-retests-q3m-v7-x2-nearest-v2.json` ; `accepted-asset-scope.csv`. Total **76/77 IDs acceptés sur leurs contrats testés**, MFIE seul ouvert ; QA73 précédente conservée.

## Delta candidat

- **7314/kind0 exclusivement** : si profil source252..255 nul ET dépendances de frame excluent tous ces indices de base/partenaires, comparer seulement252 couleurs quand CVidPalette annonce252 **ou256**. Le garde v1 refusait une palette annoncée256 à queue non nulle, bien que ces couleurs soient inutilisées. Cette possibilité est testée hôte ; la palette réelle du jeu reste à observer.
- Préfixe RGB utile exact /alpha0ou255 /autres tailles et types refusés. Les autres IDs/owners/modes gardent le contrat v1. Source fixed alpha et shader inchangés.
- **Trace `MFIE_PALETTE`**, au plus8 palettes distinctes : type/count/source lisible/acceptation/CRC/couleurs source/sortie globale/flags. Fonctionne aussi si le type est refusé. Si vanilla persiste, fournit enfin la raison palette exacte ; aucun dump de mémoire hors palette.
- Fork du **runtime v1 réellement installé**, delta deux fichiers ; Character V10 en stock exclu. `runtime.json` /`runtime-delta.patch` /sources locales épinglées.
- **DLL seule installée** : `f8bf6e0c…b6f6496`, avec sauvegarde parent ; catalogue, 1 037 feuilles, 77 CRE, INI, EXE et trois shaders identiques. **0 sprite recalculé**. `installation-verification.json` /`installed-verification.json` /reçu local `ingame-installation/active-test.json`.

## Tests / états

- `runtime-verification.json` : tests généraux natifs ; 1 040 liaisons Monster/56 383 cycles/1 240 346 cas, palettes252 et256 à queue altérée, préfixe utile altéré refusé ; pixels77 IDs/79 ressources/40 358 frames K6×3 formats ; régression Icewind1 140 ressources/94 338 cas.
- Dépendances MFIE : preuve antérieure `../q3m-monster-stability-x2-20261007-v1/short-palette-dependencies.json`, 13 ressources monde/5 886 frames, aucun index/partenaire≥252 ; SHA des mêmes assets revérifiés à l'installation.
- `analysis.json` sépare constats/logs, hypothèse de queue256 et candidat. **Aucune QA ingame MFIE-v2 déduite**, aucune acceptation complète de famille/release.
- Avertissement Character6110 CHFF4G11 présent dans le journal : autre famille, non modifiée par ce travail.

## Un seul retest

```lua
C:CreateCreature("QMON7314")
```

Apparition puis clic/changement d’action. Si toujours vanilla, lire la nouvelle session et ses lignes `MFIE_PALETTE` ; comparer le préfixe252 aux palettes natives avant toute extension supplémentaire du garde.

## Reprise / retour parent

- Scripts : `build_runtime.py`, `verify_runtime.py`, `prepare_install.py`, `install.ps1`, `finish.py`. Preuves finales immuables ; nouveau run pour un successeur.
- `restore.ps1` : jeu/InfinityLoader fermés, identité DLL/backup/fichiers conservés exigée ; revient uniquement à la DLL Monster-v1. Backup `work/before/InfinityEngine-Enhancer.dll`, mise à jour du pointeur installation ensuite nécessaire.
