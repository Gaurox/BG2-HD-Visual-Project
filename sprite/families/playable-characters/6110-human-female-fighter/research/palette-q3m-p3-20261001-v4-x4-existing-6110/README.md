# Test x4 existant — humaine guerriere 0x6110

- Installation seule, sans inference/production globale/release. Etat : `installation-verification.json`.
- 656 BAM / 178 360 frames x4 : armures 92, casques 252, boucliers 60, armes 252.
- Base immutable : `family-runs/reboutcx-x4-visual-catalog-v2` (ancienne methode RANGES12/OKLab).
- 144 images remplacees par les I/F/dep_mask Q3m K6 x4 P1 existants ; reste = 178 216 frames
  ReboutCX precedentes. **Ce pack ne constitue pas une production complete Q3m x4.**
- 12 BAM V6 / 5 175 frames (144 Q3m, reste F absent), 644 BAM V5 conserves octet pour octet.
- Corps CHFB1/2/3 et CHFF4 ; casque J6 ; boucliers C0/D3 ; armes S0/S1 : echantillons P1
  dans `coverage.json`. Centres/geometrie x1, sources et cycles preserves. B/tramage desactives.
- Runtime actuel conserve ; Nearest ; profils fpSprite/fpSELECT x1 restent desactives.
- Catalogue a echelle unique : autres animations = BAM natif pendant ce test x4 isole.
  Le catalogue x2 complet installe avant bascule est sauvegarde, avec l'INI, par la transaction.
- `coverage.json` : entrees historiques authentifiees, I/F/dep P1 identiques, V5/residus sans
  changement pixel ; `verification.json` : lecteur natif courant, 18 palettes, toutes les
  frames V6 et une frame de chacun des 656 BAM. Oracle LUT scalaire independant de l'encodeur.
- Tests hote uniquement : aucune validation visuelle/effets vivants/GL/FPS deduite.
- Vue native courte : `build/p3-6110-v4-x4-native` ; memes fichiers via liens physiques.
- `work/`, `captures/`, shards et transactions = locaux ignores. Anciens runs intacts.

Jeu et InfinityLoader fermes, depuis `G:\AI\BG2_Upscale` :

```powershell
$x4Run = 'sprite/families/playable-characters/6110-human-female-fighter/research/palette-q3m-p3-20261001-v4-x4-existing-6110'
& pipeline/scripts/Install-CreatureSprite-XN-Catalog-Test.ps1 -JobFile "$x4Run/x4-existing.job.json" -RuntimeManifest "$x4Run/runtime.json" -CreatureSpriteFilter Nearest
# Retour exact au catalogue x2 et a l'INI presents avant ce test ; DLL conservee.
& pipeline/scripts/Restore-CreatureSprite-XN-Catalog-Test.ps1 -JobFile "$x4Run/x4-existing.job.json"
```

Piloter le jeu manuellement. Tester les quatre armures puis les casques/boucliers/armes ;
repos, marche, attaques, directions, changement de couleurs. Le traitement de palette
change entre anciennes frames et echantillons Q3m : prendre cette limite en compte.
