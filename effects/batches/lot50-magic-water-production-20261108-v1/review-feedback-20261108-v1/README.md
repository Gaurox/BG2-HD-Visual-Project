# Retours06/13/34/35/45 — 2026-11-08

- 06 SPARMOR2 : original natif ZFR06O / nouveau ZMWT06 ; même durée source, IA seulement dans le nouveau.
- 13 WHIRLY : ZMWT13 corrigé CPU (canonique WHIRLY et XMWN13 corrigés aussi) ; ZFR13B conserve l’ancien HD. Tous les verts178, y compris2408pixels enfermés, sont retirés ; alpha de mélange de palette +despill, 0pixels verts couverts selonG>max(R,B)+8. Centres/durées/carrier inchangés.
- 34 SPSDRAE2 : vrai masque RGBnoir, alphamax196, usage potentiel spread CDDRBLCK. ZFR34N = natif décalé100px àdroite ; ZFR34C = même alpha en rouge.
- 35 SPSHADOW : ombre noire native5–7px, usage potentiel shadow SPATTCK2. ZFR35N = minuscule natif décalé100px ; ZFR35C = diagnostic rouge agrandi4×monde, uniquement diagnostic.
- 45 WTRBODY2 : utilisateur «non je ne sais pas. c’est pas grave on le valide» ; accepté uniquementxBR2/nearest2/Apollo30 installé, décision immuable et sélection. Aucune carte native confirmée, aucun test surmap déduit. WTRBODY1 seul trouvéAR0502(499,182) ; aucune carte modifiée.
- Recherche WTRBODY2 : AREnatifs+overrides ;5410BCS/VVC/EFF/PRO ;8550tables/IDS/INI/dialogues/sorts/items ; aucun appel natif trouvé. Une référence de notretest ZMWB45 ignorée. Pas preuve d’absence de toute construction dynamique.
- Installation `effects/installations/magic-feedback-0613343545-20261108-v2/transaction.json` ;93cibles,50backings WHIRLY remplacés avec sauvegarde, ancienHD conservé sousalias ;23808contrats passent avant+après, GPUintouché, aucunerelease.

## CLUA

Original06 puis nouveau :

```lua
C:Eval('CreateVisualEffectObject("ZFR06O",Player1)',0)
C:Eval('CreateVisualEffectObject("ZMWT06",Player1)',0)
```

13corrigé puis ancienHD :

```lua
C:Eval('CreateVisualEffectObject("ZMWT13",Player1)',0)
C:Eval('CreateVisualEffectObject("ZFR13B",Player1)',0)
```

34natif décalé puis témoin rouge :

```lua
C:Eval('CreateVisualEffectObject("ZFR34N",Player1)',0)
C:Eval('CreateVisualEffectObject("ZFR34C",Player1)',0)
```

35natif décalé puis témoin rouge agrandi :

```lua
C:Eval('CreateVisualEffectObject("ZFR35N",Player1)',0)
C:Eval('CreateVisualEffectObject("ZFR35C",Player1)',0)
```
