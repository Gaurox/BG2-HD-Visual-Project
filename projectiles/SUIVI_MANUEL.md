# Validations manuelles des projectiles — 2026-10-28

**QA52 acceptée — 2026-11-09** : [décision et périmètre](analysis/components-qa52-20261109-v1/README.md). 52 images acceptées le 2026-11-09 : 31 anciens effets, 18 réemplois, 3 effets 1WDC. 17 images liées à 138 PRO ; validation des composants seule. SANCTRY/SPPR109 et SPSHIELD/SPWI311 : transparence confirmée avec les vrais sorts. Packs mono-BAM figés sur les versions installées testées ; 0 inférence/interpolation nouvelle. Autres QA, installation et release préservées ; GPU en pause.

- Autorité par PRO : [`index/work-tracking.json:qa`](index/work-tracking.json). [Décisions figées](analysis/validations-manuelles-consolidees-20261028-v1/decisions.json), [validation finale V14](analysis/projectile-magique-v14-valide-20261028-v1/acceptance.json).
- 29 PRO avec acceptation visuelle des composants observés ; 3 décisions historiques conservées séparément. Ces nombres ne sont pas des chaînes intégrales acceptées.
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
| PFIRE2 | Boule de feu / SPWI304 | FIREBAT et effet de Boule de feu observé | Historique avant correctif | Aspect positif signalé avant correctif du vol ; V3 HD/masque/phases confirmés techniquement, sans nouvel accord visuel V3 explicite. |
| TRAPSKUL | Piège à crâne / SPWI313 | Vol SKLT observé | Historique avant correctif | Aspect positif V3 ; rendu V5 corrigé confirmé techniquement, sans nouvel accord visuel V5 explicite. |
| CHROMORB | Orbe chromatique / SPWI118 | SPCHRORB observé | Historique avant correctif | Aspect positif V3 ; rendu V5 corrigé confirmé techniquement, sans nouvel accord visuel V5 explicite. |
| MAGICMIS | Projectile magique / QA asset SPMAGMIS du 2026-09-07 | SPMAGMIS | Accepté, portée observée | V14 :28dessinsHD avecmasque,12phasesobservées dont13dessinsimpairs,0rejet ;QAasset7septembreconservée,autrescomptes/propriétaires nonextrapolés. |

## État après validation finale

- **[Projectile magique V14 accepté](analysis/projectile-magique-v14-valide-20261028-v1/README.md)** :28dessins finaux HD et masqués,12phases0..11,13dessins de phases impaires,0rejet masque/composition,0traceDropped. Canevas réel64×79 pris en charge sans retraiter le pack64×78.
- Éclairs acquis enV13 :93dessinsHD dont89masqués et50impairs pourSPCHLGT1/2/3. Vol de Semence acquis HD+masque :3dessins/phases0,2 ;aucune phase impaire mesurée dans ce court échantillon. Ne pas redemander ces essais.
- Matrice secondaire :37/37groupes avec preuve technique partagée ;pas de QA de chaque PRO/palette/cycle. Les100chaînes statiquement vérifiées restent distinctes ;aucune validation complète243/release déduite.
- **[Trace temporaire désactivée](analysis/projectile-magique-v14-valide-20261028-v1/trace-disabled.json)**, jeu/loader arrêtés ;DLLV14 et autres octets INI conservés.
- Aucun nouveau test requis sur les composants observés de cette série. Restes distincts :contrats non exercésTSKULLNP/enfantSHAREA202/valeur9 déclaréeLIGHTCHA ;nouveaux assetsBGLRYU/SPCL236U/SPGLYPHI et dépendanceMAGMIS hors campagne ;déplacement interpolé reporté [PROJ-MOTION-001](../pipeline/PROBLEMES_A_RESOUDRE.md#proj-motion-001).
