# Lot3 — analyse des quatre décors, 2026-10-11

État : analyse uniquement ; aucune production, installation ou QA nouvelle. Périmètre du découpage initial : AM0902L / AM1001A / AM1512PA / AM2008A, 10 occurrences / 10 cartes. Palettes embarquées pour les quatre.

Sources : `animations/index/{ressources,occurrences,animation_upscale_registry}.csv` ; BAM `animations/ressources/<REF>/source.bam`. Décodage `bam_export.decode_bam`, lookup `export_bam_frames.cycle_metadata`. Mesures/aperçus : `animations/tmp/lot3-analysis-20261011-v1/{source-analysis.json,installed-area-analysis.json,native-overview-assembled.png}`. ARE override prioritaires puis BIF lus ; index et installations inchangés.

| Asset | Structure vérifiée | Recette proposée (à produire/évaluer) |
|---|---|---|
| AM0902L | 32 frames distinctes, **4 tuiles synchronisées ×8 slots**, pas 32 poses successives. Montage natif256×317. C0=0,2,4,6,16,18,20,22 ; C1=1,3,5,7,17,19,21,23 ; C2=8,10,12,14,24,26,28,30 ; C3=9,11,13,15,25,27,29,31. | ReboutCX x4 contextuel : assembler par slot aux positions(-cx,-cy), correction limitée aux bandes de raccord selon doctrine multipart ; interpolation cohérente sur montage, redécoupe native. Fondu éventuel seulement silhouette extérieure ; aucun fondu des bords internes des tuiles. Pas de codec Q3m de créature à introduire dans le runtime RGBA de décor. |
| AM1001A | Fontaine + bassin losange212×149, centre108,153 ; 7 frames distinctes, 1 cycle0..6 ; 5 copies sur5 cartes. | Base LIQUIDE-SEEDVR-SPLINE4 : SeedVR2 7B INT8/LAB x4 → Apollo8 ; masque adapté aux quatre arêtes du losange et au jet, préserver éclaboussures. Fondu4px x4 de départ. Lower Edge Cover seulement si le raccord avec une carte montre un trou/liseré ; ne pas arrondir le bassin en ellipse. |
| AM1512PA | Portail parallélogramme54×109, centre27,109 ; 5 frames distinctes, **lookup10 slots [0,0,1,1,2,2,3,3,4,4]**. | Base PORTAIL-SEEDVR-SPLINE8 adaptée aux angles : SeedVR2 7B INT8/LAB x4 ; collapse uniforme avant Apollo8 7,5→30 ; contour suivant la silhouette, fondu intérieur4–8px x4 à évaluer, éviter ellipse/coins arrondis. |
| AM2008A | Effet circulaire lumineux ; 15 frames distinctes, **15 géométries**, max144×135. Centres variables. Blended sur3 cartes. | EFFET-BLENDED-REBOUTCX-APO8-PREMUL : ReboutCX x4 → Apollo8, canvas aligné avant inférence, recadrage natif par frame ; balayage inner4/8/12/16 sur sortie réelle, cœur et étincelles préservés ; prémultiplication unique et RGB nul sous alpha nul. |

## Durées cibles

Convention runtime15fps natif →30fps ; le BAM ne stocke pas de FPS. Aucun accéléré après suppression des doublons.

| Asset | Entrée d'interpolation | Sortie/cycle | Durée/cycle |
|---|---|---|---|
| AM0902L | 8 poses complètes à15fps ; 4 cycles/tuiles conservés | 16 phases par tuile, 64 frames runtime au total | 8/15s =0,533333s |
| AM1001A | 7 poses à15fps | 14 phases | 7/15s =0,466667s |
| AM1512PA | 5 poses à15/2fps, `--collapse-uniform-duplicate-holds` | 20 phases ; lookup natif10 slots conservé | 10/15s =0,666667s |
| AM2008A | 15 poses à15fps | 30 phases | 1s |

Prévision : 128 frames runtime pour les quatre assets, sous réserve de déduplication des sorties interpolées. Aucun doublon RGBA source à supprimer ; répétitions AM1512PA dans le lookup uniquement.

## Installation/QA future

- AM0902L : AR0902 (1171,811), flags0x1351 ; tiles aux centres(129,158)/(0,144)/(115,0)/(0,0), dimensions129×158/103×144/115×159/127×159. Runtime possède `resolve_timeline_subframe` pour cycles synchronisés ; contrôler sélection/centrage/continuité des4 dessins, sans modifier DLL à ce stade.
- AM1001A : AR0905/AR1001/AR1006/AR1007/AR1009 (915,533), flags0x1141 ; FLAME2S installé à préserver sur les5 cartes.
- AM1512PA : AR1512 (208,487), flags0x1101 ; FIRE_4 installé à préserver. Bit6 absent : contrôler occlusion via pont natif existant.
- AM2008A : AR1010/AR2008 (593,503), flags0x1043, FIRE_4 installé à préserver ; OH5120 (780,480), nomFiery_Boil, flags0x1212, **désactivée**, transparence70, hauteur0. Prévoir activation temporaire en console pour QA ; préserver paramètres ARE/quête/sauvegarde.
- Aucune ressource cible déjà installée. AR0902/OH5120 sans registre animation ; les8 autres cartes ont les ressources ci-dessus. Pare-feu release inchangé.
- Flags ARE : [IESDP, section animations](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/are_v1.htm#formAREAV1_0_Anim) ; bit0 activation, bit1 noir transparent, bit6 masquage par murs. Données locales ci-dessus font foi pour chaque occurrence.

Ordre proposé : AM0902L (cas contextuel), AM1001A (5 raccords de carte), AM1512PA (maintien×2/angles), AM2008A (géométries variables/rendu additif).
