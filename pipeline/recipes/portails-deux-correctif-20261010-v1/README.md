# OHHPORT / BDFORCEW — correction installée 2026-10-10

- Demande : correctif + installation ; release hors périmètre ; QA ingame du correctif en attente.
- État/retours arrière : `animations/batches/portails-deux-correctif-20261010-v1/installation.json` → reçus DLL/AR0811/OH8100.
- Installation active : `animations/packs-par-zone/portails-deux-correctif-20261010-v1-complete/{AR0811,OH8100}` ; verrou `animations/index/area-pack-lock.json`.
- OHHPORT : source native frame2 index252 noir opaque → alpha0 uniquement sur 15007 pixels noirs ; index transparent natif conservé ; 1376 pixels de sujet. Nouveau run xBR2 blend→nearest2 ; Apollo8 15→30 régénéré avec contexte corrigé ; RGB prémultiplié une fois. Runtime modifié : frames2/6/7/8/9 ; natives0/1/3/4/5 byte-identiques. Fond parasite phase5/frame8 supprimé. BAM canonique immuable.
- BDFORCEW : RGB Rebout/Apollo conservé avant prémultiplication ; SplineFit1 multicontour sur 340 frames ; erreur1px x4, espacement1.5, supersampling4, padding32, feather interne16 ; cycles/centres/cadence inchangés. Aucun cumul du feather de l'ancien pack.
- WED : polygone180 OH8100, bord `(2129,1011)→(2560,708)` ; masque natif x1 répliqué x4 = seconde crénelure. Aucun WED édité. DLL : scope `AreaRegistry` + propriétaire `AreaAnimation` + subjectId `0x574543524F464442` BDFORCEW + dither0 ; transfert binaire uniquement. Distance intérieure chamfer, smoothstep16px x4, reconstruction bilinéaire continue A ; transfert natif R/G/B exact ; RGB additif et alpha atténués ; aucun pixel masqué révélé. Dither/fractions/autres assets : chemin exact précédent.
- DLL de départ : `70a2745b212babe378c6ccd8b1660110ad3aac5a9ef7523ecbbfcea776bb6d09`, sources `sprite/.work/q3m-all-sprite-playback-x2-20261007-v1/runtime-src`. Delta : `animations/batches/portails-deux-correctif-20261010-v1/renderer-delta.patch` ; autres sources et headers générés eau/version byte-identiques au snapshot installé. INI installé inchangé.
- Vérifications : `local-checks.json` 352frames géométrie/centres/cycles, prémultiplication exacte, RGB0 sous alpha0 ; `renderer-test.log` 2tests natifs réussis ; `renderer-gl-tests.json` shader réel compilé/dessiné sur RTX5090, masques ordinaires/fractionnels/dither exacts, 132 niveaux de coverage, aucun pixel révélé. Simulation GPU ≠ QA ingame.
- Voisins préservés : AR0811 FIRE_1 15frames ; OH8100 FIRE_4/FPIT1S 26frames ; aucune autre map écrite.
- Previews : `animations/batches/portails-deux-correctif-20261010-v1/previews/{OHHPORT-before-after,BDFORCEW-WED-before-after}.png`.

```powershell
python -B pipeline/recipes/portails-deux-correctif-20261010-v1/verify_install.py --verify
# Reprise installation uniquement si nécessaire, reçus existants pris en compte :
python -B pipeline/recipes/portails-deux-correctif-20261010-v1/verify_install.py --install
```

```lua
C:MoveToArea("AR0811")
C:Eval('AmbientActivate("Tombwalk",1)')
C:MoveToArea("OH8100")
C:Eval('AmbientActivate("lounge_barrier1",1)')
C:Eval('AmbientActivate("lounge_barrier2",1)')
```
