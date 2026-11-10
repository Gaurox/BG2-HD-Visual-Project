# Sept cas natifs — revue d'usage 2026-11-10

- Demande : `fais le 1 (7 cas)` ; décision : **conserver les sept routes natives**, sans production/raccord/test spéculatif.
- [Décisions par propriétaire](decisions.json) ; [synthèse propriétaires](owner-summary.json) ; [vérification](verification.json).
- **320/320 dispositions examinées (100 %) = 313 contrats qualifiés + 7 conservations natives justifiées. Qualification technique inchangée : 313/320 (97,8125 %).** Aucune nouvelle validation visuelle ; les sept écarts HD restent consignés dans `owners.json:errors`.
- 0 pilote vers les sept IDs dans les sources scannées ; 0 revue d'usage restante, 0 nouveau job/raccord/test manuel. Réouvrir seulement si un pilote réel est identifié ou si sources/configuration changent.

| Propriétaire / PROJECTL | Image | Résultat / décision |
|---|---|---|
| LIGHTSTO / 92 | MAGMIS | BAM absent KEY + override ; aucun pilote entrant établi. Conserver le PRO ; ne pas inventer MAGMIS ni lui substituer SPMAGMIS. Appel de la foudre normal : SPPR302 → contrôleurs80..83 →22/SKYBOLT. |
| moteur21 | SPBRNHND | Constructeur ancien sans pilote établi. Image déjà produite/acceptée/cataloguée ; alias BAM natif exact BURNHAND. Mains ardentes normal : SPWI103 →340/BURNHAND. |
| moteur24 | SPBRNHND | Ancien cône, helper natif0x227800 ; aucun pilote établi. Cône de froid normal : SPWI503 →249/CONECOLD. Pas de doublon de production. |
| moteur25 | SPBRNHND | Ancien cône recoloré, même helper ; aucun pilote établi. Conserver le comportement natif ; aucune palette/règle secondaire ajoutée sans consommateur. |
| moteur44 | SPSMKJET | Aucun pilote PROJECTL44 établi. **Six appels action273** dans HEXXAT/HEXXA25 utilisent l'image comme effet visuel nommé ; route distincte, image déjà acceptée/cataloguée, scope VVC existant. |
| moteur96 | COLRSPRY | BAM stock présent, aucun pack installé ni pilote établi. Vaporisation prismatique normal : SPWI105 →248/CSPRAY. Conserver stock ; pas de génération sans usage réel. |
| moteur241 | SPHOLYMT | Aucun pilote PROJECTL241 établi. **SPIN629 opcode215** et dispatcher natif0x3c0aa1 →0x3c0dbb/op215 utilisent l'image comme effet nommé ; image acceptée/cataloguée, scope VVC existant. |

## Portée vérifiable

- PROJECTL est indexé depuis0 ; champ missile des capacités = ID+1. Enfants PRO : secondaire=raw, explosion=raw−1. Références par noms d'images ≠ lancements de ces IDs.
- [Stock](summary.json) : 1648 SPL,2867 ITM,559 EFF,243 PRO,4735 CRE,423 ARE,4 CHR,1 GAM ;4358 BCS/66 136 actions,2884 DLG ;VVC/VEF/2DA inclus. [Actif](active/summary.json) : mêmes ressources avec tous les overrides pertinents, dont1650 SPL,4937 CRE,2505 VVC. Aucun répertoire de sauvegarde joueur lu.
- Capacités, enfants PRO, effets V1/V2 (dont CRE/CHR et provenance0xa0), traps ARE, actions compilées et noms exacts examinés ;140:8 /141:1392 /327:0 /339:0. **0 référence ciblée,0 provenance ciblée,0 avertissement** dans les deux scans. Empreintes individuelles : `inputs.json`, `active/inputs.json`.
- [Exécutable](native-review.json) fixé par SHA `B51093A4…4D57` :29 références directes à la factory0x22bf00 ;6 références littérales pertinentes ;helper cône appelé uniquement par24/25. Aucun argument immédiat local vers les sept IDs trouvé. Assembleur ciblé sous `native/`.
- Branche supplémentaire SPHOLYMT : prépare un effet215, pas un projectile241. Route VVC actuelle contrôlée dans `hooks.cpp:detour_vvc_vid_cell_render` ; elle utilise les ressources enregistrées sans filtre secondaire projectile. Cela qualifie la distinction de route, **sans prétendre à une nouvelle observation HD ingame**.
- Trois sélections existantes SPBRNHND/SPSMKJET/SPHOLYMT : décisions QA et manifests SHA conformes ;ressources/cycles/nombre de frames/run installés concordants. SPBRNHND et BURNHAND ont des BAM décompressés identiques ;identités dans `decisions.json:images`.
- DLL `ED9A5E4E…9132A844`,INI `AB4A3C30…6D8B0D`,catalogue `4ED0F7CD…5B5B9` relus conformes ;0 écriture jeu. QA/install/release du suivi conservées, anciens rapports immuables ;seuls les sept champs d'intégration et pointeurs courants changent.

## Limites / reprise

- Absence dans les données stock/overrides scannés ≠ preuve universelle d'inutilisation. Fenêtres de registres locales ≠ analyse de flux complète de tout l'exécutable. Paramètres runtime optionnels, console, sauvegardes, futurs mods ou autre client multijoueur peuvent introduire un ID.
- Conservation native = décision de périmètre, **pas qualification HD ni accord visuel**. Les graphismes employés par d'autres routes conservent leurs autorités antérieures ;aucune QA de propriétaire extrapolée.
- Restent séparés : interpolation des positions `PROJ-MOTION-001` reportée ;release non demandée.
- Recette : `pipeline/recipes/projectiles-legacy-seven-20261110-v1/` ;`scan.py <nouveau-dossier> [--stock-only]` refuse un dossier existant. `native_review.py`/`publish_review.py` figent cette version et refusent de la réécrire ;adapter vers une nouvelle version pour une reprise.
- Références format : [BCS](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/bcs.htm), [CRE](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/cre_v1.htm), [ARE](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/are_v1.htm), [actions272/273](https://gibberlings3.github.io/iesdp/scripting/actions/bgeeactions.htm#273), [opcode339](https://gibberlings3.github.io/iesdp/opcodes/bgee.htm#op339). Conventions effectives des IDs/dispatchers confrontées à l'exécutable fixé ci-dessus.
