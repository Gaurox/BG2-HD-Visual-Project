# Décisions techniques

Ce fichier est un inventaire facultatif de solutions et d'essais déjà observés. Il n'impose aucune
méthode, lecture, vérification ou réouverture formelle. Chercher uniquement le sujet utile, reprendre
une solution compatible ou l'écarter si le cas courant diffère. Les états courants restent dans les
catalogues/manifests ; les mesures détaillées restent dans les runs et preuves.

## Cartes

| Sujet | Décision retenue | Réouvrir seulement si… |
|---|---|---|
| Modèle général | SeedVR2 7B INT8, LAB, x4 | comparaison multi-zone + QA explicite favorable à une autre recette |
| Topaz global | refusé ; CGI neutre seulement sous masque local | défaut local impossible à corriger autrement |
| Découpe | orchestrateur à recouvrement, frontières 64 px ; jamais bord à bord | nouvelle méthode de raccord mesurée |
| x2 maps | historique seulement ; x4 par défaut | contrainte moteur/mémoire démontrée |
| Jour/nuit | runs, builds et QA indépendants | jamais par simple commodité |
| Secondaires WED | traiter selon préflight, avec même échelle/découpe | équivalence au primaire prouvée |
| Pages PVRZ | 2048, ou 4096 lorsque le namespace nuit l'exige | extension prouvée de la limite CResRef |
| zlib niveau 0 | diagnostic seulement : latence réduite mais cible manquée et fort surcoût | méthode sélective sous la cible ou arbitrage disque explicite |
| Repagination 2112 | diagnostic block-exact seulement : amélioration insuffisante | nouvelle politique de cache ou off-frame qualifié |
| `CResPVR::Demand` sur worker | interdit : ressources, cache, GL et ownership sont couplés | aucune ; le worker reste CPU/IO privé |
| Handoff hors frame | copie uniquement à la frontière zlib manifestée, sur thread de rendu ; fallback natif à tout écart | nouveau build/callsite ou preuve contradictoire |
| Collision lecteur shadow/native | attendre le retirement du lecteur de la même page avant fallback natif | nouvelle preuve d'ownership plus stricte |
| Prototype courant | B2f : un slot JIT, quatre claims, priorité basse, arrêt au premier wide-view ; default-off | campagne A/B répétée, contrebalancée et cache froid |
| FPS EEex | plafond local 30 FPS tant que les tooltips clignotent en mode uncapped | correctif + A/B dédié `Override_uiDrawMenuStack` |
| Overlays liquides | `overlay-sources.json` décide stock/x2/x4 | QA comparative et modification explicite du manifeste |
| Réparation eau native | référence AR0900 jour : effet procédural désactivé, primaire opaque DXT1→DXT5 exclusivement eau sans secondaire à alpha128, marges incluses ; greffe RGB/alpha bornée aux raccords internes | nouveau contrat de blend, format, rôle WED ou famille ; aucune application globale sans audit |
| Coutures WTLAKE | x4 wavelet avec contexte périodique3×3 puis crop central ; LAB→wavelet seul insuffisant | QA d'une autre recette/famille ; jamais généraliser le resref ni les six frames |
| Suivi eau vers release | `pipeline/water/release-tracking-v1.json` relie chaque WED/variante aux candidats, preuves QA, overlays et runtime ; audit read-only ; aucune autorisation release | migration versionnée du schéma ou transaction release explicitement autorisée |

Procédure complète et cas exclus : [`../pipeline/WATER_REPAIR_RUNBOOK.md`](../pipeline/WATER_REPAIR_RUNBOOK.md).

Les phases B0→B2f et leurs échecs intermédiaires restent dans
`engine/InfinityEngine-Enhancer/source-patchee/docs/validation/`. Ne pas réutiliser `nCount` ou
`bWasMalloced` comme signaux d'ownership : leur offset/sémantique n'ont pas été établis.

## Animations

| Sujet | Décision retenue | Réouvrir seulement si… |
|---|---|---|
| Planche concaténée | refusée ; traiter chaque frame RGB/alpha séparément | jamais |
| Ressource ARE | inventaire typé BAM/WBM/PVRZ ; pipeline BAM limité aux BAM compatibles | pipeline dédié validé pour un autre type/palette |
| Interpolation | TimedTimeline v2 pause-aware ; v3 ajoute le routage par occurrence | nouvelle timeline sans couture ni dérive, validée ingame |
| Pack > 512 Mio | pack d'auteur puis split par zone | runtime borné alternatif démontré |
| Runs interrompus | conserver la recette utile, supprimer les frames partielles, repartir des sources | jamais depuis une sortie partielle |
| Rangement des nouveaux runs | mono-resref sous `animations/ressources/<RESREF>/runs/`; lots sous `animations/batches/`; legacy lu sans déplacement | déplacement explicitement planifié avec réécriture contrôlée de toutes les références |
| Réservation d'un run | `animation_workflow.py new-run --run` crée un marqueur exclusif hors feuille ; `finalize --run` le consomme après validation du run | annulation explicite après contrôle d'absence du run et du `.partial` |
| QA d'un run | `qa-approval.json` = revue technique/vidéo ; décision ingame immuable sous `animations/index/qa-decisions/`, sélection courante séparée | migration versionnée du contrat |
| Finalisation QA | transaction `animation_workflow.py finalize` : décision + sélection + CSV ; refus conservé seulement si réutilisable | jamais par éditions partielles |
| Acceptation candidate | `animation_release.py --run` écrit QA + candidat uniquement | remplacement explicite du candidat |
| Compilation release | `Compile-BG2HD-Release.ps1` compile tous les domaines ; aucune exécution quotidienne | finalisation explicite |
| Gate release | diagnostic delta facultatif ; gates globales au niveau finalisation/package | changement runtime/format/générateur/Core ou package |
| Occlusion xN | bridge moteur pre/post `FXRenderClippingPolys`; le Core release possède son activation ; pour une expansion xN, effacer aussi la cellule x1 transparente adjacente à un effacement natif complet ; masque peint seulement pour donnée WED absente/fausse ou exception v3 | nouvelle famille/build ou régression tracée |
| Polygone WED | prouver l'intersection avec l'alpha ; sinon créer un polygone local borné | WED source ou contour démontré différent |
| Resref avec `_` | `[A-Z0-9_]{1,8}` avec au moins un alphanumérique | jamais |
| Ressource `Blended` | neutraliser RGB sous alpha nul ; prémultiplier si alpha dégradé | jamais par correction alpha seule |
| Micro-effet < ~2 px x1 | natif par défaut ; exception `BUBBLES2` validée le 2026-09-05 avec xBR2 blend, prémultiplication `Blended` et correction moteur de l'expansion d'occlusion | QA ingame complète d'une nouvelle exception |
| Petit sujet pixelisé | recette générale `Small Subject xBR2 → Nearest2 x4 / Apollo30 RGB-Safe` (`small-subject-xbr2-nearest2-apollo30-rgb-safe`) sans blend/AA ; exception `--xbr-blend` non généralisable, validée sur `BUBBLES2` ; nearest2 vers x4, Apollo 8 15→30 ; `nearest-opaque-dilate` si chroma caché ; neutralisation RGB finale si `Blended` | silhouette, alpha ou rendu ingame contradictoires |
| Cycles vides | retirer seulement les cycles vides terminaux non référencés | registre tolérant ou occurrence les référençant |
| Contour 1 bit crénelé | spline `fit 1.0`, puis feather intérieur si la marche reste visible | QA d'un contour où spline seule suffit |
| Fumée : concavités internes rognées | `Spline Fit 1 Multi-Contour — Core Guard 16` (`spline-fit1-multicontour-core-guard16`) : restaurer l'alpha source à partir de 16 px x4 depuis le contour ; spline/feather limités à la bordure | épaisseur, famille ou défaut de contour différents |
| Coupe de canvas visible | `Oval Edge Fade 20/6` (`oval-edge-fade20x6`) : fade elliptique 20 px x4 haut/bas, 6 px x4 côtés | forme, paramètres ou défaut de coupe différents |
| Taille d'une frame x4 | toujours celle de la frame BAM native : `resolve_timeline_subframe`/`resolve_native_subframe` comparent la taille logique au dessin CVidCell et **échouent en silence** (vanilla, aucune ligne de journal) ; ne jamais rembourrer le canevas (`--gaussian-padding-x4`), utiliser `--gaussian-preserve-geometry` | contrat moteur modifié |
| Halo/trou de carte au bord d'une animation | `Lower Edge Cover` (`--lower-edge-cover-rows 5 --lower-edge-cover-depth-x4 5 --lower-edge-cover-zone-x4 10`) : alpha source étendu vers le bas, lissé par la même spline, RGB intérieur repoussé ; anneau rogné au canevas | halo au-dessus ou sur les côtés, ou carte corrigée à la source |
| Cover qui déborde sur un autre élément de la frame (jet du bassin `AM1003A` contre une statue : polygones plats + tache bleue) | `--lower-edge-cover-min-row-x4 190` : anneau limité aux rangées x4 ≥ 190, juste au-dessus des coins gauche/droit du losange (~196-198) ; défaut 0 = `AM1004A` inchangé | autre géométrie de bassin : recalculer le seuil sur les coins |
| Bassin dont la carte x4 porte déjà de l'eau sous l'animation (`AM2801A`, `AM2802A`) | pas de `Lower Edge Cover` : feather `6 px x4` seul ; mesurer au composite sur la carte x4 avant d'appliquer le cover | trou noir + halo constaté sous l'animation |
| Rectangle opaque d'animation visible en carré sur la carte x4 (`AM0309A`) | combler les trous de tramage (`--fill-alpha-holes-max-px-x4`) puis masque de zone animée (`build_animated_zone_mask.py` → `--alpha-mask`) : l'animation ne reste que là où la lumière bouge, la carte fournit le reste | animation dont tout le rectangle bouge |
| Zone en escalier (bord vertical + diagonale isométrique, marches de 4 px) dans une animation x4 | polygone WED « Cover animations » : le pont d'occlusion natif transfère sa visibilité x1 dans l'alpha ; pour une animation de fond qui peint déjà le mur, lier la ressource à son occurrence (`positionBound` ⇒ occlusion cuite, pont coupé) | animation réellement passée derrière un mur |
| Flamme à poses doublées interpolée en 30 fps (`AM003XA`, `AM0323A`, `AM0309A`, `AM0300A`) | condensation correcte mais la source n'a que 7,5 poses/s : Topaz produit surtout des fondus, pulsation perçue à 7,5 Hz ; accepté par l'utilisateur. Pistes non essayées : sélection à mouvement égal sur une sortie Topaz 120 fps, ou poses rejouées à 15 fps | exigence de fluidité sur une flamme |
| Rayon du fondu interne d'une petite flamme `Blended` (ReboutCX + premultiply) | balayage sur la sortie ReboutCX réelle, plus grand rayon gardant le cœur p95 ≥ -5 % (`FLAME2L` : 12 = +0,4 %, 16 = -2,6 %, 20 = -9,7 % avec frange verdâtre ; `FLMM`, rayon inscrit x4 11 : 6 = -1,3 %, 8 = -5,6 %, 12 = -29 %) ; la proportion 0,83 × rayon inscrit x4 des frères donnait 20, trop dur | nouvelle flamme : la proportion ne suffit pas, balayer |
| Spatial d'un feu ou brasero `Blended` pâle (sat < 65 %, lum. moy. > 150 : `FIRE`, `FPIT1M`) | essai comparatif x1 ReboutCX / SeedVR 7B avant de choisir : SeedVR invente billes, volutes ou filaments, ReboutCX reste cohérent ; ReboutCX retenu. Le fondu d'un halo d'aura se rapporte à la taille du canevas (`FPIT1M` 24 = `FPIT1S` 12 x 192/92) | flamme saturée sombre (`FIRE_4`, sat ≥ 75 %, lum. moy. ≤ 80) : SeedVR validé |
| Animation `Blended` en rectangle opaque sur fond noir (alpha 255 partout : `FIRE_3GS`, `FIRE_3GR`) | mesurer les stats sur les pixels allumés ; ReboutCX (SeedVR : visage + scintillement) ; `--mode zero` sans effet, `premultiply --inner-feather-x4 8` = fondu de bord de canevas (voile 3,9 → 0,4) | flamme dont l'alpha porte une vraie silhouette |
| Spatial d'un portail ou d'une surface texturée non `Blended` (`AM1516PT`) | SeedVR 7B/LAB, pas ReboutCX : couleur moyenne conservée (82,2 / 106,4 / 161,0 contre 82,6 / 106,7 / 161,4 en source ; ReboutCX 91,9 rouge, dérive violette) et anneaux nets ; ReboutCX reste le choix des flammes/feux `Blended` | motif sans texture fine à conserver, ou dérive de teinte mesurée sur SeedVR |

Le témoin de rétrocompatibilité TimedTimeline v2 est AR0603 ; les packs v3 prouvent le routage par
occurrence. L'état d'approbation et le renderer exact se lisent uniquement dans
`animation-release-candidates.json` et `renderer-bundle.json`.

## Effets

| Sujet | Décision retenue | Réouvrir seulement si… |
|---|---|---|
| Frontière moteur | owner scopes `CProjectileBAM::Render` + `CVEFVidCell::Render`, substitution au `CInfinity::FXRender` final | nouveau build ou famille hors de ces owners |
| Sélection | resref présent dans le registre ; aucun sort/resref codé en dur | besoin démontré d'un routage par occurrence |
| Diagnostics | stages et mesures de chaque slot bornés par ressource | format de preuve runtime versionné |
| Ajout d'un effet | pack mono-resref immuable puis composition cumulative | format de registre hétérogène requis |
| Composition v1/v2 | versions homogènes seulement ; v1 natif et v2 30 FPS non mélangés | registre avec cadence par ressource validé |

## Icônes

| Sujet | Décision retenue |
|---|---|
| Identité | un asset par resref BAM ITM/SPL ; familles multivaluées dans `icons/index/families.csv`, jamais dans le chemin |
| Extraction | BAM sous `icons/ressources/<RESREF>/source.bam` ; PVRZ V2 partagées sous `icons/dependencies/pvrz/` |
| Runs | mono-asset sous `icons/ressources/<RESREF>/runs/<run-id>/`; batch explicite sous `icons/batches/`; aucun `icons/runs/` global |
| Suivi | `icons/index/processing.csv` sépare production, sélection, QA, installation et release |

## Sprites

| Sujet | Décision retenue |
|---|---|
| Sélection | inventaire normalisé `sprite/index/`, jamais resref deviné |
| Source physique | un BAM stock par `sprite/ressources/<RESREF>/sources/<source-sha256>/`; `source/` runner le référence par liens physiques, sans copie par famille |
| Groupes | `sprite/index/family-groups.csv` décide macro-dossier et bucket depuis `engine_section` |
| Runs | sous la famille logique ; créer la feuille au premier job, jamais précréer tout l'inventaire |
| Suivi | quatre autorités indépendantes : génération courante, décisions QA immuables, reçu d'installation, candidats release |
| Pérennité QA | une acceptation reste acquise tant que les octets concernés et le contrat runtime ne changent pas ; réouverture explicite uniquement |
| Legacy | conserver les `source/`, jobs, runs et catalogues existants ; aucun déplacement/réécriture d'artefact scellé |
| Filtrage QA | `NEAREST`; `LINEAR` est seulement un A/B d'affichage |
| Variantes | pipeline xN cumulatif ; AA/xBR4 direct restent archivés |
| `.work/` | cache supprimable, jamais source |
| Ajout de famille | runbook actif [`../sprite/FAMILY_APPEND.md`](../sprite/FAMILY_APPEND.md) |
| Vérification batch | racine immuable ; `prepare` vérifie seulement le delta, `verify` quotidien contrôle les métadonnées ; `--full-verify` une fois au jalon final |
| Routage shader D7 x1 | scopes propriétaires créature + appel monde objet au sol manifesté ; ton neutre mis en file sur slot 5 `fpSprite`, slot 7 `fpSELECT` natif conservé ; aucun forçage HD/x2/ton spécial/contrat absent |
| Sampler Catmull–Rom D7 x1 | `NEAREST` temporaire limité au draw x1 `fpSprite`/`fpSELECT`, puis restauration exacte min/mag, binding et unité active ; jamais sur texture catalogue HD |

## Vidéos

| Sujet | Décision retenue | Réouvrir seulement si… |
|---|---|---|
| Upscale spatial v2 | SeedVR2 3B INT8 ConvRot, LAB, 1280×720 → 1920×1080 | QA comparative explicite favorable à une autre recette |
| VAE | tuiles 512, recouvrement 128, temporel 64/8 | défaut de couture ou contrainte mémoire démontrée |
| Inférence | seed `959948902156062`, 1 pas Euler, CFG 1, simple, denoise 1, couleur `lab` | nouvelle recette validée |
| Vidéo longue | latent temporel `auto`, recouvrement 0, fusion activée | couture temporelle mesurée |
| Temporalité | cadence et nombre d'images source conservés ; aucune interpolation | étape d'interpolation validée séparément |
| Périmètre v1 | cinématiques 1280×720 ; tutoriels 384×480 refusés | recette dédiée aux tutoriels |
| Sortie | artefact technique d'upscale ; audio et encodage de livraison non autoritaires | définition des étapes suivantes |
| Interpolation v1 | Topaz Apollo 8, 15→30 fps, `2N−1`, MOV ProRes 422 HQ technique | QA comparative explicite favorable à une autre recette |
| Doublons vidéo | `rdt=-0.01` ; supprimer uniquement les répétitions adjacentes exactes par hash décodé | politique temporelle différente explicitement validée |
| Audio après interpolation | exclu ; synchronisation et encodage définis dans une étape ultérieure | définition de l'encodage final |
| Organisation des runs | `video/<asset>/runs/<run-id>` ; aucun nouveau run global | jamais |
| Sélection | `video/index/processing.csv` sépare runs validés par étape et run du patch | changement explicite de sélection ou d'intégration |

## Release et workspace

| Sujet | Décision retenue |
|---|---|
| Sélection release | tuple exact asset/variante/run/build/hash, jamais simple liste d'IDs |
| Packages/ZIP | hors dépôt, reproductibles depuis sources et manifests |
| Dépendances | hors dépôt, aucun junction `node_modules` |
| Références externes | URL + commit suffisent ; re-cloner au besoin |
| Data-plane supersédé | archive externe indexée ; restaurer seulement l'entrée nécessaire |
| Clone autonome | le plan de contrôle committé fait autorité ; médias ignorés seulement si déclarés |
| Candidat renderer | transaction DLL+INI avec reçu, jamais copie brute |
| Tests locaux | code : `--targeted --path ...`, module direct seulement ; autorités/assets/docs : aucun test Python |
| Élargissement des tests | supprimé : le sélecteur ne connaît que la correspondance directe script/test |
| Projections globales | finalisation/livrable seulement ; mono-passe ; déterminisme doublé seulement sur demande explicite |

## Maintenance

Ajouter une décision seulement après preuve ou arbitrage explicite. Ne recopier ici ni compteurs,
ni statuts d'`areas.csv`, ni listes de release.
