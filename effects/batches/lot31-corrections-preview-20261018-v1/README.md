# Lot31 — corrections demandées, aperçu2026-10-19

- Autorisation :10effets ReboutCX+lissage,13lissage seul,12/20chronologie+noir transparent,30chronologie+lissage,14noir transparent.24/25/28/29 conservés.
- Résultat :27BAM/95contextes corrigés ; comparatif31BAM/99contextes,9968phases/658profils. [Synthèse](result.json), [vérification](verification.json), [plan exact](plan.json).
- [Galerie](http://127.0.0.1:8794/?v=corrections31) : vanilla/précédent/correction, horloge/cadrage communs ; palette/cycle/mode/phase/zoom/alpha/fond/mélange sélectionnables.30/31 démarrent en boucle. Les vues natives utilisent la même base15FPS de compatibilité ; aucune mesure ingame supplémentaire déduite.
- ReboutCX :10BAM/41palettes, modèle x4 FP16 ; entrées natives recolorées avant inférence, remplissage RGB du transparent par plus proche opaque, alpha traité séparément. Manifestes `reboutcx/*/manifest.json` ; autres effets RGB précédents conservés sauf réinterpolation12/20/30 et conversion transparente12/14/20.
- Masques24BAM : méthode SPDEATH3, Potrace alphamax1.334/opttol0.1/turdsize0/SS8 sans clamp nearest ; poses natives tracées avant interpolation alpha. Fondu Gaussian du contour seul, sigma≤4x4 adapté localement0.5..4 pour préserver traits fins ; aucun retrait. RGB existant exact en zone commune pour lissage seul. `masks/*/report.json` : aucune composante native totalement effacée. Topologie tous seuils non garantie.
-12 SPRDRABU :9cycles20slots,8poses visibles puis12slots vides.20 SPNPOISI :40slots,20poses visibles puis20slots vides. Ancienne méthode étirait les poses visibles sur les réserves invisibles. Nouveau temps : ancres natives conservées, Apollo15→30 sur entrées adjacentes distinctes puis réinsertion des véritables holds. En once,12vide dès8/15s et20dès20/15s ; durée totale20/15s et40/15s. Une image vide stockée et référencée plusieurs fois : pas de mouvement inventé pendant une pause native.
-30 SANCTRY :12poses actives distinctes6..17 ;0..5 inutilisées, pas de double actif exact à retirer. Nouvelle interpolation15→30 incluant dernière→première en boucle ; ancien aperçu rejouait la variante once, provoquant une coupure. Durée12/15s conservée. `timing-audits/` : ancres/inputs/rationnels.
-12/14/20 : noir neutre encodé dans l'alpha (`A'=round(A*max(RGB)/255)`, RGB droit renormalisé depuis flux prémultiplié). Noir exact RGBA0 ; énergie lumineuse conservée≤1octet, encodages droit/prémultiplié vérifiés. Pas de clé noire globale appliquée aux autres assets.
- Géométrie : marge20px x4 (=5x1) commune, centre+5x1 ; positions monde inchangées. Futur carrier/pack devra encoder cette marge. Données candidates `rgba/` +`results/*.json` ; pas de pack runtime/index/QA/install/release changé par cet essai. Productions historiques et installation restent distinctes. Sources et manifestes parents vérifiés.
- Vérification :99contextes, tous profils/durées exacts ; RGBA/hash/PNG, prémultiplication, bords transparents, RGB lissage seul, alpha reconstruit, noirs et pauses natives. Doublons temporels permis seulement pour pause native/image vide. `verification/*.json`.
- Recette : `pipeline/recipes/effects-lot31-corrections-20261018-v1/`. Fichiers ignorés (RGBA,PNG,NPZ,entrées Apollo) restent dans ce dossier ; aucune purge.

|N°|BAM|Palettes|Correctif|
|---|---|---|---|
|01|ARARROW|11|ReboutCX x4, Bézier +fondu alpha|
|02|AXE|6|ReboutCX x4, Bézier +fondu alpha|
|03|BOLT|13|ReboutCX x4, Bézier +fondu alpha|
|04|DAGGER|2|ReboutCX x4, Bézier +fondu alpha|
|05|DART|4|ReboutCX x4, Bézier +fondu alpha|
|06|SPEAR|1|ReboutCX x4, Bézier +fondu alpha|
|07|TRDARTST|1|ReboutCX x4, Bézier +fondu alpha|
|08|ACIDBLOB|5|Bézier +fondu alpha|
|09|MAGICSTN|8|Bézier +fondu alpha|
|10|SPFIREBL|2|Bézier +fondu alpha|
|11|SPFLMARR|4|Bézier +fondu alpha|
|12|SPRDRABU|2|temps natif, noir transparent|
|13|STNKCLDT|13|Bézier +fondu alpha|
|14|TRAVEL|10|noir transparent|
|15|WEBENTT|1|ReboutCX x4, Bézier +fondu alpha|
|16|BDETHREA|1|Bézier +fondu alpha|
|17|SPGREAAI|1|Bézier +fondu alpha|
|18|SPGREAXI|1|Bézier +fondu alpha|
|19|SPIMPPT|1|Bézier +fondu alpha|
|20|SPNPOISI|1|temps natif, noir transparent|
|21|SPRMPARI|1|Bézier +fondu alpha|
|22|SPSCHGI|1|Bézier +fondu alpha|
|23|GLPHWRDH|1|ReboutCX x4, Bézier +fondu alpha|
|24|GREASED|1|conservé|
|25|GREASEH|1|conservé|
|26|SKLH|1|ReboutCX x4, Bézier +fondu alpha|
|27|SPENTACI|1|Bézier +fondu alpha|
|28|WEBENTD|1|conservé|
|29|WEBENTH|1|conservé|
|30|SANCTRY|1|Bézier +fondu alpha, temps natif|
|31|SPSHIELD|1|Bézier +fondu alpha|
