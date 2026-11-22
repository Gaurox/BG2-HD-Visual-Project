# Avancement des validations projectiles — 2026-11-22

- **Clôture à 100 % confirmée le 2026-11-22.** 320/320 dispositions clôturées et 0 tâche active. `LIGHTSTO` via `XQLSTO` : `SKYBOLT` x4 visible, dessin HD confirmé par le moteur, `MAGMIS.BAM` de trajet absent. [Décision et preuve](analysis/lightsto-accepted-20261122-v1/acceptance.json).

- **Release locale alpha.8 intégrée** : renderer alpha.10, raccords/palettes et pont COW retenus ; [candidat effets/runtime](../releases/BG2-HD-Upscale/manifests/effect-release-candidates.json), [rattachements](../pipeline/recipes/effects-release-finalization-20261110-v1/integration.json). Installation et QA conservées ; déplacement reporté, qualification combinée sur jeu propre et publication toujours distinctes.

- **Lot images/raccords clôturé par l'utilisateur le2026-11-10 : [clôture](analysis/images-routes-closed-20261110-v1/README.md).** 0 travail actif identifié dans ce périmètre ; déplacement `PROJ-MOTION-001` maintenu pour plus tard. Qualification technique et portées QA conservées ; release séparée.
- **Courant : [sept cas natifs examinés](analysis/legacy-seven-usage-20261110-v1/README.md).** Conservation native justifiée, aucun pilote établi vers ces IDs dans les sources stock/installées scannées ; 0 nouveau raccord/asset/test demandé. [Deux couleurs acceptées](analysis/residual-four-colours-accepted-20261110-v1/README.md) conservées.
- Autorité technique : `index/owner-reconciliation-current.json` → `analysis/legacy-seven-usage-20261110-v1/owner-summary.json` ; décisions QA/install/release indépendantes : `index/work-tracking.json`.

| Indicateur | Compte | Avancement |
|---|---:|---:|
| Contextes graphiques explicites couverts |167 sorties réutilisables +8 masques natifs /175 |100 % production/disposition |
| Dispositions propriétaires examinées |320 /320 |100 % ;313 qualifiés +7 conservations natives |
| Contrats techniques qualifiés,PRO +IDs moteur |313 /320 |97,8 % |
| Contrats desPRO seuls |242 /243 |99,6 % |
| Familles actives àcorriger |0 |Les4exceptions précédentes sont installées. |
| Observations représentatives encore attendues |0 |SHWATER6 rouge /SPBOOM67 doré acceptés. |

-175contextes =variantes source/palette de107BAM explicites,pas175PRO. Lesbranches moteur réemploient aussi desimages déjà produites ;0nouvelle inférence identifiée.
- QA visuelle acquise sur les composants observés de 40 PRO et 12 IDs moteur. La qualification technique historique couvre 313/320 contrats (97,8 %).
- Quatre familles corrigées :SHWATER (scope +7palettes),FLMSTRK (routeSkyStrike),SPDIMDR1/2 (phases natives2→1→2),SPBOOM (range0 MPALETTE67/65/69).13IDs actifs +66 réconcilié par le même FLMSTRK ;images/PRO/registre inchangés.
- Contrôles :208textures SHA exactes,600contrats natifs avant+aprèsinstallation,31 668contrats du graphe complet passants,5/5suites CPU/GPU. Source/alpha/palette/cycles/centres/blend respectés ;copies GPU normal/additif distinctes. Correction du classement des couleurs intermédiaires surla bonne famille,testée par oracle indépendant.
- Runtime :DLL `ED9A5E4E…9132A844`,catalogue743ressources/72 563backings ;trace désactivée,INI initial retrouvé exactement. Environnement du lot du 2026-11-10 : pilotes natifs SPPR207 et SPWM110 vérifiés. Le pilote de test `override/XQLSTO.spl` a été ajouté le 2026-11-22.
- Sept cas natifs examinés :LIGHTSTO/MAGMIS ;IDs21/24/25→SPBRNHND,44→SPSMKJET,96→COLRSPRY,241→SPHOLYMT. État `reviewed-native-legacy-preserved` ;0 revue d'usage restante. SPSMKJET utilisé via action273/Hexxat et SPHOLYMT via opcode215 :effets nommés déjà couverts, pas ces anciens IDs. COLRSPRY reste stock sans production justifiée ;MAGMIS reste absent sans substitution inventée. Les7 écarts HD restent explicites ;absence de référence scannée ≠inutilisation universelle.
- SPSCORIC :qualification9cycles etaccord visuel antérieur conservés ;nouveau drawlive non revendiqué. Déplacement interpolé PROJ-MOTION-001 reporté ;release inchangée.
- Lot clos :2observations acceptées,palettes natives liéesHD,masques etphasesimpaires observés ;trace désactivée,DLL conservée. Aucun nouveau test PRO par PRO ni retest des images neutres.

## Historique àne pas utiliser comme file active

- Réconciliation initiale :299/320 (93,4%),13IDs avec4familles actives et8cas sanspilote. Nouveau raccord FLMSTRK résout aussi le66 sanspilote :reste7cas natifs distincts.
- Anciens161réemplois/54routes/27natifs du générateur source :projections conservatrices historiques,pas une liste d'images manquantes ni de tests àimposer.
- `qa=not-assessed` reste une absence de décision visuelle individuelle ;l'état technique est enregistré séparément sous `integration.automatic_reconciliation`.
