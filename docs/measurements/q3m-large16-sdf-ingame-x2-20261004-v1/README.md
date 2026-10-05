# Large16 : essai SDF x2 installé — 2026-10-04

- Base **sans SDF acceptée**, commit `9856d78d` ; QA immuable `sprite/index/qa-decisions/monster_large16/2026-10-04-accepted-full-available-large16-q3m-v7-x2-catmullrom-v1.json`. Cette QA ne valide pas le présent essai.
- Demande : contour sur trois variantes disponibles, puis installation. IDs A000 wyverne / A100 charognard rampant / A200 wyverne blanche ; owner11. **18 BAM monde / 1 688 frames** avec SDF V9 ; deux feuilles INV / quatre frames restent V7 auxiliaires, sans modification UI. A201/A202 sans source ; Quadrant hors périmètre.
- Recette Ankheg réutilisée : distance signée bornée/lissée σ2px x2, biais≤1px, noyau2/voisinage3, topologie foreground8/background4 ; pad6, quantification1/16px ; shader aire8×8/écran, CatmullRom prémultiplié16 taps. **1 508 masques uniques /180 réutilisations /0 inférence /0 encodage Q3m**. Cache par classe/forme/recette ; mêmes clés réutilisées à travers frames/variantes. Couleurs/palettes/source/centres/cycles/dépendances acquis.
- Chaque V9 privé de S/M restaure son V7 **octet pour octet**, dix-huit contrôles. Palette blanche native `MWYV_WS` inchangée. Monde : wyvernes zéro pixel ombre index1, charognard ombres noires127 ; compatible avec le runtime/shader V9. Les INV ont des ombres colorées et restent V7 ; aucune extension ombre couleur générale installée.
- Runtime : attente metadata spécifique `WaitForLarge16Metadata`, catalogue2 authentifié, IDs A000/A100/A200 **et owner11**, ≤5s ; worker existant, payloads paresseux, quarantaine/fallback inchangés. Appel commun capture/draw dans hooks ; Ankheg/Character/autres familles conservent leur contrat. Patch canonique dans les trois fichiers `src/iee/{creature_sprite_x2.h,creature_sprite_x2.cpp,hooks.cpp}`, `runtime-delta.patch`.
- **DLL construite depuis `16b01e52` + ce seul delta**, pas depuis HEAD contenant Character V10 en stock. `build.py` archive uniquement le moteur stable dans `.work/runtime-src`, adaption des chemins water au checkout original ; header water compilé exact au build stable. Trois shaders installés inchangés ; copies raw SHA dans `.work/runtime-shaders`, code compilé GPU identique après normalisation des fins de ligne Git. `runtime.json` épingle sources/DLL/shaders.
- Production `production.json` ; génération `current-generation.json` ; packs locaux `sprite/.work/q3m-large16-sdf-ingame-x2-20261004-v1/{isolated,combined}`. Catalogue **E23CCDC6…B522A43** : mêmes91 IDs/4 592 ressources/1 587 864 frames/**50 273 routes**, remplacement des seules18 feuilles monde. **4 574 feuilles inchangées**, dont INV, Character, Ogre, Flying, Ankheg.
- Vérification `verification.json` : suite native core ; V9 isolé/combiné ×6palettes×3formats, toutes1 688frames/cycles, uploadSDF et centres/composition Python/C++ ; Ankheg516frames et compositions historiques inchangés. `gpu-verification.json` : trois shaders compilés, **24 vues** (deux poses/ID × zoom0,75/1/1,5/3), raster comparé au CPU, fpSprite=fpDraw, fpSELECT exercé.
- `cold-lookup.log` / `cold_probe.cpp` / `cold-cases.h` : **18/18 Large16 premiers accès HD, zéro miss**, six premiers accès Ankheg conservés ; attente max96,0796ms sur cette machine. Slots valides tirés de l'oracle natif : une sentinelle n'est pas une frame à résoudre. Mesure hôte, pas garantie de latence ingame.
- Installation `installation-verification.json`, reçu actif `ingame-installation/active-test.json` : jeu/InfinityLoader fermés, sauvegarde DLL+catalogue dans `work/before`, seules DLL/catalogue/18feuilles nouvelles publiés ; **119 fichiers acquis SHA inchangés** : INI/exe/trois shaders/81packsUI/12Ankheg/CREblanc/20feuillesV7. Décisions QA immuables. Character SDF non installé ; aucun release/payload/staging/TP2/content/manifeste modifié.
- **QA de cet essai en attente utilisateur** ; aucun commit du candidat SDF déduit de la demande de committer d'abord le lot V7. Preuves scellées : ne pas rejouer production/build/verify/seal dans ce run. Nouvel essai = nouveau run.

```lua
C:CreateCreature("WYVBAB01")
C:CreateCreature("CARCRA01")
C:CreateCreature("QMWYVW01")
```

Observer apparition, marche, attaques, rotation, mort ; mêmes CLUA que le V7. Le CRE blanc ajouté au lot précédent reste identique.

Retour au **V7 sans contour validé**, jeu/InfinityLoader fermés :

```powershell
& ./docs/measurements/q3m-large16-sdf-ingame-x2-20261004-v1/restore.ps1
```

Authentifie DLL/catalogue actifs et backups +119fichiers, restaure les deux fichiers parent ; garde le CRE blanc et les feuilles non référencées. Le restore du lot V7 initial retire ensuite toute Large16, uniquement après celui-ci.

## Décision finale — SDF rejeté et retiré

- Utilisateur : « retire SDF c'est vraiment pas acceptable, ca fait beaucoup trop lisse. valide la famille sans SDF ». V9 SDF trop lisse ; QA `sprite/index/qa-decisions/monster_large16/2026-10-04-rejected-full-large16-q3m-v9-sdf-x2-catmullrom-v1.json`. **Actif : V7 x2 sans SDF validé**, QA antérieure inchangée/reconfirmée.
- `restore.ps1` exécuté ; `restoration-verification.json` : DLL+catalogue V7 parent exacts, vingt feuilles V7 et119fichiers inchangés. CREblanc, Ankheg SDF stable et Character en stock conservés. Les mentions installé/en attente plus haut sont historiques.
- Delta attente Large16 retiré des sources courantes ; `runtime-delta.patch` et build local conservent cet essai. Aucun fichier preuve antérieur réécrit, aucun commit/release demandé dans cette restauration.
