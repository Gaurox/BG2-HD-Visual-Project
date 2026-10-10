# AR0517 / SPHINCT — branche WED lissée

- Déclencheur : capture utilisateur `E:/Steam/userdata/5536307/760/remote/257350/screenshots/20261010173621_1.jpg` ; crénelure du masque natif x1 agrandi x4. Arche correspondante : polygone3 WED KEY/BIF `data/AREA050B.bif`, SHA256 `34b74eeaa6127c872fed8a2e1ec13219a5785794cf1c7848f49865f905d82491`.
- Scope runtime : `AR0517`, `SPHINCT`, occurrence497,452, owner AreaAnimation, replacement AreaRegistry, clipping réussi, dither0, transfert binaire seulement. Autres cas : chemin précédent exact.
- Lissage : garde4/fondu16 x4 inward ; reconstruction bilinéaire du coverage A. RGB du transfert natif inchangé ; shader mode2 = alpha seul pour SPHINCT non additif, sans double atténuation RGB. Mode0/1 byte-identique au shader installé précédent ; BDFORCEW +6/WED16 préservé.
- Frames, centres, cycles, coordonnées ARE, fichiers WED/maps et INI inchangés. Aucune modification installation de pack ni release. QA AR0516 conservée ; AR0517 à retester, AR0518–AR0521 encore à vérifier.
- Artefacts : `animations/batches/ar0517-sphinct-wed-smooth-20261010-v1/{diagnosis,source,native-tests,gpu-tests,installation}.json`, `renderer-delta.patch`, `SPHINCT-AR0517-before-after.png`, `.work/runtime-src`, `.work/runtime-build`, `candidate/`.
- Tests : scope C++ (autres maps/occurrences/owners/dither/clipping refusés), 2 fixtures BDFORCEW couverture exacte, headers générés eau/version exacts ; shader GLSL réel, 49 frames SPHINCT sans pixel révélé/RGB altéré, modes0/1 exacts contre shader précédent.
- Preview : fixture rasterisée du polygone3 sur fond x4 AR0517 ; simulation GPU, pas capture ingame ni reproduction certifiée de la rasterisation native.
- Installation transactionnelle : DLL `ee85fdaba70fd99d0fbf114c6dcee46cf21ccc60a93f8e650a2dbb50abaf42b0` ; reçu/backup référencé par `installation.json`. Jeu/InfinityLoader fermés ; payloads AR0516–AR0521/AR0811/OH8100 vérifiés inchangés.
- Reproduction baseline DLL `748fe476d24ffa32007d33d34f5c6e506b56147570772ee40b810556ad317c56` : `build_renderer.py` → `preview.py` → `install.py`. Runs/preuves antérieurs immuables.

```lua
C:MoveToArea("AR0517")
C:Eval('JumpToPoint([497.542])')
```
