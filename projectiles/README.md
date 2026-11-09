# Projectiles — source, production réutilisable, travail restant

**Bilan courant : [ETAT_VALIDATIONS.md](ETAT_VALIDATIONS.md).** Les3couleurs sont acceptées,10/10omissions de scope raccordées/installées,9ressources observéesHD sur les nouvelles routes ;SPSCORIC qualifié statiquement etQA visuelle antérieure conservée. Aucun essai manuel de ce lot restant ;trace désactivée. Les étapes datées ci-dessous sont historiques,aucun retest des composants acquis àcontrat inchangé.

**Trois couleurs acceptées —2026-11-09** : [décision/traces](analysis/final-four-colours-accepted-20261109-v1/README.md). HLYMITE rouge194,SHAIR4/130,SHEARTH6/137 acceptés etpalettes natives liéesHD ;0retest. Les4dernières omissions de scope sont raccordées,neutres/faisceau qualifiés statiquement,QA antérieures réutilisées. IncidentSPWI985 expliqué :opcode168 retirela cible après2s ;ancienne consignePlayer2 corrigée,aucun défautgraphique déduit.

**Quatre derniers raccords installés —2026-11-09** : [preuve](analysis/final-four-links-20261109-v1/README.md), [3couleurs seulement](analysis/final-four-links-20261109-v1/CLUA.md). HLYMITE/SHAIR/SHEARTH/SPSCORIC admis au pontFX ;palettes réalisées natives par cellule,830textures exactes,1776contrats avant+après,5suites CPU/GPU. Neutres et9cyclesfaisceau qualifiés automatiquement ;aucun retest des6acquis.3variantes colorées en attente,trace temporaire active ;0nouvelle image/release.

**Six raccords HD acceptés —2026-11-09** : [décision et méthode de suite](analysis/native-six-links-accepted-20261109-v1/README.md). Accord visuel+drawsHD/masqués/phasesimpaires pour les6ressources ;aucun nouvel essai de ces composants demandé. Suite regroupée par contrats de rendu/variantes,contrôles techniques automatisés etpreuves partagées ;pas de campagne manuelle PROparPRO.4raccords restants en unlot :HLYMITE/SHAIR/SHEARTH/SPSCORIC.

**Six raccords natifs installés —2026-11-09** : [preuve](analysis/native-six-links-20261109-v1/README.md), [CLUA S6-01→06](analysis/native-six-links-20261109-v1/CLUA.md). SKYBOLT/SPBOOM/SPFDEATH/SPGENHLA/SPGFLSH1/SPWRDFLD admis au pont secondaire ;528textures existantes exactes,1624contrats natifs avant+après,5suites passantes. DLL `4F63EC61…18469F95`,trace temporaire active ;catalogue743/72563 etPRO/images conservés. QA du nouveaucontratHD en attente ;anciens accords visuels acquis. Restent HLYMITE/SHAIR/SHEARTH/SPSCORIC.

**Tous les essais du fichier CLUA acceptés —2026-11-09** : [décision et suite](analysis/native-clua-accepted-20261109-v1/README.md).18entrées/17pilotes distincts, y compris les10pilotes réservés, acceptés visuellement sur le rendu courant.39PRO avec QA des composants observés ;3accords historiques PFIRE2/TRAPSKUL/CHROMORB actualisés.0preuve HD nouvelle déduite :les10raccords secondaires restent ouverts. [Projectionv8](analysis/20261109-native-clua-valides-v8/REPORT.md) ;QA/installation/release distinctes.

**Passe native —2026-11-09** : [contrats et raccords](analysis/native-contracts-20261109-v2/README.md), [CLUA prêts](analysis/native-contracts-20261109-v2/CLUA.md). LIGHTCHA5/7/9=périodes d'émission, réserve «cycle9» levée ;LIGHTSTO/MAGMIS absent mais aucun pilote SPL/ITM/parentPRO trouvé. Conventions des enfants corrigées dans le suivi :secondaire=raw,explosion=raw−1 ;150arêtes/111PRO corrigées,QA acquises préservées.33IDs moteur/21appelsFIREBALL examinés :0nouvelle image confirmée,10BAM installés absents du scope secondaire sur leurs classes spécialisées. Raccord/palettes avant leur QAHD ;5essais immédiatement disponibles.0modification runtime/QA/install/release.

**Projectiles3 et COW acceptés —2026-11-09** : [QA3](../effects/batches/projectiles3-accepted-20261109-v1/README.md) — BGLRYU/SPCL236U SeedVR, SPGLYPHI xBR. [QA COW188](analysis/cow-accepted-20261109-v1/README.md) — ACOWG1 Q3m x2 déjà produit,22frames/40cycles réemployés,0inférence/interpolation. Runtime743ressources/72563backings, sprites/PRO/INI natifs conservés ; [CLUA](../effects/installations/cow-sprite-bridge-20261109-v1/CLUA.md). États QA/intégration/install explicites ; aucune QA globale243 ni release déduite.

- [Analyse de départ](analysis/20261109-finalisation-analyse-v1/README.md) historique : les3sources manquantes et le raccordCOW sont résolus ;lecture LIGHTCHA9 corrigée dans la passe native ci-dessus, LIGHTSTO et raccords des classes spécialisées restent distincts.

**QA52 acceptée — 2026-11-09** : [décision et périmètre](analysis/components-qa52-20261109-v1/README.md). 52 images acceptées le 2026-11-09 : 31 anciens effets, 18 réemplois, 3 effets 1WDC. 17 images liées à 138 PRO ; validation des composants seule. SANCTRY/SPPR109 et SPSHIELD/SPWI311 : transparence confirmée avec les vrais sorts. Packs mono-BAM figés sur les versions installées testées ; 0 inférence/interpolation nouvelle. Autres QA, installation et release préservées ; GPU en pause.

- **Suivi courant : [validations manuelles](SUIVI_MANUEL.md)**.39PRO avec acceptation visuelle limitée aux composants observés ;3anciens accords historiques actualisés par la QA CLUA ci-dessus. États explicites `index/work-tracking.json:projectiles.<PRO>.qa` ;[32décisions historiques](analysis/validations-manuelles-consolidees-20261028-v1/decisions.json) conservées. Pas de QA intégrale des243PRO déduite.
- **CourantV14 accepté : [preuve finale Projectile magique](analysis/projectile-magique-v14-valide-20261028-v1/README.md)**. 28dessinsHD/masqués,12phasesdistinctes,13dessinsimpairs,0rejet ;canevasnatifvariable64×79confirmé,0imageretraitée. Trace temporairedésactivée,jeu/loaderarrêtés ;DLLV14conservée. Aucun retestdemandé surlescomposantsobservésdecettesérie.
- **[V13 : éclairs et vol de Semence confirmés](analysis/validation-v13-20261028-v1/README.md)**. Trois traînées93dessinsHD/89masqués/50phasesimpaires ; SPFIRSE2 volHD+masque sur3dessins,phases0/2 seulement. Ne pas rejouercesdeuxessais. RéserveProjectilemagiqueV13 levée parvalidationfinaleV14.
- Matrice secondaire :37/37groupesrôle/asset avec preuve technique partagée aprèsV13, sansQAdechaquepropriétaire/palette/cycle ni fermetureglobale243. SPMAGMISV14confirmé ;contratspropriétairesnonexercés,nouveauxassetsmanquants et déplacementrestentdistincts.
- **100chaînes vérifiées statiquement** conservées séparément. [Audit243](analysis/audit-complet-243-20261028-v1/README.md) :100complètes,124partielles,13natives,4avec images manquantes,LIGHTCHAcontrat à examiner,LIGHTSTOdépendance absente. Cet audit historique ne constitue pas une QAingame générale.
- **Déplacement reporté** : [PROJ-MOTION-001](../pipeline/PROBLEMES_A_RESOUDRE.md#proj-motion-001), [étude](analysis/deplacement-generalise-etude-20261028-v1/README.md). Animation des images ≠ interpolation des coordonnées ; aucune position intermédiaire ajoutée.
- Preuves/anciennes corrections : [répertoire de reprise](REPRISE_LIAISONS124.md). Ne pas redemander les validations acquises ; conserver les limites de propriétaire/palette/cycle et les états production/QA/installation/release distincts.

- Entrée : [SUIVI.md](SUIVI.md) ; détail par PRO : [work-items.csv](index/work-items.csv).
- Demande2026-10-18 : analyser tous les projectiles, distinguer le vrai travail des images déjà produites ; ne pas lancer de production en double.
- `index/resources.csv`, `dependencies.csv`, `manifest.json` : inventaire source stock ; conservé.
- Les graphismes de projectile restent produits dans `effects/` ; pas de second pipeline ou de copie des mêmes textures sous `projectiles/`.

| État | Autorité / preuve |
|---|---|
| Source | KEY/BIF + source PRO/BAM/SHA ; `index/resources.csv` |
| Image produite/acceptée | Autorités effets, animations ou sprites ; liens explicites dans `contexts.json` |
| Intégration de chaque PRO | `index/work-tracking.json:projectiles.<RESREF>.integration` + référence locale |
| QA de chaque PRO | Même fichier, `.qa` + décision explicite/preuve ; aucune promotion depuis la QA d’un BAM |
| QA des images partagées | Même fichier, `.component_visual_qa.<lot>` : `accepted-assets-only`, assets et preuve effets ; ne modifie pas `.qa` du PRO |
| Installation | Même fichier, `.installation` + reçu propre au périmètre ; catalogue seul = observation distincte |
| Release | Même fichier, `.release` + référence explicite ; aucune déduction depuis les autres états |

## Anti-doublon

- Clé image : BAM décompressé canonique (pixels/palette/indices/centres/cycles) + SHA palette RGB réalisée pour le consommateur.
- Alias source exact : réutilisation ; exemple SPIPLARI/SPIPLAAI. Une égalité d’image ne valide pas le contrat de chaque propriétaire.
- Même BAM / plusieurs palettes : sorties explicites distinctes ou représentation dynamique ; ne pas figer une couleur pour tous les PRO.
- Un résultat spatial suffit à interdire un second job spatial identique ; reprendre temporalité/pack si nécessaire.
- PRO/VVC/VEF, tables de palettes, sons, vitesse/rayon, particules moteur : aucun upscale IA autonome.
- Masques noirs : conserver natifs ; les effets visibles entièrement noirs ne sont pas des images RGB à halluciner.
- Images natives identiques et ancrées repérées entre nouvelles sources et sorties déjà représentées : pistes explicites dans l’analyse ; pas d’équivalence inventée entre canevas d’inférence différents.

## Utilisation

```powershell
python -B pipeline/scripts/projectile_tracking.py status
python -B pipeline/scripts/projectile_tracking.py queue --action new-context-required
python -B pipeline/scripts/projectile_tracking.py queue --action reuse-existing-output
python -B pipeline/scripts/projectile_tracking.py refresh --snapshot AAAAMMJJ-vN
python -B -m unittest discover -s pipeline/tests -p test_projectile_tracking.py
```

- `status`/`queue` : lectures seules, sans jeu/GPU, ni scan de pixels.
- `refresh` : analyse source/autorités en lecture, écrit seulement un nouvel instantané `analysis/<id>/` + projections de ce domaine. Aucun worker d’inférence/compilation/installation lancé.
- Historique immuable ; nouveau nom obligatoire. `index/work-analysis-current.json` identifie la projection courante et ses SHA.
- Décisions manuelles dans `index/work-tracking.json`, pas dans les CSV régénérés. Espaces `projectiles.<RESREF>` et `engine_projectiles.<ID_décimal>`. Champs optionnels : `priority` (entier), `notes`, `historical_evidence` (liste), puis `integration`, `qa`, `installation`, `release` (objets `state`, `evidence`).
- Une valeur `not-assessed` marque l’absence de décision pour ce PRO, même si certaines images ont une QA acquise.
- `analysis/<id>/` : `analysis.json` (contrats natifs/entrées/SHA/limites), `contexts.json` (palettes/usages/candidats), dépendances développées, liens PRO, usages SPL/ITM, jobs de palette, IDs moteur et rapport figé.
- Les fichiers d’index effets peuvent évoluer pendant un lot : régénérer l’analyse après son avancement ; ne pas prendre un ancien snapshot pour un état temps réel.
- `status`/`queue` signalent les entrées modifiées depuis l’instantané et refusent les projections CSV modifiées manuellement. Aucun suivi interdomaines n’est réécrit.
- Les tâches par propriétaire listent les risques à résoudre pour un nouvel usage ; elles n’imposent ni une campagne de retests de 243 PRO ni une remise en cause des QA acquises.
