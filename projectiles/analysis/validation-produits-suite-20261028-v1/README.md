# Suite validation — productions existantes seulement

- Demande utilisateur28octobre : poursuivre les validations des éléments déjà traités, exclure les nouveaux travaux d'image. Aucun job IA, nouvelle installation, modification PRO/image/release.
- `owners-243.csv` :100chaînes complètes validées techniquement sans100retests individuels (`technical-100.json`, décision enregistrée dans `index/work-tracking.json:integration`, QA visuelle séparée) ;128PRO avec des composants produits à poursuivre ;13purement natifs sans jobHD ;2dispatch natifs sans image explicite à identifier. Les6cas mixtes (4images manquantes/LIGHTSTO/LIGHTCHA) restent dans les128, mais seules leurs parties déjà produites sont éligibles aux essais.
- Exclusions d'image : BGLRYU/SPCL236U/SPGLYPHI, dépendance absenteMAGMIS. Leur absence ne bloque pas l'étude des parties déjà produites des mêmes chaînes, sans clôturer abusivement le PRO complet.
- Preuves acquises conservées : FIREBAT,nuageX58CLK,volSKLT/SPCHRORB,bindsSKLH,insectes/glace/éclairs séquence2. Aucun retest systématique de ces chemins. Une preuve d'un composant commun ne vaut pasQAvisuelle de tous ses propriétaires/palettes.
- `secondary-groups.csv` :37groupes rôle/asset produits restant historiquement partiels ou à revoir ; preuves communes acquises liées, tests ciblés proposés quand disponibles.14groupes n'ont pas encore de commande sélectionnée ni de preuve commune : chercher SPL/ITM/dispatch/driver explicite, ne pas inventer de commande de sort. Ce plan de16tests n'est donc pas une clôture automatique des128PRO.
- `tests.csv`/`tests.json` :16sorts en4vagues, référencesSPL actives/hash/champs projectile vérifiés sur l'installation actuelle. **Seule vague1 demandée maintenant** ; suivantes à adapter aux résultats, pas à jouer d'un bloc.
- `wave1-log-baseline.json` sépare les nouveaux événements des essais précédents ; conserver les prochains logs dans un nouveau dossier de preuve.

## Vague1 — quatre nouveaux chemins

Partie de test,2personnages éloignés. Lancer séparément surPlayer2 ; laisser les zones persistantes disparaître. Observer fond opaque/rectangle, transparence, dispersion, continuité et disparition. Noter simplement « nom du sort : OK / défaut ». Refaire uniquement un cas douteux si nécessaire, pas tous par défaut.

| Sort | Commande | Composants déjà produits à observer |
|---|---|---|
| Nuage puant | `C:Eval('ForceSpellRES("SPWI213",Player2)',0)` | SPCLOUDS : fond et transparence |
| Brume mortelle | `C:Eval('ForceSpellRES("SPWI614",Player2)',0)` | SPDFOGA : transparence et contour |
| Nuage incendiaire | `C:Eval('ForceSpellRES("SPWI810",Player2)',0)` | SPINCINA : feu/fumée persistants |
| Flétrissure abominable | `C:Eval('ForceSpellRES("SPWI812",Player2)',0)` | SPHORWIL/SPHORWIA : impact et dispersion |

- Les autres variantes de nuages ne sont pas déduites validées depuisX58CLK ; les anciennes sorties binairesalpha et leurs variantes corrigées restent distinctes. Vérifier le resref réellement dessiné avant de choisir la variante existante adaptée.
- À réception du retour : figer les nouveaux logs, rapprocher les quatre sorties attendues de `EFX_NATIVE_SURFACE`,0x8/0x20,`EFX_MASK_FALLBACK`,`EFX_COMPOSITE_REJECT`, puis validation visuelle ciblée ou correction de liaison. Les phases finales détaillées ne sont journalisées que pourFIREBAT/SPSMPUFF/X58CLK/SKLT/SPCHRORB ; ne pas inventer de cadence mesurée pour les autres.

## Vagues suivantes, non encore demandées à jouer

- Vague2 : Brouillard putride/SPPR250,Feu spirituel/SPPR450,Aube illusoire/SPPR609,Comète/SPWI925 — autres spreads/impacts existants.
- Vague3 : Ralentissement/SPWI312,Sommeil/SPWI116,Délivrance magie/SPWI302,Manteau terreur/SPPR416,Bénédiction/SPPR101 — dispatchSHAREA197–201. Palette/raccord secondaire à vérifier techniquement avant conclusionHD ; pas de nouvelle image requise. Enfant202sansSPLdirect vérifié reste séparé.
- Vague4 : Malédiction Séluné/SPWI953,Faisceau conscience solaire/SPCL239,Souffle/SPDD03 — variantes colorées/anneau/cône.
- Compléments : TSKULLNP n'a pas deSPLdirect repéré ; évaluer la réutilisation statique du cheminSKLT ou un driver vérifié. Cycle9LIGHTCHA : examiner la sémantique native avant d'imposer de multiples tests d'angle. Armes/BOLT2/enfants natifs : drivers et items précis à sélectionner après ces vagues.
