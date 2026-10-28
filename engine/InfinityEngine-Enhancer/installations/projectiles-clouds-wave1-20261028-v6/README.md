# Deux nuages — alpha natif réutilisé, V6

- **Installé, retest attendu**. DLL SHA9CA03C3C6CB3AFAA2EFF79398094519A728DB66833BE311E18B3FE698E9F37E4,3455488octets ; reçu `installation.json`, V5 sauvegardée sous `backups/20261028T133626459467Z-ae0ecb4d/renderer-install-receipt.json`.
- Source du défaut et preuve de compatibilité : `projectiles/analysis/validation-vague1-clouds-20261028-v1/README.md` /`evidence.json`. 984paires existantes, RGB/géométrie/cycles/timelines/carriers identiques ; seul alpha diffère. Aucune nouvelle image/IA.
- `core/effect_texture_alias.h` : SPCLOUDS→X58CLS,SPDFOGA→X58DFOG ; SPCLOUDK→X58CLK conservé. Identité commune aux préchargements, résolution et dessin ; aucun BAM/PRO/SPL natif renommé. Cible absente/incompatible → repli natif. BDWOFOGA inchangé : contrat de l'alias différent.
- `effect_secondary_scope.h` : deux alias de la même famille ajoutés à la whitelistFX. `hooks.cpp` : marqueur d'alias borné par source ; traces finalesX58CLS/X58DFOG ajoutées, quota64phases PAR ressource (7ressources suivies max), évite qu'un nuage consomme toutes les traces du suivant.
- Build `build/iee-projectile-secondary-links-20261028-v1/clouds-wave1-v6-build.log`. Tests2/2passants (`clouds-wave1-v6-tests.log`,0,97s) : raccord/whitelist/idempotence + conservation des contrats existants ; aliasBDWOFOGA incompatible reste absent. `git diff --check` passé. Code de composition/cache/masque V5 inchangé ; pas de nouvelle campagneGPU requise.
- Installation : BG2/InfinityLoader absents vérifiés hors sandbox ; DLL seule changée, INI/manifeste537/registre62099backings/PRO/shaders/personnages/eau conservés.0image retraitée,0release. Recette `pipeline/recipes/projectiles-secondary-links-20261028-v1/install.py prepare-v6|install-v6`, déjà exécutée ; reçus immuables, ne pas relancer.
- Relancer InfinityLoader et tester seulement :

```lua
C:Eval('ForceSpellRES("SPWI213",Player2)',0)
C:Eval('ForceSpellRES("SPWI614",Player2)',0)
```

- Vérifier disparition du fond opaque/contour, dispersion et transparence ; les deux nuages ne doivent pas forcément avoir la même opacité. Logs attendus : `EFX_TEXTURE_ALIAS` versX58CLS/X58DFOG, `EFX_BOUND_PHASE` x4+phases impaires, absence de repli masque. Le bind ne suffit pas à inventer une acceptation visuelle.
