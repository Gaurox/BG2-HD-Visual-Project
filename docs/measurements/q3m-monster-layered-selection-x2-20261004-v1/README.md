# Prochain lot proposé — Monster_layered complet disponible, Q3m x2

- **Proposition seulement** ; aucun traitement/inférence/pack/installation/modification moteur. Cible Q3m V7 K6/quatre partenaires/huit niveaux, palette améliorée live/x2/CatmullRom, **sans SDF**. Groupe du suivi `monster_layered` =deux classes natives2000/8000 ;tous septIDs inclus, corps/armes associés etMGNLINV auxiliaire.
- **SeptIDs/sept modèles distincts**, 66 BAM natifs/6 512frames déclarées ;**5 758travaux source/encodages uniques**, 276hits Q3m compatibles vérifiés →**5 482travaux manquants**, donttroistravaux spéciaux sans inférence. Aucun alias de modèle entre IDs ;variantes CRE/palettes d'un ID partagent son même corps/équipement.

| ID | Modèle natif / préfixe | Type | BAM | Frames | Uniques | Cache | Nouveaux |
|---|---|---|---:|---:|---:|---:|---:|
| 2000 | Sirine /MSIR | 2000 | 9 | 954 | 786 | 0 | 786 |
| 2100 | Volo /UVOL | 2000 | 8 | 532 | 277 | 276 | 1 |
| 2200 | Ogre mage /MOGM | 2000 | 8 | 960 | 870 | 0 | 870 |
| 2300 | Chevalier de la mort /MDKN | 2000 | 4 | 552 | 552 | 0 | 552 |
| 8000 | Gnoll /MGNL | 8000 | 13 | 1 090 | 1 090 | 0 | 1 090 |
| 8100 | Hobgobelin /MHOB | 8000 | 12 | 1 152 | 1 152 | 0 | 1 152 |
| 8200 | Kobold /MKOB | 8000 | 12 | 1 272 | 1 032 | 0 | 1 032 |
| **Total** | **7 modèles/IDs** | | **66** | **6 512** | **5 758** | **276** | **5 482** |

- Déduplication vérifiée SQLite/pixels/profil : **754 répétitions** =168sirine +255Volo +90ogre mage +240kobold. Un groupe de BAM entièrement identiques : **UVOLMG2/UVOLMG2E**, chacunune frame ;pas de suppression de binding/cycle/centre natif. Volo déjàpilote partiel, jamais famillecomplète acceptée ;ses276acquis sont réutilisables.
- **Ressources absentes : aucune parmiles66BAM indexés**, SHA canonique revérifié directement BIF/KEY stock, aucune surchargedansoverride. Armes déjàcomprises : sirineB/arc, VoloM, ogre mageS, gnollH/S, hobgobelinB/S, koboldB/S ;MDKN sans couchearme distincte déclarée. Ne pas assimiler resref d'armeoptionnel vide àun assetabsent.
- **Anomalie native à respecter avantproduction** : `MSIRG2BE` contient30frames largeur1/hauteur0. Analyse locale admet cesdéclarationsvides sanscréer depixels ;producteur V7 actuel lesrejette. Déterminer usages/slotsnatifs, conserver l'étatvide, nepasnormaliser la géométrie ni inventer une frame. Lesnombres incluentces30déclarations/une identitévide.
- **Prérequis runtime avantinstallation** : manifest courant ne couvrequeclasse2000, vtable`0x5aa650`/render`0x32ee90`/parser`0x3403f0`/ctor`0x311300`. Classe8000 (`monster_layered_spell`) : vtable`0x5aa840`/render`0x32f3b0`/parser`0x340610`/ctor`0x3119a0`, cheminabsent duhookowner8. Ajouter cechemin de composition pourlesseuls8000/8100/8200 et vérifier leurscouches ;sinon ils restentvanilla. Exécutablepinné `EXE_SHA256`, vtableslots38/61 relus ;aucun patch appliqué.
- Nativepalettekind : sirine/ogremage rampes1, Volo/MDKN fixe0 ;trois8000 héritentkind1 prévu, champfalse_color nonexplicitedansINI. Vérifier lecontrat palette8000 sursonchemin natif au momentdu delta moteur ;lesacquisVolo276 utilisentkind0 explicite.
- Comparaison **source** restante : Layered5 758 <Quadrant5 768 <Old6 701 ;ceci n'estpas une estimationlatence/GPU ni unclassementaprès touscaches. Sources : `sprite/index/q3m-work-tracking.json`, `q3m-source-work-plan.json`, sourceCSV/KEY/BIF ;`analyze.py`, `selection.json`, `analysis.json` conserventlesressources/duplicats/hits etlesdeuxprérequis.
