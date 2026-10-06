# Monster — stabilité runtime / QA partielle — 2026-10-07

- Production conservée : `../q3m-monster-full-x2-20261006-v2/current-generation.json`, Q3m K6/quatre partenaires/huit niveaux/x2/Nearest/sans SDF ; 62 modèles/77 IDs, 1 037 feuilles/1 040 liaisons. **0 sprite recalculé**.
- **Installé : DLL seule** `a9eeccad…16b99` ; parent `21a6f2e4…ea4b0e3`. Catalogue `86e6b4d5…534c928` inchangé ; 1 120 hashes conservés (catalogue, 1 037 feuilles, 77 CRE, INI, shaders, EXE). `installation-verification.json`, `installed-verification.json` ; reçu local `ingame-installation/active-test.json`.
- **QA utilisateur partielle : 73 IDs/60 modèles sur le runtime précédent** ; décision immuable `../../../sprite/index/qa-decisions/monsters/2026-10-07-accepted-partial-monster-73-q3m-v7-x2-nearest-v1.json`, inventaire scellé `accepted-asset-scope.csv`. 7314/7F0B/7F2C/7F36 exclus. Aucune validation ingame du runtime corrigé ni famille entière/release déduite.

## Diagnostic / changement

`analysis.json`, `last-session-sprite-evidence.txt` : dernière session 2026-10-07 00:28:19–00:41:15, catalogue331 IDs chargé. Horodatages du log conservés tels quels.

| Symptôme | Preuve | Correction |
|---|---|---|
| MFIE7314 vanilla | MFIEG12 chargé ; `target Realize=1 / captured=0`. BMP MFIEG3B252 entrées ; ancien garde exige256 | Lecture bornée au nombre déclaré ; autorisation exclusivement ID7314/kind0/252/préfixe RGB exact/alpha0ou255/queue profil nulle |
| Clic MGCL7F0B/NSOL7F2C/NSHD7F36 | G12 puis G1 chargés ; composition HD ultérieure confirmée. Avertissement global unique masque les appels manqués individuels | Owner3 : attendre métadonnées exactes lors du premier appel, délai5s existant ; éviter le retour vanilla dû au mode NonBlocking |
| Fins/changements de cycles, tout Monster | Avertissement MEAEG12/seq18/slot19 ; normalisation native déjà nécessaire pour MultiNew/Icewind | Owner3 : lire CVidCell+0x11C ; Loop/Clamp signés comme code natif, séquence hors plage→0 |

Les logs ne prouvent pas chaque flash au clic. Les causes de repli à froid/hors slot sont reproduites par le test hôte ; le retest ingame reste nécessaire. Ressource inconnue, cycle vide, lookup invalide, palette étrangère restent refusés.

Source successor = fork **du runtime installé Icewind**, delta `runtime-delta.patch` sur trois fichiers seulement ; les changements Character V10 en stock n’entrent pas dans cette DLL. `runtime.json` pin SHA DLL/sources/parent. Aucun shader/filtre/catalogue/CRE/asset modifié.

## Vérifications acquises

- `runtime-verification.json` : compilation DLL + tests généraux natifs ; oracle x64 natif231 cas (`BaldurReal.exe` épinglé).
- Monster : **1 040 liaisons /56 383 cycles /1 240 346 cas Loop/Clamp**, extrêmes int16 inclus ; zéro frame valide manquante/incorrecte. 1037 échecs de premier appel NonBlocking reproduits. Cycles vides212 /lookups invalides refusés504 /rejets Strict112342.
- Palette : 765 acceptations252, 60 761 contrôles de garde ; compte/type/RGB/alpha étrangers refusés. `analysis.json` : émulation native Realize écrit seulement252 couleurs. `short-palette-dependencies.json` : **13 ressources monde/5 886 frames**, aucun index de base/partenaire utilisé≥252 ; queue non écrite jamais consommée.
- Pixels natifs : **77 IDs /79 ressources /40 358 frames**, K6×3 formats palette ; 5 479 862 472 pixels décodés conformes aux oracles figés. Preuve exhaustive de production précédente réutilisée ; assets identiques.
- Régression Icewind : **1 140 ressources /7 401 cycles /94 338 cas**, zéro frame valide incorrecte/manquante ; autres modes/owners préservés.

## Retest utilisateur

Contrôler apparition HD, clic répété, marche/changement d’action, fin de cycle ; première action après lancement incluse.

```lua
C:CreateCreature("QMON7314")
```
```lua
C:CreateCreature("QMON7F0B")
```
```lua
C:CreateCreature("QMON7F2C")
```
```lua
C:CreateCreature("QMON7F36")
```

## Reprise / restauration

- Scripts de cette session : `analyze.py` → `build_runtime.py` → `verify_runtime.py` → `prepare_install.py` → `install.ps1` → `finish.py`. Preuves finales existantes immuables ; nouveau run pour un successeur.
- Vérification installation seule : comparer `current-generation.json`/`baseline.json` aux fichiers jeu ; aucune exécution du jeu nécessaire.
- Retour DLL parent uniquement : `./restore.ps1`, jeu/InfinityLoader fermés, SHA courant/backup et fichiers conservés exigés. Backup local `work/before/InfinityEngine-Enhancer.dll`. Mettre ensuite le pointeur installation du suivi à jour ; QA historique préservée.
