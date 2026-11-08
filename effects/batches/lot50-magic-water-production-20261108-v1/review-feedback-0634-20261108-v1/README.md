# Retour06/13/34/35

- 06 SPARMOR2 : xBR4X sans flou, interpolation **CPU minterpolate MCI** vers30FPS ; pas Apollo/GPU. Ancres/centres/pauses natifs conservés. CanoniqueSPARMOR2 +XMWN06 remplacés, ancienSeedVR conservé MFX06S/ZFX06S.
- 13 WHIRLY corrigé : explicitement accepté, QA immuable +sélection.
- 35 SPSHADOW : explicitement accepté **natif**, ni rouge ni agrandi en production.
- 34 : défaut de lanceur. Cycle0 référence seulementframe19,alpha0 ; les cycles1/2 sont visibles puis tiennent longtempsframe19. ZMWT34/ZFR34N/ZFR34C corrigés surcycle1, durée12s ; ZFX34B pourcycle2 ; ZFX34R = témoin RGBA noir avec alpha natif/x4nearest et interpolation alphaCPU, sansIA.
- Logs : rendus XMWN06/XMWN13 présents, pas de traceHD des anciens témoins34 (chemin natif). Absence de traceHD ne prouve pas un échec natif. Cause confirmée en lisant VVC +lookupBAM +alpha : cycle0vide. Aucun moteur/DLL/INI modifié.
- Installation `transaction.json` :122backings06 remplacés avec sauvegarde +2comparaisons HD ajoutées ;24936contrats natifs passent candidat+installé ; GPU toujours en pause. QA06/34 àretester.

Relancer via InfinityLoader. Une commande àlafois.

## 06 xBR actuel / ancien SeedVR

```lua
C:Eval('CreateVisualEffectObject("ZMWT06",Player1)',0)
C:Eval('CreateVisualEffectObject("ZFX06S",Player1)',0)
```

## 34 cycle1 noir / cycle1 rouge / cycle2 noir / témoin RGBA

Laisser tourner12s après fermeture de la console ; les pauses natives sont conservées.

```lua
C:Eval('CreateVisualEffectObject("ZMWT34",Player1)',0)
C:Eval('CreateVisualEffectObject("ZFR34C",Player1)',0)
C:Eval('CreateVisualEffectObject("ZFX34B",Player1)',0)
C:Eval('CreateVisualEffectObject("ZFX34R",Player1)',0)
```
