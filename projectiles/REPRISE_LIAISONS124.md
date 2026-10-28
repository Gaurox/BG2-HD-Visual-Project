# Reprise — projectiles déjà produits, 2026-10-28

## État courant après validation V14

- [Suivi manuel](SUIVI_MANUEL.md), `index/work-tracking.json:qa` :29PRO acceptés pourlescomposantsobservés,3décisionshistoriquesavantcorrectif conservées.100chaînes `integration=verified-static` distinctes ;pasQAcomplète243/124/release.
- **[SPMAGMISV14 accepté](analysis/projectile-magique-v14-valide-20261028-v1/README.md)** :28dessinsfinauxHD+masque,12phases0..11,13dessinsimpairs,0rejetmasque/composition,0traceDropped. Canevas64×79réelcompatibleavecsource64×64extraiteenmémoiredupack64×78 ;aucuneimageretraitée.
- DLLV14 activeSHA393820D32FFC94E20E50D0DD27B6511C19EA1994B64AF3444BE75AA434987912 ; [reçu](../engine/InfinityEngine-Enhancer/installations/projectiles-mask-canvas-20261028-v14/installation.json), [trace temporaire désactivée](analysis/projectile-magique-v14-valide-20261028-v1/trace-disabled.json) aprèscaptureetarrêtjeu/loader. AutresoctetsINI conservés,117PROoverrideinchangés,538ressources/62500backings,0release.
- [Éclairs/volSemenceV13 confirmés](analysis/validation-v13-20261028-v1/README.md). SPCHLGT1/2/3 :93dessinsHD/89masqués/50impairs,3chargementsCPUinitiauxsuivisdesuccès. SPFIRSE2 :3HD/2masqués,phases0/2seulement,pasdecadence/phaseimpairemesurée. Ne pasredemandercesessais.
- Matrice37/37groupesrôle/assetavecpreuvepartagée :pasuneacceptationdetousleursPRO/profils/palettes/cycles. Aucun nouveau test demandé surlescomposantsobservésdecettesérie.

## Restes séparés de cette acceptation

- TSKULLNP,enfantSHAREA202etvaleur9déclaréeLIGHTCHA :contrats/pilotesnonexercés ;aucuneQAglobalepropagée. Dernièrestracesd'éclairsséquences5/7,pasdeséquence9crééeartificiellement.
- ImagesnonproduitesBGLRYU/SPCL236U/SPGLYPHI,dépendanceMAGMIS :horscampagnedevalidationdesproductionsdéjàexistantes.
- Déplacement **reportéparutilisateur** : [PROJ-MOTION-001](../pipeline/PROBLEMES_A_RESOUDRE.md#proj-motion-001), [étude](analysis/deplacement-generalise-etude-20261028-v1/README.md). Animationdesimages≠positionsinterpolées ;aucunprototypeinstallé.
- QAhelpersXQTARG.CRE/XQSEED.SPL/XPGREEN.SPL restentisolés,aucunoriginalremplacé. Nettoyagefutur seulementjeu/loaderarrêtésetSHAconformeauxreçusV12/feuvert,s'ilsneserventplus.

## Preuves acquises et corrections conservées

| Périmètre | Preuve / limite |
|---|---|
| Feu vert | [FIREBGRT/X/R HD+masque, aspect accepté](analysis/feu-vert-valide-20261028-v1/README.md) ; XPGREEN pilote isolé, pasQA propriétaireFBFLAMGR |
| Piège / zone sauvage | [SPSETSCD/SPSETSH/SPFLAMES/SPGRWHRL acceptés](analysis/piege-zone-sauvage-valides-20261028-v1/README.md) ; condition ennemi requise pour piège |
| Mur brouillard / rouge | [V10 acceptée](analysis/mur-brouillard-v10-valide-20261028-v1/README.md), [correspondance alias](analysis/mur-brouillard-alpha-20261028-v1/alias-correspondence.json) ;0image retraitée,2683backingsSHA/2168accès sémantiques vérifiés |
| V8/V9 palettes/vols | [cinq essais acceptés](analysis/sharea-palettes-validees-20261028-v1/README.md), [phases TRAVEL confirmées](analysis/vol-animation-mouvement-20261028-v1/README.md) ;5palettes distinctes, preuve de cadence commune limitée |
| Variantes / cônes / souffles | [SPWI953/SPCL239/SPDD03](analysis/validation-variantes-20261028-v1/README.md), [SPCL239 isolé](analysis/validation-spcl239-isole-20261028-v1/README.md), [quatre cônes/souffles](analysis/validation-suite-cones-souffles-20261028-v1/README.md) ; décisions finales dans suivi manuel |
| Nuages | [CLOUDKIL V4](analysis/nuage-valide-v4-20261028-v1/acceptance.json), [CLOUD/1PDEATHF V6](analysis/nuages-v6-valides-20261028-v1/README.md), [WRITHING V7](analysis/writhing-v7-valide-20261028-v1/README.md) ; transparences acceptées |
| Crâne/orbe / Boule de feu | [V5 technique](analysis/composition-retest-v5-20261028-v1/README.md), [FIREBAT V3 technique](analysis/boule-de-feu-retest-v3-20261028-v1/README.md) ; accords visuels avant correctif gardés comme historiques, pas de nouvel accord déduit |
| Lot124 initial | [recette](../pipeline/recipes/projectiles-secondary-links-20261028-v1/README.md), [124candidats](analysis/liaisons124-20261028-v1/124-candidate-routes.csv) ; correctifs partiels, pas124QAglobales |

- XPGREEN.SPL reste un pilote de test installé ; aucun original remplacé. Nettoyage futur uniquement jeu/loader arrêtés etSHA conforme à [son reçu](analysis/validation-feu-vert-20261028-v1/installation.json).
- Ancienne demande d'arrêtPC : après coordination avec chat `Documenter les bâtiments du triangle` (`01a17feb-6c66-7c10-88cc-68d79706d5d5`) ; un seul arrêt à coordonner, pas d'arrêt pendant les essais actifs.
