# Décisions techniques et essais clos

Ce fichier conserve uniquement les décisions qui évitent de répéter un essai invalidé. Les états
de production restent dans les catalogues et manifests. Un essai n'est rouvert que si sa colonne
« condition de réouverture » est satisfaite.

## Maps

| Décision | Résultat observé | Solution retenue | Condition de réouverture |
|---|---|---|---|
| SeedVR2 3B comme modèle général | Détails et cohérence inférieurs aux références 7B/LAB | SeedVR2 7B INT8, LAB, x4 | Nouvelle comparaison contrôlée sur plusieurs zones et QA utilisateur |
| Upscale global Topaz des cartes | Transforme le décor et la colorimétrie ; essais AR0602 refusés | SeedVR ; Topaz CGI neutre seulement sous masque local explicitement validé | Défaut local impossible à corriger autrement |
| Découpe bord à bord | Coutures visibles et absence de contexte entre morceaux | `run_seedvr_comfyui.py --split-rows/--split-grid` avec recouvrement et fusion | Jamais sans nouvelle méthode de raccord mesurée |
| Échelle maps x2 | Ancienne méthode, remplacée | x4 par défaut ; conserver x2 uniquement comme historique | Contrainte moteur ou mémoire démontrée sur un cas précis |
| Jour et nuit dans un même résultat | Risque de mélanger les WED et pages | Deux traitements indépendants, mêmes gates | Aucun |
| Secondaires omises par défaut | Ne préserve pas correctement les variantes WED | Préflight puis traitement primaire/secondaire selon le WED | Cas explicitement prouvé équivalent au primaire |
| Pagination PVRZ fixe 2048 | Dépassement du resref 8 caractères sur les variantes nuit volumineuses | Page 4096 lorsque nécessaire ; gate longueur de resref | Seulement si le moteur étend la limite CResRef |
| AR0602 hybride CGI `test-27` | Référence historique, plus canonique | Run x4 7B/LAB sans masque CGI désigné par `areas.csv` | Nouvelle QA comparée et décision catalogue |
| Overlays liquides globaux | L'installation x4 tardive contredisait la QA maps x2 et WTPOOL x4 restait figé | `overlay-sources.json` : WTLAKE/POOL/LAKA-D x2, WTLAVA-D x4, WTSWAM/WTSEW/WTOIL stock ; chaque fichier publié est épinglé | Nouvelle QA comparative par resref et modification explicite du manifeste |

## Animations

| Décision | Résultat observé | Solution retenue | Condition de réouverture |
|---|---|---|---|
| Upscaler une planche concaténée | Fuites entre frames et alpha incorrect | Extraire et traiter chaque frame RGB/alpha séparément | Jamais |
| Interpolation cyclique multi-contexte | Complexité et raccords non maîtrisés | TimedTimeline pause-aware pour le 15→30 fps | Nouvelle preuve ingame sans couture ni dérive |
| Horloge runtime uniquement diagnostique | Supersédée par le prototype PORTL1A validé | TimedTimeline v2 reste compatible ; v3 ajoute le routage par occurrence, validé avec AR0900 et publié avec le renderer alpha.5 | Nouvelle version de registre ou régression du témoin AR0602 v2 |
| Pack global supérieur à 512 Mio | Risque mémoire et registre non borné | Packs par zone avec installation/restauration | Nouveau runtime démontré borné |
| AR0516 et AR0603 incomplets | Runs arrêtés avant authoring/QA, aucune référence externe | Frames brutes supprimées ; request et manifest conservés sous `archive/experiments/abandoned-animation-runs/` | Repartir des sources, jamais des frames partielles |
| Validation release globale après chaque animation | Staging et hash de l'ensemble du payload, désormais plusieurs Gio, ralentissent la QA sans augmenter la preuve du pack modifié | Gate delta par zone : manifeste, registre, index, frames, staging temporaire et TP2 ; gates globales conservées avant archive | Changement runtime, générateur, format de pack ou Core ; ou préparation d'un package |

## Sprites

| Décision | Résultat observé | Solution retenue | Condition de réouverture |
|---|---|---|---|
| Choix à partir du nom des BAM | Ne couvre pas les relations ANIMATE/INI/ITM et les collisions | Inventaire normalisé `sprite/index/` | Jamais |
| Filtrage LINEAR comme résultat QA | Lissage d'affichage seulement, non représentatif du baseline | `NEAREST` obligatoire pour QA | Nouvelle décision visuelle explicite |
| Variantes AA et xBR4 direct CDMB1 | Essais de comparaison, non retenus comme catalogue courant | Pipeline xN cumulatif `run_creature_sprite_x2.py` | Nouvelle demande d'A/B ciblée |
| `.work/` comme source | Cache CMake reconstruisible | Jobs/manifests sont les sources ; `.work/` est supprimable | Jamais |
| Runbook d'ajout de famille dans `docs/archive` | Contradiction documentaire | [`sprite/FAMILY_APPEND.md`](../sprite/FAMILY_APPEND.md) est le runbook actif | Lors d'un remplacement complet du pipeline |

## Installer et Git

| Décision | Résultat observé | Solution retenue | Condition de réouverture |
|---|---|---|---|
| Déduire la release du seul ensemble d'area IDs | Environ 37 sélections run/build divergent d'`areas.csv` | Gate exact `area + variante + run + build + hash` avant nouvelle release | Après automatisation de la sélection |
| Conserver packages et ZIP dans le projet actif | Environ 25 Gio de copies générées et obsolètes | Artifacts externes avec checksum ; sources/manifests seulement dans le dépôt | Aucun |
| Junctions `node_modules` dans le dépôt | Git et les agents parcourent le runtime externe | Dépendances installées hors dépôt, aucun reparse point | Jamais |
| Anciens clones externes complets | Données reproductibles et non utilisées | Conserver URL+commit, supprimer le clone | Re-cloner au besoin : `Goddard/Project-IE-4k@c0f8180`, `dtiefling/dshaders@4722673` |
| Packs/runs/builds data-plane supersédés | 149 groupes, 79,72 Gio, dont de nombreux packs combinés redondants, les anciens backups locaux, 8 builds CMake, 29 objets Git temporaires et un rollback xN dupliqué par l'historique Git | Archive externe `archive-post-release-20260827/MANIFEST.csv`; garder dans le workspace uniquement les sources release, runs catalogue/QA et pack installé courant | Restaurer seulement la ligne nécessaire du manifeste externe |
| Checkout Git autonome | Clone propre validé sans donnée ignorée : 159 tests Python, Phase 2 et 2 tests C++ passent | Le plan de contrôle committé est la source de vérité ; les gros médias restent hors Git selon `.gitignore` | Réouvrir si un test exige une donnée locale absente du clone |

## Règle de maintenance

Ajouter une ligne seulement après une preuve ou une décision explicite. Ne pas recopier les
statuts d'`areas.csv`, des index ou de `release.json`. Les rapports détaillés historiques vivent
dans `docs/archive/` ou `archive/`, hors routage initial des agents.
