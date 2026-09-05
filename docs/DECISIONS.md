# Décisions techniques

Ce fichier conserve les choix réutilisables et les essais à ne pas répéter. Les états courants
restent dans les catalogues/manifests ; les mesures détaillées restent dans les runs et preuves.

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
| Runs interrompus | conserver request/manifest, supprimer les frames partielles, repartir des sources | jamais depuis une sortie partielle |
| Rangement des nouveaux runs | mono-resref sous `animations/ressources/<RESREF>/runs/`; lots sous `animations/batches/`; legacy lu sans déplacement | déplacement explicitement planifié avec réécriture contrôlée de toutes les références |
| Réservation d'un run | `animation_workflow.py new-run --run` crée un marqueur exclusif hors feuille ; `finalize --run` le consomme après validation du run | annulation explicite après contrôle d'absence du run et du `.partial` |
| QA d'un run | `qa-approval.json` = revue technique/vidéo ; décision ingame immuable sous `animations/index/qa-decisions/`, sélection courante séparée | migration versionnée du contrat |
| Finalisation QA | transaction `animation_workflow.py finalize` : décision + sélection + CSV ; essais refusés conservés | jamais par éditions partielles |
| Promotion release | transaction ciblée `animation_release.py`, accord release distinct, aucun staging/package | changement partagé de renderer/format/Core ou package |
| Gate release | delta par zone pendant la tâche ; gates globales au niveau package | changement runtime/format/générateur/Core ou package |
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

Le témoin de rétrocompatibilité TimedTimeline v2 est AR0603 ; les packs v3 prouvent le routage par
occurrence. L'état d'approbation et le renderer exact se lisent uniquement dans
`animation-release-candidates.json` et `renderer-bundle.json`.

## Sprites

| Sujet | Décision retenue |
|---|---|
| Sélection | inventaire normalisé `sprite/index/`, jamais resref deviné |
| Filtrage QA | `NEAREST`; `LINEAR` est seulement un A/B d'affichage |
| Variantes | pipeline xN cumulatif ; AA/xBR4 direct restent archivés |
| `.work/` | cache supprimable, jamais source |
| Ajout de famille | runbook actif [`../sprite/FAMILY_APPEND.md`](../sprite/FAMILY_APPEND.md) |

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
| Tests locaux | plan-only par défaut ; `--run` et choix utilisateur obligatoire entre ciblés, tous ou aucun |
| Élargissement des tests | `--targeted` ne devient jamais une suite complète ; `--full --run` exige un accord distinct |
| Projections globales | plan-only et mono-passe par défaut ; choix séparé scopes ciblés/toutes/aucune ; déterminisme doublé seulement sur accord/CI |

## Maintenance

Ajouter une décision seulement après preuve ou arbitrage explicite. Ne recopier ici ni compteurs,
ni statuts d'`areas.csv`, ni listes de release.
