# Monster_layered complet — Q3m x2 palette améliorée, sans SDF

- État : **produit/installé ; QA ingame en attente**, pas de release. Sept IDs/modèles2000/2100/2200/2300/8000/8100/8200 ; toutes frames/cycles/centres, corps +chaque arme.
- Source utile : **65 BAM/6 422frames/5 757identités**. Cache276 ; nouveaux5 479encodages +deux spéciaux sans inférence ; cibles neuves32871. Aucun modèle partagé ; UVOLMG2/MG2E doublon de pixels, deux bindings conservés.
- `MSIRG2BE` : orphelin90frames, dont30 hauteur0. Native EquipWeapon=`prefix+weapon[0]+G1/G2/G1E/G2E` →MSIRBG2E ; pas MSIRG2BE. Source inchangée ; aucun pixel/geometrie inventé. `native-routes.json`, `weapon-bindings.asm`.
- Correction de l'association dans la proposition : fabrique330DD4/type2000→ctor3119A0/vtable5AA840/render32F3B0 ; type8000→ctor311300/vtable5AA650/render32EE90, déjà couvert. Nouveau hook owner8/composite +tableaux10. `factory-native.asm`, `runtime-delta.patch` ; préfixe32octets pinné.
- DLL : base installée16b01e52 +acquis V9 kind1 +seul delta hook. CPP lecteur410acf6a…569b0 identique au parent ; aucun Character V10 en stock activé, shaders/INI inchangés.
- Catalogue : parent147IDs/6 688ressources/1 686 325frames ; actif154IDs/6753ressources/1692747frames/55383routes. Quatre Volo SHA identiques au pilote local acquis, absent du parent installé ; **65feuilles ajoutées**, anciens composants/routes préservés.
- Tests : toutes6 422frames feuilles/cache/profils/référents/géométrie/cycles sans SDF ; native K6×3encodages, isolé/combiné ; 8364compositions/12728couches, zéro couche absente ; Ankheg V9 hérité ; mêmes compositions relues au chemin installé. Auxiliaires non cyclés : [], 0frames cache vérifiées.
- Installation : 65feuilles +catalogue +DLL +Volo QLYR2100 dérivé ENDVOLO sans scripts/dialogue. **2252fichiers acquis SHA préservés**, sauvegardes `work/before`. Jeu/InfinityLoader fermés ; sources BAM/INI et CRE stock conservés. `install.ps1`, `restore.ps1`.
- Autorités distinctes : `current-generation.json`, `production.json`, `verification.json`, `runtime.json`, `ingame-installation/active-test.json`, `installation-verification.json`, `installed-native-verification.json`. Validation utilisateur non déduite. Comparatif `comparison.png`, tests `CLUA.txt`, consommateurs stock `creatures.json`.

```powershell
& 'C:/Users/Adrien/AppData/Roaming/chaiNNer/python/python/python.exe' docs/measurements/q3m-monster-layered-full-x2-20261004-v1/verify.py
```
