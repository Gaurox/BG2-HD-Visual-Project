# Q3m K6 x4 complet — humaine guerriere 0x6110

- Etat final hors jeu : `verification.json` ; installation active : `installation-verification.json`.
- 656 BAM / 178 360 frames : corps/armures 92 (CHFB1/2/3, CHFF4), casques 252,
  boucliers 60, armes 252 ; 65 familles avec sources. WINGS01B/YW sans BAM natif : absence conservee.
- **Tous les pixels regeneres en Q3m K6 x4** ; aucun I historique RANGES12/OKLab reutilise.
  Palettes de fit P1 : REF, DEFAULT, LATIN1..4, poids egaux ; ReboutCX fixed86 FP16 q32,
  sortie x4 directe, guide xbr4X ; F=0..7 en octets, compression XPRESS/raw par plan.
  B et tramage desactives. F absent si nul ; geometrie/centres x1, sources, cycles preserves.
- 144 echantillons P1 x4 : I/F/dep_mask identiques octet pour octet ; infererences P1
  comparees aux sorties gelees. `recipe.json`, `coverage.json`, `preservation.json` = provenance.
- Catalogue V2 x4 isole : 1 animation, 656 composants V6 / 656 shards. Autres animations = BAM
  natif pendant le test. Catalogue x2 complet et INI precedents sauvegardes avant installation.
- DLL adaptee : limite cumulee I+F V6 x4 = 1 Gio ; I seul/fichier <=512 Mio ; x2 <=256 Mio ;
  plan par frame <=128 Mio ; caches I/F et metadonnees <=128 Mio chacun. Capacite x4 explicite
  dans `runtime.json` et verifiee par l'installateur avant changement du catalogue.
- Tests Python cibles : 45 ; CTest : 2 suites, 10 fixtures valides / 37 rejetees, dont shard
  x4 I+F >512 Mio et rejet I seul >512 Mio. Decodeur natif : toutes les frames sur 18 palettes,
  plus parcours 656 BAM puis retour au premier, composition des quatre couches V6 reelles.
  `verify_native.py` utilise une LUT scalaire independante de l'encodeur ; SHA256 des pixels.
- Nearest ; profils fpSprite/fpSELECT x1 desactives ; trace palette desactivee.
- Alpha oracle synthetique ; tests CPU, aucune validation visuelle/effets vivants/GL/FPS deduite.
  Regression REF P1 x4 +11,59 % conservee ; controle visuel manuel a faire.
- `candidate/`, `work/`, `captures/`, shards et transactions = locaux ignores ; preuves finales
  versionnees. Vue native courte `build/p3-6110-v5-x4-native` : liens physiques, memes octets.
- Runs historiques v1..v4 intacts ; aucun payload/staging/release ni autre famille modifie.

Depuis `G:\AI\BG2_Upscale`, jeu et InfinityLoader fermes :

```powershell
$q3mRun = 'sprite/families/playable-characters/6110-human-female-fighter/research/palette-q3m-p3-20261001-v5-full-x4-6110'
# Installer/reinstaller le pack et sa DLL ; ne lance pas le jeu.
& pipeline/scripts/Start-Palette-Q3m-P3.ps1 -Run $q3mRun -Scale 4 -Mode Q3m
# Controle en lecture seule de la DLL, du catalogue et des 656 shards actifs.
& pipeline/scripts/Install-IEE-Runtime-Test.ps1 -Mode Verify -Manifest "$q3mRun/runtime.json" -StateRoot "$q3mRun/ingame-runtime"
& pipeline/scripts/Install-CreatureSprite-XN-Catalog-Test.ps1 -JobFile "$q3mRun/x4-q3m-k6.job.json" -RuntimeManifest "$q3mRun/runtime.json" -CreatureSpriteFilter Nearest -VerifyOnly
# Retour au catalogue x2, a son INI et a la DLL presents avant le test.
& pipeline/scripts/Start-Palette-Q3m-P3.ps1 -Run $q3mRun -Scale 4 -Mode Restore
```

Generation reproduisible (nouveau repertoire uniquement) :

```powershell
$q3mPython = (Get-Content config/workspace-paths.local.json -Raw | ConvertFrom-Json).paths.chainner_python
& $q3mPython -B pipeline/scripts/palette_complete.py --scale 4 --workers 8 --output '<nouveau-run>' --runtime "$q3mRun/runtime.json"
```

Controle manuel : quatre armures, casques/boucliers/armes, directions/repos/marche/attaque,
changement de couleurs, effets pulses, ombres/transparence. Validation ingame et QA restent ouvertes.
