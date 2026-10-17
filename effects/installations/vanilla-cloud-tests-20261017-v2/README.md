# Nuages vanilla : six commandes Z58 — 2026-10-17

- Statut : **installé/vérifié hors jeu**, affichage à confirmer après relance vanilla. Autorisation : utilisateur demande les6commandes exactes du groupe37–42.
- Reçu : [`installation.json`](installation.json). Cible : dossier de `BG2EE VANILLA.lnk`, `G:/AI/BG2_Vanilla_23534562`.
- Ajouts seuls :6VVC `override/Z580269.vvc`, `Z580278.vvc`, `Z580290.vvc`, `Z580300.vvc`, `Z580310.vvc`, `Z580315.vvc` ; copies identiques aux contrôleurs du candidat HD installé, leurs références BAM lisent les images natives vanilla.
- Contrôles : absence de collision KEY/override ; BAM natifs présents, cycles/slots/index valides ; VVC492octets/signature/référence/cycles/FPS15/flags normal ou Blended conformes. Copie atomique, SHA256 après installation et revérification des6VVC +7fichiers préservés (exécutable/KEY/engine.lua +4alias VVCv1). Aucun BAM/SPL/PRO/renderer HD installé ; session vanilla arrêtée lors des écritures.
- V1 conservée : `effects/installations/vanilla-cloud-tests-20261017-v1/` ; ses4commandes homonymes restent disponibles. Les nouveaux noms Z58 fonctionnent désormais comme noms de contrôleurs installés dans les deux copies du jeu, avec leurs images respectives.
- Cycles : BDWOFOGA4loop ; SPCLOUDK2once ; SPCLOUDS2once ; SPDFOGA1once ; SPHORWIA2once ; SPHORWIL0loop. Flags normaux pour les4premiers ; Blended pour les2derniers ; boucles bornées comme les tests HD. Animations isolées, aucun sort/dégât/dispersion PRO.

```lua
-- 37 BDWOFOGA / cycle004-loop
C:Eval('CreateVisualEffectObject("Z580269",Player1)',0)
-- 38 SPCLOUDK / cycle002-once
C:Eval('CreateVisualEffectObject("Z580278",Player1)',0)
-- 39 SPCLOUDS / cycle002-once
C:Eval('CreateVisualEffectObject("Z580290",Player1)',0)
-- 40 SPDFOGA / cycle001-once
C:Eval('CreateVisualEffectObject("Z580300",Player1)',0)
-- 41 SPHORWIA / cycle002-once
C:Eval('CreateVisualEffectObject("Z580310",Player1)',0)
-- 42 SPHORWIL / cycle000-loop
C:Eval('CreateVisualEffectObject("Z580315",Player1)',0)
```

Relancer vanilla, Ctrl+Espace, une commande à la fois ; laisser défiler le jeu si la console l'avait mis en pause.

```powershell
python -B pipeline/recipes/effects-vanilla-cloud-tests-20261017-v2/install.py verify
# Retrait : vanilla fermé ; enlève seulement les6VVCv2 si leurs hashes concordent.
python -B pipeline/recipes/effects-vanilla-cloud-tests-20261017-v2/install.py restore
```

Recette v2 réutilise les fonctions copie atomique/vérification/retrait v1 sans modifier cette recette ni son reçu historique.
