# Validations manuelles des projectiles — 2026-11-22

**Dernier essai, `LIGHTSTO` — 2026-11-22.** Sort de test `XQLSTO`, éclair enfant `SKYBOLT` x4 accepté et confirmé par le journal moteur. `MAGMIS.BAM` absent, trajet non attesté. 0 essai restant. [Preuve et clôture à 100 %](analysis/lightsto-accepted-20261122-v1/acceptance.json).

**Lot images/raccords clôturé2026-11-10 : [clôture utilisateur](analysis/images-routes-closed-20261110-v1/README.md).** 0 essai manuel restant ;accords et limites de QA antérieurs conservés. Déplacement reporté,release séparée.

**Revue des7 cas natifs2026-11-10 : [décisions](analysis/legacy-seven-usage-20261110-v1/README.md).** Conservation native après recherche de pilotes stock/override et revue ciblée moteur ;0 test manuel supplémentaire,0 nouvel accord visuel déduit. Qualification technique313/320 conservée ;320/320 dispositions examinées. Réouvrir seulement sur identification d'un usage réel ou changement des sources ;les anciens essais ci-dessous ne sont pas à rejouer.

**État final2026-11-10 : [R4-01/R4-02 acceptés](analysis/residual-four-colours-accepted-20261110-v1/README.md).** SHWATER6 rouge/138 etSPBOOM67 doré/142 validés visuellement avecpreuves palette+HD+masque+phasesimpaires.0test manuel restant,trace désactivée ;anciensaccords conservés.39PRO +12IDs avecQA descomposants observés ;les instructions d'essais ci-dessous sont historiques,aucun retest demandé.

**Courant2026-11-10 : [2 essais de couleur uniquement](analysis/residual-four-20261110-v1/CLUA.md).**4familles résiduelles corrigées/installées ;SHWATER6 rouge etSPBOOM67 doré demandent uneobservation représentative. FLMSTRK etSPDIMDR1/2 qualifiés statiquement sansnouvel essai visuel. Anciens accords acquis,trace temporaire active ;ne pas rejouer leslots historiques ci-dessous.

**Réconciliation technique2026-11-10 : [4 exceptions actives](analysis/owner-contracts-20261110-v1/README.md).** Preuves communes reliées aux320 propriétaires,299 contrats compatibles ;aucun accord visuel élargi ou révoqué. SHWATER,FLMSTRK,SPDIMDR1/2,SPBOOM recoloré demandent un travail technique avant toute nouvelle observation utile ;**0 nouveau test manuel préparé**,0 campagne PRO par PRO. Les8 écarts sans pilote scanné restent natifs.

**État courant2026-11-09 : [bilan des validations](ETAT_VALIDATIONS.md).**39PRO et10IDs moteur avec accords visuels bornés aux composants observés. Les10raccords secondaires repérés sont installés :6routesHD acceptées+3couleurs acceptées ;SPSCORIC qualifié statiquement9cycles etaccord visuel antérieur conservé.0test de couleur en attente,trace désactivée. Les mentions «raccords ouverts» ci-dessous décrivent les étapes historiques.

**Mise à jour2026-11-09** : [tous les essais CLUA acceptés](analysis/native-clua-accepted-20261109-v1/README.md),18entrées/17pilotes distincts.39PRO avec acceptation des composants observés ;PFIRE2/TRAPSKUL/CHROMORB confirmés sur le rendu courant. Les10pilotes secondaires sont aussi acceptés visuellement, sans nouvelle preuve de substitutionHD ;leurs raccords restent ouverts. Commandes/sources/runtime figés dans `acceptance.json` ;aucune installation/release modifiée.

**Correction technique2026-11-09** : [passe nativev2](analysis/native-contracts-20261109-v2/README.md). Les légendes d'enfants/IDs ci-dessous sont historiques :PRO0x214 donne PROJECTL=raw,0x21a donne PROJECTL=raw−1. LIGHTCHA5/7/9 sont des périodes, pas des cycles. Les retours sur les images réellement observées restent acquis ;aucune nouvelle validation ni révocation QA déduite de cette correction du graphe.

**QA52 acceptée — 2026-11-09** : [décision et périmètre](analysis/components-qa52-20261109-v1/README.md). 52 images acceptées le 2026-11-09 : 31 anciens effets, 18 réemplois, 3 effets 1WDC. 17 images liées à 138 PRO ; validation des composants seule. SANCTRY/SPPR109 et SPSHIELD/SPWI311 : transparence confirmée avec les vrais sorts. Packs mono-BAM figés sur les versions installées testées ; 0 inférence/interpolation nouvelle. Autres QA, installation et release préservées ; GPU en pause.

- Autorité par PRO : [`index/work-tracking.json:qa`](index/work-tracking.json). [Décisions figées](analysis/validations-manuelles-consolidees-20261028-v1/decisions.json), [validation finale V14](analysis/projectile-magique-v14-valide-20261028-v1/acceptance.json).
- 39PRO avec acceptation visuelle des composants observés ;3anciens accords historiques confirmés par le lotCLUA2026-11-09. Ces nombres ne sont pas des chaînes intégrales acceptées.
- 100 chaînes `integration=verified-static` conservées : validation technique distincte, pas 100 essais visuels ajoutés. Production/installation/release inchangées par cette consolidation.
- États : `accepted-observed-components` = accord utilisateur limité aux effets vus ; `historical-visual-acceptance-runtime-changed` = accord antérieur au correctif de rendu ; `accepted-historical-asset` = ancien accord asset, contrat courant à examiner.
- Matrice secondaire :37/37groupes avec preuve technique partagée aprèsV13, sansacceptationglobale de tousleurspropriétaires ; SPMAGMIS resteencontrôleV14 séparé.

| PRO | Essai | Composants acceptés visuellement | État visuel | Preuve technique / limite |
|---|---|---|---|---|
| CLOUDKIL | Nuage mortel / SPWI502 | SPCLOUDK→X58CLK | Accepté, portée observée | HD/masque et phases impaires confirmés ; transparence acceptée. |
| CLOUD | Nuage puant / SPWI213 | SPCLOUDS→X58CLS | Accepté, portée observée | HD/masque et phases impaires confirmés ; transparence acceptée. |
| 1PDEATHF | Brume mortelle / SPWI614 | SPDFOGA→X58DFOG | Accepté, portée observée | HD/masque et phases impaires confirmés ; transparence acceptée. |
| 1PINCIND | Nuage incendiaire / SPWI810 | SPINCINA | Accepté, portée observée | HD/masque observés ; pas de cadence complète mesurée. |
| PWILT | Flétrissure / SPWI812 | SPHORWIL, SPHORWIA | Accepté, portée observée | HD/masque observés ; pas de cadence complète mesurée. |
| WRITHING | Brouillard putride / SPPR250 | WRITHING→X28WRTH | Accepté, portée observée | HD/masque et phases intermédiaires confirmés ; profil normal accepté. |
| BDSPFIRE | Feu spirituel / SPPR450 | BDSFIRET, BDSFIREH, BDSFIREA | Accepté, portée observée | Textures HD liées ; masques selon les événements disponibles, pas de mesure par phase complète. |
| FDAWN | Aube illusoire / SPPR609 | FDAWNX, FDAWNA | Accepté, portée observée | Textures HD liées ; masques selon les événements disponibles, pas de mesure par phase complète. |
| COMET | Comète / SPWI925 | SPCOMTRV, SPCOMEXP | Accepté, portée observée | Textures HD liées ; masques selon les événements disponibles, pas de mesure par phase complète. |
| FIREBLIC | Malédiction de Séluné / SPWI953 | FIREBICT, FIREBICX, FIREBICR | Accepté, portée observée | HD/masque observés ; tentatives de lookup 24×16 du vol conservées comme limite. |
| SPCL239 | Faisceau de la Conscience Solaire / SPCL239 | SPCL239X, SPCL239R | Accepté, portée observée | HD/masque confirmés par essai isolé ; retour visuel positif antérieur conservé. |
| DDBREAT | Souffle / SPDD03 | HDFBRER | Accepté, portée observée | Anneau HD/masque observé ; pas de validation globale des sous-projectiles. |
| SPARBLNP | Ralentissement / SPWI312 | Anneau SHAREA avec palette native, vol observé | Accepté, portée observée | Cinq palettes liées HD ; preuve des phases de vol commune TRAVEL, pas cinq mesures de cadence. Déplacement non interpolé. |
| SLEEP | Sommeil / SPWI116 | Anneau SHAREA avec palette native, vol observé | Accepté, portée observée | Cinq palettes liées HD ; preuve des phases de vol commune TRAVEL, pas cinq mesures de cadence. Déplacement non interpolé. |
| SPARGRNP | Délivrance de la magie / SPWI302 | Anneau SHAREA avec palette native, vol observé | Accepté, portée observée | Cinq palettes liées HD ; preuve des phases de vol commune TRAVEL, pas cinq mesures de cadence. Déplacement non interpolé. |
| SPARMANP | Manteau de terreur / SPPR416 | Anneau SHAREA avec palette native, vol observé | Accepté, portée observée | Cinq palettes liées HD ; preuve des phases de vol commune TRAVEL, pas cinq mesures de cadence. Déplacement non interpolé. |
| SPARPUPA | Bénédiction / SPPR101 | Anneau SHAREA avec palette native, vol observé | Accepté, portée observée | Cinq palettes liées HD ; preuve des phases de vol commune TRAVEL, pas cinq mesures de cadence. Déplacement non interpolé. |
| BURNHAND | Mains ardentes / SPWI103 | SPBHANDI | Accepté, portée observée | HD/masque confirmés sur le cône observé. |
| BDWOFOG | Mur de brouillard / OHBWFOG | BDWOFOGA→X58WFOG | Accepté, portée observée | HD/masque et phases impaires confirmés ; transparence corrigée acceptée. |
| GREEHIT | Souffle de dragon noir / SPIN691 | SPBDIMSP, SPBDRAE2 | Accepté, portée observée | HD/masque confirmés sur impact/dispersion observés. |
| REDHIT | Impact rouge / SPIN693 | SPRDRAIM, SPRDRAE2 | Accepté, portée observée | HD/masque confirmés ; manque de preuve antérieur levé. |
| TRAPBOOM | Explosion de piège / SPCL911B sur ennemi | SPSETSCD, SPSETSH, SPFLAMES | Accepté, portée observée | HD/masque confirmés ; condition ennemi satisfaite. |
| WILDZONE | Zone de magie sauvage / OHNROBE3 | SPGRWHRL | Accepté, portée observée | HD/masque confirmés sur l’effet observé. |
| FIREBLGR | Feu vert / XPGREEN | FIREBGRT, FIREBGRX, FIREBGRR | Accepté, portée observée | HD/masque confirmés ; ne valide pas le propriétaire FBFLAMGR. |
| INSEC2 | Fléau d’insectes / SPPR517 | X26PLAA, XIPLAUIN | Accepté, portée observée | HD/masque observés ; pas de mesure finale par phase. |
| ICESTORM | Tempête de glace / SPWI404 | Y31P067, COLDH | Accepté, portée observée | HD observée et masque COLDH ; tous les enfants/fragments non identifiés. |
| LIGHTCHA | Éclairs en chaîne / SPWI615 | Éclairs/branches observés | Accepté, portée observée | V13 : trois traînéesHD+masque+phasesimpaires confirmées, pasQAcomplète de touslescycles. |
| BOLT2 | Semence de feu / FIRESEED.ITM | Vol SPFIRSE2, explosion FSEEDX, dispersion FSEEDA, fumée SPSMPUFF | Accepté, portée observée | V13 : volHD+masque confirmé ;3dessins/phases0,2 seulement, pasdephaseimpaire mesurée. Effets déjàacquis conservés. |
| PFIRE2 | Boule de feu / SPWI304 | FIREBAT et explosion observée | Accepté2026-11-09, rendu courant | Accord CLUA après correctifs ;preuves techniques V3 conservées, pas de nouvelle mesure phases/masque. |
| TRAPSKUL | Piège à crâne / SPWI313 | Vol SKLT, crâne et fragmentsSKLH observés | Accepté2026-11-09, rendu courant | Accord CLUA après correctifs ;preuves V5 conservées, pas de nouvelle capture HD. |
| CHROMORB | Orbe chromatique / SPWI118 | SPCHRORB, couches/transparence observées | Accepté2026-11-09, rendu courant | Accord CLUA après correctifs ;preuves V5 conservées, pas de nouvelle capture HD. |
| MAGICMIS | Projectile magique / QA asset SPMAGMIS du 2026-09-07 | SPMAGMIS | Accepté, portée observée | V14 :28dessinsHD avecmasque,12phasesobservées dont13dessinsimpairs,0rejet ;QAasset7septembreconservée,autrescomptes/propriétaires nonextrapolés. |
| SPKLARST | SPWM157 | Rendu courant, enfant202 SHAREA+SHAREA2 | Accepté2026-11-09, portée observée | Convention secondaire corrigée ;pas de nouvelle capture HD/masque. |
| TSKULLNP | BOLT07 tiré parJan avecXBOW12 | VolSKLT,impact/fragmentsSKLH | Accepté2026-11-09, portée observée | Tir réel selon consigne corrigée ;pas de QA déduite depuis la seule création de munition. |
| SKYBOLT | Appel de la foudre / SPPR302 | Résultat visuel courant | Accepté2026-11-09, portée observée | Raccord HD secondaire encore ouvert ;niveau/contrôleur80..83 non précisé. |
| FIRESTOR | Sort interneSPWI399 | Route couranteFIRESTOR→FIREBALL | Accepté2026-11-09, portée observée | Enfant corrigé37,pas38 ;pas de validation de tous propriétairesFIREBALL. |
| ARROWFLM | TirXBOW15 viaalias13→3 | Y31P056/fuméeSPSMPUFF observés | Accepté2026-11-09, portée observée | Alias moteur également enregistré sousengine13 ;pas de mesure cadence/masque nouvelle. |
| ENTANG2 | SPPR105 | Aspect courantSPGFLSH1 | Accepté2026-11-09, portée observée | Enregistrement secondaire HD encore absent ;accord natif/courant, pas une preuve HD. |
| PFIELD | SPWI421 | Aspect courantSPWRDFLD | Accepté2026-11-09, portée observée | Enregistrement secondaire HD encore absent ;pas de promotion des autres propriétaires. |

- IDs moteur également mis à jour :13(XBOW15),65(HLYMITE),130(SHAIR4),137(SHEARTH6),190(SPSCORIC),202(SHAREA2),207(SPFDEATH),254(SPGENHLA). COW188 accepté conservé ;rendu courant seulement pour ce nouveau lot.
- ICESTORM/SPWI404 :accord courantSPBOOM ajouté à sa QA existante ;raccord HD secondaireSPBOOM reste ouvert.

## État après validation finale

- **[Projectile magique V14 accepté](analysis/projectile-magique-v14-valide-20261028-v1/README.md)** :28dessins finaux HD et masqués,12phases0..11,13dessins de phases impaires,0rejet masque/composition,0traceDropped. Canevas réel64×79 pris en charge sans retraiter le pack64×78.
- Éclairs acquis enV13 :93dessinsHD dont89masqués et50impairs pourSPCHLGT1/2/3. Vol de Semence acquis HD+masque :3dessins/phases0,2 ;aucune phase impaire mesurée dans ce court échantillon. Ne pas redemander ces essais.
- Matrice secondaire :37/37groupes avec preuve technique partagée ;pas de QA de chaque PRO/palette/cycle. Les100chaînes statiquement vérifiées restent distinctes ;aucune validation complète243/release déduite.
- **[Trace temporaire désactivée](analysis/projectile-magique-v14-valide-20261028-v1/trace-disabled.json)**, jeu/loader arrêtés ;DLLV14 et autres octets INI conservés.
- Aucun nouveau test requis sur les composants observés de cette série. Restes distincts :contrats non exercésTSKULLNP/enfantSHAREA202/valeur9 déclaréeLIGHTCHA ;nouveaux assetsBGLRYU/SPCL236U/SPGLYPHI et dépendanceMAGMIS hors campagne ;déplacement interpolé reporté [PROJ-MOTION-001](../pipeline/PROBLEMES_A_RESOUDRE.md#proj-motion-001).
