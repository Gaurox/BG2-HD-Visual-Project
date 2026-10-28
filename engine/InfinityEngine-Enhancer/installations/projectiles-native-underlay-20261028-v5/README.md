# Projectiles composés — V5, 2026-10-28

- **Installé, retest ingame en attente.** DLL SHA36541C5F212077AD247658DC60CBC6998D4594414D9E4028CDCA4F8DACE80CF5,3454464octets ; reçu `installation.json`, sauvegarde V4 dans `backups/20261028T101826481254Z-bc4e02d9/renderer-install-receipt.json`.
- Demande : corriger crâne/orbe et généraliser aux autres assets compatibles sans retraiter les images déjà produites. V4 conservait ces surfaces multicellules natives ; logs SKLT24×52 et SPCHRORB56×60… rejetés.
- Principe générique : avant la dernière soumission BAM enregistrée, copier le préfixe natif déjà dessiné depuis la surface FX verrouillée ; ordres, couleurs, ombres et opacités des couches inférieures restent natifs. Au draw final, répéter ces pixels x1 en x4 nearest et placer la dernière frame HD à `FXRenderBam(x,y)-GetFrameCenter`, sans redimensionner ses pixels. La couche HD remplace le préfixe seulement sur son support ; alpha uniforme de la palette native réalisé à chaque dessin.
- Pas de source-over inventé : noyau natif `426E43/426F66/42706E` écrit les texels réalisés, sans mélange avec le préfixe ; preuve `native-write-evidence.txt`. `42422F` calcule255-transparency ; bit0x100 autorise des écritures transparentes destructrices et reste exclu du nouveau chemin.
- Code : `core/effect_surface_owner.h` sépare propriétaire monocellule strict et candidat final avec préfixe ; `core/effect_native_underlay.h` projection/support/alpha/fingerprint ; `hooks.cpp` capture CPU RGBA avec conversion BGRA, palette réelle, corrélation/masque propres à la surface ; `effect_animation_x4_registry.*` upload et clé GPU incluant contenu natif/opacité/canevas/offset.
- Bornes/replis : au plus8soumissions, canevas natif≤1024×1024 (physique≤64Mio), allocation/accès mémoire vérifiés ; couche supérieure inconnue, alpha natif non uniforme, fumée composée, write-transparent0x100, géométrie/capture invalide → surface native complète. Interdit aussi le fallback vers un primaire HD isolé qui supprimerait des couches. Créatures hors de ce chemin. Budget GPU/64slots conservés, images/PRO/registre inchangés.
- Généralisation : aucune condition de correction spécialeSKLT/SPCHRORB ; whitelist de projectiles existante conservée. `generalization-candidates.csv` repère3PRO à ombre explicite : CHROMORB/TRAPSKUL/TSKULLNP. Opportunités statiques, pas3validations runtime. Autres préfixes compatibles peuvent bénéficier du même mécanisme ; les couches du préfixe conservent volontairement leurs pixels natifs.
- Tests finaux4/4passants : `build/iee-projectile-secondary-links-20261028-v1/composite-v5-tests-final.log` (7,08s). CPU : identité/ordre/borne de couches, transparence/alpha gradué rejeté, trous transparents/additifA0, offsets et empreintes. GPU WGL réel : pixels de préfixe conservés, couche HD au bon emplacement, opacité127/191, cache isolé quand ombre/opacité changent, tests existants de pression/LRU/étatGL. Masque : suites effet-occlusion etiee_tests inchangées passantes. Build `composite-v5-build-final.log` ; `git diff --check` passé.
- Installation : jeu/InfinityLoader absents vérifiés hors sandbox ; recette `pipeline/recipes/projectiles-secondary-links-20261028-v1/install.py prepare-v5|install-v5` déjà exécutée. DLL seule changée ;537ressources,62099backings,manifest/registre,PRO,INI,shaders,personnages/eau conservés ;0inférence,0release. Reçus existants immuables, ne pas réexécuter.
- QA nuage V4 acquise conservée pour son chemin monocellule et ses octets ; aucun nouveau test global imposé.

## Retest ciblé

Relancer InfinityLoader, partie de test sans sauvegarder, personnages espacés :

```lua
C:Eval('ForceSpellRES("SPWI313",Player2)',0)
C:Eval('ForceSpellRES("SPWI118",Player2)',0)
```

- Vérifier vol crâne + ombre + déclenchement ; orbe + ombre + couleur/transparence ; si possible passage près d'un décor occultant.
- Logs attendus : `EFX_NATIVE_SURFACE ... layers=2 nativePrefix=true nativeOpacity=...`, puis `EFX_BOUND_PHASE SKLT/SPCHRORB` au draw final,texturex4 + phases impaires. `EFX_COMPOSITE_REJECT` explique un prérequis manquant ; `EFX_MASK_FALLBACK` conserve le natif si le masque échoue.
- Ne pas déduire une QA de tous les fragments/enfants depuis ce test. Trois productions absentes (BGLRYU/SPCL236U/SPGLYPHI), ressourceLIGHTSTO/MAGMIS, variantesSHAREA/ID38 et examen cycle9LIGHTCHA restent des cas séparés.
