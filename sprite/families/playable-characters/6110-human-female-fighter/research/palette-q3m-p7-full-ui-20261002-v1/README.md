# P7 — lot UI normal 0x6110, Q3m K6 x2

- Demande 2026-10-02 : cuir validé, procédé accepté ; traiter tous les équipements de la figurine. **Lot accepté par l’utilisateur : « validé. committe ».** Décision immuable : `sprite/index/qa-decisions/paperdolls/2026-10-02-accepted-full-ui-6110-q3m-k6-x2-nearest-v1.json` ; `acceptance.json` lie la production figée à cette décision.
- Périmètre : **81 BAM / 163 frames** = 4 corps CHFF1–4INV + 77 équipements (armes INV, main gauche OIN, boucliers, casques). Exclusions : WPNH3INV/H4INV sans ITM, H6 attaque de créature, WMOIN orphelin. Corps d'autres animations et icônes d'objets exclus.
- Source : chaque BAM vanilla comparé aux octets canoniques KEY courants ; SHA, BIF, locator et tables dans `production.json`. Cycles `[0,0,1,1]` conservés ; CHFF4 frame2 non référencée conservée. Aucun BAM natif remplacé.
- Production : P12 ReboutCX float x4 → BOX x2 → Q3m K6 (REF/DEFAULT/LATIN1–4), sans tramage/frontières ; 159 nouvelles frames logiques → 138 clés pixels, dont 3 spéciales, 810 cibles neurales ; ≈14,4 s. Plans CHFF1/2 acquis réutilisés, paquets byte-identiques.
- Plans autonomes sous `planes/`, paquets V6 bruts sous `work/packs/` ; **2 119 276 octets au total**. Header `paperdoll_q3m_scope.h` dérivé des 81 identités source/géométries exactes ; copie runtime sous `src/iee/`. Nouveau run frère pour reproduction, ne pas réécrire ce lot après décision finale.
- Contrôles : 0 fuite, 0 spécial modifié ; 2 934 décodages indépendants RGBA Python et BGRA C++ (18 palettes×163 frames), rejets source/identité/géométrie/cycles/troncatures ; `decoder-verification.json`. `iee_tests` PASS, cwd moteur ; aucun profilage exhaustif ingame déduit.
- Runtime : registre par resref ; palette réalisée capturée par cellule/slot, recontrôlée au dessin ; centres/dimensions natifs, clip128×160/placement/source/Bitmap6 gardés ; divergence → natif. UI Nearest, sans mipmaps. Pool **32 textures** LRU avec flush natif avant upload/éviction ; palettes et plans indépendants. Ressources WPN partagées : routage par resref, pas par owner d'animation ; aucun autre corps ajouté.
- Installation : 79 nouveaux paquets + DLL/INI ; deux paquets acceptés CHFF1/2 conservés, catalogue/shaders monde inchangés. `installer-verification.json` : install/Verify/Restore fixture, restauration exacte, refus dérives pack/INI/baseline/paquet préservé et override UI/équipement. `installation-verification.json` copie figée du reçu actif.
- Runtime : `pipeline/runtime/manifests/iee-sprite-p7-full-ui-q3m-20261002-v1.json` ; build `build/sprite-p7-full-ui-q3m-20261002-v1/cmake`. Historique code du pilote cuir préservé sous `baseline-source/`.
- Reçu/backups : `ingame-installation/active-test.json` ; **Restore revient exactement au pilote cuir accepté** et retire les 79 seuls nouveaux paquets. Ne pas restaurer via les installateurs antérieurs tant que ce lot est installé.
- QA acquise : **lot normal 81 ressources accepté**. Session : 81 chargements, 7 ressources / 14 dessins HD `bound=true`, CRC indépendants conformes ; `runtime-evidence-qa-20261002-v1.txt`. Pas de couverture exhaustive ressource/palette déduite. Production/QA/installation restent séparées ; aucune release modifiée.

## Essai utile

Lancer normalement avec InfinityLoader ; observer l'inventaire de la guerrière avec mailles/plates, une arme + bouclier + casque, puis deux armes. Changer d'objet, de couleur et retirer/remettre l'armure ; contrôler raccords taille, placement, ordre des couches et contours. La sélection exacte des objets appartient à l'utilisateur, pas de matrice universelle obligatoire.

Journal : `P7_Q3M_PACK ready: <resref>` confirme chargement, **`P7_Q3M_DRAW resref=<resref> … bound=true` confirme dessin HD** ; palettes/pixels CRC vérifiables aux plans. Chargement du lot ≠ preuve de dessin HD des 81 ressources. Fermer jeu/InfinityLoader après l'essai et signaler le résultat.

```powershell
./install.ps1 -Mode Verify
./install.ps1 -Mode Restore # jeu et InfinityLoader fermés ; baseline cuir exacte
```
