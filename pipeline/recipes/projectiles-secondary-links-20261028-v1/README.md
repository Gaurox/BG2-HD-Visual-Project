# Raccords secondaires124PRO —2026-10-28

- Scope : `scope.json`,124racines/136PRO dans les fermetures,103RESREF candidats. Aucun job IA ni retraitement des fichiers images.
- Audit parent : `projectiles/analysis/audit-complet-243-20261028-v1/` ; progression : `projectiles/analysis/liaisons124-20261028-v1/`.
- Source : `hooks.cpp`, `core/effect_surface_owner.h`, `core/effect_smoke_palette.h`, `core/effect_secondary_scope.h`, `effect_animation_x4_registry.*`, `game/build_manifest.*`.
- Nouvelles entrées manifestées BG2EE2.7.3 : FXLock29e190,FXRenderBam29e260,centre natif411660. Signatures vérifiées, offsets hors hooks.
- FXLock commence un passage ; FXRenderBam copie l'identité de la cellule réellement dessinée ; FXRender résout cette cellule. Plusieurs soumissions/cellules →fallback natif, aucune couche perdue. Autres familles hors whitelist gardent leur chemin précédent.
- WED : capture des mutations alpha entre dessin de la cellule et FXRender ; capture existante du propriétaire prioritaire. Aucun remplacement non masqué si transfert invalide.
- Fumées SPSMPUFF : palette native effectivement réalisée, indices17..22 →tonalités source231..115. Application en mémoire à l'upload ; fingerprint palette/opacité dans la cléGPU ; backing et alpha d'origine intacts sur disque. Surface native et variante colorée distinctes des entrées neutres.
- Révision2 : ancre noire0→0 (neutralité additive),alpha natif uniforme conservé. Source native via GetFrameCenter411660 +GetFrameSize411780 ; copie x4 sans redimensionnement dans le canevas FX natif, offset depuis les arguments FXRenderBam. Cache indexé aussi par canevas/offset. Cropping/offset hors surface rejetés.
- FIREBAT : constat réel v1 natif69x78 contre pack69x65 →fallback. Révision2 projette les276x260pixels existants dans le canevas276x312 ; la position réelle reste conditionnée aux métadonnées natives et doit être vérifiée au retest.
- Traces : `EFX_NATIVE_SURFACE` (route et placement), `EFX_BOUND_PHASE` (FIREBAT/SPSMPUFF réellement liés,backing,phase,ticks,dimensions). Ne pas déduire30FPS d'un pointeur de production.

## Builds et installations

- Build de travail : `build/iee-projectile-secondary-links-20261028-v1/` ; VS2019x64 ; dépendances locales/disconnected. Hors sandbox requis pour MSBuild/WGL (le build confiné bloquait au démarrage des sous-processus).
- Tests passants `final-tests.log` : owner/scope,palette/opacité/noir,GPUcache et projection sans redimensionnement,`iee_tests`. TestsGPU : isolation couleur/neutre,LRU,pression mémoire,restaurationGL.
- `install.py prepare|install` : reçu v1 `engine/InfinityEngine-Enhancer/installations/projectiles-secondary-links-20261028-v1/`.
- `install.py prepare-v2|install-v2` : reçu v2 `engine/InfinityEngine-Enhancer/installations/projectiles-secondary-links-padding-20261028-v2/`.
- `install.py prepare-v3|install-v3` : V3 installée, `engine/InfinityEngine-Enhancer/installations/projectiles-flight-mask-20261028-v3/README.md`. Masque/corrélation monocellule par passage FX prioritaires sur le propriétaire ; corrige la contamination par le halo précédent. DLL SHA2370067272AC3CA909D86D05CF90656A24A5C0E84719049DF4817DC54DB67E7B ; 2/2 tests (`flight-mask-v3-tests.log`), QA ingame en attente. Reçu V3 existant, ne pas réexécuter.
- Retest V3 : `projectiles/analysis/boule-de-feu-retest-v3-20261028-v1/README.md`. Vol FIREBAT confirmé au dessin final x4,14phases2–15 dont7impaires, médiane33,359ms, masque0x20, aucun repli occlusion du vol observé ; preuve technique ciblée, aucune acceptation visuelle générale des124cas.
- V4installée via `prepare-v4|install-v4` : `engine/InfinityEngine-Enhancer/installations/projectiles-cloud-alpha-20261028-v4/README.md`. Sélection textureSPCLOUDK→X58CLK existant, alpha palette natif ;425pairesRGB/géométrie/cycles vérifiées,0image retraitée,2/2tests. SHA CEFBCB1986379DC23F526A2862E42DD75863D7FB96B55FACC0126DC46AB99C20 ; retest nuageV4attendu. Reçu existant, ne pas réexécuter.
- V5installée via `prepare-v5|install-v5` : `engine/InfinityEngine-Enhancer/installations/projectiles-native-underlay-20261028-v5/README.md`, SHA36541C5F212077AD247658DC60CBC6998D4594414D9E4028CDCA4F8DACE80CF5. Préfixe natif capturé avant dernière coucheHD, opacité palette native, canevas/cache/masque communs ; 4/4tests CPU/GPU passants,0image retraitée. Crâne/orbe à retester, généralisation conditionnelle (TSKULLNP notamment). Reçus existants, ne pas réexécuter.
- V6installée via `prepare-v6|install-v6` : `engine/InfinityEngine-Enhancer/installations/projectiles-clouds-wave1-20261028-v6/README.md`, SHA9CA03C3C6CB3AFAA2EFF79398094519A728DB66833BE311E18B3FE698E9F37E4. SPCLOUDS/SPDFOGA→X58CLS/X58DFOG existants,984paires vérifiées,2/2tests,0image retraitée. Retest deux nuages attendu ; SPINCINA/SPHORWIL/A acceptés visuellement pour la vague1V5. Reçus existants, ne pas réexécuter.
- Les deux reçus existent : **ne pas relancer pour écraser**. Chaque remplacement sauvegardé ; DLL+INI identique seuls fichiers gérés. Manifest537,62099textures,PRO,shaders,personnages,carte inchangés. Header eau généré identique au build installé précédent.
- V1 : fumée/explosion/nuage effectivement liés ; utilisateur signale transparence fumée incorrecte, reste semble correct ; FIREBAT etSPCHRORB en fallback. Pas d'acceptation générale.
- V2 : installé jeu/InfinityLoader fermés ; retest boule de feu reçu, aspect jugé correct. Analyse `projectiles/analysis/boule-de-feu-retest-20261028-v1/README.md` : fumée x4/interpolée confirmée au dessin final ; explosion/flammes x4+masque liés. FIREBAT : bind x4 puis repli occlusion0x40, aucune phase finale HD ; vol encore à corriger, aucune QA globale.

## Limites encore explicites

- Surfaces composites : conservées natives ; SHSKULL/SPSHADOW ne doivent pas être supprimés pour forcer du HD. CHROMORB primaire+ombre ne sont pas une seule texture de la géométrie du primaire.
- Enfants natifs : `native-hardcoded-children.txt`.73/76→SPMAGMIS ;197..202→SHAREA +BMP SHAREA3/4/5/6/2 selon ID ; BMP ≠BAM à produire. Le dispatch coloré de ces chemins n'est pas déduit de l'entrée SHAREA par défaut.
- ID38 : branche de lookup générique, pas de BAM prouvé. SPCHUNKS dans la whitelist reste une piste compatible, pas une preuve d'appel par38.
- Les3sources absentes etLIGHTSTO ne sont pas produits/modifiés. LIGHTCHA hors des124 conserve son examen de cycle9 distinct.
- Aucune release ni QA d'asset modifiée ; corrections de liaison et essais seulement.

## Retest utilisateur

Deux personnages éloignés ; sorts réels, partie de test sans sauvegarder :

```lua
C:Eval('ForceSpellRES("SPWI304",Player2)',0)
C:Eval('ForceSpellRES("SPWI502",Player2)',0)
C:Eval('ForceSpellRES("SPWI313",Player2)',0)
C:Eval('ForceSpellRES("SPWI118",Player2)',0)
```

- V2 : rejouer seulementSPWI304, confirmer fumée +projectile en vol ; lire `EFX_BOUND_PHASE` et l'absence de fallbackFIREBAT pour conclure au x4 et aux phases intermédiaires.
