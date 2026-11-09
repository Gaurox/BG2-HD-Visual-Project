# Projectiles — passe native corrigée, 2026-11-09

- Courant : `render-summary.json` ;pointeur `../../index/native-contract-review-current.json` ;[CLUA](CLUA.md).
-33IDs moteur utilisés,21occurrences FIREBALL/14modes stock ;20modes IDS examinés avec CUSTOM. EXE `B51093A4…17A14D57`, DLL installée `009A3457…81E5C60D`,743ressources.
- **0nouvelle production IA confirmée ;10BAM installés absents du scope secondaire sur leurs classes natives spécialisées.** Raccord et contrats palettes/composition à traiter avant leur QAHD.
- Analyse seule côté jeu :0patch natif,0installation,0essai ingame. États QA/install/release de `work-tracking.json` identiques ;[nouvelle projection corrigée](../20261109-native-child-indices-v7/REPORT.md).

## Corrections de lecture du moteur

| Sujet | Preuve native et résultat | Conséquence |
|---|---|---|
| LIGHTCHA5/7/9 |227569→obj36c/36e/370 ;228d73→compteur/modulo/premier éligible→CreateVisualEffect258da0. | **Périodes d'émission, pas cycles** ;réserve «cycle9» levée ;QA V13 des traînées conservée,0image/patch/retest de ces composants. |
| SecondairePRO0x214 |226d9d lit fichier214→obj3f8 inchangé ;22f7bf fait factory(raw+1) ;factory22bf00 retire1. | PROJECTL=raw, pasraw+1. |
| ExplosionPRO0x21a |226dab lit fichier21a→obj3c4=raw−1 ;22bde2 fait factory(obj3c4+1). | PROJECTL=raw−1, pasraw ;0=aucun. |
| LIGHTCHA enfant |241 à0x21a→PROJECTL240 NEWBOLT1. | Pas SPHOLYMT241 ;aucun essai SPHOLYMT dérivé de LIGHTCHA. |
| LIGHTSTO enfant |23 à0x21a→PROJECTL22 SKYBOLT. | Pas CHROMORB23. MAGMIS primaire réellement absent ;aucun parentPRO/SPL/ITM trouvé pourLIGHTSTO92. Conserver natif ;usage dynamique non exclu. |
| FIRESTOR enfant |38 à0x21a→PROJECTL37 FIREBALL. | Pas ICE_FRAGMENTS38 ;fermeture réutilisant les images connues. |
| Anneau202 | SPKLARRE secondaire201→201/SHAREA6 ;SPKLARST secondaire202→202/SHAREA2. | Pilote vérifié **SPWM157→SPKLARST** ;SPIN560/SPWM162 ne testent pas202. |

- Correction du générateur `pipeline/scripts/projectile_tracking.py` :150arêtes/111PRO corrigées (39secondaires,111explosions).8tests unitaires passent ;preuvesRVA dans `native/child-index-conventions.asm`.
- Projectionv7 :161réemplois/contrats,54routes moteur,27natifs,1dépendance absente. Classes statiques ≠ QA ;107BAM/175contextes inchangés,167sorties réutilisables+8masques natifs,0source nouvelle.
- Les anciennes légendes d'IDs/enfants restent historiques. Les accords sur les images réellement observées restent acquis. Les états `integration=verified-static` préexistants conservent leurs références historiques ;ce correctif ne prétend pas revérifier ces anciennes fermetures.

## Autres branches résolues

| Branche | Résultat |
|---|---|
| ID13/missile14 | Factory22bf73 normalise14→4 :PROJECTL3 ARROWFLM,overrideY31P056+fuméeSPSMPUFF. QA08=tir réelXBOW15. |
| ID78 | SPFIREBL interne alloué puisobj21c=0 ;Render233f85 saute le dessin. Préserver contrôleur invisible/délai. |
| IDs80..84 | Vtable59c5e0 Render98→noop1e1e0 ;SPMAGMIS interne non dessiné. Enfant22=SKYBOLT ;factory input23 à22c761/229064. Raccord SKYBOLT avant QAHD. |
| FIREBALL |21occurrences=14modes ;BAM nommés SPBOOM/SPFIREPI/SPWRDFLD/SPGFLSH1 déjà installés. Sons et particules restent natifs. SPFIREPI déjà admis au scope ;les3autres restent à raccorder. |

## Raccords réels à préparer

`render-gaps.json/.csv` : présence catalogue et absence dans `effect_secondary_scope.h` vérifiées ;ces classes spécialisées ne passent pas par le hook primaire233f20. Le flux FX29e190→29e260→29df60 dépend du gate `effect_secondary_scope::enabled(ref)` dans `hooks.cpp`.

| Rendu | BAM concernés | Qualification avant activation |
|---|---|---|
| SkyStrike2352f0 | HLYMITE,SKYBOLT,SPGENHLA | Placement/cadence ;variantes natives HLYMITE65/194. |
| SpellHit2356b0 | SHAIR,SHEARTH,SPFDEATH | SHAIR4/SHEARTH6 pour130/137 ;adaptation indexée actuelle limitée àSHAREA. Ajouter les noms seuls ne garantit pas leurs couleurs. |
| Scorcher234520 | SPSCORIC | Géométrie/orientation du faisceau,composition. |
| Fireball1eaf90 | SPBOOM,SPGFLSH1,SPWRDFLD | Mélange/alpha,préfixes/particules ;réemploi des packs. |

-10BAM communs à plusieurs propriétaires/IDs/modes ;aucune nouvelle inférence nécessaire identifiée.
- Gate manquant prouvé statiquement ;aucune capture live supplémentaire. Ne pas déduire la couverture d'une cellule depuis le catalogue ou la QA standalone de son image.
- SPHOLYMT reste hors scope mais n'a plus de pilote dans le graphe stock corrigé ;pas un11e raccord prioritaire déduit de LIGHTCHA.
- Modes dragons15/17 :littéraux legacy absents KEY (`SPRDRDEX/SPRDRDE2`),0occurrence dans les21PRO stock ;pas de production spéculative. CFG borné aux constructeurs,ressources calculées non garanties exhaustives.

## Essais préparés et fichiers

- **QA01→QA05 disponibles maintenant** :Boule de feu,Piège à crâne,Orbe chromatique,SHAREA2 viaSPWM157,BOLT07/TSKULLNP. Les3premiers accords étaient antérieurs aux corrections du rendu.
- QA08 disponible :XBOW15→aliasARROWFLM ;QA07 optionnel :FIRESTOR→FIREBALL. QA06/SKYBOLT et10pilotes réservés :attendre leurs raccords/palettes avant acceptationHD.
- `tests-ready.json` fait autorité pour les commandes ; `tests-after-links.json` pour les pilotes futurs ;SPL/ITM actifs et offsets de capacités vérifiés contre leursSHA.
- `lightcha.json`, `lightsto.json`, `native-ids.json/.csv`, `fireball-modes.json/.csv`, `effective-PROs.json`, `native/*.asm` :contrats et limites.
- `inputs.json`, `additional-inputs.json`, `runtime-readonly-baseline.json` :sources actives, DLL/catalogue/INI ;trace détaillée laissée `false`.
- Recettes `pipeline/recipes/projectiles-native-contracts-20261109-v2/{analyse,prepare_tests}.py` ;brouillons initiaux non publiés conservés sous `.tmp/projectiles-native-20261109-v1/drafts/`.
