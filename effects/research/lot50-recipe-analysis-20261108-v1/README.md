# Lot50 — recettes recommandées, 2026-11-08

**Retour de production ultérieur2026-11-08** : la proposition50SeedVR a été confrontée aux images produites.25micro-motifs inventaient des détails symboliques ; nouvelles variantes xBR4X/Apollo30 retenues provisoirement. [Résultat50 et attributions courantes](../../batches/lot50-seedvr7b-apollo30-20261108-v1/README.md). La table ci-dessous conserve l'analyse initiale ; elle n'est pas l'autorité des versions produites.

Analyse des990records source /1291slots /75cycles non vides ;50BAM toujours `not-started`. Lecture des palettes, cycles, centres, alpha, composantes, poses vides ; inspection des planches natives et des hypothèses de masquage vert. Aucune inférence/installation/QA/release lancée.

## Décision

Base commune : **SeedVR2 7B INT8/LAB x4 → Apollo apo-8 30FPS par cycle**, RGB et alpha séparés ; variantes alpha droit/prémultiplié explicites ; affichage NEAREST.50recommandations individuelles : [recipes.csv](recipes.csv), [analysis.json](analysis.json).

| Profil | Nombre | RGB après upscale, sigma x4 | Masque recommandé |
|---|---:|---:|---|
|F · petites flammes|12|0|Alpha natif nearest4, feather0 ; protéger pointes/grains.|
|T · feu texturé|7|1.2|Alpha natif, feather0 ; contrôler fragments périphériques.|
|H · énergie/halos|15|1.2, sauf3petits motifs à0|Feather0 ; témoin alpha natif + variante de flux conditionnelle selon mélange propriétaire.|
|D · grands diffus|4|1.2|Feather interne12 sur masses épaisses ; plafonner sur petits appendices, comparer au témoin0.|
|S · fumées fines|3|0|FALLMIST/SPSTINK : feather2 de départ, borné par épaisseur ; SPSMOLD :0.|
|P · particules/gouttes|6|0|Feather0, pas de retrait ; conserver toutes composantes/positions.|
|G · fond vert à résoudre|3|0 après préparation|Essai d'alpha dérivé indexé, puis profilF ; garder témoin natif et source.|

**Paramètres de départ, pas résultats validés.** Gauss0 sur petits motifs = adaptation conservatrice ; les lots26/33 utilisaient gauss1.2. Feather2 et plafonnement local du12 = propositions, pas recettes déjà acceptées telles quelles. Aucun seuil numérique de couverture ne vaut QA visuelle.

## Expérience réutilisée

| Précédent | Acquis | Application / limite |
|---|---|---|
|[Lot33 accepté](../../batches/lot33-impacts-accepted-20261018-v1/README.md), [production](../../batches/lot33-native-impacts-7b-apollo30-20261017-v1/README.md)|7B x4/Apollo30 ;28masques fins0 /5diffus12 ;32productions initiales retenues, SPDEATH3 remplacé.|BaseRGB/temporel ; SPBRNHND/SPBURN pour feu, SPMETSWM pour météores, SPSPARKS pour grains, SPRDRASI/SPHORPUF/STNKCLDD pour diffus. Analogie visuelle, aucun hash de réemploi déduit.|
|[Lot26 accepté](../../batches/lot26-accepted-20261017-v1/README.md)|Séparation fins/diffus ;17v2,8SDF sans retrait et visage corrigé retenus.|Feather12 global inadapté aux éléments étroits. Ne pas généraliser SDF à tous les feux.|
|[Nuées0.60 acceptées](../../batches/insectes-continu-accepted-20261027-v1/README.md)|Champ continu natif sigma0.25x1, isocontour0.60, SS4 ; mieux que disques/grillage ou micro-flou pour ces nuées.|Alternative locale pour marches de particules/flammes ; transposition non validée ici. Conserver témoin natif ; ne pas supprimer grains faiblement couverts.|
|[SPDEATH3 final accepté](../../batches/lot33-impacts-accepted-20261018-v1/README.md)|Bézier continu +fondu sigma4 adapté à une silhouette figurative.|Option pour contour structuré ; pas de vectorisation globale des halos/flammes chaotiques, pas de retrait1/2px.|
|[Lot31 chronologie/noir](../../batches/lot31-corrections-preview-20261018-v1/README.md), [révision](../../batches/lot31-xbr-nativealpha-black-20261019-v1/README.md)|Corrections techniques de pauses, noir neutre et flux ; installées, lot31 encore sans acceptation ingame.|Réutiliser les principes, pas toute l'ancienne fonction temporelle : conservation des ancres et occurrences nécessaire. Noir neutre = variante conditionnelle, pas vérité native établie.|
|[Nuages alpha palette](../../installations/cloud-palettealpha-20261017-v1/README.md), [acceptation ultérieure](../../batches/lot58-accepted-20261017-v1/README.md)|Préserver alpha natif gradué quand présent ; companions normaux distincts.|Ici50/50alphas réellement utilisés binaires : ne pas promettre une restauration de dégradé inexistant.|
|[Apollo padding lot33](../../../pipeline/recipes/effects-lot33-native-impacts-20261017-v1/README.md)|Crash ROI corrigé sur petits canevas par padding temporaire min128/multiples32 puis crop exact.|Prévoir ce chemin dès le départ ; préserver ancrage/crop final.|

Recettes de code : `pipeline/recipes/effects-lot33-native-impacts-20261017-v1/`, `effects-lot31-corrections-20261018-v1/correct.py`, `effects-cloud-palettealpha-20261017-v1/repair.py` ; sources de paramètres, pas scripts à relancer sur leurs lots historiques. ReboutCX/xBR du lot31 répondent surtout aux armes/traits géométriques ; aucun avantage démontré sur ce lot de textures diffuses.

## Temporel complet

- Lire les indices des cycles, pas l'ordre des records.75cycles animables ;48entrées vides conservées dans source/carrier, exclues d'Apollo. Conserver les alternatives, jamais les concaténer.
-15FPS = base de compatibilité non mesurée ;30FPS cible. Durée rationnelle `slots/15` et ancres natives ; conserver profils once/loop séparés tant que propriétaire inconnu, sans présenter tous les effets comme boucles naturelles.
- Dédupliquer le stockage et les entrées adjacentes identiques ; réinsérer holds/pauses à leur position. Préserver réapparitions non adjacentes. **Ne pas copier `distinct_keys/phase_sources` du lot33 tel quel** : suppression globale des doublons +répartition uniforme peut conserver la durée totale mais déplacer les événements.
- Adapter le chemin corrigé du lot31 : associer les sorties Apollo aux occurrences temporelles, pas seulement au dernier indice d'une identité. Ancre RGB/alpha originale aux ticks natifs ; interpolation seulement entre les poses voisines autorisées ; pas de mouvement inventé dans réserves vides.
- SPBDBURS :9cycles×20slots ; slot0transparent, slots1..7visibles,8..19transparents. DSTDVL2A :17visibles puis90transparents /107slots.
- SPSMOLD :6poses, chacune tenue3slots /18slots. LAVABUB2 :7visibles puis8transparentes /15slots. SPFSTRMI : dernier slot transparent.
- SPOUTA :3cycles×53slots, même éruption décalée ; noir opaque aux slots0..14/fin ou0..29 selon cycle, **pas alpha0 natif**. Réserves noires neutres seulement dans la variante lumineuse ; ne pas les confondre avec transparence démontrée.
- ACIDDTH :63records,21référencés seulement (42..62),2cycles9/12slots. Préserver42records hors cycles dans source/carrier ; pas de mouvement inventé à partir de ces records.

## Transparence / couleurs

- Les3fonds verts sont opaques dans le BAM : FLLGBLUE index47, FLMDBLU39, FLSM1PUR245 ; respectivement71.5%,91.3%,88.5% des pixels couverts sur tous records. Le simple index transparent0 ne les enlève pas.
- [Hypothèses examinées](green-mask-hypotheses.png) : supprimer uniquement composantes de cet index vert exact connectées au bord, dans une copie de travail ; extraction visuellement cohérente sur3poses par BAM. Vérifier toute la séquence et conserver version native ; ce n'est pas la preuve d'une clé native moteur. Source/palette/carrier historiques intacts ; futur contrat dérivé explicite.
- Mattes noires importantes : FIRE_1GR52.0%, FIRE_1GS50.3%, FIRE_4G259.0%, LAVAFIR183.7% du support natif. **Pas de seuil de détourage global.** STEAM1/4 comportent aussi des noirs : fumée sombre à conserver.
- Pour propriétaire lumineux établi, le compagnon normal peut encoder le flux : `E=round(RGB*A/255)`, `A'=round(A*max(RGB)/255)`, `RGB'=round(E*255/A')`. Vérifier énergie prémultipliée±1, cœur/couleur,3fonds. Représentation normale change l'occultation ; elle n'est pas équivalente au mélange additif sur tout décor. Conserver variante source et routage propriétaire explicite.
- RGB : exclure fond vert du modèle si hypothèse retenue ; remplissage couleur hors support avant inférence, réappliquer masque indépendant. Les3variantes vertes ne passent pas en production directement avec rectangle vert.
- Mesures noir/vert/composantes dans `analysis.json` portent sur tous les records, pas pondérées par durée ; ACIDDTH inclut donc aussi records hors cycles. La décision visuelle doit viser les cycles réellement joués.

## Attribution individuelle

ParamètresRGB/masque du profil ci-dessus ; exceptions par ligne et dansJSON. Analogue = proximité de traitement, jamais réemploi ni validation du nouvel asset.

| N° | RESREF | Profil | Analogue historique | Décision propre à cet effet |
|---:|---|---|---|---|
|01|FIM1YEL|F|SPBRNHND|Petite flamme, protéger pointes et scintillement. |
|02|FIM2YEL|F|SPBRNHND|Flamme jaune-verte compacte, même précaution sur les bords. |
|03|FIRE_1B|T|SPBURN|Flamme avec traîne sombre ; garder le brun de fumée en alpha normal. |
|04|FIRE_1C|T|SPBURN|Flamme étroite avec traîne ; pas de fondu interne large. |
|05|FIRE_1GR|H|SPSCHGI|Flamme verte sur matte sombre rectangulaire ; compagnon normal neutre conditionnel. |
|06|FIRE_1GS|H|SPSCHGI|Flamme et halo sur matte noire ; ne pas mélanger la matte avec le décor en normal. |
|07|FIRE_2|H|SPENTACI|Boule verte texturée et halo sombre ; conserver énergie lumineuse. |
|08|FIRE_2A|H|SPENTACI|Variante verte brillante ; palette indépendante, même géométrie à conserver. |
|09|FIRE_4BL|F|SPBRNHND|Petite flamme cyan, faible épaisseur ; aucun feather12. |
|10|FIRE_4G2|H|SPSCHGI|Petite flamme verte, majorité sombre ; RGB sans gauss sur ce petit motif. RGB sigma0.|
|11|FIRE_4GR|F|SPBRNHND|Petite flamme verte-jaune ; préserver franges et variations de teinte. |
|12|FISM1YEL|F|SPBRNHND|Très petite flamme, le flou peut la faire disparaître. |
|13|FLLGBLU|F|SPBRNHND|Flamme orange malgré le nom ; se baser sur la palette réellement extraite. |
|14|FLLGBLUE|G|SPBRNHND|Fond vert opaque index47 ; essai de masque indexé exact avant toute inférence. |
|15|FLLGRED|T|SPBURN|Flamme orange plus large ; préserver les petits fragments détachés. |
|16|FLM1PUR|F|SPBRNHND|Flamme violette minuscule, garder la silhouette et la couleur. |
|17|FLM1RED|F|SPBRNHND|Petite flamme orange ; traitement sans flou additionnel. |
|18|FLM2RED|F|SPBRNHND|Flamme compacte ; conserver détail et variations de taille. |
|19|FLMDBLU|G|SPBRNHND|Fond vert opaque index39, plus de90% du support ; ne pas envoyer ce fond au modèle. |
|20|FLML|F|SPBRNHND|Flamme très étroite, six poses ; protéger la structure verticale. |
|21|FLSM1PUR|G|SPBRNHND|Fond vert opaque index245 ; masque dérivé conditionnel, source conservée. |
|22|FLSM1RED|F|SPBRNHND|Flamme minuscule, priorité à la couverture des pixels lumineux. |
|23|LAVAFIR1|H|SPENTACI|Lave et pointes sur grande matte noire ; pas de détourage par seuil de luminance. |
|24|EXPLODE|T|SPBOOM|Explosion dense avec grains périphériques ; feather0 initial pour garder ces grains. |
|25|SPBDBUR|F|SPBRNHND|Petit impact vert clair ; pas de retrait ni feather large. |
|26|SPBDBURS|H|SPRDRABU|Neuf directions et réserves vides ; corriger le temps avant de juger la texture. |
|27|SPBURNS1|T|SPBURN|Trois cycles de feu ; préserver alternatives et couleurs, pas de concaténation. |
|28|SPFBSMAL|P|SPSPARKS|Petit jet de particules blanches ; ne pas fusionner les grains. |
|29|SPFINODI|H|SPENTACI|Éclat rose avec cœur, trait vertical et halo ; ne pas vectoriser le halo. |
|30|SPFIRE|P|SPSMPUFF|Petites bouffées espacées ; conserver séparation et placement. |
|31|SPFIRET|H|SPSCHGI|Petite boule lumineuse à bord sombre ; pas de feather supplémentaire sur le halo. RGB sigma0.|
|32|SPFLADOW|T|SPBRNHND|Grande colonne de feu, dents et particules à conserver. |
|33|SPFLSTRI|T|SPBRNHND|Colonne similaire mais BAM distinct ; aucun réemploi déduit de la seule ressemblance. |
|34|SPFSTRMI|H|SPENTACI|Feu diffus sur fond noir et dernière pose noire ; préserver la fin d'extinction. |
|35|SPPFIRAI|H|SPENTACI|Masse de feu avec bord noir ; vérifier séparément les trois cycles. |
|36|SPPFIRXI|H|SPENTACI|Grande colonne vive, régions sombres et langues fines ; ne pas éroder. |
|37|SPRDRAEX|D|SPRDRASI|Explosion feu-fumée diffuse ; feather12 plafonné par épaisseur pour garder les franges. |
|38|SPMETSWN|P|SPMETSWM|Météores et nombreuses particules ; centres/trajectoires natifs, jamais de fusion. |
|39|DSTDVL2A|D|STNKCLDD|Nuage de poussière large ;17poses visibles puis90slots transparents, ne pas étirer le mouvement sur107slots. |
|40|FALLMIST|S|SPSMPUFF|Petit nuage de31px ; feather2x4 de départ, pas12. |
|41|STEAM1|D|SPHORPUF|Grande vapeur avec zones noires ; conserver la fumée sombre, pas de neutralisation globale. |
|42|STEAM4|D|SPHORPUF|Vapeur large, même protection des creux et teintes sombres. |
|43|SPSMOLD|S|SPSMKJET|Fumée de9px de large ; feather0, chaque pose tenue trois slots. Feather0.|
|44|SPSTINK|S|SPSMPUFF|Petites volutes séparées ; feather2x4 plafonné, ne pas remplir les trous. |
|45|SPAGSCHO|P|SPSPARKS|Traînée blanche granuleuse ; masque fin sans feather12 ni vectorisation globale. |
|46|SPGREACI|H|SPENTACI|Nappe violette avec halo ; conserver la structure interne, ne pas tracer le halo en Bézier. |
|47|ACIDDTH|H|SPSCHGI|Petite flamme verte sur noir ; seuls21des63records sont utilisés par les deux cycles. RGB sigma0.|
|48|LAVABUB1|P|SPSPARKS|Quelques gouttes orange sur grand canevas ; pas de crop qui déplace les centres. |
|49|LAVABUB2|P|SPSPARKS|Gouttes minuscules puis huit poses noires ; préserver cette pause. |
|50|SPOUTA|H|SPRDRABU|Trois phases d'éruption et pauses décalées ; garder la position temporelle des apparitions. |

## Essais représentatifs conseillés avant généralisation

FIM1YEL (petit feu), SPFLADOW (grande colonne), FIRE_1GR (matte), STEAM1 (fumée sombre), SPSMOLD (fumée étroite/holds), SPMETSWN (particules), FLLGBLUE (vert), SPBDBURS (9directions/pauses). Objectif : régler les adaptations de masque, puis réutiliser les RGB acquis si seule l'alpha doit changer ; pas de nouvel appel7B/Apollo pour une retouche de masque.

Sorties envisagées : nouveaux runs spatiaux/temporels par BAM, packs mono-BAM, comparatif natif/traité avec cycles/fonds/normal-lumineux. QA utilisateur après production ; usage/propriétaire/blend/teinte/cadence à établir pour intégration ultérieure. Aucune intégration release implicite.
