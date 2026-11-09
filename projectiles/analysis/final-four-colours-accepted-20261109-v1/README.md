# Trois couleurs acceptées —2026-11-09

- Décision utilisateur :«les3tests sont validé visuellement». HLYMITE rouge194,SHAIR4/130,SHEARTH6/137 acceptés ;0retest demandé. DLL `5A1559B5…3106612B` conservée.
- `acceptance.json`, `CLUA-tested.md`, `trace-summary.json`, `trace-selected.txt.gz` :commandes réellement utilisées figées,palettes natives effectivement liées àl'uploadHD pourles3ressources,phasesimpaires observées. Masque mesuré pourHLYMITE/SHAIR ;aucun masqueSHEARTH observé,ne pas en inventer. SPSCORIC reste qualifié statiquement9cycles etQA visuelle antérieure réutilisée ;aucun nouveaudraw live revendiqué.
- **Incident du piloteSPWI985** :leSPL natif contient1effet168,target2,timing4,durée2s,paramètres0/0. Il retire la créature ciblée ;Player2 disparaît par effet de jeu, pas à cause du renduHD. `SPWI985-native-effect.json` lie les octets/SHA. Référence :[IESDP168](https://gibberlings3.github.io/iesdp/opcodes/bgee.htm#op168).
- ConsigneinitialePlayer2 corrigée :utiliser une créature jetable pour tout éventuel usage futur ;recharger la sauvegarde avant l'essai pour restaurerlecompagnon. Ne pas recréer/remplacer arbitrairement un compagnon global ;aucune modification des sauvegardes réalisée.
- `tracking-before.json` conserve lesQA antérieures ;installation/release etQA hors lot intactes. Contrôles neutres/faisceau automatisés,aucune nouvelle campagne manuelle.
